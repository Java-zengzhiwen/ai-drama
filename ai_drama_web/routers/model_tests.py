from fastapi import APIRouter, Header, HTTPException, Request, Response

from ai_drama_web.schemas.model_tests import (
    ModelTestCreate,
    ModelTestFeatureStatus,
    ModelTestRead,
)
from ai_drama_web.suppliers.model_tests import ModelTestError, ModelTestService
from ai_drama_web.suppliers.models import RevisionConflict


router = APIRouter()


@router.get("/api/model-tests/status", response_model=ModelTestFeatureStatus)
async def feature_status(request: Request):
    return {"enabled": bool(request.app.state.model_tests_enabled)}


@router.post(
    "/api/models/{supplier_model_id}/tests",
    response_model=ModelTestRead,
    status_code=202,
)
async def create_model_test(
    supplier_model_id: str,
    payload: ModelTestCreate,
    request: Request,
    if_match: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
):
    if not request.app.state.model_tests_enabled:
        raise HTTPException(409, detail={"error_code": "MODEL_TESTS_DISABLED"})
    if not idempotency_key:
        raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})
    revision = _model_revision(if_match, supplier_model_id)
    service = ModelTestService(request.app.state.product_store)
    try:
        run, _created = service.create_model_test(
            supplier_model_id=supplier_model_id,
            prompt=payload.prompt,
            reasoning_effort=payload.reasoning_effort,
            size=payload.size,
            quality=payload.quality,
            idempotency_key=idempotency_key,
            expected_model_revision=revision,
        )
    except RevisionConflict as exc:
        code = "IDEMPOTENCY_CONFLICT" if "IDEMPOTENCY" in str(exc) else "REVISION_CONFLICT"
        raise HTTPException(409, detail={"error_code": code}) from exc
    except ModelTestError as exc:
        _model_test_error(exc)
    request.app.state.model_test_runner.wake()
    return service.safe_read(run["test_run_id"])


@router.get(
    "/api/models/{supplier_model_id}/tests/by-idempotency-key",
    response_model=ModelTestRead,
)
async def recover_model_test(
    supplier_model_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None),
):
    if not idempotency_key:
        raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})
    try:
        return ModelTestService(request.app.state.product_store).safe_read_by_key(
            supplier_model_id, idempotency_key
        )
    except ModelTestError as exc:
        _model_test_error(exc)


@router.get("/api/model-tests/{test_run_id}", response_model=ModelTestRead)
async def get_model_test(test_run_id: str, request: Request):
    try:
        return ModelTestService(request.app.state.product_store).safe_read(test_run_id)
    except ModelTestError as exc:
        _model_test_error(exc)


@router.get("/api/model-tests/{test_run_id}/content")
async def get_model_test_content(test_run_id: str, request: Request):
    run = request.app.state.product_store.get_supplier_model_test_run(test_run_id)
    if run is None:
        raise HTTPException(404, detail={"error_code": "MODEL_TEST_NOT_FOUND"})
    if (
        run["status"] != "completed"
        or run["capability"] != "image"
        or not run["content_object_id"]
        or not run["media_type"].startswith("image/")
    ):
        raise HTTPException(404, detail={"error_code": "MODEL_TEST_CONTENT_NOT_FOUND"})
    content = request.app.state.runtime_store.read_bytes_object(run["content_object_id"])
    return Response(
        content=content,
        media_type=run["media_type"],
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(len(content)),
        },
    )


def _model_revision(header, model_id):
    if not header:
        raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})
    expected = '"model-%s-' % model_id
    if not header.startswith(expected) or not header.endswith('"'):
        raise HTTPException(400, detail={"error_code": "INVALID_ETAG"})
    try:
        return int(header[len(expected) : -1])
    except ValueError as exc:
        raise HTTPException(400, detail={"error_code": "INVALID_ETAG"}) from exc


def _model_test_error(exc):
    if exc.code in {"MODEL_NOT_FOUND", "MODEL_TEST_NOT_FOUND"}:
        status = 404
    elif exc.code in {
        "INVALID_REASONING_EFFORT",
        "INVALID_IMAGE_SIZE",
        "INVALID_IMAGE_QUALITY",
        "MODEL_TEST_REASONING_UNSUPPORTED",
        "MODEL_TEST_IMAGE_OPTIONS_UNSUPPORTED",
    }:
        status = 422
    else:
        status = 409
    raise HTTPException(
        status,
        detail={"error_code": exc.code, "error_message": _safe_message(exc.code)},
    ) from exc


def _safe_message(code):
    messages = {
        "MODEL_TEST_CAPABILITY_UNSUPPORTED": "当前阶段仅支持测试文本和图片模型。",
        "MODEL_TEST_PROMPT_INVALID": "测试提示词为空或超过长度限制。",
        "SUPPLIER_DISABLED": "供应商已停用。",
        "MODEL_DISABLED": "模型已停用。",
        "CREDENTIAL_MISSING": "请先配置供应商密钥。",
        "CREDENTIAL_STORAGE_CORRUPT": "供应商密钥存储异常。",
        "SUPPLIER_OPERATION_UNAVAILABLE": "适配代码未导出该模型能力。",
        "SUPPLIER_RUNTIME_UNAVAILABLE": "供应商运行时不可用。",
        "INVALID_REASONING_EFFORT": "当前模型不支持所选思考深度。",
        "INVALID_IMAGE_SIZE": "当前图片模型不支持所选尺寸。",
        "INVALID_IMAGE_QUALITY": "当前图片模型不支持所选质量。",
        "MODEL_TEST_REASONING_UNSUPPORTED": "当前模型能力不支持思考深度。",
        "MODEL_TEST_IMAGE_OPTIONS_UNSUPPORTED": "当前模型能力不支持图片尺寸或质量。",
    }
    return messages.get(code, "模型测试无法启动。")
