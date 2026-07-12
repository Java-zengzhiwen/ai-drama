import hashlib
import json
import uuid

from .models import RevisionConflict


class ModelCatalogError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class ModelCatalogService:
    def __init__(self, store):
        self.store = store

    def list_models(self, supplier_id):
        return self.store.list_supplier_models(supplier_id)

    def create_overlay(
        self,
        supplier_id,
        *,
        provider_model_name,
        display_name,
        capability,
        definition,
        expected_catalog_revision,
        idempotency_key,
    ):
        body = {
            "provider_model_name": provider_model_name,
            "display_name": display_name,
            "capability": capability,
            "definition": definition,
        }
        request_hash = hashlib.sha256(
            json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        replay = self.store.conn.execute(
            "SELECT * FROM model_creation_requests WHERE supplier_id = ? AND idempotency_key = ?",
            (supplier_id, idempotency_key),
        ).fetchone()
        if replay:
            if replay["request_hash"] != request_hash:
                raise ModelCatalogError("IDEMPOTENCY_CONFLICT")
            return self.store.get_supplier_model(replay["supplier_model_id"]), False
        self._reject_active_duplicate(supplier_id, capability, provider_model_name)
        try:
            return self.store.create_supplier_model_idempotent(
                supplier_id,
                supplier_model_id=uuid.uuid4().hex,
                source="overlay",
                provider_model_name=provider_model_name,
                display_name=display_name,
                capability=capability,
                definition=definition,
                expected_catalog_revision=expected_catalog_revision,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        except RevisionConflict as exc:
            if "idempotency" in str(exc):
                raise ModelCatalogError("IDEMPOTENCY_CONFLICT") from exc
            raise

    def revise_model(
        self,
        supplier_model_id,
        *,
        provider_model_name,
        display_name,
        capability,
        definition,
        expected_catalog_revision,
        expected_model_revision,
        acknowledged_binding_count,
    ):
        model = self._model(supplier_model_id)
        actual = self.store.count_model_references(supplier_model_id)
        if actual != acknowledged_binding_count:
            raise ModelCatalogError("AFFECTED_BINDING_ACK_REQUIRED")
        if model.enabled:
            self._reject_active_duplicate(
                model.supplier_id, capability, provider_model_name, exclude_id=supplier_model_id
            )
        return self.store.revise_supplier_model(
            supplier_model_id,
            provider_model_name=provider_model_name,
            display_name=display_name,
            capability=capability,
            definition=definition,
            expected_catalog_revision=expected_catalog_revision,
            expected_model_revision=expected_model_revision,
        )

    def set_enabled(
        self, supplier_model_id, *, enabled, expected_catalog_revision, expected_model_revision
    ):
        model = self._model(supplier_model_id)
        if enabled:
            revision = self.store.get_supplier_model_revision(model.current_model_revision_id)
            self._reject_active_duplicate(
                model.supplier_id,
                revision.capability,
                revision.provider_model_name,
                exclude_id=supplier_model_id,
            )
        return self.store.set_supplier_model_enabled(
            supplier_model_id,
            enabled=enabled,
            expected_catalog_revision=expected_catalog_revision,
            expected_model_revision=expected_model_revision,
        )

    def delete_overlay(
        self, supplier_model_id, *, expected_catalog_revision, expected_model_revision
    ):
        model = self._model(supplier_model_id)
        if model.source == "built_in":
            raise ModelCatalogError("BUILT_IN_MODEL_DELETE_FORBIDDEN")
        if self.store.count_model_references(supplier_model_id):
            raise ModelCatalogError("MODEL_REFERENCED")
        self.store.delete_supplier_model(
            supplier_model_id,
            expected_catalog_revision=expected_catalog_revision,
            expected_model_revision=expected_model_revision,
        )

    def _model(self, supplier_model_id):
        model = self.store.get_supplier_model(supplier_model_id)
        if model is None:
            raise ModelCatalogError("MODEL_NOT_FOUND")
        return model

    def _reject_active_duplicate(
        self, supplier_id, capability, provider_model_name, *, exclude_id=""
    ):
        if self.store.find_active_model_name(
            supplier_id, capability, provider_model_name, exclude_id=exclude_id
        ):
            raise ModelCatalogError("MODEL_NAME_CONFLICT")
