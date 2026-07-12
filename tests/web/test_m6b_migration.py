from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import M6B_MODEL_CATALOG_MIGRATION_ID, ProductStore
from ai_drama_web.suppliers.models import stable_builtin_model_id
from ai_drama_web.suppliers.compiler import compile_supplier


M6B_TABLES = {
    "supplier_models",
    "supplier_model_revisions",
    "project_model_bindings",
    "project_model_operation_overrides",
    "execution_snapshots",
    "model_creation_requests",
    "supplier_idempotency_records",
}


def _open(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return runtime, ProductStore(runtime)


def test_m6b_migration_is_additive_and_replayable(tmp_path):
    runtime, store = _open(tmp_path)
    project = store.create_project(name="Preserved")
    supplier_ids = {item.slug: item.supplier_id for item in store.list_suppliers()}

    tables = {
        row["name"]
        for row in runtime.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert M6B_TABLES <= tables
    assert runtime.conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
        (M6B_MODEL_CATALOG_MIGRATION_ID,),
    ).fetchone()
    assert all(item.model_catalog_revision == 0 for item in store.list_suppliers())
    runtime.close()

    runtime, replayed = _open(tmp_path)
    assert replayed.get_project(project.project_id).name == "Preserved"
    assert {item.slug: item.supplier_id for item in replayed.list_suppliers()} == supplier_ids
    assert runtime.conn.execute(
        "SELECT COUNT(*) AS n FROM schema_migrations WHERE migration_id = ?",
        (M6B_MODEL_CATALOG_MIGRATION_ID,),
    ).fetchone()["n"] == 1


def test_builtin_model_identity_is_deterministic_and_supplier_scoped():
    first = stable_builtin_model_id("supplier-a", "text:model-v1")
    assert first == stable_builtin_model_id("supplier-a", "text:model-v1")
    assert first != stable_builtin_model_id("supplier-b", "text:model-v1")
    assert first != stable_builtin_model_id("supplier-a", "text:model-v2")


def test_m6b_upgrade_seeds_base_models_from_current_immutable_manifest(tmp_path):
    runtime, store = _open(tmp_path)
    supplier = store.list_suppliers()[0]
    source = """
export const vendor = {
  id: "migration", version: "1", name: "Migration", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "migration-text",
  inputs: [], inputValues: {},
  models: [{ providerModelName: "legacy-text", displayName: "Legacy Text", capability: "text" }]
};
export async function textRequest() { return { text: "fake" }; }
"""
    artifact = compile_supplier(source, runtime_store=runtime)
    store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id=artifact.source_object_id,
        source_hash=artifact.source_hash,
        compiled_artifact_object_id=artifact.compiled_artifact_object_id,
        compiled_artifact_hash=artifact.compiled_artifact_hash,
        manifest_hash=artifact.manifest_hash,
        adapter_contract_version=artifact.adapter_contract_version,
        worker_protocol_version="1",
        worker_runtime_version=artifact.worker_runtime_version,
        compiler_name=artifact.compiler_name,
        compiler_version=artifact.compiler_version,
        compiler_options_hash=artifact.compiler_options_hash,
        helper_api_version=artifact.helper_api_version,
        expected_revision=1,
    )
    runtime.conn.execute("DELETE FROM supplier_model_revisions")
    runtime.conn.execute("DELETE FROM supplier_models")
    runtime.conn.execute(
        "DELETE FROM schema_migrations WHERE migration_id = ?",
        (M6B_MODEL_CATALOG_MIGRATION_ID,),
    )
    runtime.conn.commit()
    runtime.close()

    runtime, upgraded = _open(tmp_path)
    models = upgraded.list_supplier_models(supplier.supplier_id)
    assert len(models) == 1
    assert models[0].source == "built_in"
    revision = upgraded.get_supplier_model_revision(models[0].current_model_revision_id)
    assert revision.provider_model_name == "legacy-text"
    assert models[0].supplier_model_id == stable_builtin_model_id(
        supplier.supplier_id, "text:legacy-text"
    )
