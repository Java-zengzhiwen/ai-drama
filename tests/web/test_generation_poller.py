import pytest

from ai_drama_web.providers.models import ProviderJob, ProviderResult
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import AssetDeliveryService
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.services.generation_poller import GenerationPoller

from test_generation_job_service import _ready_fixture


@pytest.mark.asyncio
async def test_poller_cycle_submits_due_queued_jobs(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued",
    )
    backend = PollerBackend()

    result = await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()

    job = store.get_generation_job(queued.job_id)
    assert result.submitted == 1
    assert job.internal_status == "submitted"
    assert job.provider_job_id == "abc_123"
    assert len(backend.created) == 1


@pytest.mark.asyncio
async def test_poller_respects_rpm_limit(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    first = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued-1",
    )
    second = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued-2",
    )
    backend = PollerBackend()

    result = await GenerationPoller(store, runtime, backend, rpm=1, poll_interval_seconds=5).run_cycle()

    assert result.submitted == 1
    assert store.get_generation_job(first.job_id).internal_status == "submitted"
    assert store.get_generation_job(second.job_id).internal_status == "queued"
    assert len(backend.created) == 1


@pytest.mark.asyncio
async def test_poller_skips_polling_job_before_next_poll_at(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued",
    )
    backend = PollerBackend()
    await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()
    store.transition_generation_job(queued.job_id, "polling", next_poll_at="9999-01-01T00:00:00Z")

    result = await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()

    job = store.get_generation_job(queued.job_id)
    assert result.polled == 0
    assert job.internal_status == "polling"
    assert job.provider_result_id == ""


@pytest.mark.asyncio
async def test_poller_persists_next_poll_at_for_processing_jobs(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued",
    )
    backend = ProcessingPollerBackend()
    await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()

    result = await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()

    job = store.get_generation_job(queued.job_id)
    assert result.polled == 1
    assert job.internal_status == "polling"
    assert job.next_poll_at


@pytest.mark.asyncio
async def test_poller_refreshes_submitted_jobs_with_non_video_prefix_provider_id(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued",
    )
    backend = PollerBackend()
    submitted = await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()
    assert submitted.submitted == 1

    result = await GenerationPoller(store, runtime, backend, rpm=60, poll_interval_seconds=5).run_cycle()

    job = store.get_generation_job(queued.job_id)
    assert result.polled == 1
    assert job.internal_status == "completed"
    assert store.get_generation_result(job.provider_result_id).object_id


@pytest.mark.asyncio
async def test_poller_marks_orphaned_submitting_as_submission_outcome_unknown(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="queued",
    )
    store.transition_generation_job(queued.job_id, "submitting")

    result = await GenerationPoller(store, runtime, PollerBackend(), rpm=60, poll_interval_seconds=5).run_cycle()

    job = store.get_generation_job(queued.job_id)
    assert result.submission_outcome_unknown == 1
    assert job.internal_status == "failed"
    assert job.error_code == "submission_outcome_unknown"


@pytest.mark.asyncio
async def test_poller_marks_invalid_public_base_url_as_input_unreachable(tmp_path):
    runtime, store, queue_service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    queued = queue_service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="invalid-public-base-url",
    )
    backend = PollerBackend()
    execution_service = GenerationExecutionService(
        store,
        runtime,
        backend,
        asset_delivery=AssetDeliveryService(
            store,
            runtime,
            LocalSecretStore(tmp_path / "runtime.db-data"),
            public_base_url="https://10.0.0.1",
        ),
    )

    result = await GenerationPoller(
        store,
        runtime,
        backend,
        rpm=60,
        poll_interval_seconds=5,
        execution_service=execution_service,
    ).run_cycle()

    job = store.get_generation_job(queued.job_id)
    assert result.submitted == 1
    assert job.internal_status == "failed"
    assert job.error_code == "input_unreachable"
    assert job.error_message == "video input asset is not provider reachable"


class PollerBackend:
    def __init__(self):
        self.created = []

    def create_video_job(self, request):
        self.created.append(request)
        return ProviderJob(
            provider_job_id="abc_123",
            status="submitted",
            raw={"provider": "fake-video"},
        )

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
            raw={"provider": "fake-video"},
        )

    def get_job_status(self, provider_job_id):
        return self.get_video_job_status(provider_job_id)

    def fetch_result(self, provider_job_id):
        return self.fetch_video_result(provider_job_id)


class ProcessingPollerBackend(PollerBackend):
    def get_video_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="in_progress",
            raw={"provider": "fake-video", "status": "in_progress"},
        )
