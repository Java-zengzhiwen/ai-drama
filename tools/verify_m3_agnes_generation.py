#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r"Using `httpx` with `starlette\.testclient` is deprecated.*")

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_drama_runtime.shot_prompt_canonical import (  # noqa: E402
    CANONICAL_PARSER_VERSION,
    CONTENT_PROFILE,
    serialize_shot_prompt_json,
    shot_prompt_content_hash,
)
from ai_drama_runtime.store import now_iso  # noqa: E402
from ai_drama_web.app import create_app  # noqa: E402
from ai_drama_web.providers.models import ProviderJob, ProviderResult  # noqa: E402


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _expect_status(response, status_code: int):
    if response.status_code != status_code:
        raise AssertionError(f"expected {status_code}, got {response.status_code}: {response.text}")
    return response.json()


class FakeVideoBackend:
    def __init__(self):
        self.created = []
        self.polls = 0

    def create_video_job(self, request):
        self.created.append(request)
        return ProviderJob(provider_job_id=f"abc_{len(self.created)}", status="submitted", raw={"ok": True})

    def get_video_job_status(self, provider_job_id):
        self.polls += 1
        return ProviderJob(provider_job_id=provider_job_id, status="completed", raw={"status": "completed"})

    def fetch_video_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url="https://cdn.example.test/video.mp4",
            content=b"mp4-bytes",
            raw={"url": "https://cdn.example.test/video.mp4"},
        )

    def get_job_status(self, provider_job_id):
        return self.get_video_job_status(provider_job_id)

    def fetch_result(self, provider_job_id):
        return self.fetch_video_result(provider_job_id)


def _install_backend(client: TestClient, backend: FakeVideoBackend):
    client.app.state.generation_backend = backend
    client.app.state.generation_poller.backend = backend
    client.app.state.generation_poller.execution_service.backend = backend


def _seed_ready_shot_prompt(client: TestClient):
    def seed():
        runtime = client.app.state.runtime_store
        store = client.app.state.product_store
        project = store.create_project(name="M3 Verification")
        chapter = store.create_chapter(project.project_id, "Chapter 1", 1)
        first_asset = store.create_uploaded_asset(
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            asset_type="character_reference",
            name="Character",
            data=PNG_BYTES,
            media_type="image/png",
            metadata={},
        )
        first_asset = store.update_asset_status(first_asset.asset_id, "usable")
        keyframe = store.create_uploaded_asset(
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            asset_type="shot_keyframe",
            name="Keyframe",
            data=PNG_BYTES,
            media_type="image/png",
            metadata={},
        )
        keyframe = store.update_asset_status(keyframe.asset_id, "usable")
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
                    "asset_refs": [first_asset.asset_id, keyframe.asset_id],
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
        text = serialize_shot_prompt_json(canonical).decode("utf-8")
        content_hash = shot_prompt_content_hash(canonical)
        content_object_id = runtime.write_text_object(text)
        run = runtime.create_run(
            artifact_id=f"{chapter.chapter_id}:shot-prompts",
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            skill_id="verify-shot-prompt",
            skill_version="1",
            skill_hash="",
            runtime="verify",
            provider="verify",
            model="verify",
            status="SUCCEEDED",
            request_object_id=content_object_id,
            response_object_id=content_object_id,
            input_hash=content_hash,
            request_hash=content_hash,
        )
        revision = runtime.insert_revision(
            artifact_id=f"{chapter.chapter_id}:shot-prompts",
            artifact_type="shot_prompt_set",
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            run_id=run.run_id,
            skill_id="verify-shot-prompt",
            skill_version="1",
            skill_package_hash="",
            runtime_provider="verify",
            runtime_model="verify",
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=content_object_id,
            parser_version=CANONICAL_PARSER_VERSION,
            content_profile=CONTENT_PROFILE,
        )
        runtime.insert_review_record_with_opened_event(
            artifact_id="artifact",
            revision_id=revision.revision_id,
            scope="shot",
            shot_id="SHOT_001",
            body=json.dumps(
                {
                    "schema_version": "shot-prompt-readiness-v1",
                    "status": "ready",
                    "revision_id": revision.revision_id,
                    "shot_id": "SHOT_001",
                    "content_hash": content_hash,
                    "marked_at": now_iso(),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            blocking=False,
            created_by="verify",
            note="ready",
        )
        return project.project_id, chapter.chapter_id, revision.revision_id

    return client.portal.call(seed)


def _run_workflow(client: TestClient):
    backend = FakeVideoBackend()
    _install_backend(client, backend)
    _project_id, chapter_id, revision_id = _seed_ready_shot_prompt(client)

    created = _expect_status(
        client.post(
            f"/api/chapters/{chapter_id}/generation/video-jobs",
            json={"prompt_revision_id": revision_id, "shot_id": "SHOT_001", "idempotency_key": "source"},
        ),
        200,
    )
    duplicate = _expect_status(
        client.post(
            f"/api/chapters/{chapter_id}/generation/video-jobs",
            json={"prompt_revision_id": revision_id, "shot_id": "SHOT_001", "idempotency_key": "source"},
        ),
        200,
    )
    assert duplicate["job_id"] == created["job_id"]

    submitted = client.portal.call(client.app.state.generation_poller.run_cycle)
    assert submitted.submitted == 1
    completed = client.portal.call(client.app.state.generation_poller.run_cycle)
    assert completed.polled == 1

    results = _expect_status(client.get(f"/api/chapters/{chapter_id}/results"), 200)
    result = results[0]["results"][0]
    assert result["local_result_available"] is True
    assert result["local_content_url"]
    content = client.get(result["local_content_url"])
    if content.status_code != 200 or content.content != b"mp4-bytes":
        raise AssertionError("persisted video bytes were not served")
    _expect_status(client.post(f"/api/shots/SHOT_001/results/{result['result_id']}/select"), 200)
    _expect_status(
        client.post(f"/api/results/{result['result_id']}/review", json={"decision": "passed", "failure_category": "", "note": ""}),
        200,
    )
    rerun = _expect_status(
        client.post(
            f"/api/generation/jobs/{created['job_id']}/rerun",
            json={"idempotency_key": "rerun-1", "prompt": "Override prompt", "duration_seconds": 10},
        ),
        200,
    )
    assert rerun["new_job"]["attempt_number"] == 2
    after_rerun = _expect_status(client.get(f"/api/chapters/{chapter_id}/results"), 200)
    assert after_rerun[0]["results"][0]["result_id"] == result["result_id"]

    def seed_orphaned_submitting():
        store = client.app.state.product_store
        runtime = client.app.state.runtime_store
        orphan = store.create_generation_job(
            provider="agnes",
            job_type="video",
            project_id=created["project_id"],
            chapter_id=chapter_id,
            shot_id="SHOT_001",
            prompt_revision_id=revision_id,
            idempotency_key="orphan",
            request_hash="orphan-hash",
            request_object_id=runtime.write_text_object("{}"),
            attempt_number=3,
        )
        orphan = store.transition_generation_job(orphan.job_id, "queued")
        return store.transition_generation_job(orphan.job_id, "submitting").job_id

    orphan_id = client.portal.call(seed_orphaned_submitting)
    recovered = client.portal.call(client.app.state.generation_poller.run_cycle)
    assert recovered.submission_outcome_unknown == 1
    orphan = _expect_status(client.get(f"/api/generation/jobs/{orphan_id}"), 200)
    assert orphan["error_code"] == "submission_outcome_unknown"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-drama-m3-") as tmp:
        app = create_app(data_root=Path(tmp) / "runtime-data", skills_root="skills")
        app.state.settings.public_base_url = "https://assets.example.test"
        with TestClient(app) as client:
            _run_workflow(client)
    print("M3_AGNES_GENERATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
