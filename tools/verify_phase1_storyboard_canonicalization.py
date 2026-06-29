#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    evidence: str
    expected: str = ""
    actual: str = ""


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _check(name: str, ok: bool, evidence: str, expected: str = "", actual: str = "") -> CheckResult:
    return CheckResult(name=name, ok=ok, evidence=evidence, expected=expected, actual=actual)


def _pytest_summary() -> CheckResult:
    proc = _run([sys.executable, "-m", "pytest", "-q"])
    output = proc.stdout + proc.stderr
    match = re.search(r"(^|\s)(\d+) passed(?:\s|$)", output)
    actual = "%s passed" % match.group(2) if match else output.strip().splitlines()[-1] if output.strip() else ""
    return _check("baseline_pytest", proc.returncode == 0 and actual == "92 passed", actual, "92 passed", actual)


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
    print("PHASE1_STORYBOARD_CANONICALIZATION: FAIL")
    print("- check: mode")
    print("  evidence: mode %s is not implemented yet" % args.mode)
    print("  expected: implementation slice after preflight")
    print("  actual: pending")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
