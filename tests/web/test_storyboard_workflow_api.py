import hashlib
import json
import sqlite3


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


def _generate_script(client, chapter_id):
    response = client.post(f"/api/chapters/{chapter_id}/script/generate")
    assert response.status_code == 200
    return response.json()


def _approve_script(client, revision_id):
    response = client.post(f"/api/script-revisions/{revision_id}/approve")
    assert response.status_code == 200
    return response.json()


def _generate_storyboard_after_approving_script(client):
    _, chapter = _create_chapter_with_source(client)
    script = _generate_script(client, chapter["chapter_id"])
    _approve_script(client, script["revision_id"])
    response = client.post(f"/api/chapters/{chapter['chapter_id']}/storyboard/generate")
    assert response.status_code == 200
    return response.json()


def _delete_bundle_outputs(app, revision_id):
    with sqlite3.connect(app.state.settings.data_root / "runtime.db") as conn:
        conn.execute("DELETE FROM revision_outputs WHERE revision_id = ?", (revision_id,))


def test_storyboard_generation_requires_current_approved_script(client):
    _, chapter = _create_chapter_with_source(client)
    script = _generate_script(client, chapter["chapter_id"])

    response = client.post(f"/api/chapters/{chapter['chapter_id']}/storyboard/generate")

    assert response.status_code == 409
    assert response.json() == {
        "error_code": "SOURCE_REVISION_NOT_APPROVED",
        "error_message": "source revision is not approved",
    }
    assert script["approval_status"] == "pending"


def test_storyboard_workflow_generates_lists_edits_and_approves_current_revision(client):
    _, chapter = _create_chapter_with_source(client)
    script = _generate_script(client, chapter["chapter_id"])
    approved_script = _approve_script(client, script["revision_id"])

    generated_response = client.post(f"/api/chapters/{chapter['chapter_id']}/storyboard/generate")

    assert generated_response.status_code == 200
    generated = generated_response.json()
    assert generated["artifact_id"] == f"{chapter['chapter_id']}:script:storyboard"
    assert generated["chapter_id"] == chapter["chapter_id"]
    assert generated["approval_status"] == "pending"
    assert generated["current"] is False
    canonical = json.loads(generated["content"])
    assert canonical["schema_version"] == "storyboard-canonical-v1"
    assert canonical["source"] == {
        "script_artifact_id": approved_script["artifact_id"],
        "script_revision_id": approved_script["revision_id"],
        "script_content_hash": hashlib.sha256(approved_script["content"].encode("utf-8")).hexdigest(),
    }
    assert {item["validator_id"]: item["status"] for item in generated["validation_results"]}[
        "storyboard_canonical_schema"
    ] == "PASS"
    assert {item["validator_id"]: item["status"] for item in generated["validation_results"]}[
        "storyboard_bundle_integrity"
    ] == "PASS"

    revisions_response = client.get(f"/api/chapters/{chapter['chapter_id']}/storyboard/revisions")
    assert revisions_response.status_code == 200
    assert [item["revision_id"] for item in revisions_response.json()] == [generated["revision_id"]]

    edited_canonical = canonical.copy()
    edited_canonical["scenes"] = [scene.copy() for scene in canonical["scenes"]]
    edited_canonical["scenes"][0]["summary"] = "Shen Qinghe wakes and actively checks the old evidence."
    edited_response = client.put(
        f"/api/storyboard-revisions/{generated['revision_id']}",
        json={"content": json.dumps(edited_canonical, ensure_ascii=False)},
    )

    assert edited_response.status_code == 200
    edited = edited_response.json()
    assert edited["revision_id"] != generated["revision_id"]
    assert edited["artifact_id"] == generated["artifact_id"]
    assert edited["approval_status"] == "pending"
    assert edited["current"] is False
    assert json.loads(edited["content"])["source"] == canonical["source"]
    edited_validations = {item["validator_id"]: item["status"] for item in edited["validation_results"]}
    assert edited_validations["storyboard_canonical_schema"] == "PASS"
    assert edited_validations["storyboard_bundle_integrity"] == "PASS"

    approved_response = client.post(f"/api/storyboard-revisions/{edited['revision_id']}/approve")

    assert approved_response.status_code == 200
    approved = approved_response.json()
    assert approved["revision_id"] == edited["revision_id"]
    assert approved["approval_status"] == "approved"
    assert approved["current"] is True

    rejected_response = client.post(
        f"/api/storyboard-revisions/{generated['revision_id']}/reject",
        json={"reviewer": "producer", "note": "use edited canonical version"},
    )

    assert rejected_response.status_code == 200
    rejected = rejected_response.json()
    assert rejected["revision_id"] == generated["revision_id"]
    assert rejected["approval_status"] == "rejected"
    assert rejected["current"] is False


def test_storyboard_approve_maps_bundle_errors(client):
    generated = _generate_storyboard_after_approving_script(client)
    _delete_bundle_outputs(client.app, generated["revision_id"])

    response = client.post(f"/api/storyboard-revisions/{generated['revision_id']}/approve")

    assert response.status_code == 422
    assert response.json()["error_code"] == "BUNDLE_NOT_MATERIALIZED"
    assert response.json()["error_message"]


def test_storyboard_manual_edit_maps_bundle_materialization_errors(client, monkeypatch):
    from ai_drama_runtime.services import BundleError, RuntimeService

    generated = _generate_storyboard_after_approving_script(client)

    def fail_materialize(self, revision_id):
        raise BundleError("BUNDLE_OUTPUT_CONFLICT", "simulated bundle conflict")

    monkeypatch.setattr(RuntimeService, "materialize_storyboard_bundle", fail_materialize)

    response = client.put(
        f"/api/storyboard-revisions/{generated['revision_id']}",
        json={"content": generated["content"]},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error_code": "BUNDLE_OUTPUT_CONFLICT",
        "error_message": "simulated bundle conflict",
    }


def test_storyboard_skill_config_errors_are_stable(client, monkeypatch):
    from ai_drama_runtime.registry import DuplicateSkillError, SkillRegistry

    _, chapter = _create_chapter_with_source(client)
    script = _generate_script(client, chapter["chapter_id"])
    _approve_script(client, script["revision_id"])

    def fail_scan(roots):
        raise DuplicateSkillError("duplicate storyboard skill")

    monkeypatch.setattr(SkillRegistry, "scan", fail_scan)

    response = client.post(f"/api/chapters/{chapter['chapter_id']}/storyboard/generate")

    assert response.status_code == 503
    assert response.json() == {
        "error_code": "SKILL_CONFIG_INVALID",
        "error_message": "duplicate storyboard skill",
    }
