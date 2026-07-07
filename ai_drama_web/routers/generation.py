import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.config import Settings
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.schemas.generation import (
    GenerationJobDetailRead,
    GenerationJobRead,
    VideoJobCreate,
)
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import AssetDeliveryInvalidPublicBaseUrl
from ai_drama_web.services.generation_jobs import GenerationJobBlocked, GenerationJobService
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")

UI_STATUS_BY_INTERNAL_STATUS = {
    "draft": "waiting",
    "queued": "queued",
    "submitting": "submitting",
    "submitted": "generating",
    "polling": "generating",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_secret_store(request: Request) -> LocalSecretStore:
    return request.app.state.secret_store


def get_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
    settings: Settings = Depends(get_settings),
    secret_store: LocalSecretStore = Depends(get_secret_store),
) -> GenerationJobService:
    return GenerationJobService(
        product_store,
        runtime_store,
        secret_store,
        public_base_url=settings.public_base_url,
    )


@router.post(
    "/chapters/{chapter_id}/generation/video-jobs",
    response_model=GenerationJobRead,
)
async def queue_video_job(
    chapter_id: str,
    payload: VideoJobCreate,
    service: GenerationJobService = Depends(get_service),
):
    try:
        job = service.queue_video_job(
            prompt_revision_id=payload.prompt_revision_id,
            shot_id=payload.shot_id,
            idempotency_key=payload.idempotency_key,
            overrides=payload.overrides,
        )
    except GenerationJobBlocked as exc:
        return _error(409, "shot_prompt_blocked", str(exc))
    except AssetDeliveryInvalidPublicBaseUrl:
        return _error(409, "input_unreachable", "public asset delivery URL is not provider reachable")
    if job.chapter_id != chapter_id:
        raise HTTPException(status_code=404, detail="chapter or shot prompt revision not found")
    return _job_read(job)


@router.get(
    "/chapters/{chapter_id}/generation/jobs",
    response_model=list[GenerationJobRead],
)
async def list_generation_jobs(
    chapter_id: str,
    product_store: ProductStore = Depends(get_product_store),
):
    return [_job_read(job) for job in product_store.list_generation_jobs_for_chapter(chapter_id)]


@router.get("/generation/jobs/{job_id}", response_model=GenerationJobDetailRead)
async def generation_job_detail(
    job_id: str,
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
):
    job = product_store.get_generation_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="generation job not found")
    body = _job_read(job)
    return {**body, "request": json.loads(runtime_store.read_text(job.request_object_id))}


def _job_read(job) -> dict:
    return {
        "job_id": job.job_id,
        "provider": job.provider,
        "job_type": job.job_type,
        "project_id": job.project_id,
        "chapter_id": job.chapter_id,
        "shot_id": job.shot_id,
        "prompt_revision_id": job.prompt_revision_id,
        "provider_job_id": job.provider_job_id,
        "provider_result_id": job.provider_result_id,
        "internal_status": job.internal_status,
        "ui_status": UI_STATUS_BY_INTERNAL_STATUS[job.internal_status],
        "idempotency_key": job.idempotency_key,
        "request_hash": job.request_hash,
        "request_object_id": job.request_object_id,
        "response_object_id": job.response_object_id,
        "attempt_number": job.attempt_number,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "submitted_at": job.submitted_at,
        "next_poll_at": job.next_poll_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _error(status_code: int, error_code: str, error_message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "error_message": error_message},
    )
