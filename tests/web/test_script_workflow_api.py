import hashlib
import sqlite3
import uuid


VALID_EDITED_SCRIPT = """# Edited Drama Script Revision

runtime_model: manual-edit
source_basis: web

## Scene: 1-1

【画面】
女主在清晨醒来，确认自己回到旧日房间，桌上的账册仍在原位。

【动作】
她先压住惊慌，再把账册、发簪和信笺依次收好，准备重新布局。

【台词】
女主：这一世，我要先看清局，再决定谁能留下。
"""


def _create_chapter_with_source(client):
    project = client.post(
        "/api/projects",
        json={
            "name": "生死",
            "description": "古装重生短剧",
            "series_canon": "明代商贾世界",
            "characters_context": "沈清荷、沈清莲、顾长渊",
            "production_brief": "真人写实，16:9，低饱和",
        },
    ).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    client.post(
        f"/api/chapters/{chapter['chapter_id']}/source-revisions",
        json={"content": "沈清荷醒来后发现自己回到成亲前，她决定重新查账。"},
    )
    return project, chapter


def _write_text_object(objects_root, text):
    data = text.encode("utf-8")
    object_id = hashlib.sha256(data).hexdigest()
    directory = objects_root / object_id[:2]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / object_id
    if not path.exists():
        path.write_bytes(data)
    return object_id


def _insert_validation_row(app, revision_id, status, index):
    objects_root = app.state.settings.data_root / "objects"
    stdout_object_id = _write_text_object(objects_root, "")
    stderr_object_id = _write_text_object(objects_root, "")
    report_object_id = _write_text_object(objects_root, "{}")
    with sqlite3.connect(app.state.settings.data_root / "runtime.db") as conn:
        conn.execute(
            """
            INSERT INTO validation_results
            (validation_id, revision_id, validator_id, validator_name, status, required,
             exit_code, error_code, duration_ms, stdout_object_id, stderr_object_id,
             report_object_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                revision_id,
                "rerun_validator",
                "rerun_validator",
                status,
                1,
                0 if status == "PASS" else 1,
                "" if status == "PASS" else "ERR_RERUN",
                1,
                stdout_object_id,
                stderr_object_id,
                report_object_id,
                "2026-07-05T13:36:%02dZ" % index,
            ),
        )


def test_script_workflow_generates_lists_edits_and_approves_current_revision(client):
    project, chapter = _create_chapter_with_source(client)

    generated_response = client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate")

    assert generated_response.status_code == 200
    generated = generated_response.json()
    assert generated["artifact_id"] == f"{chapter['chapter_id']}:script"
    assert generated["chapter_id"] == chapter["chapter_id"]
    assert generated["approval_status"] == "pending"
    assert generated["current"] is False
    assert "Mock Drama Script Revision" in generated["content"]
    assert {item["validator_id"]: item["status"] for item in generated["validation_results"]}[
        "runtime_script_revision_structure"
    ] == "PASS"

    revisions_response = client.get(f"/api/chapters/{chapter['chapter_id']}/script/revisions")
    assert revisions_response.status_code == 200
    assert [item["revision_id"] for item in revisions_response.json()] == [generated["revision_id"]]

    edited_response = client.put(
        f"/api/script-revisions/{generated['revision_id']}",
        json={"content": VALID_EDITED_SCRIPT},
    )

    assert edited_response.status_code == 200
    edited = edited_response.json()
    assert edited["revision_id"] != generated["revision_id"]
    assert edited["artifact_id"] == generated["artifact_id"]
    assert edited["approval_status"] == "pending"
    assert edited["current"] is False
    assert edited["content"] == VALID_EDITED_SCRIPT
    assert {item["validator_id"]: item["status"] for item in edited["validation_results"]}[
        "runtime_script_revision_structure"
    ] == "PASS"

    approved_response = client.post(f"/api/script-revisions/{edited['revision_id']}/approve")

    assert approved_response.status_code == 200
    approved = approved_response.json()
    assert approved["revision_id"] == edited["revision_id"]
    assert approved["approval_status"] == "approved"
    assert approved["current"] is True

    revisions = client.get(f"/api/chapters/{chapter['chapter_id']}/script/revisions").json()
    by_id = {item["revision_id"]: item for item in revisions}
    assert by_id[generated["revision_id"]]["approval_status"] == "pending"
    assert by_id[generated["revision_id"]]["current"] is False
    assert by_id[edited["revision_id"]]["approval_status"] == "approved"
    assert by_id[edited["revision_id"]]["current"] is True


def test_script_workflow_maps_gate_and_approval_errors(client):
    project = client.post("/api/projects", json={"name": "生死"}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()

    blocked_generate = client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate")

    assert blocked_generate.status_code == 409
    assert blocked_generate.json() == {
        "error_code": "SOURCE_REVISION_REQUIRED",
        "error_message": "chapter source revision is required",
    }

    _, sourced_chapter = _create_chapter_with_source(client)
    generated = client.post(f"/api/chapters/{sourced_chapter['chapter_id']}/script/generate").json()
    invalid_edit = client.put(
        f"/api/script-revisions/{generated['revision_id']}",
        json={"content": "# too short"},
    ).json()

    blocked_approval = client.post(f"/api/script-revisions/{invalid_edit['revision_id']}/approve")

    assert blocked_approval.status_code == 422
    assert blocked_approval.json()["error_code"] == "APPROVAL_BLOCKED"
    assert "required validators did not pass" in blocked_approval.json()["error_message"]


def test_script_workflow_maps_runtime_failure_without_500(tmp_path):
    from fastapi.testclient import TestClient

    from ai_drama_web.app import create_app

    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    app.state.settings.runtime_provider = "unsupported-provider"
    with TestClient(app) as test_client:
        _, chapter = _create_chapter_with_source(test_client)

        response = test_client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate")

    assert response.status_code == 502
    assert response.json()["error_code"] == "RUNTIME_PROVIDER_ERROR"
    assert response.json()["error_message"]


def test_script_workflow_resolves_skills_when_started_outside_repo(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from ai_drama_web.app import create_app

    monkeypatch.chdir(tmp_path)
    app = create_app(data_root=tmp_path / "runtime-data")
    with TestClient(app) as test_client:
        _, chapter = _create_chapter_with_source(test_client)

        response = test_client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate")

    assert response.status_code == 200
    assert response.json()["validation_results"]


def test_script_revision_response_keeps_full_validation_history(client):
    _, chapter = _create_chapter_with_source(client)
    generated = client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate").json()
    _insert_validation_row(client.app, generated["revision_id"], "FAIL", 1)
    _insert_validation_row(client.app, generated["revision_id"], "PASS", 2)

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/script/revisions")

    validation_rows = response.json()[0]["validation_results"]
    rerun_statuses = [
        item["status"]
        for item in validation_rows
        if item["validator_id"] == "rerun_validator"
    ]
    assert rerun_statuses == ["FAIL", "PASS"]


def test_script_workflow_rejects_revision(client):
    _, chapter = _create_chapter_with_source(client)
    generated = client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate").json()

    rejected_response = client.post(
        f"/api/script-revisions/{generated['revision_id']}/reject",
        json={"reviewer": "producer", "note": "needs tighter scene action"},
    )

    assert rejected_response.status_code == 200
    rejected = rejected_response.json()
    assert rejected["revision_id"] == generated["revision_id"]
    assert rejected["approval_status"] == "rejected"
    assert rejected["current"] is False
