#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BRANCH = "test/storyboard-complete-verification"
EXECUTION_START_COMMIT = "63590fd5230eb2f874d41b8aa0dbe9bfd2ca4874"
FOUNDATION_BASELINE_COMMIT = "69f27e8168ade5e241e9c643746c62220e9e09de"
AUTHORIZED_PREP_FILES = {
    "AGENTS.md",
    "docs/superpowers/plans/2026-06-29-phase-1-storyboard-canonicalization-implementation-plan.md",
    "docs/superpowers/specs/2026-06-29-phase-1-agent-execution-acceptance-contract.md",
}
FROZEN_FILES = {
    "docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md",
    "docs/superpowers/specs/2026-06-29-phase-1-agent-execution-acceptance-contract.md",
    "docs/superpowers/plans/2026-06-29-phase-1-storyboard-canonicalization-implementation-plan.md",
}
ALLOWED_CHANGED_FILES = {
    "ai_drama_runtime/store.py",
    "ai_drama_runtime/services.py",
    "ai_drama_runtime/request.py",
    "ai_drama_runtime/parser.py",
    "ai_drama_runtime/runtime.py",
    "ai_drama_runtime/validators.py",
    "ai_drama_runtime/cli.py",
    "ai_drama_runtime/manifest.py",
    "ai_drama_runtime/storyboard_canonical.py",
    "ai_drama_runtime/storyboard_renderer.py",
    "ai_drama_runtime/storyboard_migration.py",
    "tools/verify_phase1_storyboard_canonicalization.py",
    "tools/verify_storyboard_workflow.py",
    "docs/superpowers/reports/2026-06-29-phase-1-storyboard-canonicalization-verification.md",
}
ALLOWED_CHANGED_PREFIXES = (
    "skills/ai-drama-storyboard-design-skill/v0.2.0/",
    "tests/",
)
REQUIRED_CANONICAL_VALIDATORS = {
    "storyboard_canonical_schema",
    "storyboard_shot_identity",
    "storyboard_shot_order",
    "storyboard_duration",
    "storyboard_source_coverage",
    "storyboard_continuity",
    "storyboard_renderer_parity",
    "storyboard_source_freshness",
}


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
    actual = "%s passed" % match.group(2) if match else output.strip().splitlines()[-1] if output.strip() else ""
    return _check("baseline_pytest", proc.returncode == 0 and actual == "92 passed", actual, "92 passed", actual)


def _pytest_check(name: str) -> CheckResult:
    env = dict(os.environ)
    env["PHASE1_VERIFIER_INNER"] = "1"
    proc = _run([sys.executable, "-m", "pytest", "-q"], env=env)
    output = proc.stdout + proc.stderr
    summary = output.strip().splitlines()[-1] if output.strip() else ""
    return _check(name, proc.returncode == 0, summary, "pytest returncode 0", "returncode %s; %s" % (proc.returncode, summary))


def preflight_checks() -> list[CheckResult]:
    branch = _run(["git", "branch", "--show-current"]).stdout.strip()
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    status = _run(["git", "status", "--short"]).stdout.strip()
    ancestor = _run(["git", "merge-base", "--is-ancestor", FOUNDATION_BASELINE_COMMIT, "HEAD"])
    diff = _run(["git", "diff", "--name-only", f"{FOUNDATION_BASELINE_COMMIT}..HEAD"]).stdout.splitlines()
    diff_set = set(diff)
    return [
        _check("branch", branch == EXPECTED_BRANCH, branch, EXPECTED_BRANCH, branch),
        _check("head", head == EXECUTION_START_COMMIT, head, EXECUTION_START_COMMIT, head),
        _check("foundation_ancestor", ancestor.returncode == 0, "merge-base exit=%s" % ancestor.returncode, "0", str(ancestor.returncode)),
        _check("working_tree_clean", status == "", "clean" if status == "" else status, "clean", status or "clean"),
        _check(
            "authorized_prep_diff",
            diff_set <= AUTHORIZED_PREP_FILES,
            ",".join(diff),
            ",".join(sorted(AUTHORIZED_PREP_FILES)),
            ",".join(sorted(diff_set)),
        ),
        _pytest_summary(),
    ]


def portable_checks() -> list[CheckResult]:
    return [_pytest_check("portable_pytest")]


def final_checks() -> list[CheckResult]:
    branch = _run(["git", "branch", "--show-current"]).stdout.strip()
    status = _run(["git", "status", "--short"]).stdout.strip()
    ancestor = _run(["git", "merge-base", "--is-ancestor", EXECUTION_START_COMMIT, "HEAD"])
    diff_check = _run(["git", "diff", "--check"])
    changed = _run(["git", "diff", "--name-only", f"{EXECUTION_START_COMMIT}..HEAD"]).stdout.splitlines()
    changed_set = set(changed)
    disallowed = sorted(
        path
        for path in changed_set
        if path not in ALLOWED_CHANGED_FILES and not any(path.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
    )
    frozen_changed = sorted(path for path in changed_set if path in FROZEN_FILES)
    v0_1_changed = sorted(path for path in changed_set if path.startswith("skills/ai-drama-storyboard-design-skill/v0.1.0/"))
    try:
        manifest = json.loads((REPO_ROOT / "skills/ai-drama-storyboard-design-skill/v0.2.0/skill.json").read_text(encoding="utf-8"))
        validators = {item.get("validator_id") for item in manifest.get("validators", []) if item.get("required") is True}
    except Exception:
        validators = set()
    missing_validators = sorted(REQUIRED_CANONICAL_VALIDATORS - validators)
    return [
        _check("branch", branch == EXPECTED_BRANCH, branch, EXPECTED_BRANCH, branch),
        _check("execution_start_ancestor", ancestor.returncode == 0, "merge-base exit=%s" % ancestor.returncode, "0", str(ancestor.returncode)),
        _check("working_tree_clean", status == "", "clean" if status == "" else status, "clean", status or "clean"),
        _check("git_diff_check", diff_check.returncode == 0, diff_check.stdout.strip() or "clean", "clean", diff_check.stdout.strip() or diff_check.stderr.strip() or "clean"),
        _check("changed_file_allowlist", not disallowed, ",".join(disallowed) or "all changed files allowed", "no disallowed files", ",".join(disallowed)),
        _check("frozen_docs_unchanged", not frozen_changed, ",".join(frozen_changed) or "unchanged", "unchanged", ",".join(frozen_changed)),
        _check("v0_1_0_unchanged", not v0_1_changed, ",".join(v0_1_changed) or "unchanged", "unchanged", ",".join(v0_1_changed)),
        _check("required_canonical_validators", not missing_validators, ",".join(sorted(validators)), ",".join(sorted(REQUIRED_CANONICAL_VALIDATORS)), ",".join(missing_validators)),
        _pytest_check("final_pytest"),
    ]


def _print_results(results: list[CheckResult]) -> int:
    failures = [item for item in results if not item.ok]
    if failures:
        print("PHASE1_STORYBOARD_CANONICALIZATION: FAIL")
        for item in failures:
            print("- check: %s" % item.name)
            print("  evidence: %s" % item.evidence)
            print("  expected: %s" % item.expected)
            print("  actual: %s" % item.actual)
        return 1
    for item in results:
        print("%s=%s" % (item.name, item.evidence))
    print("PHASE1_STORYBOARD_CANONICALIZATION: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight", "portable", "final"], default="portable")
    args = parser.parse_args(argv)
    if args.mode == "preflight":
        return _print_results(preflight_checks())
    if args.mode == "portable":
        return _print_results(portable_checks())
    return _print_results(final_checks())


if __name__ == "__main__":
    raise SystemExit(main())
