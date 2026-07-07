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
    GenerationJobBlocked,
    GenerationJobService,
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
    assert [item["asset_id"] for item in request["assets"]] == asset_ids
    assert all(item["url"].startswith("https://assets.example.test/public/assets/") for item in request["assets"])
    assert store.list_generation_jobs_for_chapter(revision.chapter_id) == [job]


def test_explicit_rerun_creates_next_attempt_with_overrides(tmp_path):
    runtime, _store, service, revision, _canonical, _asset_ids = _ready_fixture(tmp_path)
    first = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="source",
    )

    rerun = service.queue_video_job(
        prompt_revision_id=revision.revision_id,
        shot_id="SHOT_001",
        idempotency_key="rerun-1",
        explicit_rerun=True,
        overrides={"prompt": "Override prompt"},
    )

    assert rerun.job_id != first.job_id
    assert rerun.attempt_number == 2
    assert json.loads(runtime.read_text(rerun.request_object_id))["prompt"] == "Override prompt"


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
