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


def _verify_chapter_discovery_contracts() -> None:
    store_text = (REPO_ROOT / "ai_drama_web" / "store.py").read_text(encoding="utf-8")
    router_text = (REPO_ROOT / "ai_drama_web" / "routers" / "projects.py").read_text(encoding="utf-8")
    dashboard_text = (
        REPO_ROOT / "web" / "src" / "features" / "projects" / "ProjectDashboardPage.tsx"
    ).read_text(encoding="utf-8")
    e2e_text = (REPO_ROOT / "web" / "tests" / "m1-workflow.spec.ts").read_text(encoding="utf-8")

    assert "def list_chapters(" in store_text
    assert '@router.get("/projects/{project_id}/chapters"' in router_text
    assert "queryFn: async () => []" not in dashboard_text
    assert "listChapters(projectId)" in dashboard_text
    assert 'page.reload()' in e2e_text
    assert 'getByRole("link", { name: "第一章" })' in e2e_text


def _run_workflow(client: TestClient) -> tuple[str, str]:
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
    return project["project_id"], chapter["chapter_id"]


def main() -> int:
    _verify_chapter_discovery_contracts()
    with tempfile.TemporaryDirectory(prefix="ai-drama-m1-web-") as tmp:
        data_root = Path(tmp) / "runtime-data"
        app = create_app(data_root=data_root, skills_root="skills")
        with TestClient(app) as client:
            project_id, chapter_id = _run_workflow(client)
        recreated_app = create_app(data_root=data_root, skills_root="skills")
        with TestClient(recreated_app) as client:
            discovered_chapters = _expect_status(client.get(f"/api/projects/{project_id}/chapters"), 200)
            assert [item["chapter_id"] for item in discovered_chapters] == [chapter_id]
    print("M1_WEB_WORKFLOW_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
