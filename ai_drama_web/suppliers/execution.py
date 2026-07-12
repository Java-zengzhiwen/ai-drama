import json
from dataclasses import replace

from .contracts import CompiledSupplierArtifact
from .snapshots import SupplierRuntimeUnavailable, load_snapshot
from .worker import SupplierWorker, WorkerLimits


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
            snapshot = load_snapshot(self.store, snapshot_hash)
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
            return self.worker.invoke(artifact, operation, payload, mode="execution", limits=limits or WorkerLimits()).value
        except SupplierRuntimeUnavailable:
            raise
        except RuntimeError as exc:
            code = str(exc)
            if code in {"CREDENTIAL_STORAGE_CORRUPT", "CREDENTIAL_NOT_READY"}:
                raise SupplierExecutionError(code) from exc
            raise
