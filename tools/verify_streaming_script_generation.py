#!/usr/bin/env python3
"""Semantic, offline verifier for reconnectable script streaming."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERN = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})"
)


def run(command):
    env = dict(os.environ)
    for key in tuple(env):
        upper = key.upper()
        if upper in {
            "AGNES_API_KEY",
            "AIXORA_API_KEY",
            "ANTHROPIC_API_KEY",
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "XAI_API_KEY",
        }:
            env.pop(key, None)
    env.update(
        {
            "AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED": "false",
            "AI_DRAMA_SCRIPT_STREAMING_ENABLED": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
        }
    )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def pytest_cases(*cases):
    return run([sys.executable, "-m", "pytest", "-q", *cases])


def tracked_secret_scan():
    listed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        return False
    for raw_path in listed.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = ROOT / os.fsdecode(raw_path)
        try:
            content = path.read_bytes()
        except (OSError, IsADirectoryError):
            continue
        if SECRET_PATTERN.search(content):
            return False
    return True


def verify():
    checks = {
        "STREAM-001": pytest_cases("tests/web/test_streaming_response_evidence.py"),
        "STREAM-002": pytest_cases(
            "tests/web/test_aixora_adapter.py::test_text_responses_normalizes_output_and_reasoning_effort",
            "tests/web/test_aixora_adapter.py::test_text_stream_uses_responses_sse_contract",
        ),
        "STREAM-003": pytest_cases("tests/suppliers/test_worker_streaming.py"),
        "STREAM-004": pytest_cases(
            "tests/web/test_execution_snapshot.py::test_stream_gateway_uses_exact_frozen_snapshot_runtime_and_inputs"
        ),
        "STREAM-005": pytest_cases("tests/web/test_script_stream_store.py"),
        "STREAM-006": pytest_cases(
            "tests/acceptance/test_streaming_script_fake_provider.py",
            "tests/web/test_script_generation_runner.py",
        ),
        "STREAM-007": pytest_cases(
            "tests/web/test_script_stream_api.py::test_events_replay_only_after_cursor",
            "tests/web/test_script_stream_store.py::test_duplicate_event_must_have_same_hash",
        ),
        "STREAM-008": run(
            [
                "npm",
                "--prefix",
                "web",
                "run",
                "test",
                "--",
                "--run",
                "src/features/script/ScriptTab.test.tsx",
                "src/features/script/streaming.test.ts",
            ]
        ),
        "STREAM-009": pytest_cases(
            "tests/acceptance/test_streaming_script_fake_provider.py::test_fake_stream_api_creates_one_validated_revision_and_one_submit"
        ),
        "STREAM-010": pytest_cases(
            "tests/web/test_script_stream_api.py::test_streaming_flag_off_keeps_legacy_endpoint",
            "tests/acceptance/test_m6e_rollout_rollback.py::test_off_on_off_restart_preserves_history_and_off_uses_no_supplier_gateway",
        ),
        "STREAM-011": tracked_secret_scan(),
        "STREAM-012": pytest_cases(
            "tests/acceptance/test_streaming_script_fake_provider.py",
            "tests/web/test_script_stream_api.py",
            "tests/web/test_streaming_response_evidence.py",
        )
        and run(
            [
                "npm",
                "--prefix",
                "web",
                "run",
                "test",
                "--",
                "--run",
                "vitest/default-network-denial.test.ts",
            ]
        ),
    }
    passed = all(checks.values())
    return {
        "schema_version": "streaming-script-generation-verification-v1",
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "result": "PASS" if passed else "FAIL",
        "real_provider_requests": False,
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    result = verify()
    if args.format == "markdown":
        print("# Streaming Script Generation Verification")
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

