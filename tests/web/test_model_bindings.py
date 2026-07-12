import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.models import RevisionConflict
from ai_drama_web.suppliers.resolution import BindingError, ModelBindingService
from tests.web.model_test_support import create_model


def _setup(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Bindings")
    supplier = store.list_suppliers()[0]
    text = create_model(store, supplier, capability="text", name="text", catalog_revision=0, key="t")
    image = create_model(store, supplier, capability="image", name="image", catalog_revision=1, key="i")
    video = create_model(store, supplier, capability="video", name="video", catalog_revision=2, key="v")
    return store, project, text, image, video


def test_binding_set_is_one_atomic_cas_unit(tmp_path):
    store, project, text, image, video = _setup(tmp_path)
    service = ModelBindingService(store)
    binding = service.replace(
        project.project_id,
        defaults={"text": text.supplier_model_id, "image": image.supplier_model_id, "video": video.supplier_model_id},
        overrides={"storyboard_design": text.supplier_model_id},
        expected_revision=0,
    )
    assert binding.binding_set_revision == 1
    assert service.get(project.project_id).overrides == {"storyboard_design": text.supplier_model_id}

    with pytest.raises(RevisionConflict):
        service.replace(
            project.project_id,
            defaults={"text": text.supplier_model_id, "image": "", "video": ""},
            overrides={},
            expected_revision=0,
        )
    assert service.get(project.project_id).default_image_model_id == image.supplier_model_id


def test_binding_rejects_capability_mismatch_and_unknown_operation(tmp_path):
    store, project, text, image, _video = _setup(tmp_path)
    service = ModelBindingService(store)
    with pytest.raises(BindingError, match="MODEL_CAPABILITY_MISMATCH"):
        service.replace(
            project.project_id,
            defaults={"text": image.supplier_model_id, "image": "", "video": ""},
            overrides={},
            expected_revision=0,
        )
    with pytest.raises(BindingError, match="UNKNOWN_OPERATION_KEY"):
        service.replace(
            project.project_id,
            defaults={"text": text.supplier_model_id, "image": "", "video": ""},
            overrides={"not_an_operation": text.supplier_model_id},
            expected_revision=0,
        )
