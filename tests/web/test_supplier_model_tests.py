import hashlib
import json
import pytest
import time
from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import CredentialInUse, SupplierCredentialStore
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.models import RevisionConflict
from ai_drama_web.suppliers.model_tests import ModelTestError, ModelTestExecutor, ModelTestService
from ai_drama_web.suppliers.rate_limits import SupplierRateLimiter
from ai_drama_web.suppliers.resolution import ResolvedModel
from ai_drama_web.suppliers.snapshots import SnapshotBuilder, load_snapshot
from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from tests.web.model_test_support import create_model, install_test_supplier_runtime


class FakeModelTestGateway:
    def __init__(self, response=None, error=None):
        self.response = response or {"output": "connection ok", "usage": {"total_tokens": 2}}
        self.error = error
        self.calls = []

    def invoke(self, snapshot_hash, operation, request):
        self.calls.append((snapshot_hash, operation, request))
        if self.error:
            raise self.error
        return self.response


def _store_and_snapshot(tmp_path, capability="text"):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    supplier = store.create_supplier(slug=f"model-test-{capability}", display_name="Model Test")
    install_test_supplier_runtime(store, supplier)
    supplier = store.get_supplier(supplier.supplier_id)
    model = create_model(
        store,
        supplier,
        capability=capability,
        name=f"test-{capability}",
        catalog_revision=supplier.model_catalog_revision,
        key=f"create-{capability}",
    )
    credential_store = SupplierCredentialStore(store, tmp_path / "runtime-data")
    credential = credential_store.replace(
        supplier.supplier_id, "test-credential", expected_revision=0
    )
    supplier = store.get_supplier(supplier.supplier_id)
    revision = store.get_supplier_model_revision(model.current_model_revision_id)
    resolution = ResolvedModel(
        "",
        "supplier_model_test",
        capability,
        "direct_model_test",
        supplier,
        model,
        revision,
    )
    snapshot = SnapshotBuilder(store).build(
        resolution,
        credential_resolution_mode="current",
        resolved_credential_version_id=credential.credential_version_id,
        resolved_constraints={},
        worker_limits={"timeout_seconds": 30},
    )
    return runtime, store, snapshot, credential_store


def _create_run(store, snapshot, *, key="model-test-key-1", request_hash="request-hash-1"):
    request_object_id = store.runtime.write_text_object('{"prompt":"hello"}')
    return store.create_supplier_model_test_run(
        test_run_id="test-run-1",
        supplier_id=snapshot.supplier_id,
        supplier_model_id=snapshot.supplier_model_id,
        credential_version_id=snapshot.resolved_credential_version_id,
        snapshot=snapshot,
        capability=snapshot.capability,
        idempotency_key=key,
        request_hash=request_hash,
        request_object_id=request_object_id,
    )


def test_model_test_run_round_trip_is_separate_from_generation_tables(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)

    run, created = _create_run(store, snapshot)

    assert created is True
    assert run["status"] == "queued"
    assert run["attempt_count"] == 0
    assert run["credential_version_id"] == snapshot.resolved_credential_version_id
    assert store.get_supplier_model_test_run("test-run-1")["snapshot_hash"] == run["snapshot_hash"]
    assert store.conn.execute("SELECT count(*) FROM generation_jobs").fetchone()[0] == 0
    assert store.conn.execute("SELECT count(*) FROM assets").fetchone()[0] == 0
    runtime.close()


def test_model_test_idempotency_replays_same_hash_and_rejects_changed_hash(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    first, created = _create_run(store, snapshot)

    replay, replay_created = _create_run(store, snapshot)

    assert created is True
    assert replay_created is False
    assert replay["test_run_id"] == first["test_run_id"]
    with pytest.raises(RevisionConflict, match="IDEMPOTENCY_CONFLICT"):
        _create_run(store, snapshot, request_hash="different-hash")
    runtime.close()


def test_model_test_claim_is_atomic_and_submit_once(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    _create_run(store, snapshot)

    claimed = store.claim_supplier_model_test_run(
        "test-run-1", lease_owner="worker-1", lease_expires_at="2099-01-01T00:00:00Z"
    )
    losing_claim = store.claim_supplier_model_test_run(
        "test-run-1", lease_owner="worker-2", lease_expires_at="2099-01-01T00:00:00Z"
    )

    assert claimed["status"] == "submitting"
    assert claimed["attempt_count"] == 1
    assert claimed["lease_owner"] == "worker-1"
    assert losing_claim is None
    runtime.close()


def test_model_test_completion_and_failure_are_terminal(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    _create_run(store, snapshot)
    store.claim_supplier_model_test_run(
        "test-run-1", lease_owner="worker-1", lease_expires_at="2099-01-01T00:00:00Z"
    )
    result_id = runtime.write_text_object('{"output":"ok"}')
    evidence_id = runtime.write_text_object('{"status":"ok"}')

    completed = store.complete_supplier_model_test_run(
        "test-run-1",
        normalized_result_object_id=result_id,
        sanitized_evidence_object_id=evidence_id,
    )

    assert completed["status"] == "completed"
    assert completed["finished_at"]
    with pytest.raises(RevisionConflict, match="MODEL_TEST_NOT_SUBMITTING"):
        store.fail_supplier_model_test_run(
            "test-run-1", error_code="FAILED", error_message="must not overwrite"
        )
    runtime.close()


def test_interrupted_submitting_runs_become_unknown_without_new_attempt(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    _create_run(store, snapshot)
    store.claim_supplier_model_test_run(
        "test-run-1", lease_owner="worker-1", lease_expires_at="2000-01-01T00:00:00Z"
    )

    changed = store.mark_interrupted_model_tests_unknown()
    run = store.get_supplier_model_test_run("test-run-1")

    assert changed == 1
    assert run["status"] == "submission_outcome_unknown"
    assert run["attempt_count"] == 1
    assert run["error_code"] == "SUBMISSION_OUTCOME_UNKNOWN"
    runtime.close()


def test_credential_delete_treats_queued_model_test_as_active_reference(tmp_path):
    runtime, store, snapshot, credentials = _store_and_snapshot(tmp_path)
    _create_run(store, snapshot)

    with pytest.raises(CredentialInUse) as error:
        credentials.delete(snapshot.supplier_id, expected_revision=1)

    assert error.value.active_job_count == 1
    assert store.get_supplier_model_test_run("test-run-1")["status"] == "queued"
    runtime.close()


def test_force_delete_fails_queued_model_test_before_submission(tmp_path):
    runtime, store, snapshot, credentials = _store_and_snapshot(tmp_path)
    _create_run(store, snapshot)

    credentials.delete(snapshot.supplier_id, expected_revision=1, force=True)
    run = store.get_supplier_model_test_run("test-run-1")

    assert run["status"] == "failed"
    assert run["attempt_count"] == 0
    assert run["error_code"] == "CREDENTIAL_REVOKED"
    runtime.close()


def test_force_delete_marks_submitting_model_test_unknown(tmp_path):
    runtime, store, snapshot, credentials = _store_and_snapshot(tmp_path)
    _create_run(store, snapshot)
    store.claim_supplier_model_test_run(
        "test-run-1", lease_owner="worker-1", lease_expires_at="2099-01-01T00:00:00Z"
    )

    credentials.delete(snapshot.supplier_id, expected_revision=1, force=True)
    run = store.get_supplier_model_test_run("test-run-1")

    assert run["status"] == "submission_outcome_unknown"
    assert run["attempt_count"] == 1
    assert run["error_code"] == "SUBMISSION_OUTCOME_UNKNOWN"
    runtime.close()


def test_service_creates_text_run_from_direct_model_snapshot(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    service = ModelTestService(store)

    run, created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="service-key",
        expected_model_revision=1,
    )

    assert created is True
    assert run["status"] == "queued"
    assert run["capability"] == "text"
    persisted_snapshot = runtime.read_text(run["snapshot_object_id"])
    assert '"operation_key":"supplier_model_test"' in persisted_snapshot
    assert '"binding_source":"direct_model_test"' in persisted_snapshot
    assert '"rate_limit_bucket_key":"test-bucket"' in persisted_snapshot
    request = runtime.read_text(run["request_object_id"])
    assert request == '{"prompt":"hello","test_contract_version":"model-test-v1"}'
    assert service.safe_read(run["test_run_id"])["reasoning_effort"] == "medium"
    runtime.close()


def test_text_model_test_override_wins_and_is_frozen_for_audit(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    service = ModelTestService(store)

    run, created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        reasoning_effort="high",
        idempotency_key="reasoning-override",
        expected_model_revision=1,
    )

    assert created is True
    persisted = load_snapshot(store, run["snapshot_hash"])
    assert persisted.resolved_constraints["reasoning_effort"] == "high"
    assert runtime.read_text(run["request_object_id"]) == (
        '{"parameters":{"reasoning_effort":"high"},"prompt":"hello",'
        '"test_contract_version":"model-test-v1"}'
    )
    assert service.safe_read(run["test_run_id"])["reasoning_effort"] == "high"
    runtime.close()


def test_text_model_test_uses_supplier_default_before_model_default(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    supplier = store.get_supplier(snapshot.supplier_id)
    model = store.get_supplier_model(snapshot.supplier_model_id)
    revision = store.get_supplier_model_revision(model.current_model_revision_id)
    ModelCatalogService(store).revise_model(
        model.supplier_model_id,
        provider_model_name=revision.provider_model_name,
        display_name=revision.display_name,
        capability="text",
        definition={"constraints": {"profile": "test-text", "reasoning_effort": "low"}},
        expected_catalog_revision=supplier.model_catalog_revision,
        expected_model_revision=model.revision,
        acknowledged_binding_count=0,
    )
    current = store.get_supplier_model(model.supplier_model_id)
    config_raw = json.dumps({"reasoning_effort": "medium"}, separators=(",", ":"))
    config_object_id = runtime.write_text_object(config_raw)
    store.replace_supplier_config(
        supplier.supplier_id,
        config_object_id=config_object_id,
        config_hash=hashlib.sha256(config_raw.encode()).hexdigest(),
        expected_revision=supplier.config_revision,
    )

    run, _created = ModelTestService(store).create_model_test(
        supplier_model_id=model.supplier_model_id,
        prompt="hello",
        idempotency_key="reasoning-model-default",
        expected_model_revision=current.revision,
    )

    persisted = load_snapshot(store, run["snapshot_hash"])
    assert persisted.resolved_constraints["reasoning_effort"] == "medium"
    runtime.close()


def test_image_model_test_rejects_reasoning_before_writing_run(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(
        tmp_path, capability="image"
    )

    with pytest.raises(ModelTestError, match="MODEL_TEST_REASONING_UNSUPPORTED"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="a cup",
            reasoning_effort="high",
            idempotency_key="image-reasoning",
            expected_model_revision=1,
        )

    assert store.conn.execute(
        "SELECT count(*) FROM supplier_model_test_runs"
    ).fetchone()[0] == 0
    runtime.close()


def test_text_model_test_rejects_invalid_reasoning_before_writing_run(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)

    with pytest.raises(ModelTestError, match="INVALID_REASONING_EFFORT"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            reasoning_effort="turbo",
            idempotency_key="invalid-reasoning",
            expected_model_revision=1,
        )

    assert store.conn.execute(
        "SELECT count(*) FROM supplier_model_test_runs"
    ).fetchone()[0] == 0
    runtime.close()


def test_service_replays_same_key_and_input_but_conflicts_on_changed_prompt(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    service = ModelTestService(store)
    first, created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="service-replay",
        expected_model_revision=1,
    )

    replay, replay_created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="service-replay",
        expected_model_revision=1,
    )

    assert created is True
    assert replay_created is False
    assert replay["test_run_id"] == first["test_run_id"]
    with pytest.raises(RevisionConflict, match="IDEMPOTENCY_CONFLICT"):
        service.create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="changed",
            idempotency_key="service-replay",
            expected_model_revision=1,
        )
    runtime.close()


def test_service_replay_conflicts_when_reasoning_override_changes(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    service = ModelTestService(store)
    service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        reasoning_effort="low",
        idempotency_key="reasoning-conflict",
        expected_model_revision=1,
    )

    with pytest.raises(RevisionConflict, match="IDEMPOTENCY_CONFLICT"):
        service.create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            reasoning_effort="high",
            idempotency_key="reasoning-conflict",
            expected_model_revision=1,
        )
    runtime.close()


def test_image_service_uses_provider_neutral_default_size(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path, capability="image")

    run, _created = ModelTestService(store).create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="a cup",
        idempotency_key="image-size",
        expected_model_revision=1,
    )

    assert runtime.read_text(run["request_object_id"]) == (
        '{"prompt":"a cup","quality":"auto","size":"1024x768",'
        '"test_contract_version":"model-test-v1"}'
    )
    assert ModelTestService(store).safe_read(run["test_run_id"])["size"] == "1024x768"
    assert ModelTestService(store).safe_read(run["test_run_id"])["quality"] == "auto"
    runtime.close()


def test_image_model_test_override_is_frozen_and_auditable(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(
        tmp_path, capability="image"
    )
    supplier = store.get_supplier(snapshot.supplier_id)
    model = store.get_supplier_model(snapshot.supplier_model_id)
    revision = store.get_supplier_model_revision(model.current_model_revision_id)
    ModelCatalogService(store).revise_model(
        model.supplier_model_id,
        provider_model_name=revision.provider_model_name,
        display_name=revision.display_name,
        capability="image",
        definition={
            "default_size": "1024x1024",
            "constraints": {
                "supported_sizes": ["auto", "1024x1024", "1024x1536", "1536x1024"],
                "default_quality": "auto",
                "supported_qualities": ["auto", "low", "medium", "high"],
            },
        },
        expected_catalog_revision=supplier.model_catalog_revision,
        expected_model_revision=model.revision,
        acknowledged_binding_count=0,
    )
    current = store.get_supplier_model(model.supplier_model_id)

    run, created = ModelTestService(store).create_model_test(
        supplier_model_id=model.supplier_model_id,
        prompt="a cup",
        size="1024x1536",
        quality="high",
        idempotency_key="image-options",
        expected_model_revision=current.revision,
    )

    assert created is True
    persisted = load_snapshot(store, run["snapshot_hash"])
    assert persisted.resolved_constraints == {"size": "1024x1536", "quality": "high"}
    safe = ModelTestService(store).safe_read(run["test_run_id"])
    assert safe["size"] == "1024x1536"
    assert safe["quality"] == "high"
    assert runtime.read_text(run["request_object_id"]) == (
        '{"prompt":"a cup","quality":"high","size":"1024x1536",'
        '"test_contract_version":"model-test-v1"}'
    )
    runtime.close()


def test_text_model_test_rejects_image_options_before_writing_run(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)

    with pytest.raises(ModelTestError, match="MODEL_TEST_IMAGE_OPTIONS_UNSUPPORTED"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            size="1024x1024",
            idempotency_key="text-image-options",
            expected_model_revision=1,
        )

    assert store.conn.execute(
        "SELECT count(*) FROM supplier_model_test_runs"
    ).fetchone()[0] == 0
    runtime.close()


def test_service_rejects_missing_capability_export_before_run(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    supplier = store.get_supplier(snapshot.supplier_id)
    source = """
export const vendor = {
  id: "missing-export", version: "1", name: "Missing", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1", helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "test-bucket", inputs: [], inputValues: {}, models: []
};
"""
    artifact = compile_supplier(source, runtime_store=runtime)
    store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id=artifact.source_object_id,
        source_hash=artifact.source_hash,
        compiled_artifact_object_id=artifact.compiled_artifact_object_id,
        compiled_artifact_hash=artifact.compiled_artifact_hash,
        manifest_hash=artifact.manifest_hash,
        manifest=artifact.vendor,
        adapter_contract_version=artifact.adapter_contract_version,
        worker_protocol_version="1",
        worker_runtime_version=artifact.worker_runtime_version,
        compiler_name=artifact.compiler_name,
        compiler_version=artifact.compiler_version,
        compiler_options_hash=artifact.compiler_options_hash,
        helper_api_version=artifact.helper_api_version,
        rate_limit_bucket_key=artifact.vendor["rateLimitBucketKey"],
        expected_revision=supplier.revision,
    )

    with pytest.raises(ModelTestError, match="SUPPLIER_OPERATION_UNAVAILABLE"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            idempotency_key="missing-export",
            expected_model_revision=1,
        )

    assert store.conn.execute("SELECT count(*) FROM supplier_model_test_runs").fetchone()[0] == 0
    runtime.close()


@pytest.mark.parametrize("prompt", ["", "x" * 4001])
def test_service_rejects_invalid_text_prompt_before_run(tmp_path, prompt):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)

    with pytest.raises(ModelTestError, match="MODEL_TEST_PROMPT_INVALID"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt=prompt,
            idempotency_key="invalid-prompt",
            expected_model_revision=1,
        )

    assert store.conn.execute("SELECT count(*) FROM supplier_model_test_runs").fetchone()[0] == 0
    runtime.close()


def test_service_rejects_video_model_before_run(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path, capability="video")

    with pytest.raises(ModelTestError, match="MODEL_TEST_CAPABILITY_UNSUPPORTED"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            idempotency_key="video-test",
            expected_model_revision=1,
        )

    assert store.conn.execute("SELECT count(*) FROM supplier_model_test_runs").fetchone()[0] == 0
    runtime.close()


def test_service_rejects_disabled_supplier_and_model_before_run(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    supplier = store.get_supplier(snapshot.supplier_id)
    store.update_supplier(snapshot.supplier_id, enabled=False, expected_revision=supplier.revision)

    with pytest.raises(ModelTestError, match="SUPPLIER_DISABLED"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            idempotency_key="disabled-supplier",
            expected_model_revision=1,
        )

    store.update_supplier(
        snapshot.supplier_id,
        enabled=True,
        expected_revision=store.get_supplier(snapshot.supplier_id).revision,
    )
    current = store.get_supplier(snapshot.supplier_id)
    store.set_supplier_model_enabled(
        snapshot.supplier_model_id,
        enabled=False,
        expected_catalog_revision=current.model_catalog_revision,
        expected_model_revision=1,
    )
    with pytest.raises(ModelTestError, match="MODEL_DISABLED"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            idempotency_key="disabled-model",
            expected_model_revision=2,
        )
    runtime.close()


def test_service_requires_current_ready_credential_before_run(tmp_path):
    runtime, store, snapshot, credentials = _store_and_snapshot(tmp_path)
    credentials.delete(snapshot.supplier_id, expected_revision=1)

    with pytest.raises(ModelTestError, match="CREDENTIAL_MISSING"):
        ModelTestService(store).create_model_test(
            supplier_model_id=snapshot.supplier_model_id,
            prompt="hello",
            idempotency_key="missing-credential",
            expected_model_revision=1,
        )

    assert store.conn.execute("SELECT count(*) FROM supplier_model_test_runs").fetchone()[0] == 0
    runtime.close()


def test_executor_claims_and_invokes_text_once(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    service = ModelTestService(store)
    run, _created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="execute-text",
        expected_model_revision=1,
    )
    gateway = FakeModelTestGateway()
    executor = ModelTestExecutor(store, gateway)

    executor.execute(run["test_run_id"])
    executor.execute(run["test_run_id"])
    result = service.safe_read(run["test_run_id"])

    assert [call[1] for call in gateway.calls] == ["textRequest"]
    assert result["status"] == "completed"
    assert result["output"] == "connection ok"
    assert result["usage"] == {"total_tokens": 2}
    runtime.close()


def test_executor_persists_image_bytes_and_sanitizes_provider_url(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path, capability="image")
    service = ModelTestService(store)
    run, _created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="a cup",
        idempotency_key="execute-image",
        expected_model_revision=1,
    )
    gateway = FakeModelTestGateway(
        response={
            "media_type": "image/png",
            "bytes": b"\x89PNG\r\n\x1a\nimage",
            "url": "https://fake.invalid/result.png?token=secret-value",
        }
    )

    ModelTestExecutor(store, gateway).execute(run["test_run_id"])
    result = service.safe_read(run["test_run_id"])
    stored = store.get_supplier_model_test_run(run["test_run_id"])

    assert result["status"] == "completed"
    assert result["media_type"] == "image/png"
    assert result["byte_size"] == 13
    assert runtime.read_bytes_object(stored["content_object_id"]).startswith(b"\x89PNG")
    evidence = runtime.read_text(stored["sanitized_evidence_object_id"])
    assert "token=" not in evidence
    assert "secret-value" not in evidence
    assert '"bytes"' not in evidence
    runtime.close()


def test_executor_rejects_image_media_type_when_magic_bytes_do_not_match(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path, capability="image")
    service = ModelTestService(store)
    run, _created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="a cup",
        idempotency_key="invalid-image-magic",
        expected_model_revision=1,
    )
    gateway = FakeModelTestGateway(
        response={"media_type": "image/png", "bytes": b"not-a-png"}
    )

    ModelTestExecutor(store, gateway).execute(run["test_run_id"])
    result = service.safe_read(run["test_run_id"])

    assert result["status"] == "failed"
    assert result["error_code"] == "PROVIDER_RESPONSE_MALFORMED"
    runtime.close()


def test_executor_marks_ambiguous_gateway_failure_unknown_without_retry(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    service = ModelTestService(store)
    run, _created = service.create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="execute-failure",
        expected_model_revision=1,
    )
    gateway = FakeModelTestGateway(error=RuntimeError("SUPPLIER_WORKER_TIMEOUT"))
    executor = ModelTestExecutor(store, gateway)

    executor.execute(run["test_run_id"])
    executor.execute(run["test_run_id"])
    result = service.safe_read(run["test_run_id"])

    assert len(gateway.calls) == 1
    assert result["status"] == "submission_outcome_unknown"
    assert result["error_code"] == "SUBMISSION_OUTCOME_UNKNOWN"
    runtime.close()


def test_model_test_uses_shared_snapshot_bucket_limiter(tmp_path):
    runtime, store, snapshot, _credentials = _store_and_snapshot(tmp_path)
    run, _created = ModelTestService(store).create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="shared-limit",
        expected_model_revision=1,
    )
    now = [100.0]
    limiter = SupplierRateLimiter(rpm=1, clock=lambda: now[0])
    assert limiter.acquire(snapshot.rate_limit_bucket_key) is True
    gateway = FakeModelTestGateway()
    executor = ModelTestExecutor(store, gateway, rate_limiter=limiter)

    assert executor.execute(run["test_run_id"])["status"] == "queued"
    assert gateway.calls == []
    now[0] += 60.1
    assert executor.execute(run["test_run_id"])["status"] == "completed"
    assert len(gateway.calls) == 1
    runtime.close()


def test_force_delete_during_worker_return_is_idempotent_and_does_not_raise(tmp_path):
    runtime, store, snapshot, credentials = _store_and_snapshot(tmp_path)
    run, _created = ModelTestService(store).create_model_test(
        supplier_model_id=snapshot.supplier_model_id,
        prompt="hello",
        idempotency_key="delete-during-return",
        expected_model_revision=1,
    )

    class DeletingGateway(FakeModelTestGateway):
        def invoke(self, snapshot_hash, operation, request):
            value = super().invoke(snapshot_hash, operation, request)
            credentials.delete(snapshot.supplier_id, expected_revision=1, force=True)
            return value

    result = ModelTestExecutor(store, DeletingGateway()).execute(run["test_run_id"])

    assert result["status"] == "submission_outcome_unknown"
    assert result["error_code"] == "SUBMISSION_OUTCOME_UNKNOWN"
    runtime.close()


def test_drain_queued_isolates_one_run_failure_and_continues(monkeypatch):
    class Store:
        def list_queued_supplier_model_tests(self, limit=20):
            return [
                {"test_run_id": "broken", "snapshot_hash": "snapshot-broken"},
                {"test_run_id": "healthy", "snapshot_hash": "snapshot-healthy"},
            ]

    class Executor(ModelTestExecutor):
        def __init__(self):
            super().__init__(Store(), FakeModelTestGateway())
            self.calls = []

        def execute(self, test_run_id):
            self.calls.append(test_run_id)
            if test_run_id == "broken":
                raise RuntimeError("unexpected per-run failure")
            return {"status": "completed"}

    monkeypatch.setattr(
        "ai_drama_web.suppliers.model_tests.load_snapshot",
        lambda _store, digest: type("Snapshot", (), {"rate_limit_bucket_key": digest})(),
    )
    executor = Executor()

    assert executor.drain_queued() == 1
    assert executor.calls == ["broken", "healthy"]


def _install_api_model(app, tmp_path, capability):
    store = app.state.product_store
    supplier = store.create_supplier(
        slug=f"api-model-test-{capability}", display_name="API Model Test"
    )
    install_test_supplier_runtime(store, supplier)
    supplier = store.get_supplier(supplier.supplier_id)
    model = create_model(
        store,
        supplier,
        capability=capability,
        name=f"api-{capability}",
        catalog_revision=supplier.model_catalog_revision,
        key=f"api-create-{capability}",
    )
    app.state.supplier_credential_store.replace(
        supplier.supplier_id, "api-test-credential", expected_revision=0
    )
    return model


def _wait_for_terminal(client, test_run_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/model-tests/{test_run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] not in {"queued", "submitting"}:
            return payload
        time.sleep(0.05)
    raise AssertionError("model test did not reach a terminal state")


def test_model_test_feature_status_is_default_off_and_create_is_blocked(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DRAMA_MODEL_TESTS_ENABLED", raising=False)
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        status = client.get("/api/model-tests/status")
        blocked = client.post(
            "/api/models/not-used/tests",
            headers={"Idempotency-Key": "blocked", "If-Match": '"model-not-used-1"'},
            json={"prompt": "hello"},
        )

    assert status.status_code == 200
    assert status.json() == {"enabled": False}
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error_code"] == "MODEL_TESTS_DISABLED"


def test_app_shares_one_rate_limiter_between_generation_and_model_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_MODEL_TESTS_ENABLED", "true")
    monkeypatch.setenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", "true")
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app, client=("127.0.0.1", 50000)):
        assert app.state.generation_poller.rate_limiter is app.state.supplier_rate_limiter
        assert app.state.model_test_runner.rate_limiter is app.state.supplier_rate_limiter
        assert app.state.m6_generation_coordinator.rate_limiter is app.state.supplier_rate_limiter


def test_text_model_test_api_queues_recovers_and_completes_locally(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_MODEL_TESTS_ENABLED", "true")
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        model = client.portal.call(lambda: _install_api_model(app, tmp_path, "text"))
        response = client.post(
            f"/api/models/{model.supplier_model_id}/tests",
            headers={
                "Idempotency-Key": "api-text-key",
                "If-Match": f'"model-{model.supplier_model_id}-1"',
            },
            json={"prompt": "hello"},
        )
        assert response.status_code == 202
        created = response.json()
        assert "prompt" not in created
        recovered = client.get(
            f"/api/models/{model.supplier_model_id}/tests/by-idempotency-key",
            headers={"Idempotency-Key": "api-text-key"},
        )
        assert recovered.status_code == 200
        assert recovered.json()["test_run_id"] == created["test_run_id"]
        terminal = _wait_for_terminal(client, created["test_run_id"])

    assert terminal["status"] == "completed"
    assert terminal["output"] == "hello"
    assert terminal["usage"] == {"total_tokens": 1}
    assert terminal["reasoning_effort"] == "medium"
    assert "credential" not in terminal


@pytest.mark.parametrize(
    ("capability", "reasoning_effort", "expected_code"),
    [
        ("text", "turbo", "INVALID_REASONING_EFFORT"),
        ("image", "high", "MODEL_TEST_REASONING_UNSUPPORTED"),
    ],
)
def test_model_test_api_rejects_unsupported_reasoning_locally(
    tmp_path, monkeypatch, capability, reasoning_effort, expected_code
):
    monkeypatch.setenv("AI_DRAMA_MODEL_TESTS_ENABLED", "true")
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        model = client.portal.call(lambda: _install_api_model(app, tmp_path, capability))
        response = client.post(
            f"/api/models/{model.supplier_model_id}/tests",
            headers={
                "Idempotency-Key": f"api-reasoning-{capability}",
                "If-Match": f'"model-{model.supplier_model_id}-1"',
            },
            json={"prompt": "hello", "reasoning_effort": reasoning_effort},
        )
        run_count = client.portal.call(
            lambda: app.state.product_store.conn.execute(
                "SELECT count(*) FROM supplier_model_test_runs"
            ).fetchone()[0]
        )

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == expected_code
    assert run_count == 0


def test_image_model_test_content_is_local_and_private(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_MODEL_TESTS_ENABLED", "true")
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        model = client.portal.call(lambda: _install_api_model(app, tmp_path, "image"))
        response = client.post(
            f"/api/models/{model.supplier_model_id}/tests",
            headers={
                "Idempotency-Key": "api-image-key",
                "If-Match": f'"model-{model.supplier_model_id}-1"',
            },
            json={"prompt": "a cup", "size": "1024x1536", "quality": "high"},
        )
        terminal = _wait_for_terminal(client, response.json()["test_run_id"])
        content = client.get(
            f"/api/model-tests/{response.json()['test_run_id']}/content"
        )

    assert terminal["status"] == "completed"
    assert terminal["media_type"] == "image/png"
    assert terminal["size"] == "1024x1536"
    assert terminal["quality"] == "high"
    assert content.status_code == 200
    assert content.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert content.headers["content-type"] == "image/png"
    assert content.headers["cache-control"] == "private, no-store"
    assert content.headers["x-content-type-options"] == "nosniff"
