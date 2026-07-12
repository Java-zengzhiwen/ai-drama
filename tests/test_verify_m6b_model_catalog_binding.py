import json
import subprocess
import sys


EXPECTED_CHECKS = {
    "stable_identities",
    "immutable_revisions",
    "overlay_base_isolation",
    "catalog_etag",
    "project_defaults",
    "operation_override",
    "fail_closed_resolution",
    "snapshot_hash",
    "idempotency_conflict",
    "loopback_guard",
    "migration_replay",
    "zero_real_network",
    "m1_m5_regression",
}


def test_m6b_verifier_emits_sanitized_json_and_markdown(tmp_path):
    json_path = tmp_path / "m6b.json"
    markdown_path = tmp_path / "m6b.md"
    result = subprocess.run(
        [
            sys.executable,
            "tools/verify_m6b_model_catalog_binding.py",
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(json_path.read_text())
    assert report["result"] == "PASS"
    assert set(report["checks"]) == EXPECTED_CHECKS
    assert all(value == "PASS" for value in report["checks"].values())
    assert report["real_request_counts"] == {"text": 0, "image": 0, "video": 0}
    combined = json_path.read_text() + markdown_path.read_text() + result.stdout
    assert "Bearer " not in combined
    assert "api_key" not in combined
    assert "https://apihub" not in combined
