import json

from pydantic import ValidationError

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.models import ProductionProfileRecord
from ai_drama_web.schemas.profiles import validate_profile_payload
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


class ProfileValidationError(Exception):
    pass


class ProductionProfileService:
    def __init__(self, product_store: ProductStore, runtime_store: RuntimeStore):
        self.product_store = product_store
        self.runtime_store = runtime_store

    def create_profile(self, project_id, data):
        self._require_project(project_id)
        self._require_chapter_scope(project_id, data.chapter_id)
        return self._read(
            self.product_store.create_production_profile(
                project_id=project_id,
                chapter_id=data.chapter_id,
                profile_type=data.profile_type,
                name=data.payload["name"],
                payload=data.payload,
            )
        )

    def list_profiles(self, project_id, *, chapter_id=None, profile_type=None):
        self._require_project(project_id)
        if chapter_id is not None:
            self._require_chapter_scope(project_id, chapter_id)
        return [
            self._read(record)
            for record in self.product_store.list_production_profiles(
                project_id,
                chapter_id=chapter_id,
                profile_type=profile_type,
            )
        ]

    def update_profile(self, profile_id, data):
        existing = self.product_store.get_production_profile(profile_id)
        if existing is None:
            raise MissingRecord
        try:
            payload = validate_profile_payload(existing.profile_type, data.payload)
        except (KeyError, ValidationError, ValueError) as exc:
            raise ProfileValidationError from exc
        updated = self.product_store.update_production_profile_payload(
            profile_id,
            name=payload["name"],
            payload=payload,
        )
        if updated is None:
            raise MissingRecord
        return self._read(updated)

    def delete_profile(self, profile_id):
        if not self.product_store.delete_production_profile(profile_id):
            raise MissingRecord

    def _require_project(self, project_id):
        if self.product_store.get_project(project_id) is None:
            raise MissingRecord

    def _require_chapter_scope(self, project_id, chapter_id):
        if not chapter_id:
            return
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise MissingRecord

    def _read(self, record: ProductionProfileRecord):
        return {
            "profile_id": record.profile_id,
            "project_id": record.project_id,
            "chapter_id": record.chapter_id,
            "profile_type": record.profile_type,
            "name": record.name,
            "payload": json.loads(self.runtime_store.read_text(record.payload_object_id)),
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
