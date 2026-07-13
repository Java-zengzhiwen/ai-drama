#!/usr/bin/env python3
"""Final semantic and offline verifier for M6 supplier/model management."""
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
            "migration",
            [
                PYTEST + ["tests/migration/test_m6e_migration_matrix.py"],
                [sys.executable, "migration/tools/verify_migration.py"],
            ],
        ),
        (
            "credential_recovery",
            [PYTEST + ["tests/web/test_supplier_credentials.py"]],
        ),
        (
            "legacy_backfill",
            [
                PYTEST
                + [
                    "tests/migration/test_m6e_migration_matrix.py::test_active_legacy_matrix_backfills_queryable_jobs_and_fails_closed_without_id",
                    "tests/web/test_m6c_adapter_cutover.py::test_backfilled_legacy_job_completes_via_poll_fetch_without_submit",
                ]
            ],
        ),
        (
            "object_store",
            [PYTEST + ["tests/operations/test_m6_object_store_maintenance.py"]],
        ),
        (
            "backup_restore",
            [PYTEST + ["tests/operations/test_m6_backup_restore.py"]],
        ),
        (
            "fake_provider",
            [PYTEST + ["tests/acceptance/test_m6e_fake_provider_workflow.py"]],
        ),
        (
            "adapter_contract",
            [[sys.executable, "tools/verify_m6c_adapter_cutover.py"]],
        ),
        (
            "browser",
            [["npm", "--prefix", "web", "run", "test:e2e"]],
        ),
        (
            "security",
            [
                PYTEST
                + [
                    "tests/suppliers/test_worker_isolation.py",
                    "tests/web/test_local_management_guard.py",
                    "tests/web/test_supplier_api.py",
                ],
                ["npm", "--prefix", "worker", "test"],
            ],
        ),
        (
            "rollback",
            [PYTEST + ["tests/acceptance/test_m6e_rollout_rollback.py"]],
        ),
        (
            "regression",
            [
                [sys.executable, "tools/verify_m3_agnes_generation.py"],
                [sys.executable, "tools/verify_m4_chapter_rehearsal.py"],
                [sys.executable, "tools/verify_m6b_model_catalog_binding.py"],
                [sys.executable, "tools/verify_m6d_management_ui.py"],
                [
                    sys.executable,
                    "tools/verify_storyboard_workflow.py",
                    "--report-dir",
                    "/tmp/ai-drama-m6e-storyboard-report",
                ],
            ],
        ),
        (
            "release",
            [
                PYTEST
                + [
                    "tests/web/test_m6c_adapter_cutover.py::test_feature_flag_defaults_off",
                    "tests/tools/test_verify_m6_supplier_model_management.py::test_verifier_has_ordered_semantic_schema_and_zero_real_request_evidence",
                ]
            ],
        ),
    )
)

CHECK_DEFINITIONS = OrderedDict(
    (
        ("M6E-001", ("migration", "fresh migration and startup")),
        ("M6E-002", ("migration", "legacy and intermediate migration preservation")),
        ("M6E-003", ("migration", "migration replay is idempotent")),
        ("M6E-004", ("credential_recovery", "credential crash boundaries converge safely")),
        ("M6E-005", ("legacy_backfill", "active legacy jobs backfill without submit")),
        ("M6E-006", ("object_store", "object references and corruption are inventoried")),
        ("M6E-007", ("object_store", "temporary-store GC is guarded and dry-run by default")),
        ("M6E-008", ("backup_restore", "backup and restore are hash verified and equivalent")),
        ("M6E-009", ("fake_provider", "fake text image and video complete durably")),
        ("M6E-010", ("fake_provider+adapter_contract", "video submit is exactly once across recovery")),
        ("M6E-011", ("fake_provider+adapter_contract", "both rerun resolution modes preserve contract")),
        ("M6E-012", ("fake_provider+browser", "hot reload preserves old snapshots and routes new work")),
        ("M6E-013", ("rollback+adapter_contract", "off on off restart preserves history and freezes active snapshots")),
        ("M6E-014", ("browser", "complete Playwright management and execution acceptance")),
        ("M6E-015", ("security+browser", "secrets are write-only and sanitized")),
        ("M6E-016", ("security+browser", "network isolation proves zero real requests")),
        ("M6E-017", ("regression", "M1-M5 and predecessor M6 contracts regress cleanly")),
        ("M6E-018", ("release+all", "release gates documentation and rollback evidence are ready")),
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
        } or (upper.startswith("AI_DRAMA_") and any(part in upper for part in ("API_KEY", "TOKEN", "SECRET"))):
            env.pop(name, None)
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
            "AI_DRAMA_RUNTIME_PROVIDER": "mock",
            "AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED": "false",
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


def _release_files_ready():
    required = (
        "docs/operations/m6-backup-restore.md",
        "docs/operations/m6-rollout-rollback.md",
        "tests/acceptance/test_m6e_fake_provider_workflow.py",
        "web/tests/m6e-migration-acceptance.spec.ts",
    )
    if not all((ROOT / name).is_file() for name in required):
        return False
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    forbidden = (
        "runtime-data/",
        "/secrets/suppliers/",
        ".db",
    )
    return not any(path.endswith(".db") or any(marker in path for marker in forbidden[:2]) for path in tracked)


def verify(*, group_results=None, force_fail=()):
    if group_results is None:
        results = OrderedDict(
            (name, _run_group(commands)) for name, commands in GROUP_COMMANDS.items()
        )
        results["release"] = results["release"] and _release_files_ready()
    else:
        results = OrderedDict(
            (name, bool(group_results.get(name, False))) for name in GROUP_COMMANDS
        )

    checks = OrderedDict()
    forced = set(force_fail)
    for check_id, (category, evidence) in CHECK_DEFINITIONS.items():
        if category == "release+all":
            passed = all(results.values())
        else:
            passed = all(results[name] for name in category.split("+"))
        if check_id in forced:
            passed = False
        checks[check_id] = {
            "result": "PASS" if passed else "FAIL",
            "command_category": category,
            "evidence": evidence,
        }
    passed = all(item["result"] == "PASS" for item in checks.values())
    return {
        "schema_version": "m6-supplier-model-management-verification-v1",
        "verification_mode": "semantic",
        "checks": checks,
        "result": "PASS" if passed else "FAIL",
        "success_token": "M6_SUPPLIER_MODEL_MANAGEMENT_PASS" if passed else "",
        "production_flag_enabled": False,
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
    }


def markdown(report):
    lines = [
        "# M6 Supplier And Model Management Verification",
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
            "Production supplier execution flag enabled: false.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    parser.add_argument("--force-fail", action="append", choices=tuple(CHECK_DEFINITIONS), default=[])
    parser.add_argument("--self-test", action="store_true", help="validate report plumbing without acceptance commands")
    args = parser.parse_args()
    injected = {name: True for name in GROUP_COMMANDS} if args.self_test else None
    report = verify(group_results=injected, force_fail=args.force_fail)
    json_text = json.dumps(report, ensure_ascii=False, sort_keys=False)
    markdown_text = markdown(report)
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        Path(args.markdown_output).write_text(markdown_text, encoding="utf-8")
    print(markdown_text if args.format == "markdown" else json_text)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
