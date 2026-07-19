import asyncio
import json

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ai_drama_runtime.services import ApprovalBlocked, WorkflowGateError
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.config import Settings
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.schemas.workflows import (
    ErrorResponse,
    RevisionDecision,
    ScriptGenerationRequest,
    ScriptGenerationRunRead,
    ScriptRevisionRead,
    ScriptRevisionUpdate,
)
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.services.script_workflow import ScriptWorkflowService, WorkflowExecutionError
from ai_drama_web.store import ProductStore

router = APIRouter(prefix="/api")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repo_root(request: Request):
    return request.app.state.repo_root


def get_service(
    request: Request,
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
    settings: Settings = Depends(get_settings),
    repo_root=Depends(get_repo_root),
) -> ScriptWorkflowService:
    executor = request.app.state.m6_generation_coordinator if settings.m6_supplier_execution_enabled else None
    return ScriptWorkflowService(product_store, runtime_store, settings, repo_root, executor)


def _error(status_code: int, error_code: str, error_message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "error_message": error_message},
    )


@router.post(
    "/chapters/{chapter_id}/script/generate",
    response_model=ScriptRevisionRead,
    responses={409: {"model": ErrorResponse}},
)
async def generate_script(
    chapter_id: str,
    payload: ScriptGenerationRequest = Body(default_factory=ScriptGenerationRequest),
    service: ScriptWorkflowService = Depends(get_service),
):
    try:
        return service.generate_script(
            chapter_id,
            target_duration_minutes=payload.target_duration_minutes,
        )
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except WorkflowGateError as exc:
        return _error(409, exc.code, exc.safe_message)
    except WorkflowExecutionError as exc:
        return _error(exc.status_code, exc.code, exc.safe_message)


@router.post(
    "/chapters/{chapter_id}/script/generations",
    status_code=202,
    response_model=ScriptGenerationRunRead,
)
async def start_script_generation(
    chapter_id: str,
    request: Request,
    payload: ScriptGenerationRequest = Body(default_factory=ScriptGenerationRequest),
    idempotency_key: str = Header(alias="Idempotency-Key"),
    service: ScriptWorkflowService = Depends(get_service),
):
    if not request.app.state.settings.script_streaming_enabled:
        return _error(409, "SCRIPT_STREAMING_DISABLED", "script streaming is disabled")
    if not request.app.state.settings.m6_supplier_execution_enabled:
        return _error(
            409,
            "SCRIPT_STREAMING_RUNTIME_UNAVAILABLE",
            "streaming supplier runtime is unavailable",
        )
    try:
        return service.start_script_generation(
            chapter_id,
            idempotency_key=idempotency_key,
            target_duration_minutes=payload.target_duration_minutes,
        )
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")
    except WorkflowGateError as exc:
        return _error(409, exc.code, exc.safe_message)
    except WorkflowExecutionError as exc:
        return _error(exc.status_code, exc.code, exc.safe_message)


@router.get(
    "/script-generation-runs/{run_id}", response_model=ScriptGenerationRunRead
)
async def get_script_generation_run(
    run_id: str,
    product_store: ProductStore = Depends(get_product_store),
):
    run = product_store.get_script_generation_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="script generation run not found")
    return run


@router.get("/script-generation-runs/{run_id}/events")
async def stream_script_generation_events(
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    product_store: ProductStore = Depends(get_product_store),
):
    if product_store.get_script_generation_run(run_id) is None:
        raise HTTPException(status_code=404, detail="script generation run not found")

    async def event_stream():
        cursor = after_sequence
        heartbeat_at = asyncio.get_running_loop().time()
        while True:
            events = product_store.list_script_generation_events(
                run_id, after_sequence=cursor
            )
            for event in events:
                cursor = event["sequence"]
                payload = json.loads(
                    product_store.runtime.read_text(event["payload_object_id"])
                )
                data = {"sequence": cursor, **payload}
                yield (
                    f"id: {cursor}\n"
                    f"event: {event['event_type']}\n"
                    f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
                )
            current = product_store.get_script_generation_run(run_id)
            if current["status"] in {
                "completed",
                "failed",
                "unknown_outcome",
            }:
                return
            now = asyncio.get_running_loop().time()
            if now - heartbeat_at >= 15:
                yield ": heartbeat\n\n"
                heartbeat_at = now
            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chapters/{chapter_id}/script/revisions", response_model=list[ScriptRevisionRead])
async def list_script_revisions(chapter_id: str, service: ScriptWorkflowService = Depends(get_service)):
    try:
        return service.list_revisions(chapter_id)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="chapter not found")


@router.put("/script-revisions/{revision_id}", response_model=ScriptRevisionRead)
async def update_script_revision(
    revision_id: str,
    payload: ScriptRevisionUpdate,
    service: ScriptWorkflowService = Depends(get_service),
):
    try:
        return service.create_manual_revision(revision_id, payload.content)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="script revision not found")


@router.post(
    "/script-revisions/{revision_id}/approve",
    response_model=ScriptRevisionRead,
    responses={422: {"model": ErrorResponse}},
)
async def approve_script_revision(
    revision_id: str,
    payload: RevisionDecision = Body(default_factory=RevisionDecision),
    service: ScriptWorkflowService = Depends(get_service),
):
    try:
        return service.approve_revision(revision_id, payload.reviewer, payload.note)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="script revision not found")
    except ApprovalBlocked as exc:
        return _error(422, "APPROVAL_BLOCKED", str(exc))


@router.post("/script-revisions/{revision_id}/reject", response_model=ScriptRevisionRead)
async def reject_script_revision(
    revision_id: str,
    payload: RevisionDecision = Body(default_factory=RevisionDecision),
    service: ScriptWorkflowService = Depends(get_service),
):
    try:
        return service.reject_revision(revision_id, payload.reviewer, payload.note)
    except MissingRecord:
        raise HTTPException(status_code=404, detail="script revision not found")
