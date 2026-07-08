import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.config import Settings
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.schemas.generation import (
    GenerationRerunCreate,
    GenerationRerunRead,
    GenerationJobDetailRead,
    GenerationJobRead,
    ResultReviewCreate,
    ResultReviewRead,
    ShotResultSelectionRead,
    ShotResultsRead,
    VideoJobCreate,
)
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import AssetDeliveryInvalidPublicBaseUrl
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.services.asset_delivery import AssetDeliveryService
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.services.generation_jobs import (
    GenerationIdempotencyConflict,
    GenerationInvalidRequest,
    GenerationJobBlocked,
    GenerationJobService,
)
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


def get_generation_backend(request: Request) -> GenerationBackend:
    backend = getattr(request.app.state, "generation_backend", None)
    if backend is None:
        raise RuntimeError("generation backend is not configured")
    return backend


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


def get_execution_service(
    request: Request,
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
    backend: GenerationBackend = Depends(get_generation_backend),
) -> GenerationExecutionService:
    return GenerationExecutionService(
        product_store,
        runtime_store,
        backend,
        asset_delivery=AssetDeliveryService(
            product_store,
            runtime_store,
            request.app.state.secret_store,
            public_base_url=request.app.state.settings.public_base_url,
        ),
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
            expected_chapter_id=chapter_id,
        )
    except GenerationJobBlocked as exc:
        return _error(409, "shot_prompt_blocked", str(exc))
    except GenerationInvalidRequest as exc:
        return _error(422, "invalid_request", str(exc))
    except GenerationIdempotencyConflict as exc:
        return _error(409, "idempotency_conflict", str(exc))
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


@router.post("/generation/jobs/{job_id}/refresh", response_model=GenerationJobRead)
async def refresh_generation_job(
    job_id: str,
    service: GenerationExecutionService = Depends(get_execution_service),
):
    try:
        return _job_read(service.refresh_job(job_id))
    except ValueError as exc:
        if str(exc) == "generation job not found":
            raise HTTPException(status_code=404, detail="generation job not found")
        return _error(409, "job_not_refreshable", str(exc))


@router.get("/chapters/{chapter_id}/results", response_model=list[ShotResultsRead])
async def list_chapter_results(
    chapter_id: str,
    product_store: ProductStore = Depends(get_product_store),
):
    jobs = product_store.list_generation_jobs_for_chapter(chapter_id)
    shot_ids = []
    for job in jobs:
        if job.shot_id not in shot_ids:
            shot_ids.append(job.shot_id)
    groups = []
    for shot_id in shot_ids:
        results = product_store.list_generation_results_for_shot(chapter_id, shot_id)
        if not results:
            continue
        selection = product_store.current_generation_result_selection(chapter_id, shot_id)
        groups.append(
            {
                "shot_id": shot_id,
                "current_result_id": "" if selection is None else selection.result_id,
                "results": [_result_read(product_store, result) for result in results],
            }
        )
    return groups


@router.post(
    "/shots/{shot_id}/results/{result_id}/select",
    response_model=ShotResultSelectionRead,
)
async def select_result(
    shot_id: str,
    result_id: str,
    product_store: ProductStore = Depends(get_product_store),
):
    result = product_store.get_generation_result(result_id)
    if result is None or result.shot_id != shot_id:
        raise HTTPException(status_code=404, detail="generation result not found")
    return product_store.select_generation_result(result.chapter_id, shot_id, result_id)


@router.post("/results/{result_id}/review", response_model=ResultReviewRead)
async def review_result(
    result_id: str,
    payload: ResultReviewCreate,
    product_store: ProductStore = Depends(get_product_store),
):
    if product_store.get_generation_result(result_id) is None:
        raise HTTPException(status_code=404, detail="generation result not found")
    return product_store.create_result_review(
        result_id=result_id,
        decision=payload.decision,
        failure_category=payload.failure_category,
        note=payload.note,
    )


@router.get("/results/{result_id}/content")
async def result_content(
    result_id: str,
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
):
    result = product_store.get_generation_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="generation result not found")
    if not result.object_id:
        return _error(409, "local_result_missing", "local result content is not available")
    return Response(
        content=runtime_store.read_bytes_object(result.object_id),
        media_type=result.media_type,
    )


@router.post("/generation/jobs/{job_id}/rerun", response_model=GenerationRerunRead)
async def rerun_generation_job(
    job_id: str,
    payload: GenerationRerunCreate,
    service: GenerationJobService = Depends(get_service),
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
):
    source = product_store.get_generation_job(job_id)
    if source is None:
        raise HTTPException(status_code=404, detail="generation job not found")
    overrides = _rerun_overrides(payload)
    try:
        new_job = service.queue_video_job(
            prompt_revision_id=source.prompt_revision_id,
            shot_id=source.shot_id,
            idempotency_key=payload.idempotency_key,
            explicit_rerun=True,
            overrides=overrides,
        )
    except GenerationJobBlocked as exc:
        return _error(409, "shot_prompt_blocked", str(exc))
    except GenerationInvalidRequest as exc:
        return _error(422, "invalid_request", str(exc))
    except GenerationIdempotencyConflict as exc:
        return _error(409, "idempotency_conflict", str(exc))
    except AssetDeliveryInvalidPublicBaseUrl:
        return _error(409, "input_unreachable", "public asset delivery URL is not provider reachable")
    rerun = product_store.create_rerun_record(
        source_job_id=source.job_id,
        new_job_id=new_job.job_id,
        overrides_object_id=runtime_store.write_text_object(
            json.dumps(
                overrides,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        ),
    )
    return {
        "rerun_id": rerun.rerun_id,
        "source_job_id": rerun.source_job_id,
        "new_job": _job_read(new_job),
        "created_at": rerun.created_at,
    }


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


def _result_read(product_store: ProductStore, result) -> dict:
    job = product_store.get_generation_job(result.job_id)
    return {
        "result_id": result.result_id,
        "job_id": result.job_id,
        "attempt_number": 0 if job is None else job.attempt_number,
        "media_type": result.media_type,
        "source_url": result.source_url,
        "source_url_state": result.source_url_state,
        "local_result_available": bool(result.object_id),
        "local_content_url": "" if not result.object_id else f"/api/results/{result.result_id}/content",
        "created_at": result.created_at,
    }


def _rerun_overrides(payload: GenerationRerunCreate) -> dict:
    overrides = {}
    if payload.prompt is not None:
        overrides["prompt"] = payload.prompt
    if payload.negative_prompt is not None:
        overrides["negative_prompt"] = payload.negative_prompt
    if payload.asset_ids is not None:
        overrides["asset_ids"] = list(payload.asset_ids)
    if payload.duration_seconds is not None:
        overrides["duration_seconds"] = payload.duration_seconds
    parameters = {}
    if payload.mode is not None:
        parameters["mode"] = payload.mode
    if payload.seed is not None:
        parameters["seed"] = payload.seed
    if parameters:
        overrides["parameters"] = parameters
    return overrides


def _error(status_code: int, error_code: str, error_message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "error_message": error_message},
    )
