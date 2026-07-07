import copy
import json

from ai_drama_runtime.shot_prompt_canonical import (
    parse_shot_prompt_json,
    serialize_shot_prompt_json,
    shot_prompt_content_hash,
)
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.storyboard_canonical import (
    CONTENT_PROFILE as STORYBOARD_PROFILE,
    CANONICAL_PARSER_VERSION as STORYBOARD_PARSER_VERSION,
    canonical_storyboard_hash,
    serialize_canonical_json,
)
from ai_drama_web.store import ProductStore


def _create_project_and_chapter(client):
    project = client.post("/api/projects", json={"name": "生死账"}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    return project, chapter


def _storyboard_canonical(project_id, chapter_id, *, two_shots=False):
    canonical = {
        "schema_version": "storyboard-canonical-v1",
        "project_id": project_id,
        "chapter_id": chapter_id,
        "source": {
            "script_artifact_id": f"{chapter_id}:script",
            "script_revision_id": "script-revision-001",
            "script_content_hash": "a" * 64,
        },
        "scenes": [
            {
                "scene_id": "SCENE_MAIN_HALL",
                "scene_order": 1,
                "source_scene_reference": "1-1",
                "location": "SCENE_MAIN_HALL",
                "time": "day",
                "interior_exterior": "interior",
                "characters": ["CHAR_SHEN"],
                "summary": "Shen hides the jade token in the hall.",
            }
        ],
        "shots": [
            {
                "scene_id": "SCENE_MAIN_HALL",
                "shot_id": "SHOT_001",
                "shot_order": 1,
                "source_scene_reference": "1-1",
                "duration_seconds": 8,
                "shot_size": "medium",
                "camera_angle": "eye_level",
                "camera_movement": None,
                "visual_composition": {
                    "framing": "medium shot with jade token foreground",
                    "subject_focus": "CHAR_SHEN",
                    "background_relation": "hall screen remains still",
                    "screen_direction": "left-to-right",
                },
                "character_positions": [
                    {
                        "character_id": "CHAR_SHEN",
                        "screen_zone": "center",
                        "depth": "foreground",
                        "pose": "standing",
                        "facing": "right",
                    }
                ],
                "character_actions": [
                    {"character_id": "CHAR_SHEN", "action_order": 1, "action": "hides PROP_JADE in her sleeve"}
                ],
                "emotion_performance": [
                    {
                        "character_id": "CHAR_SHEN",
                        "emotion": "tense",
                        "intensity": "medium",
                        "performance_note": "controlled panic",
                    }
                ],
                "dialogue": [
                    {"speaker_character_id": "CHAR_SHEN", "text": "Not now.", "lip_sync_required": True}
                ],
                "sound_notes": ["quiet room tone"],
                "continuity_in": {
                    "must_preserve": ["jade token visible"],
                    "must_change": [],
                    "source_unit_or_shot_id": None,
                },
                "continuity_out": {
                    "must_preserve": ["jade token hidden"],
                    "must_change": [],
                    "source_unit_or_shot_id": None,
                },
            }
        ],
    }
    if two_shots:
        second = copy.deepcopy(canonical["shots"][0])
        second["shot_id"] = "SHOT_002"
        second["shot_order"] = 2
        second["character_actions"][0]["action"] = "keeps PROP_JADE hidden"
        second["continuity_in"]["source_unit_or_shot_id"] = "SHOT_001"
        second["continuity_out"]["source_unit_or_shot_id"] = "SHOT_001"
        canonical["shots"].append(second)
    return canonical


def _open_runtime_store(client):
    data_root = client.app.state.settings.data_root
    return RuntimeStore(data_root / "runtime.db", data_root / "objects")


def _approve_storyboard(client, canonical):
    with _open_runtime_store(client) as runtime_store:
        artifact_id = f"{canonical['chapter_id']}:script:storyboard"
        runtime_store.ensure_artifact(artifact_id, "storyboard", canonical["project_id"], canonical["chapter_id"])
        content = serialize_canonical_json(canonical).decode("utf-8")
        content_object_id = runtime_store.write_text_object(content)
        content_hash = canonical_storyboard_hash(canonical)
        run = runtime_store.create_run(
            artifact_id=artifact_id,
            project_id=canonical["project_id"],
            chapter_id=canonical["chapter_id"],
            skill_id="test-storyboard",
            skill_version="v0.0.0",
            skill_hash="test",
            runtime="test",
            provider="test",
            model="test",
            status="SUCCEEDED",
            request_object_id=content_object_id,
            response_object_id=content_object_id,
            input_hash=content_hash,
            request_hash=content_hash,
        )
        revision = runtime_store.insert_revision(
            artifact_id=artifact_id,
            artifact_type="storyboard",
            project_id=canonical["project_id"],
            chapter_id=canonical["chapter_id"],
            run_id=run.run_id,
            skill_id="test-storyboard",
            skill_version="v0.0.0",
            skill_package_hash="test",
            runtime_provider="test",
            runtime_model="test",
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=content_object_id,
            parser_version=STORYBOARD_PARSER_VERSION,
            content_profile=STORYBOARD_PROFILE,
        )
        runtime_store.approve_in_transaction(revision, "tester", "approved canonical storyboard")
        return runtime_store.get_revision(revision.revision_id)


def _with_product_store(client, callback):
    with _open_runtime_store(client) as runtime_store:
        return callback(ProductStore(runtime_store))


def _create_ready_requirements(client, chapter_id, storyboard_revision, storyboard_canonical):
    def create(store):
        character = store.create_production_profile(
            project_id=storyboard_revision.project_id,
            chapter_id=chapter_id,
            profile_type="character",
            name="CHAR_SHEN",
            payload={"name": "CHAR_SHEN", "identity_notes": "same face", "costume_notes": "blue robe"},
        )
        asset = store.create_generated_asset(
            project_id=storyboard_revision.project_id,
            chapter_id=chapter_id,
            asset_type="character_reference",
            name="CHAR_SHEN reference",
            data=b"fake-png-bytes",
            media_type="image/png",
            source_job_id="job-001",
            metadata={},
        )
        shot_asset = store.create_generated_asset(
            project_id=storyboard_revision.project_id,
            chapter_id=chapter_id,
            asset_type="shot_keyframe",
            name="SHOT keyframe",
            data=b"fake-keyframe-bytes",
            media_type="image/png",
            source_job_id="job-shot-001",
            metadata={},
        )
        store.update_asset_status(asset.asset_id, "usable")
        store.update_asset_status(shot_asset.asset_id, "usable")
        store.create_asset_binding(
            asset_id=asset.asset_id,
            target_type="character",
            target_id=character.profile_id,
            role="primary_reference",
            is_current=True,
        )
        for shot in storyboard_canonical["shots"]:
            store.create_asset_binding(
                asset_id=shot_asset.asset_id,
                target_type="shot",
                target_id=shot["shot_id"],
                role="keyframe",
                is_current=True,
            )
        payload = {
            "status": "ready",
            "storyboard_content_hash": storyboard_revision.content_hash,
            "shot_rows": [
                {
                    "shot_id": shot["shot_id"],
                    "status": "ready",
                    "ready": [
                        {
                            "need_type": "character_asset",
                            "target_type": "character",
                            "target_id": character.profile_id,
                            "role": "primary_reference",
                            "asset_type": "character_reference",
                            "asset_id": asset.asset_id,
                            "status": "ready",
                        },
                        {
                            "need_type": "shot_keyframe",
                            "target_type": "shot",
                            "target_id": shot["shot_id"],
                            "role": "keyframe",
                            "asset_type": "shot_keyframe",
                            "asset_id": shot_asset.asset_id,
                            "status": "ready",
                        }
                    ],
                    "missing_assets": [],
                    "asset_generation_in_progress": [],
                    "asset_review_required": [],
                }
                for shot in storyboard_canonical["shots"]
            ],
            "missing_assets": [],
            "asset_generation_in_progress": [],
            "asset_review_required": [],
        }
        requirement_set = store.create_asset_requirement_set(
            chapter_id=chapter_id,
            storyboard_revision_id=storyboard_revision.revision_id,
            payload=payload,
        )
        return {"asset_id": asset.asset_id, "shot_asset_id": shot_asset.asset_id, "requirement_set": requirement_set}

    return _with_product_store(client, create)


def _setup_chapter(client, *, ready_assets=True, two_shots=False):
    project, chapter = _create_project_and_chapter(client)
    storyboard = _storyboard_canonical(project["project_id"], chapter["chapter_id"], two_shots=two_shots)
    revision = _approve_storyboard(client, storyboard)
    assets = None
    if ready_assets:
        assets = _create_ready_requirements(client, chapter["chapter_id"], revision, storyboard)
    return project, chapter, revision, storyboard, assets


def _generate(client, chapter_id):
    response = client.post(f"/api/chapters/{chapter_id}/shot-prompts/generate")
    assert response.status_code == 200, response.text
    return response.json()


def test_generate_before_asset_requirements_ready_returns_conflict(client):
    _, chapter, _, _, _ = _setup_chapter(client, ready_assets=False)

    response = client.post(f"/api/chapters/{chapter['chapter_id']}/shot-prompts/generate")

    assert response.status_code == 409
    assert response.json() == {
        "error_code": "ASSET_REQUIREMENTS_NOT_READY",
        "error_message": "asset requirements are not ready",
    }


def test_generate_and_list_revisions_with_ready_assets(client):
    _, chapter, storyboard_revision, _, _ = _setup_chapter(client)

    generated = _generate(client, chapter["chapter_id"])

    assert generated["chapter_id"] == chapter["chapter_id"]
    assert generated["number"] == 1
    assert generated["approval_status"] == "pending"
    assert generated["current"] is False
    assert generated["source_storyboard_revision_id"] == storyboard_revision.revision_id
    assert generated["validation_results"][0]["status"] == "PASS"
    assert generated["readiness"]["SHOT_001"]["status"] == "draft"
    content = parse_shot_prompt_json(generated["content"])
    assert content["schema_version"] == "shot-prompt-canonical-v1"
    assert generated["shots"] == content["shots"]

    revisions = client.get(f"/api/chapters/{chapter['chapter_id']}/shot-prompts/revisions")
    assert revisions.status_code == 200, revisions.text
    assert [item["revision_id"] for item in revisions.json()] == [generated["revision_id"]]


def test_manual_edit_rejects_invalid_content_and_accepts_valid_canonical(client):
    _, chapter, _, _, _ = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])

    invalid = client.put(
        f"/api/shot-prompt-revisions/{generated['revision_id']}",
        json={"content": json.dumps({"schema_version": "shot-prompt-canonical-v1"})},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error_code"] == "INVALID_REVISION_CONTENT"

    canonical = parse_shot_prompt_json(generated["content"])
    canonical["shots"][0]["positive_prompt"] = "Edited live action prompt preserving the jade token."
    edited_content = serialize_shot_prompt_json(canonical).decode("utf-8")
    edited = client.put(
        f"/api/shot-prompt-revisions/{generated['revision_id']}",
        json={"content": edited_content},
    )

    assert edited.status_code == 200, edited.text
    payload = edited.json()
    assert payload["revision_id"] != generated["revision_id"]
    assert payload["number"] == generated["number"] + 1
    assert payload["validation_results"][0]["status"] == "PASS"
    assert payload["shots"][0]["positive_prompt"] == "Edited live action prompt preserving the jade token."


def test_manual_edit_rejects_source_identity_changes(client):
    _, chapter, _, _, _ = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])
    canonical = parse_shot_prompt_json(generated["content"])
    canonical["source_storyboard_revision_id"] = "other-storyboard-revision"

    changed_source = client.put(
        f"/api/shot-prompt-revisions/{generated['revision_id']}",
        json={"content": serialize_shot_prompt_json(canonical).decode("utf-8")},
    )

    assert changed_source.status_code == 422
    assert changed_source.json()["error_code"] == "INVALID_REVISION_CONTENT"

    canonical = parse_shot_prompt_json(generated["content"])
    canonical["project_id"] = "other-project"

    changed_project = client.put(
        f"/api/shot-prompt-revisions/{generated['revision_id']}",
        json={"content": serialize_shot_prompt_json(canonical).decode("utf-8")},
    )

    assert changed_project.status_code == 422
    assert changed_project.json()["error_code"] == "INVALID_REVISION_CONTENT"


def test_mark_ready_rejects_invalid_duration_or_unusable_assets_then_preserves_canonical_content(client):
    _, chapter, _, _, assets = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])
    revision_id = generated["revision_id"]

    broken = parse_shot_prompt_json(generated["content"])
    broken["shots"][0]["duration_seconds"] = 16
    with _open_runtime_store(client) as runtime_store:
        revision = runtime_store.get_revision(revision_id)
        object_id = runtime_store.write_text_object(json.dumps(broken, ensure_ascii=False, sort_keys=True))
        runtime_store.conn.execute(
            "UPDATE revisions SET content_object_id = ? WHERE revision_id = ?",
            (object_id, revision.revision_id),
        )
        runtime_store.conn.commit()
    invalid_duration = client.post(f"/api/shot-prompt-revisions/{revision_id}/shots/SHOT_001/mark-ready")
    assert invalid_duration.status_code == 422
    assert invalid_duration.json()["error_code"] == "CANONICAL_VALIDATION_FAILED"

    canonical = parse_shot_prompt_json(generated["content"])
    with _open_runtime_store(client) as runtime_store:
        revision = runtime_store.get_revision(revision_id)
        object_id = runtime_store.write_text_object(serialize_shot_prompt_json(canonical).decode("utf-8"))
        runtime_store.conn.execute(
            "UPDATE revisions SET content_object_id = ?, content_hash = ? WHERE revision_id = ?",
            (object_id, shot_prompt_content_hash(canonical), revision.revision_id),
        )
        runtime_store.conn.commit()
    _with_product_store(client, lambda store: store.update_asset_status(assets["asset_id"], "draft"))
    unusable = client.post(f"/api/shot-prompt-revisions/{revision_id}/shots/SHOT_001/mark-ready")
    assert unusable.status_code == 409
    assert unusable.json()["error_code"] == "ASSET_NOT_USABLE"

    _with_product_store(client, lambda store: store.update_asset_status(assets["asset_id"], "usable"))
    with _open_runtime_store(client) as runtime_store:
        before = runtime_store.get_revision(revision_id)
        before_content = runtime_store.read_text(before.content_object_id)
        before_hash = before.content_hash
    ready = client.post(f"/api/shot-prompt-revisions/{revision_id}/shots/SHOT_001/mark-ready")

    assert ready.status_code == 200, ready.text
    assert ready.json()["readiness"]["SHOT_001"]["status"] == "ready"
    with _open_runtime_store(client) as runtime_store:
        after = runtime_store.get_revision(revision_id)
        assert runtime_store.read_text(after.content_object_id) == before_content
        assert after.content_hash == before_hash


def test_mark_ready_rejects_required_validator_failures(client):
    _, chapter, _, _, _ = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])
    canonical = parse_shot_prompt_json(generated["content"])
    canonical["shots"][0]["agnes_video_params"]["duration_seconds"] = canonical["shots"][0]["duration_seconds"] + 1
    edited = client.put(
        f"/api/shot-prompt-revisions/{generated['revision_id']}",
        json={"content": serialize_shot_prompt_json(canonical).decode("utf-8")},
    )
    assert edited.status_code == 200, edited.text
    assert {item["validator_id"]: item["status"] for item in edited.json()["validation_results"]}[
        "shot_prompt_set_structure"
    ] == "FAIL"

    response = client.post(f"/api/shot-prompt-revisions/{edited.json()['revision_id']}/shots/SHOT_001/mark-ready")

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_REQUIRED_FAILED"


def test_mark_ready_rejects_missing_required_asset_ref(client):
    _, chapter, _, _, assets = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])
    canonical = parse_shot_prompt_json(generated["content"])
    canonical["shots"][0]["asset_refs"] = [assets["asset_id"]]
    edited = client.put(
        f"/api/shot-prompt-revisions/{generated['revision_id']}",
        json={"content": serialize_shot_prompt_json(canonical).decode("utf-8")},
    )
    assert edited.status_code == 200, edited.text

    response = client.post(f"/api/shot-prompt-revisions/{edited.json()['revision_id']}/shots/SHOT_001/mark-ready")

    assert response.status_code == 409
    assert response.json()["error_code"] == "ASSET_MISSING"


def test_mark_ready_rejects_asset_that_is_no_longer_current_for_requirement(client):
    project, chapter, _, _, assets = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])

    def replace_shot_keyframe(store):
        replacement = store.create_generated_asset(
            project_id=project["project_id"],
            chapter_id=generated["chapter_id"],
            asset_type="shot_keyframe",
            name="replacement keyframe",
            data=b"replacement-keyframe",
            media_type="image/png",
            source_job_id="job-shot-002",
            metadata={},
        )
        store.update_asset_status(replacement.asset_id, "usable")
        store.create_asset_binding(
            asset_id=replacement.asset_id,
            target_type="shot",
            target_id="SHOT_001",
            role="keyframe",
            is_current=True,
        )
        store.create_asset_binding(
            asset_id=assets["shot_asset_id"],
            target_type="character",
            target_id="other-current-target",
            role="primary_reference",
            is_current=True,
        )

    _with_product_store(client, replace_shot_keyframe)

    response = client.post(f"/api/shot-prompt-revisions/{generated['revision_id']}/shots/SHOT_001/mark-ready")

    assert response.status_code == 409
    assert response.json()["error_code"] == "ASSET_NOT_CURRENT"


def test_agnes_preview_returns_single_shot_request_sections(client):
    _, chapter, _, _, assets = _setup_chapter(client)
    generated = _generate(client, chapter["chapter_id"])
    shot = generated["shots"][0]

    response = client.get(
        f"/api/shot-prompt-revisions/{generated['revision_id']}/shots/{shot['shot_id']}/agnes-preview"
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "shot_id": "SHOT_001",
        "positive_prompt": shot["positive_prompt"],
        "negative_prompt": shot["negative_prompt"],
        "asset_refs": [assets["asset_id"], assets["shot_asset_id"]],
        "continuity_notes": shot["continuity_notes"],
        "agnes_video_params": shot["agnes_video_params"],
    }


def test_regenerate_one_shot_creates_new_valid_revision_and_changes_only_target_prompt(client):
    _, chapter, storyboard_revision, _, _ = _setup_chapter(client, two_shots=True)
    generated = _generate(client, chapter["chapter_id"])
    original = parse_shot_prompt_json(generated["content"])

    response = client.post(
        f"/api/shot-prompt-revisions/{generated['revision_id']}/shots/SHOT_002/regenerate"
    )

    assert response.status_code == 200, response.text
    regenerated = response.json()
    assert regenerated["revision_id"] != generated["revision_id"]
    assert regenerated["number"] == generated["number"] + 1
    assert regenerated["source_storyboard_revision_id"] == storyboard_revision.revision_id
    assert regenerated["validation_results"][0]["status"] == "PASS"
    updated = parse_shot_prompt_json(regenerated["content"])
    assert updated["source_storyboard_revision_id"] == original["source_storyboard_revision_id"]
    assert updated["shots"][0] == original["shots"][0]
    assert updated["shots"][1]["positive_prompt"] != original["shots"][1]["positive_prompt"]
    assert "regenerated for SHOT_002" in updated["shots"][1]["positive_prompt"]
