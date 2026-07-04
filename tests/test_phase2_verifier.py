import os
import subprocess
import sys
from importlib import util
from pathlib import Path

import pytest


if os.environ.get("PHASE2_VERIFIER_INNER") == "1":
    pytest.skip("skip verifier self-tests inside verifier pytest run", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO_ROOT / "tools" / "verify_phase2_minimal_bundle_foundation.py"


def _load_verifier_module():
    spec = util.spec_from_file_location("phase2_verifier", VERIFIER_PATH)
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_preflight_branch_head_and_clean_tree(monkeypatch):
    verifier = _load_verifier_module()

    def fake_run(args, **kwargs):
        command = " ".join(args)
        if command == "git branch --show-current":
            return subprocess.CompletedProcess(args, 0, verifier.EXPECTED_BRANCH + "\n", "")
        if command == "git rev-parse HEAD":
            return subprocess.CompletedProcess(args, 0, verifier.EXECUTION_START_COMMIT + "\n", "")
        if command == "git status --short":
            return subprocess.CompletedProcess(args, 0, "", "")
        if command.startswith("git merge-base --is-ancestor"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if command.startswith("git diff --name-only"):
            return subprocess.CompletedProcess(args, 0, "\n".join(sorted(verifier.AUTHORIZED_EXECUTION_START_FILES)) + "\n", "")
        raise AssertionError(command)

    monkeypatch.setattr(verifier, "_run", fake_run)
    monkeypatch.setattr(
        verifier,
        "_pytest_summary",
        lambda: verifier.CheckResult("baseline_pytest", True, "135 passed", "135 passed", "135 passed"),
    )

    results = verifier.preflight_checks()

    assert {item.name: item.ok for item in results} == {
        "branch": True,
        "head": True,
        "phase1_baseline_ancestor": True,
        "phase2_design_baseline_ancestor": True,
        "phase2_planning_baseline_ancestor": True,
        "working_tree_clean": True,
        "execution_start_diff": True,
        "baseline_pytest": True,
    }


def test_portable_mode_runs_pytest_only(monkeypatch):
    verifier = _load_verifier_module()

    seen = []

    def fake_pytest(name):
        seen.append(name)
        return verifier.CheckResult(name, True, "pytest ok", "pytest ok", "pytest ok")

    monkeypatch.setattr(verifier, "_pytest_check", fake_pytest)

    results = verifier.portable_checks()

    assert [item.name for item in results] == ["portable_pytest"]
    assert all(item.ok for item in results)
    assert seen == ["portable_pytest"]


def test_final_mode_enforces_allowlist_and_frozen_files(monkeypatch):
    verifier = _load_verifier_module()

    allowed_changes = "\n".join(
        [
            "ai_drama_runtime/services.py",
            "tests/test_phase2_verifier.py",
            "tools/verify_phase2_minimal_bundle_foundation.py",
        ]
    )

    def fake_run(args, **kwargs):
        command = " ".join(args)
        if command == "git branch --show-current":
            return subprocess.CompletedProcess(args, 0, verifier.EXPECTED_BRANCH + "\n", "")
        if command == "git status --short":
            return subprocess.CompletedProcess(args, 0, "", "")
        if command.startswith("git merge-base --is-ancestor"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if command == "git diff --check":
            return subprocess.CompletedProcess(args, 0, "", "")
        if command == "git diff --name-only %s..HEAD" % verifier.EXECUTION_START_COMMIT:
            return subprocess.CompletedProcess(args, 0, allowed_changes + "\n", "")
        if command.startswith("git diff --quiet"):
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(command)

    monkeypatch.setattr(verifier, "_run", fake_run)
    monkeypatch.setattr(verifier, "_pytest_check", lambda name: verifier.CheckResult(name, True, "ok", "ok", "ok"))

    names = {item.name for item in verifier.final_checks()}

    assert "branch" in names
    assert "execution_start_ancestor" in names
    assert "working_tree_clean" in names
    assert "diff_check" in names
    assert "changed_file_allowlist" in names
    assert "protected_files_unchanged" in names
    assert "v0_1_0_unchanged" in names
    assert "v0_2_0_unchanged" in names
    assert "script_v0_6_1_unchanged" in names
    assert "workflow_unchanged" in names
    assert "final_pytest" in names
