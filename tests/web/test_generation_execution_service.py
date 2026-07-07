import json

import pytest

from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderJob, ProviderResult
from ai_drama_web.services.generation_execution import GenerationExecutionService

from test_generation_job_service import _ready_fixture


def test_submit_queued_video_job_sends_saved_request_and_persists_provider_job(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    backend = CapturingVideoBackend()

    submitted = GenerationExecutionService(store, runtime, backend).submit_queued_job(queued.job_id)

    assert submitted.internal_status == "submitted"
    assert submitted.provider_job_id == "video-provider-1"
    assert submitted.response_object_id
    assert backend.requests[0].prompt == "Shen Qinghe turns toward the lantern."
    assert backend.requests[0].negative_prompt == "warped face"
    assert backend.requests[0].duration_seconds == 5
    assert backend.requests[0].parameters == {"frame_rate": 24, "num_frames": 121}
    assert all(url.startswith("https://assets.example.test/public/assets/") for url in backend.requests[0].input_images)
    response = json.loads(runtime.read_text(submitted.response_object_id))
    assert response["provider"] == "fake-video"
    assert response["request_prompt"] == "Shen Qinghe turns toward the lantern."


def test_submit_queued_video_job_records_provider_error_without_leaking_raw_message(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )

    failed = GenerationExecutionService(store, runtime, FailingVideoBackend()).submit_queued_job(queued.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "provider_busy"
    assert failed.error_message == "video provider failed"
    assert "provider-secret" not in failed.error_message


def test_refresh_submitted_video_job_persists_completed_result(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    service = GenerationExecutionService(store, runtime, CompletingVideoBackend())
    submitted = service.submit_queued_job(queued.job_id)

    completed = service.refresh_job(submitted.job_id)

    assert completed.internal_status == "completed"
    assert completed.provider_result_id
    result = store.get_generation_result(completed.provider_result_id)
    assert result.job_id == completed.job_id
    assert result.shot_id == "SHOT_001"
    assert result.media_type == "video/mp4"
    assert result.source_url == "https://cdn.example.test/video.mp4"
    assert runtime.read_bytes_object(result.object_id) == b"mp4-bytes"
    metadata = json.loads(runtime.read_text(result.metadata_object_id))
    assert metadata["provider_result"]["provider_job_id"] == "video-provider-1"


def test_refresh_submitted_video_job_records_result_expired(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    service = GenerationExecutionService(store, runtime, ExpiredResultVideoBackend())
    submitted = service.submit_queued_job(queued.job_id)

    failed = service.refresh_job(submitted.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "result_expired"
    assert failed.error_message == "video provider failed"


def test_submit_queued_video_job_rejects_nonqueued_job(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    store.transition_generation_job(queued.job_id, "cancelled")

    with pytest.raises(ValueError, match="only queued jobs can be submitted"):
        GenerationExecutionService(store, runtime, CapturingVideoBackend()).submit_queued_job(queued.job_id)


class CapturingVideoBackend:
    def __init__(self):
        self.requests = []

    def create_video_job(self, request):
        self.requests.append(request)
        return ProviderJob(
            provider_job_id="video-provider-1",
            status="submitted",
            raw={
                "provider": "fake-video",
                "request_prompt": request.prompt,
            },
        )


class FailingVideoBackend:
    def create_video_job(self, request):
        raise ProviderError(
            "provider_busy",
            "provider-secret unavailable",
            provider="fake-video",
            raw={"provider-secret": "leak"},
        )


class CompletingVideoBackend(CapturingVideoBackend):
    def get_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="completed",
            raw={"provider": "fake-video", "status": "completed"},
        )

    def fetch_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url="https://cdn.example.test/video.mp4",
            content=b"mp4-bytes",
            raw={"provider": "fake-video", "url": "https://cdn.example.test/video.mp4"},
        )


class ExpiredResultVideoBackend(CapturingVideoBackend):
    def get_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="completed",
            raw={"provider": "fake-video", "status": "completed"},
        )

    def fetch_result(self, provider_job_id):
        raise ProviderError(
            "result_expired",
            "provider url expired",
            provider="fake-video",
            raw={"url": "https://cdn.example.test/expired.mp4"},
        )
