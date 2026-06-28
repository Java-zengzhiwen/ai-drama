# Storyboard Workflow MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a validated Storyboard Workflow MVP that accepts an approved script revision, enforces strict upstream gates, runs storyboard validators, preserves provenance, and exports fresh storyboard revisions.

**Architecture:** Extend the existing local runtime with a second artifact type (`storyboard`) that reuses the same store, approval, export, and compare machinery. The storyboard path must gate on an approved source script revision, capture inherited context snapshots, persist gate failures, and keep source approval provenance immutable even if later approvals change.

**Tech Stack:** Python 3.9+, SQLite, JSON, Markdown, pytest.

---

### Task 1: Lock Storyboard input gates

**Files:**
- Modify: `ai_drama_runtime/cli.py`
- Modify: `ai_drama_runtime/services.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cli_rejects_skill_input_type_mismatch(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_cli.py::test_cli_rejects_skill_input_type_mismatch`
Expected: FAIL before the gate logic is implemented.

- [ ] **Step 3: Write minimal implementation**

```python
mode = p.add_mutually_exclusive_group(required=True)
mode.add_argument("--input")
mode.add_argument("--source-revision")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_cli.py::test_cli_rejects_skill_input_type_mismatch`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_runtime/cli.py ai_drama_runtime/services.py tests/test_cli.py
git commit -m "fix: enforce storyboard input modes"
```

### Task 2: Persist Storyboard gate failures

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Test: `tests/test_storyboard_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_storyboard_request_requires_all_inherited_context(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_storyboard_workflow.py::test_storyboard_request_requires_all_inherited_context`
Expected: FAIL before gate persistence is added.

- [ ] **Step 3: Write minimal implementation**

```python
store.insert_workflow_gate_record(...)
raise WorkflowGateError("SOURCE_CONTEXT_MISSING", ...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_storyboard_workflow.py::test_storyboard_request_requires_all_inherited_context`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/services.py tests/test_storyboard_workflow.py
git commit -m "fix: persist storyboard gate failures"
```

### Task 3: Preserve storyboard provenance

**Files:**
- Modify: `ai_drama_runtime/request.py`
- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_storyboard_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_storyboard_run_uses_current_approved_script_and_becomes_stale_when_script_changes(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_storyboard_workflow.py::test_storyboard_run_uses_current_approved_script_and_becomes_stale_when_script_changes`
Expected: FAIL before captured provenance is fixed.

- [ ] **Step 3: Write minimal implementation**

```python
approval = store.latest_approval(source_revision.revision_id)
"source_script_approval_record_id": approval.record_id if approval else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_storyboard_workflow.py::test_storyboard_run_uses_current_approved_script_and_becomes_stale_when_script_changes`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_runtime/request.py ai_drama_runtime/services.py ai_drama_runtime/store.py tests/test_storyboard_workflow.py
git commit -m "fix: preserve storyboard provenance"
```

### Task 4: Complete Storyboard contract and validators

**Files:**
- Modify: `skills/ai-drama-storyboard-design-skill/v0.1.0/SKILL.md`
- Modify: `skills/ai-drama-storyboard-design-skill/v0.1.0/contracts/*.md`
- Modify: `skills/ai-drama-storyboard-design-skill/v0.1.0/schemas/*.json`
- Modify: `skills/ai-drama-storyboard-design-skill/v0.1.0/templates/*.md`
- Modify: `skills/ai-drama-storyboard-design-skill/v0.1.0/templates/*.json`
- Modify: `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/*.py`
- Test: `tests/test_storyboard_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_storyboard_validators_execute_and_persist_outputs(tmp_path):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_storyboard_workflow.py::test_storyboard_validators_execute_and_persist_outputs`
Expected: FAIL before the contract and parser are aligned.

- [ ] **Step 3: Write minimal implementation**

```markdown
scene_id
shot_id
shot_order
source_scene_reference
duration_seconds
shot_size
camera_angle
camera_movement
visual_composition
character_positions
character_actions
emotion_performance
dialogue
sound_notes
continuity_in
continuity_out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_storyboard_workflow.py::test_storyboard_validators_execute_and_persist_outputs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-drama-storyboard-design-skill/v0.1.0 tests/test_storyboard_workflow.py
git commit -m "feat: complete storyboard contract and validators"
```

### Task 5: Final verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/runtime-mvp.md`
- Modify: `docs/项目完整开发路径与当前状态.md`
- Modify: `docs/storyboard/storyboard-workflow-mvp.md`
- Modify: `docs/storyboard/storyboard-validator-matrix.md`
- Modify: `docs/storyboard/storyboard-cli-guide.md`
- Modify: `docs/superpowers/plans/2026-06-28-storyboard-workflow-mvp.md`

- [ ] **Step 1: Run full verification**

Run:
`python3 migration/tools/verify_migration.py`
`PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q`

- [ ] **Step 2: Verify outputs**

Expected: zero failures, working tree clean after commit.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/runtime-mvp.md docs/项目完整开发路径与当前状态.md docs/storyboard docs/superpowers/plans/2026-06-28-storyboard-workflow-mvp.md
git commit -m "docs: complete storyboard workflow documentation"
```

## Self-review

- Spec coverage: input gates, gate persistence, provenance, contract/schema, validators, and docs all have explicit tasks.
- Placeholder scan: no TBD/TODO placeholders remain in the actionable steps.
- Type consistency: `source_revision_id`, `storyboard_revision`, and `storyboard_approved` are used consistently across tasks.
