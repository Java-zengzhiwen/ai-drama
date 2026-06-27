#!/usr/bin/env python3
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
REPORTS = ROOT / "test-reports" / "phase-b-contract"
REPORTS.mkdir(parents=True, exist_ok=True)


def run(cmd, cwd=ROOT):
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except Exception:
        payload = {}
    return proc, payload


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def refresh_fixture_hashes(fixture):
    sidecar_path = fixture / "evidence-sidecar.json"
    if sidecar_path.exists():
        sidecar = load(sidecar_path)
        for path_value in list(sidecar.get("hashes", {}).keys()):
            path = fixture / path_value
            if path.exists():
                sidecar["hashes"][path_value] = sha(path)
        write(sidecar_path, sidecar)

    handoff = load(fixture / "script-handoff-manifest.json")
    for group in ["input_refs", "output_refs"]:
        for ref in handoff.get(group, {}).values():
            if isinstance(ref, dict):
                path = fixture / ref.get("path", "")
                if path.exists():
                    ref["sha256"] = sha(path)
    for key in ["validation_report_ref", "stage_result_ref"]:
        ref = handoff.get(key)
        if isinstance(ref, dict):
            path = fixture / ref.get("path", "")
            if path.exists():
                ref["sha256"] = sha(path)
    write(fixture / "script-handoff-manifest.json", handoff)

    registry_path = fixture / "artifact-registry.json"
    if registry_path.exists():
        registry = load(registry_path)
        for item in registry.get("artifacts", []):
            path = fixture / item.get("path", "")
            if path.exists():
                item["sha256"] = sha(path)
                item["size_bytes"] = path.stat().st_size
        write(registry_path, registry)


def fixture_copy(name="neutral-project"):
    tmp = Path(tempfile.mkdtemp(prefix="phase-b-contract-"))
    shutil.copytree(ROOT / "fixtures" / name, tmp / "fixture")
    return tmp, tmp / "fixture"


records = []


def record(name, cmd, expected_result, expected_error_code="", cwd=ROOT):
    proc, payload = run(cmd, cwd=cwd)
    actual_result = "pass" if proc.returncode == 0 else "fail"
    actual_error_code = payload.get("error_code", "")
    passed = actual_result == expected_result and (not expected_error_code or actual_error_code == expected_error_code)
    records.append({
        "name": name,
        "command": " ".join(map(str, cmd)),
        "expected_result": expected_result,
        "expected_error_code": expected_error_code,
        "actual_result": actual_result,
        "actual_error_code": actual_error_code,
        "exit_code": proc.returncode,
        "passed": passed,
        "stdout_tail": proc.stdout[-800:],
        "stderr_tail": proc.stderr[-800:],
    })


with tempfile.TemporaryDirectory(prefix="phase-b-schema-") as td:
    td = Path(td)
    schema = td / "draft-feature.schema.json"
    instance = td / "instance.json"
    report = td / "report.json"
    write(schema, {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"known": {"type": "string"}},
        "unevaluatedProperties": False,
    })
    write(instance, {"known": "ok", "extra": "must be rejected by real Draft 2020-12"})
    record(
        "draft_2020_12_unevaluated_properties_rejected",
        [PY, "validators/validate_schema.py", "--schema", str(schema), "--instance", str(instance), "--report", str(report)],
        "fail",
        "ERR_SCHEMA_VALIDATION",
    )


tmp, f = fixture_copy()
d = load(f / "script-handoff-manifest.json")
first_output = next(iter(d["output_refs"].values()))
if isinstance(first_output, dict):
    first_output.pop("sha256", None)
write(f / "script-handoff-manifest.json", d)
record(
    "handoff_refs_require_sha256",
    [PY, "validators/validate_handoff_contract.py", "--handoff", str(f / "script-handoff-manifest.json"), "--base-dir", str(f), "--report", str(REPORTS / "missing-sha.json")],
    "fail",
    "ERR_HANDOFF_REFS",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
d = load(f / "script-handoff-manifest.json")
d["output_refs"].pop("source_claim_audit", None)
write(f / "script-handoff-manifest.json", d)
record(
    "handoff_requires_source_claim_audit_output",
    [PY, "validators/validate_handoff_contract.py", "--handoff", str(f / "script-handoff-manifest.json"), "--base-dir", str(f), "--report", str(REPORTS / "source-claim-handoff.json")],
    "fail",
    "ERR_HANDOFF_REFS",
)
shutil.rmtree(tmp)

tmp, f = fixture_copy()
d = load(f / "script-handoff-manifest.json")
d["validation_report_ref"] = {"path": "missing-validation.json", "sha256": "0" * 64}
write(f / "script-handoff-manifest.json", d)
record(
    "handoff_validation_report_ref_must_exist",
    [PY, "validators/validate_handoff_contract.py", "--handoff", str(f / "script-handoff-manifest.json"), "--base-dir", str(f), "--report", str(REPORTS / "missing-validation-ref.json")],
    "fail",
    "ERR_HANDOFF_REFS",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
d = load(f / "script-handoff-manifest.json")
d["stage_result_ref"] = {"path": "script-approval-request.json", "sha256": "0" * 64}
write(f / "script-handoff-manifest.json", d)
record(
    "handoff_stage_result_ref_hash_must_match",
    [PY, "validators/validate_handoff_contract.py", "--handoff", str(f / "script-handoff-manifest.json"), "--base-dir", str(f), "--report", str(REPORTS / "stale-stage-ref.json")],
    "fail",
    "ERR_HANDOFF_REFS",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
d = load(f / "source-conflict-registry.json")
if "items" in d:
    d["items"] = d.get("items", [])[1:]
else:
    d["conflicts"] = d.get("conflicts", [])[1:]
write(f / "source-conflict-registry.json", d)
record(
    "source_claim_audit_requires_known_conflict_registry_entries",
    [PY, "validators/validate_source_claim_audit.py", "--source-claim-audit", str(f / "source-claim-audit.json"), "--source-conflicts", str(f / "source-conflict-registry.json"), "--report", str(REPORTS / "source-claim-registry-missing.json")],
    "fail",
    "ERR_SOURCE_CLAIM_AUDIT_REGISTRY_MISSING",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
d = load(f / "schema-validation-report.json")
d["status"] = "pending_r1_validator_run"
d["repair_version"] = "v0.6.1-rc2.3-r1"
d["reports"] = {"schema-script": {"final_status": "pass", "instance_path": "/" + "Users/example/" + "phase" + "-b/script.json"}}
write(f / "schema-validation-report.json", d)
refresh_fixture_hashes(f)
record(
    "handoff_rejects_stale_schema_validation_report",
    [PY, "validators/validate_handoff_contract.py", "--handoff", str(f / "script-handoff-manifest.json"), "--base-dir", str(f), "--report", str(REPORTS / "stale-schema-validation-report.json")],
    "fail",
    "ERR_AUTHORITATIVE_STALE",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
d = load(f / "final-validation-report.json")
d["status"] = "pending_refreshed_validation"
d["repair_version"] = "v0.6.1-rc2.3-r1"
write(f / "final-validation-report.json", d)
refresh_fixture_hashes(f)
record(
    "integrity_rejects_pending_final_validation_report",
    [PY, "validators/validate_artifact_integrity.py", "--artifact-registry", str(f / "artifact-registry.json"), "--evidence-sidecar", str(f / "evidence-sidecar.json"), "--review-request", str(f / "script-approval-request.json"), "--base-dir", str(f), "--report", str(REPORTS / "pending-final-validation-report.json")],
    "fail",
    "ERR_AUTHORITATIVE_STALE",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
d = load(f / "script.json")
d["artifact_version"] = "wrong-version"
write(f / "script.json", d)
refresh_fixture_hashes(f)
record(
    "handoff_rejects_mismatched_script_artifact_version",
    [PY, "validators/validate_handoff_contract.py", "--handoff", str(f / "script-handoff-manifest.json"), "--base-dir", str(f), "--report", str(REPORTS / "mismatched-artifact-version.json")],
    "fail",
    "ERR_ARTIFACT_VERSION_MISMATCH",
)
shutil.rmtree(tmp)


with tempfile.TemporaryDirectory(prefix="phase-b-beats-") as td:
    td = Path(td)
    beats = td / "core-story-beats.json"
    report = td / "core-story-beats-report.json"
    write(beats, {"beats": [{"beat_id": "B1", "importance": "critical", "source_evidence": "source paragraph 1", "summary": "too coarse"}]})
    record(
        "critical_core_beats_require_dimensional_fields",
        [PY, "validators/validate_core_story_beats.py", "--beat-registry", str(beats), "--report", str(report)],
        "fail",
        "ERR_BEAT_DIMENSION_FIELD",
    )


tmp, f = fixture_copy()
script = f / "script.md"
script.write_text(script.read_text(encoding="utf-8") + "\n\n### Script Body\nMARKDOWN_ONLY_FACT_NOT_IN_JSON\n", encoding="utf-8")
record(
    "markdown_only_story_fact_rejected",
    [PY, "validators/validate_markdown_json_equivalence.py", "--script", str(script), "--script-json", str(f / "script.json"), "--coverage-report", str(f / "coverage-report.json"), "--report", str(REPORTS / "markdown-only.json")],
    "fail",
    "ERR_EQUIV_MARKDOWN_ONLY_CONTENT",
)
shutil.rmtree(tmp)


tmp, f = fixture_copy()
script_text = (f / "script.md").read_text(encoding="utf-8").strip()
presentation = f / "presentation.md"
presentation.write_text(
    "# Acceptance Presentation\n"
    "Current Revision\nScene Overview\nStrict Critical Beat Coverage\nPartial Beats\n"
    "Production Assumptions\nAdaptation Extensions\nSource Conflicts\nCurrent Issues\n"
    "Recommended Decision\nNext After Approval\nRevision Impact Scope\n"
    "SCRIPT_APPROVAL\nUSER_ACCEPTANCE_REQUIRED\napproved_for_downstream=true\n"
    "accept\nrequest_revision\nreject\n\nFull Script\n\n" + script_text + "\n",
    encoding="utf-8",
)
record(
    "creator_presentation_rejects_auto_downstream_approval",
    [PY, "validators/validate_creator_presentation.py", "--presentation", str(presentation), "--script", str(f / "script.md"), "--report", str(REPORTS / "presentation-auto-approval.json")],
    "fail",
    "ERR_PRESENTATION_AUTO_APPROVAL",
)
shutil.rmtree(tmp)


with tempfile.TemporaryDirectory(prefix="phase-b-runtime-") as td:
    td = Path(td)
    out = td / "runtime.zip"
    record(
        "runtime_package_excludes_non_runtime_content",
        [PY, "scripts/build_runtime_package.py", "--root", str(ROOT), "--output", str(out)],
        "pass",
    )
    if out.exists():
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        forbidden = [
            n for n in names
            if n.startswith(("fixtures/", "test-reports/", "vendor/", "tests/"))
            or "pilot" in n.lower()
            or "gold" in n.lower()
            or "evaluation" in n.lower()
            or "__pycache__" in n
            or n.endswith((".pyc", ".pyo", ".DS_Store"))
        ]
        records.append({
            "name": "runtime_zip_forbidden_content_scan",
            "command": f"inspect {out}",
            "expected_result": "pass",
            "actual_result": "fail" if forbidden else "pass",
            "expected_error_code": "",
            "actual_error_code": "ERR_RUNTIME_FORBIDDEN_CONTENT" if forbidden else "",
            "exit_code": 1 if forbidden else 0,
            "passed": not forbidden,
            "forbidden_entries": forbidden[:50],
        })


all_ok = all(r["passed"] for r in records)
report = {"final_status": "pass" if all_ok else "fail", "phase_b_contract_tests": records}
(REPORTS / "run-phase-b-contract-tests.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
sys.exit(0 if all_ok else 1)
