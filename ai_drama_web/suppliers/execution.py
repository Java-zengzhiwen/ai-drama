import json
import hashlib
import tempfile
from pathlib import Path
from dataclasses import replace

from .contracts import CompiledSupplierArtifact
from .snapshots import SupplierRuntimeUnavailable, load_snapshot
from .worker import SupplierWorker, WorkerLimits
from .media import image_bytes_match_media_type


class SupplierExecutionError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class SnapshotExecutionGateway:
    """Loads every execution dependency from one immutable snapshot."""
    def __init__(self, store, credential_store, *, worker=None):
        self.store = store
        self.credential_store = credential_store
        self.worker = worker or SupplierWorker()

    def invoke(self, snapshot_hash, operation, request, *, limits=None):
        try:
            if limits is not None:
                raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE")
            row = self.store.conn.execute(
                "SELECT snapshot_object_id FROM execution_snapshots WHERE snapshot_hash = ?", (snapshot_hash,)
            ).fetchone()
            if row is None:
                raise SupplierRuntimeUnavailable("SUPPLIER_RUNTIME_UNAVAILABLE")
            indexed = json.loads(self.store.runtime.read_text(row["snapshot_object_id"]))
            credential_id = indexed.get("resolved_credential_version_id", "")
            if credential_id:
                credential_record = self.store.get_credential_version(credential_id)
                if credential_record is None:
                    raise SupplierExecutionError("CREDENTIAL_MISSING")
                if credential_record.state != "ready":
                    raise SupplierExecutionError(
                        "CREDENTIAL_STORAGE_CORRUPT"
                        if credential_record.state == "credential_storage_corrupt"
                        else "CREDENTIAL_REVOKED"
                    )
            snapshot = load_snapshot(self.store, snapshot_hash)
            frozen_limits = WorkerLimits(**snapshot.worker_limits)
            version = self.store.get_supplier_version(snapshot.supplier_version_id)
            config = self.store.get_config_revision(snapshot.config_revision_id)
            compiled_code = self.store.runtime.read_text(snapshot.compiled_artifact_object_id)
            config_value = json.loads(self.store.runtime.read_text(config.config_object_id)) if config.config_object_id else {}
            credential = ""
            if snapshot.resolved_credential_version_id:
                credential = self.credential_store.read(snapshot.resolved_credential_version_id)
            artifact = CompiledSupplierArtifact(
                source_object_id=version.source_object_id,
                source_hash=version.source_hash,
                compiled_artifact_object_id=version.compiled_artifact_object_id,
                compiled_artifact_hash=version.compiled_artifact_hash,
                manifest_hash=version.manifest_hash,
                compiled_code=compiled_code,
                vendor={},
                compiler_name=version.compiler_name,
                compiler_version=version.compiler_version,
                compiler_options_hash=version.compiler_options_hash,
                adapter_contract_version=version.adapter_contract_version,
                helper_api_version=version.helper_api_version,
                worker_runtime_version=version.worker_runtime_version,
            )
            payload = {
                "request": request,
                "model": snapshot.provider_model_name,
                "config": config_value,
                "credential": credential,
            }
            value = self.worker.invoke(artifact, operation, payload, mode="execution", limits=frozen_limits).value
            if isinstance(value, dict) and value.get("local_file"):
                value = dict(value)
                local_file = Path(value.pop("local_file")).resolve()
                temp_root = Path(tempfile.gettempdir()).resolve()
                if temp_root not in local_file.parents or not local_file.parent.name.startswith("ai-drama-worker-media-"):
                    raise SupplierExecutionError("SUPPLIER_MEDIA_REFERENCE_INVALID")
                try:
                    data = local_file.read_bytes()
                    if len(data) != int(value.get("size", -1)) or hashlib.sha256(data).hexdigest() != value.get("sha256"):
                        raise SupplierExecutionError("SUPPLIER_MEDIA_REFERENCE_INVALID")
                    media_type = str(value.get("media_type") or "")
                    if operation == "imageRequest" and not image_bytes_match_media_type(
                        data, media_type
                    ):
                        raise SupplierExecutionError("PROVIDER_RESPONSE_MALFORMED")
                    value["bytes"] = data
                finally:
                    local_file.unlink(missing_ok=True)
                    local_file.parent.rmdir()
            return value
        except SupplierRuntimeUnavailable:
            raise
        except RuntimeError as exc:
            code = str(exc)
            if code in {"CREDENTIAL_STORAGE_CORRUPT", "CREDENTIAL_NOT_READY"}:
                raise SupplierExecutionError(code) from exc
            raise
