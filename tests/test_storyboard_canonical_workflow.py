from pathlib import Path

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.storyboard_canonical import CONTENT_PROFILE, canonical_storyboard_hash, parse_canonical_json
from ai_drama_runtime.storyboard_renderer import render_storyboard_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_CANONICAL_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.2.0"
SCRIPT_ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"), repo_root=REPO_ROOT)


def _approved_script_revision(service):
    result = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script")
    service.approve_revision(result.revision.revision_id, "tester")
    return service.store.current_approved("shengsi-chapter-001")


def test_canonical_storyboard_skill_package_is_discoverable():
    package = load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT)

    assert package.skill_id == "ai-drama-storyboard-design-skill"
    assert package.version == "v0.2.0"
    assert package.metadata["execution_profiles"][0]["profile_id"] == CONTENT_PROFILE
    assert package.metadata["execution_profiles"][0]["output_format"] == "json"


def test_canonical_storyboard_run_stores_canonical_json_and_dependency(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-canonical-v1",
        )

        assert result.run.status == "SUCCEEDED"
        assert result.revision.artifact_type == "storyboard"
        assert result.revision.content_profile == CONTENT_PROFILE
        assert result.revision.derivation_type == "model_generation"
        assert result.revision.parser_version == "storyboard-canonical-json-v1"
        assert result.revision.approval_status == "pending"
        assert service.store.latest_approval(result.revision.revision_id) is None
        assert service.revision_source_revision_id(result.revision.revision_id) == source.revision_id

        canonical = parse_canonical_json(service.store.read_text(result.revision.content_object_id))
        assert canonical["source"]["script_revision_id"] == source.revision_id
        assert canonical["source"]["script_content_hash"] == source.content_hash
        assert result.revision.content_hash == canonical_storyboard_hash(canonical)
        assert render_storyboard_markdown(canonical).startswith("# Storyboard Canonical Render\n")
        statuses = {item.validator_id: item.status for item in result.validation_results}
        assert statuses["storyboard_canonical_schema"] == "PASS"
        assert statuses["storyboard_shot_identity"] == "PASS"
        assert statuses["storyboard_shot_order"] == "PASS"
        assert statuses["storyboard_duration"] == "PASS"
        assert statuses["storyboard_source_coverage"] == "PASS"
        assert statuses["storyboard_continuity"] == "PASS"
        assert statuses["storyboard_renderer_parity"] == "PASS"
        assert statuses["storyboard_source_freshness"] == "PASS"


def test_canonical_storyboard_export_renders_markdown_without_rewriting_canonical(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-canonical-v1",
        )
        canonical_before = service.store.read_text(result.revision.content_object_id)
        service.approve_revision(result.revision.revision_id, "tester")

        output = tmp_path / "canonical-storyboard.md"
        service.export_approved(result.revision.artifact_id, output)

        assert output.read_text(encoding="utf-8").startswith("# Storyboard Canonical Render\n")
        assert service.store.read_text(result.revision.content_object_id) == canonical_before


def test_canonical_source_coverage_validator_detects_missing_script_scene(tmp_path):
    with _service(tmp_path) as service:
        source_run = service.run_acceptance(
            load_skill_package(SCRIPT_SKILL_ROOT),
            SCRIPT_ACCEPTANCE_ROOT,
            "mock",
            "mock",
            mock_mode="three_scene_script",
        )
        service.approve_revision(source_run.revision.revision_id, "tester")

        result = service.run_storyboard(
            load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
            source_run.revision.revision_id,
            "mock",
            "mock-storyboard-canonical-v1",
        )

        statuses = {item.validator_id: item for item in result.validation_results}
        assert statuses["storyboard_source_coverage"].status == "FAIL"
        assert statuses["storyboard_source_coverage"].error_code == "SHOT_COVERAGE_INCOMPLETE"


def test_canonical_continuity_validator_detects_unknown_source_unit(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-canonical-v1",
        )
        canonical = parse_canonical_json(service.store.read_text(result.revision.content_object_id))
        canonical["shots"][0]["continuity_out"]["source_unit_or_shot_id"] = "SHOT_MISSING"
        object_id = service.store.write_text_object(__import__("json").dumps(canonical, ensure_ascii=False, sort_keys=True))
        broken = service.store.insert_revision(
            artifact_id=result.revision.artifact_id,
            artifact_type="storyboard",
            project_id=result.revision.project_id,
            chapter_id=result.revision.chapter_id,
            run_id=result.run.run_id,
            skill_id=result.revision.skill_id,
            skill_version=result.revision.skill_version,
            skill_package_hash=result.revision.skill_package_hash,
            runtime_provider="test",
            runtime_model="test",
            content_object_id=object_id,
            content_hash=canonical_storyboard_hash(canonical),
            raw_response_object_id=object_id,
            parser_version=result.revision.parser_version,
            content_profile=CONTENT_PROFILE,
        )
        validations = __import__("ai_drama_runtime.validators", fromlist=["run_declared_validators"]).run_declared_validators(
            service.store,
            load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
            broken,
            REPO_ROOT,
            repo_root=REPO_ROOT,
        )
        continuity = {item.validator_id: item for item in validations}["storyboard_continuity"]
        assert continuity.status == "FAIL"
        assert continuity.error_code == "SHOT_MAPPING_INVALID"


def test_canonical_freshness_detects_parent_hash_mismatch_and_blocks_approval(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-canonical-v1",
        )
        service.store.conn.execute(
            "UPDATE revision_dependencies SET parent_content_hash = ? WHERE child_revision_id = ?",
            ("0" * 64, result.revision.revision_id),
        )
        service.store.conn.commit()

        assert service.revision_freshness(result.revision.revision_id) == "STALE"
        import pytest
        from ai_drama_runtime.services import ApprovalBlocked

        with pytest.raises(ApprovalBlocked):
            service.approve_revision(result.revision.revision_id, "tester")
