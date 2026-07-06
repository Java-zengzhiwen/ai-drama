import json
from pathlib import Path

import pytest

from ai_drama_runtime.registry import SkillRegistry
from ai_drama_runtime.services import RuntimeService, WorkflowGateError
from ai_drama_runtime.shot_prompt_canonical import (
    CANONICAL_PARSER_VERSION as SHOT_PROMPT_PARSER_VERSION,
    CONTENT_PROFILE as SHOT_PROMPT_PROFILE,
    parse_shot_prompt_json,
    shot_prompt_content_hash,
)
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.storyboard_canonical import (
    CANONICAL_PARSER_VERSION as STORYBOARD_PARSER_VERSION,
    CONTENT_PROFILE as STORYBOARD_PROFILE,
    canonical_storyboard_hash,
    serialize_canonical_json,
)
from ai_drama_runtime.validators import run_declared_validators
from ai_drama_web.store import ProductStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SHOT_PROMPT_SKILL_REF = "ai-drama-shot-prompt-skill@v0.1.0"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"), repo_root=REPO_ROOT)


def _shot_prompt_skill():
    return SkillRegistry.scan([REPO_ROOT / "skills"]).get_ref(SHOT_PROMPT_SKILL_REF)


def _project_chapter(store):
    product = ProductStore(store)
    project = product.create_project(name="生死账", series_canon="family revenge", production_brief="live action")
    chapter = product.create_chapter(project.project_id, "第一章", 1)
    return product, project, chapter


def _storyboard_canonical(project_id, chapter_id, *, shot_id="SHOT_001", two_shots=False):
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
                "shot_id": shot_id,
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
                "continuity_in": {"must_preserve": ["jade token visible"], "must_change": [], "source_unit_or_shot_id": None},
                "continuity_out": {"must_preserve": ["jade token hidden"], "must_change": [], "source_unit_or_shot_id": None},
            }
        ],
    }
    if two_shots:
        second = json.loads(json.dumps(canonical["shots"][0]))
        second["shot_id"] = "SHOT_002"
        second["shot_order"] = 2
        second["character_actions"][0]["action"] = "keeps PROP_JADE hidden"
        second["continuity_in"]["source_unit_or_shot_id"] = "SHOT_001"
        second["continuity_out"]["source_unit_or_shot_id"] = "SHOT_001"
        canonical["shots"].append(second)
    return canonical


def _insert_storyboard_revision(service, project_id, chapter_id, *, approved=True, shot_id="SHOT_001", two_shots=False):
    canonical = _storyboard_canonical(project_id, chapter_id, shot_id=shot_id, two_shots=two_shots)
    text = serialize_canonical_json(canonical).decode("utf-8")
    content_object_id = service.store.write_text_object(text)
    artifact_id = f"{chapter_id}:script:storyboard"
    service.store.ensure_artifact(artifact_id, "storyboard", project_id, chapter_id)
    run = service.store.create_run(
        artifact_id=artifact_id,
        project_id=project_id,
        chapter_id=chapter_id,
        skill_id="test-storyboard",
        skill_version="v0.0.0",
        skill_hash="test",
        runtime="test",
        provider="test",
        model="test",
        status="SUCCEEDED",
        request_object_id=content_object_id,
        response_object_id=content_object_id,
        input_hash=canonical_storyboard_hash(canonical),
        request_hash=canonical_storyboard_hash(canonical),
    )
    revision = service.store.insert_revision(
        artifact_id=artifact_id,
        artifact_type="storyboard",
        project_id=project_id,
        chapter_id=chapter_id,
        run_id=run.run_id,
        skill_id="test-storyboard",
        skill_version="v0.0.0",
        skill_package_hash="test",
        runtime_provider="test",
        runtime_model="test",
        content_object_id=content_object_id,
        content_hash=canonical_storyboard_hash(canonical),
        raw_response_object_id=content_object_id,
        parser_version=STORYBOARD_PARSER_VERSION,
        content_profile=STORYBOARD_PROFILE,
    )
    if approved:
        service.store.approve_in_transaction(revision, "tester", "approved canonical storyboard")
        revision = service.store.get_revision(revision.revision_id)
    return revision, canonical


def _ready_asset_requirements(product, store, chapter_id, revision, canonical):
    character = product.create_production_profile(
        project_id=revision.project_id,
        chapter_id=chapter_id,
        profile_type="character",
        name="CHAR_SHEN",
        payload={"name": "CHAR_SHEN", "identity_notes": "same face", "costume_notes": "blue robe"},
    )
    asset = product.create_generated_asset(
        project_id=revision.project_id,
        chapter_id=chapter_id,
        asset_type="character_reference",
        name="CHAR_SHEN reference",
        data=b"fake-image-bytes",
        media_type="image/png",
        source_job_id="job-001",
        metadata={},
    )
    product.update_asset_status(asset.asset_id, "usable")
    product.create_asset_binding(
        asset_id=asset.asset_id,
        target_type="character",
        target_id=character.profile_id,
        role="primary_reference",
        is_current=True,
    )
    payload = {
        "status": "ready",
        "storyboard_content_hash": revision.content_hash,
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
                    }
                ],
                "missing_assets": [],
                "asset_generation_in_progress": [],
                "asset_review_required": [],
            }
            for shot in canonical["shots"]
        ],
        "missing_assets": [],
        "asset_generation_in_progress": [],
        "asset_review_required": [],
    }
    return product.create_asset_requirement_set(
        chapter_id=chapter_id,
        storyboard_revision_id=revision.revision_id,
        payload=payload,
    )


def _setup_ready_source(service):
    product, project, chapter = _project_chapter(service.store)
    revision, canonical = _insert_storyboard_revision(service, project.project_id, chapter.chapter_id)
    _ready_asset_requirements(product, service.store, chapter.chapter_id, revision, canonical)
    return product, project, chapter, revision, canonical


def test_missing_storyboard_revision_records_gate(tmp_path):
    with _service(tmp_path) as service:
        with pytest.raises(WorkflowGateError) as exc:
            service.run_shot_prompt(_shot_prompt_skill(), "missing-revision", "mock", "mock-model")

        assert exc.value.code == "SOURCE_REVISION_NOT_FOUND"
        gates = service.store.workflow_gate_records()
        assert [(gate.error_code, gate.source_revision_id) for gate in gates] == [
            ("SOURCE_REVISION_NOT_FOUND", "missing-revision")
        ]


def test_unapproved_storyboard_revision_is_blocked(tmp_path):
    with _service(tmp_path) as service:
        product, project, chapter = _project_chapter(service.store)
        revision, canonical = _insert_storyboard_revision(
            service,
            project.project_id,
            chapter.chapter_id,
            approved=False,
        )
        _ready_asset_requirements(product, service.store, chapter.chapter_id, revision, canonical)

        with pytest.raises(WorkflowGateError) as exc:
            service.run_shot_prompt(_shot_prompt_skill(), revision.revision_id, "mock", "mock-model")

        assert exc.value.code == "SOURCE_REVISION_NOT_APPROVED"


def test_superseded_storyboard_revision_is_blocked_as_not_current(tmp_path):
    with _service(tmp_path) as service:
        product, project, chapter = _project_chapter(service.store)
        first, canonical = _insert_storyboard_revision(service, project.project_id, chapter.chapter_id)
        _ready_asset_requirements(product, service.store, chapter.chapter_id, first, canonical)
        _insert_storyboard_revision(service, project.project_id, chapter.chapter_id, shot_id="SHOT_002")

        with pytest.raises(WorkflowGateError) as exc:
            service.run_shot_prompt(_shot_prompt_skill(), first.revision_id, "mock", "mock-model")

        assert exc.value.code == "SOURCE_REVISION_NOT_CURRENT_APPROVED"


def test_asset_requirements_missing_or_not_ready_blocks_generation(tmp_path):
    with _service(tmp_path) as service:
        _, project, chapter = _project_chapter(service.store)
        revision, _ = _insert_storyboard_revision(service, project.project_id, chapter.chapter_id)

        with pytest.raises(WorkflowGateError) as exc:
            service.run_shot_prompt(_shot_prompt_skill(), revision.revision_id, "mock", "mock-model")

        assert exc.value.code == "ASSET_REQUIREMENTS_NOT_READY"
        product = ProductStore(service.store)
        product.create_asset_requirement_set(
            chapter_id=chapter.chapter_id,
            storyboard_revision_id=revision.revision_id,
            payload={
                "status": "missing_assets",
                "storyboard_content_hash": revision.content_hash,
                "shot_rows": [],
                "missing_assets": [{"status": "missing_assets"}],
                "asset_generation_in_progress": [],
                "asset_review_required": [],
            },
        )

        with pytest.raises(WorkflowGateError) as not_ready:
            service.run_shot_prompt(_shot_prompt_skill(), revision.revision_id, "mock", "mock-model")

        assert not_ready.value.code == "ASSET_REQUIREMENTS_NOT_READY"


def test_asset_requirements_ready_without_storyboard_hash_blocks_generation(tmp_path):
    with _service(tmp_path) as service:
        product, project, chapter = _project_chapter(service.store)
        revision, _ = _insert_storyboard_revision(service, project.project_id, chapter.chapter_id)
        product.create_asset_requirement_set(
            chapter_id=chapter.chapter_id,
            storyboard_revision_id=revision.revision_id,
            payload={
                "status": "ready",
                "shot_rows": [],
                "missing_assets": [],
                "asset_generation_in_progress": [],
                "asset_review_required": [],
            },
        )

        with pytest.raises(WorkflowGateError) as exc:
            service.run_shot_prompt(_shot_prompt_skill(), revision.revision_id, "mock", "mock-model")

        assert exc.value.code == "ASSET_REQUIREMENTS_NOT_READY"


def test_successful_mock_generation_persists_revision_dependency_snapshots_and_validator(tmp_path):
    with _service(tmp_path) as service:
        _, _, _, source, _ = _setup_ready_source(service)

        result = service.run_shot_prompt(_shot_prompt_skill(), source.revision_id, "mock", "mock-model")

        assert result.run.status == "SUCCEEDED"
        assert result.revision.artifact_type == "shot_prompt_set"
        assert result.revision.content_profile == SHOT_PROMPT_PROFILE
        assert result.revision.parser_version == SHOT_PROMPT_PARSER_VERSION
        canonical = parse_shot_prompt_json(service.store.read_text(result.revision.content_object_id))
        assert canonical["source_storyboard_revision_id"] == source.revision_id
        assert result.revision.content_hash == shot_prompt_content_hash(canonical)
        assert [item.status for item in result.validation_results] == ["PASS"]
        deps = service.store.revision_dependencies(result.revision.revision_id)
        assert len(deps) == 1
        assert deps[0].relation_type == "derived_from"
        assert deps[0].parent_revision_id == source.revision_id
        assert deps[0].parent_content_hash == source.content_hash
        assert deps[0].parent_approval_record_id == service.store.latest_approval(source.revision_id).record_id
        snapshots = {item.logical_type: item for item in service.store.input_snapshots(result.run.run_id)}
        assert {
            "source_storyboard_revision",
            "storyboard_canonical",
            "production_profiles",
            "asset_requirements",
            "asset_bindings",
        }.issubset(snapshots)
        request = json.loads(result.adapter_request_json)
        assert request["inputs"]["source_storyboard_revision_id"] == source.revision_id
        assert request["inputs"]["source_storyboard_content_hash"] == source.content_hash
        assert request["inputs"]["storyboard_canonical"]["schema_version"] == "storyboard-canonical-v1"


def test_mock_generation_handles_empty_optional_storyboard_action_arrays(tmp_path):
    with _service(tmp_path) as service:
        product, project, chapter = _project_chapter(service.store)
        revision, canonical = _insert_storyboard_revision(service, project.project_id, chapter.chapter_id)
        canonical["shots"][0]["character_actions"] = []
        canonical["shots"][0]["emotion_performance"] = []
        canonical_text = serialize_canonical_json(canonical).decode("utf-8")
        canonical_object_id = service.store.write_text_object(canonical_text)
        canonical_hash = canonical_storyboard_hash(canonical)
        service.store.conn.execute(
            """
            UPDATE revisions
            SET content_object_id = ?, content_hash = ?
            WHERE revision_id = ?
            """,
            (canonical_object_id, canonical_hash, revision.revision_id),
        )
        service.store.conn.commit()
        revision = service.store.get_revision(revision.revision_id)
        _ready_asset_requirements(product, service.store, chapter.chapter_id, revision, canonical)

        result = service.run_shot_prompt(_shot_prompt_skill(), revision.revision_id, "mock", "mock-model")

        canonical_prompt = parse_shot_prompt_json(service.store.read_text(result.revision.content_object_id))
        assert canonical_prompt["shots"][0]["action"] == "perform the storyboard action"
        assert canonical_prompt["shots"][0]["emotion"] == "focused"


def test_mock_generation_deduplicates_reused_asset_refs_across_shots(tmp_path):
    with _service(tmp_path) as service:
        product, project, chapter = _project_chapter(service.store)
        revision, canonical = _insert_storyboard_revision(
            service,
            project.project_id,
            chapter.chapter_id,
            two_shots=True,
        )
        _ready_asset_requirements(product, service.store, chapter.chapter_id, revision, canonical)

        result = service.run_shot_prompt(_shot_prompt_skill(), revision.revision_id, "mock", "mock-model")

        assert result.run.status == "SUCCEEDED"
        canonical_prompt = parse_shot_prompt_json(service.store.read_text(result.revision.content_object_id))
        for shot in canonical_prompt["shots"]:
            assert len(shot["asset_refs"]) == len(set(shot["asset_refs"]))


def test_declared_validator_applies_to_real_shot_prompt_set_revision(tmp_path):
    with _service(tmp_path) as service:
        _, _, _, source, _ = _setup_ready_source(service)
        skill = _shot_prompt_skill()
        result = service.run_shot_prompt(skill, source.revision_id, "mock", "mock-model")

        validation = run_declared_validators(service.store, skill, result.revision, REPO_ROOT, repo_root=REPO_ROOT)[0]

        assert validation.status == "PASS"


def test_business_key_reuse_creates_new_revision_on_existing_shot_prompt_artifact(tmp_path):
    with _service(tmp_path) as service:
        _, _, _, source, _ = _setup_ready_source(service)
        skill = _shot_prompt_skill()

        first = service.run_shot_prompt(skill, source.revision_id, "mock", "mock-model")
        second = service.run_shot_prompt(skill, source.revision_id, "mock", "mock-model")

        assert second.revision.artifact_id == first.revision.artifact_id
        assert [item.number for item in service.store.revisions_for_artifact(first.revision.artifact_id)] == [1, 2]
        artifacts = [
            artifact
            for artifact in service.store.artifacts()
            if artifact["artifact_type"] == "shot_prompt_set"
            and artifact["business_key_value"] == source.revision_id
        ]
        assert len(artifacts) == 1
