from dataclasses import replace

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.resolution import ModelBindingService, ModelResolver
from ai_drama_web.suppliers.model_catalog import ModelCatalogError, ModelCatalogService
from ai_drama_web.suppliers.snapshots import (
    SnapshotBuilder,
    SupplierRuntimeUnavailable,
    canonical_snapshot_json,
    load_snapshot,
    persist_snapshot,
    snapshot_hash,
)
from tests.web.model_test_support import create_model


def _resolved(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Snapshot")
    supplier = store.list_suppliers()[0]
    model = create_model(store, supplier, capability="text", name="snapshot-text", catalog_revision=0, key="snapshot")
    ModelBindingService(store).replace(
        project.project_id,
        defaults={"text": model.supplier_model_id, "image": "", "video": ""},
        overrides={},
        expected_revision=0,
    )
    return runtime, store, ModelResolver(store).resolve(project.project_id, "script_adaptation")


def test_snapshot_is_canonical_complete_and_content_addressed(tmp_path):
    runtime, store, resolved = _resolved(tmp_path)
    snapshot = SnapshotBuilder(store).build(
        resolved,
        credential_resolution_mode="current",
        resolved_credential_version_id="credential-version",
        resolved_constraints={"temperature": 0.3},
        worker_limits={"timeout_seconds": 30, "max_output_bytes": 4194304},
        created_at="2026-07-13T00:00:00.000000Z",
    )
    raw = canonical_snapshot_json(snapshot)
    assert raw == canonical_snapshot_json(snapshot)
    assert "credential-version" in raw
    assert "plaintext" not in raw
    assert snapshot.supplier_model_id == resolved.model.supplier_model_id
    assert snapshot.model_revision_id == resolved.revision.model_revision_id
    assert snapshot.provider_model_name == "snapshot-text"
    assert snapshot.compiled_artifact_hash
    assert snapshot.worker_protocol_version == "1"
    assert snapshot.config_revision_id
    assert snapshot.model_catalog_revision == 1
    assert snapshot.worker_limits_hash

    record = persist_snapshot(store, snapshot)
    assert record.snapshot_hash == snapshot_hash(snapshot)
    assert runtime.read_text(record.snapshot_object_id) == raw
    assert load_snapshot(store, record.snapshot_hash) == snapshot


def test_material_fingerprint_changes_snapshot_hash(tmp_path):
    _runtime, store, resolved = _resolved(tmp_path)
    original = SnapshotBuilder(store).build(
        resolved,
        credential_resolution_mode="current",
        resolved_credential_version_id="credential-version",
        resolved_constraints={},
        worker_limits={"timeout_seconds": 30},
        created_at="2026-07-13T00:00:00.000000Z",
    )
    for field, value in {
        "compiled_artifact_hash": "changed-compiled",
        "model_revision_id": "changed-model-revision",
        "config_hash": "changed-config",
        "model_catalog_revision": 99,
        "worker_limits_hash": "changed-limits",
    }.items():
        assert snapshot_hash(replace(original, **{field: value})) != snapshot_hash(original)


def test_historical_snapshot_keeps_old_model_revision_and_missing_object_fails_closed(tmp_path):
    runtime, store, resolved = _resolved(tmp_path)
    old = SnapshotBuilder(store).build(
        resolved,
        credential_resolution_mode="current",
        resolved_credential_version_id="",
        resolved_constraints={},
        worker_limits={},
        created_at="2026-07-13T00:00:00.000000Z",
    )
    record = persist_snapshot(store, old)
    store.revise_supplier_model(
        resolved.model.supplier_model_id,
        provider_model_name="renamed-current",
        display_name="Renamed",
        capability="text",
        definition={},
        expected_catalog_revision=1,
        expected_model_revision=1,
    )
    loaded = load_snapshot(store, record.snapshot_hash)
    assert loaded.model_revision_id == old.model_revision_id
    assert loaded.provider_model_name == "snapshot-text"

    runtime.conn.execute(
        "UPDATE execution_snapshots SET snapshot_object_id = 'missing-object' WHERE snapshot_hash = ?",
        (record.snapshot_hash,),
    )
    runtime.conn.commit()
    with pytest.raises(SupplierRuntimeUnavailable, match="SUPPLIER_RUNTIME_UNAVAILABLE"):
        load_snapshot(store, record.snapshot_hash)


def test_snapshotted_model_cannot_be_physically_deleted(tmp_path):
    _runtime, store, resolved = _resolved(tmp_path)
    snapshot = SnapshotBuilder(store).build(
        resolved,
        credential_resolution_mode="current",
        resolved_credential_version_id="",
        resolved_constraints={},
        worker_limits={},
        created_at="2026-07-13T00:00:00.000000Z",
    )
    persist_snapshot(store, snapshot)
    with pytest.raises(ModelCatalogError, match="MODEL_REFERENCED"):
        ModelCatalogService(store).delete_overlay(
            resolved.model.supplier_model_id,
            expected_catalog_revision=1,
            expected_model_revision=1,
        )
