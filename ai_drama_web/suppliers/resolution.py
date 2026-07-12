from dataclasses import dataclass

from ai_drama_runtime.services import NotFound

from .models import ProjectModelBindingRecord, RevisionConflict
from .operations import OPERATION_CAPABILITIES


class BindingError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class ModelResolutionError(BindingError):
    pass


@dataclass(frozen=True)
class BindingSet:
    project_id: str
    default_text_model_id: str
    default_image_model_id: str
    default_video_model_id: str
    binding_set_revision: int
    overrides: dict[str, str]


@dataclass(frozen=True)
class ResolvedModel:
    project_id: str
    operation_key: str
    capability: str
    binding_source: str
    supplier: object
    model: object
    revision: object


class ModelBindingService:
    def __init__(self, store):
        self.store = store

    def get(self, project_id):
        if self.store.get_project(project_id) is None:
            raise BindingError("PROJECT_NOT_FOUND")
        record = self.store.get_project_model_binding(project_id)
        overrides = self.store.get_project_model_overrides(project_id)
        if record is None:
            return BindingSet(project_id, "", "", "", 0, overrides)
        return BindingSet(
            record.project_id,
            record.default_text_model_id or "",
            record.default_image_model_id or "",
            record.default_video_model_id or "",
            record.binding_set_revision,
            overrides,
        )

    def replace(self, project_id, *, defaults, overrides, expected_revision):
        if self.store.get_project(project_id) is None:
            raise BindingError("PROJECT_NOT_FOUND")
        normalized_defaults = {name: str(defaults.get(name) or "") for name in ("text", "image", "video")}
        for capability, model_id in normalized_defaults.items():
            if model_id:
                self._validate_capability(model_id, capability)
        for operation_key, model_id in overrides.items():
            capability = OPERATION_CAPABILITIES.get(operation_key)
            if capability is None:
                raise BindingError("UNKNOWN_OPERATION_KEY")
            self._validate_capability(model_id, capability)
        try:
            self.store.replace_project_model_bindings(
                project_id,
                defaults=normalized_defaults,
                overrides=dict(overrides),
                expected_revision=expected_revision,
            )
        except RevisionConflict:
            raise
        except ValueError as exc:
            raise BindingError(str(exc)) from exc
        return self.get(project_id)

    def _validate_capability(self, supplier_model_id, expected):
        model = self.store.get_supplier_model(supplier_model_id)
        if model is None:
            raise BindingError("MODEL_NOT_FOUND")
        revision = self.store.get_supplier_model_revision(model.current_model_revision_id)
        if revision.capability != expected:
            raise BindingError("MODEL_CAPABILITY_MISMATCH")


class ModelResolver:
    def __init__(self, store):
        self.store = store

    def resolve(self, project_id, operation_key):
        capability = OPERATION_CAPABILITIES.get(operation_key)
        if capability is None:
            raise ModelResolutionError("UNKNOWN_OPERATION_KEY")
        binding = ModelBindingService(self.store).get(project_id)
        model_id = binding.overrides.get(operation_key, "")
        source = "operation_override"
        if not model_id:
            model_id = getattr(binding, "default_%s_model_id" % capability)
            source = "capability_default"
        if not model_id:
            raise ModelResolutionError("MODEL_BINDING_MISSING")
        model = self.store.get_supplier_model(model_id)
        if model is None:
            raise ModelResolutionError("MODEL_BINDING_MISSING")
        revision = self.store.get_supplier_model_revision(model.current_model_revision_id)
        if revision is None or revision.capability != capability:
            raise ModelResolutionError("MODEL_CAPABILITY_MISMATCH")
        supplier = self.store.get_supplier(model.supplier_id)
        if supplier is None or not supplier.enabled:
            raise ModelResolutionError("SUPPLIER_DISABLED")
        if not model.enabled:
            raise ModelResolutionError("MODEL_DISABLED")
        return ResolvedModel(
            project_id,
            operation_key,
            capability,
            source,
            supplier,
            model,
            revision,
        )
