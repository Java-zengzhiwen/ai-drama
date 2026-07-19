import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit

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
from ai_drama_web.suppliers.credentials import CredentialInUse
from ai_drama_web.suppliers.models import RevisionConflict
from ai_drama_web.suppliers.templates import custom_supplier_template


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
        replay = store.get_supplier_creation_request(idempotency_key)
        if replay:
            if replay["request_hash"] != body_hash:
                raise RevisionConflict("supplier creation idempotency conflict")
            supplier = store.get_supplier(replay["supplier_id"])
            response.status_code = 200
            return _supplier_read(request, supplier)
        source = custom_supplier_template(payload.slug, payload.display_name)
        artifact = compile_supplier(source, runtime_store=request.app.state.runtime_store)
        supplier, created = store.create_supplier_idempotent(
            slug=payload.slug,
            display_name=payload.display_name,
            idempotency_key=idempotency_key,
            request_hash=body_hash,
            initial_version={
                "source_object_id": artifact.source_object_id,
                "source_hash": artifact.source_hash,
                "compiled_artifact_object_id": artifact.compiled_artifact_object_id,
                "compiled_artifact_hash": artifact.compiled_artifact_hash,
                "manifest_hash": artifact.manifest_hash,
                "manifest": artifact.vendor,
                "adapter_contract_version": artifact.adapter_contract_version,
                "worker_protocol_version": "1",
                "worker_runtime_version": artifact.worker_runtime_version,
                "compiler_name": artifact.compiler_name,
                "compiler_version": artifact.compiler_version,
                "compiler_options_hash": artifact.compiler_options_hash,
                "helper_api_version": artifact.helper_api_version,
                "rate_limit_bucket_key": artifact.vendor["rateLimitBucketKey"],
            },
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
    supplier = _require_supplier(request, supplier_id)
    current_values = _current_config_object(request, supplier)
    current_values.update(payload.values)
    _validate_config_values(current_values, _current_manifest(request, supplier))
    normalized = json.dumps(current_values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
    force: bool = False,
):
    revision = _expected_revision(if_match, "credential")
    try:
        request.app.state.supplier_credential_store.delete(
            supplier_id, expected_revision=revision, force=force
        )
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    except CredentialInUse as exc:
        raise HTTPException(
            409,
            detail={
                "error_code": "CREDENTIAL_IN_USE",
                "active_job_count": exc.active_job_count,
            },
        ) from exc
    current_revision = request.app.state.product_store.get_supplier(
        supplier_id
    ).credential_revision
    response.headers["ETag"] = _etag("credential", current_revision)
    return {"configured": False, "masked_suffix": ""}


def _supplier_read(request, supplier):
    manifest = _current_manifest(request, supplier)
    config_values = _current_config_values(request, supplier)
    models = request.app.state.product_store.list_supplier_models(supplier.supplier_id)
    inputs = _safe_inputs(manifest.get("inputs"))
    input_values = _safe_string_map(manifest.get("inputValues"))
    capabilities = sorted(
        {
            revision.capability
            for model in models
            if (
                revision := request.app.state.product_store.get_supplier_model_revision(
                    model.current_model_revision_id
                )
            )
            is not None
        }
    )
    safe_manifest = {
        key: manifest[key]
        for key in (
            "id",
            "version",
            "name",
            "author",
            "adapterContractVersion",
            "helperApiVersion",
            "rateLimitBucketKey",
        )
        if isinstance(manifest.get(key), str)
    }
    if manifest:
        safe_manifest["inputs"] = inputs
        safe_manifest["inputValues"] = input_values
    return {
        **supplier.__dict__,
        "credential": _stored_credential_status(request, supplier),
        "credential_active_job_count": _credential_active_job_count(request, supplier),
        "author": str(manifest.get("author") or ""),
        "version": str(manifest.get("version") or ""),
        "manifest": safe_manifest,
        "inputs": inputs,
        "input_values": input_values,
        "config_values": config_values,
        "capabilities": capabilities,
        "model_count": len(models),
        "base_url_summary": _base_url_summary(config_values),
    }


def _current_manifest(request, supplier):
    if not supplier.current_supplier_version_id:
        return {}
    version = request.app.state.product_store.get_supplier_version(
        supplier.current_supplier_version_id
    )
    if version is None or not version.manifest_object_id:
        return {}
    return _read_json_object(request, version.manifest_object_id)


def _current_config_values(request, supplier):
    return _safe_string_map(_current_config_object(request, supplier))


def _current_config_object(request, supplier):
    if not supplier.current_config_revision_id:
        return {}
    revision = request.app.state.product_store.get_config_revision(
        supplier.current_config_revision_id
    )
    if revision is None or not revision.config_object_id:
        return {}
    return _read_json_object(request, revision.config_object_id)


def _read_json_object(request, object_id):
    try:
        value = json.loads(request.app.state.runtime_store.read_text(object_id))
    except (FileNotFoundError, OSError, RuntimeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


_SECRET_FIELD = re.compile(r"(?:api[_-]?key|credential|secret|password|bearer|token)", re.I)


def _is_secret_field(name):
    return bool(_SECRET_FIELD.search(str(name or "")))


def _safe_inputs(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        identity = item.get("name") or item.get("key") or item.get("id") or ""
        if _is_secret_field(identity) or item.get("secret") is True:
            continue
        result.append(
            {
                str(key): field_value
                for key, field_value in item.items()
                if str(key) not in {"value", "credential", "secret"}
                and not _is_secret_field(key)
                and isinstance(field_value, (str, int, float, bool, type(None), list, dict))
            }
        )
    return result


def _validate_config_values(values, manifest):
    inputs = manifest.get("inputs") if isinstance(manifest, dict) else []
    if not isinstance(inputs, list):
        return
    for field in inputs:
        if not isinstance(field, dict) or field.get("type") != "select":
            continue
        key = field.get("key") or field.get("name") or field.get("id")
        if not isinstance(key, str) or key not in values:
            continue
        options = field.get("options")
        allowed = {
            option.get("value")
            for option in options
            if isinstance(option, dict) and isinstance(option.get("value"), str)
        } if isinstance(options, list) else set()
        if values[key] not in allowed:
            raise HTTPException(
                422,
                detail={
                    "error_code": "INVALID_SUPPLIER_CONFIG_VALUE",
                    "field": key,
                },
            )


def _safe_string_map(value):
    if not isinstance(value, dict):
        return {}
    return {
        str(key): _strip_url_query(field_value)
        for key, field_value in value.items()
        if not _is_secret_field(key) and isinstance(field_value, str)
    }


def _strip_url_query(value):
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https"}:
        return value
    try:
        hostname = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return ""
    if not hostname:
        return ""
    safe_host = f"[{hostname}]" if ":" in hostname else hostname
    safe_netloc = f"{safe_host}:{port}" if port is not None else safe_host
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, "", ""))


def _base_url_summary(config_values):
    for key in ("base_url", "image_endpoint", "video_endpoint", "video_status_endpoint"):
        if config_values.get(key):
            return config_values[key][:240]
    return ""


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


def _credential_active_job_count(request, supplier):
    if not supplier.current_credential_version_id:
        return 0
    return len(
        request.app.state.supplier_credential_store.active_job_references(
            supplier.current_credential_version_id
        )
    ) + len(
        request.app.state.supplier_credential_store.active_model_test_references(
            supplier.current_credential_version_id
        )
    )


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
