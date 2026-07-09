import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_verify_m4_chapter_rehearsal_writes_report_and_keeps_rerun_trace():
    report_json = REPO_ROOT / "runtime-data" / "reports" / "m4-chapter-rehearsal-report.json"
    report_md = REPO_ROOT / "runtime-data" / "reports" / "m4-chapter-rehearsal-report.md"
    report_json.unlink(missing_ok=True)
    report_md.unlink(missing_ok=True)

    result = subprocess.run(
        [sys.executable, "tools/verify_m4_chapter_rehearsal.py"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "M4_CHAPTER_REHEARSAL_PASS" in result.stdout
    assert "apihub.agnes-ai.com" not in result.stdout + result.stderr
    assert report_json.exists()
    assert report_md.exists()
    report = json.loads(report_json.read_text(encoding="utf-8"))
    assert report["source_job_id"]
    assert report["source_result_id"]
    assert report["rerun_job_id"]
    assert report["rerun_result_id"]
    assert report["current_selection"]["SHOT_002"] == report["rerun_result_id"]
    assert report["attempt_numbers"]["SHOT_001"] == [1]
    assert report["attempt_numbers"]["SHOT_002"] == [1, 2]
    assert report["schema_version"] == "m4-chapter-rehearsal-report-v1"
    assert report["environment"]["provider"] == "mock"
    assert report["environment"]["real_agnes_request_made"] is False
    assert report["scenarios"]["SHOT_001"]["passed"] is True
    assert report["scenarios"]["SHOT_002"]["passed"] is True
    assert report["operator_checklist"]
    assert "AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST" in report["deferred_items"]
    shot_002_timeline = report["job_status_timeline"]["SHOT_002"]
    assert shot_002_timeline[0]["status"] == "failed"
    assert shot_002_timeline[0]["error_code"] == "generation_failed"
    assert shot_002_timeline[1]["status"] == "completed"
    assert len(report["result_versions"]["SHOT_002"]) == 1
    assert report["verification_summary"]["real_agnes_request_made"] is False
    markdown = report_md.read_text(encoding="utf-8")
    assert "## Scenario Matrix" in markdown
    assert "## Operator Checklist" in markdown
    assert "## Deferred Items" in markdown
