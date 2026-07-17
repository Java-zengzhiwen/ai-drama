import pytest
from types import SimpleNamespace

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.model_catalog import ModelCatalogError, ModelCatalogService
from ai_drama_web.suppliers.models import ModelNameConflict
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


@pytest.mark.parametrize("effort", ["turbo", "none", "", 7, [], {"nested": "bad"}])
def test_catalog_rejects_invalid_reasoning_definition_before_persistence(tmp_path, effort):
    _runtime, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]

    with pytest.raises(ModelCatalogError, match="INVALID_REASONING_EFFORT"):
        catalog.create_overlay(
            supplier.supplier_id,
            provider_model_name="invalid-reasoning",
            display_name="Invalid Reasoning",
            capability="text",
            definition={"constraints": {"reasoning_effort": effort}},
            expected_catalog_revision=0,
            idempotency_key="invalid-reasoning",
        )

    assert store.list_supplier_models(supplier.supplier_id) == []


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
        "INSERT INTO project_model_bindings VALUES (?, ?, NULL, NULL, 1, ?, ?)",
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


def test_archived_overlay_is_hidden_but_retained_and_replay_is_idempotent(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    model, _ = catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="historical",
        display_name="Historical",
        capability="text",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="historical",
    )

    archived = store.archive_supplier_model(
        model.supplier_model_id,
        expected_catalog_revision=1,
        expected_model_revision=1,
        archive_reason="historical_snapshot",
    )
    replayed = store.archive_supplier_model(
        model.supplier_model_id,
        expected_catalog_revision=2,
        expected_model_revision=2,
        archive_reason="historical_snapshot",
    )

    assert archived.archived_at
    assert archived.archive_reason == "historical_snapshot"
    assert archived.enabled == 0
    assert archived.revision == 2
    assert replayed == archived
    assert store.list_supplier_models(supplier.supplier_id) == []
    assert store.list_supplier_models(supplier.supplier_id, include_archived=True) == [archived]
    assert store.get_supplier_model_revision(model.current_model_revision_id) is not None
    assert store.get_supplier(supplier.supplier_id).model_catalog_revision == 2


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


def test_store_transaction_rejects_active_duplicate_without_service_precheck(tmp_path):
    _, store, catalog = _catalog(tmp_path)
    supplier = store.list_suppliers()[0]
    catalog.create_overlay(
        supplier.supplier_id,
        provider_model_name="race-name",
        display_name="First",
        capability="text",
        definition={},
        expected_catalog_revision=0,
        idempotency_key="race-first",
    )
    with pytest.raises(ModelNameConflict):
        store.create_supplier_model_idempotent(
            supplier.supplier_id,
            supplier_model_id="33333333333333333333333333333333",
            source="overlay",
            provider_model_name="race-name",
            display_name="Second",
            capability="text",
            definition={},
            expected_catalog_revision=1,
            idempotency_key="race-second",
            request_hash="race-second-hash",
        )


def test_catalog_removal_delegates_reference_decision_to_one_store_transaction():
    model = SimpleNamespace(source="overlay", archived_at="")

    class AtomicStore:
        called = None

        def get_supplier_model(self, _model_id):
            return model

        def remove_supplier_model_atomically(self, model_id, **preconditions):
            self.called = (model_id, preconditions)
            return None

    store = AtomicStore()

    ModelCatalogService(store).delete_overlay(
        "model-id", expected_catalog_revision=7, expected_model_revision=3
    )

    assert store.called == (
        "model-id",
        {"expected_catalog_revision": 7, "expected_model_revision": 3},
    )
