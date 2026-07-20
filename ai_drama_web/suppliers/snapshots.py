from dataclasses import asdict, dataclass
import hashlib
import json

from ai_drama_runtime.store import now_iso

from .models import ExecutionSnapshotRecord
from .worker import (
    SUPPORTED_RUNTIME_PAIRS,
    WorkerLimits,
    current_worker_runtime_version,
)


class SupplierRuntimeUnavailable(RuntimeError):
    def __init__(self, code="SUPPLIER_RUNTIME_UNAVAILABLE"):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ExecutionSnapshot:
    snapshot_schema_version: str
    supplier_id: str
    supplier_version_id: str
    supplier_source_hash: str
    manifest_hash: str
    compiled_artifact_object_id: str
    compiled_artifact_hash: str
    adapter_contract_version: str
    worker_protocol_version: str
    worker_runtime_version: str
    compiler_name: str
    compiler_version: str
    compiler_options_hash: str
    helper_api_version: str
    rate_limit_bucket_key: str
    supplier_model_id: str
    model_revision_id: str
    provider_model_name: str
    capability: str
    operation_key: str
    binding_source: str
    config_revision_id: str
    config_hash: str
    model_catalog_revision: int
    credential_resolution_mode: str
    resolved_credential_version_id: str
    resolved_constraints: dict
    worker_limits: dict
    worker_limits_hash: str
    source_snapshot_hash: str
    source_supplier_version_id: str
    source_config_revision_id: str
    source_model_revision_id: str
    created_at: str


class SnapshotBuilder:
    def __init__(self, store):
        self.store = store

    def build(
        self,
        resolution,
        *,
        credential_resolution_mode,
        resolved_credential_version_id,
        resolved_constraints,
        worker_limits,
        created_at=None,
        source_snapshot_hash="",
        source_supplier_version_id="",
        source_config_revision_id="",
        source_model_revision_id="",
    ):
        supplier = resolution.supplier
        version = self.store.get_supplier_version(supplier.current_supplier_version_id)
        config = self.store.get_config_revision(supplier.current_config_revision_id)
        if version is None or config is None:
            self._unavailable()
        for object_id in (
            version.source_object_id,
            version.compiled_artifact_object_id,
            resolution.revision.definition_object_id,
        ):
            self._require_object(object_id)
        if config.config_object_id:
            self._require_object(config.config_object_id)
        normalized_limits = asdict(WorkerLimits())
        normalized_limits.update(worker_limits)
        limits_hash = hashlib.sha256(_canonical(normalized_limits).encode("utf-8")).hexdigest()
        return ExecutionSnapshot(
            snapshot_schema_version="execution-snapshot-v1",
            supplier_id=supplier.supplier_id,
            supplier_version_id=version.supplier_version_id,
            supplier_source_hash=version.source_hash,
            manifest_hash=version.manifest_hash,
            compiled_artifact_object_id=version.compiled_artifact_object_id,
            compiled_artifact_hash=version.compiled_artifact_hash,
            adapter_contract_version=version.adapter_contract_version,
            worker_protocol_version=version.worker_protocol_version,
            worker_runtime_version=version.worker_runtime_version,
            compiler_name=version.compiler_name,
            compiler_version=version.compiler_version,
            compiler_options_hash=version.compiler_options_hash,
            helper_api_version=version.helper_api_version,
            rate_limit_bucket_key=version.rate_limit_bucket_key or supplier.supplier_id,
            supplier_model_id=resolution.model.supplier_model_id,
            model_revision_id=resolution.revision.model_revision_id,
            provider_model_name=resolution.revision.provider_model_name,
            capability=resolution.capability,
            operation_key=resolution.operation_key,
            binding_source=resolution.binding_source,
            config_revision_id=config.config_revision_id,
            config_hash=config.config_hash,
            model_catalog_revision=supplier.model_catalog_revision,
            credential_resolution_mode=credential_resolution_mode,
            resolved_credential_version_id=resolved_credential_version_id,
            resolved_constraints=dict(resolved_constraints),
            worker_limits=normalized_limits,
            worker_limits_hash=limits_hash,
            source_snapshot_hash=source_snapshot_hash,
            source_supplier_version_id=source_supplier_version_id,
            source_config_revision_id=source_config_revision_id,
            source_model_revision_id=source_model_revision_id,
            created_at=created_at or now_iso(),
        )

    def _require_object(self, object_id):
        try:
            self.store.runtime.read_text(object_id)
        except Exception:
            self._unavailable()

    def _unavailable(self):
        raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE")


def _canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_snapshot_json(snapshot):
    return _canonical(asdict(snapshot))


def snapshot_hash(snapshot):
    return hashlib.sha256(canonical_snapshot_json(snapshot).encode("utf-8")).hexdigest()


def persist_snapshot(store, snapshot):
    _validate_snapshot(store, snapshot)
    raw = canonical_snapshot_json(snapshot)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    object_id = store.runtime.write_text_object(raw)
    store.conn.execute(
        """
        INSERT OR IGNORE INTO execution_snapshots
        (snapshot_hash, snapshot_object_id, supplier_id, supplier_model_id,
         model_revision_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            digest,
            object_id,
            snapshot.supplier_id,
            snapshot.supplier_model_id,
            snapshot.model_revision_id,
            snapshot.created_at,
        ),
    )
    store.conn.commit()
    row = store.conn.execute(
        "SELECT * FROM execution_snapshots WHERE snapshot_hash = ?", (digest,)
    ).fetchone()
    if row is None or row["snapshot_object_id"] != object_id:
        raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE")
    return ExecutionSnapshotRecord(**dict(row))


def load_snapshot(store, digest):
    row = store.conn.execute(
        "SELECT * FROM execution_snapshots WHERE snapshot_hash = ?", (digest,)
    ).fetchone()
    if row is None:
        raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE")
    try:
        raw = store.runtime.read_text(row["snapshot_object_id"])
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != digest:
            raise ValueError("snapshot hash mismatch")
        payload = json.loads(raw)
        snapshot = ExecutionSnapshot(**payload)
        if (
            row["supplier_id"] != snapshot.supplier_id
            or row["supplier_model_id"] != snapshot.supplier_model_id
            or row["model_revision_id"] != snapshot.model_revision_id
        ):
            raise ValueError("snapshot index mismatch")
        _validate_snapshot(store, snapshot)
        return snapshot
    except Exception as exc:
        raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE") from exc


def _validate_snapshot(store, snapshot):
    try:
        supplier = store.get_supplier(snapshot.supplier_id)
        version = store.get_supplier_version(snapshot.supplier_version_id)
        model = store.get_supplier_model(snapshot.supplier_model_id)
        revision = store.get_supplier_model_revision(snapshot.model_revision_id)
        config = store.get_config_revision(snapshot.config_revision_id)
        if supplier is None or version is None or model is None or revision is None or config is None:
            raise ValueError("snapshot reference missing")
        if version.supplier_id != supplier.supplier_id or model.supplier_id != supplier.supplier_id:
            raise ValueError("snapshot supplier mismatch")
        if revision.supplier_model_id != model.supplier_model_id:
            raise ValueError("snapshot model mismatch")
        expected = {
            "supplier_source_hash": version.source_hash,
            "manifest_hash": version.manifest_hash,
            "compiled_artifact_object_id": version.compiled_artifact_object_id,
            "compiled_artifact_hash": version.compiled_artifact_hash,
            "adapter_contract_version": version.adapter_contract_version,
            "worker_protocol_version": version.worker_protocol_version,
            "worker_runtime_version": version.worker_runtime_version,
            "compiler_name": version.compiler_name,
            "compiler_version": version.compiler_version,
            "compiler_options_hash": version.compiler_options_hash,
            "helper_api_version": version.helper_api_version,
            "rate_limit_bucket_key": version.rate_limit_bucket_key or supplier.supplier_id,
            "provider_model_name": revision.provider_model_name,
            "capability": revision.capability,
            "config_hash": config.config_hash,
        }
        if any(getattr(snapshot, field) != value for field, value in expected.items()):
            raise ValueError("snapshot fingerprint mismatch")
        if config.supplier_id != supplier.supplier_id:
            raise ValueError("snapshot config mismatch")
        _verify_object(store, version.source_object_id, version.source_hash)
        _verify_object(
            store, version.compiled_artifact_object_id, version.compiled_artifact_hash
        )
        if version.manifest_object_id:
            _verify_object(store, version.manifest_object_id, version.manifest_hash)
        _verify_object(store, revision.definition_object_id, revision.definition_hash)
        if config.config_object_id:
            _verify_object(store, config.config_object_id, config.config_hash)
        if (
            snapshot.worker_protocol_version,
            snapshot.helper_api_version,
        ) not in SUPPORTED_RUNTIME_PAIRS:
            raise ValueError("worker protocol or helper API unavailable")
        if snapshot.worker_runtime_version != current_worker_runtime_version():
            raise ValueError("worker runtime unavailable")
        if hashlib.sha256(_canonical(snapshot.worker_limits).encode("utf-8")).hexdigest() != snapshot.worker_limits_hash:
            raise ValueError("worker limits fingerprint mismatch")
        WorkerLimits(**snapshot.worker_limits)
        if snapshot.resolved_credential_version_id:
            credential = store.get_credential_version(snapshot.resolved_credential_version_id)
            if (
                credential is None
                or credential.supplier_id != supplier.supplier_id
                or credential.state != "ready"
            ):
                raise ValueError("credential unavailable")
        elif snapshot.credential_resolution_mode == "historical":
            raise ValueError("historical credential missing")
    except SupplierRuntimeUnavailable:
        raise
    except Exception as exc:
        raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE") from exc


def _verify_object(store, object_id, expected_hash):
    raw = store.runtime.read_text(object_id)
    actual = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if expected_hash and actual != expected_hash:
        raise ValueError("immutable object hash mismatch")
