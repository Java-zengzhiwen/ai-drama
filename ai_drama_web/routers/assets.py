import json

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError
from starlette.responses import JSONResponse, Response

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.schemas.assets import (
    AssetBindingCreate,
    AssetBindingRead,
    AssetGenerateImageRequest,
    AssetRead,
    AssetRejectRequest,
    AssetType,
    AssetUploadFields,
)
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.services.asset_generation import (
    AssetGenerationResultFetchFailed,
    AssetGenerationResultMissing,
    AssetGenerationService,
)
from ai_drama_web.services.assets import (
    AssetAdoptionNotAllowed,
    AssetRejectReasonRequired,
    AssetService,
    AssetTooLarge,
    AssetUnsupportedMediaType,
)
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")


def get_service(
    request: Request,
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
) -> AssetService:
    return AssetService(
        product_store,
        runtime_store,
        max_upload_bytes=_max_asset_upload_bytes(request),
    )


def get_generation_service(
    request: Request,
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
) -> AssetGenerationService:
    backend = getattr(request.app.state, "generation_backend", None)
    if backend is None:
        backend = FakeGenerationBackend()
        request.app.state.generation_backend = backend
    return AssetGenerationService(product_store, runtime_store, backend)


@router.post("/chapters/{chapter_id}/assets", response_model=AssetRead)
async def upload_asset(
    chapter_id: str,
    file: UploadFile = File(...),
    asset_type: AssetType = Form(...),
    name: str = Form(...),
    metadata: str = Form("{}"),
    service: AssetService = Depends(get_service),
):
    try:
        parsed_metadata = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="metadata must be a JSON object")
    if not isinstance(parsed_metadata, dict):
        raise HTTPException(status_code=422, detail="metadata must be a JSON object")
    try:
        fields = _asset_upload_fields(
            asset_type=asset_type,
            name=name,
            metadata=parsed_metadata,
        )
    except ValidationError:
        raise HTTPException(status_code=422, detail="invalid asset upload fields")
    try:
        return service.upload_asset(
            chapter_id,
            fields=fields,
            data=await _read_limited_upload(file, service.max_upload_bytes),
            media_type=file.content_type or "",
        )
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except AssetTooLarge:
        raise HTTPException(status_code=413, detail="asset upload exceeds configured size limit")
    except AssetUnsupportedMediaType:
        raise HTTPException(status_code=415, detail="unsupported asset media type")


@router.post("/chapters/{chapter_id}/assets/generate-image", response_model=AssetRead)
async def generate_image_asset(
    chapter_id: str,
    payload: AssetGenerateImageRequest,
    service: AssetGenerationService = Depends(get_generation_service),
):
    try:
        return service.generate_image_asset(chapter_id, payload)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter or input asset not found")
    except ProviderError as exc:
        return JSONResponse(
            status_code=502,
            content={"error_code": exc.code, "error_message": "image provider failed"},
        )
    except (AssetGenerationResultMissing, AssetGenerationResultFetchFailed, KeyError):
        raise HTTPException(status_code=502, detail="image generation provider error: unknown_provider_error")


@router.get("/chapters/{chapter_id}/assets", response_model=list[AssetRead])
async def list_assets(
    chapter_id: str,
    service: AssetService = Depends(get_service),
):
    try:
        return service.list_assets(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")


@router.post("/assets/{asset_id}/bindings", response_model=AssetBindingRead)
async def bind_asset(
    asset_id: str,
    payload: AssetBindingCreate,
    service: AssetService = Depends(get_service),
):
    try:
        return service.bind_asset(asset_id, payload)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="asset or target not found")
    except AssetAdoptionNotAllowed:
        raise HTTPException(status_code=409, detail="only usable assets can be current")


@router.post("/assets/{asset_id}/mark-usable", response_model=AssetRead)
async def mark_asset_usable(
    asset_id: str,
    service: AssetService = Depends(get_service),
):
    try:
        return service.mark_usable(asset_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="asset not found")


@router.post("/assets/{asset_id}/reject", response_model=AssetRead)
async def reject_asset(
    asset_id: str,
    payload: AssetRejectRequest | None = Body(default=None),
    service: AssetService = Depends(get_service),
):
    try:
        return service.reject(asset_id, reason="" if payload is None else payload.reason)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="asset not found")
    except AssetRejectReasonRequired:
        raise HTTPException(status_code=422, detail="rejection reason is required")


@router.get("/assets/{asset_id}/content")
async def asset_content(
    asset_id: str,
    service: AssetService = Depends(get_service),
):
    try:
        content, media_type = service.content(asset_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="asset not found")
    return Response(content=content, media_type=media_type)


def _asset_upload_fields(*, asset_type: str, name: str, metadata: dict):
    return AssetUploadFields.model_validate(
        {
            "asset_type": asset_type,
            "name": name,
            "metadata": metadata,
        }
    )


def _max_asset_upload_bytes(request: Request) -> int:
    return request.app.state.max_asset_upload_bytes


async def _read_limited_upload(file: UploadFile, max_upload_bytes: int) -> bytes:
    return await file.read(max_upload_bytes + 1)
