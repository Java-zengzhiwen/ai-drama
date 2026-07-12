from dataclasses import dataclass


class RevisionConflict(ValueError):
    pass


@dataclass(frozen=True)
class SupplierRecord:
    supplier_id: str
    slug: str
    display_name: str
    source: str
    enabled: int
    current_supplier_version_id: str
    current_config_revision_id: str
    current_credential_version_id: str
    revision: int
    config_revision: int
    credential_revision: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SupplierVersionRecord:
    supplier_version_id: str
    supplier_id: str
    revision: int
    source_object_id: str
    source_hash: str
    compiled_artifact_object_id: str
    compiled_artifact_hash: str
    manifest_hash: str
    adapter_contract_version: str
    worker_protocol_version: str
    worker_runtime_version: str
    compiler_name: str
    compiler_version: str
    compiler_options_hash: str
    helper_api_version: str
    built_in: int
    created_at: str


@dataclass(frozen=True)
class ConfigRevisionRecord:
    config_revision_id: str
    supplier_id: str
    revision: int
    config_object_id: str
    config_hash: str
    created_at: str


@dataclass(frozen=True)
class CredentialVersionRecord:
    credential_version_id: str
    supplier_id: str
    revision: int
    state: str
    secret_path: str
    content_hash: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CredentialJournalRecord:
    operation_id: str
    supplier_id: str
    credential_version_id: str
    operation: str
    state: str
    temp_path: str
    final_path: str
    content_hash: str
    created_at: str
    updated_at: str
