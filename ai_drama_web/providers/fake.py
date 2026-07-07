import hashlib
import json
from copy import deepcopy

from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.models import (
    ImageGenerationRequest,
    ProviderJob,
    ProviderResult,
    VideoGenerationRequest,
)


FAKE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class FakeGenerationBackend(GenerationBackend):
    def __init__(self) -> None:
        self._jobs: dict[str, ProviderJob] = {}

    def create_image_job(self, request: ImageGenerationRequest) -> ProviderJob:
        request_raw = {
            "prompt": request.prompt,
            "size": request.size,
            "input_images": list(request.input_images),
        }
        provider_job_id = self._image_job_id(request_raw)
        job = ProviderJob(
            provider_job_id=provider_job_id,
            status="succeeded",
            raw={
                "provider": "fake",
                "media_type": "image",
                "request": request_raw,
            },
        )
        self._jobs[provider_job_id] = _copy_job(job)
        return _copy_job(job)

    def create_video_job(self, request: VideoGenerationRequest) -> ProviderJob:
        raise NotImplementedError("fake backend does not support video generation")

    def get_job_status(self, provider_job_id: str) -> ProviderJob:
        try:
            return _copy_job(self._jobs[provider_job_id])
        except KeyError as exc:
            raise KeyError(f"unknown provider job id: {provider_job_id}") from exc

    def fetch_result(self, provider_job_id: str) -> ProviderResult:
        job = self.get_job_status(provider_job_id)
        if job.raw.get("media_type") != "image":
            raise ValueError(f"unsupported provider job media type: {job.raw.get('media_type')}")
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="image/png",
            url=f"fake://images/{provider_job_id}.png",
            content=FAKE_PNG_BYTES,
            raw={
                "provider": "fake",
                "media_type": "image/png",
                "source_job": deepcopy(job.raw),
            },
        )

    @staticmethod
    def _image_job_id(request_raw: dict) -> str:
        payload = json.dumps(request_raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"fake-image-{digest}"


def _copy_job(job: ProviderJob) -> ProviderJob:
    return ProviderJob(
        provider_job_id=job.provider_job_id,
        status=job.status,
        raw=deepcopy(job.raw),
    )
