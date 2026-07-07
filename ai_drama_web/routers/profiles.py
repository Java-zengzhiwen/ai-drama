from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_204_NO_CONTENT

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.schemas.profiles import (
    ProductionProfileCreate,
    ProductionProfileRead,
    ProductionProfileUpdate,
    ProfileType,
)
from ai_drama_web.services.profiles import ProductionProfileService, ProfileValidationError
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")


def get_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
) -> ProductionProfileService:
    return ProductionProfileService(product_store, runtime_store)


@router.post("/projects/{project_id}/profiles", response_model=ProductionProfileRead)
async def create_profile(
    project_id: str,
    payload: ProductionProfileCreate,
    service: ProductionProfileService = Depends(get_service),
):
    try:
        return service.create_profile(project_id, payload)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="project or chapter not found")


@router.get("/projects/{project_id}/profiles", response_model=list[ProductionProfileRead])
async def list_profiles(
    project_id: str,
    chapter_id: str | None = None,
    profile_type: ProfileType | None = None,
    service: ProductionProfileService = Depends(get_service),
):
    try:
        return service.list_profiles(project_id, chapter_id=chapter_id, profile_type=profile_type)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="project or chapter not found")


@router.put("/profiles/{profile_id}", response_model=ProductionProfileRead)
async def update_profile(
    profile_id: str,
    payload: ProductionProfileUpdate,
    service: ProductionProfileService = Depends(get_service),
):
    try:
        return service.update_profile(profile_id, payload)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="profile not found")
    except ProfileValidationError:
        raise HTTPException(status_code=422, detail="invalid profile payload")


@router.delete("/profiles/{profile_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    service: ProductionProfileService = Depends(get_service),
):
    try:
        service.delete_profile(profile_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="profile not found")
