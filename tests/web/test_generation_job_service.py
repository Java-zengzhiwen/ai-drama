import json

import pytest

from ai_drama_runtime.shot_prompt_canonical import (
    CONTENT_PROFILE,
    CANONICAL_PARSER_VERSION,
    serialize_shot_prompt_json,
    shot_prompt_content_hash,
)
from ai_drama_runtime.store import RuntimeStore, now_iso
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.generation_jobs import (
    GenerationIdempotencyConflict,
    GenerationInvalidRequest,
    GenerationJobBlocked,
    GenerationJobService,
    video_timing_for_duration,
)
from ai_drama_web.store import ProductStore


def _runtime_and_store(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return runtime, ProductStore(runtime)


def _ready_fixture(tmp_path):
    runtime, store = _runtime_and_store(tmp_path)
    project = store.create_project(name="Project")
    chapter = store.create_chapter(project.project_id, "Chapter", 1)
    character = store.create_generated_asset(
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        asset_type="character_reference",
        name="Character",
        data=b"png-character",
        media_type="image/png",
        source_job_id="image-job-1",
        metadata={},
    )
    keyframe = store.create_generated_asset(
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        asset_type="shot_keyframe",
        name="Keyframe",
        data=b"png-keyframe",
        media_type="image/png",
        source_job_id="image-job-2",
        metadata={},
    )
    store.update_asset_status(character.asset_id, "usable")
    store.update_asset_status(keyframe.asset_id, "usable")
    canonical = {
        "schema_version": "shot-prompt-canonical-v1",
        "project_id": project.project_id,
        "chapter_id": chapter.chapter_id,
        "source_storyboard_revision_id": "storyboard-rev-1",
        "shots": [
            {
                "shot_id": "SHOT_001",
                "shot_order": 1,
                "duration_seconds": 5,
                "scene_id": "SCENE_001",
                "character_ids": ["CHAR_001"],
                "prop_ids": [],
                "asset_refs": [character.asset_id, keyframe.asset_id],
                "camera": {"shot_size": "medium"},
                "action": "turns toward the lantern",
                "emotion": "tense",
                "dialogue": [],
                "positive_prompt": "Shen Qinghe turns toward the lantern.",
                "negative_prompt": "warped face",
                "continuity_notes": ["preserve blue robe"],
                "agnes_video_params": {"num_frames": 121, "frame_rate": 24},
            }
        ],
    }
    revision = _insert_shot_prompt_revision(runtime, canonical)
    _mark_ready(runtime, revision.revision_id, "SHOT_001")
    service = GenerationJobService(
        store,
        runtime,
        LocalSecretStore(tmp_path / "runtime.db-data"),
        public_base_url="https://assets.example.test",
    )
    return runtime, store, service, revision, canonical, [character.asset_id, keyframe.asset_id]


def _insert_shot_prompt_revision(runtime, canonical):
    text = serialize_shot_prompt_json(canonical).decode("utf-8")
    content_hash = shot_prompt_content_hash(canonical)
    content_object_id = runtime.write_text_object(text)
    run = runtime.create_run(
        artifact_id=f"{canonical['chapter_id']}:shot-prompts",
        project_id=canonical["project_id"],
        chapter_id=canonical["chapter_id"],
        skill_id="test-shot-prompt",
        skill_version="1",
        skill_hash="",
        runtime="test",
        provider="test",
        model="test",
        status="SUCCEEDED",
        request_object_id=content_object_id,
        response_object_id=content_object_id,
        input_hash=content_hash,
        request_hash=content_hash,
    )
    return runtime.insert_revision(
        artifact_id=f"{canonical['chapter_id']}:shot-prompts",
        artifact_type="shot_prompt_set",
        project_id=canonical["project_id"],
        chapter_id=canonical["chapter_id"],
        run_id=run.run_id,
        skill_id="test-shot-prompt",
        skill_version="1",
        skill_package_hash="",
        runtime_provider="test",
        runtime_model="test",
        content_object_id=content_object_id,
        content_hash=content_hash,
        raw_response_object_id=content_object_id,
        parser_version=CANONICAL_PARSER_VERSION,
        content_profile=CONTENT_PROFILE,
    )


def _mark_ready(runtime, revision_id, shot_id):
    runtime.insert_review_record_with_opened_event(
        artifact_id="artifact",
        revision_id=revision_id,
        scope="shot",
        shot_id=shot_id,
        body=json.dumps(
            {
                "schema_version": "shot-prompt-readiness-v1",
                "status": "ready",
                "revision_id": revision_id,
                "shot_id": shot_id,
                "content_hash": "hash",
                "marked_at": now_iso(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        blocking=False,
        created_by="test",
        note="ready",
    )


def test_queue_video_job_persists_canonical_request_and_returns_existing_duplicate(tmp_path):
    runtime, store, service, revision, _canonical, asset_ids = _ready_fixture(tmp_path)

    job = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="idem-1",
    )
    duplicate = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="idem-1",
    )

    assert duplicate.job_id == job.job_id
    assert job.internal_status == "queued"
    assert job.attempt_number == 1
    request = json.loads(runtime.read_text(job.request_object_id))
    assert request["prompt"] == "Shen Qinghe turns toward the lantern."
    assert request["negative_prompt"] == "warped face"
    assert request["duration_seconds"] == 5
    assert request["parameters"] == {"frame_rate": 24, "num_frames": 121}
    assert request["asset_ids"] == asset_ids
    assert "assets" not in request
    assert "url" not in json.dumps(request)
    assert store.list_generation_jobs_for_chapter(revision.chapter_id) == [job]


def test_explicit_rerun_creates_next_attempt_with_overrides(tmp_path):
    runtime, store, service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    first = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="source",
    )
    replacement = store.create_generated_asset(
        project_id=revision.project_id,
        chapter_id=revision.chapter_id,
        asset_type="shot_keyframe",
        name="Replacement",
        data=b"png-replacement",
        media_type="image/png",
        source_job_id="image-job-3",
        metadata={},
    )
    store.update_asset_status(replacement.asset_id, "usable")

    rerun = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="rerun-1",
        explicit_rerun=True,
        overrides={"prompt": "Override prompt", "asset_ids": [replacement.asset_id]},
    )

    assert rerun.job_id != first.job_id
    assert rerun.attempt_number == 2
    request = json.loads(runtime.read_text(rerun.request_object_id))
    assert request["prompt"] == "Override prompt"
    assert request["asset_ids"] == [replacement.asset_id]


def test_duration_5_and_10_seconds_map_to_official_frame_counts():
    assert video_timing_for_duration(5) == {"num_frames": 121, "frame_rate": 24}
    assert video_timing_for_duration(10) == {"num_frames": 241, "frame_rate": 24}


def test_invalid_duration_is_rejected(tmp_path):
    _runtime, _store, service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)

    with pytest.raises(GenerationInvalidRequest, match="unsupported video duration"):
        service.queue_video_job(
            prompt_revision_id=revision.revision_id,
            shot_id="SHOT_001",
            idempotency_key="bad-duration",
            explicit_rerun=True,
            overrides={"duration_seconds": 6},
        )


def test_conflicting_duration_and_num_frames_is_rejected(tmp_path):
    runtime, _store, service, revision, canonical, _asset_ids = _ready_fixture(tmp_path)
    canonical["shots"][0]["agnes_video_params"] = {"num_frames": 241, "frame_rate": 24}
    object_id = runtime.write_text_object(serialize_shot_prompt_json(canonical).decode("utf-8"))
    runtime.conn.execute(
        "UPDATE revisions SET content_object_id = ? WHERE revision_id = ?",
        (object_id, revision.revision_id),
    )
    runtime.conn.commit()

    with pytest.raises(GenerationInvalidRequest, match="duration timing conflicts"):
        service.queue_video_job(
            prompt_revision_id=revision.revision_id,
            shot_id="SHOT_001",
            idempotency_key="conflict",
        )


def test_rerun_duration_override_changes_provider_request(tmp_path):
    runtime, _store, service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)

    rerun = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="duration-10",
        explicit_rerun=True,
        overrides={"duration_seconds": 10},
    )

    request = json.loads(runtime.read_text(rerun.request_object_id))
    assert request["duration_seconds"] == 10
    assert request["parameters"] == {"frame_rate": 24, "num_frames": 241}


def test_same_key_different_shot_returns_idempotency_conflict(tmp_path):
    _runtime, _store, service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="same-key",
    )

    with pytest.raises(GenerationIdempotencyConflict):
        service.queue_video_job(
            prompt_revision_id=revision.revision_id,
            shot_id="MISSING_SHOT",
            idempotency_key="same-key",
        )


def test_queue_video_job_blocks_unready_or_unusable_inputs(tmp_path):
    _runtime, store, service, revision, _canonical, asset_ids = _ready_fixture(tmp_path)
    with pytest.raises(GenerationJobBlocked, match="shot prompt is not ready"):
        service.queue_video_job(
            prompt_revision_id=revision.revision_id,
            shot_id="MISSING_SHOT",
            idempotency_key="missing",
        )

    store.update_asset_status(asset_ids[0], "draft")
    with pytest.raises(GenerationJobBlocked, match="asset is not usable"):
        service.queue_video_job(
            prompt_revision_id=revision.revision_id,
            shot_id="SHOT_001",
            idempotency_key="unusable",
        )
