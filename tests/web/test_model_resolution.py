import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from ai_drama_web.suppliers.resolution import ModelBindingService, ModelResolutionError, ModelResolver
from tests.web.model_test_support import create_model


def _setup(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Resolve")
    supplier = store.list_suppliers()[0]
    default = create_model(store, supplier, capability="text", name="default", catalog_revision=0, key="default")
    override = create_model(store, supplier, capability="text", name="override", catalog_revision=1, key="override")
    ModelBindingService(store).replace(
        project.project_id,
        defaults={"text": default.supplier_model_id, "image": "", "video": ""},
        overrides={"storyboard_design": override.supplier_model_id},
        expected_revision=0,
    )
    return store, project, supplier, default, override


def test_override_precedes_capability_default(tmp_path):
    store, project, _supplier, default, override = _setup(tmp_path)
    resolver = ModelResolver(store)
    specific = resolver.resolve(project.project_id, "storyboard_design")
    inherited = resolver.resolve(project.project_id, "script_adaptation")
    assert specific.model.supplier_model_id == override.supplier_model_id
    assert specific.binding_source == "operation_override"
    assert inherited.model.supplier_model_id == default.supplier_model_id
    assert inherited.binding_source == "capability_default"


def test_resolution_fails_closed_for_missing_disabled_or_mismatch(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Closed")
    resolver = ModelResolver(store)
    with pytest.raises(ModelResolutionError, match="MODEL_BINDING_MISSING"):
        resolver.resolve(project.project_id, "shot_video_generation")
    with pytest.raises(ModelResolutionError, match="UNKNOWN_OPERATION_KEY"):
        resolver.resolve(project.project_id, "unknown")

    supplier = store.list_suppliers()[0]
    model = create_model(store, supplier, capability="text", name="disabled", catalog_revision=0, key="disabled")
    ModelBindingService(store).replace(
        project.project_id,
        defaults={"text": model.supplier_model_id, "image": "", "video": ""},
        overrides={},
        expected_revision=0,
    )
    ModelCatalogService(store).set_enabled(
        model.supplier_model_id,
        enabled=False,
        expected_catalog_revision=1,
        expected_model_revision=1,
    )
    with pytest.raises(ModelResolutionError, match="MODEL_DISABLED"):
        resolver.resolve(project.project_id, "script_adaptation")

    ModelCatalogService(store).set_enabled(
        model.supplier_model_id,
        enabled=True,
        expected_catalog_revision=2,
        expected_model_revision=2,
    )
    store.update_supplier(supplier.supplier_id, enabled=False, expected_revision=1)
    with pytest.raises(ModelResolutionError, match="SUPPLIER_DISABLED"):
        resolver.resolve(project.project_id, "script_adaptation")


def test_resolver_has_no_side_effects_or_worker_calls(tmp_path):
    store, project, _supplier, _default, _override = _setup(tmp_path)
    before = store.conn.total_changes
    resolved = ModelResolver(store).resolve(project.project_id, "script_adaptation")
    assert resolved.revision.capability == "text"
    assert store.conn.total_changes == before
