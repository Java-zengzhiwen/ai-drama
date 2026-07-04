#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_BRANCH = "test/phase2-minimal-bundle-foundation"
PHASE1_BASELINE_COMMIT = "d9f13967d90ae0b2829c3182dd0aebe85c495daf"
PHASE2_DESIGN_BASELINE_COMMIT = "f933182a3db4b3f03de31b4241da29e5be9e3fdd"
PHASE2_PLANNING_BASELINE_COMMIT = "68283d41f6db549326979120de9881c995d14a41"
EXECUTION_START_COMMIT = "e2e8e5a33b3a470ea215d303eb0ccd3ed1b025bf"

AUTHORIZED_EXECUTION_START_FILES = {
    "docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md",
}

ALLOWED_CHANGED_FILES = {
    "ai_drama_runtime/cli.py",
    "ai_drama_runtime/services.py",
    "ai_drama_runtime/store.py",
    "ai_drama_runtime/validators.py",
    "docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/README.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py",
    "tests/test_cli.py",
    "tests/test_phase2_verifier.py",
    "tests/test_storyboard_canonical_workflow.py",
    "tests/test_storyboard_legacy_migration.py",
    "tests/test_storyboard_renderer.py",
    "tests/test_storyboard_workflow.py",
    "tests/test_validators_approval_export.py",
    "tools/verify_phase2_minimal_bundle_foundation.py",
}

PROTECTED_FILES = (
    "docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md",
    "docs/superpowers/specs/2026-06-29-phase-2-minimal-bundle-foundation-design.md",
    "docs/superpowers/specs/2026-06-29-phase-2-agent-execution-acceptance-contract.md",
    "docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md",
    "docs/testing/storyboard-workflow-verification/storyboard-verification-report.md",
    "docs/testing/storyboard-workflow-verification/storyboard-verification-report.json",
    "ai_drama_runtime/manifest.py",
    "ai_drama_runtime/storyboard_canonical.py",
    "ai_drama_runtime/storyboard_renderer.py",
    "ai_drama_runtime/storyboard_migration.py",
    "tools/verify_phase1_storyboard_canonicalization.py",
    "tools/verify_storyboard_workflow.py",
    "tests/test_phase1_verifier.py",
    "tests/acceptance/test_storyboard_workflow_acceptance.py",
)

PROTECTED_PREFIXES = {
    "v0_1_0_unchanged": "skills/ai-drama-storyboard-design-skill/v0.1.0",
    "v0_2_0_unchanged": "skills/ai-drama-storyboard-design-skill/v0.2.0",
    "script_v0_6_1_unchanged": "skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4",
}

WORKFLOW_FILE = ".github/workflows/storyboard-workflow-verification.yml"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    evidence: str
    expected: str = ""
    actual: str = ""


def _run(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)


def _check(name: str, ok: bool, evidence: str, expected: str = "", actual: str = "") -> CheckResult:
    return CheckResult(name=name, ok=ok, evidence=evidence, expected=expected, actual=actual)


def _pytest_summary() -> CheckResult:
    proc = _run([sys.executable, "-m", "pytest", "-q"])
    output = proc.stdout + proc.stderr
    match = re.search(r"(^|\s)(\d+) passed(?:\s|$)", output)
    actual = "%s passed" % match.group(2) if match else _last_line(output)
    return _check("baseline_pytest", proc.returncode == 0 and actual == "135 passed", actual, "135 passed", actual)


def _pytest_check(name: str) -> CheckResult:
    env = dict(os.environ)
    env["PHASE2_VERIFIER_INNER"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider"
    proc = _run([sys.executable, "-m", "pytest", "-q"], env=env)
    output = proc.stdout + proc.stderr
    summary = _last_line(output)
    return _check(name, proc.returncode == 0, summary, "pytest returncode 0", "returncode %s; %s" % (proc.returncode, summary))


def _last_line(text: str) -> str:
    return text.strip().splitlines()[-1] if text.strip() else ""


def _names_from_diff(base: str) -> set[str]:
    return set(filter(None, _run(["git", "diff", "--name-only", f"{base}..HEAD"]).stdout.splitlines()))


def _diff_quiet_check(name: str, base: str, paths: list[str]) -> CheckResult:
    proc = _run(["git", "diff", "--quiet", f"{base}..HEAD", "--", *paths])
    return _check(name, proc.returncode == 0, "unchanged" if proc.returncode == 0 else "changed", "unchanged", "unchanged" if proc.returncode == 0 else "changed")


def preflight_checks() -> list[CheckResult]:
    branch = _run(["git", "branch", "--show-current"]).stdout.strip()
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    status = _run(["git", "status", "--short"]).stdout.strip()
    phase1 = _run(["git", "merge-base", "--is-ancestor", PHASE1_BASELINE_COMMIT, EXECUTION_START_COMMIT])
    design = _run(["git", "merge-base", "--is-ancestor", PHASE2_DESIGN_BASELINE_COMMIT, EXECUTION_START_COMMIT])
    planning = _run(["git", "merge-base", "--is-ancestor", PHASE2_PLANNING_BASELINE_COMMIT, EXECUTION_START_COMMIT])
    changed = set(
        filter(
            None,
            _run(["git", "diff", "--name-only", f"{PHASE2_PLANNING_BASELINE_COMMIT}..{EXECUTION_START_COMMIT}"]).stdout.splitlines(),
        )
    )
    extra = sorted(changed - AUTHORIZED_EXECUTION_START_FILES)
    missing = sorted(AUTHORIZED_EXECUTION_START_FILES - changed)
    return [
        _check("branch", branch == EXPECTED_BRANCH, branch, EXPECTED_BRANCH, branch),
        _check("head", head == EXECUTION_START_COMMIT, head, EXECUTION_START_COMMIT, head),
        _check("phase1_baseline_ancestor", phase1.returncode == 0, "merge-base exit=%s" % phase1.returncode, "0", str(phase1.returncode)),
        _check("phase2_design_baseline_ancestor", design.returncode == 0, "merge-base exit=%s" % design.returncode, "0", str(design.returncode)),
        _check("phase2_planning_baseline_ancestor", planning.returncode == 0, "merge-base exit=%s" % planning.returncode, "0", str(planning.returncode)),
        _check("working_tree_clean", status == "", "clean" if status == "" else status, "clean", status or "clean"),
        _check(
            "execution_start_diff",
            not extra and not missing,
            ",".join(sorted(changed)),
            ",".join(sorted(AUTHORIZED_EXECUTION_START_FILES)),
            "extra=%s missing=%s" % (",".join(extra), ",".join(missing)),
        ),
        _pytest_summary(),
    ]


def portable_checks() -> list[CheckResult]:
    return [_pytest_check("portable_pytest")]


def final_checks(execution_start_commit: str = EXECUTION_START_COMMIT) -> list[CheckResult]:
    branch = _run(["git", "branch", "--show-current"]).stdout.strip()
    status = _run(["git", "status", "--short"]).stdout.strip()
    ancestor = _run(["git", "merge-base", "--is-ancestor", execution_start_commit, "HEAD"])
    diff_check = _run(["git", "diff", "--check"])
    changed = _names_from_diff(execution_start_commit)
    extra = sorted(changed - ALLOWED_CHANGED_FILES)
    results = [
        _check("branch", branch == EXPECTED_BRANCH, branch, EXPECTED_BRANCH, branch),
        _check("execution_start_ancestor", ancestor.returncode == 0, "merge-base exit=%s" % ancestor.returncode, "0", str(ancestor.returncode)),
        _check("working_tree_clean", status == "", "clean" if status == "" else status, "clean", status or "clean"),
        _check("diff_check", diff_check.returncode == 0, diff_check.stdout.strip() or diff_check.stderr.strip() or "clean", "clean", diff_check.stdout.strip() or diff_check.stderr.strip() or "clean"),
        _check("changed_file_allowlist", not extra, ",".join(extra) or "all changed files allowed", "no disallowed files", ",".join(extra)),
        _diff_quiet_check("protected_files_unchanged", execution_start_commit, list(PROTECTED_FILES)),
    ]
    for name, prefix in PROTECTED_PREFIXES.items():
        results.append(_diff_quiet_check(name, execution_start_commit, [prefix]))
    results.append(_diff_quiet_check("workflow_unchanged", execution_start_commit, [WORKFLOW_FILE]))
    results.append(_pytest_check("final_pytest"))
    return results


def _print_results(results: list[CheckResult]) -> int:
    failures = [item for item in results if not item.ok]
    if failures:
        print("PHASE2_MINIMAL_BUNDLE_FOUNDATION: FAIL")
        for item in failures:
            print("- check: %s" % item.name)
            print("  evidence: %s" % item.evidence)
            print("  expected: %s" % item.expected)
            print("  actual: %s" % item.actual)
        return 1
    for item in results:
        print("%s=%s" % (item.name, item.evidence))
    print("PHASE2_MINIMAL_BUNDLE_FOUNDATION: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "portable", "final"], default="portable")
    parser.add_argument("--execution-start-commit", default=EXECUTION_START_COMMIT)
    args = parser.parse_args(argv)
    if args.mode == "preflight":
        return _print_results(preflight_checks())
    if args.mode == "portable":
        return _print_results(portable_checks())
    return _print_results(final_checks(args.execution_start_commit))


if __name__ == "__main__":
    raise SystemExit(main())
