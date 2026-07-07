import json

import pytest

from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderJob
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
