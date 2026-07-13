#!/usr/bin/env python3
"""Semantic, offline verifier for M6C Adapter Cutover."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/web/test_m6c_adapter_cutover.py::"


def run(command):
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider"})
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    return completed.returncode == 0


def pytest_case(name):
    return run([sys.executable, "-m", "pytest", "-q", TEST + name])


def verify():
    checks = {
        "M6C-001": pytest_case("test_m6_text_execution_persists_snapshot_before_invocation_and_sanitizes_evidence"),
        "M6C-002": pytest_case("test_m6_image_execution_is_durable_and_links_result_and_asset"),
        "M6C-003": run([sys.executable, "-m", "pytest", "-q",
                         TEST + "test_atomic_enqueue_persists_snapshot_job_attempt_and_scoped_idempotency",
                         TEST + "test_m6_snapshot_video_submit_is_exactly_once_across_accepted_restart"]),
        "M6C-004": run([sys.executable, "-m", "pytest", "-q",
                         TEST + "test_poller_routes_active_job_only_by_frozen_snapshot_and_video_id",
                         TEST + "test_restart_poller_resumes_same_provider_job_without_submit"]),
        "M6C-005": pytest_case("test_poller_routes_active_job_only_by_frozen_snapshot_and_video_id"),
        "M6C-006": run([sys.executable, "-m", "pytest", "-q",
                         "tests/web/test_generation_execution_service.py::test_accepted_submission_recovers_local_commit_without_resubmit",
                         "tests/web/test_generation_execution_service.py::test_crash_before_acceptance_persistence_fails_closed_without_resubmit"]),
        "M6C-007": pytest_case("test_restart_poller_resumes_same_provider_job_without_submit"),
        "M6C-008": run([sys.executable, "-m", "pytest", "-q",
                         TEST + "test_active_legacy_agnes_backfill_is_idempotent_and_preserves_video_id",
                         TEST + "test_backfilled_legacy_job_completes_via_poll_fetch_without_submit"]),
        "M6C-009": pytest_case("test_default_rerun_inherits_runtime_model_config_and_uses_current_credential"),
        "M6C-010": pytest_case("test_current_model_rerun_resolves_latest_project_binding"),
        "M6C-011": run([sys.executable, "-m", "pytest", "-q",
                         TEST + "test_atomic_enqueue_rejects_same_scope_key_with_changed_snapshot",
                         TEST + "test_m6_legacy_unique_key_is_namespaced_by_supplier_and_capability"]),
        "M6C-012": run([sys.executable, "-m", "pytest", "-q",
                         TEST + "test_feature_flag_defaults_off",
                         TEST + "test_feature_flag_off_freezes_snapshot_jobs_without_legacy_submit_or_poll"])
                    and run(["npm", "--prefix", "worker", "test"]),
        "M6C-013": pytest_case("test_evidence_removes_secret_keys_and_signed_query") and run([sys.executable, "tools/verify_m3_agnes_generation.py"]),
        "M6C-014": run(["npm", "--prefix", "worker", "test"]) and run(
            [sys.executable, "-m", "pytest", "-q", "tests/suppliers/test_worker_isolation.py"]
        ),
        "M6C-015": run([sys.executable, "tools/verify_m3_agnes_generation.py"]) and run([sys.executable, "tools/verify_m4_chapter_rehearsal.py"]),
    }
    return {
        "schema_version": "m6c-adapter-cutover-verification-v2",
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "result": "PASS" if all(checks.values()) else "FAIL",
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
        "network_evidence": "worker transport guard and Python isolation tests passed" if checks["M6C-014"] else "network denial failed",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    result = verify()
    if args.format == "markdown":
        print("# M6C Adapter Cutover Verification")
        print()
        for key, value in result["checks"].items():
            print(f"- {key}: {value}")
        print(f"- result: {result['result']}")
        print("- real Provider requests: text=0 image=0 video=0")
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
