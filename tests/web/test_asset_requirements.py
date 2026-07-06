import hashlib
import json

from ai_drama_runtime.storyboard_canonical import CONTENT_PROFILE, canonical_storyboard_hash
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _create_project_and_chapter(client):
    project = client.post("/api/projects", json={"name": "生死"}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    return project, chapter


def _create_profile(client, project_id, chapter_id, profile_type, name):
    payload = {
        "name": name,
        "continuity_notes": f"{name} continuity",
    }
    if profile_type == "character":
        payload.update(
            {
                "identity_notes": f"{name} identity",
                "appearance_notes": "",
                "costume_notes": f"{name} costume",
            }
        )
    elif profile_type == "scene":
        payload.update(
            {
                "scene_layout_notes": f"{name} layout",
                "lighting_notes": f"{name} light",
            }
        )
    elif profile_type == "prop":
        payload["prop_handling_notes"] = f"{name} handling"
    else:
        raise AssertionError(f"unexpected profile type: {profile_type}")
    response = client.post(
        f"/api/projects/{project_id}/profiles",
        json={
            "chapter_id": chapter_id,
            "profile_type": profile_type,
            "payload": payload,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _upload_asset(client, chapter_id, asset_type, name):
    response = client.post(
        f"/api/chapters/{chapter_id}/assets",
        data={"asset_type": asset_type, "name": name},
        files={"file": ("reference.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _make_asset_current(client, asset_id, target_type, target_id, role):
    usable = client.post(f"/api/assets/{asset_id}/mark-usable")
    assert usable.status_code == 200, usable.text
    binding = client.post(
        f"/api/assets/{asset_id}/bindings",
        json={
            "target_type": target_type,
            "target_id": target_id,
            "role": role,
            "is_current": True,
        },
    )
    assert binding.status_code == 200, binding.text


def _canonical_storyboard(project_id, chapter_id, first_character_id, second_character_id):
    return {
        "schema_version": "storyboard-canonical-v1",
        "project_id": project_id,
        "chapter_id": chapter_id,
        "source": {
            "script_artifact_id": f"{chapter_id}:script",
            "script_revision_id": "script-revision-1",
            "script_content_hash": "a" * 64,
        },
        "scenes": [
            {
                "scene_id": "SCENE_MAIN_HALL",
                "scene_order": 1,
                "source_scene_reference": "S1",
                "location": "SCENE_MAIN_HALL",
                "time": "day",
                "interior_exterior": "interior",
                "characters": [first_character_id, second_character_id],
                "summary": "PROP_JADE is revealed in the hall.",
            }
        ],
        "shots": [
            {
                "scene_id": "SCENE_MAIN_HALL",
                "shot_id": "SHOT_001",
                "shot_order": 1,
                "source_scene_reference": "S1",
                "duration_seconds": 6,
                "shot_size": "medium",
                "camera_angle": "eye-level",
                "camera_movement": None,
                "visual_composition": {
                    "framing": "two-shot with PROP_JADE foreground",
                    "subject_focus": "characters and PROP_JADE",
                    "background_relation": "SCENE_MAIN_HALL screen behind them",
                    "screen_direction": "left-to-right",
                },
                "character_positions": [
                    {
                        "character_id": first_character_id,
                        "screen_zone": "left",
                        "depth": "midground",
                        "pose": "standing",
                        "facing": "right",
                    },
                    {
                        "character_id": second_character_id,
                        "screen_zone": "right",
                        "depth": "midground",
                        "pose": "standing",
                        "facing": "left",
                    },
                ],
                "character_actions": [
                    {"character_id": first_character_id, "action_order": 1, "action": "holds PROP_JADE"},
                    {"character_id": second_character_id, "action_order": 2, "action": "looks at PROP_JADE"},
                ],
                "emotion_performance": [
                    {
                        "character_id": first_character_id,
                        "emotion": "tense",
                        "intensity": "medium",
                        "performance_note": None,
                    },
                    {
                        "character_id": second_character_id,
                        "emotion": "watchful",
                        "intensity": "low",
                        "performance_note": None,
                    },
                ],
                "dialogue": [
                    {"speaker_character_id": first_character_id, "text": "PROP_JADE belongs here.", "lip_sync_required": True}
                ],
                "sound_notes": ["quiet room tone"],
                "continuity_in": {"must_preserve": ["PROP_JADE visible"], "must_change": [], "source_unit_or_shot_id": None},
                "continuity_out": {"must_preserve": ["PROP_JADE visible"], "must_change": [], "source_unit_or_shot_id": None},
            }
        ],
    }


def _approve_storyboard(client, canonical):
    with _open_runtime_store(client) as runtime_store:
        artifact_id = f"{canonical['chapter_id']}:script:storyboard"
        runtime_store.ensure_artifact(artifact_id, "storyboard", canonical["project_id"], canonical["chapter_id"])
        content = json.dumps(canonical, ensure_ascii=False)
        content_object_id = runtime_store.write_text_object(content)
        run = runtime_store.create_run(
            artifact_id=artifact_id,
            project_id=canonical["project_id"],
            chapter_id=canonical["chapter_id"],
            skill_id="test-storyboard",
            skill_version="0.0.0",
            skill_hash="test",
            runtime="test",
            provider="test",
            model="test",
            status="completed",
            request_object_id=content_object_id,
            input_hash=canonical_storyboard_hash(canonical),
        )
        revision = runtime_store.insert_revision(
            artifact_id=artifact_id,
            artifact_type="storyboard",
            project_id=canonical["project_id"],
            chapter_id=canonical["chapter_id"],
            run_id=run.run_id,
            skill_id="test-storyboard",
            skill_version="0.0.0",
            skill_package_hash="test",
            runtime_provider="test",
            runtime_model="test",
            content_object_id=content_object_id,
            content_hash=canonical_storyboard_hash(canonical),
            raw_response_object_id=content_object_id,
            parser_version="storyboard-canonical-json-v1",
            content_profile=CONTENT_PROFILE,
        )
        runtime_store.approve_in_transaction(revision, "tester", "approved canonical storyboard")
        return revision


def _open_runtime_store(client):
    data_root = client.app.state.settings.data_root
    return RuntimeStore(data_root / "runtime.db", data_root / "objects")


def _with_product_store(client, callback):
    with _open_runtime_store(client) as runtime_store:
        return callback(ProductStore(runtime_store))


def _setup_requirements_chapter(client):
    project, chapter = _create_project_and_chapter(client)
    first_character = _create_profile(client, project["project_id"], chapter["chapter_id"], "character", "沈清荷")
    second_character = _create_profile(client, project["project_id"], chapter["chapter_id"], "character", "沈清莲")
    scene = _create_profile(client, project["project_id"], chapter["chapter_id"], "scene", "SCENE_MAIN_HALL")
    prop = _create_profile(client, project["project_id"], chapter["chapter_id"], "prop", "PROP_JADE")
    canonical = _canonical_storyboard(
        project["project_id"],
        chapter["chapter_id"],
        first_character["profile_id"],
        second_character["profile_id"],
    )
    revision = _approve_storyboard(client, canonical)
    return {
        "project": project,
        "chapter": chapter,
        "first_character": first_character,
        "second_character": second_character,
        "scene": scene,
        "prop": prop,
        "revision": revision,
        "canonical": canonical,
    }


def test_analyze_canonical_storyboard_reports_missing_assets_and_ready_character(client):
    setup = _setup_requirements_chapter(client)
    chapter_id = setup["chapter"]["chapter_id"]
    character_asset = _upload_asset(client, chapter_id, "character_reference", "沈清荷 reference")
    _make_asset_current(
        client,
        character_asset["asset_id"],
        "character",
        setup["first_character"]["profile_id"],
        "primary_reference",
    )

    response = client.post(f"/api/chapters/{chapter_id}/asset-requirements/analyze")

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["chapter_id"] == chapter_id
    assert result["storyboard_revision_id"] == setup["revision"].revision_id
    assert result["storyboard_content_hash"] == setup["revision"].content_hash
    with _open_runtime_store(client) as runtime_store:
        requirement_payload = runtime_store.read_bytes_object(result["content_object_id"])
    assert json.loads(requirement_payload.decode("utf-8"))["storyboard_content_hash"] == setup["revision"].content_hash
    assert hashlib.sha256(requirement_payload).hexdigest() == result["content_hash"]
    assert result["content_hash"] != setup["revision"].content_hash
    assert result["status"] == "missing_assets"
    assert result["created_at"]
    assert result["content_object_id"]
    assert result["shot_rows"] == [
        {
            "shot_id": "SHOT_001",
            "status": "missing_assets",
            "ready": [
                {
                    "need_type": "character_asset",
                    "target_type": "character",
                    "target_id": setup["first_character"]["profile_id"],
                    "role": "primary_reference",
                    "asset_type": "character_reference",
                    "asset_id": character_asset["asset_id"],
                    "status": "ready",
                }
            ],
            "missing_assets": [
                {
                    "need_type": "character_asset",
                    "target_type": "character",
                    "target_id": setup["second_character"]["profile_id"],
                    "role": "primary_reference",
                    "asset_type": "character_reference",
                    "status": "missing_assets",
                },
                {
                    "need_type": "scene_asset",
                    "target_type": "scene",
                    "target_id": setup["scene"]["profile_id"],
                    "role": "layout_reference",
                    "asset_type": "scene_reference",
                    "status": "missing_assets",
                },
                {
                    "need_type": "prop_asset",
                    "target_type": "prop",
                    "target_id": setup["prop"]["profile_id"],
                    "role": "handling_reference",
                    "asset_type": "prop_reference",
                    "status": "missing_assets",
                },
                {
                    "need_type": "shot_keyframe",
                    "target_type": "shot",
                    "target_id": "SHOT_001",
                    "role": "keyframe",
                    "asset_type": "shot_keyframe",
                    "status": "missing_assets",
                },
            ],
            "asset_generation_in_progress": [],
            "asset_review_required": [],
        }
    ]
    assert result["missing_assets"] == result["shot_rows"][0]["missing_assets"]
    assert result["asset_generation_in_progress"] == []
    assert result["asset_review_required"] == []

    latest = client.get(f"/api/chapters/{chapter_id}/asset-requirements/latest")
    assert latest.status_code == 200, latest.text
    assert latest.json() == result


def test_non_usable_bound_assets_surface_generation_or_review_states(client):
    setup = _setup_requirements_chapter(client)
    chapter_id = setup["chapter"]["chapter_id"]
    generating_asset = _upload_asset(client, chapter_id, "character_reference", "沈清莲 generating")
    _with_product_store(
        client,
        lambda store: (
            store.update_asset_status(generating_asset["asset_id"], "generating"),
            store.create_asset_binding(
                asset_id=generating_asset["asset_id"],
                target_type="character",
                target_id=setup["second_character"]["profile_id"],
                role="primary_reference",
            ),
        ),
    )
    rejected_asset = _upload_asset(client, chapter_id, "scene_reference", "Scene rejected")
    _with_product_store(
        client,
        lambda store: (
            store.update_asset_status(rejected_asset["asset_id"], "rejected", metadata={"reason": "layout mismatch"}),
            store.create_asset_binding(
                asset_id=rejected_asset["asset_id"],
                target_type="scene",
                target_id=setup["scene"]["profile_id"],
                role="layout_reference",
            ),
        ),
    )

    response = client.post(f"/api/chapters/{chapter_id}/asset-requirements/analyze")

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "asset_generation_in_progress"
    assert result["asset_generation_in_progress"] == [
        {
            "need_type": "character_asset",
            "target_type": "character",
            "target_id": setup["second_character"]["profile_id"],
            "role": "primary_reference",
            "asset_type": "character_reference",
            "asset_id": generating_asset["asset_id"],
            "status": "asset_generation_in_progress",
        }
    ]
    assert result["asset_review_required"] == [
        {
            "need_type": "scene_asset",
            "target_type": "scene",
            "target_id": setup["scene"]["profile_id"],
            "role": "layout_reference",
            "asset_type": "scene_reference",
            "asset_id": rejected_asset["asset_id"],
            "status": "asset_review_required",
        }
    ]


def test_analyze_returns_ready_after_all_current_usable_assets_exist(client):
    setup = _setup_requirements_chapter(client)
    chapter_id = setup["chapter"]["chapter_id"]
    for asset_type, target_type, target_id, role, name in [
        ("character_reference", "character", setup["first_character"]["profile_id"], "primary_reference", "沈清荷"),
        ("character_reference", "character", setup["second_character"]["profile_id"], "primary_reference", "沈清莲"),
        ("scene_reference", "scene", setup["scene"]["profile_id"], "layout_reference", "正厅"),
        ("prop_reference", "prop", setup["prop"]["profile_id"], "handling_reference", "玉佩"),
    ]:
        asset = _upload_asset(client, chapter_id, asset_type, name)
        _make_asset_current(client, asset["asset_id"], target_type, target_id, role)
    shot_asset = _upload_asset(client, chapter_id, "shot_keyframe", "SHOT_001 keyframe")
    client.post(f"/api/assets/{shot_asset['asset_id']}/mark-usable")
    shot_binding = client.post(
        f"/api/assets/{shot_asset['asset_id']}/bindings",
        json={
            "target_type": "shot",
            "target_id": "SHOT_001",
            "role": "keyframe",
            "is_current": True,
        },
    )
    assert shot_binding.status_code == 200, shot_binding.text

    response = client.post(f"/api/chapters/{chapter_id}/asset-requirements/analyze")

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "ready"
    assert result["shot_rows"][0]["status"] == "ready"
    assert len(result["shot_rows"][0]["ready"]) == 5
    assert result["missing_assets"] == []
    assert result["asset_generation_in_progress"] == []
    assert result["asset_review_required"] == []


def test_missing_chapter_and_missing_approved_storyboard_are_reported(client):
    missing = client.post("/api/chapters/missing/asset-requirements/analyze")
    assert missing.status_code == 404

    _, chapter = _create_project_and_chapter(client)
    response = client.post(f"/api/chapters/{chapter['chapter_id']}/asset-requirements/analyze")
    assert response.status_code == 409
    assert response.json() == {
        "error_code": "STORYBOARD_NOT_APPROVED",
        "error_message": "current approved canonical storyboard is required",
    }

    latest = client.get(f"/api/chapters/{chapter['chapter_id']}/asset-requirements/latest")
    assert latest.status_code == 409
    assert latest.json() == {
        "error_code": "ASSET_REQUIREMENTS_NOT_ANALYZED",
        "error_message": "asset requirements have not been analyzed",
    }


def test_analyze_rejects_storyboard_with_mismatched_chapter_or_hash(client):
    setup = _setup_requirements_chapter(client)
    chapter_id = setup["chapter"]["chapter_id"]
    with _open_runtime_store(client) as runtime_store:
        revision = runtime_store.current_approved(f"{chapter_id}:script:storyboard")
        broken = dict(setup["canonical"])
        broken["chapter_id"] = "other-chapter"
        broken_object_id = runtime_store.write_text_object(json.dumps(broken, ensure_ascii=False))
        runtime_store.conn.execute(
            "UPDATE revisions SET content_object_id = ? WHERE revision_id = ?",
            (broken_object_id, revision.revision_id),
        )
        runtime_store.conn.commit()

    response = client.post(f"/api/chapters/{chapter_id}/asset-requirements/analyze")

    assert response.status_code == 409
    assert response.json() == {
        "error_code": "STORYBOARD_NOT_APPROVED",
        "error_message": "current approved canonical storyboard is required",
    }


def test_analyze_does_not_use_global_shot_asset_from_another_project(client):
    setup = _setup_requirements_chapter(client)
    other_project = client.post("/api/projects", json={"name": "旁支"}).json()

    def create_other_global_shot_asset(store):
        asset = store.create_generated_asset(
            project_id=other_project["project_id"],
            chapter_id="",
            asset_type="shot_keyframe",
            name="other project keyframe",
            data=PNG_BYTES,
            media_type="image/png",
            source_job_id="other-job",
            metadata={},
        )
        store.update_asset_status(asset.asset_id, "usable")
        store.create_asset_binding(
            asset_id=asset.asset_id,
            target_type="shot",
            target_id="SHOT_001",
            role="keyframe",
            is_current=True,
        )

    _with_product_store(client, create_other_global_shot_asset)

    response = client.post(f"/api/chapters/{setup['chapter']['chapter_id']}/asset-requirements/analyze")

    assert response.status_code == 200, response.text
    result = response.json()
    shot_keyframes = [
        item for item in result["shot_rows"][0]["missing_assets"] if item["need_type"] == "shot_keyframe"
    ]
    assert shot_keyframes == [
        {
            "need_type": "shot_keyframe",
            "target_type": "shot",
            "target_id": "SHOT_001",
            "role": "keyframe",
            "asset_type": "shot_keyframe",
            "status": "missing_assets",
        }
    ]


def test_current_shot_keyframe_bindings_are_project_scoped(client):
    first_setup = _setup_requirements_chapter(client)
    second_setup = _setup_requirements_chapter(client)

    first_shot_asset = _upload_asset(client, first_setup["chapter"]["chapter_id"], "shot_keyframe", "first keyframe")
    second_shot_asset = _upload_asset(client, second_setup["chapter"]["chapter_id"], "shot_keyframe", "second keyframe")
    for asset in [first_shot_asset, second_shot_asset]:
        usable = client.post(f"/api/assets/{asset['asset_id']}/mark-usable")
        assert usable.status_code == 200, usable.text
        binding = client.post(
            f"/api/assets/{asset['asset_id']}/bindings",
            json={
                "target_type": "shot",
                "target_id": "SHOT_001",
                "role": "keyframe",
                "is_current": True,
            },
        )
        assert binding.status_code == 200, binding.text

    response = client.post(f"/api/chapters/{first_setup['chapter']['chapter_id']}/asset-requirements/analyze")

    assert response.status_code == 200, response.text
    ready_keyframes = [
        item for item in response.json()["shot_rows"][0]["ready"] if item["need_type"] == "shot_keyframe"
    ]
    assert ready_keyframes == [
        {
            "need_type": "shot_keyframe",
            "target_type": "shot",
            "target_id": "SHOT_001",
            "role": "keyframe",
            "asset_type": "shot_keyframe",
            "asset_id": first_shot_asset["asset_id"],
            "status": "ready",
        }
    ]


def test_public_shot_binding_rejects_tampered_approved_storyboard(client):
    setup = _setup_requirements_chapter(client)
    chapter_id = setup["chapter"]["chapter_id"]
    shot_asset = _upload_asset(client, chapter_id, "shot_keyframe", "tampered keyframe")
    client.post(f"/api/assets/{shot_asset['asset_id']}/mark-usable")
    with _open_runtime_store(client) as runtime_store:
        revision = runtime_store.current_approved(f"{chapter_id}:script:storyboard")
        broken = dict(setup["canonical"])
        broken["shots"] = [dict(setup["canonical"]["shots"][0], shot_id="SHOT_TAMPER")]
        broken_object_id = runtime_store.write_text_object(json.dumps(broken, ensure_ascii=False))
        runtime_store.conn.execute(
            "UPDATE revisions SET content_object_id = ? WHERE revision_id = ?",
            (broken_object_id, revision.revision_id),
        )
        runtime_store.conn.commit()

    response = client.post(
        f"/api/assets/{shot_asset['asset_id']}/bindings",
        json={
            "target_type": "shot",
            "target_id": "SHOT_TAMPER",
            "role": "keyframe",
            "is_current": True,
        },
    )

    assert response.status_code == 404


def test_chapter_profile_overrides_global_profile_name_match(client):
    project, chapter = _create_project_and_chapter(client)
    global_scene = _create_profile(client, project["project_id"], "", "scene", "SCENE_MAIN_HALL")
    local_scene = _create_profile(client, project["project_id"], chapter["chapter_id"], "scene", "SCENE_MAIN_HALL")
    first_character = _create_profile(client, project["project_id"], chapter["chapter_id"], "character", "沈清荷")
    second_character = _create_profile(client, project["project_id"], chapter["chapter_id"], "character", "沈清莲")
    _create_profile(client, project["project_id"], chapter["chapter_id"], "prop", "PROP_JADE")
    canonical = _canonical_storyboard(
        project["project_id"],
        chapter["chapter_id"],
        first_character["profile_id"],
        second_character["profile_id"],
    )
    _approve_storyboard(client, canonical)
    global_scene_asset = _upload_asset(client, chapter["chapter_id"], "scene_reference", "global scene")
    _make_asset_current(client, global_scene_asset["asset_id"], "scene", global_scene["profile_id"], "layout_reference")

    response = client.post(f"/api/chapters/{chapter['chapter_id']}/asset-requirements/analyze")

    assert response.status_code == 200, response.text
    scene_missing = [
        item for item in response.json()["missing_assets"] if item["need_type"] == "scene_asset"
    ]
    assert scene_missing == [
        {
            "need_type": "scene_asset",
            "target_type": "scene",
            "target_id": local_scene["profile_id"],
            "role": "layout_reference",
            "asset_type": "scene_reference",
            "status": "missing_assets",
        }
    ]
