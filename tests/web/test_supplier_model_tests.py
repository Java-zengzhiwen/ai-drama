import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import CredentialInUse, SupplierCredentialStore
from ai_drama_web.suppliers.models import RevisionConflict
from ai_drama_web.suppliers.resolution import ResolvedModel
from ai_drama_web.suppliers.snapshots import SnapshotBuilder
from tests.web.model_test_support import create_model, install_test_supplier_runtime


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
