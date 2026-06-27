import json
from pathlib import Path

import pytest

from ai_drama_runtime.manifest import SkillValidator
from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import ApprovalBlocked, ExportConflict, RuntimeService
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.validators import run_declared_validators


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


def test_required_not_applicable_validator_does_not_mark_run_failed(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    validators = list(package.validators) + [
        SkillValidator(
            "bundle_required",
            "bundle_required",
            package.validators[0].entrypoint,
            True,
            ["full_artifact_bundle"],
            [],
            [],
            1,
            "zero_is_pass",
            "migrated_skill",
            ["drama_script_json"],
            "NOT_APPLICABLE",
            "requires complete bundle",
        )
    ]
    package = type("Pkg", (), {**package.__dict__, "validators": validators})()

    result = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock")

    assert result.run.status == "SUCCEEDED"
    assert {item.validator_id: item.status for item in result.validation_results}["bundle_required"] == "NOT_APPLICABLE"


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
    output.unlink()
    with pytest.raises(ExportConflict):
        service.export_approved("shengsi-chapter-001", output)
    service.export_approved("shengsi-chapter-001", output, force=True)
    sidecar = json.loads((tmp_path / "approved.md.provenance.json").read_text(encoding="utf-8"))
    assert sidecar["artifact_id"] == "shengsi-chapter-001"
    assert sidecar["revision_id"] == second.revision.revision_id
    assert sidecar["export_time"].endswith("Z")
    assert service.store.read_text(service.store.export_records("shengsi-chapter-001")[-1].provenance_object_id) == (
        tmp_path / "approved.md.provenance.json"
    ).read_text(encoding="utf-8")


def test_validator_dependency_missing_timeout_and_crash_continue(tmp_path):
    store = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store.ensure_artifact("a", "drama_script", "p", "c")
    run = store.create_run(
        artifact_id="a",
        project_id="p",
        chapter_id="c",
        skill_id="s",
        skill_version="v1",
        skill_hash="h",
        runtime="mock",
        provider="mock",
        model="m",
        status="SUCCEEDED",
        request_object_id=store.write_text_object("request"),
        response_object_id=store.write_text_object("{}"),
        input_hash="h",
    )
    revision = store.insert_revision(
        artifact_id="a",
        artifact_type="drama_script",
        project_id="p",
        chapter_id="c",
        run_id=run.run_id,
        skill_id="s",
        skill_version="v1",
        skill_package_hash="h",
        runtime_provider="mock",
        runtime_model="m",
        content_object_id=store.write_text_object("# Script\n\n## Scene\nBody"),
        content_hash="h",
        raw_response_object_id=store.write_text_object("{}"),
        parser_version="p",
    )
    timeout_py = tmp_path / "timeout.py"
    crash_py = tmp_path / "crash.py"
    pass_py = tmp_path / "pass.py"
    timeout_py.write_text("import time; time.sleep(2)\n", encoding="utf-8")
    crash_py.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    pass_py.write_text("print('ok')\n", encoding="utf-8")
    validators = [
        SkillValidator("missing", "missing", pass_py, False, ["drama_script_revision"], ["python3", "{entrypoint}"], ["definitely_missing_pkg_xyz"], 1, "zero_is_pass"),
        SkillValidator("timeout", "timeout", timeout_py, False, ["drama_script_revision"], ["python3", "{entrypoint}"], [], 1, "zero_is_pass"),
        SkillValidator("crash", "crash", crash_py, False, ["drama_script_revision"], ["python3", "{entrypoint}"], [], 1, "zero_is_pass"),
        SkillValidator("pass", "pass", pass_py, False, ["drama_script_revision"], ["python3", "{entrypoint}"], [], 1, "zero_is_pass"),
    ]
    package = type("Pkg", (), {"validators": validators, "root": tmp_path})()

    results = run_declared_validators(store, package, revision, tmp_path, repo_root=tmp_path)
    statuses = {item.validator_id: item.status for item in results}
    assert statuses["missing"] == "SKIPPED_DEPENDENCY_MISSING"
    assert statuses["timeout"] == "FAIL"
    assert statuses["crash"] == "FAIL"
    assert statuses["pass"] == "PASS"
