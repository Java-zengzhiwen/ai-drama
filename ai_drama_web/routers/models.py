import json

from fastapi import APIRouter, Header, HTTPException, Request, Response

from ai_drama_runtime.services import NotFound
from ai_drama_web.schemas.models import SupplierModelCreate, SupplierModelPatch
from ai_drama_web.suppliers.model_catalog import ModelCatalogError, ModelCatalogService
from ai_drama_web.suppliers.models import RevisionConflict


router = APIRouter()


@router.get("/api/suppliers/{supplier_id}/models")
async def list_models(supplier_id: str, request: Request, response: Response):
    supplier = _supplier(request, supplier_id)
    response.headers["ETag"] = _catalog_etag(supplier.model_catalog_revision)
    return [_model_read(request, item) for item in request.app.state.product_store.list_supplier_models(supplier_id)]


@router.post("/api/suppliers/{supplier_id}/models")
async def create_model(
    supplier_id: str,
    payload: SupplierModelCreate,
    request: Request,
    response: Response,
    if_none_match: str | None = Header(default=None),
    if_match: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
):
    if if_none_match != "*" or not idempotency_key:
        _precondition_required()
    catalog_revision = _etag_revision(if_match, "model-catalog")
    _supplier(request, supplier_id)
    try:
        model, created = ModelCatalogService(request.app.state.product_store).create_overlay(
            supplier_id,
            **payload.model_dump(),
            expected_catalog_revision=catalog_revision,
            idempotency_key=idempotency_key,
        )
    except ModelCatalogError as exc:
        _catalog_error(exc)
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    response.status_code = 201 if created else 200
    _set_model_headers(response, request, model)
    return _model_read(request, model)


@router.get("/api/models/{supplier_model_id}")
async def get_model(supplier_model_id: str, request: Request, response: Response):
    model = _model(request, supplier_model_id)
    _set_model_headers(response, request, model)
    return _model_read(request, model)


@router.patch("/api/models/{supplier_model_id}")
async def patch_model(
    supplier_model_id: str,
    payload: SupplierModelPatch,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None),
):
    model = _model(request, supplier_model_id)
    model_revision = _etag_revision(if_match, "model-%s" % supplier_model_id)
    catalog_revision = _etag_revision(if_match, "model-catalog")
    catalog = ModelCatalogService(request.app.state.product_store)
    try:
        if payload.enabled is not None:
            updated = catalog.set_enabled(
                supplier_model_id,
                enabled=payload.enabled,
                expected_catalog_revision=catalog_revision,
                expected_model_revision=model_revision,
            )
        else:
            current = request.app.state.product_store.get_supplier_model_revision(
                model.current_model_revision_id
            )
            definition = json.loads(
                request.app.state.runtime_store.read_text(current.definition_object_id)
            )
            updated = catalog.revise_model(
                supplier_model_id,
                provider_model_name=payload.provider_model_name or current.provider_model_name,
                display_name=payload.display_name or current.display_name,
                capability=payload.capability or current.capability,
                definition=definition if payload.definition is None else payload.definition,
                expected_catalog_revision=catalog_revision,
                expected_model_revision=model_revision,
                acknowledged_binding_count=payload.acknowledged_binding_count,
            )
    except ModelCatalogError as exc:
        _catalog_error(exc)
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    _set_model_headers(response, request, updated)
    return _model_read(request, updated)


@router.delete("/api/models/{supplier_model_id}", status_code=204)
async def delete_model(
    supplier_model_id: str,
    request: Request,
    if_match: str | None = Header(default=None),
):
    _model(request, supplier_model_id)
    model_revision = _etag_revision(if_match, "model-%s" % supplier_model_id)
    catalog_revision = _etag_revision(if_match, "model-catalog")
    try:
        ModelCatalogService(request.app.state.product_store).delete_overlay(
            supplier_model_id,
            expected_catalog_revision=catalog_revision,
            expected_model_revision=model_revision,
        )
    except ModelCatalogError as exc:
        _catalog_error(exc)
    except RevisionConflict as exc:
        raise HTTPException(409, detail={"error_code": "REVISION_CONFLICT"}) from exc
    return Response(status_code=204)


def _model_read(request, model):
    revision = request.app.state.product_store.get_supplier_model_revision(
        model.current_model_revision_id
    )
    definition = json.loads(request.app.state.runtime_store.read_text(revision.definition_object_id))
    return {
        **model.__dict__,
        **revision.__dict__,
        "entity_revision": model.revision,
        "definition": definition,
        "binding_count": request.app.state.product_store.count_project_binding_references(
            model.supplier_model_id
        ),
    }


def _set_model_headers(response, request, model):
    supplier = request.app.state.product_store.get_supplier(model.supplier_id)
    response.headers["ETag"] = _model_etag(model.supplier_model_id, model.revision)
    response.headers["X-Model-Catalog-ETag"] = _catalog_etag(supplier.model_catalog_revision)


def _supplier(request, supplier_id):
    supplier = request.app.state.product_store.get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(404, detail={"error_code": "SUPPLIER_NOT_FOUND"})
    return supplier


def _model(request, supplier_model_id):
    model = request.app.state.product_store.get_supplier_model(supplier_model_id)
    if model is None:
        raise HTTPException(404, detail={"error_code": "MODEL_NOT_FOUND"})
    return model


def _etag_revision(header, prefix):
    if not header:
        _precondition_required()
    for token in header.split(","):
        value = token.strip().strip('"')
        marker = prefix + "-"
        if value.startswith(marker):
            try:
                return int(value.removeprefix(marker))
            except ValueError:
                break
    raise HTTPException(400, detail={"error_code": "INVALID_ETAG"})


def _precondition_required():
    raise HTTPException(428, detail={"error_code": "PRECONDITION_REQUIRED"})


def _catalog_error(exc):
    status = 404 if exc.code == "MODEL_NOT_FOUND" else 409
    raise HTTPException(status, detail={"error_code": exc.code}) from exc


def _model_etag(model_id, revision):
    return '"model-%s-%s"' % (model_id, revision)


def _catalog_etag(revision):
    return '"model-catalog-%s"' % revision
