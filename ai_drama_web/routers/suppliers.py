import hashlib
import json

from fastapi import APIRouter, Header, HTTPException, Request, Response

from ai_drama_runtime.services import NotFound
from ai_drama_web.schemas.suppliers import (
    SupplierCodeUpdate,
    SupplierConfigUpdate,
    SupplierCreate,
    SupplierSecretUpdate,
    SupplierUpdate,
)
from ai_drama_web.suppliers.compiler import SupplierCompileError, compile_supplier
from ai_drama_web.suppliers.models import RevisionConflict


router = APIRouter(prefix="/api/suppliers")


@router.get("")
async def list_suppliers(request: Request):
    return [_supplier_read(request, item) for item in request.app.state.product_store.list_suppliers()]


@router.post("")
async def create_supplier(
    payload: SupplierCreate,
    request: Request,
    response: Response,
    if_none_match: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
):
    if if_none_match != "*" or not idempotency_key:
        raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})
    body_hash = _hash(payload.model_dump())
    store = request.app.state.product_store
    try:
        supplier, created = store.create_supplier_idempotent(
            slug=payload.slug,
            display_name=payload.display_name,
            idempotency_key=idempotency_key,
            request_hash=body_hash,
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "IDEMPOTENCY_CONFLICT"}) from exc
    except ValueError as exc:
        raise HTTPException(409, detail={"error_code": "SUPPLIER_SLUG_CONFLICT"}) from exc
    response.status_code = 201 if created else 200
    return _supplier_read(request, supplier)


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: str, request: Request, response: Response):
    supplier = _require_supplier(request, supplier_id)
    response.headers["ETag"] = _etag("supplier", supplier.revision)
    return _supplier_read(request, supplier)


@router.patch("/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match, "supplier")
    try:
        supplier = request.app.state.product_store.update_supplier(
            supplier_id,
            display_name=payload.display_name,
            enabled=payload.enabled,
            expected_revision=revision,
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    response.headers["ETag"] = _etag("supplier", supplier.revision)
    return _supplier_read(request, supplier)


@router.get("/{supplier_id}/code")
async def get_supplier_code(supplier_id: str, request: Request):
    supplier = _require_supplier(request, supplier_id)
    if not supplier.current_supplier_version_id:
        return {"source": "", "supplier_version_id": ""}
    version = request.app.state.product_store.get_supplier_version(
        supplier.current_supplier_version_id
    )
    return {
        "source": request.app.state.runtime_store.read_text(version.source_object_id),
        "supplier_version_id": version.supplier_version_id,
    }


@router.put("/{supplier_id}/code")
async def put_supplier_code(
    supplier_id: str,
    payload: SupplierCodeUpdate,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match, "supplier")
    try:
        artifact = compile_supplier(payload.source, runtime_store=request.app.state.runtime_store)
        version = request.app.state.product_store.replace_supplier_version(
            supplier_id,
            source_object_id=artifact.source_object_id,
            source_hash=artifact.source_hash,
            compiled_artifact_object_id=artifact.compiled_artifact_object_id,
            compiled_artifact_hash=artifact.compiled_artifact_hash,
            manifest_hash=artifact.manifest_hash,
            manifest=artifact.vendor,
            adapter_contract_version=artifact.adapter_contract_version,
            worker_protocol_version="1",
            worker_runtime_version=artifact.worker_runtime_version,
            compiler_name=artifact.compiler_name,
            compiler_version=artifact.compiler_version,
            compiler_options_hash=artifact.compiler_options_hash,
            helper_api_version=artifact.helper_api_version,
            rate_limit_bucket_key=artifact.vendor["rateLimitBucketKey"],
            expected_revision=revision,
        )
    except SupplierCompileError as exc:
        raise HTTPException(
            422,
            detail={
                "error_code": exc.code,
                "error_message": exc.message,
                "line": exc.line,
                "column": exc.column,
            },
        ) from exc
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    response.headers["ETag"] = _etag("supplier", version.revision)
    return {
        "supplier_version_id": version.supplier_version_id,
        "source_hash": version.source_hash,
        "compiled_artifact_hash": version.compiled_artifact_hash,
        "manifest_hash": version.manifest_hash,
        "compiler_name": artifact.compiler_name,
        "compiler_version": artifact.compiler_version,
    }


@router.post("/{supplier_id}/restore-built-in")
async def restore_builtin(
    supplier_id: str,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match, "supplier")
    try:
        supplier = request.app.state.product_store.restore_builtin_supplier_version(
            supplier_id, expected_revision=revision
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    except NotFound as exc:
        raise HTTPException(409, detail={"error_code": "BUILTIN_VERSION_MISSING"}) from exc
    response.headers["ETag"] = _etag("supplier", supplier.revision)
    return _supplier_read(request, supplier)


@router.put("/{supplier_id}/config")
async def put_supplier_config(
    supplier_id: str,
    payload: SupplierConfigUpdate,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match, "config")
    normalized = json.dumps(payload.values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    object_id = request.app.state.runtime_store.write_text_object(normalized)
    try:
        record = request.app.state.product_store.replace_supplier_config(
            supplier_id,
            config_object_id=object_id,
            config_hash=hashlib.sha256(normalized.encode()).hexdigest(),
            expected_revision=revision,
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    response.headers["ETag"] = _etag("config", record.revision)
    return {"config_revision_id": record.config_revision_id, "revision": record.revision}


@router.put("/{supplier_id}/secret")
async def put_supplier_secret(
    supplier_id: str,
    payload: SupplierSecretUpdate,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match, "credential")
    try:
        record = request.app.state.supplier_credential_store.replace(
            supplier_id, payload.credential, expected_revision=revision
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    response.headers["ETag"] = _etag("credential", record.revision)
    return _credential_status(payload.credential)


@router.delete("/{supplier_id}/secret")
async def delete_supplier_secret(
    supplier_id: str,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    revision = _expected_revision(if_match, "credential")
    try:
        request.app.state.supplier_credential_store.delete(
            supplier_id, expected_revision=revision
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    current_revision = request.app.state.product_store.get_supplier(
        supplier_id
    ).credential_revision
    response.headers["ETag"] = _etag("credential", current_revision)
    return {"configured": False, "masked_suffix": ""}


def _supplier_read(request, supplier):
    return {
        **supplier.__dict__,
        "credential": _stored_credential_status(request, supplier),
    }


def _stored_credential_status(request, supplier):
    if not supplier.current_credential_version_id:
        return {"configured": False, "masked_suffix": ""}
    try:
        value = request.app.state.supplier_credential_store.read(
            supplier.current_credential_version_id
        )
    except RuntimeError:
        return {"configured": True, "masked_suffix": ""}
    return _credential_status(value)


def _credential_status(value):
    return {"configured": True, "masked_suffix": value[-4:] if len(value) > 4 else ""}


def _require_supplier(request, supplier_id):
    supplier = request.app.state.product_store.get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(404, detail={"error_code": "SUPPLIER_NOT_FOUND"})
    return supplier


def _expected_revision(header, prefix):
    if not header:
        raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})
    expected = header.strip('"').removeprefix(prefix + "-")
    try:
        return int(expected)
    except ValueError as exc:
        raise HTTPException(400, detail={"error_code": "INVALID_ETAG"}) from exc


def _etag(prefix, revision):
    return '"%s-%s"' % (prefix, revision)


def _hash(value):
    normalized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode()).hexdigest()
