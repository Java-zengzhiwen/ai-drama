from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from ai_drama_web.suppliers.compiler import compile_supplier


def create_model(store, supplier, *, capability, name, catalog_revision, key):
    model, _ = ModelCatalogService(store).create_overlay(
        supplier.supplier_id,
        provider_model_name=name,
        display_name=name,
        capability=capability,
        definition={"constraints": {"profile": name}},
        expected_catalog_revision=catalog_revision,
        idempotency_key=key,
    )
    return model


def install_test_supplier_runtime(store, supplier, *, rate_bucket="test-bucket"):
    source = f"""
export const vendor = {{
  id: "test-runtime", version: "1", name: "Test Runtime", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "{rate_bucket}", inputs: [], inputValues: {{}}, models: []
}};
export async function textRequest(payload) {{ return {{ output: String(payload.request?.prompt || ""), usage: {{ total_tokens: 1 }} }}; }}
export async function imageRequest() {{ return {{ media_type: "image/png", bytes: "fake-png" }}; }}
"""
    artifact = compile_supplier(source, runtime_store=store.runtime)
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
