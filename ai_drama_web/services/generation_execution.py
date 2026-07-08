import json

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import VideoGenerationRequest
from ai_drama_web.services.asset_delivery import AssetDeliveryInvalidPublicBaseUrl, AssetDeliveryService
from ai_drama_web.store import ProductStore


class GenerationExecutionService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        backend: GenerationBackend,
        *,
        asset_delivery: AssetDeliveryService | None = None,
    ) -> None:
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.backend = backend
        self.asset_delivery = asset_delivery

    def submit_queued_job(self, job_id: str):
        job = self.product_store.get_generation_job(job_id)
        if job is None:
            raise ValueError("generation job not found")
        if job.internal_status != "queued":
            raise ValueError("only queued jobs can be submitted")
        submitting = self.product_store.transition_generation_job(job.job_id, "submitting")
        request = json.loads(self.runtime_store.read_text(submitting.request_object_id))
        try:
            provider_job = self.backend.create_video_job(
                VideoGenerationRequest(
                    prompt=request["prompt"],
                    negative_prompt=request.get("negative_prompt", ""),
                    duration_seconds=request["duration_seconds"],
                    input_images=self._materialize_asset_urls(request),
                    parameters=dict(request.get("parameters") or {}),
                )
            )
        except ProviderError as exc:
            return self.product_store.transition_generation_job(
                submitting.job_id,
                "failed",
                error_code=exc.code,
                error_message="video provider failed",
            )
        except AssetDeliveryInvalidPublicBaseUrl:
            return self.product_store.transition_generation_job(
                submitting.job_id,
                "failed",
                error_code="input_unreachable",
                error_message="video input asset is not provider reachable",
            )
        except Exception:
            return self.product_store.transition_generation_job(
                submitting.job_id,
                "failed",
                error_code="unknown_provider_error",
                error_message="video provider failed",
            )
        response_object_id = self.runtime_store.write_text_object(
            json.dumps(
                provider_job.raw,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        return self.product_store.attach_generation_provider_job(
            submitting.job_id,
            provider_job_id=provider_job.provider_job_id,
            response_object_id=response_object_id,
        )

    def refresh_job(self, job_id: str):
        job = self.product_store.get_generation_job(job_id)
        if job is None:
            raise ValueError("generation job not found")
        if job.internal_status == "queued":
            return job
        if job.internal_status in {"completed", "failed", "cancelled"}:
            return job
        if job.internal_status not in {"submitted", "polling"}:
            raise ValueError("generation job is not refreshable")
        try:
            if job.job_type == "video":
                provider_job = self.backend.get_video_job_status(job.provider_job_id)
            else:
                provider_job = self.backend.get_job_status(job.provider_job_id)
            if provider_job.status in {"submitted", "queued"}:
                return job
            if provider_job.status in {"polling", "processing", "running", "in_progress"}:
                return self.product_store.transition_generation_job(job.job_id, "polling")
            if provider_job.status == "failed":
                return self.product_store.transition_generation_job(
                    job.job_id,
                    "failed",
                    error_code="generation_failed",
                    error_message="video provider failed",
                )
            if provider_job.status != "completed":
                return self.product_store.transition_generation_job(
                    job.job_id,
                    "failed",
                    error_code="unknown_provider_error",
                    error_message="video provider failed",
                )
            if job.job_type == "video":
                result = self.backend.fetch_video_result(job.provider_job_id)
            else:
                result = self.backend.fetch_result(job.provider_job_id)
        except ProviderError as exc:
            return self.product_store.transition_generation_job(
                job.job_id,
                "failed",
                error_code=exc.code,
                error_message="video provider failed",
            )
        object_id = ""
        if result.content is not None:
            object_id = self.runtime_store.write_bytes_object(result.content)
        else:
            return self.product_store.transition_generation_job(
                job.job_id,
                "failed",
                error_code="result_expired",
                error_message="video provider failed",
            )
        metadata_object_id = self.runtime_store.write_text_object(
            json.dumps(
                {
                    "provider_job": provider_job.raw,
                    "provider_result": {
                        "provider_job_id": result.provider_job_id,
                        "media_type": result.media_type,
                        "url": result.url,
                        "raw": result.raw,
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        return self.product_store.complete_generation_job_with_result(
            job_id=job.job_id,
            object_id=object_id,
            media_type=result.media_type,
            source_url=result.url,
            source_url_state="source_url_active",
            metadata_object_id=metadata_object_id,
        )

    def _materialize_asset_urls(self, request: dict) -> list[str]:
        if "assets" in request:
            return [asset["url"] for asset in request["assets"]]
        asset_ids = request.get("asset_ids") or []
        if self.asset_delivery is None:
            return [str(asset_id) for asset_id in asset_ids]
        return [self.asset_delivery.signed_asset_url(str(asset_id)) for asset_id in asset_ids]
