import json

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import VideoGenerationRequest
from ai_drama_web.store import ProductStore


class GenerationExecutionService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        backend: GenerationBackend,
    ) -> None:
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.backend = backend

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
                    input_images=[asset["url"] for asset in request["assets"]],
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
