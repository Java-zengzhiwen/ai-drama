import json
from pathlib import Path

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import ApprovalBlocked, ExportConflict, RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))


def test_validator_statuses_and_required_approval_block(tmp_path):
    service = _service(tmp_path)
    result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock-a")

    statuses = {item.validator_id: item.status for item in result.validation_results}
    assert statuses["runtime_script_revision_structure"] == "PASS"
    assert "NOT_APPLICABLE" in statuses.values()

    bad = service.run_acceptance(
        load_skill_package(SKILL_ROOT),
        ACCEPTANCE_ROOT,
        "mock",
        "mock-b",
        mock_mode="empty_response",
    )
    assert bad.run.status == "PARSE_FAILED"

    service.approve_revision(result.revision.revision_id, "tester")
    assert service.current_approved("shengsi-chapter-001").revision_id == result.revision.revision_id


def test_required_failed_validator_blocks_approval(tmp_path):
    service = _service(tmp_path)
    result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock-a")
    service.store.insert_validation(
        revision_id=result.revision.revision_id,
        validator_id="forced",
        validator_name="forced",
        status="FAIL",
        required=1,
        exit_code=1,
        error_code="ERR_FORCED",
        duration_ms=1,
        stdout_object_id=service.store.write_text_object(""),
        stderr_object_id=service.store.write_text_object(""),
        report_object_id=service.store.write_text_object("{}"),
    )

    with pytest.raises(ApprovalBlocked):
        service.approve_revision(result.revision.revision_id, "tester")


def test_compare_includes_metadata_and_export_needs_force_with_sidecar(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    first = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock-a")
    second = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock-b")
    service.approve_revision(second.revision.revision_id, "tester")

    diff = service.compare_revisions(first.revision.revision_id, second.revision.revision_id)
    assert "metadata:" in diff
    assert "validator_status:" in diff
    assert "--- " in diff

    output = tmp_path / "approved.md"
    service.export_approved("shengsi-chapter-001", output)
    with pytest.raises(ExportConflict):
        service.export_approved("shengsi-chapter-001", output)
    service.export_approved("shengsi-chapter-001", output, force=True)
    sidecar = json.loads((tmp_path / "approved.md.provenance.json").read_text(encoding="utf-8"))
    assert sidecar["artifact_id"] == "shengsi-chapter-001"
    assert sidecar["revision_id"] == second.revision.revision_id
