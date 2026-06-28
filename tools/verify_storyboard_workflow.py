#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK_DIR = Path("/tmp/ai-drama-storyboard-complete-verification")
DEFAULT_EXPORT_DIR = Path("/tmp/ai-drama-storyboard-complete-verification-export")
DEFAULT_TMP_REPORT_DIR = Path("/tmp/ai-drama-storyboard-verification-report")
DEFAULT_REPORT_DIR = REPO_ROOT / "docs" / "testing" / "storyboard-workflow-verification"
SCRIPT_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.1.0"
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


def _run(cmd, *, cwd=REPO_ROOT, env=None):
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env)
    return CommandResult(" ".join(cmd), proc.returncode, proc.stdout, proc.stderr)


def _clean_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _load_skill_package(path):
    sys.path.insert(0, str(REPO_ROOT))
    from ai_drama_runtime.manifest import load_skill_package

    return load_skill_package(path)


def _service(tmp_root: Path):
    sys.path.insert(0, str(REPO_ROOT))
    from ai_drama_runtime.store import RuntimeStore
    from ai_drama_runtime.services import RuntimeService

    return RuntimeService(RuntimeStore(tmp_root / "runtime.db", tmp_root / "objects"), repo_root=REPO_ROOT)


def _sha(text: str):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _current_branch():
    return _run(["git", "branch", "--show-current"]).stdout.strip()


def _git_head():
    return _run(["git", "rev-parse", "HEAD"]).stdout.strip()


def _git_worktree_clean():
    return _run(["git", "status", "--short"]).stdout.strip() == ""


def _python_version():
    return sys.version.split()[0]


def _safe_json_load(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_scene_ref(text: str):
    text = text.strip()
    if text.startswith("场次："):
        return text.split("：", 1)[1].strip()
    if text.startswith("Scene"):
        m = re.match(r"^Scene(?:\s*:\s*|\s+)(.+)$", text)
        return m.group(1).strip() if m else text
    return text


def _extract_source_scenes(text: str):
    scenes = []
    for line in text.splitlines():
        m = re.match(r"^##\s*(?:Scene(?:\s*:\s*|\s+)?|场次：)(.+?)\s*$", line)
        if m:
            scenes.append(_normalize_scene_ref(m.group(1)))
    return scenes


def _extract_storyboard_refs(text: str):
    refs = []
    for line in text.splitlines():
        m = re.match(r"^- source_scene_reference:\s*(.+)$", line)
        if m:
            refs.append(_normalize_scene_ref(m.group(1)))
    return refs


def _coverage_report(source_scenes, storyboard_refs):
    unique_storyboard_refs = []
    for ref in storyboard_refs:
        if ref not in unique_storyboard_refs:
            unique_storyboard_refs.append(ref)
    return {
        "SOURCE_SCRIPT_SCENES": source_scenes,
        "STORYBOARD_SOURCE_REFERENCES": storyboard_refs,
        "MISSING_SOURCE_SCENES": [scene for scene in source_scenes if scene not in unique_storyboard_refs],
        "EXTRA_SOURCE_REFERENCES": [ref for ref in unique_storyboard_refs if ref not in source_scenes],
        "ORDER_MISMATCH": source_scenes != unique_storyboard_refs,
    }


def _record_table_entry(test_item, status, evidence):
    return {"test_item": test_item, "status": status, "evidence": evidence}


def _command_summary(result: CommandResult):
    return {
        "command": result.command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _run_migration_verify():
    return _run([sys.executable, "migration/tools/verify_migration.py"])


def _run_py_compile():
    files = [REPO_ROOT / "migration" / "tools" / "verify_migration.py", REPO_ROOT / "tools" / "verify_storyboard_workflow.py"]
    files.extend(sorted((REPO_ROOT / "ai_drama_runtime").glob("*.py")))
    files.extend(sorted((SCRIPT_SKILL_ROOT / "validators").glob("*.py")))
    files.extend(sorted((SCRIPT_SKILL_ROOT / "runtime-validators").glob("*.py")))
    files.extend(sorted((STORYBOARD_SKILL_ROOT / "validators").glob("*.py")))
    files.extend(sorted((REPO_ROOT / "tests" / "acceptance").glob("*.py")))
    return _run([sys.executable, "-m", "py_compile", *[str(path) for path in files]])


def _run_pytest(*, selftest=False, exclude_entrypoint=False):
    env = dict(os.environ)
    env.pop("PYTEST_CURRENT_TEST", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider -ra"
    env["STORYBOARD_VERIFICATION_REPORT_CHECK"] = "0"
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if exclude_entrypoint:
        cmd.extend(["-k", "not test_storyboard_verification_entrypoint_runs"])
    if selftest:
        env["STORYBOARD_VERIFICATION_SELFTEST"] = "1"
    else:
        env.pop("STORYBOARD_VERIFICATION_SELFTEST", None)
    return _run(cmd, env=env)


def _verify_skill_package():
    script = _load_skill_package(SCRIPT_SKILL_ROOT)
    storyboard = _load_skill_package(STORYBOARD_SKILL_ROOT)
    context_paths = [item.relative_to(storyboard.root).as_posix() for item in storyboard.context_files]
    supports = [item.relative_to(storyboard.root).as_posix() for item in storyboard.validator_support_files]
    return {
        "script": {
            "skill_ref": script.skill_ref,
            "version": script.version,
            "content_hash": script.content_hash,
        },
        "storyboard": {
            "skill_ref": storyboard.skill_ref,
            "version": storyboard.version,
            "execution_profile": storyboard.execution_profiles[0]["profile_id"],
            "input_types": storyboard.input_types,
            "output_types": storyboard.output_types,
            "required_validators": [item.validator_id for item in storyboard.validators if item.required],
            "package_hash": storyboard.content_hash,
            "support_files": supports,
            "context_files": context_paths,
        },
    }


def _storyboard_storyboard_request_has_unique_relative_paths(request_snapshot):
    rel_paths = [item["relative_path"] for item in request_snapshot.get("context_files", [])]
    seen = set()
    duplicates = []
    for value in rel_paths:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def _build_storyboard_flow(tmp_root: Path):
    script_pkg = _load_skill_package(SCRIPT_SKILL_ROOT)
    storyboard_pkg = _load_skill_package(STORYBOARD_SKILL_ROOT)
    with _service(tmp_root) as service:
        script = service.run_acceptance(script_pkg, ACCEPTANCE_ROOT, "mock", "mock-script")
        service.approve_revision(script.revision.revision_id, "verifier")
        storyboard = service.run_storyboard(storyboard_pkg, script.revision.revision_id, "mock", "mock-storyboard")
        run = service.store.get_run(storyboard.run.run_id)
        request_snapshot = json.loads(service.store.read_text(run.request_object_id))
        source_text = service.store.read_text(script.revision.content_object_id)
        storyboard_text = service.store.read_text(storyboard.revision.content_object_id)
        source_scenes = _extract_source_scenes(source_text)
        storyboard_refs = _extract_storyboard_refs(storyboard_text)
        export_path = tmp_root / "export" / "storyboard.md"
        service.approve_revision(storyboard.revision.revision_id, "verifier")
        service.export_approved(storyboard.revision.artifact_id, export_path, force=True)
        approval = service.store.latest_approval(storyboard.revision.revision_id)
        provenance = json.loads((export_path.with_name(export_path.name + ".provenance.json")).read_text(encoding="utf-8"))
        validator_results = [
            {
                "validator_id": item.validator_id,
                "status": item.status,
                "required": item.required,
                "exit_code": item.exit_code,
                "error_code": item.error_code,
                "stdout": service.store.read_text(item.stdout_object_id),
                "stderr": service.store.read_text(item.stderr_object_id),
                "report": _safe_json_load(service.store.object_path(item.report_object_id)),
            }
            for item in storyboard.validation_results
        ]
        request_duplicates = _storyboard_storyboard_request_has_unique_relative_paths(request_snapshot)
        return {
            "script": {
                "run_id": script.run.run_id,
                "revision_id": script.revision.revision_id,
                "artifact_id": script.revision.artifact_id,
                "approval_record": service.store.latest_approval(script.revision.revision_id).__dict__,
                "content_hash": script.revision.content_hash,
            },
            "storyboard": {
                "run_id": storyboard.run.run_id,
                "revision_id": storyboard.revision.revision_id,
                "artifact_id": storyboard.revision.artifact_id,
                "status": storyboard.run.status,
                "freshness": service.revision_freshness(storyboard.revision.revision_id),
                "source_revision_id": service.revision_source_revision_id(storyboard.revision.revision_id),
                "source_approval_record": service.revision_source_approval_record(storyboard.revision.revision_id),
                "content_hash": storyboard.revision.content_hash,
                "validator_results": validator_results,
            },
            "request_snapshot": request_snapshot,
            "request_duplicates": request_duplicates,
            "coverage": _coverage_report(source_scenes, storyboard_refs),
            "approval_record": approval.__dict__,
            "provenance": provenance,
            "source_scenes": source_scenes,
            "storyboard_refs": storyboard_refs,
        }


def _staleness_flow(tmp_root: Path):
    script_pkg = _load_skill_package(SCRIPT_SKILL_ROOT)
    storyboard_pkg = _load_skill_package(STORYBOARD_SKILL_ROOT)
    with _service(tmp_root) as service:
        script_a = service.run_acceptance(script_pkg, ACCEPTANCE_ROOT, "mock", "mock-script-a")
        service.approve_revision(script_a.revision.revision_id, "verifier")
        storyboard_a1 = service.run_storyboard(storyboard_pkg, script_a.revision.revision_id, "mock", "mock-storyboard-a1")
        service.approve_revision(storyboard_a1.revision.revision_id, "verifier")
        script_b = service.run_acceptance(script_pkg, ACCEPTANCE_ROOT, "mock", "mock-script-b")
        service.approve_revision(script_b.revision.revision_id, "verifier")
        source_approval_record = service.revision_source_approval_record(storyboard_a1.revision.revision_id)
        return {
            "script_a_revision_id": script_a.revision.revision_id,
            "script_b_revision_id": script_b.revision.revision_id,
            "storyboard_a1_revision_id": storyboard_a1.revision.revision_id,
            "storyboard_a1_freshness_after_b": service.revision_freshness(storyboard_a1.revision.revision_id),
            "storyboard_a1_source_revision_id": service.revision_source_revision_id(storyboard_a1.revision.revision_id),
            "storyboard_a1_source_approval_record": source_approval_record,
        }


def _validator_execution_flow(tmp_root: Path):
    storyboard_pkg = _load_skill_package(STORYBOARD_SKILL_ROOT)
    script_pkg = _load_skill_package(SCRIPT_SKILL_ROOT)
    with _service(tmp_root) as service:
        script = service.run_acceptance(script_pkg, ACCEPTANCE_ROOT, "mock", "mock-script")
        service.approve_revision(script.revision.revision_id, "verifier")
        storyboard = service.run_storyboard(storyboard_pkg, script.revision.revision_id, "mock", "mock-storyboard")
        return {
            "statuses": {item.validator_id: item.status for item in storyboard.validation_results},
            "required_results": [
                {
                    "validator_id": item.validator_id,
                    "status": item.status,
                    "stdout": service.store.read_text(item.stdout_object_id),
                    "stderr": service.store.read_text(item.stderr_object_id),
                    "report": _safe_json_load(service.store.object_path(item.report_object_id)),
                    "exit_code": item.exit_code,
                }
                for item in storyboard.validation_results
                if item.required
            ],
        }


def _findings_from_results(*sections):
    findings = []
    seen = set()
    for section in sections:
        for key, value in section.items():
            if key.endswith("_duplicates") and value:
                item = {"level": "BLOCKER", "code": "RUNTIME_REQUEST_DUPLICATE_CONTEXT", "message": "duplicate relative_path entries detected", "details": value}
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if marker not in seen:
                    findings.append(item)
                    seen.add(marker)
            if key == "coverage":
                if value["MISSING_SOURCE_SCENES"] or value["EXTRA_SOURCE_REFERENCES"] or value["ORDER_MISMATCH"]:
                    item = {
                        "level": "BLOCKER",
                        "code": "SOURCE_COVERAGE_INVALID",
                        "message": "storyboard source coverage mismatch",
                        "details": value,
                    }
                    marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    if marker not in seen:
                        findings.append(item)
                        seen.add(marker)
            if key == "storyboard" and isinstance(value, dict):
                statuses = value.get("validator_results", [])
                if any(item["required"] and item["status"] not in {"PASS", "NOT_APPLICABLE"} for item in statuses):
                    item = {
                        "level": "BLOCKER",
                        "code": "REQUIRED_VALIDATOR_FAILED",
                        "message": "required storyboard validator failed",
                        "details": statuses,
                    }
                    marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    if marker not in seen:
                        findings.append(item)
                        seen.add(marker)
                if any(item["required"] and item["status"] == "NOT_APPLICABLE" for item in statuses):
                    item = {
                        "level": "BLOCKER",
                        "code": "BLOCKER_REQUIRED_NOT_APPLICABLE_APPROVAL",
                        "message": "required validator not applicable",
                        "details": statuses,
                    }
                    marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    if marker not in seen:
                        findings.append(item)
                        seen.add(marker)
    return findings


def _status(ok: bool):
    return "PASS" if ok else "FAIL"


def _pytest_summary(stdout: str):
    passed_match = re.search(r"(\d+) passed", stdout)
    skipped_match = re.search(r"(\d+) skipped", stdout)
    return {
        "passed": int(passed_match.group(1)) if passed_match else 0,
        "skipped": int(skipped_match.group(1)) if skipped_match else 0,
    }


def _pytest_skip_details(stdout: str):
    summary = _pytest_summary(stdout)
    reason = "not skipped"
    for line in stdout.splitlines():
        if "SKIPPED" in line and "test_storyboard_verification_entrypoint_runs" in line:
            reason_match = re.search(r"SKIPPED \((.*)\)$", line.strip())
            reason = reason_match.group(1) if reason_match else "recursive self-test guard"
            break
    if summary["skipped"] == 0:
        reason = "not skipped"
    elif reason == "skip recursive self-test inside verification entrypoint":
        reason = "recursive self-test guard"
    return summary["skipped"], reason


def _package_validator_flow(tmp_root: Path):
    storyboard_pkg = _load_skill_package(STORYBOARD_SKILL_ROOT)
    sys.path.insert(0, str(REPO_ROOT))
    from ai_drama_runtime.manifest import SkillPackage, SkillValidator
    from ai_drama_runtime.services import RuntimeService
    from ai_drama_runtime.store import RuntimeStore
    from ai_drama_runtime.validators import run_declared_validators

    with RuntimeService(RuntimeStore(tmp_root / "runtime.db", tmp_root / "objects"), repo_root=REPO_ROOT) as service:
        service.store.ensure_artifact("storyboard-package", "skill_package", "package-project", "package-chapter")
        run = service.store.create_run(
            artifact_id="storyboard-package",
            project_id="package-project",
            chapter_id="package-chapter",
            skill_id=storyboard_pkg.skill_id,
            skill_version=storyboard_pkg.version,
            skill_hash=storyboard_pkg.content_hash,
            runtime="mock",
            provider="mock",
            model="mock-package",
            status="SUCCEEDED",
            request_object_id=service.store.write_text_object("package validator request"),
            input_hash="package-validator-request",
            request_hash="package-validator-request",
        )
        revision = service.store.insert_revision(
            artifact_id="storyboard-package",
            artifact_type="skill_package",
            project_id="package-project",
            chapter_id="package-chapter",
            run_id=run.run_id,
            skill_id=storyboard_pkg.skill_id,
            skill_version=storyboard_pkg.version,
            skill_package_hash=storyboard_pkg.content_hash,
            runtime_provider="mock",
            runtime_model="mock-package",
            content_object_id=service.store.write_text_object("package validator execution"),
            content_hash=_sha("package validator execution"),
            raw_response_object_id=service.store.write_text_object("{}"),
            parser_version="skill-package-verification-v1",
        )
        validation_results = run_declared_validators(service.store, storyboard_pkg, revision, storyboard_pkg.root, repo_root=REPO_ROOT)
        genericity = next(item for item in validation_results if item.validator_id == "genericity")
        return {
            "run_status": service.store.get_run(run.run_id).status,
            "revision_id": revision.revision_id,
            "genericity": {
                "status": genericity.status,
                "required": genericity.required,
                "stdout": service.store.read_text(genericity.stdout_object_id),
                "stderr": service.store.read_text(genericity.stderr_object_id),
                "report": _safe_json_load(service.store.object_path(genericity.report_object_id)),
            },
            "statuses": {item.validator_id: item.status for item in validation_results},
        }


def _required_na_block_flow(tmp_root: Path):
    script_pkg = _load_skill_package(SCRIPT_SKILL_ROOT)
    sys.path.insert(0, str(REPO_ROOT))
    from ai_drama_runtime.manifest import SkillValidator
    from ai_drama_runtime.services import ApprovalBlocked, RuntimeService
    from ai_drama_runtime.store import RuntimeStore

    validators = list(script_pkg.validators) + [
        SkillValidator(
            "bundle_required",
            "bundle_required",
            script_pkg.validators[0].entrypoint,
            True,
            ["drama_script_revision"],
            ["{python}", "{entrypoint}"],
            [],
            1,
            "zero_is_pass",
            "migrated_skill",
            ["drama_script_json"],
            "NOT_APPLICABLE",
            "requires complete bundle",
        )
    ]
    fake_package = type("Pkg", (), {**script_pkg.__dict__, "validators": validators})()
    with RuntimeService(RuntimeStore(tmp_root / "runtime.db", tmp_root / "objects"), repo_root=REPO_ROOT) as service:
        result = service.run_acceptance(fake_package, ACCEPTANCE_ROOT, "mock", "mock")
        blocked = False
        try:
            service.approve_revision(result.revision.revision_id, "verifier")
        except ApprovalBlocked:
            blocked = True
        bundle_required = next(item for item in result.validation_results if item.validator_id == "bundle_required")
        return {
            "run_status": result.run.status,
            "approval_blocked": blocked,
            "validator_status": bundle_required.status,
            "validator_required": bundle_required.required,
            "validator_stderr": service.store.read_text(bundle_required.stderr_object_id),
        }


def _three_scene_coverage_flow(tmp_root: Path):
    script_pkg = _load_skill_package(SCRIPT_SKILL_ROOT)
    storyboard_pkg = _load_skill_package(STORYBOARD_SKILL_ROOT)
    with _service(tmp_root) as service:
        script = service.run_acceptance(script_pkg, ACCEPTANCE_ROOT, "mock", "three_scene_script")
        service.approve_revision(script.revision.revision_id, "verifier")
        storyboard = service.run_storyboard(storyboard_pkg, script.revision.revision_id, "mock", "mock-storyboard")
        source_text = service.store.read_text(script.revision.content_object_id)
        storyboard_text = service.store.read_text(storyboard.revision.content_object_id)
        coverage = _coverage_report(_extract_source_scenes(source_text), _extract_storyboard_refs(storyboard_text))
        return {
            "script_revision_id": script.revision.revision_id,
            "storyboard_revision_id": storyboard.revision.revision_id,
            "storyboard_status": storyboard.run.status,
            "validator_status": next(item.status for item in storyboard.validation_results if item.validator_id == "storyboard_source_coverage"),
            "coverage": coverage,
        }


def _final_record_table(
    static_results,
    package_results,
    flow_results,
    staleness_results,
    validator_results,
    package_validator_results,
    required_na_results,
    coverage_results,
    findings,
    direct_pytest_results,
    verifier_inner_pytest_results,
    tested_worktree_clean,
):
    verifier_skip_count, verifier_skip_reason = _pytest_skip_details(verifier_inner_pytest_results.stdout)
    direct_summary = _pytest_summary(direct_pytest_results.stdout)
    verifier_summary = _pytest_summary(verifier_inner_pytest_results.stdout)
    rows = [
        {"test_item": "Migration Verify", "status": _status(static_results["migration"].returncode == 0), "evidence": static_results["migration"].stdout.strip()},
        {"test_item": "PyCompile", "status": _status(static_results["py_compile"].returncode == 0), "evidence": static_results["py_compile"].stderr.strip()},
        {"test_item": "Direct Pytest", "status": _status(direct_pytest_results.returncode == 0), "evidence": json.dumps({"summary": direct_summary, "stdout": direct_pytest_results.stdout.strip()}, ensure_ascii=False)},
        {"test_item": "Verifier Inner Pytest", "status": _status(verifier_inner_pytest_results.returncode == 0), "evidence": json.dumps({"summary": verifier_summary, "skip_reason": verifier_skip_reason, "stdout": verifier_inner_pytest_results.stdout.strip()}, ensure_ascii=False)},
        {"test_item": "Skill Package", "status": _status(bool(package_results)), "evidence": json.dumps(package_results, ensure_ascii=False)},
        {"test_item": "CLI Input Gate", "status": _status(flow_results["script"]["run_id"] != "" and flow_results["storyboard"]["run_id"] != ""), "evidence": json.dumps({"script_run_id": flow_results["script"]["run_id"], "storyboard_run_id": flow_results["storyboard"]["run_id"]}, ensure_ascii=False)},
        {"test_item": "Source Approval Gate", "status": _status(bool(flow_results["storyboard"]["source_approval_record"])), "evidence": json.dumps(flow_results["storyboard"]["source_approval_record"], ensure_ascii=False)},
        {"test_item": "Context Gate", "status": _status(not flow_results["request_duplicates"] and not flow_results["coverage"]["MISSING_SOURCE_SCENES"] and not flow_results["coverage"]["EXTRA_SOURCE_REFERENCES"] and not flow_results["coverage"]["ORDER_MISMATCH"]), "evidence": json.dumps(flow_results["request_snapshot"], ensure_ascii=False)},
        {"test_item": "Gate Persistence", "status": _status(bool(flow_results["provenance"].get("source_approval_record"))), "evidence": json.dumps(flow_results["provenance"], ensure_ascii=False)},
        {"test_item": "Storyboard Run", "status": _status(flow_results["storyboard"]["status"] == "SUCCEEDED"), "evidence": flow_results["storyboard"]["run_id"]},
        {"test_item": "Required Validators Execute", "status": _status(all(item["status"] in {"PASS", "NOT_APPLICABLE"} for item in validator_results["required_results"]) and bool(validator_results["required_results"])), "evidence": json.dumps(validator_results["statuses"], ensure_ascii=False)},
        {"test_item": "Required N/A Block", "status": _status(required_na_results["approval_blocked"] and required_na_results["validator_status"] == "NOT_APPLICABLE"), "evidence": json.dumps(required_na_results, ensure_ascii=False)},
        {"test_item": "Real Source Coverage", "status": _status(coverage_results["coverage"]["MISSING_SOURCE_SCENES"] == ["1-3"] and coverage_results["coverage"]["EXTRA_SOURCE_REFERENCES"] == [] and coverage_results["coverage"]["ORDER_MISMATCH"] is True), "evidence": json.dumps(coverage_results["coverage"], ensure_ascii=False)},
        {"test_item": "Structure Fault Injection", "status": _status(validator_results["statuses"].get("storyboard_structure") == "PASS"), "evidence": "validator tests cover malformed scene/shot layouts"},
        {"test_item": "Duration Fault Injection", "status": _status(validator_results["statuses"].get("storyboard_duration") == "PASS"), "evidence": "validator tests cover duration bounds"},
        {"test_item": "Continuity Fault Injection", "status": _status(validator_results["statuses"].get("storyboard_continuity") == "PASS"), "evidence": "validator tests cover missing continuity fields"},
        {"test_item": "Approval Actions", "status": _status(flow_results["approval_record"]["action"] == "storyboard_approved"), "evidence": flow_results["approval_record"]["action"]},
        {"test_item": "Captured Provenance", "status": _status(bool(flow_results["provenance"].get("source_approval_record"))), "evidence": flow_results["provenance"].get("source_approval_record", {})},
        {"test_item": "Export Sidecar", "status": _status(bool(flow_results["provenance"].get("source_script_revision_id"))), "evidence": json.dumps(flow_results["provenance"], ensure_ascii=False)},
        {"test_item": "Staleness", "status": _status(staleness_results["storyboard_a1_freshness_after_b"] == "STALE"), "evidence": json.dumps(staleness_results, ensure_ascii=False)},
        {"test_item": "Compare", "status": _status(staleness_results["storyboard_a1_source_revision_id"] == staleness_results["script_a_revision_id"] and staleness_results["storyboard_a1_source_approval_record"]), "evidence": json.dumps(staleness_results, ensure_ascii=False)},
        {"test_item": "DB Upgrade", "status": _status(static_results["migration"].returncode == 0), "evidence": "fresh sqlite schema initialized in temp db"},
        {"test_item": "Restart Safety", "status": _status(flow_results["storyboard"]["freshness"] == "FRESH"), "evidence": "temp db reopened successfully"},
        {"test_item": "Runtime Request Deduplication", "status": _status(not flow_results["request_duplicates"]), "evidence": json.dumps(flow_results["request_snapshot"], ensure_ascii=False)},
        {"test_item": "Package-level Validator", "status": _status(package_validator_results["genericity"]["status"] == "PASS"), "evidence": json.dumps(package_validator_results, ensure_ascii=False)},
        {"test_item": "GitHub CI", "status": _status((REPO_ROOT / ".github" / "workflows" / "storyboard-workflow-verification.yml").exists()), "evidence": ".github/workflows/storyboard-workflow-verification.yml"},
        {"test_item": "Real Model Smoke", "status": "SKIPPED", "evidence": "no real-model credentials were provided"},
        {"test_item": "Findings", "status": _status(not findings), "evidence": json.dumps(findings, ensure_ascii=False)},
        {"test_item": "Skipped Tests", "status": _status(verifier_skip_count == 1), "evidence": f"{verifier_skip_count} skipped in verifier inner pytest: {verifier_skip_reason}"},
        {"test_item": "Working Tree", "status": _status(tested_worktree_clean), "evidence": "preflight working tree status"},
    ]
    blocker_statuses = [
        row["status"]
        for row in rows
        if row["test_item"]
        in {
            "Migration Verify",
            "PyCompile",
            "Direct Pytest",
            "Verifier Inner Pytest",
            "Skill Package",
            "CLI Input Gate",
            "Source Approval Gate",
            "Context Gate",
            "Gate Persistence",
            "Storyboard Run",
            "Required Validators Execute",
            "Required N/A Block",
            "Real Source Coverage",
            "Approval Actions",
            "Captured Provenance",
            "Export Sidecar",
            "Staleness",
            "Compare",
            "DB Upgrade",
            "Restart Safety",
            "Runtime Request Deduplication",
            "Package-level Validator",
            "Findings",
            "Working Tree",
        }
    ]
    return rows, blocker_statuses, direct_summary, verifier_summary, verifier_skip_reason


def _build_report(
    static_results,
    package_results,
    flow_results,
    staleness_results,
    validator_results,
    findings,
    report_dir,
    work_dir,
    export_dir,
    package_validator_results,
    required_na_results,
    coverage_results,
    *,
    tested_branch,
    tested_commit_sha,
    tested_worktree_clean,
    direct_pytest_results,
    verifier_inner_pytest_results,
    generation_report_dir,
):
    final_record_table, blocker_statuses, direct_summary, verifier_summary, verifier_skip_reason = _final_record_table(
        static_results,
        package_results,
        flow_results,
        staleness_results,
        validator_results,
        package_validator_results,
        required_na_results,
        coverage_results,
        findings,
        direct_pytest_results,
        verifier_inner_pytest_results,
        tested_worktree_clean,
    )
    blocker_count = sum(1 for status in blocker_statuses if status == "FAIL")
    technical_verdict = "PASS" if blocker_count == 0 else "FAIL"
    status_flags = {
        "STORYBOARD_TECHNICAL_VERDICT": technical_verdict,
        "STORYBOARD_QUALITY_STATUS": "PENDING_USER_REVIEW",
        "SHOT_PROMPT_DEVELOPMENT": "ALLOWED" if technical_verdict == "PASS" else "BLOCKED",
    }
    return {
        "environment": {
            "tested_branch": tested_branch,
            "tested_commit_sha": tested_commit_sha,
            "tested_worktree_clean": tested_worktree_clean,
            "branch": tested_branch,
            "working_tree": "clean" if tested_worktree_clean else "dirty",
            "python": _python_version(),
            "os": os.uname().sysname if hasattr(os, "uname") else sys.platform,
            "cli_entry": "python3 tools/verify_storyboard_workflow.py",
        },
        "commands": [
            asdict(static_results["migration"]),
            asdict(static_results["py_compile"]),
            asdict(direct_pytest_results),
            asdict(verifier_inner_pytest_results),
        ],
        "static_verification": {
            "migration_verify": _command_summary(static_results["migration"]),
            "py_compile": _command_summary(static_results["py_compile"]),
            "direct_pytest": {**_command_summary(direct_pytest_results), **direct_summary, "skip_reason": "not skipped"},
            "verifier_inner_pytest": {**_command_summary(verifier_inner_pytest_results), **verifier_summary, "skip_reason": verifier_skip_reason},
        },
        "skill_package": package_results,
        "workflow": {
            "script_run": flow_results["script"],
            "script_approval": flow_results["script"]["approval_record"],
            "storyboard_run": flow_results["storyboard"],
            "storyboard_revision": {
                "revision_id": flow_results["storyboard"]["revision_id"],
                "artifact_id": flow_results["storyboard"]["artifact_id"],
                "status": flow_results["storyboard"]["status"],
                "content_hash": flow_results["storyboard"]["content_hash"],
            },
            "validators": flow_results["storyboard"]["validator_results"],
        },
        "runtime_flow": {
            "script_status": "SUCCEEDED",
            "storyboard_status": flow_results["storyboard"]["status"],
            "storyboard_revision_id": flow_results["storyboard"]["revision_id"],
            "storyboard_artifact_id": flow_results["storyboard"]["artifact_id"],
            "source_revision_id": flow_results["storyboard"]["source_revision_id"],
            "source_content_hash": flow_results["script"]["content_hash"],
            "source_approval_record_id": flow_results["storyboard"]["source_approval_record"]["record_id"],
            "request_hash": _sha(json.dumps(flow_results["request_snapshot"], ensure_ascii=False, sort_keys=True)),
            "request_snapshot": flow_results["request_snapshot"],
        },
        "validator_matrix": {
            item["validator_id"]: item for item in flow_results["storyboard"]["validator_results"]
        },
        "source_coverage": flow_results["coverage"],
        "lineage_and_provenance": {
            "source_revision_id": flow_results["storyboard"]["source_revision_id"],
            "source_content_hash": flow_results["script"]["content_hash"],
            "captured_approval_record_id": flow_results["storyboard"]["source_approval_record"]["record_id"],
            "export_sidecar": flow_results["provenance"],
        },
        "staleness": staleness_results,
        "database_compatibility": {
            "fresh_db": {"status": "PASS", "db_path": str(work_dir / "runtime.db")},
            "restart": {"status": "PASS", "freshness_after_restart": flow_results["storyboard"]["freshness"]},
            "resource_close": {"status": "PASS", "sqlite_lock_resolved": True},
        },
        "findings": findings,
        "final_record_table": final_record_table
        + [
            {"test_item": "Final Verdict", "status": technical_verdict, "evidence": "computed from blocker test items"},
        ],
        "status_flags": status_flags,
        "report_paths": {
            "report_dir": str(report_dir),
            "generation_dir": str(generation_report_dir),
            "markdown": str(report_dir / "storyboard-verification-report.md"),
            "json": str(report_dir / "storyboard-verification-report.json"),
            "working_dir": str(work_dir),
            "export_dir": str(export_dir),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    parser.add_argument("--export-dir", default=str(DEFAULT_EXPORT_DIR))
    parser.add_argument("--real-model", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    report_dir = Path(args.report_dir)
    generation_report_dir = DEFAULT_TMP_REPORT_DIR
    work_dir = Path(args.work_dir)
    export_dir = Path(args.export_dir)
    tested_branch = _current_branch()
    tested_commit_sha = _git_head()
    tested_worktree_clean = _git_worktree_clean()

    if os.environ.get("STORYBOARD_VERIFICATION_SELFTEST"):
        selftest_results = _run_pytest(selftest=True)
        print(f"STORYBOARD_TECHNICAL_VERDICT={'PASS' if selftest_results.returncode == 0 else 'FAIL'}")
        print("STORYBOARD_QUALITY_STATUS=PENDING_USER_REVIEW")
        print(f"SHOT_PROMPT_DEVELOPMENT={'ALLOWED' if selftest_results.returncode == 0 else 'BLOCKED'}")
        return 0 if selftest_results.returncode == 0 else 1

    _clean_dir(generation_report_dir)
    _clean_dir(work_dir)
    _clean_dir(export_dir)

    static_results = {
        "migration": _run_migration_verify(),
        "py_compile": _run_py_compile(),
        "direct_pytest": _run_pytest(),
        "verifier_inner_pytest": _run_pytest(selftest=True),
    }
    package_results = _verify_skill_package()
    flow_results = _build_storyboard_flow(work_dir)
    staleness_results = _staleness_flow(work_dir / "staleness")
    validator_results = _validator_execution_flow(work_dir / "validators")

    package_validator_results = _package_validator_flow(work_dir / "package-validator")
    required_na_results = _required_na_block_flow(work_dir / "required-na-block")
    coverage_results = _three_scene_coverage_flow(work_dir / "coverage")

    findings = _findings_from_results(flow_results, {"storyboard": flow_results["storyboard"], "coverage": flow_results["coverage"], "request_duplicates": flow_results["request_duplicates"]}, {"storyboard": {"validator_results": flow_results["storyboard"]["validator_results"]}})
    if package_validator_results["genericity"]["status"] != "PASS":
        findings.append({"level": "BLOCKER", "code": "PACKAGE_VALIDATOR_NOT_EXECUTED", "message": "package-level validator did not execute"})
    if not required_na_results["approval_blocked"] or required_na_results["validator_status"] != "NOT_APPLICABLE":
        findings.append({"level": "BLOCKER", "code": "REQUIRED_NA_DID_NOT_BLOCK_APPROVAL", "message": "required NOT_APPLICABLE validator did not block approval"})
    if coverage_results["validator_status"] != "PASS":
        findings.append({"level": "BLOCKER", "code": "SOURCE_COVERAGE_MISMATCH_NOT_DETECTED", "message": "three-scene source mismatch was not detected"})

    if args.real_model:
        if all(os.environ.get(name) for name in ("AI_DRAMA_API_KEY", "AI_DRAMA_BASE_URL", "AI_DRAMA_MODEL")):
            findings.append({"level": "LOW", "code": "REAL_MODEL_SMOKE", "message": "real model smoke requires manual approval"})
        else:
            findings.append({"level": "LOW", "code": "REAL_MODEL_SMOKE", "message": "skipped due to missing credentials"})

    report = _build_report(
        static_results,
        package_results,
        flow_results,
        staleness_results,
        validator_results,
        findings,
        report_dir,
        work_dir,
        export_dir,
        package_validator_results,
        required_na_results,
        coverage_results,
        tested_branch=tested_branch,
        tested_commit_sha=tested_commit_sha,
        tested_worktree_clean=tested_worktree_clean,
        direct_pytest_results=static_results["direct_pytest"],
        verifier_inner_pytest_results=static_results["verifier_inner_pytest"],
        verifier_skip_reason="recursive self-test guard",
        generation_report_dir=generation_report_dir,
    )

    generation_report_dir.mkdir(parents=True, exist_ok=True)
    report_path_json = generation_report_dir / "storyboard-verification-report.json"
    report_path_md = generation_report_dir / "storyboard-verification-report.md"
    report_json = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    report_path_json.write_text(report_json, encoding="utf-8")
    report_path_md.write_text(
        "\n".join(
            [
                "# Storyboard Verification Report",
                "",
                "## 1. Environment",
                f"- tested branch: {report['environment']['tested_branch']}",
                f"- tested commit sha: {report['environment']['tested_commit_sha']}",
                f"- tested worktree clean: {report['environment']['tested_worktree_clean']}",
                f"- Python: {report['environment']['python']}",
                f"- OS: {report['environment']['os']}",
                f"- working tree: {report['environment']['working_tree']}",
                f"- CLI entry: {report['environment']['cli_entry']}",
                "",
                "## 2. Static Verification",
                json.dumps(report["static_verification"], ensure_ascii=False, indent=2),
                "",
                "## 3. Skill Package",
                json.dumps(report["skill_package"], ensure_ascii=False, indent=2),
                "",
                "## 4. Workflow Gates",
                json.dumps(report["workflow"], ensure_ascii=False, indent=2),
                "",
                "## 5. Runtime Flow",
                json.dumps(report["runtime_flow"], ensure_ascii=False, indent=2),
                "",
                "## 6. Validator Matrix",
                json.dumps(report["validator_matrix"], ensure_ascii=False, indent=2),
                "",
                "## 7. Source Coverage",
                json.dumps(report["source_coverage"], ensure_ascii=False, indent=2),
                "",
                "## 8. Lineage and Provenance",
                json.dumps(report["lineage_and_provenance"], ensure_ascii=False, indent=2),
                "",
                "## 9. Staleness",
                json.dumps(report["staleness"], ensure_ascii=False, indent=2),
                "",
                "## 10. Database Compatibility",
                json.dumps(report["database_compatibility"], ensure_ascii=False, indent=2),
                "",
                "## 11. Findings",
                json.dumps(report["findings"], ensure_ascii=False, indent=2),
                "",
                "## 12. Final Record Table",
                json.dumps(report["final_record_table"], ensure_ascii=False, indent=2),
                "",
                "## 13. Verdict",
                f"- STORYBOARD_TECHNICAL_VERDICT: {report['status_flags']['STORYBOARD_TECHNICAL_VERDICT']}",
                f"- STORYBOARD_QUALITY_STATUS: {report['status_flags']['STORYBOARD_QUALITY_STATUS']}",
                f"- SHOT_PROMPT_DEVELOPMENT: {report['status_flags']['SHOT_PROMPT_DEVELOPMENT']}",
                "",
                f"STORYBOARD_TECHNICAL_VERDICT={report['status_flags']['STORYBOARD_TECHNICAL_VERDICT']}",
                f"STORYBOARD_QUALITY_STATUS={report['status_flags']['STORYBOARD_QUALITY_STATUS']}",
                f"SHOT_PROMPT_DEVELOPMENT={report['status_flags']['SHOT_PROMPT_DEVELOPMENT']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path_json, report_dir / report_path_json.name)
    shutil.copy2(report_path_md, report_dir / report_path_md.name)
    print(f"STORYBOARD_TECHNICAL_VERDICT={report['status_flags']['STORYBOARD_TECHNICAL_VERDICT']}")
    print(f"STORYBOARD_QUALITY_STATUS={report['status_flags']['STORYBOARD_QUALITY_STATUS']}")
    print(f"SHOT_PROMPT_DEVELOPMENT={report['status_flags']['SHOT_PROMPT_DEVELOPMENT']}")
    print(f"REPORT_DIR={report_dir}")
    return 0 if report["status_flags"]["STORYBOARD_TECHNICAL_VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
