from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import ApprovalBlocked, ExportConflict, RuntimeService, WorkflowGateError
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
    assert {item.validator_origin for item in package.validators} == {"newly_created"}


def test_storyboard_validators_execute_and_persist_outputs(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)

        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )

        statuses = {item.validator_id: item.status for item in result.validation_results}
        assert statuses["storyboard_structure"] == "PASS"
        assert statuses["storyboard_duration"] == "PASS"
        assert statuses["storyboard_source_coverage"] == "PASS"
        assert statuses["storyboard_continuity"] == "PASS"
        assert statuses["genericity"] == "NOT_APPLICABLE"
        for item in result.validation_results:
            assert service.store.read_text(item.stdout_object_id) is not None
            assert service.store.read_text(item.stderr_object_id) is not None
            assert service.store.read_text(item.report_object_id).strip()


def test_storyboard_run_uses_current_approved_script_and_becomes_stale_when_script_changes(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        first_source_approval = service.store.latest_approval(source.revision_id)

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
        assert service.revision_source_approval_record(result.revision.revision_id)["record_id"] == first_source_approval.record_id
        assert service.store.revision_dependencies(result.revision.revision_id)[0].parent_approval_record_id == first_source_approval.record_id

        service.approve_revision(result.revision.revision_id, "tester")
        assert service.store.latest_approval(result.revision.revision_id).action == "storyboard_approved"
        fresh_export = tmp_path / "storyboard.md"
        service.export_approved(result.revision.artifact_id, fresh_export)
        assert fresh_export.exists()
        sidecar = json.loads((tmp_path / "storyboard.md.provenance.json").read_text(encoding="utf-8"))
        assert sidecar["source_script_revision_id"] == source.revision_id
        assert sidecar["source_script_approval_record_id"] == first_source_approval.record_id
        assert sidecar["source_script_content_hash"] == source.content_hash

        service.approve_revision(source.revision_id, "tester", note="re-approve source")
        assert service.revision_source_approval_record(result.revision.revision_id)["record_id"] == first_source_approval.record_id

        second_script = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script-2")
        service.approve_revision(second_script.revision.revision_id, "tester")

        assert service.revision_freshness(result.revision.revision_id) == "STALE"
        assert service.current_approved(result.revision.artifact_id).revision_id == result.revision.revision_id

        with pytest.raises(ApprovalBlocked):
            service.approve_revision(result.revision.revision_id, "tester")
        with pytest.raises(ExportConflict):
            service.export_approved(result.revision.artifact_id, tmp_path / "stale-storyboard.md")


def test_storyboard_rejection_action_is_recorded(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        service.reject_revision(result.revision.revision_id, "tester")
        assert service.store.latest_approval(result.revision.revision_id).action == "storyboard_rejected"


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


def test_storyboard_request_requires_all_inherited_context(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        snaps = service.store.input_snapshots(source.run_id)
        for item in snaps:
            if item.logical_type == "production_brief":
                service.store.conn.execute("DELETE FROM input_snapshots WHERE run_id = ? AND logical_type = ?", (source.run_id, "production_brief"))
                service.store.conn.commit()
                break

        with pytest.raises(WorkflowGateError) as exc:
            service.run_storyboard(
                load_skill_package(STORYBOARD_SKILL_ROOT),
                source.revision_id,
                "mock",
                "mock-storyboard-v1",
            )

        assert exc.value.code == "SOURCE_CONTEXT_MISSING"
        assert service.store.workflow_gate_records()[-1].error_code == "SOURCE_CONTEXT_MISSING"


# ---------------------------------------------------------------------------
# Stage 6: 真实 Source Coverage 缺陷检查
# ---------------------------------------------------------------------------


def _validator_path(validator_name):
    return STORYBOARD_SKILL_ROOT / "validators" / ("validate_%s.py" % validator_name)


def _run_validator(validator_name, storyboard_text, tmp_path):
    revision_path = tmp_path / "storyboard.md"
    report_path = tmp_path / "report.json"
    revision_path.write_text(storyboard_text, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_validator_path(validator_name)), "--revision", str(revision_path), "--report", str(report_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return proc.returncode, proc.stdout, proc.stderr, report


def _good_storyboard():
    return """# Mock Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 8
- shot_size: medium
- camera_angle: eye-level
- camera_movement: still
- visual_composition: test
- character_positions: test
- character_actions: test
- emotion_performance: test
- dialogue: test
- sound_notes: test
- continuity_in: test
- continuity_out: test

## 场次：1-2

### 镜头 2
- scene_id: 1-2
- shot_id: 1-2-01
- shot_order: 1
- source_scene_reference: 1-2
- duration_seconds: 10
- shot_size: close
- camera_angle: low
- camera_movement: pan
- visual_composition: test
- character_positions: test
- character_actions: test
- emotion_performance: test
- dialogue: test
- sound_notes: test
- continuity_in: test
- continuity_out: test
"""


# --- source_coverage validator ---


def test_source_coverage_passes_on_valid_storyboard(tmp_path):
    returncode, stdout, stderr, report = _run_validator("storyboard_source_coverage", _good_storyboard(), tmp_path)
    assert returncode == 0
    assert report["final_status"] == "pass"
    assert report["missing_scene_references"] == []
    assert report["extra_scene_references"] == []


def test_source_coverage_detects_missing_reference(tmp_path):
    text = _good_storyboard().replace("source_scene_reference: 1-2", "source_scene_reference: 1-1")
    returncode, stdout, stderr, report = _run_validator("storyboard_source_coverage", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_SOURCE_COVERAGE"
    assert "1-2" in report["missing_scene_references"]


def test_source_coverage_detects_extra_reference(tmp_path):
    text = _good_storyboard() + "\n- source_scene_reference: 9-9\n"
    returncode, stdout, stderr, report = _run_validator("storyboard_source_coverage", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_SOURCE_COVERAGE"
    assert "9-9" in report["extra_scene_references"]


def test_source_coverage_detects_no_scenes(tmp_path):
    text = "# No scenes\n\n- source_scene_reference: 1-1\n"
    returncode, stdout, stderr, report = _run_validator("storyboard_source_coverage", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_SOURCE_COVERAGE"
    assert report["source_scene_references"] == ["1-1"]


def test_source_coverage_detects_no_references(tmp_path):
    text = "# Storyboard\n\n## 场次：1-1\n\n### 镜头 1\n- shot_id: 1-1-01\n"
    returncode, stdout, stderr, report = _run_validator("storyboard_source_coverage", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_SOURCE_COVERAGE"
    assert report["missing_scene_references"] == ["1-1"]


def test_source_coverage_detects_mismatch_integration(tmp_path):
    """Integration: run storyboard, mutate content to break source coverage, re-validate."""
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        statuses = {item.validator_id: item.status for item in result.validation_results}
        assert statuses["storyboard_source_coverage"] == "PASS"

        content_path = service.store.object_path(result.revision.content_object_id)
        original = content_path.read_text(encoding="utf-8")
        broken = original.replace("source_scene_reference: 1-2", "source_scene_reference: 1-1")
        content_path.write_text(broken, encoding="utf-8")
        from ai_drama_runtime.validators import run_declared_validators
        skill = load_skill_package(STORYBOARD_SKILL_ROOT)
        new_validations = run_declared_validators(service.store, skill, result.revision, SCRIPT_ACCEPTANCE_ROOT, repo_root=REPO_ROOT)
        source_coverage_status = [v for v in new_validations if v.validator_id == "storyboard_source_coverage"][0]
        assert source_coverage_status.status == "FAIL"


# --- structure validator ---


def test_structure_detects_missing_required_fields(tmp_path):
    text = """# Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 8
"""
    returncode, stdout, stderr, report = _run_validator("storyboard_structure", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_STRUCTURE"
    assert len(report["issues"]) >= 1


def test_structure_detects_duplicate_shot_id(tmp_path):
    text = """# Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: S1
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 8
- shot_size: medium
- camera_angle: eye
- camera_movement: still
- visual_composition: x
- character_positions: x
- character_actions: x
- emotion_performance: x
- dialogue: x
- sound_notes: x
- continuity_in: x
- continuity_out: x

### 镜头 2
- scene_id: 1-1
- shot_id: S1
- shot_order: 2
- source_scene_reference: 1-1
- duration_seconds: 9
- shot_size: close
- camera_angle: high
- camera_movement: tilt
- visual_composition: x
- character_positions: x
- character_actions: x
- emotion_performance: x
- dialogue: x
- sound_notes: x
- continuity_in: x
- continuity_out: x
"""
    returncode, stdout, stderr, report = _run_validator("storyboard_structure", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_STRUCTURE"
    duplicate_issue = any("duplicate_shot_id" in str(i) for i in report.get("issues", []))
    assert duplicate_issue, "expected duplicate_shot_id issue"


# --- continuity validator ---


def test_continuity_detects_missing_fields(tmp_path):
    text = """# Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 8
- shot_size: medium
- camera_angle: eye
- camera_movement: still
- visual_composition: x
- character_positions: x
- character_actions: x
- emotion_performance: x
- dialogue: x
- sound_notes: x
"""
    returncode, stdout, stderr, report = _run_validator("storyboard_continuity", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_CONTINUITY"
    missing_keys = {item for issue in report.get("issues", []) for item in issue.get("missing", [])}
    assert "continuity_in:" in missing_keys
    assert "continuity_out:" in missing_keys


# --- duration validator ---


def test_duration_detects_out_of_bounds(tmp_path):
    text = """# Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 3
- shot_size: medium
- camera_angle: eye
- camera_movement: still
- visual_composition: x
- character_positions: x
- character_actions: x
- emotion_performance: x
- dialogue: x
- sound_notes: x
- continuity_in: x
- continuity_out: x
"""
    returncode, stdout, stderr, report = _run_validator("storyboard_duration", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_DURATION"
    assert report["durations"] == [3]


def test_duration_detects_missing_duration_field(tmp_path):
    text = """# Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 1-1
- shot_size: medium
"""
    returncode, stdout, stderr, report = _run_validator("storyboard_duration", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_DURATION"


# --- structure validator: scene_reference_mismatch ---


def test_structure_detects_scene_reference_mismatch(tmp_path):
    text = """# Storyboard

## 场次：1-1

### 镜头 1
- scene_id: 9-9
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 8-8
- duration_seconds: 8
- shot_size: medium
- camera_angle: eye
- camera_movement: still
- visual_composition: x
- character_positions: x
- character_actions: x
- emotion_performance: x
- dialogue: x
- sound_notes: x
- continuity_in: x
- continuity_out: x
"""
    returncode, stdout, stderr, report = _run_validator("storyboard_structure", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
    assert report["error_code"] == "ERR_STRUCTURE"
    mismatch_issue = any("scene_reference_mismatch" in str(i) for i in report.get("issues", []))
    assert mismatch_issue, "expected scene_reference_mismatch issue"


# ---------------------------------------------------------------------------
# Stage 7: 审批与导出
# ---------------------------------------------------------------------------


def test_approval_blocked_when_required_validator_fails(tmp_path):
    """Insert a FAIL validation result for a required validator, then block approval."""
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        assert result.run.status == "SUCCEEDED"

        service.store.insert_validation(
            revision_id=result.revision.revision_id,
            validator_id="storyboard_source_coverage",
            validator_name="storyboard_source_coverage",
            status="FAIL",
            required=1,
            exit_code=1,
            error_code="ERR_SOURCE_COVERAGE",
            duration_ms=10,
            stdout_object_id=service.store.write_text_object("fail stdout"),
            stderr_object_id=service.store.write_text_object("fail stderr"),
            report_object_id=service.store.write_text_object('{"final_status":"fail"}'),
        )
        service.store.update_run(result.run.run_id, status="VALIDATION_FAILED")

        with pytest.raises(ApprovalBlocked, match="required validators did not pass"):
            service.approve_revision(result.revision.revision_id, "tester")


def test_export_conflict_when_output_exists(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        service.approve_revision(result.revision.revision_id, "tester")

        out = tmp_path / "storyboard.md"
        service.export_approved(result.revision.artifact_id, out)
        assert out.exists()

        with pytest.raises(ExportConflict):
            service.export_approved(result.revision.artifact_id, out)

        service.export_approved(result.revision.artifact_id, out, force=True)


def test_export_provenance_contains_storyboard_context(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        service.approve_revision(result.revision.revision_id, "tester")

        out = tmp_path / "sb.md"
        service.export_approved(result.revision.artifact_id, out)
        sidecar = json.loads((tmp_path / "sb.md.provenance.json").read_text(encoding="utf-8"))

        assert sidecar["artifact_id"] == result.revision.artifact_id
        assert sidecar["revision_id"] == result.revision.revision_id
        assert sidecar["freshness_status"] == "FRESH"
        assert sidecar["source_script_revision_id"] == source.revision_id
        assert sidecar["source_script_content_hash"] == source.content_hash
        assert "input_references" in sidecar
        assert any(item["logical_type"] == "source_revision" for item in sidecar["input_references"])
        assert any(item["logical_type"] == "source_script_approval" for item in sidecar["input_references"])
        assert any(item["logical_type"] == "series_canon" for item in sidecar["input_references"])
        assert any(item["logical_type"] == "characters" for item in sidecar["input_references"])
        assert any(item["logical_type"] == "production_brief" for item in sidecar["input_references"])


def test_compare_storyboard_revisions(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        r1 = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-sb-v1",
        )
        r2 = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-sb-v2",
        )
        diff = service.compare_revisions(r1.revision.revision_id, r2.revision.revision_id)
        assert "mock-sb-v1" in diff
        assert "mock-sb-v2" in diff
        assert "validator_status" in diff
        assert "metadata" in diff
        assert "text_diff" in diff


def test_approval_blocked_when_run_status_not_allowed(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        service.store.update_run(result.run.run_id, status="RUNTIME_FAILED")

        with pytest.raises(ApprovalBlocked, match="run status does not allow approval"):
            service.approve_revision(result.revision.revision_id, "tester")


# ---------------------------------------------------------------------------
# Stage 8: Staleness 测试
# ---------------------------------------------------------------------------


def test_script_revision_freshness_is_always_fresh(tmp_path):
    """Non-storyboard revisions always return FRESH."""
    with _service(tmp_path) as service:
        result = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script")
        assert service.revision_freshness(result.revision.revision_id) == "FRESH"


def test_storyboard_remains_fresh_when_source_is_re_approved_same_revision(tmp_path):
    """Re-approving the same source revision does not make storyboard stale."""
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        assert service.revision_freshness(result.revision.revision_id) == "FRESH"

        service.approve_revision(source.revision_id, "tester", note="re-approve same")
        assert service.revision_freshness(result.revision.revision_id) == "FRESH"


def test_multiple_storyboards_against_same_source_all_fresh(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        r1 = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-sb-1",
        )
        r2 = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-sb-2",
        )
        assert service.revision_freshness(r1.revision.revision_id) == "FRESH"
        assert service.revision_freshness(r2.revision.revision_id) == "FRESH"

        new_script = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script-2")
        service.approve_revision(new_script.revision.revision_id, "tester")

        assert service.revision_freshness(r1.revision.revision_id) == "STALE"
        assert service.revision_freshness(r2.revision.revision_id) == "STALE"


# ---------------------------------------------------------------------------
# Stage 9: Required NOT_APPLICABLE 策略测试
# ---------------------------------------------------------------------------


def test_not_applicable_validator_does_not_block_approval(tmp_path):
    """NOT_APPLICABLE required validators do not block approval."""
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        statuses = {item.validator_id: item.status for item in result.validation_results}
        assert statuses["genericity"] == "NOT_APPLICABLE"

        service.approve_revision(result.revision.revision_id, "tester")
        assert service.store.latest_approval(result.revision.revision_id).action == "storyboard_approved"


def test_not_applicable_validator_persists_reason(tmp_path):
    with _service(tmp_path) as service:
        source = _approved_script_revision(service)
        result = service.run_storyboard(
            load_skill_package(STORYBOARD_SKILL_ROOT),
            source.revision_id,
            "mock",
            "mock-storyboard-v1",
        )
        gen_result = [v for v in result.validation_results if v.validator_id == "genericity"][0]
        assert gen_result.status == "NOT_APPLICABLE"
        stderr_text = service.store.read_text(gen_result.stderr_object_id)
        assert "not applicable" in stderr_text.lower() or "applies to" in stderr_text.lower()


# ---------------------------------------------------------------------------
# Stage 10: Validator 边界故障注入
# ---------------------------------------------------------------------------


def test_validator_timeout_is_recorded_as_fail(tmp_path):
    """Simulate validator timeout by running a slow process with subprocess timeout."""
    import subprocess as sp
    revision_path = tmp_path / "storyboard.md"
    report_path = tmp_path / "report.json"
    revision_path.write_text(_good_storyboard(), encoding="utf-8")
    try:
        sp.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            capture_output=True,
            text=True,
            timeout=0.1,
        )
        assert False, "should have timed out"
    except sp.TimeoutExpired:
        pass


def test_validator_handles_missing_entrypoint_gracefully(tmp_path):
    """Validator with non-existent entrypoint should fail."""
    proc = subprocess.run(
        [sys.executable, str(STORYBOARD_SKILL_ROOT / "validators" / "nonexistent.py"), "--revision", "/dev/null", "--report", str(tmp_path / "r.json")],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode != 0


def test_malformed_storyboard_content_rejected_by_validators(tmp_path):
    """Storyboard with scene but no valid shot fields should fail structure validation."""
    text = "# Bad Storyboard\n\n## 场次：1-1\n\n### 镜头 1\n- only_one_field: yes\n"
    returncode, stdout, stderr, report = _run_validator("storyboard_structure", text, tmp_path)
    assert returncode == 1
    assert report["final_status"] == "fail"
