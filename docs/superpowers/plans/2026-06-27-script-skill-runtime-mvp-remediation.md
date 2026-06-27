# Script Skill Runtime MVP Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the current Script Skill Runtime MVP so it satisfies the approved remediation spec without adding a service layer or downstream product scope.

**Architecture:** Keep the runtime local and CLI-first. Tighten trust boundaries in the manifest loader, add a small local registry, persist run/input/revision/validator/approval/export provenance in SQLite plus immutable content objects, and keep model adapters as one-shot calls.

**Tech Stack:** Python stdlib, SQLite, argparse, PyYAML, pytest, optional OpenAI SDK for credentialed smoke only.

---

### Task 1: Manifest And Registry

**Files:**
- Modify: `ai_drama_runtime/manifest.py`
- Create: `ai_drama_runtime/registry.py`
- Modify: `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/skill.json`
- Create: `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/script_revision_structure.py`
- Test: `tests/test_manifest.py`

- [ ] Write failing tests for required manifest fields, invalid types, absolute paths, `..`, symlink escape, duplicate `skill_id+version`, invalid package isolation, registry list/show/get/validate, and declared-only package hashes.
- [ ] Implement root-confined path resolution and manifest contract validation.
- [ ] Implement local registry with duplicate/invalid/not-found errors.
- [ ] Move runtime structure validator into a package-contained wrapper.
- [ ] Run focused tests and commit.

### Task 2: Input Snapshots, Run Lifecycle, Parser

**Files:**
- Modify: `ai_drama_runtime/acceptance.py`
- Modify: `ai_drama_runtime/runtime.py`
- Create: `ai_drama_runtime/parser.py`
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Test: `tests/test_runtime_lifecycle.py`

- [ ] Write failing tests for per-input hashes/snapshots, acceptance path and symlink escape, reference-output isolation, runtime failure, empty response, parse failure, persisted failed runs, uppercase run states (`RUNNING`, `SUCCEEDED`, `RUNTIME_FAILED`, `PARSE_FAILED`, `VALIDATION_FAILED`), error fields, revision supersedes chain, and no revision on failure.
- [ ] Create runs before runtime calls and update final status.
- [ ] Persist input snapshots and normalized request snapshots.
- [ ] Add parser version and explicit parse failure handling.
- [ ] Run focused tests and commit.

### Task 3: Validators, Approval, Compare, Export

**Files:**
- Modify: `ai_drama_runtime/validators.py`
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Test: `tests/test_validators_approval_export.py`

- [ ] Write failing tests for PASS, FAIL, SKIPPED_DEPENDENCY_MISSING, NOT_APPLICABLE, timeout, crash, stdout/stderr persistence, required blocking for every non-PASS required status, approval transactions, one current approved revision per artifact, reject records, metadata compare, no overwrite export, force export, and provenance sidecar.
- [ ] Implement validator statuses and dependency/applicability checks.
- [ ] Tighten approval preconditions and same-transaction approval records.
- [ ] Add metadata-aware compare and export sidecar.
- [ ] Run focused tests and commit.

### Task 4: CLI, Docs, Fresh Venv

**Files:**
- Modify: `ai_drama_runtime/cli.py`
- Modify: `README.md`
- Modify: `docs/runtime-mvp.md`
- Create: `.env.example`
- Test: `tests/test_cli.py`

- [ ] Write failing tests for required command shape, exit codes, restart-safe reads, API config precedence (`AI_DRAMA_API_KEY` before `OPENAI_API_KEY`, `AI_DRAMA_BASE_URL` before `OPENAI_BASE_URL`, CLI model before `AI_DRAMA_MODEL`), and credential redaction.
- [ ] Implement `--data-root`, `--skills-root`, `skill-id@version`, nested command groups, and stable exit codes.
- [ ] Document actual MVP scope, install, dependencies, config precedence, command matrix, exit codes, validator statuses, and limits.
- [ ] Verify fresh venv install, full tests with clean exit, CLI skills list, mock flow, migration verification, py_compile, diff check, forbidden scope search, and unchanged migrated business files / acceptance files / SOURCE_ROOT.
- [ ] Run final review and commit.
