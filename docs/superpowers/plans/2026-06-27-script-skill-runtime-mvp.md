# Script Skill Runtime MVP Plan

## Goal

Deliver a local, single-user, CLI-first runtime for the migrated AI drama script adaptation skill. The MVP must discover the active skill package, validate a requested version, run against the Shengsi Chapter 001 acceptance corpus without leaking the approved reference script into the model prompt, persist immutable runs and script revisions, execute declared validators, support revision comparison, enforce one current approved revision per artifact, survive process restarts, and export the approved script.

## Constraints

- Do not modify `/Users/zengzhiwen/AI-manju/ai-drama-script-agent-lab`.
- Do not change migrated skill business prompt, contract semantics, or validator business logic.
- Do not edit acceptance corpus text.
- Do not send `approved-script.md` to any model prompt; it is reference-only.
- Do not add web UI, API service, agent runtime, workflow engine, registry service, database server, queues, vector database, LangChain, LangGraph, CrewAI, LibTV, Agnes, or Jianying integrations.
- Keep implementation Python stdlib-first, with optional PyYAML/jsonschema/openai only where useful.

## Architecture

- `ai_drama_runtime/manifest.py`: load and validate local skill metadata, versions, hashes, and declared validators.
- `ai_drama_runtime/acceptance.py`: load acceptance corpus, validate manifest references, snapshot input files, and exclude reference outputs from runtime requests.
- `ai_drama_runtime/runtime.py`: provide deterministic `mock` runtime and optional OpenAI-compatible runtime.
- `ai_drama_runtime/store.py`: SQLite schema plus immutable content-addressed files for run requests, run responses, script revisions, validation results, approval records, and exports.
- `ai_drama_runtime/validators.py`: execute manifest-declared local validator commands, capture output, status, and blocking flags.
- `ai_drama_runtime/services.py`: orchestrate runs, comparisons, approvals, rejection, export, and restart-safe reads.
- `ai_drama_runtime/cli.py`: argparse CLI for discovery, validation, run, validators, compare, approve/reject, current approved, export, and status.

## TDD Checklist

1. Write tests for acceptance manifest validation and reference-output exclusion.
2. Write tests for skill discovery and version validation.
3. Write tests for immutable run/revision persistence and restart reads.
4. Write tests for validator pass/fail/skip persistence and approval blocking.
5. Write tests for one-current-approved-revision enforcement, reject records, compare output, and export.
6. Write tests for CLI smoke paths using the mock runtime.
7. Run tests once before implementation to confirm expected RED failures.
8. Implement the smallest code needed to pass.
9. Run focused tests, then full verification.

## Commit Plan

1. Commit acceptance corpus on `main` if it is not already committed.
2. Create `feat/script-skill-runtime-mvp`.
3. Commit this plan.
4. Commit runtime implementation, tests, docs, and skill metadata.
5. Run final verification before completion; do not push.

## Verification Plan

- `python3 migration/tools/verify_migration.py`
- `python3 -m py_compile migration/tools/verify_migration.py skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/*.py ai_drama_runtime/*.py`
- `python3 -m pytest`
- CLI smoke with `mock` runtime against `acceptance/shengsi-chapter-001`
- Restart-safe read using a second CLI process and same SQLite DB
- `git diff --check`
- Scope checks for forbidden runtime families and `SOURCE_ROOT` mutation
