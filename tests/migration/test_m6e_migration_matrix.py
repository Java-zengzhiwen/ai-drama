import json

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.legacy_agnes_backfill import LegacyAgnesBackfill
from ai_drama_web.store import ProductStore


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
        assert blocked.internal_status == status
    for status in TERMINAL:
        terminal = store.get_generation_job(jobs[status].job_id)
        assert terminal.snapshot_hash == ""
        assert terminal.legacy_backfill_state == ""
        assert terminal.internal_status == status
