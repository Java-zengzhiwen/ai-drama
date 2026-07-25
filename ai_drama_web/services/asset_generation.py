import base64
import json

import httpx

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.models import AssetRecord
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.models import ImageGenerationRequest
from ai_drama_web.schemas.assets import AssetGenerateImageRequest
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


class AssetGenerationResultMissing(Exception):
    pass


class AssetGenerationResultFetchFailed(Exception):
    pass


def asset_data_uri(media_type: str, data: bytes) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


class AssetGenerationService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        backend: GenerationBackend,
        m6_coordinator=None,
        supplier_execution_enabled: bool = False,
    ) -> None:
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.backend = backend
        self.m6_coordinator = m6_coordinator
        self.supplier_execution_enabled = supplier_execution_enabled

    def generate_image_asset(self, chapter_id: str, request: AssetGenerateImageRequest):
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord

        input_images = list(request.input_images)
        for asset_id in request.input_asset_ids:
            input_asset = self.product_store.get_asset(asset_id)
            if (
                input_asset is None
                or input_asset.project_id != chapter.project_id
                or input_asset.chapter_id != chapter.chapter_id
            ):
                raise MissingRecord
            input_images.append(asset_data_uri(input_asset.media_type, self.runtime_store.read_bytes_object(input_asset.object_id)))

        if self.supplier_execution_enabled:
            request_body = request.model_dump(exclude_none=True)
            request_body["input_images"] = input_images
            key = request.idempotency_key or __import__("hashlib").sha256(
                json.dumps(request_body, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            return self.m6_coordinator.generate_image(
                project_id=chapter.project_id,
                chapter_id=chapter.chapter_id,
                idempotency_key=key,
                request=request_body,
            )

        image_request = ImageGenerationRequest(
            prompt=request.prompt,
            size=request.size,
            input_images=input_images,
        )
        job = self.backend.create_image_job(image_request)
        result = self.backend.fetch_result(job.provider_job_id)
        result_content = result.content
        if result_content is None:
            result_content = self._download_result_content(result.url)

        metadata = dict(request.metadata)
        metadata.update(
            {
                "generation": {
                    "prompt": request.prompt,
                    "size": request.size,
                    "input_asset_ids": list(request.input_asset_ids),
                    "input_images": list(request.input_images),
                },
                "provider_job": {
                    "provider_job_id": job.provider_job_id,
                    "status": job.status,
                    "raw": job.raw,
                },
                "provider_result": {
                    "provider_job_id": result.provider_job_id,
                    "media_type": result.media_type,
                    "url": result.url,
                    "raw": result.raw,
                },
            }
        )
        return self._read_asset(
            self.product_store.create_generated_asset(
                project_id=chapter.project_id,
                chapter_id=chapter.chapter_id,
                asset_type=request.asset_type,
                name=request.name,
                data=result_content,
                media_type=result.media_type,
                source_job_id=result.provider_job_id,
                metadata=metadata,
            )
        )

    def _download_result_content(self, url: str) -> bytes:
        if not url:
            raise AssetGenerationResultMissing
        try:
            response = httpx.get(url, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AssetGenerationResultFetchFailed from exc
        if not response.content:
            raise AssetGenerationResultMissing
        return response.content

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
            "metadata": json.loads(self.runtime_store.read_text(record.metadata_object_id)),
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
