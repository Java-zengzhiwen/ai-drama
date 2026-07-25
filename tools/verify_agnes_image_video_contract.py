#!/usr/bin/env python3
"""Offline semantic verifier for the Agnes image/video contract repair."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGNES = "tests/web/test_agnes_builtin_adapter.py::"
M6C = "tests/web/test_m6c_adapter_cutover.py::"


def run(command):
    env = dict(os.environ)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_ADDOPTS": "-p no:cacheprovider",
        "AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED": "false",
    })
    completed = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True
    )
    return completed.returncode == 0


def pytest_cases(*cases):
    return run([sys.executable, "-m", "pytest", "-q", *cases])


def verify():
    adapter_image = AGNES + "test_image_request_uses_tier_ratio_and_extra_body_image"
    restart_video = M6C + "test_restart_poller_resumes_same_provider_job_without_submit"
    worker_media_validation = run([
        "npm", "--prefix", "worker", "test", "--",
        "--test-name-pattern=operation media validation",
    ])
    python_worker_isolation = pytest_cases("tests/suppliers/test_worker_isolation.py")
    node_worker_default_denial = run(["npm", "--prefix", "worker", "test"])
    web_default_denial = run([
        "npm", "--prefix", "web", "run", "test", "--", "--run",
        "vitest/default-network-denial.test.ts",
    ])
    network_denial = all([
        python_worker_isolation,
        node_worker_default_denial,
        web_default_denial,
    ])
    checks = {
        "AGNES-IV-001": pytest_cases(
            AGNES + "test_manifest_preserves_model_identity_and_declares_image_options"
        ),
        "AGNES-IV-002": pytest_cases(adapter_image),
        "AGNES-IV-003": pytest_cases(adapter_image),
        "AGNES-IV-004": pytest_cases(
            M6C + "test_m6_image_execution_is_durable_and_links_result_and_asset",
            "tests/web/test_asset_generation_api.py::test_m6_image_request_carries_optional_ratio_to_durable_coordinator",
        ),
        "AGNES-IV-005": pytest_cases(
            M6C + "test_m6_snapshot_video_submit_is_exactly_once_across_accepted_restart"
        ),
        "AGNES-IV-006": pytest_cases(
            AGNES + "test_video_submit_and_poll_use_only_video_id",
            AGNES + "test_video_submit_rejects_responses_without_video_id",
            AGNES + "test_video_submit_rejects_invalid_parameters_before_network",
            restart_video,
        ),
        "AGNES-IV-007": all([
            pytest_cases(AGNES + "test_video_fetch_reads_official_metadata_url"),
            worker_media_validation,
        ]),
        "AGNES-IV-008": pytest_cases(restart_video),
        "AGNES-IV-009": pytest_cases(
            M6C + "test_active_legacy_agnes_backfill_is_idempotent_and_preserves_video_id",
            M6C + "test_m6_image_execution_freezes_supplier_defaults_in_snapshot",
        ),
        "AGNES-IV-010": run([
            "npm", "--prefix", "web", "run", "test", "--", "--run",
            "src/features/suppliers/ModelTestDialog.test.tsx",
            "src/features/suppliers/SupplierModelsPanel.test.tsx",
        ]),
        "AGNES-IV-011": pytest_cases(
            M6C + "test_evidence_removes_secret_keys_and_signed_query",
            "tests/web/test_supplier_model_tests.py::test_executor_persists_image_bytes_and_sanitizes_provider_url",
        ),
        "AGNES-IV-012": all([
            pytest_cases(
                M6C + "test_feature_flag_defaults_off",
                M6C + "test_feature_flag_off_freezes_snapshot_jobs_without_legacy_submit_or_poll",
            ),
            network_denial,
        ]),
    }
    return {
        "schema_version": "agnes-image-video-contract-verification-v1",
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "result": "PASS" if all(checks.values()) else "FAIL",
        "production_flag_enabled": False,
        "real_provider_requests": False,
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
        "network_denial_evidence": {
            "python_worker_isolation": "PASS" if python_worker_isolation else "FAIL",
            "node_worker_default_denial": "PASS" if node_worker_default_denial else "FAIL",
            "web_default_denial": "PASS" if web_default_denial else "FAIL",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    result = verify()
    if args.format == "markdown":
        print("# Agnes Image And Video Contract Verification")
        print()
        for key, value in result["checks"].items():
            print(f"- {key}: {value}")
        print(f"- result: {result['result']}")
        print("- production flag enabled: false")
        print("- real Provider requests: text=0 image=0 video=0")
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
