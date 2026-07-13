import json

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.generation_poller import GenerationPoller
from ai_drama_web.services.legacy_agnes_backfill import LegacyAgnesBackfill
from ai_drama_web.store import ProductStore
from tests.fixtures.m6e_store_factory import ALL_M6_MIGRATIONS, M6EStoreFactory


ACTIVE = ("queued", "submitting", "submitted", "polling")
TERMINAL = ("completed", "failed")


def _job(store, runtime, project_id, status, index):
    request_object_id = runtime.write_text_object(json.dumps({"prompt": status}))
    job = store.create_generation_job(
        provider="agnes",
        job_type="video",
        project_id=project_id,
        chapter_id="legacy-chapter",
        shot_id=f"shot-{index}",
        prompt_revision_id=f"prompt-{index}",
        idempotency_key=f"legacy-{status}-{index}",
        request_hash=f"hash-{status}-{index}",
        request_object_id=request_object_id,
        attempt_number=1,
    )
    store.transition_generation_job(job.job_id, "queued")
    if status in {"submitting", "submitted", "polling", "completed", "failed"}:
        store.transition_generation_job(job.job_id, "submitting")
    if status in {"submitted", "polling", "completed", "failed"}:
        store.attach_generation_provider_job(
            job.job_id,
            provider_job_id=f"video-{index}",
            response_object_id="",
        )
    if status in {"polling", "completed", "failed"}:
        store.transition_generation_job(job.job_id, "polling")
    if status in {"completed", "failed"}:
        store.transition_generation_job(job.job_id, status)
    return store.get_generation_job(job.job_id)


def test_fresh_and_replayed_m6_store_is_deterministic(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    first = ProductStore(runtime)
    supplier_ids = {item.slug: item.supplier_id for item in first.list_suppliers()}
    migrations = [
        row["migration_id"]
        for row in runtime.conn.execute(
            "SELECT migration_id FROM schema_migrations ORDER BY migration_id"
        ).fetchall()
    ]

    replayed = ProductStore(runtime)

    assert {item.slug: item.supplier_id for item in replayed.list_suppliers()} == supplier_ids
    assert [
        row["migration_id"]
        for row in runtime.conn.execute(
            "SELECT migration_id FROM schema_migrations ORDER BY migration_id"
        ).fetchall()
    ] == migrations
    assert len(migrations) == len(set(migrations))


def test_real_m5_schema_upgrades_without_rewriting_history(tmp_path):
    runtime, expected = M6EStoreFactory(tmp_path).m5()

    migrated = ProductStore(runtime)
    replayed = ProductStore(runtime)

    project = replayed.get_project(expected["project_id"])
    job = replayed.get_generation_job(expected["job_id"])
    result = replayed.get_generation_result(expected["result_id"])
    assert project.name == "M5 Project"
    assert replayed.get_chapter(expected["chapter_id"]).current_source_revision_id == "m5-source"
    assert runtime.read_text(expected["source_object_id"]) == "m5 source history"
    assert job.internal_status == "completed"
    assert job.provider_job_id == "m5-video-id"
    assert job.snapshot_hash == ""
    assert result.object_id == expected["result_object_id"]
    assert runtime.read_bytes_object(result.object_id) == b"m5-result-media"
    assert runtime.read_text(job.request_object_id) == '{"prompt":"m5 completed"}'
    for migration_id in ALL_M6_MIGRATIONS:
        assert runtime.conn.execute(
            "SELECT COUNT(*) AS n FROM schema_migrations WHERE migration_id=?",
            (migration_id,),
        ).fetchone()["n"] == 1
    assert migrated.get_project(expected["project_id"]).project_id == project.project_id


@pytest.mark.parametrize("stage", ("m6a", "m6b", "m6c", "m6d"))
def test_m6_intermediate_stage_upgrade_preserves_pointers_revisions_and_rows(tmp_path, stage):
    root = tmp_path / stage
    expected = M6EStoreFactory(root).intermediate(stage)
    runtime = RuntimeStore(root / "runtime.db", root / "objects")

    upgraded = ProductStore(runtime)
    first_models = {
        (model.supplier_id, model.supplier_model_id, model.revision)
        for supplier in upgraded.list_suppliers()
        for model in upgraded.list_supplier_models(supplier.supplier_id)
    }
    replayed = ProductStore(runtime)
    second_models = {
        (model.supplier_id, model.supplier_model_id, model.revision)
        for supplier in replayed.list_suppliers()
        for model in replayed.list_supplier_models(supplier.supplier_id)
    }

    assert replayed.get_project(expected["project_id"]) is not None
    assert runtime.read_text(expected["source_object_id"]) == f"{stage} immutable source"
    assert first_models == second_models
    assert len(second_models) == len({(supplier_id, model_id) for supplier_id, model_id, _ in second_models})
    assert all(revision >= 1 for _supplier_id, _model_id, revision in second_models)
    for slug, pointer in expected["suppliers"].items():
        supplier = next(item for item in replayed.list_suppliers() if item.slug == slug)
        assert (
            supplier.supplier_id,
            supplier.current_supplier_version_id,
            supplier.current_config_revision_id,
            supplier.revision,
            supplier.config_revision,
        ) == pointer
    for migration_id in ALL_M6_MIGRATIONS:
        assert runtime.conn.execute(
            "SELECT COUNT(*) AS n FROM schema_migrations WHERE migration_id=?",
            (migration_id,),
        ).fetchone()["n"] == 1


def test_active_legacy_matrix_backfills_queryable_jobs_and_fails_closed_without_id(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="M5 legacy")
    jobs = {
        status: _job(store, runtime, project.project_id, status, index)
        for index, status in enumerate((*ACTIVE, *TERMINAL), start=1)
    }
    # queued/submitting have no stable provider id and must be audited fail-closed.
    secrets = LocalSecretStore(tmp_path)
    secrets.set_agnes_api_key("local-legacy-fixture")

    first = LegacyAgnesBackfill(store, runtime, tmp_path, secrets).run()
    second = LegacyAgnesBackfill(store, runtime, tmp_path, secrets).run()

    assert (first, second) == (2, 0)
    for status in ("submitted", "polling"):
        migrated = store.get_generation_job(jobs[status].job_id)
        assert migrated.snapshot_hash
        assert migrated.legacy_backfill_state == "completed"
        assert migrated.provider_job_id == jobs[status].provider_job_id
        assert migrated.internal_status == status
    for status in ("queued", "submitting"):
        blocked = store.get_generation_job(jobs[status].job_id)
        assert blocked.snapshot_hash == ""
        assert blocked.legacy_backfill_state == "failed"
        assert blocked.error_code == "LEGACY_PROVIDER_ID_MISSING"
        assert blocked.internal_status == ("cancelled" if status == "queued" else "failed")
        assert blocked.completed_at
    for status in TERMINAL:
        terminal = store.get_generation_job(jobs[status].job_id)
        assert terminal.snapshot_hash == ""
        assert terminal.legacy_backfill_state == ""
        assert terminal.internal_status == status


@pytest.mark.asyncio
async def test_missing_legacy_provider_id_is_terminal_before_poller_and_never_submits(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Legacy submit guard")
    queued = _job(store, runtime, project.project_id, "queued", 1)
    submitting = _job(store, runtime, project.project_id, "submitting", 2)
    secrets = LocalSecretStore(tmp_path)

    assert LegacyAgnesBackfill(store, runtime, tmp_path, secrets).run() == 0

    class NoSubmitBackend:
        submit_count = 0

        def create_video_job(self, _request):
            self.submit_count += 1
            raise AssertionError("legacy job without provider id must never submit")

    backend = NoSubmitBackend()
    cycle = await GenerationPoller(
        store, runtime, backend, rpm=60, poll_interval_seconds=1
    ).run_cycle()

    assert cycle.submitted == 0
    assert backend.submit_count == 0
    assert store.get_generation_job(queued.job_id).internal_status == "cancelled"
    assert store.get_generation_job(submitting.job_id).internal_status == "failed"
