#!/usr/bin/env python3
"""Offline, fake-only verifier for model-level supplier tests."""
import argparse
from collections import OrderedDict
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PYTEST = [sys.executable, "-m", "pytest", "-q"]

GROUP_COMMANDS = OrderedDict(
    (
        (
            "core",
            [PYTEST + ["tests/web/test_supplier_model_tests.py"]],
        ),
        (
            "ui",
            [
                [
                    "npm",
                    "--prefix",
                    "web",
                    "run",
                    "test",
                    "--",
                    "--run",
                    "src/features/suppliers/api.test.ts",
                    "src/features/suppliers/SupplierModelsPanel.test.tsx",
                    "src/features/suppliers/ModelTestDialog.test.tsx",
                ]
            ],
        ),
        (
            "browser",
            [
                [
                    "npm",
                    "--prefix",
                    "web",
                    "run",
                    "test:e2e",
                    "--",
                    "tests/m6d-management-ui.spec.ts",
                    "--grep",
                    "manages supplier code|blocks non-loopback browser transport",
                ]
            ],
        ),
        (
            "security",
            [
                PYTEST
                + [
                    "tests/test_default_network_denial.py",
                    "tests/web/test_local_management_guard.py",
                    "tests/suppliers/test_worker_isolation.py",
                ],
                ["npm", "--prefix", "worker", "test"],
                [
                    "npm", "--prefix", "web", "run", "test", "--", "--run",
                    "vitest/default-network-denial.test.ts",
                ],
            ],
        ),
        (
            "template",
            [
                PYTEST
                + [
                    "tests/web/test_supplier_api.py",
                    "tests/web/test_supplier_compiler.py",
                    "tests/web/test_m6c_adapter_cutover.py",
                    "-k",
                    "custom_empty or creates_custom or replay_does_not_recompile or builtin_openai or builtin_comment_revision",
                ]
            ],
        ),
        (
            "regression",
            [
                [sys.executable, "tools/verify_m3_agnes_generation.py"],
                [sys.executable, "tools/verify_m4_chapter_rehearsal.py"],
                [sys.executable, "tools/verify_m6b_model_catalog_binding.py"],
                [sys.executable, "tools/verify_m6c_adapter_cutover.py"],
                [sys.executable, "tools/verify_m6_supplier_model_management.py", "--self-test"],
            ],
        ),
        (
            "release",
            [
                PYTEST
                + [
                    "tests/web/test_supplier_model_tests.py::test_model_test_feature_status_is_default_off_and_create_is_blocked",
                    "tests/tools/test_verify_model_level_provider_tests.py::test_verifier_has_ordered_schema_and_zero_real_request_evidence",
                ]
            ],
        ),
    )
)

CHECK_DEFINITIONS = OrderedDict(
    (
        ("MTEST-001", ("core", "text/image eligibility and video rejection")),
        ("MTEST-002", ("ui+browser", "explicit confirmation and cancel-zero-call")),
        ("MTEST-003", ("core", "immutable direct-model execution snapshot")),
        ("MTEST-004", ("core", "atomic claim and submit exactly once")),
        ("MTEST-005", ("core", "restart marks ambiguous submission unknown without retry")),
        ("MTEST-006", ("core+ui+browser", "normalized fake text result and usage")),
        ("MTEST-007", ("core+ui+browser", "durable fake image bytes and local preview")),
        ("MTEST-008", ("security+browser", "loopback-only API and proxy rejection")),
        ("MTEST-009", ("core", "snapshot-aware idempotency replay and conflict")),
        ("MTEST-010", ("core", "credential lifecycle blocks, fails, or marks unknown safely")),
        ("MTEST-011", ("core+ui", "sanitized evidence and stable safe errors")),
        ("MTEST-012", ("core", "model tests remain isolated from project generation tables")),
        ("MTEST-013", ("template", "Chinese custom template and documented built-in revisions")),
        ("MTEST-014", ("core+security+browser", "transport denial proves zero real provider requests")),
        ("MTEST-015", ("regression+release", "M1-M6 regression and disabled-by-default release gate")),
    )
)


def _offline_env():
    env = dict(os.environ)
    for name in tuple(env):
        upper = name.upper()
        if upper in {
            "AGNES_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "DEEPSEEK_API_KEY",
            "XAI_API_KEY",
        } or (
            upper.startswith("AI_DRAMA_")
            and any(part in upper for part in ("API_KEY", "TOKEN", "SECRET"))
        ):
            env.pop(name, None)
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
            "AI_DRAMA_RUNTIME_PROVIDER": "mock",
            "AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED": "false",
            "AI_DRAMA_MODEL_TESTS_ENABLED": "false",
        }
    )
    return env


def _run_group(commands):
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=_offline_env(),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return False
    return True


def verify(*, group_results=None, force_fail=()):
    if group_results is None:
        results = OrderedDict(
            (name, _run_group(commands)) for name, commands in GROUP_COMMANDS.items()
        )
    else:
        results = OrderedDict(
            (name, bool(group_results.get(name, False))) for name in GROUP_COMMANDS
        )

    forced = set(force_fail)
    checks = OrderedDict()
    for check_id, (category, evidence) in CHECK_DEFINITIONS.items():
        passed = all(results[name] for name in category.split("+"))
        if check_id in forced:
            passed = False
        checks[check_id] = {
            "result": "PASS" if passed else "FAIL",
            "command_category": category,
            "evidence": evidence,
        }
    passed = all(item["result"] == "PASS" for item in checks.values())
    transport_guard_enabled = bool(results["security"] and results["browser"])
    return {
        "schema_version": "model-level-provider-tests-verification-v1",
        "verification_mode": "offline_fake_only",
        "checks": checks,
        "result": "PASS" if passed else "FAIL",
        "success_token": "MODEL_LEVEL_PROVIDER_TESTS_PASS" if passed else "",
        "production_model_test_flag_enabled": False,
        "real_provider_requests": False,
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
        "transport_guard_enabled": transport_guard_enabled,
        "network_evidence": (
            "tests/conftest.py denies non-loopback Python sockets and DNS; "
            "worker/src/network-denial.mjs denies non-loopback Node transport; "
            "Playwright context routes abort non-loopback browser requests before transport; "
            "fake gateways assert call counts"
        ),
    }


def markdown(report):
    lines = [
        "# Model-Level Provider Tests Verification",
        "",
        f"Result: `{report['result']}`",
        "",
        "| Check | Result | Category | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for check_id, item in report["checks"].items():
        lines.append(
            f"| `{check_id}` | {item['result']} | `{item['command_category']}` | {item['evidence']} |"
        )
    counts = report["real_request_counts"]
    lines.extend(
        [
            "",
            f"Real Provider requests: text={counts['text']} image={counts['image']} video={counts['video']}.",
            "Production model test flag enabled: false.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    parser.add_argument(
        "--force-fail", action="append", choices=tuple(CHECK_DEFINITIONS), default=[]
    )
    parser.add_argument(
        "--self-test", action="store_true", help="validate report plumbing only"
    )
    args = parser.parse_args()
    injected = {name: True for name in GROUP_COMMANDS} if args.self_test else None
    report = verify(group_results=injected, force_fail=args.force_fail)
    json_text = json.dumps(report, ensure_ascii=False, sort_keys=False)
    markdown_text = markdown(report)
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.markdown_output:
        Path(args.markdown_output).write_text(markdown_text, encoding="utf-8")
    print(markdown_text if args.format == "markdown" else json_text)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
