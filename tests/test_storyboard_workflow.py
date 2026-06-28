from pathlib import Path
import shutil

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import ApprovalBlocked, ExportConflict, RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.1.0"
SCRIPT_ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))


def _approved_script_revision(service):
    result = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script")
    service.approve_revision(result.revision.revision_id, "tester")
    return service.store.current_approved("shengsi-chapter-001")


def test_storyboard_skill_package_is_discoverable():
    package = load_skill_package(STORYBOARD_SKILL_ROOT)

    assert package.skill_id == "ai-drama-storyboard-design-skill"
    assert package.version == "v0.1.0"
    assert package.metadata["execution_profiles"][0]["profile_id"] == "storyboard-markdown-mvp-v1"
    assert {item.validator_id for item in package.validators} >= {
        "storyboard_structure",
        "storyboard_duration",
        "storyboard_source_coverage",
        "storyboard_continuity",
    }


def test_storyboard_run_uses_current_approved_script_and_becomes_stale_when_script_changes(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)

        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        assert result.run.status == "SUCCEEDED"
        assert result.revision is not None
        assert service.revision_freshness(result.revision.revision_id) == "FRESH"
        assert service.revision_source_revision_id(result.revision.revision_id) == source.revision_id
        assert service.revision_source_approval_record(result.revision.revision_id)["action"] == "script_approved"

        service.approve_revision(result.revision.revision_id, "tester")
        fresh_export = tmp_path / "storyboard.md"
        service.export_approved(result.revision.artifact_id, fresh_export)
        assert fresh_export.exists()

        second_script = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script-2")
        service.approve_revision(second_script.revision.revision_id, "tester")

        assert service.revision_freshness(result.revision.revision_id) == "STALE"
        assert service.current_approved(result.revision.artifact_id).revision_id == result.revision.revision_id

        with pytest.raises(ApprovalBlocked):
            service.approve_revision(result.revision.revision_id, "tester")
        with pytest.raises(ExportConflict):
            service.export_approved(result.revision.artifact_id, tmp_path / "stale-storyboard.md")


def test_storyboard_runtime_reloads_freshness_after_restart(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        service.approve_revision(result.revision.revision_id, "tester")

    reopened = RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))
    try:
        assert reopened.revision_freshness(result.revision.revision_id) == "FRESH"
    finally:
        reopened.close()
