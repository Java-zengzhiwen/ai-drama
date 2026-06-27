from pathlib import Path

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import ApprovalBlocked, RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_ROOT = (
    REPO_ROOT
    / "skills"
    / "ai-drama-script-adaptation-skill"
    / "v0.6.1-rc2.4"
)


def _service(tmp_path):
    store = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return RuntimeService(store)


def test_mock_run_persists_immutable_revision_and_restart_reads(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)

    result = service.run_acceptance(
        skill=package,
        acceptance_root=ACCEPTANCE_ROOT,
        runtime="mock",
        model="mock-script-v1",
    )

    assert result.run.status == "succeeded"
    assert any(
        item.validator_name == "runtime_script_revision_structure"
        and item.required
        and item.status == "passed"
        for item in result.validation_results
    )
    assert result.revision.artifact_id == "shengsi-chapter-001"
    assert result.revision.content_hash
    request_text = service.store.read_text(result.run.request_object_id)
    assert "approved-script.md" not in request_text
    assert (ACCEPTANCE_ROOT / "approved-script.md").read_text(encoding="utf-8") not in request_text

    restarted = _service(tmp_path)
    loaded = restarted.store.get_revision(result.revision.revision_id)
    assert loaded.content_hash == result.revision.content_hash
    assert restarted.store.read_text(loaded.content_object_id).startswith("#")


def test_approval_keeps_one_current_approved_revision_and_exports(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    first = service.run_acceptance(package, ACCEPTANCE_ROOT, runtime="mock", model="mock-a")
    second = service.run_acceptance(package, ACCEPTANCE_ROOT, runtime="mock", model="mock-b")

    service.approve_revision(first.revision.revision_id, reviewer="tester", note="first")
    service.approve_revision(second.revision.revision_id, reviewer="tester", note="second")

    current = service.current_approved("shengsi-chapter-001")
    assert current.revision_id == second.revision.revision_id
    assert service.store.get_revision(first.revision.revision_id).approval_status == "superseded"

    export_path = tmp_path / "approved.md"
    export_record = service.export_approved("shengsi-chapter-001", export_path)
    assert export_path.read_text(encoding="utf-8") == service.store.read_text(
        second.revision.content_object_id
    )
    assert export_record.revision_id == second.revision.revision_id
    assert service.store.export_records("shengsi-chapter-001")[-1].destination == str(export_path)


def test_compare_revisions_and_reject_records(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    first = service.run_acceptance(package, ACCEPTANCE_ROOT, runtime="mock", model="mock-a")
    second = service.run_acceptance(package, ACCEPTANCE_ROOT, runtime="mock", model="mock-b")

    diff = service.compare_revisions(
        first.revision.revision_id,
        second.revision.revision_id,
    )
    assert "--- " in diff
    assert "+++ " in diff

    service.reject_revision(second.revision.revision_id, reviewer="tester", note="needs work")
    assert service.store.get_revision(second.revision.revision_id).approval_status == "rejected"


def test_required_validator_failure_blocks_approval(tmp_path):
    skill_root = tmp_path / "skill"
    validators = skill_root / "validators"
    validators.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text("Skill instructions", encoding="utf-8")
    (validators / "fail.py").write_text(
        "import sys\nprint('nope')\nsys.exit(7)\n",
        encoding="utf-8",
    )
    (skill_root / "skill.json").write_text(
        """
{
  "skill_id": "test-skill",
  "version": "v1",
  "instructions_entry": "SKILL.md",
  "validators": [
    {
      "name": "fail",
      "entrypoint": "validators/fail.py",
      "required": true,
      "command": ["python3", "{entrypoint}"]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    package = load_skill_package(skill_root)
    service = _service(tmp_path)

    result = service.run_acceptance(package, ACCEPTANCE_ROOT, runtime="mock", model="mock")

    assert result.validation_results[0].status == "failed"
    with pytest.raises(ApprovalBlocked):
        service.approve_revision(result.revision.revision_id, reviewer="tester")
