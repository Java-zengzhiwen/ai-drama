import pytest

from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.providers.models import (
    ImageGenerationRequest,
    ProviderJob,
    ProviderResult,
    VideoGenerationRequest,
)


def test_create_image_job_records_succeeded_status_with_stable_id():
    backend = FakeGenerationBackend()
    request = ImageGenerationRequest(
        prompt="沈清荷 standing in the Shen residence hall",
        size="1024x1024",
        input_images=["asset://primary-reference"],
    )

    job = backend.create_image_job(request)
    duplicate_job = backend.create_image_job(request)
    status = backend.get_job_status(job.provider_job_id)

    assert isinstance(job, ProviderJob)
    assert job.provider_job_id.startswith("fake-image-")
    assert duplicate_job.provider_job_id == job.provider_job_id
    assert status == job
    assert job.status == "succeeded"
    assert job.raw == {
        "provider": "fake",
        "media_type": "image",
        "request": {
            "prompt": "沈清荷 standing in the Shen residence hall",
            "size": "1024x1024",
            "input_images": ["asset://primary-reference"],
        },
    }


def test_fetch_result_returns_png_bytes_and_raw_metadata_for_image_job():
    backend = FakeGenerationBackend()
    request = ImageGenerationRequest(prompt="empty courtyard", size="512x512")
    job = backend.create_image_job(request)

    result = backend.fetch_result(job.provider_job_id)

    assert isinstance(result, ProviderResult)
    assert result.provider_job_id == job.provider_job_id
    assert result.media_type == "image/png"
    assert result.url == f"fake://images/{job.provider_job_id}.png"
    assert result.content is not None
    assert result.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert result.raw == {
        "provider": "fake",
        "media_type": "image/png",
        "source_job": job.raw,
    }


def test_returned_raw_metadata_cannot_mutate_backend_state():
    backend = FakeGenerationBackend()
    job = backend.create_image_job(ImageGenerationRequest(prompt="portrait", size="512x512"))

    job.raw["media_type"] = "video"
    status = backend.get_job_status(job.provider_job_id)
    result = backend.fetch_result(job.provider_job_id)
    result.raw["source_job"]["media_type"] = "video"

    assert status.raw["media_type"] == "image"
    assert backend.get_job_status(job.provider_job_id).raw["media_type"] == "image"
    assert backend.fetch_result(job.provider_job_id).raw["source_job"]["media_type"] == "image"


def test_unknown_job_ids_raise_clear_errors():
    backend = FakeGenerationBackend()

    with pytest.raises(KeyError, match="unknown provider job id: missing-job"):
        backend.get_job_status("missing-job")

    with pytest.raises(KeyError, match="unknown provider job id: missing-job"):
        backend.fetch_result("missing-job")


def test_create_video_job_records_video_and_explicit_video_result():
    backend = FakeGenerationBackend()
    request = VideoGenerationRequest(
        prompt="slow push-in on the family hall",
        duration_seconds=5,
        input_images=["asset://scene-reference"],
        negative_prompt="text overlays",
        parameters={"camera": "push-in"},
    )

    job = backend.create_video_job(request)
    status = backend.get_video_job_status(job.provider_job_id)
    result = backend.fetch_video_result(job.provider_job_id)

    assert job.provider_job_id.startswith("fake-video-")
    assert status.status == "completed"
    assert result.media_type == "video/mp4"
    assert result.content == b"fake-mp4-bytes"
