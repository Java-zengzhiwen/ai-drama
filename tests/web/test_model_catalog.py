import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.model_catalog import ModelCatalogError, ModelCatalogService
from ai_drama_web.suppliers.models import RevisionConflict


def _catalog(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    return runtime, store, ModelCatalogService(store)


def test_overlay_revision_keeps_stable_identity_and_old_revision(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    model, created = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="text-v1",
        display_name="Text One",
        capability="text",
        definition={"temperature": {"maximum": 1}},
        expected_catalog_revision=0,
        idempotency_key="create-text",
    )
    old_revision = store.get_supplier_model_revision(model.current_model_revision_id)

    revised = catalog.revise_model(
        model.supplier_model_id,
        provider_model_name="text-v2",
        display_name="Text Two",
        capability="text",
        definition={"temperature": {"maximum": 2}},
        expected_catalog_revision=1,
        expected_model_revision=1,
        acknowledged_binding_count=0,
    )

    assert created is True
    assert revised.supplier_model_id == model.supplier_model_id
    assert revised.current_model_revision_id != old_revision.model_revision_id
    assert store.get_supplier_model_revision(old_revision.model_revision_id).provider_model_name == "text-v1"
    assert store.get_supplier_model_revision(revised.current_model_revision_id).provider_model_name == "text-v2"


def test_active_duplicate_name_is_rejected_but_disabled_model_allows_reuse(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    first, _ = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="same-name",
        display_name="First",
        capability="text",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="first",
    )
    with pytest.raises(ModelCatalogError, match="MODEL_NAME_CONFLICT"):
        catalog.create_overlay(
            supplier.supplier_id,
            provider_model_name="same-name",
            display_name="Second",
            capability="text",
            definition={},
            expected_catalog_revision=1,
            idempotency_key="second",
        )

    catalog.set_enabled(
        first.supplier_model_id,
        enabled=False,
        expected_catalog_revision=1,
        expected_model_revision=1,
    )
    second, _ = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="same-name",
        display_name="Second",
        capability="text",
        definition={},
        expected_catalog_revision=2,
        idempotency_key="second",
    )
    assert second.supplier_model_id != first.supplier_model_id


def test_create_is_idempotent_and_catalog_revision_is_independent(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    model, created = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="idempotent",
        display_name="Idempotent",
        capability="image",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="same-key",
    )
    replay, replay_created = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="idempotent",
        display_name="Idempotent",
        capability="image",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="same-key",
    )
    assert replay.supplier_model_id == model.supplier_model_id
    assert replay_created is False
    assert store.get_supplier(supplier.supplier_id).config_revision == 1
    assert store.get_supplier(supplier.supplier_id).model_catalog_revision == 1

    with pytest.raises(ModelCatalogError, match="IDEMPOTENCY_CONFLICT"):
        catalog.create_overlay(
            supplier.supplier_id,
            provider_model_name="changed",
            display_name="Changed",
            capability="image",
            definition={},
            expected_catalog_revision=1,
            idempotency_key="same-key",
        )


def test_stale_catalog_and_model_revision_are_rejected(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    model, _ = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="cas",
        display_name="CAS",
        capability="video",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="cas",
    )
    catalog.set_enabled(
        model.supplier_model_id,
        enabled=False,
        expected_catalog_revision=1,
        expected_model_revision=1,
    )
    with pytest.raises(RevisionConflict):
        catalog.set_enabled(
            model.supplier_model_id,
            enabled=True,
            expected_catalog_revision=1,
            expected_model_revision=1,
        )


def test_base_and_referenced_models_cannot_be_physically_deleted(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    overlay, _ = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="bound",
        display_name="Bound",
        capability="text",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="bound",
    )
    store.conn.execute(
        "INSERT INTO project_model_bindings VALUES (?, ?, '', '', 1, ?, ?)",
        (store.create_project(name="Bound").project_id, overlay.supplier_model_id, "now", "now"),
    )
    store.conn.commit()
    with pytest.raises(ModelCatalogError, match="MODEL_REFERENCED"):
        catalog.delete_overlay(
            overlay.supplier_model_id,
            expected_catalog_revision=1,
            expected_model_revision=1,
        )

    base = store.create_supplier_model(
        supplier.supplier_id,
        supplier_model_id="22222222222222222222222222222222",
        source="built_in",
        provider_model_name="base",
        display_name="Base",
        capability="text",
        definition={},
        expected_catalog_revision=1,
    )
    with pytest.raises(ModelCatalogError, match="BUILT_IN_MODEL_DELETE_FORBIDDEN"):
        catalog.delete_overlay(
            base.supplier_model_id,
            expected_catalog_revision=2,
            expected_model_revision=1,
        )


def test_unreferenced_overlay_can_be_deleted_with_history(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    model, _ = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="temporary",
        display_name="Temporary",
        capability="image",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="temporary",
    )
    catalog.delete_overlay(
        model.supplier_model_id,
        expected_catalog_revision=1,
        expected_model_revision=1,
    )
    assert store.get_supplier_model(model.supplier_model_id) is None
    assert store.get_supplier_model_revision(model.current_model_revision_id) is None


def test_model_and_idempotency_record_commit_atomically(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    store.conn.executescript(
        """
        CREATE TRIGGER abort_model_creation_request
        BEFORE INSERT ON model_creation_requests
        BEGIN
          SELECT RAISE(ABORT, 'simulated model journal failure');
        END;
        """
    )
    with pytest.raises(Exception, match="simulated model journal failure"):
        catalog.create_overlay(
            supplier.supplier_id,
            provider_model_name="atomic",
            display_name="Atomic",
            capability="text",
            definition={},
            expected_catalog_revision=0,
            idempotency_key="atomic",
        )
    assert store.list_supplier_models(supplier.supplier_id) == []
    assert store.get_supplier(supplier.supplier_id).model_catalog_revision == 0
