from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import M6B_MODEL_CATALOG_MIGRATION_ID, ProductStore
from ai_drama_web.suppliers.models import stable_builtin_model_id


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
