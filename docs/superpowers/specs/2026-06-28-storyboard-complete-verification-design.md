# Storyboard Workflow Complete Verification Design

**Goal:** Install a reproducible verification layer for the main-branch Storyboard Workflow MVP and use it to produce auditable evidence for release gating.

**Architecture:** The verification layer has one shared execution entrypoint that drives the same checks locally and in CI. Pytest acceptance tests cover the workflow gates, validator execution, provenance, staleness, and database compatibility against temporary databases and temporary export roots. A standalone script orchestrates the full run, collects machine-readable outputs, and writes Markdown and JSON reports.

**Tech Stack:** Python, pytest, SQLite, GitHub Actions, local filesystem temp directories, existing `ai_drama_runtime` services and skill packages.

---

## Design Principles

- Verification must be isolated from production data.
- The same entrypoint must work on a developer laptop and in GitHub Actions.
- Tests must assert observed runtime behavior, not reimplement business logic.
- Report output must be derived from executed commands and stored artifacts.
- No real-model smoke test may run automatically.

## Verification Layers

### Layer 1: Static and baseline checks

- `python3 migration/tools/verify_migration.py`
- `python3 -m py_compile ...`
- `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q`

These checks confirm the repo remains structurally valid before the workflow-specific verification runs.

### Layer 2: Skill package verification

- Skill discovery for the Script and Storyboard packages
- Storyboard package version and profile checks
- Validator inventory checks
- Package hash stability and path escape rejection

### Layer 3: CLI gate verification

- Required input mode enforcement
- Invalid source revision and context errors
- Workflow gate persistence and restart visibility

### Layer 4: End-to-end runtime flow

- Script run
- Script approval
- Storyboard run
- Storyboard validation
- Storyboard approval
- Export with provenance

### Layer 5: Validator behavior

- Required validators execute
- `NOT_APPLICABLE` is blocked from approval when required
- Negative storyboard text fixtures trigger predictable validator failures

### Layer 6: Source coverage and provenance

- Coverage compares source script scenes against storyboard source references
- Provenance captures the source approval record at generation time
- Freshness changes when the source script approval changes

### Layer 7: Database compatibility

- Fresh database initialization
- Existing database reopen and reuse
- SQLite resource release after close

## Output Contract

The verification script must write:

- `storyboard-verification-report.md`
- `storyboard-verification-report.json`

Default report directory:

- `/tmp/ai-drama-storyboard-verification-report`

Default scratch directories:

- `/tmp/ai-drama-storyboard-complete-verification`
- `/tmp/ai-drama-storyboard-complete-verification-export`

## Final Status Flags

The report must conclude with:

- `STORYBOARD_TECHNICAL_VERDICT`
- `STORYBOARD_QUALITY_STATUS`
- `SHOT_PROMPT_DEVELOPMENT`

Only pass results from all blocker-level checks may set technical verdict to `PASS`.
