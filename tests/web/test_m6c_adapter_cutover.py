import json
import pytest
import hashlib
import tempfile
import subprocess
import threading
from pathlib import Path

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.config import Settings
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.adapters import FakeSupplierAdapter, SupplierAdapterGateway, sanitize_evidence
from ai_drama_web.suppliers.idempotency import SupplierIdempotencyConflict, canonical_request_hash
from ai_drama_web.suppliers.resolution import ModelBindingService, ModelResolver
from ai_drama_web.suppliers.snapshots import SnapshotBuilder, snapshot_hash
from ai_drama_web.suppliers.snapshots import load_snapshot, persist_snapshot
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.services.generation_poller import GenerationPoller
from ai_drama_web.providers.fake import FakeGenerationBackend
from tests.web.model_test_support import create_model, install_test_supplier_runtime
from ai_drama_web.suppliers.credentials import SupplierCredentialStore
from ai_drama_web.services.m6_generation import M6GenerationCoordinator, M6GenerationError
from ai_drama_web.services.legacy_agnes_backfill import LegacyAgnesBackfill, _legacy_source
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.suppliers.builtin_adapters import OPENAI_SOURCE, install_builtin_adapters
from ai_drama_web.suppliers.execution import SnapshotExecutionGateway, SupplierExecutionError
from ai_drama_web.suppliers.worker import SupplierInvocationResult, WorkerLimits
from ai_drama_web.suppliers.snapshots import SupplierRuntimeUnavailable
from ai_drama_web.suppliers.rate_limits import SupplierRateLimiter
from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from ai_drama_web.suppliers.reasoning import (
    ReasoningEffortError,
    resolve_reasoning_effort,
)


def test_feature_flag_defaults_off():
    assert Settings().m6_supplier_execution_enabled is False


@pytest.mark.asyncio
async def test_feature_flag_off_freezes_snapshot_jobs_without_legacy_submit_or_poll(tmp_path):
    runtime, store, project, snapshot = _snapshot_fixture(tmp_path)
    queued, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id, capability="video", provider="m6:test:video",
        job_type="video", project_id=project.project_id, chapter_id="chapter",
        shot_id="queued", prompt_revision_id="prompt", idempotency_key="rollback-queued",
        request={"prompt": "queued"}, snapshot=snapshot,
    )
    polling, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id, capability="video", provider="m6:test:video",
        job_type="video", project_id=project.project_id, chapter_id="chapter",
        shot_id="polling", prompt_revision_id="prompt", idempotency_key="rollback-polling",
        request={"prompt": "polling"}, snapshot=snapshot,
    )
    store.transition_generation_job(polling.job_id, "submitting")
    store.record_submission_attempt(polling.job_id, state="accepted", provider_job_id="frozen-video")
    store.commit_accepted_submission(polling.job_id)
    store.transition_generation_job(polling.job_id, "polling")

    class LegacyBackend:
        submit_count = 0
        poll_count = 0

        def create_video_job(self, _request):
            self.submit_count += 1
            raise AssertionError("snapshot job must not fall through legacy submit")

        def get_video_job_status(self, _provider_job_id):
            self.poll_count += 1
            raise AssertionError("snapshot job must not fall through legacy poll")

    backend = LegacyBackend()
    execution = GenerationExecutionService(
        store, runtime, backend, supplier_execution_enabled=False
    )
    cycle = await GenerationPoller(
        store, runtime, backend, rpm=60, poll_interval_seconds=1,
        execution_service=execution,
    ).run_cycle()

    assert (cycle.submitted, cycle.polled, cycle.skipped) == (0, 0, 2)
    assert (backend.submit_count, backend.poll_count) == (0, 0)
    assert store.get_generation_job(queued.job_id).internal_status == "queued"
    assert store.get_generation_job(polling.job_id).internal_status == "polling"


def test_fake_video_polls_video_id_and_submits_once():
    fake = FakeSupplierAdapter()
    gateway = SupplierAdapterGateway(fake, supplier_slug="fake")
    submitted = gateway.video_submit({"prompt": "p"})
    gateway.video_poll(submitted.value["video_id"])
    gateway.video_fetch(submitted.value["video_id"])
    assert submitted.value == {"video_id": "fake-video-1"}
    assert (fake.submit_count, fake.poll_count, fake.fetch_count) == (1, 1, 1)


def test_evidence_removes_secret_keys_and_signed_query():
    value = sanitize_evidence({"Authorization": "Bearer x", "url": "https://example.invalid/a?token=x"})
    assert value == {"url": "https://example.invalid/a"}


def test_m6c_migration_is_additive_and_replayable(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    ProductStore(runtime)
    columns = {row["name"] for row in store.conn.execute("PRAGMA table_info(generation_jobs)")}
    assert {"snapshot_hash", "snapshot_object_id", "source_job_id", "rerun_resolution_mode"} <= columns
    assert store.conn.execute("SELECT 1 FROM schema_migrations WHERE migration_id = 'm6c_adapter_cutover_v1'").fetchone()
    assert store.conn.execute("SELECT COUNT(*) FROM generation_submission_attempts").fetchone()[0] == 0


def _snapshot_fixture(tmp_path, capability="video"):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="M6C")
    supplier = store.list_suppliers()[0]
    install_test_supplier_runtime(store, supplier, rate_bucket="frozen-bucket")
    supplier = store.get_supplier(supplier.supplier_id)
    model = create_model(store, supplier, capability=capability, name=f"fake-{capability}", catalog_revision=0, key=f"model-{capability}")
    defaults = {"text": "", "image": "", "video": ""}
    defaults[capability] = model.supplier_model_id
    ModelBindingService(store).replace(project.project_id, defaults=defaults, overrides={}, expected_revision=0)
    operation = {"video": "shot_video_generation", "image": "storyboard_keyframe_image", "text": "script_adaptation"}[capability]
    resolved = ModelResolver(store).resolve(project.project_id, operation)
    snapshot = SnapshotBuilder(store).build(
        resolved,
        credential_resolution_mode="current",
        resolved_credential_version_id="",
        resolved_constraints={},
        worker_limits={"timeout_seconds": 30},
    )
    return runtime, store, project, snapshot


def _coordinator_fixture(tmp_path, capability):
    runtime, store, project, _snapshot = _snapshot_fixture(tmp_path, capability)
    supplier = store.list_suppliers()[0]
    credentials = SupplierCredentialStore(store, tmp_path)
    credentials.replace(supplier.supplier_id, "selected-secret", expected_revision=0)
    gateway = _SnapshotGateway()
    coordinator = M6GenerationCoordinator(store, runtime, credentials, gateway)
    return runtime, store, project, supplier, gateway, coordinator


def test_atomic_enqueue_persists_snapshot_job_attempt_and_scoped_idempotency(tmp_path):
    runtime, store, project, snapshot = _snapshot_fixture(tmp_path)
    request = {"prompt": "shot"}
    job, created = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id,
        capability="video",
        provider="agnes",
        job_type="video",
        project_id=project.project_id,
        chapter_id="chapter",
        shot_id="shot",
        prompt_revision_id="revision",
        idempotency_key="same",
        request=request,
        snapshot=snapshot,
    )
    assert created is True
    assert job.internal_status == "queued"
    assert job.snapshot_hash == snapshot_hash(snapshot)
    assert runtime.read_text(job.snapshot_object_id)
    assert store.get_submission_attempt(job.job_id)["state"] == "prepared"
    replay, replay_created = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id, capability="video", provider="agnes", job_type="video",
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="same", request=request, snapshot=snapshot,
    )
    assert (replay.job_id, replay_created) == (job.job_id, False)


def test_atomic_enqueue_rejects_same_scope_key_with_changed_snapshot(tmp_path):
    _runtime, store, project, snapshot = _snapshot_fixture(tmp_path)
    args = dict(supplier_id=snapshot.supplier_id, capability="video", provider="agnes", job_type="video",
                project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
                idempotency_key="conflict", request={"prompt": "one"}, snapshot=snapshot)
    store.enqueue_generation_job_with_snapshot(**args)
    with pytest.raises(SupplierIdempotencyConflict, match="IDEMPOTENCY_CONFLICT"):
        store.enqueue_generation_job_with_snapshot(**{**args, "request": {"prompt": "two"}})
    assert store.conn.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 1


def test_m6_legacy_unique_key_is_namespaced_by_supplier_and_capability(tmp_path):
    runtime, store, project, supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "video")
    video, _ = coordinator.enqueue_video(
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="shared-key", request={"prompt": "video"},
    )
    image_model = create_model(
        store, store.get_supplier(supplier.supplier_id), capability="image", name="fake-image-shared",
        catalog_revision=1, key="image-shared-model",
    )
    video_model_id = load_snapshot(store, video.snapshot_hash).supplier_model_id
    ModelBindingService(store).replace(
        project.project_id,
        defaults={"text": "", "image": image_model.supplier_model_id, "video": video_model_id},
        overrides={}, expected_revision=1,
    )
    chapter = store.create_chapter(project.project_id, title="Chapter", position=1)
    image = coordinator.generate_image(
        project_id=project.project_id, chapter_id=chapter.chapter_id, idempotency_key="shared-key",
        request={"prompt": "image", "size": "1024x768", "asset_type": "shot_keyframe", "name": "Image"},
    )
    image_job = store.get_generation_job(image["job_id"])
    assert video.idempotency_key == image_job.idempotency_key == "shared-key"
    assert video.provider != image_job.provider
    assert store.conn.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 2


class _SnapshotGateway:
    def __init__(self):
        self.calls = []

    def invoke(self, snapshot_hash_value, operation, payload):
        self.calls.append((snapshot_hash_value, operation, payload))
        if operation == "videoPoll":
            return {"status": "completed", "video_id": payload["video_id"]}
        if operation == "videoFetch":
            return {"media_type": "video/mp4", "bytes": b"snapshot-video"}
        if operation == "imageRequest":
            return {"media_type": "image/png", "bytes": b"snapshot-image", "url": "https://fake.invalid/a?token=x"}
        if operation == "textRequest":
            return {"output": "deterministic text", "usage": {"input_tokens": 2, "output_tokens": 3}, "authorization": "sensitive-marker"}
        raise AssertionError(operation)


@pytest.mark.asyncio
async def test_poller_routes_active_job_only_by_frozen_snapshot_and_video_id(tmp_path):
    runtime, store, project, snapshot = _snapshot_fixture(tmp_path)
    job, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id, capability="video", provider="agnes", job_type="video",
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="poll", request={"prompt": "shot"}, snapshot=snapshot,
    )
    store.transition_generation_job(job.job_id, "submitting")
    store.record_submission_attempt(job.job_id, state="accepted", provider_job_id="video-id-1")
    store.commit_accepted_submission(job.job_id)
    gateway = _SnapshotGateway()
    execution = GenerationExecutionService(
        store, runtime, FakeGenerationBackend(), supplier_gateway=gateway, supplier_execution_enabled=True
    )
    poller = GenerationPoller(store, runtime, FakeGenerationBackend(), rpm=1, poll_interval_seconds=1, execution_service=execution)

    result = await poller.run_cycle()

    assert result.polled == 1
    assert [(call[1], call[2]["video_id"]) for call in gateway.calls] == [
        ("videoPoll", "video-id-1"), ("videoFetch", "video-id-1")
    ]
    assert all(call[0] == job.snapshot_hash for call in gateway.calls)
    assert store.get_generation_job(job.job_id).internal_status == "completed"


@pytest.mark.asyncio
async def test_restart_poller_resumes_same_provider_job_without_submit(tmp_path):
    runtime, store, project, snapshot = _snapshot_fixture(tmp_path)
    job, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id, capability="video", provider="m6:test:video", job_type="video",
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="restart", request={"prompt": "shot"}, snapshot=snapshot,
    )
    store.transition_generation_job(job.job_id, "submitting")
    store.record_submission_attempt(job.job_id, state="accepted", provider_job_id="same-video-id")
    store.commit_accepted_submission(job.job_id)

    class RestartGateway(_SnapshotGateway):
        def __init__(self, status):
            super().__init__()
            self.status = status
        def invoke(self, digest, operation, payload):
            self.calls.append((digest, operation, payload))
            if operation == "videoPoll":
                return {"status": self.status, "video_id": payload["video_id"]}
            if operation == "videoFetch":
                return {"media_type": "video/mp4", "bytes": b"restart-video"}
            raise AssertionError(operation)

    first_gateway = RestartGateway("polling")
    first = GenerationPoller(
        store, runtime, FakeGenerationBackend(), rpm=1, poll_interval_seconds=1,
        execution_service=GenerationExecutionService(store, runtime, FakeGenerationBackend(), supplier_gateway=first_gateway, supplier_execution_enabled=True),
    )
    await first.run_cycle()
    assert store.get_generation_job(job.job_id).provider_job_id == "same-video-id"
    second_gateway = RestartGateway("completed")
    restarted = GenerationPoller(
        store, runtime, FakeGenerationBackend(), rpm=1, poll_interval_seconds=1,
        execution_service=GenerationExecutionService(store, runtime, FakeGenerationBackend(), supplier_gateway=second_gateway, supplier_execution_enabled=True),
    )
    await restarted.run_cycle()
    assert store.get_generation_job(job.job_id).internal_status == "completed"
    assert [call[1] for call in first_gateway.calls + second_gateway.calls] == ["videoPoll", "videoPoll", "videoFetch"]


def test_m6_video_enqueue_resolves_current_credential_before_creating_job(tmp_path):
    runtime, store, project, supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "video")
    job, created = coordinator.enqueue_video(
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="m6-video", request={"prompt": "shot"},
    )
    persisted = json.loads(runtime.read_text(job.snapshot_object_id))
    assert created is True
    assert persisted["resolved_credential_version_id"] == store.get_supplier(supplier.supplier_id).current_credential_version_id
    assert store.get_submission_attempt(job.job_id)["state"] == "prepared"


def test_m6_enqueue_missing_credential_fails_before_job(tmp_path):
    runtime, store, project, _snapshot = _snapshot_fixture(tmp_path, "video")
    coordinator = M6GenerationCoordinator(store, runtime, SupplierCredentialStore(store, tmp_path), _SnapshotGateway())
    with pytest.raises(M6GenerationError, match="CREDENTIAL_MISSING"):
        coordinator.enqueue_video(
            project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
            idempotency_key="missing", request={"prompt": "shot"},
        )
    assert store.conn.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 0


def test_m6_image_execution_is_durable_and_links_result_and_asset(tmp_path):
    _runtime, store, project, _supplier, gateway, coordinator = _coordinator_fixture(tmp_path, "image")
    chapter = store.create_chapter(project.project_id, title="Chapter", position=1)
    asset = coordinator.generate_image(
        project_id=project.project_id, chapter_id=chapter.chapter_id, idempotency_key="image-one",
        request={"prompt": "frame", "size": "1024x768", "asset_type": "shot_keyframe", "name": "Frame"},
    )
    job = store.get_generation_job(asset["job_id"])
    assert job.internal_status == "completed"
    assert store.get_submission_attempt(job.job_id)["state"] == "committed"
    assert asset["source_job_id"] == job.job_id
    assert store.get_generation_result(job.provider_result_id).object_id == asset["object_id"]
    assert [call[1] for call in gateway.calls] == ["imageRequest"]


def test_m6_image_accepted_crash_recovers_result_and_asset_without_second_request(tmp_path):
    runtime, store, project, _supplier, gateway, coordinator = _coordinator_fixture(tmp_path, "image")
    chapter = store.create_chapter(project.project_id, title="Chapter", position=1)

    def crash(name):
        if name == "image_accepted_persisted":
            raise SystemExit("crash")

    coordinator._checkpoint = crash
    with pytest.raises(SystemExit, match="crash"):
        coordinator.generate_image(
            project_id=project.project_id, chapter_id=chapter.chapter_id, idempotency_key="image-crash",
            request={"prompt": "frame", "size": "1024x768", "asset_type": "shot_keyframe", "name": "Frame"},
        )
    job = store.list_generation_jobs_for_chapter(chapter.chapter_id)[0]
    assert store.get_submission_attempt(job.job_id)["state"] == "accepted"
    GenerationExecutionService(store, runtime, FakeGenerationBackend()).recover_submission_attempts()
    coordinator._checkpoint = lambda _name: None
    assert coordinator.recover_image_jobs() == 1
    assert store.get_generation_job(job.job_id).internal_status == "completed"
    assert store.conn.execute("SELECT COUNT(*) FROM assets WHERE source_job_id=?", (job.job_id,)).fetchone()[0] == 1
    assert [call[1] for call in gateway.calls] == ["imageRequest"]


def test_m6_text_execution_persists_snapshot_before_invocation_and_sanitizes_evidence(tmp_path):
    runtime, store, project, _supplier, gateway, coordinator = _coordinator_fixture(tmp_path, "text")
    result = coordinator.execute_text(
        project_id=project.project_id,
        operation_key="script_adaptation",
        idempotency_key="text-one",
        request={"prompt": "adapt"},
    )
    row = store.get_supplier_text_run(result["run_id"])
    assert row["status"] == "completed"
    assert row["snapshot_hash"] == gateway.calls[0][0]
    assert row["request_object_id"]
    evidence = runtime.read_text(row["evidence_object_id"])
    assert "selected-secret" not in evidence
    assert "sensitive-marker" not in evidence
    assert result["output"] == "deterministic text"
    assert result["usage"] == {"input_tokens": 2, "output_tokens": 3}


@pytest.mark.parametrize(
    ("request_value", "definition", "config", "expected"),
    [
        (
            {"parameters": {"reasoning_effort": "high"}},
            {"constraints": {"reasoning_effort": "low"}},
            {"reasoning_effort": "medium"},
            "high",
        ),
        (
            {},
            {"constraints": {"reasoning_effort": "low"}},
            {"reasoning_effort": "high"},
            "low",
        ),
        ({}, {}, {"reasoning_effort": "high"}, "high"),
        ({}, {}, {}, "medium"),
    ],
)
def test_reasoning_resolution_precedence(request_value, definition, config, expected):
    assert resolve_reasoning_effort(
        request=request_value,
        model_definition=definition,
        supplier_config=config,
    ) == expected


@pytest.mark.parametrize("value", ["turbo", [], {"nested": "bad"}])
def test_reasoning_resolution_rejects_unexposed_value(value):
    with pytest.raises(ReasoningEffortError, match="INVALID_REASONING_EFFORT"):
        resolve_reasoning_effort(
            request={"parameters": {"reasoning_effort": value}},
            model_definition={},
            supplier_config={},
        )


@pytest.mark.parametrize(
    ("request_value", "expected"),
    [({"prompt": "adapt"}, "low"), ({"prompt": "adapt", "parameters": {"reasoning_effort": "high"}}, "high")],
)
def test_m6_text_execution_freezes_effective_reasoning_in_snapshot(tmp_path, request_value, expected):
    _runtime, store, project, supplier, gateway, coordinator = _coordinator_fixture(
        tmp_path, "text"
    )
    resolved = ModelResolver(store).resolve(project.project_id, "script_adaptation")
    ModelCatalogService(store).revise_model(
        resolved.model.supplier_model_id,
        provider_model_name=resolved.revision.provider_model_name,
        display_name=resolved.revision.display_name,
        capability="text",
        definition={"constraints": {"profile": "fake-text", "reasoning_effort": "low"}},
        expected_catalog_revision=supplier.model_catalog_revision,
        expected_model_revision=resolved.model.revision,
        acknowledged_binding_count=1,
    )

    coordinator.execute_text(
        project_id=project.project_id,
        operation_key="script_adaptation",
        idempotency_key=f"reasoning-{expected}",
        request=request_value,
    )

    snapshot = load_snapshot(store, gateway.calls[0][0])
    assert snapshot.resolved_constraints == {"reasoning_effort": expected}


def test_m6_text_idempotent_replay_does_not_consume_or_require_rate_limit(tmp_path):
    _runtime, _store, project, _supplier, gateway, coordinator = _coordinator_fixture(
        tmp_path, "text"
    )
    coordinator.rate_limiter = SupplierRateLimiter(rpm=1)
    first = coordinator.execute_text(
        project_id=project.project_id,
        operation_key="script_adaptation",
        idempotency_key="rate-replay",
        request={"prompt": "adapt"},
    )

    replay = coordinator.execute_text(
        project_id=project.project_id,
        operation_key="script_adaptation",
        idempotency_key="rate-replay",
        request={"prompt": "adapt"},
    )

    assert replay == first
    assert [call[1] for call in gateway.calls] == ["textRequest"]


def test_m6_image_idempotent_replay_does_not_consume_or_require_rate_limit(tmp_path):
    _runtime, _store, project, _supplier, gateway, coordinator = _coordinator_fixture(
        tmp_path, "image"
    )
    coordinator.rate_limiter = SupplierRateLimiter(rpm=1)
    chapter = _store.create_chapter(project.project_id, title="Chapter", position=1)
    request = {
        "prompt": "frame",
        "size": "1024x768",
        "asset_type": "shot_keyframe",
        "name": "Frame",
    }
    first = coordinator.generate_image(
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        idempotency_key="image-rate-replay",
        request=request,
    )

    replay = coordinator.generate_image(
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        idempotency_key="image-rate-replay",
        request=request,
    )

    assert replay == first
    assert [call[1] for call in gateway.calls] == ["imageRequest"]


def test_image_submission_claim_allows_one_concurrent_gateway_call(tmp_path):
    _runtime, store, project, snapshot = _snapshot_fixture(tmp_path, "image")
    request = {"prompt": "frame"}
    job, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=snapshot.supplier_id,
        capability="image",
        provider=f"m6:{snapshot.supplier_id}:image",
        job_type="image",
        project_id=project.project_id,
        chapter_id="chapter",
        shot_id="shot",
        prompt_revision_id="",
        idempotency_key="concurrent-image",
        request=request,
        snapshot=snapshot,
    )
    barrier = threading.Barrier(2)
    gateway = _SnapshotGateway()
    errors = []

    def claim_and_call():
        try:
            local_runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
            local_store = ProductStore(local_runtime)
            barrier.wait(timeout=5)
            claimed = local_store.claim_generation_submission(job.job_id)
            if claimed is not None:
                gateway.invoke(job.snapshot_hash, "imageRequest", request)
        except Exception as exc:  # pragma: no cover - reported by the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=claim_and_call) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert [call[1] for call in gateway.calls] == ["imageRequest"]
    assert store.get_generation_job(job.job_id).internal_status == "submitting"
    assert store.get_submission_attempt(job.job_id)["state"] == "submitting"


def test_active_legacy_agnes_backfill_is_idempotent_and_preserves_video_id(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Legacy")
    request_object_id = runtime.write_text_object(json.dumps({"prompt": "legacy"}))
    job = store.create_generation_job(
        provider="agnes", job_type="video", project_id=project.project_id,
        chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="legacy", request_hash="hash", request_object_id=request_object_id,
        attempt_number=1,
    )
    store.transition_generation_job(job.job_id, "queued")
    store.transition_generation_job(job.job_id, "submitting")
    store.attach_generation_provider_job(job.job_id, provider_job_id="legacy-video-id", response_object_id="")
    secrets = LocalSecretStore(tmp_path)
    secrets.set_agnes_api_key("legacy-secret")
    backfill = LegacyAgnesBackfill(store, runtime, tmp_path, secrets)

    first = backfill.run()
    second = backfill.run()

    migrated = store.get_generation_job(job.job_id)
    assert (first, second) == (1, 0)
    assert migrated.provider_job_id == "legacy-video-id"
    assert migrated.internal_status == "submitted"
    assert migrated.snapshot_hash
    assert migrated.legacy_backfill_state == "completed"
    assert store.get_submission_attempt(job.job_id) is None


def test_legacy_agnes_adapter_maps_status_fetches_media_and_never_submits(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    artifact = compile_supplier(_legacy_source(), runtime_store=runtime)
    script = r'''
const vm=require("node:vm"); let input="";
process.stdin.on("data", c => input += c).on("end", async () => {
  const context=vm.createContext({});
  new vm.Script("globalThis.module={exports:{}};globalThis.exports=module.exports;").runInContext(context);
  new vm.Script(input).runInContext(context);
  const calls=[];
  const helpers={http:{request:async request => {
    calls.push(request);
    if (calls.length===1) return {data:{status:"processing",video_url:"https://media.invalid/result.mp4"}};
    if (calls.length===2) return {data:{status:"completed",video_url:"https://media.invalid/result.mp4"}};
    return {local_file:"/tmp/fake",sha256:"hash",size:8,media_type:"video/mp4"};
  }}};
  const payload={request:{video_id:"video-123"},config:{video_status_endpoint:"https://api.invalid/status"},credential:"secret"};
  const polled=await context.module.exports.videoPoll(payload,helpers);
  const fetched=await context.module.exports.videoFetch(payload,helpers);
  process.stdout.write(JSON.stringify({polled,fetched,calls}));
});
'''
    completed = subprocess.run(["node", "-e", script], input=artifact.compiled_code, text=True, capture_output=True, check=True)
    result = json.loads(completed.stdout)
    assert result["polled"] == {"video_id": "video-123", "status": "polling"}
    assert result["fetched"]["media_type"] == "video/mp4"
    assert result["calls"][0]["query"] == {"video_id": "video-123"}
    assert len(result["calls"]) == 3


@pytest.mark.asyncio
async def test_backfilled_legacy_job_completes_via_poll_fetch_without_submit(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Legacy E2E")
    request_object_id = runtime.write_text_object(json.dumps({"prompt": "legacy"}))
    job = store.create_generation_job(
        provider="agnes", job_type="video", project_id=project.project_id, chapter_id="chapter",
        shot_id="shot", prompt_revision_id="revision", idempotency_key="legacy-e2e",
        request_hash="hash", request_object_id=request_object_id, attempt_number=1,
    )
    store.transition_generation_job(job.job_id, "queued")
    store.transition_generation_job(job.job_id, "submitting")
    store.attach_generation_provider_job(job.job_id, provider_job_id="legacy-e2e-video", response_object_id="")
    secrets = LocalSecretStore(tmp_path)
    secrets.set_agnes_api_key("legacy-secret")
    assert LegacyAgnesBackfill(store, runtime, tmp_path, secrets).run() == 1
    gateway = _SnapshotGateway()
    poller = GenerationPoller(
        store, runtime, FakeGenerationBackend(), rpm=1, poll_interval_seconds=1,
        execution_service=GenerationExecutionService(store, runtime, FakeGenerationBackend(), supplier_gateway=gateway, supplier_execution_enabled=True),
    )
    await poller.run_cycle()
    completed = store.get_generation_job(job.job_id)
    assert completed.internal_status == "completed"
    assert completed.provider_job_id == "legacy-e2e-video"
    assert [call[1] for call in gateway.calls] == ["videoPoll", "videoFetch"]
    assert runtime.read_bytes_object(store.get_generation_result(completed.provider_result_id).object_id) == b"snapshot-video"


def test_default_rerun_inherits_runtime_model_config_and_uses_current_credential(tmp_path):
    runtime, store, project, supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "video")
    source, _ = coordinator.enqueue_video(
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="source", request={"prompt": "source"},
    )
    old = load_snapshot(store, source.snapshot_hash)
    credentials = coordinator.credentials
    credentials.replace(supplier.supplier_id, "rotated-secret", expected_revision=1)

    rerun, _ = coordinator.rerun_video(
        source_job=source, idempotency_key="rerun", request={"prompt": "rerun"},
        use_current_project_model=False,
    )
    new = load_snapshot(store, rerun.snapshot_hash)
    assert new.supplier_version_id == old.supplier_version_id
    assert new.config_revision_id == old.config_revision_id
    assert new.model_revision_id == old.model_revision_id
    assert new.provider_model_name == old.provider_model_name
    assert new.resolved_credential_version_id != old.resolved_credential_version_id
    assert new.credential_resolution_mode == "current"
    assert new.source_snapshot_hash == source.snapshot_hash
    assert rerun.source_job_id == source.job_id


def test_default_rerun_missing_current_credential_creates_nothing(tmp_path):
    _runtime, store, project, supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "video")
    source, _ = coordinator.enqueue_video(
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="source-missing", request={"prompt": "source"},
    )
    store.conn.execute("UPDATE suppliers SET current_credential_version_id='' WHERE supplier_id=?", (supplier.supplier_id,))
    store.conn.commit()
    before = store.conn.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0]
    with pytest.raises(M6GenerationError, match="CREDENTIAL_MISSING"):
        coordinator.rerun_video(
            source_job=source, idempotency_key="rerun-missing", request={"prompt": "rerun"},
            use_current_project_model=False,
        )
    assert store.conn.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == before


def test_current_model_rerun_resolves_latest_project_binding(tmp_path):
    _runtime, store, project, _supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "video")
    source, _ = coordinator.enqueue_video(
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="source-current", request={"prompt": "source"},
    )
    old = load_snapshot(store, source.snapshot_hash)
    model = store.get_supplier_model(old.supplier_model_id)
    store.revise_supplier_model(
        model.supplier_model_id,
        provider_model_name="new-current-video", display_name="New Current Video",
        capability="video", definition={"constraints": {}},
        expected_catalog_revision=1, expected_model_revision=1,
        acknowledged_binding_count=1,
    )
    rerun, _ = coordinator.rerun_video(
        source_job=source, idempotency_key="rerun-current", request={"prompt": "rerun"},
        use_current_project_model=True,
    )
    new = load_snapshot(store, rerun.snapshot_hash)
    assert new.model_revision_id != old.model_revision_id
    assert new.provider_model_name == "new-current-video"
    assert rerun.rerun_resolution_mode == "current_project_model"


def test_builtin_openai_and_agnes_adapters_install_as_immutable_worker_artifacts(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    installed = install_builtin_adapters(store)
    assert installed == 2
    for slug, capabilities in {"openai": {"text"}, "agnes": {"image", "video"}}.items():
        supplier = next(item for item in store.list_suppliers() if item.slug == slug)
        version = store.get_supplier_version(supplier.current_supplier_version_id)
        assert version.worker_runtime_version.startswith("v")
        assert runtime.read_text(version.compiled_artifact_object_id)
        source = runtime.read_text(version.source_object_id)
        assert "AI 生成适配代码步骤" in source
        assert "不要提供真实 API Key" in source
        assert "helpers.http.request" in source
        if slug == "agnes":
            assert "必须使用 video_id 查询" in source
            assert "不得使用 task_id" in source
        actual = {
            store.get_supplier_model_revision(model.current_model_revision_id).capability
            for model in store.list_supplier_models(supplier.supplier_id) if model.enabled
        }
        assert actual == capabilities
    version_count = runtime.conn.execute(
        "SELECT COUNT(*) FROM supplier_versions"
    ).fetchone()[0]
    assert install_builtin_adapters(store) == 0
    assert runtime.conn.execute(
        "SELECT COUNT(*) FROM supplier_versions"
    ).fetchone()[0] == version_count


def test_builtin_comment_revision_advances_once_without_deleting_history(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    assert install_builtin_adapters(store) == 2
    supplier = next(item for item in store.list_suppliers() if item.slug == "openai")
    documented_version = store.get_supplier_version(supplier.current_supplier_version_id)
    old_source = OPENAI_SOURCE.replace("m6c-2-comments", "m6c-1")
    old = compile_supplier(old_source, runtime_store=runtime)
    legacy_version = store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id=old.source_object_id,
        source_hash=old.source_hash,
        compiled_artifact_object_id=old.compiled_artifact_object_id,
        compiled_artifact_hash=old.compiled_artifact_hash,
        manifest_hash=old.manifest_hash,
        manifest=old.vendor,
        adapter_contract_version=old.adapter_contract_version,
        worker_protocol_version="1",
        worker_runtime_version=old.worker_runtime_version,
        compiler_name=old.compiler_name,
        compiler_version=old.compiler_version,
        compiler_options_hash=old.compiler_options_hash,
        helper_api_version=old.helper_api_version,
        rate_limit_bucket_key=old.vendor["rateLimitBucketKey"],
        expected_revision=supplier.revision,
        built_in=True,
    )

    assert install_builtin_adapters(store) == 1
    advanced = store.get_supplier(
        supplier.supplier_id
    ).current_supplier_version_id
    assert advanced not in {
        documented_version.supplier_version_id,
        legacy_version.supplier_version_id,
    }
    assert store.get_supplier_version(legacy_version.supplier_version_id)
    assert install_builtin_adapters(store) == 0
    assert store.get_supplier(supplier.supplier_id).current_supplier_version_id == advanced


def test_builtin_comment_install_does_not_replace_user_edited_current_version(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    assert install_builtin_adapters(store) == 2
    supplier = next(item for item in store.list_suppliers() if item.slug == "openai")
    user_source = OPENAI_SOURCE.replace("m6c-2-comments", "user-edited-1")
    user = compile_supplier(user_source, runtime_store=runtime)
    user_version = store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id=user.source_object_id,
        source_hash=user.source_hash,
        compiled_artifact_object_id=user.compiled_artifact_object_id,
        compiled_artifact_hash=user.compiled_artifact_hash,
        manifest_hash=user.manifest_hash,
        manifest=user.vendor,
        adapter_contract_version=user.adapter_contract_version,
        worker_protocol_version="1",
        worker_runtime_version=user.worker_runtime_version,
        compiler_name=user.compiler_name,
        compiler_version=user.compiler_version,
        compiler_options_hash=user.compiler_options_hash,
        helper_api_version=user.helper_api_version,
        rate_limit_bucket_key=user.vendor["rateLimitBucketKey"],
        expected_revision=supplier.revision,
        built_in=False,
    )

    assert install_builtin_adapters(store) == 0
    assert store.get_supplier(supplier.supplier_id).current_supplier_version_id == user_version.supplier_version_id


def test_media_result_larger_than_protocol_output_uses_bounded_local_reference(tmp_path):
    _runtime, store, project, _supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "image")
    snapshot_record = persist_snapshot(
        store, coordinator._resolve_snapshot(project.project_id, "storyboard_keyframe_image")
    )
    directory = Path(tempfile.mkdtemp(prefix="ai-drama-worker-media-"))
    local_file = directory / "result.bin"
    data = b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024)
    local_file.write_bytes(data)

    class Worker:
        def invoke(self, artifact, operation, payload, **_kwargs):
            return SupplierInvocationResult(
                value={"local_file": str(local_file), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "media_type": "image/png"},
                worker_protocol_version="1", helper_api_version=artifact.helper_api_version,
                worker_runtime_version=artifact.worker_runtime_version,
            )

    gateway = SnapshotExecutionGateway(store, coordinator.credentials, worker=Worker())
    result = gateway.invoke(snapshot_record.snapshot_hash, "imageRequest", {"prompt": "fake"})
    assert result["bytes"] == data
    assert not local_file.exists()


def test_gateway_rejects_non_image_media_type_for_image_operation(tmp_path):
    _runtime, store, project, _supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "image")
    snapshot_record = persist_snapshot(
        store, coordinator._resolve_snapshot(project.project_id, "storyboard_keyframe_image")
    )
    directory = Path(tempfile.mkdtemp(prefix="ai-drama-worker-media-"))
    local_file = directory / "result.bin"
    data = b"\x89PNG\r\n\x1a\nfixture"
    local_file.write_bytes(data)

    class Worker:
        def invoke(self, artifact, operation, payload, **_kwargs):
            return SupplierInvocationResult(
                value={"local_file": str(local_file), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "media_type": "application/octet-stream"},
                worker_protocol_version="1", helper_api_version=artifact.helper_api_version,
                worker_runtime_version=artifact.worker_runtime_version,
            )

    gateway = SnapshotExecutionGateway(store, coordinator.credentials, worker=Worker())
    with pytest.raises(SupplierExecutionError, match="PROVIDER_RESPONSE_MALFORMED"):
        gateway.invoke(snapshot_record.snapshot_hash, "imageRequest", {"prompt": "fake"})
    assert not local_file.exists()
    assert not directory.exists()


def test_gateway_rejects_malformed_image_magic_and_cleans_worker_file(tmp_path):
    _runtime, store, project, _supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "image")
    snapshot_record = persist_snapshot(
        store, coordinator._resolve_snapshot(project.project_id, "storyboard_keyframe_image")
    )
    directory = Path(tempfile.mkdtemp(prefix="ai-drama-worker-media-"))
    local_file = directory / "result.bin"
    data = b"not-a-png"
    local_file.write_bytes(data)

    class Worker:
        def invoke(self, artifact, operation, payload, **_kwargs):
            return SupplierInvocationResult(
                value={"local_file": str(local_file), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "media_type": "image/png"},
                worker_protocol_version="1", helper_api_version=artifact.helper_api_version,
                worker_runtime_version=artifact.worker_runtime_version,
            )

    gateway = SnapshotExecutionGateway(store, coordinator.credentials, worker=Worker())
    with pytest.raises(SupplierExecutionError, match="PROVIDER_RESPONSE_MALFORMED"):
        gateway.invoke(snapshot_record.snapshot_hash, "imageRequest", {"prompt": "fake"})
    assert not local_file.exists()
    assert not directory.exists()


def test_gateway_rebuilds_worker_limits_from_snapshot_and_rejects_override(tmp_path):
    _runtime, store, project, _supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "text")
    record = persist_snapshot(store, coordinator._resolve_snapshot(project.project_id, "script_adaptation"))

    class Worker:
        received = None
        def invoke(self, artifact, operation, payload, **kwargs):
            self.received = kwargs["limits"]
            return SupplierInvocationResult(
                value={"output": "ok", "usage": {}}, worker_protocol_version="1",
                helper_api_version=artifact.helper_api_version,
                worker_runtime_version=artifact.worker_runtime_version,
            )

    worker = Worker()
    gateway = SnapshotExecutionGateway(store, coordinator.credentials, worker=worker)
    gateway.invoke(record.snapshot_hash, "textRequest", {"prompt": "x"})
    assert worker.received.timeout_seconds == 30
    assert worker.received.max_output_bytes == 4 * 1024 * 1024
    with pytest.raises(SupplierRuntimeUnavailable, match="SUPPLIER_RUNTIME_UNAVAILABLE"):
        gateway.invoke(record.snapshot_hash, "textRequest", {"prompt": "x"}, limits=WorkerLimits(timeout_seconds=1))


def test_m6_snapshot_video_submit_is_exactly_once_across_accepted_restart(tmp_path):
    runtime, store, project, _supplier, _gateway, coordinator = _coordinator_fixture(tmp_path, "video")
    job, _ = coordinator.enqueue_video(
        project_id=project.project_id, chapter_id="chapter", shot_id="shot", prompt_revision_id="revision",
        idempotency_key="m6-submit-once", request={"prompt": "shot", "asset_ids": [], "parameters": {}},
    )

    class SubmitGateway:
        submit_count = 0
        def invoke(self, digest, operation, payload):
            assert digest == job.snapshot_hash
            assert operation == "videoSubmit"
            self.submit_count += 1
            return {"video_id": "m6-video-id", "status": "queued"}

    gateway = SubmitGateway()
    def crash(name):
        if name == "accepted_persisted":
            raise SystemExit("restart")
    service = GenerationExecutionService(
        store, runtime, FakeGenerationBackend(), supplier_gateway=gateway,
        supplier_execution_enabled=True, checkpoint=crash,
    )
    with pytest.raises(SystemExit, match="restart"):
        service.submit_queued_job(job.job_id)
    assert gateway.submit_count == 1
    restarted = GenerationExecutionService(
        store, runtime, FakeGenerationBackend(), supplier_gateway=gateway,
        supplier_execution_enabled=True,
    )
    assert restarted.recover_submission_attempts() == 1
    recovered = store.get_generation_job(job.job_id)
    assert recovered.provider_job_id == "m6-video-id"
    assert store.get_submission_attempt(job.job_id)["state"] == "committed"
    assert gateway.submit_count == 1
