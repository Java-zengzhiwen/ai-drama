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
    assert all(item.current_supplier_version_id for item in suppliers)
    first_ids = {item.slug: item.supplier_id for item in suppliers}
    runtime.close()

    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    reopened = ProductStore(runtime)

    assert {item.slug: item.supplier_id for item in reopened.list_suppliers()} == first_ids
    config_count = runtime.conn.execute(
        "SELECT COUNT(*) AS n FROM supplier_config_revisions"
    ).fetchone()["n"]
    assert config_count == 5
    assert runtime.conn.execute(
        "SELECT COUNT(*) AS n FROM supplier_versions WHERE built_in = 1"
    ).fetchone()["n"] == 5


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


def test_supplier_version_persists_complete_runtime_fingerprint(tmp_path):
    _, store = _store(tmp_path)
    supplier = store.create_supplier(slug="fingerprint", display_name="Fingerprint")

    version = store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id="source",
        source_hash="source-hash",
        compiled_artifact_object_id="compiled",
        compiled_artifact_hash="compiled-hash",
        manifest_hash="manifest-hash",
        adapter_contract_version="ai-drama-supplier-v1",
        worker_protocol_version="1",
        worker_runtime_version="v25.5.0",
        compiler_name="esbuild",
        compiler_version="0.25.12",
        compiler_options_hash="options-hash",
        helper_api_version="ai-drama-helper-v1",
        expected_revision=1,
    )

    assert version.adapter_contract_version == "ai-drama-supplier-v1"
    assert version.worker_protocol_version == "1"
    assert version.worker_runtime_version == "v25.5.0"
    assert version.compiler_name == "esbuild"
    assert version.compiler_version == "0.25.12"
    assert version.compiler_options_hash == "options-hash"
    assert version.helper_api_version == "ai-drama-helper-v1"


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


def test_supplier_creation_and_idempotency_record_are_one_transaction(tmp_path):
    _, store = _store(tmp_path)
    store.conn.executescript(
        """
        CREATE TRIGGER abort_supplier_creation_request
        BEFORE INSERT ON supplier_creation_requests
        BEGIN
          SELECT RAISE(ABORT, 'simulated journal failure');
        END;
        """
    )

    with pytest.raises(Exception, match="simulated journal failure"):
        store.create_supplier_idempotent(
            slug="atomic",
            display_name="Atomic",
            idempotency_key="atomic-key",
            request_hash="request-hash",
        )

    assert store.conn.execute("SELECT 1 FROM suppliers WHERE slug = 'atomic'").fetchone() is None


def test_supplier_update_uses_atomic_compare_and_swap(tmp_path):
    _, store = _store(tmp_path)
    supplier = store.create_supplier(slug="cas", display_name="CAS")

    updated = store.update_supplier(
        supplier.supplier_id,
        display_name="Updated",
        expected_revision=1,
    )

    assert updated.revision == 2
    with pytest.raises(RevisionConflict):
        store.update_supplier(
            supplier.supplier_id,
            display_name="Stale",
            expected_revision=1,
        )
