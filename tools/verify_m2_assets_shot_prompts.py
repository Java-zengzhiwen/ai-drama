#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r"Using `httpx` with `starlette\.testclient` is deprecated.*")

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_drama_web.app import create_app


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
    if status_code == 204:
        return None
    return response.json()


def _create_profile(client: TestClient, project_id: str, chapter_id: str, profile_type: str, name: str):
    payload = {
        "name": name,
        "continuity_notes": f"{name} continuity",
    }
    if profile_type == "character":
        payload.update({"identity_notes": f"{name} identity", "appearance_notes": "", "costume_notes": "blue robe"})
    elif profile_type == "scene":
        payload.update({"scene_layout_notes": f"{name} layout", "lighting_notes": "soft daylight"})
    elif profile_type == "prop":
        payload.update({"prop_handling_notes": "kept in sleeve"})
    response = client.post(
        f"/api/projects/{project_id}/profiles",
        json={"chapter_id": chapter_id, "profile_type": profile_type, "payload": payload},
    )
    return _expect_status(response, 200)


def _upload_asset(client: TestClient, chapter_id: str, asset_type: str, name: str):
    return _expect_status(
        client.post(
            f"/api/chapters/{chapter_id}/assets",
            data={"asset_type": asset_type, "name": name},
            files={"file": ("reference.png", PNG_BYTES, "image/png")},
        ),
        200,
    )


def _generate_asset(client: TestClient, chapter_id: str, asset_type: str, name: str):
    return _expect_status(
        client.post(
            f"/api/chapters/{chapter_id}/assets/generate-image",
            json={
                "asset_type": asset_type,
                "name": name,
                "prompt": f"{name} stable reference",
                "size": "512x512",
            },
        ),
        200,
    )


def _make_current(client: TestClient, asset_id: str, target_type: str, target_id: str, role: str):
    _expect_status(client.post(f"/api/assets/{asset_id}/mark-usable"), 200)
    return _expect_status(
        client.post(
            f"/api/assets/{asset_id}/bindings",
            json={"target_type": target_type, "target_id": target_id, "role": role, "is_current": True},
        ),
        200,
    )


def _run_workflow(client: TestClient):
    project = _expect_status(
        client.post(
            "/api/projects",
            json={
                "name": "M2 Verification",
                "description": "古装重生短剧",
                "series_canon": "明代商贾世界",
                "characters_context": "沈清荷、沈清莲、顾长渊",
                "production_brief": "真人写实，16:9，低饱和",
            },
        ),
        200,
    )
    chapter = _expect_status(
        client.post(f"/api/projects/{project['project_id']}/chapters", json={"title": "第一章", "position": 1}),
        200,
    )
    _expect_status(
        client.post(
            f"/api/chapters/{chapter['chapter_id']}/source-revisions",
            json={"content": "沈清荷在正厅藏起玉佩，准备重新查账。"},
        ),
        200,
    )
    script = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate"), 200)
    _expect_status(client.post(f"/api/script-revisions/{script['revision_id']}/approve"), 200)
    storyboard = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/storyboard/generate"), 200)
    _expect_status(client.post(f"/api/storyboard-revisions/{storyboard['revision_id']}/approve"), 200)

    character = _create_profile(client, project["project_id"], chapter["chapter_id"], "character", "CHAR_SHEN_QINGHE")
    scene_one = _create_profile(client, project["project_id"], chapter["chapter_id"], "scene", "SCENE_001")
    scene_two = _create_profile(client, project["project_id"], chapter["chapter_id"], "scene", "SCENE_002")

    status = _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)
    assert status["status"] == "assets_incomplete"

    missing = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/asset-requirements/analyze"), 200)
    assert missing["status"] == "missing_assets"

    character_asset = _upload_asset(client, chapter["chapter_id"], "character_reference", "CHAR_SHEN_QINGHE upload")
    scene_one_asset = _generate_asset(client, chapter["chapter_id"], "scene_reference", "SCENE_001 generated")
    scene_two_asset = _upload_asset(client, chapter["chapter_id"], "scene_reference", "SCENE_002 upload")
    shot_one_asset = _upload_asset(client, chapter["chapter_id"], "shot_keyframe", "SHOT_001 keyframe")
    shot_two_asset = _upload_asset(client, chapter["chapter_id"], "shot_keyframe", "SHOT_002 keyframe")

    generated_content = client.get(f"/api/assets/{scene_one_asset['asset_id']}/content")
    if generated_content.status_code != 200:
        raise AssertionError(f"expected generated image content, got {generated_content.status_code}: {generated_content.text}")
    assert generated_content.content == PNG_BYTES
    _make_current(client, character_asset["asset_id"], "character", character["profile_id"], "primary_reference")
    _make_current(client, scene_one_asset["asset_id"], "scene", scene_one["profile_id"], "layout_reference")
    _make_current(client, scene_two_asset["asset_id"], "scene", scene_two["profile_id"], "layout_reference")
    _make_current(client, shot_one_asset["asset_id"], "shot", "SHOT_001", "keyframe")
    _make_current(client, shot_two_asset["asset_id"], "shot", "SHOT_002", "keyframe")

    ready = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/asset-requirements/analyze"), 200)
    assert ready["status"] == "ready"
    assert [row["status"] for row in ready["shot_rows"]] == ["ready", "ready"]
    status = _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)
    assert status["status"] == "assets_ready"

    prompt = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/shot-prompts/generate"), 200)
    assert prompt["readiness"]["SHOT_001"]["status"] == "draft"
    assert prompt["readiness"]["SHOT_002"]["status"] == "draft"
    status = _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)
    assert status["status"] == "prompts_draft"

    preview = _expect_status(
        client.get(f"/api/shot-prompt-revisions/{prompt['revision_id']}/shots/SHOT_001/agnes-preview"),
        200,
    )
    assert preview["asset_refs"] == prompt["shots"][0]["asset_refs"]

    ready_prompt = _expect_status(
        client.post(f"/api/shot-prompt-revisions/{prompt['revision_id']}/shots/SHOT_001/mark-ready"),
        200,
    )
    assert ready_prompt["readiness"]["SHOT_001"]["status"] == "ready"
    status = _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)
    assert status == {"status": "prompts_draft", "blocking_reason": "", "next_action": "mark_shot_prompts_ready"}
    _expect_status(
        client.post(f"/api/shot-prompt-revisions/{prompt['revision_id']}/shots/SHOT_002/mark-ready"),
        200,
    )
    status = _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)
    assert status == {"status": "prompts_ready", "blocking_reason": "", "next_action": "m2_complete"}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-drama-m2-") as tmp:
        app = create_app(data_root=Path(tmp) / "runtime-data", skills_root="skills")
        with TestClient(app) as client:
            _run_workflow(client)
    print("M2_ASSETS_SHOT_PROMPTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
