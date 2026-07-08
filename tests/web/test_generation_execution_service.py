import json

import pytest

from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderJob, ProviderResult
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import AssetDeliveryService
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

    submitted = _execution_service(tmp_path, runtime, store, backend).submit_queued_job(queued.job_id)

    assert submitted.internal_status == "submitted"
    assert submitted.provider_job_id == "video-provider-1"
    assert submitted.response_object_id
    assert backend.requests[0].prompt == "Shen Qinghe turns toward the lantern."
    assert backend.requests[0].negative_prompt == "warped face"
    assert backend.requests[0].duration_seconds == 5
    assert backend.requests[0].parameters == {"num_frames": 121}
    assert all(url.startswith("https://assets.example.test/public/assets/") for url in backend.requests[0].input_images)
    persisted_request = json.loads(runtime.read_text(queued.request_object_id))
    assert "url" not in json.dumps(persisted_request)
    response = json.loads(runtime.read_text(submitted.response_object_id))
    assert response["provider"] == "fake-video"
    assert response["request_prompt"] == "Shen Qinghe turns toward the lantern."


def test_execution_materializes_fresh_signed_urls(tmp_path, monkeypatch):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="fresh-url",
    )
    backend = CapturingVideoBackend()
    monkeypatch.setattr("ai_drama_web.services.asset_delivery.time.time", lambda: 100)

    _execution_service(tmp_path, runtime, store, backend).submit_queued_job(queued.job_id)

    assert "expires=1000" in backend.requests[0].input_images[0]
    persisted_request = json.loads(runtime.read_text(queued.request_object_id))
    assert "signature" not in json.dumps(persisted_request)


def test_restarted_queued_job_uses_new_signed_urls(tmp_path, monkeypatch):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="restart-fresh-url",
    )
    backend = CapturingVideoBackend()
    monkeypatch.setattr("ai_drama_web.services.asset_delivery.time.time", lambda: 200)

    _execution_service(tmp_path, runtime, store, backend).submit_queued_job(queued.job_id)

    assert "expires=1100" in backend.requests[0].input_images[0]


def test_expired_old_signature_does_not_affect_submit(tmp_path, monkeypatch):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="ignore-old-signature",
    )
    old_signed_url = queue_service.asset_delivery.signed_asset_url(_asset_ids[0], ttl_seconds=1)
    backend = CapturingVideoBackend()
    monkeypatch.setattr("ai_drama_web.services.asset_delivery.time.time", lambda: 5000)

    _execution_service(tmp_path, runtime, store, backend).submit_queued_job(queued.job_id)

    assert old_signed_url not in backend.requests[0].input_images
    assert "expires=5900" in backend.requests[0].input_images[0]


def test_submit_queued_video_job_records_provider_error_without_leaking_raw_message(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )

    failed = _execution_service(tmp_path, runtime, store, FailingVideoBackend()).submit_queued_job(queued.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "provider_busy"
    assert failed.error_message == "video provider failed"
    assert "provider-secret" not in failed.error_message


def test_missing_agnes_key_marks_job_failed_with_authentication_or_configuration_error(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit-missing-key",
    )

    failed = _execution_service(tmp_path, runtime, store, MissingAgnesKeyBackend()).submit_queued_job(queued.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code in {"authentication", "configuration_error"}
    assert failed.error_message == "video provider failed"


def test_submit_queued_video_job_records_unknown_exception_without_sticking_submitting(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )

    failed = _execution_service(tmp_path, runtime, store, NotImplementedVideoBackend()).submit_queued_job(queued.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "unknown_provider_error"
    assert failed.error_message == "video provider failed"


def test_refresh_submitted_video_job_persists_completed_result(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    service = _execution_service(tmp_path, runtime, store, CompletingVideoBackend())
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


def test_m3_video_execution_uses_explicit_video_status_method(tmp_path):
    backend = ExplicitVideoBackend("abc123")
    completed = _completed_with_backend(tmp_path, backend)

    assert completed.internal_status == "completed"
    assert backend.video_status_calls == ["abc123"]
    assert backend.generic_status_calls == []


def test_m3_video_execution_uses_explicit_video_result_method(tmp_path):
    backend = ExplicitVideoBackend("job-plainid")
    completed = _completed_with_backend(tmp_path, backend)

    assert completed.internal_status == "completed"
    assert backend.video_result_calls == ["job-plainid"]
    assert backend.generic_result_calls == []


def test_m3_video_execution_handles_video_id_without_video_prefix(tmp_path):
    completed = _completed_with_backend(tmp_path, ExplicitVideoBackend("abc123"))

    assert completed.internal_status == "completed"


def test_m3_video_execution_handles_video_id_without_underscore(tmp_path):
    completed = _completed_with_backend(tmp_path, ExplicitVideoBackend("x7k9q"))

    assert completed.internal_status == "completed"


def test_legacy_video_compatibility_path_is_not_used_by_m3_execution(tmp_path):
    backend = ExplicitVideoBackend("video_456")
    completed = _completed_with_backend(tmp_path, backend)

    assert completed.internal_status == "completed"
    assert backend.generic_status_calls == []
    assert backend.generic_result_calls == []


def test_refresh_submitted_video_job_records_result_expired(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    service = _execution_service(tmp_path, runtime, store, ExpiredResultVideoBackend())
    submitted = service.submit_queued_job(queued.job_id)

    failed = service.refresh_job(submitted.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "result_expired"
    assert failed.error_message == "video provider failed"


def test_completed_job_requires_local_result_bytes(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    service = _execution_service(tmp_path, runtime, store, UrlOnlyVideoBackend())
    submitted = service.submit_queued_job(queued.job_id)

    failed = service.refresh_job(submitted.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "result_expired"


def test_submit_queued_video_job_rejects_nonqueued_job(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="submit",
    )
    store.transition_generation_job(queued.job_id, "cancelled")

    with pytest.raises(ValueError, match="only queued jobs can be submitted"):
        _execution_service(tmp_path, runtime, store, CapturingVideoBackend()).submit_queued_job(queued.job_id)


def _execution_service(tmp_path, runtime, store, backend):
    return GenerationExecutionService(
        store,
        runtime,
        backend,
        asset_delivery=AssetDeliveryService(
            store,
            runtime,
            LocalSecretStore(tmp_path / "runtime.db-data"),
            public_base_url="https://assets.example.test",
        ),
    )


def _completed_with_backend(tmp_path, backend):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key=f"submit-{backend.provider_job_id}",
    )
    service = _execution_service(tmp_path, runtime, store, backend)
    submitted = service.submit_queued_job(queued.job_id)
    return service.refresh_job(submitted.job_id)


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


class MissingAgnesKeyBackend:
    def create_video_job(self, request):
        raise ProviderError("authentication", "missing Agnes API key", provider="agnes")


class NotImplementedVideoBackend:
    def create_video_job(self, request):
        raise NotImplementedError("video not implemented")


class CompletingVideoBackend(CapturingVideoBackend):
    def get_video_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="completed",
            raw={"provider": "fake-video", "status": "completed"},
        )

    def fetch_video_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url="https://cdn.example.test/video.mp4",
            content=b"mp4-bytes",
            raw={"provider": "fake-video", "url": "https://cdn.example.test/video.mp4"},
        )

    def get_job_status(self, provider_job_id):
        return self.get_video_job_status(provider_job_id)

    def fetch_result(self, provider_job_id):
        return self.fetch_video_result(provider_job_id)


class ExpiredResultVideoBackend(CapturingVideoBackend):
    def get_video_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="completed",
            raw={"provider": "fake-video", "status": "completed"},
        )

    def fetch_video_result(self, provider_job_id):
        raise ProviderError(
            "result_expired",
            "provider url expired",
            provider="fake-video",
            raw={"url": "https://cdn.example.test/expired.mp4"},
        )


class UrlOnlyVideoBackend(CompletingVideoBackend):
    def fetch_video_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url="https://cdn.example.test/video.mp4",
            content=None,
            raw={"provider": "fake-video"},
        )


class ExplicitVideoBackend(CapturingVideoBackend):
    def __init__(self, provider_job_id):
        super().__init__()
        self.provider_job_id = provider_job_id
        self.video_status_calls = []
        self.video_result_calls = []
        self.generic_status_calls = []
        self.generic_result_calls = []

    def create_video_job(self, request):
        self.requests.append(request)
        return ProviderJob(provider_job_id=self.provider_job_id, status="submitted", raw={"provider": "explicit-video"})

    def get_job_status(self, provider_job_id):
        self.generic_status_calls.append(provider_job_id)
        raise AssertionError("M3 video execution must not call generic get_job_status")

    def fetch_result(self, provider_job_id):
        self.generic_result_calls.append(provider_job_id)
        raise AssertionError("M3 video execution must not call generic fetch_result")

    def get_video_job_status(self, provider_job_id):
        self.video_status_calls.append(provider_job_id)
        return ProviderJob(provider_job_id=provider_job_id, status="completed", raw={"provider": "explicit-video"})

    def fetch_video_result(self, provider_job_id):
        self.video_result_calls.append(provider_job_id)
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url=f"https://cdn.example.test/{provider_job_id}.mp4",
            content=b"mp4-bytes",
            raw={"provider": "explicit-video"},
        )
