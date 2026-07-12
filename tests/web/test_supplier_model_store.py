from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


def test_supplier_model_records_round_trip(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    supplier = store.list_suppliers()[0]

    model = store.create_supplier_model(
        supplier.supplier_id,
        supplier_model_id="11111111111111111111111111111111",
        source="overlay",
        provider_model_name="fake-text-v1",
        display_name="Fake Text",
        capability="text",
        definition={"temperature": {"maximum": 1}},
        expected_catalog_revision=0,
    )

    assert model.supplier_id == supplier.supplier_id
    assert model.source == "overlay"
    assert model.enabled == 1
    revision = store.get_supplier_model_revision(model.current_model_revision_id)
    assert revision.provider_model_name == "fake-text-v1"
    assert revision.capability == "text"
    assert runtime.read_text(revision.definition_object_id) == '{"temperature":{"maximum":1}}'
    assert store.get_supplier(supplier.supplier_id).model_catalog_revision == 1
