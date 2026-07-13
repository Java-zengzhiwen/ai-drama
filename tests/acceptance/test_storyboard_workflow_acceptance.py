import os
import json
from pathlib import Path
import subprocess
import sys

import pytest


def test_storyboard_verifier_inner_pytest_is_scoped_to_storyboard_contract():
    import importlib.util
    import sys
    verifier_path = REPO_ROOT / "tools" / "verify_storyboard_workflow.py"
    spec = importlib.util.spec_from_file_location("storyboard_verifier", verifier_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    targets = module._storyboard_pytest_targets()
    assert targets
    assert "tests/web/test_m6c_adapter_cutover.py" not in targets
    assert all("storyboard" in target or "shot_prompt" in target or "acceptance" in target for target in targets)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_storyboard_verification_script_exists():
    assert (REPO_ROOT / "tools" / "verify_storyboard_workflow.py").exists()


def test_storyboard_verification_ci_workflow_exists():
    assert (REPO_ROOT / ".github" / "workflows" / "storyboard-workflow-verification.yml").exists()


def test_storyboard_verification_entrypoint_runs():
    if os.environ.get("STORYBOARD_VERIFICATION_SELFTEST"):
        pytest.skip("skip recursive self-test inside verification entrypoint")
    env = dict(os.environ)
    env["STORYBOARD_VERIFICATION_SELFTEST"] = "1"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "verify_storyboard_workflow.py")],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert proc.returncode == 0
    assert "STORYBOARD_TECHNICAL_VERDICT=" in proc.stdout


def test_storyboard_verification_report_is_repo_local():
    if os.environ.get("STORYBOARD_VERIFICATION_SELFTEST"):
        assert str(REPO_ROOT / "docs" / "testing" / "storyboard-workflow-verification").startswith(str(REPO_ROOT))
        return
    if os.environ.get("STORYBOARD_VERIFICATION_REPORT_CHECK") == "0":
        return
    report_dir = REPO_ROOT / "docs" / "testing" / "storyboard-workflow-verification"
    if not (report_dir / "storyboard-verification-report.md").exists():
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "verify_storyboard_workflow.py")],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=180,
        )
        assert proc.returncode == 0
    assert (report_dir / "storyboard-verification-report.md").exists()
    assert (report_dir / "storyboard-verification-report.json").exists()
    data = json.loads((report_dir / "storyboard-verification-report.json").read_text(encoding="utf-8"))
    assert data["status_flags"]["STORYBOARD_TECHNICAL_VERDICT"] in {"PASS", "FAIL"}
    assert "tested_commit_sha" in data["environment"]
    assert "tested_worktree_clean" in data["environment"]
    assert "head" not in data["environment"]
    assert "direct_pytest" in data["static_verification"]
    assert "verifier_inner_pytest" in data["static_verification"]
    assert "MISSING_SOURCE_SCENES" in data["source_coverage"]
    assert "EXTRA_SOURCE_REFERENCES" in data["source_coverage"]
    assert "ORDER_MISMATCH" in data["source_coverage"]
    assert any(item["test_item"] == "Migration Verify" for item in data["final_record_table"])
    verdict = next(item for item in data["final_record_table"] if item["test_item"] == "Final Verdict")
    assert verdict["status"] == data["status_flags"]["STORYBOARD_TECHNICAL_VERDICT"]
    direct = data["static_verification"]["direct_pytest"]
    verifier = data["static_verification"]["verifier_inner_pytest"]
    tested_branch = data["environment"]["tested_branch"]
    tested_commit_sha = data["environment"]["tested_commit_sha"]
    tested_worktree_clean = data["environment"]["tested_worktree_clean"]
    assert isinstance(tested_branch, str) and tested_branch
    assert isinstance(tested_commit_sha, str) and len(tested_commit_sha) == 40
    assert all(ch in "0123456789abcdef" for ch in tested_commit_sha)
    assert isinstance(tested_worktree_clean, bool)
    assert direct["returncode"] == 0
    assert direct["passed"] > 0
    assert direct["skipped"] >= 0
    assert verifier["returncode"] == 0
    assert verifier["passed"] > 0
    assert verifier["skipped"] == 1
    assert verifier["skip_reason"] == "recursive self-test guard"


def test_storyboard_source_scene_extraction_supports_all_documented_headers():
    from tools.verify_storyboard_workflow import _extract_source_scenes

    text = """## Scene 1\nbody\n## Scene: 1-1\nbody\n## 场次：1-2\nbody\n"""
    assert _extract_source_scenes(text) == ["1", "1-1", "1-2"]
