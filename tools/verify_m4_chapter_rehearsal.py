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


class M4RehearsalBackend:
    def __init__(self):
        self.created = []
        self.by_provider_job_id = {}

    def create_video_job(self, request):
        shot_id = "SHOT_002" if "SHOT_002" in request.prompt else "SHOT_001"
        attempt = 1 + sum(1 for item in self.created if item["shot_id"] == shot_id)
        provider_job_id = f"m4-{shot_id.lower()}-attempt-{attempt}"
        self.created.append({"provider_job_id": provider_job_id, "shot_id": shot_id, "attempt": attempt})
        self.by_provider_job_id[provider_job_id] = {"shot_id": shot_id, "attempt": attempt}
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="submitted",
            raw={"provider": "m4-rehearsal", "shot_id": shot_id, "attempt": attempt},
        )

    def get_video_job_status(self, provider_job_id):
        job = self.by_provider_job_id[provider_job_id]
        if job["shot_id"] == "SHOT_002" and job["attempt"] == 1:
            return ProviderJob(
                provider_job_id=provider_job_id,
                status="failed",
                raw={"provider": "m4-rehearsal", "status": "failed", "failure_category": "generation_failed"},
            )
        return ProviderJob(
            provider_job_id=provider_job_id,
            status="completed",
            raw={"provider": "m4-rehearsal", "status": "completed"},
        )

    def fetch_video_result(self, provider_job_id):
        job = self.by_provider_job_id[provider_job_id]
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="video/mp4",
            url=f"https://cdn.example.test/m4/{job['shot_id'].lower()}-{job['attempt']}.mp4",
            content=f"m4-video-bytes:{job['shot_id']}:{job['attempt']}".encode("utf-8"),
            raw={"provider": "m4-rehearsal", "shot_id": job["shot_id"], "attempt": job["attempt"]},
        )

    def get_job_status(self, provider_job_id):
        return self.get_video_job_status(provider_job_id)

    def fetch_result(self, provider_job_id):
        return self.fetch_video_result(provider_job_id)


def _install_backend(client: TestClient, backend: M4RehearsalBackend):
    client.app.state.generation_backend = backend
    client.app.state.generation_poller.backend = backend
    client.app.state.generation_poller.execution_service.backend = backend


def _seed_rehearsal(client: TestClient):
    def seed():
        runtime = client.app.state.runtime_store
        store = client.app.state.product_store
        project = store.create_project(name="M4 Chapter Rehearsal")
        chapter = store.create_chapter(project.project_id, "Mock Chapter", 1)
        character = store.create_uploaded_asset(
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            asset_type="character_reference",
            name="Character Reference",
            data=PNG_BYTES,
            media_type="image/png",
            metadata={},
        )
        character = store.update_asset_status(character.asset_id, "usable")
        keyframe = store.create_uploaded_asset(
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            asset_type="shot_keyframe",
            name="Shot Keyframe",
            data=PNG_BYTES,
            media_type="image/png",
            metadata={},
        )
        keyframe = store.update_asset_status(keyframe.asset_id, "usable")
        canonical = {
            "schema_version": "shot-prompt-canonical-v1",
            "project_id": project.project_id,
            "chapter_id": chapter.chapter_id,
            "source_storyboard_revision_id": "storyboard-rehearsal-1",
            "shots": [
                _shot("SHOT_001", 1, [character.asset_id, keyframe.asset_id]),
                _shot("SHOT_002", 2, [character.asset_id, keyframe.asset_id]),
            ],
        }
        text = serialize_shot_prompt_json(canonical).decode("utf-8")
        content_hash = shot_prompt_content_hash(canonical)
        content_object_id = runtime.write_text_object(text)
        run = runtime.create_run(
            artifact_id=f"{chapter.chapter_id}:shot-prompts",
            project_id=project.project_id,
            chapter_id=chapter.chapter_id,
            skill_id="m4-rehearsal-shot-prompt",
            skill_version="1",
            skill_hash="",
            runtime="verify",
            provider="mock",
            model="mock",
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
            skill_id="m4-rehearsal-shot-prompt",
            skill_version="1",
            skill_package_hash="",
            runtime_provider="verify",
            runtime_model="mock",
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=content_object_id,
            parser_version=CANONICAL_PARSER_VERSION,
            content_profile=CONTENT_PROFILE,
        )
        for shot_id in ("SHOT_001", "SHOT_002"):
            runtime.insert_review_record_with_opened_event(
                artifact_id="artifact",
                revision_id=revision.revision_id,
                scope="shot",
                shot_id=shot_id,
                body=json.dumps(
                    {
                        "schema_version": "shot-prompt-readiness-v1",
                        "status": "ready",
                        "revision_id": revision.revision_id,
                        "shot_id": shot_id,
                        "content_hash": content_hash,
                        "marked_at": now_iso(),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                blocking=False,
                created_by="m4-rehearsal",
                note="ready",
            )
        return {
            "project_id": project.project_id,
            "chapter_id": chapter.chapter_id,
            "revision_id": revision.revision_id,
            "asset_ids": [character.asset_id, keyframe.asset_id],
        }

    return client.portal.call(seed)


def _shot(shot_id: str, order: int, asset_refs: list[str]) -> dict:
    return {
        "shot_id": shot_id,
        "shot_order": order,
        "duration_seconds": 5,
        "scene_id": "SCENE_001",
        "character_ids": ["CHAR_001"],
        "prop_ids": [],
        "asset_refs": asset_refs,
        "camera": {"shot_size": "medium"},
        "action": f"{shot_id} rehearsal action",
        "emotion": "focused",
        "dialogue": [],
        "positive_prompt": f"{shot_id} rehearsal prompt.",
        "negative_prompt": "warped face",
        "continuity_notes": ["keep blocking stable"],
        "agnes_video_params": {"num_frames": 121, "frame_rate": 24},
    }


def _run_rehearsal(client: TestClient) -> dict:
    backend = M4RehearsalBackend()
    _install_backend(client, backend)
    seeded = _seed_rehearsal(client)
    chapter_id = seeded["chapter_id"]
    revision_id = seeded["revision_id"]

    source_jobs = {}
    for shot_id in ("SHOT_001", "SHOT_002"):
        source_jobs[shot_id] = _expect_status(
            client.post(
                f"/api/chapters/{chapter_id}/generation/video-jobs",
                json={
                    "prompt_revision_id": revision_id,
                    "shot_id": shot_id,
                    "idempotency_key": f"m4-source-{shot_id}",
                },
            ),
            200,
        )
    _run_cycles(client, 3)

    results = _expect_status(client.get(f"/api/chapters/{chapter_id}/results"), 200)
    shot_001_result = _only_result(results, "SHOT_001")
    _expect_status(client.post(f"/api/shots/SHOT_001/results/{shot_001_result['result_id']}/select"), 200)
    shot_001_review = _expect_status(
        client.post(
            f"/api/results/{shot_001_result['result_id']}/review",
            json={"decision": "passed", "failure_category": "", "note": "M4 source pass"},
        ),
        200,
    )

    failed_job = _expect_status(client.get(f"/api/generation/jobs/{source_jobs['SHOT_002']['job_id']}"), 200)
    assert failed_job["internal_status"] == "failed"
    assert failed_job["error_code"] == "generation_failed"
    rerun = _expect_status(
        client.post(
            f"/api/generation/jobs/{failed_job['job_id']}/rerun",
            json={"idempotency_key": "m4-rerun-SHOT_002", "prompt": "SHOT_002 rerun rehearsal prompt."},
        ),
        200,
    )
    rerun_job = rerun["new_job"]
    _run_cycles(client, 2)
    final_results = _expect_status(client.get(f"/api/chapters/{chapter_id}/results"), 200)
    shot_002_result = _only_result(final_results, "SHOT_002")
    _expect_status(client.post(f"/api/shots/SHOT_002/results/{shot_002_result['result_id']}/select"), 200)
    shot_002_review = _expect_status(
        client.post(
            f"/api/results/{shot_002_result['result_id']}/review",
            json={"decision": "passed", "failure_category": "", "note": "M4 rerun pass"},
        ),
        200,
    )

    return client.portal.call(
        _build_report,
        client,
        seeded,
        source_jobs,
        shot_001_result,
        shot_001_review,
        failed_job,
        rerun_job,
        shot_002_result,
        shot_002_review,
    )


def _run_cycles(client: TestClient, count: int) -> None:
    for _index in range(count):
        client.portal.call(client.app.state.generation_poller.run_cycle)


def _only_result(results: list[dict], shot_id: str) -> dict:
    group = next(item for item in results if item["shot_id"] == shot_id)
    if len(group["results"]) != 1:
        raise AssertionError(f"expected one result for {shot_id}, got {len(group['results'])}")
    return group["results"][0]


def _build_report(
    client: TestClient,
    seeded: dict,
    source_jobs: dict,
    shot_001_result: dict,
    shot_001_review: dict,
    failed_job: dict,
    rerun_job: dict,
    shot_002_result: dict,
    shot_002_review: dict,
) -> dict:
    store = client.app.state.product_store
    shot_ids = ("SHOT_001", "SHOT_002")
    jobs_by_shot = {}
    for shot_id in shot_ids:
        rows = store.conn.execute(
            "SELECT * FROM generation_jobs WHERE chapter_id = ? AND shot_id = ? ORDER BY attempt_number ASC",
            (seeded["chapter_id"], shot_id),
        ).fetchall()
        jobs_by_shot[shot_id] = [dict(row) for row in rows]
    result_versions = {}
    local_content_urls = {}
    object_ids = {}
    current_selection = {}
    for shot_id in shot_ids:
        result_versions[shot_id] = []
        for result in store.list_generation_results_for_shot(seeded["chapter_id"], shot_id):
            result_versions[shot_id].append({"result_id": result.result_id, "job_id": result.job_id})
            local_content_urls[result.result_id] = f"/api/results/{result.result_id}/content"
            object_ids[result.result_id] = result.object_id
        selection = store.current_generation_result_selection(seeded["chapter_id"], shot_id)
        current_selection[shot_id] = "" if selection is None else selection.result_id

    report = {
        "project_id": seeded["project_id"],
        "chapter_id": seeded["chapter_id"],
        "shot_prompt_revision_id": seeded["revision_id"],
        "asset_ids": seeded["asset_ids"],
        "source_job_id": source_jobs["SHOT_001"]["job_id"],
        "source_result_id": shot_001_result["result_id"],
        "selected_result_id": shot_001_result["result_id"],
        "review_id": shot_001_review["review_id"],
        "rerun_job_id": rerun_job["job_id"],
        "rerun_result_id": shot_002_result["result_id"],
        "attempt_numbers": {
            shot_id: [job["attempt_number"] for job in jobs_by_shot[shot_id]]
            for shot_id in shot_ids
        },
        "job_status_timeline": {
            shot_id: [
                {
                    "job_id": job["job_id"],
                    "attempt_number": job["attempt_number"],
                    "status": job["internal_status"],
                    "error_code": job["error_code"],
                }
                for job in jobs_by_shot[shot_id]
            ]
            for shot_id in shot_ids
        },
        "result_versions": result_versions,
        "current_selection": current_selection,
        "failure_categories_tested": ["generation_failed"],
        "local_content_urls": local_content_urls,
        "object_ids": object_ids,
        "verification_summary": {
            "source_material": True,
            "generation_queue": True,
            "persistent_poller": True,
            "local_result_persistence": True,
            "result_selection": True,
            "review": True,
            "rerun": True,
            "version_history": True,
            "real_agnes_request_made": False,
        },
        "shot_002_review_id": shot_002_review["review_id"],
        "shot_002_failed_source_job_id": failed_job["job_id"],
    }
    assert current_selection["SHOT_001"] == shot_001_result["result_id"]
    assert current_selection["SHOT_002"] == shot_002_result["result_id"]
    assert jobs_by_shot["SHOT_002"][0]["internal_status"] == "failed"
    assert jobs_by_shot["SHOT_002"][1]["internal_status"] == "completed"
    return report


def _write_reports(report: dict) -> tuple[Path, Path]:
    report_dir = REPO_ROOT / "runtime-data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "m4-chapter-rehearsal-report.json"
    md_path = report_dir / "m4-chapter-rehearsal-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# M4 Chapter Rehearsal Report",
                "",
                f"- project_id: `{report['project_id']}`",
                f"- chapter_id: `{report['chapter_id']}`",
                f"- shot_prompt_revision_id: `{report['shot_prompt_revision_id']}`",
                f"- source_job_id: `{report['source_job_id']}`",
                f"- source_result_id: `{report['source_result_id']}`",
                f"- rerun_job_id: `{report['rerun_job_id']}`",
                f"- rerun_result_id: `{report['rerun_result_id']}`",
                "- real_agnes_request_made: `false`",
                "",
                "## Verification Summary",
                "",
                *[
                    f"- {key}: `{value}`"
                    for key, value in report["verification_summary"].items()
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return json_path, md_path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-drama-m4-") as tmp:
        app = create_app(data_root=Path(tmp) / "runtime-data", skills_root="skills")
        app.state.settings.public_base_url = "https://assets.example.test"
        with TestClient(app) as client:
            report = _run_rehearsal(client)
    json_path, md_path = _write_reports(report)
    print(f"report_json={json_path}")
    print(f"report_md={md_path}")
    print("M4_CHAPTER_REHEARSAL_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
