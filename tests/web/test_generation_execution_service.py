import json

import pytest

from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderJob, ProviderResult
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import AssetDeliveryService
from ai_drama_web.services.generation_execution import GenerationExecutionService

from test_generation_job_service import _ready_fixture


def test_submit_queued_video_job_sends_only_the_standard_shot_keyframe(tmp_path):
    runtime, store, queue_service, revision, _canonical, asset_ids = _ready_fixture(tmp_path)
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
    assert backend.requests[0].parameters == {"frame_rate": 24, "num_frames": 121}
    assert len(backend.requests[0].input_images) == 1
    assert backend.requests[0].input_images[0].startswith("https://assets.example.test/public/assets/")
    assert asset_ids[1] in backend.requests[0].input_images[0]
    persisted_request = json.loads(runtime.read_text(queued.request_object_id))
    assert "url" not in json.dumps(persisted_request)
    response = json.loads(runtime.read_text(submitted.response_object_id))
    assert response["provider"] == "fake-video"
    assert response["request_prompt"] == "Shen Qinghe turns toward the lantern."
    assert response["mixed_keys"]["2"] == "two"
    assert len(response["colliding_keys"]) == 2
    signature = backend.requests[0].input_images[0].split("signature=", 1)[1]
    assert signature not in json.dumps(response)
    assert store.get_submission_attempt(submitted.job_id)["state"] == "committed"


def test_accepted_submission_recovers_local_commit_without_resubmit(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id, shot_id="SHOT_001", idempotency_key="accepted-crash"
    )
    backend = CapturingVideoBackend()

    def crash(name):
        if name == "accepted_persisted":
            raise SystemExit("crash")

    service = _execution_service(tmp_path, runtime, store, backend)
    service._checkpoint = crash
    with pytest.raises(SystemExit, match="crash"):
        service.submit_queued_job(queued.job_id)
    assert store.get_submission_attempt(queued.job_id)["state"] == "accepted"
    assert store.get_generation_job(queued.job_id).internal_status == "submitting"

    recovered = service.recover_submission_attempts()
    assert recovered == 1
    assert store.get_generation_job(queued.job_id).provider_job_id == "video-provider-1"
    assert store.get_submission_attempt(queued.job_id)["state"] == "committed"
    assert len(backend.requests) == 1


@pytest.mark.asyncio
async def test_crash_before_acceptance_persistence_fails_closed_without_resubmit(tmp_path):
    from ai_drama_web.services.generation_poller import GenerationPoller

    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id, shot_id="SHOT_001", idempotency_key="unknown-crash"
    )
    backend = CapturingVideoBackend()
    service = _execution_service(tmp_path, runtime, store, backend)

    def crash(name):
        if name == "provider_returned":
            raise SystemExit("crash")

    service._checkpoint = crash
    with pytest.raises(SystemExit, match="crash"):
        service.submit_queued_job(queued.job_id)
    assert store.get_submission_attempt(queued.job_id)["state"] == "submitting"
    poller = GenerationPoller(store, runtime, backend, rpm=1, poll_interval_seconds=1, execution_service=service)
    result = await poller.run_cycle()
    assert result.submission_outcome_unknown == 1
    assert store.get_generation_job(queued.job_id).error_code == "submission_outcome_unknown"
    assert len(backend.requests) == 1


def test_execution_rejects_legacy_queued_standard_video_with_multiple_shot_keyframes(tmp_path):
    runtime, store, queue_service, revision, _canonical, asset_ids = _ready_fixture(tmp_path)
    second_keyframe = store.create_generated_asset(
        project_id=revision.project_id,
        chapter_id=revision.chapter_id,
        asset_type="shot_keyframe",
        name="Second keyframe",
        data=b"png-second-keyframe",
        media_type="image/png",
        source_job_id="image-job-3",
        metadata={},
    )
    store.update_asset_status(second_keyframe.asset_id, "usable")
    backend = CapturingVideoBackend()
    service = _execution_service(tmp_path, runtime, store, backend)

    with pytest.raises(ProviderError) as exc_info:
        service._video_input_asset_ids(
            {
                "asset_ids": [asset_ids[1], second_keyframe.asset_id],
                "parameters": {},
            }
        )

    assert exc_info.value.code == "invalid_request"
    assert backend.requests == []


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
    assert failed.response_object_id
    evidence = json.loads(runtime.read_text(failed.response_object_id))
    assert evidence["provider"] == "fake-video"
    assert evidence["error_code"] == "provider_busy"
    assert evidence["raw"]["status_code"] == 503
    assert evidence["raw"]["response"]["code"] == "publish_video_queue_failed"
    assert evidence["raw"]["nonfinite"] is None
    assert evidence["raw"]["binary"] == "<bytes>"
    assert evidence["raw"]["mixed_keys"]["2"] == "two"
    persisted = json.dumps(evidence)
    for secret in (
        "provider-api-key",
        "provider-bearer",
        "signed-value",
        "inline-api-key",
        "inline-token",
        "url-token",
        "dict-signature",
        "leak",
    ):
        assert secret not in persisted


def test_refresh_provider_reported_failure_persists_sanitized_evidence(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="reported-failure",
    )
    service = _execution_service(tmp_path, runtime, store, ReportedFailedVideoBackend())
    submitted = service.submit_queued_job(queued.job_id)

    failed = service.refresh_job(submitted.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "generation_failed"
    evidence = json.loads(runtime.read_text(failed.response_object_id))
    assert evidence["provider"] == "fake-video"
    assert evidence["status"] == "failed"
    assert evidence["raw"]["provider_response"]["error"]["code"] == "generation_failed"
    assert "reported-failure-token" not in json.dumps(evidence)


def test_legacy_inline_assets_cannot_bypass_video_input_validation(tmp_path):
    runtime, store, _queue_service, _revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    service = _execution_service(tmp_path, runtime, store, CapturingVideoBackend())

    with pytest.raises(ProviderError) as exc_info:
        service._materialize_asset_urls(
            {
                "assets": [
                    {"url": "https://assets.example.test/character.png"},
                    {"url": "https://assets.example.test/keyframe.png"},
                ]
            }
        )

    assert exc_info.value.code == "invalid_request"


def test_submit_queued_video_job_maps_invalid_public_base_url_to_input_unreachable(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="invalid-base-url",
    )

    failed = _execution_service(
        tmp_path,
        runtime,
        store,
        CapturingVideoBackend(),
        public_base_url="http://localhost:8000",
    ).submit_queued_job(queued.job_id)

    assert failed.internal_status == "failed"
    assert failed.error_code == "input_unreachable"
    assert failed.error_message == "video input asset is not provider reachable"


def test_invalid_public_base_url_does_not_leave_job_submitting(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="invalid-base-url-submitting",
    )

    _execution_service(
        tmp_path,
        runtime,
        store,
        CapturingVideoBackend(),
        public_base_url="https://127.0.0.1",
    ).submit_queued_job(queued.job_id)

    assert store.get_generation_job(queued.job_id).internal_status == "failed"


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


def test_completed_result_does_not_persist_or_expose_signed_source_url(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="signed-result-url",
    )
    service = _execution_service(tmp_path, runtime, store, SignedResultVideoBackend())
    submitted = service.submit_queued_job(queued.job_id)

    completed = service.refresh_job(submitted.job_id)

    result = store.get_generation_result(completed.provider_result_id)
    assert result.source_url == "https://cdn.example.test/signed.mp4?expires=123"
    assert result.source_url_state == "source_url_expired"
    assert "result-signature" not in result.source_url
    assert "result-token" not in result.source_url
    assert "result-user" not in result.source_url
    assert "result-password" not in result.source_url
    assert "fragment-token" not in result.source_url
    assert runtime.read_bytes_object(result.object_id) == b"signed-mp4-bytes"


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
    evidence = json.loads(runtime.read_text(failed.response_object_id))
    assert evidence["provider"] == "fake-video"
    assert evidence["error_code"] == "result_expired"
    assert evidence["raw"]["phase"] == "download"
    persisted = json.dumps(evidence)
    assert "refresh-secret" not in persisted
    assert "refresh-signature" not in persisted


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


def _execution_service(tmp_path, runtime, store, backend, *, public_base_url="https://assets.example.test"):
    return GenerationExecutionService(
        store,
        runtime,
        backend,
        asset_delivery=AssetDeliveryService(
            store,
            runtime,
            LocalSecretStore(tmp_path / "runtime.db-data"),
            public_base_url=public_base_url,
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
                "request_images": list(request.input_images),
                "mixed_keys": {"ok": 1, 2: "two"},
                "colliding_keys": {"1": "string", 1: "integer"},
            },
        )


class FailingVideoBackend:
    def create_video_job(self, request):
        raise ProviderError(
            "provider_busy",
            "provider-secret unavailable",
            provider="fake-video",
            raw={
                "status_code": 503,
                "response": {
                    "code": "publish_video_queue_failed",
                    "api_key": "provider-api-key",
                },
                "authorization": "Bearer provider-bearer",
                "provider-secret": "leak",
                "url": "https://assets.example.test/input.png?expires=1&signature=signed-value",
                "detail": "api_key=inline-api-key token=inline-token",
                "callback": "https://example.test/callback?access_token=url-token",
                "signature": "dict-signature",
                "nonfinite": float("nan"),
                "binary": b"binary-secret",
                "mixed_keys": {"ok": 1, 2: "two"},
            },
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


class SignedResultVideoBackend(CompletingVideoBackend):
    def fetch_video_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url=(
                "https://result-user:result-password@cdn.example.test/signed.mp4?expires=123"
                "&signature=result-signature&access_token=result-token#access_token=fragment-token"
            ),
            content=b"signed-mp4-bytes",
            raw={"provider": "fake-video"},
        )


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
            raw={
                "phase": "download",
                "client_secret": "refresh-secret",
                "url": "https://cdn.example.test/expired.mp4?signature=refresh-signature",
            },
        )


class ReportedFailedVideoBackend(CapturingVideoBackend):
    def get_video_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="failed",
            raw={
                "provider": "fake-video",
                "provider_response": {
                    "status": "failed",
                    "error": {
                        "code": "generation_failed",
                        "access_token": "reported-failure-token",
                    },
                },
            },
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
