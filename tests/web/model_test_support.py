from ai_drama_web.suppliers.model_catalog import ModelCatalogService


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
