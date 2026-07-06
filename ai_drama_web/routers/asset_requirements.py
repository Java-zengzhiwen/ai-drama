from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.services.asset_requirements import (
    AssetRequirementService,
    AssetRequirementsNotAnalyzed,
    StoryboardNotApproved,
)
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")


def get_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
) -> AssetRequirementService:
    return AssetRequirementService(product_store, runtime_store)


@router.post("/chapters/{chapter_id}/asset-requirements/analyze")
async def analyze_asset_requirements(
    chapter_id: str,
    service: AssetRequirementService = Depends(get_service),
):
    try:
        return service.analyze(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except StoryboardNotApproved:
        return _error(
            409,
            "STORYBOARD_NOT_APPROVED",
            "current approved canonical storyboard is required",
        )


@router.get("/chapters/{chapter_id}/asset-requirements/latest")
async def latest_asset_requirements(
    chapter_id: str,
    service: AssetRequirementService = Depends(get_service),
):
    try:
        return service.latest(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except AssetRequirementsNotAnalyzed:
        return _error(
            409,
            "ASSET_REQUIREMENTS_NOT_ANALYZED",
            "asset requirements have not been analyzed",
        )


def _error(status_code: int, error_code: str, error_message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "error_message": error_message},
    )
