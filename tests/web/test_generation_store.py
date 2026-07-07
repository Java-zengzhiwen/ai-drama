import json

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


def _store(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return runtime, ProductStore(runtime)


def _project_chapter(store):
    project = store.create_project(name="Project")
    chapter = store.create_chapter(project.project_id, "Chapter 1", 1)
    return project, chapter


def _request_object(runtime, value=None):
    payload = {"prompt": "shot prompt", "duration": 5} if value is None else value
    return runtime.write_text_object(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def test_generation_job_lifecycle_enforces_transitions_and_provider_ids(tmp_path):
    runtime, store = _store(tmp_path)
    _project, chapter = _project_chapter(store)
    request_object_id = _request_object(runtime)

    job = store.create_generation_job(
        provider="agnes",
        job_type="video",
        project_id=chapter.project_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        prompt_revision_id="prompt-rev-1",
        idempotency_key="idem-1",
        request_hash="hash-1",
        request_object_id=request_object_id,
        attempt_number=1,
    )

    assert job.internal_status == "draft"
    assert job.provider_job_id == ""

    queued = store.transition_generation_job(job.job_id, "queued")
    submitting = store.transition_generation_job(queued.job_id, "submitting")
    submitted = store.attach_generation_provider_job(
        submitting.job_id,
        provider_job_id="video-123",
        response_object_id=runtime.write_text_object('{"video_id":"video-123"}'),
    )

    assert submitted.internal_status == "submitted"
    assert submitted.provider_job_id == "video-123"

    polling = store.transition_generation_job(
        submitted.job_id,
        "polling",
        provider_result_id="provider-result-1",
    )
    completed = store.transition_generation_job(polling.job_id, "completed")

    assert completed.internal_status == "completed"
    assert completed.provider_result_id == "provider-result-1"

    with pytest.raises(ValueError, match="invalid generation job transition"):
        store.transition_generation_job(completed.job_id, "queued")


def test_generation_jobs_are_idempotent_by_provider_and_key(tmp_path):
    runtime, store = _store(tmp_path)
    _project, chapter = _project_chapter(store)
    request_object_id = _request_object(runtime)

    first = store.create_generation_job(
        provider="agnes",
        job_type="video",
        project_id=chapter.project_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        prompt_revision_id="prompt-rev-1",
        idempotency_key="same-key",
        request_hash="hash-1",
        request_object_id=request_object_id,
        attempt_number=1,
    )
    duplicate = store.create_generation_job(
        provider="agnes",
        job_type="video",
        project_id=chapter.project_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        prompt_revision_id="prompt-rev-1",
        idempotency_key="same-key",
        request_hash="hash-1",
        request_object_id=request_object_id,
        attempt_number=1,
    )

    assert duplicate.job_id == first.job_id
    assert store.list_generation_jobs_for_chapter(chapter.chapter_id) == [first]


def test_results_selection_reviews_and_reruns_are_versioned(tmp_path):
    runtime, store = _store(tmp_path)
    _project, chapter = _project_chapter(store)
    source_request_object_id = _request_object(runtime)
    source_job = store.create_generation_job(
        provider="agnes",
        job_type="video",
        project_id=chapter.project_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        prompt_revision_id="prompt-rev-1",
        idempotency_key="source",
        request_hash="hash-source",
        request_object_id=source_request_object_id,
        attempt_number=1,
    )
    replacement_job = store.create_generation_job(
        provider="agnes",
        job_type="video",
        project_id=chapter.project_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        prompt_revision_id="prompt-rev-1",
        idempotency_key="rerun",
        request_hash="hash-rerun",
        request_object_id=_request_object(runtime, {"prompt": "rerun"}),
        attempt_number=2,
    )

    first_result = store.create_generation_result(
        job_id=source_job.job_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        object_id=runtime.write_bytes_object(b"first-video"),
        media_type="video/mp4",
        source_url="https://provider.example/first.mp4",
        metadata_object_id=runtime.write_text_object('{"attempt":1}'),
    )
    second_result = store.create_generation_result(
        job_id=replacement_job.job_id,
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        object_id=runtime.write_bytes_object(b"second-video"),
        media_type="video/mp4",
        source_url="https://provider.example/second.mp4",
        metadata_object_id=runtime.write_text_object('{"attempt":2}'),
    )

    assert store.select_generation_result(chapter.chapter_id, "1-01", first_result.result_id).result_id == first_result.result_id
    assert store.select_generation_result(chapter.chapter_id, "1-01", second_result.result_id).result_id == second_result.result_id
    assert store.current_generation_result_selection(chapter.chapter_id, "1-01").result_id == second_result.result_id
    assert [result.result_id for result in store.list_generation_results_for_shot(chapter.chapter_id, "1-01")] == [
        first_result.result_id,
        second_result.result_id,
    ]

    review = store.create_result_review(
        result_id=second_result.result_id,
        decision="failed",
        failure_category="visual_quality_error",
        note="needs rerun",
    )
    assert review.result_id == second_result.result_id
    assert review.failure_category == "visual_quality_error"

    rerun = store.create_rerun_record(
        source_job_id=source_job.job_id,
        new_job_id=replacement_job.job_id,
        overrides_object_id=runtime.write_text_object('{"positive_prompt":"rerun"}'),
    )

    assert rerun.source_job_id == source_job.job_id
    assert rerun.new_job_id == replacement_job.job_id
    assert store.next_generation_attempt_number(
        chapter_id=chapter.chapter_id,
        shot_id="1-01",
        provider="agnes",
        job_type="video",
    ) == 3
