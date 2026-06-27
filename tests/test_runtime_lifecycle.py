from pathlib import Path
import shutil

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))


def test_success_run_snapshots_each_input_and_excludes_reference_output(tmp_path):
    service = _service(tmp_path)
    case_root = tmp_path / "case"
    shutil.copytree(ACCEPTANCE_ROOT, case_root)
    result = service.run_acceptance(load_skill_package(SKILL_ROOT), case_root, "mock", "mock-a")

    assert result.run.status == "SUCCEEDED"
    assert result.revision is not None
    snapshots = service.store.input_snapshots(result.run.run_id)
    assert {item.logical_type for item in snapshots} == {
        "source_chapter",
        "series_canon",
        "characters",
        "production_brief",
    }
    request_text = service.store.read_text(result.run.request_object_id)
    assert "approved-script.md" not in request_text
    assert (case_root / "approved-script.md").read_text(encoding="utf-8") not in request_text

    original_hash = snapshots[0].sha256
    snapshots[0].source_path.write_text("mutated", encoding="utf-8")
    assert service.store.read_text(snapshots[0].object_id)
    assert service.store.input_snapshots(result.run.run_id)[0].sha256 == original_hash


def test_runtime_failure_and_parse_failure_are_persisted_without_revision(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)

    failed = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock", mock_mode="runtime_failure")
    assert failed.run.status == "RUNTIME_FAILED"
    assert failed.revision is None
    assert service.store.get_run(failed.run.run_id).error_code == "RUNTIME_FAILED"

    parsed = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock", mock_mode="parse_failure")
    assert parsed.run.status == "PARSE_FAILED"
    assert parsed.revision is None
    assert service.store.revisions_for_artifact("shengsi-chapter-001") == []


def test_multiple_success_runs_create_supersedes_chain(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    first = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock-a")
    second = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock-b")

    assert first.run.run_id != second.run.run_id
    assert first.revision.revision_id != second.revision.revision_id
    assert second.revision.supersedes_revision_id == first.revision.revision_id
