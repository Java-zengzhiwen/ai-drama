#!/usr/bin/env python3
"""Offline verifier for the AIXORA adapter and archive-delete contract."""
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
            "archive",
            [
                PYTEST
                + [
                    "tests/web/test_model_catalog.py",
                    "tests/web/test_model_api.py",
                    "tests/web/test_execution_snapshot.py",
                    "-k",
                    "delete or archive or archived",
                ]
            ],
        ),
        (
            "adapter",
            [PYTEST + ["tests/web/test_aixora_adapter.py", "tests/web/test_supplier_compiler.py"]],
        ),
        ("worker", [["npm", "--prefix", "worker", "test"]]),
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
                    "src/features/suppliers/SupplierModelsPanel.test.tsx",
                ]
            ],
        ),
        (
            "security",
            [
                PYTEST
                + [
                    "tests/test_default_network_denial.py",
                    "tests/suppliers/test_worker_isolation.py",
                    "tests/web/test_local_management_guard.py",
                ]
            ],
        ),
        (
            "migration",
            [
                PYTEST + ["tests/migration/test_m6e_migration_matrix.py", "-k", "archive"],
                [sys.executable, "migration/tools/verify_migration.py"],
            ],
        ),
        (
            "regression",
            [
                [sys.executable, "tools/verify_model_level_provider_tests.py", "--self-test"],
                [sys.executable, "tools/verify_m6_supplier_model_management.py", "--self-test"],
            ],
        ),
    )
)

CHECK_DEFINITIONS = OrderedDict(
    (
        ("AIXORA-001", ("adapter", "exact four text models and GPT Image 2 manifest")),
        ("AIXORA-002", ("adapter", "Responses output, usage, and reasoning effort normalization")),
        (
            "AIXORA-003",
            (
                "adapter+worker",
                "offline URL/base64 normalization, image magic validation, and bounded local media persistence",
            ),
        ),
        (
            "AIXORA-004",
            (
                "adapter+worker",
                "offline ordered edit inputs plus Worker pre-network multipart assembly and aggregate limits",
            ),
        ),
        (
            "AIXORA-005",
            (
                "worker+security",
                "trusted-local adapter API isolation, helper v1 compatibility, helper v2 media limits, redirect and peer checks",
            ),
        ),
        ("AIXORA-006", ("archive", "physical delete, history archive, and active binding block")),
        ("AIXORA-007", ("archive+ui", "archived identities hidden from catalogs and selections")),
        ("AIXORA-008", ("archive+migration", "immutable history and replay-safe additive migration")),
        ("AIXORA-009", ("security", "loopback management and default transport denial")),
        ("AIXORA-010", ("regression+security", "M6 governance gates and zero real provider calls")),
    )
)


def offline_env():
    env = dict(os.environ)
    for name in tuple(env):
        upper = name.upper()
        if (
            upper.endswith("API_KEY")
            or upper.endswith("_TOKEN")
            or upper.endswith("_SECRET")
            or "AIXORA" in upper
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


def run_group(commands):
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=offline_env(),
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return False
    return True


def verify(*, group_results=None, force_fail=()):
    if group_results is None:
        results = OrderedDict(
            (name, run_group(commands)) for name, commands in GROUP_COMMANDS.items()
        )
    else:
        results = OrderedDict(
            (name, bool(group_results.get(name, False))) for name in GROUP_COMMANDS
        )
    forced = set(force_fail)
    checks = OrderedDict()
    for check_id, (categories, evidence) in CHECK_DEFINITIONS.items():
        passed = all(results[name] for name in categories.split("+"))
        if check_id in forced:
            passed = False
        checks[check_id] = {
            "result": "PASS" if passed else "FAIL",
            "command_category": categories,
            "evidence": evidence,
        }
    passed = all(item["result"] == "PASS" for item in checks.values())
    return {
        "schema_version": "aixora-adapter-model-archive-verification-v1",
        "verification_mode": "offline_fake_only",
        "checks": checks,
        "result": "PASS" if passed else "FAIL",
        "success_token": "AIXORA_MODEL_ARCHIVE_PASS" if passed else "",
        "production_m6_execution_flag_enabled": False,
        "real_provider_requests": False,
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
        "transport_guard_enabled": bool(results["security"] and results["worker"]),
    }


def markdown(report):
    lines = [
        "# AIXORA Adapter And Model Archive Verification",
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
    lines.extend(
        [
            "",
            "Automated real Provider requests: text=0 image=0 video=0.",
            "Production M6 execution flag enabled: false.",
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
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    injected = {name: True for name in GROUP_COMMANDS} if args.self_test else None
    report = verify(group_results=injected, force_fail=args.force_fail)
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.markdown_output:
        Path(args.markdown_output).write_text(markdown(report), encoding="utf-8")
    print(markdown(report) if args.format == "markdown" else json.dumps(report, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
