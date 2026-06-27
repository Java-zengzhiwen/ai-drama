from pathlib import Path

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def test_all_migrated_validators_are_registered_except_common():
    package = load_skill_package(SKILL_ROOT)
    registered = {v.validator_id for v in package.validators if v.validator_origin == "migrated_skill"}
    actual = {
        path.stem.replace("validate_", "")
        for path in (SKILL_ROOT / "validators").glob("*.py")
        if path.name != "common.py"
    }

    assert actual <= registered
    assert "common" not in registered


def test_markdown_profile_records_bundle_validators_as_not_applicable(tmp_path):
    with RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")) as service:
        result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock")
        statuses = {item.validator_id: item.status for item in result.validation_results}

        assert statuses["runtime_script_revision_structure"] == "PASS"
        assert statuses["schema"] == "NOT_APPLICABLE"
        assert statuses["source_claim_audit"] == "NOT_APPLICABLE"
