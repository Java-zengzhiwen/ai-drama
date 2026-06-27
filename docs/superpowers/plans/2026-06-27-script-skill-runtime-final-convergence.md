# Script Skill Runtime Final Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Close the last approved Script Skill Runtime MVP specification gaps without rebuilding stable Registry, Store, CLI, or artifact flows.

**Architecture:** Add a normalized `RuntimeRequest` as the single source for adapter input, persisted snapshots, and request hashes. Keep the current markdown-only execution path but make `markdown-script-mvp-v1` explicit, register every migrated validator with profile applicability, persist usage/errors/input diffs, harden approval ordering, and close resources explicitly.

**Tech Stack:** Python stdlib, SQLite, argparse, PyYAML, pytest, optional OpenAI SDK.

---

### Task 1: Normalized Runtime Request And Execution Profile

**Files:**
- Create: `ai_drama_runtime/request.py`
- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_runtime/runtime.py`
- Modify: `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/skill.json`
- Test: `tests/test_runtime_request.py`

- [x] Write failing tests proving instructions/context/input files enter one normalized request, `approved-script.md` and API keys do not, request hash is stable, and context/input changes alter the hash.
- [x] Build `RuntimeRequest` from manifest-declared active files and acceptance inputs.
- [x] Make adapters consume only `RuntimeRequest` fields, not hidden prompt concatenation.
- [x] Add `execution_profile=markdown-script-mvp-v1` metadata and unsupported bundle artifact reporting.
- [x] Run focused tests and commit.

### Task 2: Validator Inventory And Matrix

**Files:**
- Modify: `ai_drama_runtime/manifest.py`
- Modify: `ai_drama_runtime/validators.py`
- Modify: `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/skill.json`
- Create: `docs/runtime-validator-matrix.md`
- Test: `tests/test_validator_inventory.py`

- [x] Write failing tests proving all migrated validator files except `common.py` are registered, bundle validators return `NOT_APPLICABLE`, applicable validators run, and missing dependencies are distinct.
- [x] Extend validator metadata with origin, required artifacts, current profile status, and reason.
- [x] Make approval rules apply only to required applicable validators.
- [x] Document the matrix.
- [x] Run focused tests and commit.

### Task 3: Usage, Error Codes, Compare Input Diffs

**Files:**
- Modify: `ai_drama_runtime/runtime.py`
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_runtime/cli.py`
- Test: `tests/test_usage_errors_compare.py`

- [x] Write failing tests for usage persistence, missing key/model/timeout/provider/empty/parse error codes, and compare input/request hash diffs.
- [x] Persist usage fields and provider raw usage.
- [x] Preserve stable adapter error codes.
- [x] Add input reference/hash/request hash diff to compare.
- [x] Run focused tests and commit.

### Task 4: Approval Ordering And Resource Lifecycle

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_runtime/cli.py`
- Test: `tests/test_approval_ordering_resources.py`

- [x] Write failing tests for same-second approve/reject order, restart ordering, sidecar latest approval, CLI store closure, `{python}` validator substitution, and deterministic timeout.
- [x] Add monotonic approval sequence and microsecond UTC timestamps.
- [x] Ensure CLI closes stores and validator executor uses `sys.executable`.
- [x] Run focused tests and commit.

### Task 5: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/runtime-mvp.md`
- Modify: `.env.example`
- Test: full verification commands

- [x] Update docs for markdown profile, request snapshot, validator matrix, usage/errors, approval ordering, compare/export, config precedence, tests, and limits.
- [x] Run fresh venv full command matrix.
- [x] Run independent spec review, then code quality review.
- [x] Run final verification matrix and commit docs/fixes.
