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
