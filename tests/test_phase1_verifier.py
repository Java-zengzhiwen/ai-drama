import subprocess
import sys
import os
from importlib import util
from pathlib import Path

import pytest


if os.environ.get("PHASE1_VERIFIER_INNER") == "1":
    pytest.skip("skip verifier self-tests inside verifier pytest run", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO_ROOT / "tools" / "verify_phase1_storyboard_canonicalization.py"


def _verifier(*args):
    return subprocess.run(
        [sys.executable, "tools/verify_phase1_storyboard_canonicalization.py", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _load_verifier_module():
    spec = util.spec_from_file_location("phase1_verifier", VERIFIER_PATH)
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase1_verifier_preflight_checks_launch_contract(monkeypatch):
    verifier = _load_verifier_module()

    def fake_run(args):
        command = " ".join(args)
        if command == "git branch --show-current":
            return subprocess.CompletedProcess(args, 0, verifier.EXPECTED_BRANCH + "\n", "")
        if command == "git rev-parse HEAD":
            return subprocess.CompletedProcess(args, 0, verifier.EXECUTION_START_COMMIT + "\n", "")
        if command.startswith("git status --short"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if command.startswith("git merge-base --is-ancestor"):
            return subprocess.CompletedProcess(args, 0, "", "")
        if command.startswith("git diff --name-only"):
            return subprocess.CompletedProcess(args, 0, "\n".join(sorted(verifier.AUTHORIZED_PREP_FILES)) + "\n", "")
        raise AssertionError(command)

    monkeypatch.setattr(verifier, "_run", fake_run)
    monkeypatch.setattr(verifier, "_pytest_summary", lambda: verifier.CheckResult("baseline_pytest", True, "92 passed", "92 passed", "92 passed"))

    results = verifier.preflight_checks()

    assert {item.name: item.ok for item in results} == {
        "branch": True,
        "head": True,
        "foundation_ancestor": True,
        "working_tree_clean": True,
        "authorized_prep_diff": True,
        "baseline_pytest": True,
    }


def test_phase1_verifier_rejects_unknown_mode():
    result = _verifier("--mode", "unknown")

    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_phase1_verifier_portable_mode_passes():
    result = _verifier("--mode", "portable")

    assert result.returncode == 0
    assert "PHASE1_STORYBOARD_CANONICALIZATION: PASS" in result.stdout
