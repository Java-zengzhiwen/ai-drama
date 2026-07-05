from fastapi import APIRouter, Depends, HTTPException

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.schemas.projects import (
    ChapterCreate,
    ChapterRead,
    ProjectCreate,
    ProjectRead,
    SourceRevisionCreate,
    SourceRevisionRead,
)
from ai_drama_web.services.chapter_status import ChapterStatusService
from ai_drama_web.services.projects import DuplicateChapterPosition, MissingRecord, ProjectService
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")


def get_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
) -> ProjectService:
    return ProjectService(product_store, runtime_store)


def get_chapter_status_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
) -> ChapterStatusService:
    return ChapterStatusService(product_store, runtime_store)


@router.post("/projects", response_model=ProjectRead)
async def create_project(payload: ProjectCreate, service: ProjectService = Depends(get_service)):
    return service.create_project(payload)


@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(service: ProjectService = Depends(get_service)):
    return service.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, service: ProjectService = Depends(get_service)):
    try:
        return service.get_project(project_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="project not found")


@router.post("/projects/{project_id}/chapters", response_model=ChapterRead)
async def create_chapter(project_id: str, payload: ChapterCreate, service: ProjectService = Depends(get_service)):
    try:
        return service.create_chapter(project_id, payload)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="project not found")
    except DuplicateChapterPosition:
        raise HTTPException(status_code=409, detail="duplicate chapter position")


@router.get("/chapters/{chapter_id}", response_model=ChapterRead)
async def get_chapter(chapter_id: str, service: ProjectService = Depends(get_service)):
    try:
        chapter, source_text = service.get_chapter(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    return ChapterRead.model_validate(chapter).model_copy(update={"source_text": source_text})


@router.get("/chapters/{chapter_id}/status")
async def get_chapter_status(
    chapter_id: str,
    service: ChapterStatusService = Depends(get_chapter_status_service),
):
    try:
        return service.get_status(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")


@router.post("/chapters/{chapter_id}/source-revisions", response_model=SourceRevisionRead)
async def create_source_revision(
    chapter_id: str,
    payload: SourceRevisionCreate,
    service: ProjectService = Depends(get_service),
):
    try:
        return service.create_source_revision(chapter_id, payload)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
