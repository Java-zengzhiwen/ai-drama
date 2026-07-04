# Storyboard Workflow Complete Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable storyboard verification harness, acceptance tests, and CI entrypoint that prove the main-branch Storyboard Workflow MVP is technically sound.

**Architecture:** Keep the verification script thin and data driven. Put assertions in pytest acceptance tests so the script can invoke them and summarize the results. Use temporary directories for SQLite and exports so each run is isolated, deterministic, and safe to repeat.

**Tech Stack:** Python, pytest, SQLite, GitHub Actions, subprocess, JSON/Markdown reporting.

---

### Task 1: Add the acceptance test harness

**Files:**
- Create: `tests/acceptance/test_storyboard_workflow_acceptance.py`
- Modify: `tests/test_storyboard_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_storyboard_verification_entrypoint_exists():
    from pathlib import Path

    assert Path("tools/verify_storyboard_workflow.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/acceptance/test_storyboard_workflow_acceptance.py -v`
Expected: FAIL because the file or module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create the acceptance test module and shared helpers that exercise temporary repositories, temporary SQLite databases, and the existing runtime service.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/acceptance/test_storyboard_workflow_acceptance.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/acceptance/test_storyboard_workflow_acceptance.py tests/test_storyboard_workflow.py
git commit -m "test: add storyboard verification acceptance coverage"
```

### Task 2: Add the standalone verification script

**Files:**
- Create: `tools/verify_storyboard_workflow.py`
- Modify: `pyproject.toml` if needed for executable packaging

- [ ] **Step 1: Write the failing test**

```python
def test_verify_storyboard_workflow_script_runs():
    import subprocess, sys
    result = subprocess.run([sys.executable, "tools/verify_storyboard_workflow.py"], capture_output=True, text=True)
    assert result.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/acceptance/test_storyboard_workflow_acceptance.py::test_verify_storyboard_workflow_script_runs -v`
Expected: FAIL because the script is missing.

- [ ] **Step 3: Write minimal implementation**

Implement the script so it executes the verification suite, writes Markdown and JSON reports, and exits non-zero on failure.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/acceptance/test_storyboard_workflow_acceptance.py::test_verify_storyboard_workflow_script_runs -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/verify_storyboard_workflow.py
git commit -m "feat: add storyboard verification entrypoint"
```

### Task 3: Add CI wiring and documentation

**Files:**
- Create: `.github/workflows/storyboard-workflow-verification.yml`
- Create: `docs/testing/storyboard-workflow-complete-verification.md`

- [ ] **Step 1: Write the failing test**

```python
def test_github_workflow_exists():
    from pathlib import Path

    assert Path(".github/workflows/storyboard-workflow-verification.yml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/acceptance/test_storyboard_workflow_acceptance.py::test_github_workflow_exists -v`
Expected: FAIL until the workflow file exists.

- [ ] **Step 3: Write minimal implementation**

Add a CI workflow that runs the same migration, compile, pytest, and standalone verification commands.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/acceptance/test_storyboard_workflow_acceptance.py::test_github_workflow_exists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/storyboard-workflow-verification.yml docs/testing/storyboard-workflow-complete-verification.md
git commit -m "docs: add storyboard verification workflow"
```

## Coverage Check

- Skill package checks: planned in acceptance tests and script summary.
- CLI gates: planned in acceptance tests.
- Runtime flow: planned in acceptance tests.
- Validators: planned in acceptance tests.
- Source coverage and provenance: planned in acceptance tests.
- Database compatibility: planned in acceptance tests.
- CI: planned in workflow file.
