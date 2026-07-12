import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.models import RevisionConflict


def _store(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return runtime, ProductStore(runtime)


def test_builtin_suppliers_have_stable_ids_and_one_config_each(tmp_path):
    runtime, store = _store(tmp_path)

    suppliers = store.list_suppliers()

    assert [item.slug for item in suppliers] == [
        "agnes",
        "anthropic",
        "deepseek",
        "openai",
        "xai",
    ]
    assert all(item.source == "built_in" for item in suppliers)
    assert all(item.revision == 1 for item in suppliers)
    assert all(item.current_config_revision_id for item in suppliers)
    first_ids = {item.slug: item.supplier_id for item in suppliers}
    runtime.close()

    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    reopened = ProductStore(runtime)

    assert {item.slug: item.supplier_id for item in reopened.list_suppliers()} == first_ids
    config_count = runtime.conn.execute(
        "SELECT COUNT(*) AS n FROM supplier_config_revisions"
    ).fetchone()["n"]
    assert config_count == 5


def test_supplier_versions_are_immutable_and_replace_requires_current_revision(tmp_path):
    _, store = _store(tmp_path)
    supplier = store.create_supplier(slug="local-studio", display_name="Local Studio")

    first = store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id="source-1",
        source_hash="hash-1",
        compiled_artifact_object_id="compiled-1",
        compiled_artifact_hash="compiled-hash-1",
        manifest_hash="manifest-hash-1",
        expected_revision=1,
    )
    second = store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id="source-2",
        source_hash="hash-2",
        compiled_artifact_object_id="compiled-2",
        compiled_artifact_hash="compiled-hash-2",
        manifest_hash="manifest-hash-2",
        expected_revision=2,
    )

    assert first.supplier_version_id != second.supplier_version_id
    assert store.get_supplier_version(first.supplier_version_id).source_hash == "hash-1"
    assert store.get_supplier(supplier.supplier_id).current_supplier_version_id == second.supplier_version_id
    assert store.get_supplier(supplier.supplier_id).revision == 3

    with pytest.raises(RevisionConflict):
        store.replace_supplier_version(
            supplier.supplier_id,
            source_object_id="stale",
            source_hash="stale",
            compiled_artifact_object_id="stale",
            compiled_artifact_hash="stale",
            manifest_hash="stale",
            expected_revision=2,
        )


def test_config_revision_counter_is_independent_from_supplier_revision(tmp_path):
    _, store = _store(tmp_path)
    supplier = store.create_supplier(slug="config-only", display_name="Config Only")
    original_supplier_revision = supplier.revision

    config = store.replace_supplier_config(
        supplier.supplier_id,
        config_object_id="config-object",
        config_hash="config-hash",
        expected_revision=1,
    )

    refreshed = store.get_supplier(supplier.supplier_id)
    assert config.revision == 2
    assert refreshed.config_revision == 2
    assert refreshed.revision == original_supplier_revision


def test_supplier_slug_is_unique(tmp_path):
    _, store = _store(tmp_path)
    store.create_supplier(slug="unique", display_name="First")

    with pytest.raises(ValueError, match="supplier slug already exists"):
        store.create_supplier(slug="unique", display_name="Second")

