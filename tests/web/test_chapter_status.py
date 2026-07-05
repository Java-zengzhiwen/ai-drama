import pytest


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
        ("storyboard_approved", "open_assets"),
    ],
)
def test_chapter_status_is_derived_from_source_and_artifact_revisions(client, status, next_action):
    chapter = _arrange_status(client, status)

    response = client.get(f"/api/chapters/{chapter['chapter_id']}/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": status,
        "blocking_reason": "",
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
    assert response.json()["status"] == "storyboard_approved"
