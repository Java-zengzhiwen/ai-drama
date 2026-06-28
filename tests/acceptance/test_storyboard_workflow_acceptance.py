import os
import json
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_storyboard_verification_script_exists():
    assert (REPO_ROOT / "tools" / "verify_storyboard_workflow.py").exists()


def test_storyboard_verification_ci_workflow_exists():
    assert (REPO_ROOT / ".github" / "workflows" / "storyboard-workflow-verification.yml").exists()


def test_storyboard_verification_entrypoint_runs():
    if os.environ.get("STORYBOARD_VERIFICATION_SELFTEST"):
        pytest.skip("skip recursive self-test inside verification entrypoint")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "verify_storyboard_workflow.py")],
        cwd=REPO_ROOT,
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
    assert "MISSING_SOURCE_SCENES" in data["source_coverage"]
    assert "EXTRA_SOURCE_REFERENCES" in data["source_coverage"]
    assert "ORDER_MISMATCH" in data["source_coverage"]
    assert any(item["test_item"] == "Migration Verify" for item in data["final_record_table"])


def test_storyboard_source_scene_extraction_supports_all_documented_headers():
    from tools.verify_storyboard_workflow import _extract_source_scenes

    text = """## Scene 1\nbody\n## Scene: 1-1\nbody\n## 场次：1-2\nbody\n"""
    assert _extract_source_scenes(text) == ["1", "1-1", "1-2"]
