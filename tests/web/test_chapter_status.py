import pytest

from ai_drama_runtime.shot_prompt_canonical import parse_shot_prompt_json


def _create_chapter_with_source(client):
    project = client.post("/api/projects", json={"name": "生死"}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    client.post(
        f"/api/chapters/{chapter['chapter_id']}/source-revisions",
        json={"content": "沈清荷醒来后发现自己回到成亲前。"},
    )
    return chapter


def _insert_revision(client, chapter, artifact_suffix, artifact_type, approval_status="pending"):
    from ai_drama_runtime.store import RuntimeStore

    data_root = client.app.state.settings.data_root
    store = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    artifact_id = f"{chapter['chapter_id']}:{artifact_suffix}"
    try:
        content = f"{artifact_type} revision"
        content_object_id = store.write_text_object(content)
        request_object_id = store.write_text_object("{}")
        run = store.create_run(
            artifact_id=artifact_id,
            project_id=chapter["project_id"],
            chapter_id=chapter["chapter_id"],
            skill_id="test-skill",
            skill_version="1",
            skill_hash="test-hash",
            runtime="manual",
            provider="local-test",
            model="status-test",
            status="SUCCEEDED",
            request_object_id=request_object_id,
            input_hash=content_object_id,
        )
        revision = store.insert_revision(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            project_id=chapter["project_id"],
            chapter_id=chapter["chapter_id"],
            run_id=run.run_id,
            skill_id=run.skill_id,
            skill_version=run.skill_version,
            skill_package_hash=run.skill_hash,
            runtime_provider=run.provider,
            runtime_model=run.model,
            content_object_id=content_object_id,
            content_hash=content_object_id,
            raw_response_object_id=content_object_id,
            parser_version="test-parser",
        )
        if approval_status == "approved":
            store.approve_in_transaction(revision, reviewer="local-user", note="")
            revision = store.current_approved(artifact_id)
        elif approval_status == "rejected":
            store.record_rejection(revision, reviewer="local-user", note="")
            revision = store.get_revision(revision.revision_id)
        return revision
    finally:
        store.close()


def _arrange_status(client, status):
    chapter = _create_chapter_with_source(client)
    if status in {"script_draft", "script_approved", "storyboard_draft", "storyboard_approved"}:
        _insert_revision(
            client,
            chapter,
            "script",
            "drama_script",
            approval_status="approved"
            if status in {"script_approved", "storyboard_draft", "storyboard_approved"}
            else "pending",
        )
    if status in {"storyboard_draft", "storyboard_approved"}:
        _insert_revision(
            client,
            chapter,
            "script:storyboard",
            "storyboard",
            approval_status="approved" if status == "storyboard_approved" else "pending",
        )
    return chapter


@pytest.mark.parametrize(
    ("status", "next_action"),
    [
        ("source_ready", "generate_script"),
        ("script_draft", "approve_script"),
        ("script_approved", "generate_storyboard"),
        ("storyboard_draft", "approve_storyboard"),
        ("assets_incomplete", "analyze_assets"),
    ],
)
def test_chapter_status_is_derived_from_source_and_artifact_revisions(client, status, next_action):
    chapter = _arrange_status(client, "storyboard_approved" if status == "assets_incomplete" else status)
    if status == "assets_incomplete":
        from tests.web.test_shot_prompt_api import _storyboard_canonical

        storyboard = _storyboard_canonical(chapter["project_id"], chapter["chapter_id"])
        _replace_approved_storyboard(client, chapter, storyboard)

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": status,
        "blocking_reason": "asset requirements are not ready" if status == "assets_incomplete" else "",
        "next_action": next_action,
    }


def test_chapter_status_is_not_manually_writable(client):
    chapter = _create_chapter_with_source(client)

    response = client.post(
        f"/api/chapters/{chapter['chapter_id']}/status",
        json={"status": "storyboard_approved"},
    )

    assert response.status_code == 405


def test_chapter_status_returns_404_for_missing_chapter(client):
    response = client.get("/api/chapters/missing/status")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("artifact_suffix", "artifact_type", "draft_status", "approve_action"),
    [
        ("script", "drama_script", "script_draft", "approve_script"),
        ("script:storyboard", "storyboard", "storyboard_draft", "approve_storyboard"),
    ],
)
def test_rejected_revisions_are_not_actionable_drafts(
    client,
    artifact_suffix,
    artifact_type,
    draft_status,
    approve_action,
):
    chapter = _create_chapter_with_source(client)
    if artifact_type == "storyboard":
        _insert_revision(client, chapter, "script", "drama_script", approval_status="approved")
    _insert_revision(client, chapter, artifact_suffix, artifact_type, approval_status="rejected")

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    assert response.status_code == 200
    assert response.json()["status"] != draft_status
    assert response.json()["next_action"] != approve_action


def test_superseded_storyboard_draft_does_not_hide_current_approved_script(client):
    chapter = _create_chapter_with_source(client)
    _insert_revision(client, chapter, "script", "drama_script", approval_status="approved")
    storyboard = _insert_revision(client, chapter, "script:storyboard", "storyboard", approval_status="approved")
    _insert_revision(client, chapter, "script:storyboard", "storyboard", approval_status="approved")

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    from ai_drama_runtime.store import RuntimeStore

    data_root = client.app.state.settings.data_root
    store = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    try:
        assert store.get_revision(storyboard.revision_id).approval_status == "superseded"
    finally:
        store.close()
    assert response.status_code == 200
    assert response.json()["status"] == "assets_incomplete"


def test_chapter_status_derives_milestone_2_asset_and_prompt_states(client):
    from tests.web.test_shot_prompt_api import (
        _create_ready_requirements,
        _generate,
        _storyboard_canonical,
    )

    chapter = _arrange_status(client, "storyboard_approved")
    storyboard = _storyboard_canonical(chapter["project_id"], chapter["chapter_id"])
    storyboard_revision = _replace_approved_storyboard(client, chapter, storyboard)

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")
    assert response.status_code == 200
    assert response.json() == {
        "status": "assets_incomplete",
        "blocking_reason": "asset requirements are not ready",
        "next_action": "analyze_assets",
    }

    _create_ready_requirements(client, chapter["chapter_id"], storyboard_revision, storyboard)

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")
    assert response.status_code == 200
    assert response.json() == {
        "status": "assets_ready",
        "blocking_reason": "",
        "next_action": "generate_shot_prompts",
    }

    generated = _generate(client, chapter["chapter_id"])

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")
    assert response.status_code == 200
    assert response.json() == {
        "status": "prompts_draft",
        "blocking_reason": "",
        "next_action": "mark_shot_prompts_ready",
    }

    shot = parse_shot_prompt_json(generated["content"])["shots"][0]
    ready = client.post(
        f"/api/shot-prompt-revisions/{generated['revision_id']}/shots/{shot['shot_id']}/mark-ready"
    )
    assert ready.status_code == 200, ready.text

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")
    assert response.status_code == 200
    assert response.json() == {
        "status": "prompts_ready",
        "blocking_reason": "",
        "next_action": "m2_complete",
    }


def test_chapter_status_requires_asset_requirements_to_match_storyboard_hash(client):
    from ai_drama_runtime.store import RuntimeStore
    from ai_drama_web.store import ProductStore
    from tests.web.test_shot_prompt_api import _storyboard_canonical

    chapter = _arrange_status(client, "storyboard_approved")
    storyboard = _storyboard_canonical(chapter["project_id"], chapter["chapter_id"])
    storyboard_revision = _replace_approved_storyboard(client, chapter, storyboard)
    data_root = client.app.state.settings.data_root
    with RuntimeStore(data_root / "runtime.db", data_root / "objects") as runtime_store:
        ProductStore(runtime_store).create_asset_requirement_set(
            chapter_id=chapter["chapter_id"],
            storyboard_revision_id=storyboard_revision.revision_id,
            payload={
                "status": "ready",
                "storyboard_content_hash": "b" * 64,
                "shot_rows": [],
                "missing_assets": [],
                "asset_generation_in_progress": [],
                "asset_review_required": [],
            },
        )

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "assets_incomplete",
        "blocking_reason": "asset requirements are not ready",
        "next_action": "analyze_assets",
    }


def test_chapter_status_reports_non_canonical_storyboard_before_m2(client):
    chapter = _arrange_status(client, "storyboard_approved")

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "assets_incomplete",
        "blocking_reason": "current approved canonical storyboard is required",
        "next_action": "approve_storyboard",
    }


def test_chapter_status_ignores_shot_prompts_from_superseded_storyboard(client):
    from tests.web.test_shot_prompt_api import (
        _create_ready_requirements,
        _generate,
        _storyboard_canonical,
    )

    chapter = _arrange_status(client, "storyboard_approved")
    storyboard = _storyboard_canonical(chapter["project_id"], chapter["chapter_id"])
    first_revision = _replace_approved_storyboard(client, chapter, storyboard)
    _create_ready_requirements(client, chapter["chapter_id"], first_revision, storyboard)
    generated = _generate(client, chapter["chapter_id"])
    shot = parse_shot_prompt_json(generated["content"])["shots"][0]
    ready = client.post(
        f"/api/shot-prompt-revisions/{generated['revision_id']}/shots/{shot['shot_id']}/mark-ready"
    )
    assert ready.status_code == 200, ready.text

    updated_storyboard = _storyboard_canonical(chapter["project_id"], chapter["chapter_id"])
    updated_storyboard["shots"][0]["visual_composition"]["framing"] = "updated composition"
    second_revision = _replace_approved_storyboard(client, chapter, updated_storyboard)
    _create_ready_requirements(client, chapter["chapter_id"], second_revision, updated_storyboard)

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "assets_ready",
        "blocking_reason": "",
        "next_action": "generate_shot_prompts",
    }


def _replace_approved_storyboard(client, chapter, storyboard):
    import json

    from ai_drama_runtime.store import RuntimeStore
    from ai_drama_runtime.storyboard_canonical import (
        CANONICAL_PARSER_VERSION,
        CONTENT_PROFILE,
        canonical_storyboard_hash,
        serialize_canonical_json,
    )

    data_root = client.app.state.settings.data_root
    store = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    try:
        artifact_id = f"{chapter['chapter_id']}:script:storyboard"
        store.conn.execute("UPDATE revisions SET approval_status = 'superseded' WHERE artifact_id = ?", (artifact_id,))
        store.conn.commit()
        content = serialize_canonical_json(storyboard).decode("utf-8")
        content_object_id = store.write_text_object(content)
        content_hash = canonical_storyboard_hash(storyboard)
        request_object_id = store.write_text_object(json.dumps({"test": "chapter-status"}))
        run = store.create_run(
            artifact_id=artifact_id,
            project_id=chapter["project_id"],
            chapter_id=chapter["chapter_id"],
            skill_id="test-storyboard",
            skill_version="v0.0.0",
            skill_hash="test",
            runtime="test",
            provider="test",
            model="test",
            status="SUCCEEDED",
            request_object_id=request_object_id,
            response_object_id=content_object_id,
            input_hash=content_hash,
            request_hash=content_hash,
        )
        revision = store.insert_revision(
            artifact_id=artifact_id,
            artifact_type="storyboard",
            project_id=chapter["project_id"],
            chapter_id=chapter["chapter_id"],
            run_id=run.run_id,
            skill_id=run.skill_id,
            skill_version=run.skill_version,
            skill_package_hash=run.skill_hash,
            runtime_provider=run.provider,
            runtime_model=run.model,
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=content_object_id,
            parser_version=CANONICAL_PARSER_VERSION,
            content_profile=CONTENT_PROFILE,
        )
        store.approve_in_transaction(revision, reviewer="local-user", note="")
        return store.current_approved(artifact_id)
    finally:
        store.close()
