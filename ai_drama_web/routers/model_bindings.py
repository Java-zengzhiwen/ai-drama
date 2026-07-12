from fastapi import APIRouter, Header, HTTPException, Request, Response

from ai_drama_web.schemas.models import ProjectModelBindingsUpdate
from ai_drama_web.suppliers.models import RevisionConflict
from ai_drama_web.suppliers.resolution import (
    BindingError,
    ModelBindingService,
    ModelResolutionError,
    ModelResolver,
)


router = APIRouter(prefix="/api/projects")


@router.get("/{project_id}/model-bindings")
async def get_bindings(project_id: str, request: Request, response: Response):
    try:
        binding = ModelBindingService(request.app.state.product_store).get(project_id)
    except BindingError as exc:
        _binding_error(exc)
    response.headers["ETag"] = _etag(binding.binding_set_revision)
    return _binding_read(binding)


@router.put("/{project_id}/model-bindings")
async def put_bindings(
    project_id: str,
    payload: ProjectModelBindingsUpdate,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match)
    try:
        binding = ModelBindingService(request.app.state.product_store).replace(
            project_id,
            defaults=payload.defaults,
            overrides=payload.operation_overrides,
            expected_revision=revision,
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    except BindingError as exc:
        _binding_error(exc)
    response.headers["ETag"] = _etag(binding.binding_set_revision)
    return _binding_read(binding)


@router.get("/{project_id}/model-resolution/{operation_key}")
async def resolve_model(project_id: str, operation_key: str, request: Request):
    try:
        resolved = ModelResolver(request.app.state.product_store).resolve(project_id, operation_key)
    except ModelResolutionError as exc:
        _binding_error(exc)
    return {
        "project_id": project_id,
        "operation_key": operation_key,
        "capability": resolved.capability,
        "binding_source": resolved.binding_source,
        "supplier_id": resolved.supplier.supplier_id,
        "supplier_model_id": resolved.model.supplier_model_id,
        "model_revision_id": resolved.revision.model_revision_id,
        "provider_model_name": resolved.revision.provider_model_name,
    }


def _binding_read(binding):
    return {
        "project_id": binding.project_id,
        "defaults": {
            "text": binding.default_text_model_id,
            "image": binding.default_image_model_id,
            "video": binding.default_video_model_id,
        },
        "operation_overrides": binding.overrides,
        "binding_set_revision": binding.binding_set_revision,
    }


def _expected_revision(header):
    if not header:
        raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})
    try:
        return int(header.strip().strip('"').removeprefix("binding-set-"))
    except ValueError as exc:
        raise HTTPException(400, detail={"error_code": "INVALID_ETAG"}) from exc


def _etag(revision):
    return '"binding-set-%s"' % revision


def _binding_error(exc):
    status = 404 if exc.code == "PROJECT_NOT_FOUND" else 409
    raise HTTPException(status, detail={"error_code": exc.code}) from exc
