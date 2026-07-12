from dataclasses import dataclass


@dataclass(frozen=True)
class CompiledSupplierArtifact:
    source_object_id: str
    source_hash: str
    compiled_artifact_object_id: str
    compiled_artifact_hash: str
    manifest_hash: str
    compiled_code: str
    vendor: dict
    compiler_name: str
    compiler_version: str
    compiler_options_hash: str
    adapter_contract_version: str
    helper_api_version: str
    worker_runtime_version: str
