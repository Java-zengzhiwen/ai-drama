import json

from fastapi.testclient import TestClient

from ai_drama_runtime.shot_prompt_canonical import (
    CANONICAL_PARSER_VERSION,
    CONTENT_PROFILE,
    serialize_shot_prompt_json,
    shot_prompt_content_hash,
)
from ai_drama_runtime.store import RuntimeStore, now_iso
from ai_drama_web.app import create_app
from ai_drama_web.providers.models import ProviderJob, ProviderResult
from ai_drama_web.store import ProductStore


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _app_client(data_root):
    app = create_app(data_root=data_root, skills_root="skills")
    app.state.settings.public_base_url = "https://assets.example.test"
    return TestClient(app)


def _ready_chapter(tmp_path):
    data_root = tmp_path / "runtime-data"
    runtime = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Project")
    chapter = store.create_chapter(project.project_id, "Chapter", 1)
    first_asset = _usable_asset(
        store,
        project.project_id,
        chapter.chapter_id,
        "Character",
        "character_reference",
    )
    second_asset = _usable_asset(
        store,
        project.project_id,
        chapter.chapter_id,
        "Keyframe",
        "shot_keyframe",
    )
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
                "asset_refs": [first_asset.asset_id, second_asset.asset_id],
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
    runtime.close()
    return data_root, chapter, revision, canonical


def _usable_asset(store, project_id, chapter_id, name, asset_type):
    asset = store.create_uploaded_asset(
        project_id=project_id,
        chapter_id=chapter_id,
        asset_type=asset_type,
        name=name,
        data=PNG_BYTES,
        media_type="image/png",
        metadata={},
    )
    return store.update_asset_status(asset.asset_id, "usable")


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


def test_queue_video_job_endpoint_returns_existing_job_for_duplicate_idempotency(tmp_path):
    data_root, chapter, revision, _canonical = _ready_chapter(tmp_path)
    with _app_client(data_root) as client:
        payload = {
            "prompt_revision_id": revision.revision_id,
            "shot_id": "SHOT_001",
            "idempotency_key": "submit-1",
        }
        created = client.post(
            f"/api/chapters/{chapter.chapter_id}/generation/video-jobs",
            json=payload,
        )
        duplicate = client.post(
            f"/api/chapters/{chapter.chapter_id}/generation/video-jobs",
            json=payload,
        )
        listed = client.get(f"/api/chapters/{chapter.chapter_id}/generation/jobs")

    assert created.status_code == 200, created.text
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["job_id"] == created.json()["job_id"]
    assert created.json()["internal_status"] == "queued"
    assert created.json()["ui_status"] == "queued"
    assert created.json()["attempt_number"] == 1
    assert listed.status_code == 200, listed.text
    assert [item["job_id"] for item in listed.json()] == [created.json()["job_id"]]


def test_generation_job_detail_includes_saved_request_preview(tmp_path):
    data_root, chapter, revision, _canonical = _ready_chapter(tmp_path)
    with _app_client(data_root) as client:
        created = client.post(
            f"/api/chapters/{chapter.chapter_id}/generation/video-jobs",
            json={
                "prompt_revision_id": revision.revision_id,
                "shot_id": "SHOT_001",
                "idempotency_key": "submit-1",
            },
        ).json()
        detail = client.get(f"/api/generation/jobs/{created['job_id']}")

    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["request"]["prompt"] == "Shen Qinghe turns toward the lantern."
    assert body["request"]["negative_prompt"] == "warped face"
    assert body["request"]["parameters"] == {"frame_rate": 24, "num_frames": 121}
    assert body["request"]["assets"][0]["url"].startswith("https://assets.example.test/public/assets/")


def test_refresh_generation_job_submits_queued_video_job(tmp_path):
    data_root, chapter, revision, _canonical = _ready_chapter(tmp_path)
    with _app_client(data_root) as client:
        client.app.state.generation_backend = ApiVideoBackend()
        created = client.post(
            f"/api/chapters/{chapter.chapter_id}/generation/video-jobs",
            json={
                "prompt_revision_id": revision.revision_id,
                "shot_id": "SHOT_001",
                "idempotency_key": "submit-1",
            },
        ).json()
        refreshed = client.post(f"/api/generation/jobs/{created['job_id']}/refresh")

    assert refreshed.status_code == 200, refreshed.text
    body = refreshed.json()
    assert body["internal_status"] == "submitted"
    assert body["ui_status"] == "generating"
    assert body["provider_job_id"] == "api-video-1"


def test_results_api_lists_selects_and_reviews_generation_result(tmp_path):
    data_root, chapter, revision, _canonical = _ready_chapter(tmp_path)
    with _app_client(data_root) as client:
        client.app.state.generation_backend = CompletedApiVideoBackend()
        created = client.post(
            f"/api/chapters/{chapter.chapter_id}/generation/video-jobs",
            json={
                "prompt_revision_id": revision.revision_id,
                "shot_id": "SHOT_001",
                "idempotency_key": "submit-1",
            },
        ).json()
        submitted = client.post(f"/api/generation/jobs/{created['job_id']}/refresh").json()
        completed = client.post(f"/api/generation/jobs/{submitted['job_id']}/refresh").json()
        listed = client.get(f"/api/chapters/{chapter.chapter_id}/results")
        result_id = listed.json()[0]["results"][0]["result_id"]
        selected = client.post(f"/api/shots/SHOT_001/results/{result_id}/select")
        reviewed = client.post(
            f"/api/results/{result_id}/review",
            json={
                "decision": "passed",
                "failure_category": "",
                "note": "current cut",
            },
        )

    assert completed["internal_status"] == "completed"
    assert listed.status_code == 200, listed.text
    assert listed.json() == [
        {
            "shot_id": "SHOT_001",
            "current_result_id": "",
            "results": [
                {
                    "result_id": result_id,
                    "job_id": completed["job_id"],
                    "attempt_number": 1,
                    "media_type": "video/mp4",
                    "source_url": "https://cdn.example.test/video.mp4",
                    "local_result_available": True,
                    "created_at": listed.json()[0]["results"][0]["created_at"],
                }
            ],
        }
    ]
    assert selected.status_code == 200, selected.text
    assert selected.json()["result_id"] == result_id
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["decision"] == "passed"


def test_queue_video_job_endpoint_blocks_unready_shot(tmp_path):
    data_root, chapter, revision, _canonical = _ready_chapter(tmp_path)
    with _app_client(data_root) as client:
        response = client.post(
            f"/api/chapters/{chapter.chapter_id}/generation/video-jobs",
            json={
                "prompt_revision_id": revision.revision_id,
                "shot_id": "MISSING_SHOT",
                "idempotency_key": "missing",
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "error_code": "shot_prompt_blocked",
        "error_message": "shot prompt is not ready",
    }


class ApiVideoBackend:
    def create_video_job(self, request):
        return ProviderJob(
            provider_job_id="api-video-1",
            status="submitted",
            raw={"provider": "api-video", "prompt": request.prompt},
        )


class CompletedApiVideoBackend(ApiVideoBackend):
    def get_job_status(self, provider_job_id):
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="completed",
            raw={"provider": "api-video", "status": "completed"},
        )

    def fetch_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url="https://cdn.example.test/video.mp4",
            content=b"mp4-bytes",
            raw={"provider": "api-video", "url": "https://cdn.example.test/video.mp4"},
        )
