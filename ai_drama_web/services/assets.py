import json

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.models import AssetBindingRecord, AssetRecord
from ai_drama_web.schemas.assets import AssetUploadFields
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp"}
PROFILE_TARGET_TYPES = {"character", "scene", "prop"}


class AssetUnsupportedMediaType(Exception):
    pass


class AssetTooLarge(Exception):
    pass


class AssetRejectReasonRequired(Exception):
    pass


class AssetAdoptionNotAllowed(Exception):
    pass


class AssetService:
    def __init__(self, product_store: ProductStore, runtime_store: RuntimeStore, *, max_upload_bytes: int):
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.max_upload_bytes = max_upload_bytes

    def upload_asset(self, chapter_id: str, *, fields: AssetUploadFields, data: bytes, media_type: str):
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord
        if len(data) > self.max_upload_bytes:
            raise AssetTooLarge
        normalized_media_type = _normalize_media_type(media_type)
        if normalized_media_type not in ALLOWED_MEDIA_TYPES or not _bytes_match_media_type(data, normalized_media_type):
            raise AssetUnsupportedMediaType
        return self._read_asset(
            self.product_store.create_uploaded_asset(
                project_id=chapter.project_id,
                chapter_id=chapter.chapter_id,
                asset_type=fields.asset_type,
                name=fields.name,
                data=data,
                media_type=normalized_media_type,
                metadata=fields.metadata,
            )
        )

    def list_assets(self, chapter_id: str):
        if self.product_store.get_chapter(chapter_id) is None:
            raise MissingRecord
        return [self._read_asset(record) for record in self.product_store.list_assets_for_chapter(chapter_id)]

    def bind_asset(self, asset_id: str, data):
        asset = self.product_store.get_asset(asset_id)
        if asset is None:
            raise MissingRecord
        if data.is_current and asset.status != "usable":
            raise AssetAdoptionNotAllowed
        self._require_target_scope(asset, data.target_type, data.target_id)
        return self._read_binding(
            self.product_store.create_asset_binding(
                asset_id=asset.asset_id,
                target_type=data.target_type,
                target_id=data.target_id,
                role=data.role,
                is_current=data.is_current,
            )
        )

    def mark_usable(self, asset_id: str):
        return self._set_status(asset_id, "usable")

    def reject(self, asset_id: str, *, reason: str = ""):
        asset = self.product_store.get_asset(asset_id)
        if asset is None:
            raise MissingRecord
        rejection_reason = reason.strip()
        if (asset.status == "usable" or self.product_store.asset_has_current_binding(asset.asset_id)) and not rejection_reason:
            raise AssetRejectReasonRequired
        metadata = self._asset_metadata(asset)
        if rejection_reason:
            metadata["rejection_reason"] = rejection_reason
        updated = self.product_store.update_asset_status(asset_id, "rejected", metadata=metadata)
        if updated is None:
            raise MissingRecord
        self.product_store.clear_current_asset_bindings(asset_id)
        return self._read_asset(updated)

    def content(self, asset_id: str):
        asset = self.product_store.get_asset(asset_id)
        if asset is None:
            raise MissingRecord
        return self.runtime_store.read_bytes_object(asset.object_id), asset.media_type

    def _set_status(self, asset_id: str, status: str):
        updated = self.product_store.update_asset_status(asset_id, status)
        if updated is None:
            raise MissingRecord
        return self._read_asset(updated)

    def _require_target_scope(self, asset: AssetRecord, target_type: str, target_id: str):
        if target_type == "shot":
            raise MissingRecord
        if target_type not in PROFILE_TARGET_TYPES:
            return
        profile = self.product_store.get_production_profile(target_id)
        if profile is None or profile.profile_type != target_type:
            raise MissingRecord
        if profile.project_id != asset.project_id:
            raise MissingRecord
        if profile.chapter_id and profile.chapter_id != asset.chapter_id:
            raise MissingRecord

    def _read_asset(self, record: AssetRecord):
        return {
            "asset_id": record.asset_id,
            "project_id": record.project_id,
            "chapter_id": record.chapter_id,
            "asset_type": record.asset_type,
            "name": record.name,
            "object_id": record.object_id,
            "media_type": record.media_type,
            "width": record.width,
            "height": record.height,
            "status": record.status,
            "source_type": record.source_type,
            "source_job_id": record.source_job_id,
            "metadata": self._asset_metadata(record),
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def _read_binding(self, record: AssetBindingRecord):
        return {
            "binding_id": record.binding_id,
            "asset_id": record.asset_id,
            "target_type": record.target_type,
            "target_id": record.target_id,
            "role": record.role,
            "is_current": bool(record.is_current),
            "created_at": record.created_at,
        }

    def _asset_metadata(self, record: AssetRecord):
        return json.loads(self.runtime_store.read_text(record.metadata_object_id))


def _normalize_media_type(media_type: str) -> str:
    return media_type.split(";", 1)[0].strip().lower()


def _bytes_match_media_type(data: bytes, media_type: str) -> bool:
    if media_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if media_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False
