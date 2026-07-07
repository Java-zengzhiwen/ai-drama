from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from ai_drama_runtime.services import WorkflowGateError
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.config import Settings
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.services.script_workflow import WorkflowExecutionError
from ai_drama_web.services.shot_prompts import (
    ShotPromptInvalidContent,
    ShotPromptReadinessBlocked,
    ShotPromptService,
    ShotPromptShotNotFound,
)
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")


class ShotPromptRevisionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repo_root(request: Request):
    return request.app.state.repo_root


def get_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
    settings: Settings = Depends(get_settings),
    repo_root=Depends(get_repo_root),
) -> ShotPromptService:
    return ShotPromptService(product_store, runtime_store, settings, repo_root)


@router.post("/chapters/{chapter_id}/shot-prompts/generate")
async def generate_shot_prompts(
    chapter_id: str,
    service: ShotPromptService = Depends(get_service),
):
    try:
        return service.generate(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except WorkflowGateError as exc:
        return _error(409, exc.code, exc.safe_message)
    except WorkflowExecutionError as exc:
        return _error(exc.status_code, exc.code, exc.safe_message)


@router.get("/chapters/{chapter_id}/shot-prompts/revisions")
async def list_shot_prompt_revisions(
    chapter_id: str,
    service: ShotPromptService = Depends(get_service),
):
    try:
        return service.list_revisions(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except ShotPromptInvalidContent as exc:
        return _error(422, exc.code, exc.safe_message)


@router.put("/shot-prompt-revisions/{revision_id}")
async def update_shot_prompt_revision(
    revision_id: str,
    payload: ShotPromptRevisionUpdate,
    service: ShotPromptService = Depends(get_service),
):
    try:
        return service.create_manual_revision(revision_id, payload.content)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="shot prompt revision not found")
    except ShotPromptInvalidContent as exc:
        return _error(422, exc.code, exc.safe_message)
    except WorkflowExecutionError as exc:
        return _error(exc.status_code, exc.code, exc.safe_message)


@router.post("/shot-prompt-revisions/{revision_id}/shots/{shot_id}/regenerate")
async def regenerate_shot_prompt(
    revision_id: str,
    shot_id: str,
    service: ShotPromptService = Depends(get_service),
):
    try:
        return service.regenerate_shot(revision_id, shot_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="shot prompt revision not found")
    except ShotPromptShotNotFound:
        raise HTTPException(status_code=404, detail="shot not found")
    except ShotPromptInvalidContent as exc:
        return _error(422, exc.code, exc.safe_message)
    except WorkflowExecutionError as exc:
        return _error(exc.status_code, exc.code, exc.safe_message)


@router.post("/shot-prompt-revisions/{revision_id}/shots/{shot_id}/mark-ready")
async def mark_shot_prompt_ready(
    revision_id: str,
    shot_id: str,
    service: ShotPromptService = Depends(get_service),
):
    try:
        return service.mark_ready(revision_id, shot_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="shot prompt revision not found")
    except ShotPromptShotNotFound:
        raise HTTPException(status_code=404, detail="shot not found")
    except ShotPromptInvalidContent as exc:
        return _error(422, exc.code, exc.safe_message)
    except ShotPromptReadinessBlocked as exc:
        return _error(exc.status_code, exc.code, exc.safe_message)


@router.get("/shot-prompt-revisions/{revision_id}/shots/{shot_id}/agnes-preview")
async def agnes_preview(
    revision_id: str,
    shot_id: str,
    service: ShotPromptService = Depends(get_service),
):
    try:
        return service.agnes_preview(revision_id, shot_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="shot prompt revision not found")
    except ShotPromptShotNotFound:
        raise HTTPException(status_code=404, detail="shot not found")
    except ShotPromptInvalidContent as exc:
        return _error(422, exc.code, exc.safe_message)


def _error(status_code: int, error_code: str, error_message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "error_message": error_message},
    )
