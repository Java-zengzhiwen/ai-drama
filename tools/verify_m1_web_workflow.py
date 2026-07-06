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


SOURCE_TEXT = "沈清荷醒来后发现自己回到成亲前，她决定重新查账。"


def _expect_status(response, status_code: int):
    if response.status_code != status_code:
        raise AssertionError(f"expected {status_code}, got {response.status_code}: {response.text}")
    return response.json()


def _run_workflow(client: TestClient) -> None:
    project = _expect_status(
        client.post(
            "/api/projects",
            json={
                "name": "M1 Web Verification",
                "description": "local deterministic milestone verification",
                "series_canon": "明代商贾世界",
                "characters_context": "沈清荷、沈清莲、顾长渊",
                "production_brief": "真人写实，16:9，低饱和",
            },
        ),
        200,
    )
    chapter = _expect_status(
        client.post(
            f"/api/projects/{project['project_id']}/chapters",
            json={"title": "第一章", "position": 1},
        ),
        200,
    )
    discovered_chapters = _expect_status(client.get(f"/api/projects/{project['project_id']}/chapters"), 200)
    assert [item["chapter_id"] for item in discovered_chapters] == [chapter["chapter_id"]]

    _expect_status(
        client.post(
            f"/api/chapters/{chapter['chapter_id']}/source-revisions",
            json={"content": SOURCE_TEXT},
        ),
        200,
    )
    assert _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)["status"] == "source_ready"

    script = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate"), 200)
    assert script["approval_status"] == "pending"
    approved_script = _expect_status(client.post(f"/api/script-revisions/{script['revision_id']}/approve"), 200)
    assert approved_script["approval_status"] == "approved"
    assert _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)["status"] == "script_approved"

    storyboard = _expect_status(client.post(f"/api/chapters/{chapter['chapter_id']}/storyboard/generate"), 200)
    assert storyboard["approval_status"] == "pending"
    approved_storyboard = _expect_status(
        client.post(f"/api/storyboard-revisions/{storyboard['revision_id']}/approve"),
        200,
    )
    assert approved_storyboard["approval_status"] == "approved"

    final_status = _expect_status(client.get(f"/api/chapters/{chapter['chapter_id']}/status"), 200)
    assert final_status["status"] == "storyboard_approved"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-drama-m1-web-") as tmp:
        app = create_app(data_root=Path(tmp) / "runtime-data", skills_root="skills")
        with TestClient(app) as client:
            _run_workflow(client)
    print("M1_WEB_WORKFLOW_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
