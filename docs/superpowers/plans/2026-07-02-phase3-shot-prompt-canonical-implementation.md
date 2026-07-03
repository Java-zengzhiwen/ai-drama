# Phase 3 Shot Prompt Canonical Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 3 Shot Prompt Canonical Foundation from an approved and fresh Storyboard Revision through deterministic prompt rendering, bundle integrity, review, qualification, approval, and live Phase 4 eligibility checks.

**Architecture:** Extend the current Phase 0-2 Artifact, Revision, Dependency, Validation, Bundle, Approval, Gate, Export, and Skill package patterns. Keep `revisions.content_object_id` as canonical authority, candidate render objects outside formal `revision_outputs`, Approval Qualification outside the Content Bundle, and Phase 4 execution outside this phase. Dependency direction is `store -> canonical/renderer/integrity -> validators -> services -> cli`; validators do not import `RuntimeService`.

**Tech Stack:** Python, SQLite, pytest, argparse CLI, existing `ai_drama_runtime` Store/Runtime/Skill architecture, deterministic JSON serialization, SHA-256 content-addressed object storage, repository-local verifier scripts.

---

Plan Status: IMPLEMENTATION_PLAN_PENDING_USER_REVIEW
Implementation: IMPLEMENTATION_NOT_AUTHORIZED
Phase 4: PHASE4_NOT_AUTHORIZED

## Source Baseline

- Branch: `test/phase2-minimal-bundle-foundation`
- Design Approval Baseline: `b178f8eabe4a0e7474e27d7225f76355e743b373`
- Implementation Plan Baseline: `d2df5b615e4a291f9b81128df101c8dd15ebb512`
- Future Implementation Start Commit: supplied at execution time through `--execution-start-commit <IMPLEMENTATION_AUTHORIZATION_COMMIT>`
- Approved Design Spec: `docs/superpowers/specs/2026-07-01-phase3-shot-prompt-canonical-design.md`
- Design status verified: `Document Status: DESIGN_SPEC_APPROVED`
- Planning authorization verified: `Implementation Planning: IMPLEMENTATION_PLANNING_AUTHORIZED`
- Implementation state verified: `Implementation: IMPLEMENTATION_NOT_AUTHORIZED`
- This plan does not implement code, database changes, migrations, tests, skill changes, generation, asset binding, Phase 4 work, or push.

The Design Approval Commit, this Implementation Plan Commit, and the future Implementation Start Commit are distinct. The Phase 3 verifier final mode must require the future Implementation Start Commit as a runtime argument. It must not hard-code the implementation authorization point in source.

## Repository Evidence Read

- Runtime and Store: `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, `ai_drama_runtime/validators.py`, `ai_drama_runtime/cli.py`
- Storyboard foundation: `ai_drama_runtime/storyboard_canonical.py`, `ai_drama_runtime/storyboard_renderer.py`, `ai_drama_runtime/storyboard_migration.py`
- Skill loader and registry: `ai_drama_runtime/manifest.py`, `ai_drama_runtime/registry.py`, `ai_drama_runtime/request.py`
- Verification pattern: `tools/verify_phase2_minimal_bundle_foundation.py`
- Existing tests: `tests/test_manifest.py`, `tests/test_validator_inventory.py`, `tests/test_storyboard_canonical_serialization.py`, `tests/test_storyboard_canonical_workflow.py`, `tests/test_storyboard_legacy_migration.py`, `tests/test_storyboard_renderer.py`, `tests/test_storyboard_workflow.py`, `tests/test_validators_approval_export.py`, `tests/test_runtime_lifecycle.py`, `tests/test_cli.py`, `tests/test_phase1_verifier.py`, `tests/test_phase2_verifier.py`, `tests/acceptance/test_storyboard_workflow_acceptance.py`
- Protected upstream skill: `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`

## File Map

Create:

- `ai_drama_runtime/shot_prompt_canonical.py`: parser, duplicate-key rejection, NFC normalization, deterministic serialization, schema validation, content hash, draft/formal profiles, `append_dedup`, and Runtime-derived `slot_id`.
- `ai_drama_runtime/shot_prompt_renderer.py`: exact renderer registry, effective intent merge, positive image/video prompt rendering, dialogue rendering, negative rendering, fixed fact invariants, asset requirements rendering, render provenance, and review markdown.
- `ai_drama_runtime/shot_prompt_bundle.py`: candidate object contract, render validation, validation report candidate, bundle manifest construction, bundle materialization payloads, and bundle integrity pure helpers.
- `ai_drama_runtime/shot_prompt_migration.py`: SQLite inventory, deterministic preview, apply, replay, rollback behavior, and table rebuild helpers.
- `tools/verify_phase3_shot_prompt_canonical_foundation.py`: portable/final verifier with explicit execution start commit contract and verification report generation.
- `tests/fixtures/shot_prompt_canonical/minimal_storyboard.json`: minimal approved Storyboard source fixture.
- `tests/fixtures/shot_prompt_canonical/valid_draft_shared_only.json`: Draft fixture with `shared_intent` only.
- `tests/fixtures/shot_prompt_canonical/valid_formal_mixed_modalities.json`: Formal fixture with image-only, video-only, and dual-modality shots.
- `tests/fixtures/shot_prompt_canonical/invalid_duplicate_key.json`: duplicate-key fixture.
- `tests/fixtures/shot_prompt_canonical/invalid_slot_id_authored.json`: authored `slot_id` rejection fixture.
- `tests/golden/shot_prompt_renderer/rendered-positive-prompts.json`: deterministic positive prompt golden.
- `tests/golden/shot_prompt_renderer/rendered-negative-prompts.json`: deterministic negative prompt golden.
- `tests/golden/shot_prompt_renderer/asset-requirements.json`: deterministic asset requirement golden with derived `slot_id`.
- `tests/golden/shot_prompt_renderer/render-provenance.json`: minimal provenance golden.
- `tests/golden/shot_prompt_renderer/review.md`: deterministic review surface golden.
- `tests/test_phase3_verifier.py`: verifier mode, allowlist, protected-file, report, and leakage tests.
- `tests/test_shot_prompt_store_migration.py`: inventory, preview, apply, replay, table rebuild, FK, CHECK, unique index, and rollback tests.
- `tests/test_shot_prompt_canonical_parser.py`: parser, duplicate key, NFC bytes, hash, root, renderer lock, draft/formal, and forbidden field tests.
- `tests/test_shot_prompt_canonical_schema.py`: shot, intent, dialogue, continuity, asset slot, negative constraint, set-default, and merge tests.
- `tests/test_shot_prompt_validators.py`: runtime-native validator dispatch and persisted validation results.
- `tests/test_shot_prompt_renderer.py`: renderer registry, merge, positive, video, dialogue, negative, asset, provenance, review, and golden tests.
- `tests/test_shot_prompt_bundle.py`: candidate object contract, render validation, validation report, materialization, atomic rollback, and integrity tests.
- `tests/test_shot_prompt_review_records.py`: review records and append-only event lifecycle tests.
- `tests/test_shot_prompt_approval_lifecycle.py`: qualification, evidence, approval, rejection, revocation, supersession, and eligibility tests.
- `tests/test_shot_prompt_cli.py`: command surface, JSON stdout, stderr, exit code, side effects, and rejected option tests.
- `tests/test_shot_prompt_skill_package.py`: skill package loader, validator declarations, profile, schema, contract, and package hash tests.
- `tests/test_shot_prompt_end_to_end.py`: happy path, supersession, revoke, source stale, bundle tamper, and eligibility tests.
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/skill.json`: Phase 3 skill package metadata using the existing loader schema.
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/SKILL.md`: agent-facing Phase 3 authoring instructions.
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/README.md`: package README.
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/contracts/shot-prompt-canonical-contract-v1.md`: canonical authoring contract.
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/schemas/shot-prompt-canonical.schema.json`: Draft/Formal schema.
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/validators/runtime_native.py`: real entrypoint file declared by runtime-native validators.
- `reports/phase3-shot-prompt-canonical-verification.json`: generated verification report.
- `reports/phase3-shot-prompt-canonical-verification.md`: generated verification summary.

Modify:

- `ai_drama_runtime/store.py`: DDL, dataclasses, migrations, Store records, insert/read APIs, review records, approval evidence, and transactions.
- `ai_drama_runtime/services.py`: Shot Prompt orchestration, canonical byte storage, render candidate flow, bundle materialization, review, qualification, lifecycle, eligibility, and export blocking.
- `ai_drama_runtime/validators.py`: runtime-native Shot Prompt validator dispatch without importing `RuntimeService`.
- `ai_drama_runtime/cli.py`: explicit `shot-prompts` command surface using existing argparse and exit-code style.
- `ai_drama_runtime/manifest.py`: allow the new shot prompt execution profile while preserving storyboard profile validation.
- `ai_drama_runtime/runtime.py`: add mock canonical Shot Prompt response only for Phase 3 tests.
- `ai_drama_runtime/request.py`: add Shot Prompt runtime request construction using existing Skill package metadata.

Protected files:

- `docs/superpowers/specs/2026-07-01-phase3-shot-prompt-canonical-design.md`
- `docs/superpowers/plans/2026-07-02-phase3-shot-prompt-canonical-implementation.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`
- `docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md`
- `docs/superpowers/specs/2026-06-29-phase-1-agent-execution-acceptance-contract.md`
- `docs/superpowers/specs/2026-06-29-phase-2-minimal-bundle-foundation-design.md`
- `docs/superpowers/specs/2026-06-29-phase-2-agent-execution-acceptance-contract.md`
- Phase 0-2 release artifacts under existing protected report and skill package paths.

Verifier allowlist exact files:

- All Create and Modify files in this File Map.
- `reports/phase3-shot-prompt-canonical-verification.json`
- `reports/phase3-shot-prompt-canonical-verification.md`

Verifier allowlist controlled prefixes:

- `tests/fixtures/shot_prompt_canonical/`
- `tests/golden/shot_prompt_renderer/`
- `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/`

No allowlist entry permits the full repository.

## Frozen Contracts

### Dependency Direction

```text
store.py
↑
shot_prompt_canonical.py / shot_prompt_renderer.py / shot_prompt_bundle.py / shot_prompt_migration.py
↑
validators.py
↑
services.py
↑
cli.py
```

`validators.py` must not import `RuntimeService`. Bundle Integrity logic lives in `shot_prompt_bundle.py` and is called by both validators and services.

### Verifier Modes

```text
portable:
- no fixed branch requirement
- no execution start ancestor requirement
- runs functional tests and static boundary checks

final:
- requires target branch test/phase2-minimal-bundle-foundation
- requires --execution-start-commit
- requires clean tree
- checks execution start commit is HEAD ancestor
- checks changed files against exact allowlist plus controlled prefixes
- checks protected files are unchanged from execution start commit
- runs all portable checks
```

The verification report records `execution_start_commit`, `code_head_at_report_generation`, Design Spec hash, Plan hash, verifier version, changed files, protected files, command results, acceptance matrix, and `no_phase4_execution=true`. The final HEAD is not a self-referential required report field; the report is evidence generated by the verifier against the code head visible when the verifier ran.

### Candidate Object Set

```python
@dataclass(frozen=True)
class ShotPromptCandidateObject:
    filename: str
    object_id: str
    content_hash: str
    media_type: str
    generator: str
    generator_version: str
    canonical_content_hash: str
    renderer_profile_id: str
    renderer_profile_version: str
```

Candidate objects are written to the object store and returned by services. Render and Render Validation do not write formal `revision_outputs`.

### Phase 3 Logical Types

```python
PHASE3_REVISION_OUTPUT_TYPES = {
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
}
```

Existing earlier values stay accepted by the Store.

### Runtime-Native Validator IDs

```python
SHOT_PROMPT_VALIDATORS = {
    "shot_prompt_source_eligibility": ("ERROR", True),
    "shot_prompt_dependency_binding": ("ERROR", True),
    "shot_prompt_full_shot_coverage": ("ERROR", True),
    "shot_prompt_storyboard_fact_read_only": ("ERROR", True),
    "shot_prompt_current_shot_membership": ("ERROR", True),
    "shot_prompt_modality_completeness": ("ERROR", True),
    "shot_prompt_dialogue_coverage": ("ERROR", True),
    "shot_prompt_dialogue_consistency": ("ERROR", True),
    "shot_prompt_continuity": ("ERROR", True),
    "shot_prompt_asset_slots": ("ERROR", True),
    "shot_prompt_platform_neutrality": ("ERROR", True),
    "shot_prompt_forbidden_fields": ("ERROR", True),
    "shot_prompt_language_consistency_lint": ("WARNING", False),
    "shot_prompt_high_risk_asset_warning": ("WARNING", False),
    "shot_prompt_render_validation": ("ERROR", True),
    "shot_prompt_bundle_integrity": ("ERROR", True),
    "shot_prompt_approval_qualification": ("ERROR", True),
}
```

Each validator persists a `validation_results` row with deterministic JSON report bytes.

### Required CLI Surface

```text
shot-prompts create-revision
shot-prompts validate --profile draft|formal
shot-prompts render
shot-prompts validate-render
shot-prompts materialize-bundle
shot-prompts check-integrity
shot-prompts review-open
shot-prompts review-event
shot-prompts review-status
shot-prompts qualify
shot-prompts approve
shot-prompts reject
shot-prompts revoke
shot-prompts eligibility
shot-prompts export-formal
shot-prompts export-diagnostic
shot-prompts export-execution
```

CLI v1 rejects partial selectors, `asset_id`, URL, filesystem path binding, upload ID, platform parameters, waiver input, and exact timecodes.

## Task Dependency Graph

```mermaid
flowchart TD
  T0["Task 0: verifier skeleton"]
  T1["Task 1: migration inventory"]
  T2["Task 2: artifact business key migration"]
  T3["Task 3: revision outputs rebuild"]
  T4["Task 4: approval status rebuild"]
  T5["Task 5: approval evidence migration"]
  T6["Task 6: review tables migration"]
  T7["Task 7: migration apply replay rollback"]
  T8["Task 8: canonical parser bytes hash"]
  T9["Task 9: root renderer draft formal"]
  T10["Task 10: shot intent schemas"]
  T11["Task 11: dialogue schema"]
  T12["Task 12: continuity schema"]
  T13["Task 13: asset slots"]
  T14["Task 14: negative and defaults"]
  T15["Task 15: source validators"]
  T16["Task 16: modality dialogue validators"]
  T17["Task 17: continuity asset validators"]
  T18["Task 18: lint and warning validators"]
  T19["Task 19: renderer registry and merge"]
  T20["Task 20: positive renderers"]
  T21["Task 21: negative renderer"]
  T22["Task 22: assets provenance review"]
  T23["Task 23: candidate contract"]
  T24["Task 24: render validation report"]
  T25["Task 25: bundle materialization"]
  T26["Task 26: bundle integrity"]
  T27["Task 27: review records"]
  T28["Task 28: qualification report"]
  T29["Task 29: approval lifecycle"]
  T30["Task 30: services"]
  T31["Task 31: CLI"]
  T32["Task 32: skill package"]
  T33["Task 33: end to end"]
  T34["Task 34: final verifier reports"]

  T0 --> T1 --> T2 --> T3 --> T4 --> T5 --> T6 --> T7
  T0 --> T8 --> T9 --> T10 --> T11 --> T12 --> T13 --> T14
  T14 --> T15 --> T16 --> T17 --> T18
  T14 --> T19 --> T20 --> T21 --> T22
  T22 --> T23 --> T24 --> T25 --> T26
  T6 --> T27 --> T28 --> T29
  T18 --> T30
  T26 --> T30
  T29 --> T30
  T30 --> T31
  T18 --> T32
  T31 --> T33 --> T34
```

Parallel rules:

- Tasks 1-7 are Store and migration tasks and must run in numeric order because they modify `store.py` and `shot_prompt_migration.py`.
- Tasks 8-14 are canonical schema tasks and must run in numeric order because they modify `shot_prompt_canonical.py`.
- Tasks 15-18 are validator tasks and must run in numeric order because they modify `validators.py`.
- Tasks 19-22 are renderer tasks and must run in numeric order because they modify `shot_prompt_renderer.py`.
- Task 27 can run after Task 6 without waiting for renderer work.
- Task 32 can run after Task 18 because Skill declarations depend on validator IDs.
- No two tasks that modify the same file run in parallel.

## Commit Strategy

- Task 0: `test: add phase 3 verifier skeleton`
- Task 1: `test: add phase 3 migration inventory preview`
- Task 2: `feat: add shot prompt artifact business key migration`
- Task 3: `feat: rebuild revision outputs for shot prompt types`
- Task 4: `feat: rebuild revision approval status checks`
- Task 5: `feat: add shot prompt approval evidence columns`
- Task 6: `feat: add shot prompt review tables`
- Task 7: `test: cover shot prompt migration replay rollback`
- Task 8: `feat: add shot prompt canonical parser bytes`
- Task 9: `feat: validate shot prompt root renderer profiles`
- Task 10: `feat: validate shot prompt intent schemas`
- Task 11: `feat: validate shot prompt dialogue contract`
- Task 12: `feat: validate shot prompt continuity contract`
- Task 13: `feat: validate shot prompt asset slots`
- Task 14: `feat: validate shot prompt defaults and negatives`
- Task 15: `feat: add shot prompt source validators`
- Task 16: `feat: add shot prompt modality dialogue validators`
- Task 17: `feat: add shot prompt continuity asset validators`
- Task 18: `feat: add shot prompt lint validators`
- Task 19: `feat: add shot prompt renderer registry merge`
- Task 20: `feat: render shot prompt positive outputs`
- Task 21: `feat: render shot prompt negative outputs`
- Task 22: `feat: render shot prompt assets provenance review`
- Task 23: `feat: define shot prompt candidate objects`
- Task 24: `feat: validate shot prompt render candidates`
- Task 25: `feat: materialize shot prompt bundle`
- Task 26: `feat: verify shot prompt bundle integrity`
- Task 27: `feat: add shot prompt review records`
- Task 28: `feat: write shot prompt qualification reports`
- Task 29: `feat: add shot prompt approval lifecycle`
- Task 30: `feat: orchestrate shot prompt runtime services`
- Task 31: `feat: add shot prompt cli commands`
- Task 32: `feat: add shot prompt canonical skill package`
- Task 33: `test: add shot prompt end to end coverage`
- Task 34: `test: add shot prompt final verification`

## Tasks

### Task 0: Phase 3 Verifier Skeleton

**Depends on:** None

**Files:**
- Create: `tools/verify_phase3_shot_prompt_canonical_foundation.py`
- Create: `tests/test_phase3_verifier.py`
- Test: `tests/test_phase3_verifier.py`
- Verify: `python3 -m pytest tests/test_phase3_verifier.py -q`

**Design requirements covered:**
- Design Section 17 verification command requirement
- P01 verifier skeleton, allowlist, protected files, portable/final modes

- [ ] **Step 1: Write the failing test**

```python
def test_final_mode_requires_execution_start_commit(monkeypatch):
    verifier = _load_verifier_module()
    assert verifier.main(["--mode", "final"]) == 2
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_phase3_verifier.py::test_final_mode_requires_execution_start_commit -q
```

Expected:

```text
FAIL with FileNotFoundError for tools/verify_phase3_shot_prompt_canonical_foundation.py
```

- [ ] **Step 3: Implement the minimal production change**

```python
@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    evidence: str
    expected: str = ""
    actual: str = ""

def _run(args, *, env=None):
    return subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["portable", "final"], default="portable")
    parser.add_argument("--execution-start-commit", default="")
    parser.add_argument("--report-json", default="reports/phase3-shot-prompt-canonical-verification.json")
    parser.add_argument("--report-md", default="reports/phase3-shot-prompt-canonical-verification.md")
    args = parser.parse_args(argv)
    if args.mode == "final" and not args.execution_start_commit:
        print("final mode requires --execution-start-commit", file=sys.stderr)
        return 2
    results = portable_checks() if args.mode == "portable" else final_checks(args.execution_start_commit)
    return _print_results(results)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_phase3_verifier.py::test_final_mode_requires_execution_start_commit -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_phase2_verifier.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add tools/verify_phase3_shot_prompt_canonical_foundation.py tests/test_phase3_verifier.py
git commit -m "test: add phase 3 verifier skeleton"
```

### Task 1: Migration Inventory And Preview

**Depends on:** Task 0

**Files:**
- Create: `ai_drama_runtime/shot_prompt_migration.py`
- Create: `tests/test_shot_prompt_store_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_migration_preview_is_deterministic -q`

**Design requirements covered:**
- Design Section 15 Store and Migration Requirements
- P02 migration inventory and deterministic preview

- [ ] **Step 1: Write the failing test**

```python
def test_phase3_migration_preview_is_deterministic(tmp_path):
    db_path = tmp_path / "runtime.db"
    _create_phase2_legacy_db(db_path)
    first = preview_phase3_store_migration(db_path)
    second = preview_phase3_store_migration(db_path)
    assert first == second
    assert first["mode"] == "preview"
    assert first["tables"]["revision_outputs"]["needs_rebuild"] is True
    assert first["tables"]["artifacts"]["missing_columns"] == ["business_key_type", "business_key_value"]
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_migration_preview_is_deterministic -q
```

Expected:

```text
FAIL with ImportError for preview_phase3_store_migration
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _table_sql(conn, name):
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone()
    return row[0] if row else ""

def _table_info(conn, name):
    return [dict(row) for row in conn.execute("PRAGMA table_info(%s)" % name).fetchall()]

def _foreign_keys(conn, name):
    return [dict(row) for row in conn.execute("PRAGMA foreign_key_list(%s)" % name).fetchall()]

def _indexes(conn, name):
    return [dict(row) for row in conn.execute("PRAGMA index_list(%s)" % name).fetchall()]

def preview_phase3_store_migration(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        artifacts = {row["name"] for row in conn.execute("PRAGMA table_info(artifacts)").fetchall()}
        output_sql = _table_sql(conn, "revision_outputs")
        return {
            "mode": "preview",
            "tables": {
                "artifacts": {"missing_columns": [c for c in ["business_key_type", "business_key_value"] if c not in artifacts]},
                "revision_outputs": {"needs_rebuild": "shot_prompt_positive_prompts" not in output_sql},
                "revisions": {"needs_rebuild": "revoked" not in _table_sql(conn, "revisions")},
                "approval_records": {"needs_evidence": "qualification_report_hash" not in {r["name"] for r in conn.execute("PRAGMA table_info(approval_records)").fetchall()}},
                "review_records": {"missing": _table_sql(conn, "review_records") == ""},
                "review_record_events": {"missing": _table_sql(conn, "review_record_events") == ""},
            },
        }
    finally:
        conn.close()
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_migration_preview_is_deterministic -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "test: add phase 3 migration inventory preview"
```

### Task 2: Artifact Business Key Migration

**Depends on:** Task 1

**Files:**
- Modify: `ai_drama_runtime/store.py:RuntimeStore._init_schema`
- Modify: `ai_drama_runtime/shot_prompt_migration.py:apply_phase3_store_migration`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_artifact_business_key_migration_preserves_legacy_rows -q`

**Design requirements covered:**
- Acceptance Criterion 1
- P02 artifact business key migration

- [ ] **Step 1: Write the failing test**

```python
def test_artifact_business_key_migration_preserves_legacy_rows(tmp_path):
    db_path = tmp_path / "runtime.db"
    _create_phase2_legacy_db(db_path)
    apply_phase3_store_migration(db_path)
    with RuntimeStore(db_path, tmp_path / "objects") as store:
        columns = _columns(store, "artifacts")
        assert {"business_key_type", "business_key_value"} <= columns
        assert store.artifacts()[0]["artifact_id"] == "legacy-storyboard-artifact"
        store.ensure_shot_prompt_artifact("source-rev-1", "project-1", "chapter-1")
        store.ensure_shot_prompt_artifact("source-rev-1", "project-1", "chapter-1")
        rows = [row for row in store.artifacts() if row["artifact_type"] == "shot_prompt_set"]
        assert len(rows) == 1
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_artifact_business_key_migration_preserves_legacy_rows -q
```

Expected:

```text
FAIL because RuntimeStore has no ensure_shot_prompt_artifact
```

- [ ] **Step 3: Implement the minimal production change**

```python
def ensure_shot_prompt_artifact(self, source_storyboard_revision_id, project_id, chapter_id):
    artifact_id = "shot-prompt-set-" + hashlib.sha256(source_storyboard_revision_id.encode("utf-8")).hexdigest()[:24]
    self.conn.execute(
        """
        INSERT OR IGNORE INTO artifacts
        (artifact_id, artifact_type, project_id, chapter_id, business_key_type, business_key_value, created_at)
        VALUES (?, 'shot_prompt_set', ?, ?, 'source_storyboard_revision_id', ?, ?)
        """,
        (artifact_id, project_id, chapter_id, source_storyboard_revision_id, now_iso()),
    )
    self.conn.commit()
    row = self.conn.execute(
        """
        SELECT * FROM artifacts
        WHERE artifact_type = 'shot_prompt_set'
          AND business_key_type = 'source_storyboard_revision_id'
          AND business_key_value = ?
        """,
        (source_storyboard_revision_id,),
    ).fetchone()
    return dict(row)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_artifact_business_key_migration_preserves_legacy_rows -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_runtime_lifecycle.py tests/test_storyboard_workflow.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add shot prompt artifact business key migration"
```

### Task 3: Revision Outputs Table Rebuild

**Depends on:** Task 2

**Files:**
- Modify: `ai_drama_runtime/store.py:RuntimeStore._ensure_columns`
- Modify: `ai_drama_runtime/shot_prompt_migration.py:_rebuild_revision_outputs`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_rebuild_preserves_rows_and_adds_phase3_types -q`

**Design requirements covered:**
- Acceptance Criteria 26-30
- P02 revision outputs table rebuild

- [ ] **Step 1: Write the failing test**

```python
def test_revision_outputs_rebuild_preserves_rows_and_adds_phase3_types(tmp_path):
    db_path = tmp_path / "runtime.db"
    _create_phase2_legacy_db_with_revision_output(db_path)
    apply_phase3_store_migration(db_path)
    with RuntimeStore(db_path, tmp_path / "objects") as store:
        table_sql = store.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='revision_outputs'").fetchone()["sql"]
        assert "rendered_markdown" in table_sql
        assert "shot_prompt_positive_prompts" in table_sql
        assert store.get_revision_output("legacy-revision", "rendered_markdown").content_hash == "legacy-hash"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_rebuild_preserves_rows_and_adds_phase3_types -q
```

Expected:

```text
FAIL because the CHECK does not include shot_prompt_positive_prompts
```

- [ ] **Step 3: Implement the minimal production change**

```python
REVISION_OUTPUT_LOGICAL_TYPES = (
    "rendered_positive_prompt",
    "rendered_negative_prompt",
    "rendered_markdown",
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)

def _rebuild_revision_outputs(conn):
    allowed = ",".join("'%s'" % item for item in REVISION_OUTPUT_LOGICAL_TYPES)
    conn.executescript(
        f"""
        PRAGMA foreign_keys=OFF;
        BEGIN IMMEDIATE;
        CREATE TABLE revision_outputs_new (
          revision_output_id TEXT PRIMARY KEY,
          revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
          logical_type TEXT NOT NULL CHECK (logical_type IN ({allowed})),
          object_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          media_type TEXT NOT NULL,
          generator TEXT NOT NULL,
          generator_version TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(revision_id, logical_type)
        );
        INSERT INTO revision_outputs_new
        SELECT revision_output_id, revision_id, logical_type, object_id, content_hash, media_type, generator, generator_version, created_at
        FROM revision_outputs;
        DROP TABLE revision_outputs;
        ALTER TABLE revision_outputs_new RENAME TO revision_outputs;
        CREATE INDEX revision_outputs_content_hash_idx ON revision_outputs(content_hash);
        CREATE INDEX revision_outputs_object_id_idx ON revision_outputs(object_id);
        PRAGMA foreign_key_check;
        COMMIT;
        PRAGMA foreign_keys=ON;
        """
    )
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_rebuild_preserves_rows_and_adds_phase3_types -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: rebuild revision outputs for shot prompt types"
```

### Task 4: Revision Approval Status Rebuild

**Depends on:** Task 3

**Files:**
- Modify: `ai_drama_runtime/store.py:RuntimeStore._ensure_columns`
- Modify: `ai_drama_runtime/shot_prompt_migration.py:_rebuild_revisions`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revisions_rebuild_adds_revoked_status_and_preserves_current_approved_index -q`

**Design requirements covered:**
- Acceptance Criteria 35-36
- P02 revision approval status migration

- [ ] **Step 1: Write the failing test**

```python
def test_revisions_rebuild_adds_revoked_status_and_preserves_current_approved_index(tmp_path):
    db_path = tmp_path / "runtime.db"
    _create_phase2_legacy_db(db_path)
    apply_phase3_store_migration(db_path)
    with RuntimeStore(db_path, tmp_path / "objects") as store:
        sql = store.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='revisions'").fetchone()["sql"]
        assert "revoked" in sql
        indexes = {row["name"] for row in store.conn.execute("PRAGMA index_list(revisions)").fetchall()}
        assert "one_current_approved_revision" in indexes
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revisions_rebuild_adds_revoked_status_and_preserves_current_approved_index -q
```

Expected:

```text
FAIL because the revisions table has no approval_status CHECK with revoked
```

- [ ] **Step 3: Implement the minimal production change**

```python
APPROVAL_STATUSES = ("pending", "approved", "rejected", "superseded", "revoked")

def _rebuild_revisions(conn):
    allowed = ",".join("'%s'" % item for item in APPROVAL_STATUSES)
    conn.executescript(
        f"""
        PRAGMA foreign_keys=OFF;
        BEGIN IMMEDIATE;
        CREATE TABLE revisions_new (
          revision_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          artifact_type TEXT NOT NULL,
          project_id TEXT NOT NULL,
          chapter_id TEXT NOT NULL,
          run_id TEXT NOT NULL,
          skill_id TEXT NOT NULL,
          skill_version TEXT NOT NULL,
          skill_package_hash TEXT NOT NULL,
          runtime_provider TEXT NOT NULL,
          runtime_model TEXT NOT NULL,
          number INTEGER NOT NULL,
          content_object_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          raw_response_object_id TEXT NOT NULL,
          parser_version TEXT NOT NULL,
          content_profile TEXT NOT NULL DEFAULT '',
          derivation_type TEXT NOT NULL DEFAULT 'model_generation',
          supersedes_revision_id TEXT NOT NULL,
          approval_status TEXT NOT NULL CHECK (approval_status IN ({allowed})),
          created_at TEXT NOT NULL,
          FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );
        INSERT INTO revisions_new SELECT * FROM revisions;
        DROP TABLE revisions;
        ALTER TABLE revisions_new RENAME TO revisions;
        CREATE UNIQUE INDEX one_current_approved_revision ON revisions(artifact_id) WHERE approval_status = 'approved';
        PRAGMA foreign_key_check;
        COMMIT;
        PRAGMA foreign_keys=ON;
        """
    )
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revisions_rebuild_adds_revoked_status_and_preserves_current_approved_index -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_validators_approval_export.py tests/test_approval_ordering_resources.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: rebuild revision approval status checks"
```

### Task 5: Approval Evidence Migration

**Depends on:** Task 4

**Files:**
- Modify: `ai_drama_runtime/store.py:ApprovalRecord`
- Modify: `ai_drama_runtime/store.py:RuntimeStore._ensure_columns`
- Modify: `ai_drama_runtime/shot_prompt_migration.py:_migrate_approval_records`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_evidence_columns_preserve_old_records -q`

**Design requirements covered:**
- Acceptance Criteria 31 and 37
- P02 approval evidence migration

- [ ] **Step 1: Write the failing test**

```python
def test_approval_evidence_columns_preserve_old_records(tmp_path):
    db_path = tmp_path / "runtime.db"
    _create_phase2_legacy_db_with_approval(db_path)
    apply_phase3_store_migration(db_path)
    with RuntimeStore(db_path, tmp_path / "objects") as store:
        approval = store.approval_record("legacy-approval")
        assert approval.qualification_report_hash == ""
        assert approval.bundle_manifest_hash == ""
        assert store.latest_approval("legacy-revision").record_id == "legacy-approval"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_evidence_columns_preserve_old_records -q
```

Expected:

```text
FAIL because ApprovalRecord has no qualification_report_hash field
```

- [ ] **Step 3: Implement the minimal production change**

```python
APPROVAL_EVIDENCE_COLUMNS = {
    "source_storyboard_revision_id": "TEXT NOT NULL DEFAULT ''",
    "canonical_content_hash": "TEXT NOT NULL DEFAULT ''",
    "bundle_manifest_hash": "TEXT NOT NULL DEFAULT ''",
    "qualification_report_hash": "TEXT NOT NULL DEFAULT ''",
    "qualification_report_object_id": "TEXT NOT NULL DEFAULT ''",
    "renderer_profile_id": "TEXT NOT NULL DEFAULT ''",
    "renderer_profile_version": "TEXT NOT NULL DEFAULT ''",
    "qualification_profile_id": "TEXT NOT NULL DEFAULT ''",
    "qualification_profile_version": "TEXT NOT NULL DEFAULT ''",
    "revoked_approval_record_id": "TEXT NOT NULL DEFAULT ''",
}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_evidence_columns_preserve_old_records -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add shot prompt approval evidence columns"
```

### Task 6: Review Tables Migration

**Depends on:** Task 5

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Create: `tests/test_shot_prompt_review_records.py`
- Test: `tests/test_shot_prompt_store_migration.py`, `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_review_tables_have_scope_event_checks_and_ordering_indexes -q`

**Design requirements covered:**
- Acceptance Criteria 33-34
- P02 review tables migration

- [ ] **Step 1: Write the failing test**

```python
def test_review_tables_have_scope_event_checks_and_ordering_indexes(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        review_sql = _table_sql(store, "review_records")
        event_sql = _table_sql(store, "review_record_events")
        assert "scope IN ('set','shot')" in review_sql
        assert "event_type IN ('opened','resolved','reopened','voided')" in event_sql
        assert "review_record_events_review_id_created_event_idx" in _index_names(store, "review_record_events")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_review_tables_have_scope_event_checks_and_ordering_indexes -q
```

Expected:

```text
FAIL because review_records does not exist
```

- [ ] **Step 3: Implement the minimal production change**

```sql
CREATE TABLE IF NOT EXISTS review_records (
  review_id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  revision_id TEXT NOT NULL,
  scope TEXT NOT NULL CHECK (scope IN ('set','shot')),
  shot_id TEXT,
  reviewer TEXT NOT NULL,
  body_object_id TEXT NOT NULL,
  blocking INTEGER NOT NULL CHECK (blocking IN (0,1)),
  created_at TEXT NOT NULL,
  CHECK ((scope = 'set' AND shot_id IS NULL) OR (scope = 'shot' AND shot_id IS NOT NULL)),
  FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
);
CREATE TABLE IF NOT EXISTS review_record_events (
  event_id TEXT PRIMARY KEY,
  review_id TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('opened','resolved','reopened','voided')),
  reviewer TEXT NOT NULL,
  note TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(review_id) REFERENCES review_records(review_id)
);
CREATE INDEX IF NOT EXISTS review_records_revision_shot_idx ON review_records(revision_id, shot_id);
CREATE INDEX IF NOT EXISTS review_records_artifact_revision_idx ON review_records(artifact_id, revision_id);
CREATE INDEX IF NOT EXISTS review_record_events_review_id_created_event_idx ON review_record_events(review_id, created_at, event_id);
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_review_tables_have_scope_event_checks_and_ordering_indexes -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py tests/test_shot_prompt_review_records.py
git commit -m "feat: add shot prompt review tables"
```

### Task 7: Migration Apply Replay Rollback

**Depends on:** Task 6

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Modify: `tests/test_shot_prompt_store_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_migration_apply_replay_and_rollback -q`

**Design requirements covered:**
- P02 migration apply, replay, rollback tests

- [ ] **Step 1: Write the failing test**

```python
def test_phase3_migration_apply_replay_and_rollback(tmp_path, monkeypatch):
    db_path = tmp_path / "runtime.db"
    _create_phase2_legacy_db(db_path)
    apply_phase3_store_migration(db_path)
    apply_phase3_store_migration(db_path)
    with RuntimeStore(db_path, tmp_path / "objects") as store:
        assert store.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    broken = tmp_path / "broken.db"
    _create_phase2_legacy_db(broken)
    monkeypatch.setattr("ai_drama_runtime.shot_prompt_migration._create_review_tables", _raise_after_revision_rebuild)
    with pytest.raises(RuntimeError):
        apply_phase3_store_migration(broken)
    conn = sqlite3.connect(broken)
    assert conn.execute("SELECT name FROM sqlite_master WHERE name LIKE '%_new'").fetchall() == []
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_migration_apply_replay_and_rollback -q
```

Expected:

```text
FAIL because apply rollback leaves a transient table or is not idempotent
```

- [ ] **Step 3: Implement the minimal production change**

```python
def apply_phase3_store_migration(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        _add_artifact_business_key_columns(conn)
        if _revision_outputs_needs_rebuild(conn):
            _rebuild_revision_outputs(conn)
        if _revisions_need_rebuild(conn):
            _rebuild_revisions(conn)
        _add_approval_evidence_columns(conn)
        _create_review_tables(conn)
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            raise RuntimeError("foreign key check failed: %s" % fk)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_migration_apply_replay_and_rollback -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py tests/test_shot_prompt_store_migration.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "test: cover shot prompt migration replay rollback"
```

### Task 8: Canonical Parser Bytes And Hash

**Depends on:** Task 0

**Files:**
- Create: `ai_drama_runtime/shot_prompt_canonical.py`
- Create: `tests/test_shot_prompt_canonical_parser.py`
- Create: `tests/fixtures/shot_prompt_canonical/invalid_duplicate_key.json`
- Test: `tests/test_shot_prompt_canonical_parser.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_parser.py::test_shot_prompt_parse_rejects_duplicate_keys_and_hashes_exact_bytes -q`

**Design requirements covered:**
- Acceptance Criterion 38
- P03 parser and duplicate-key rejection
- P06 canonical bytes and hash

- [ ] **Step 1: Write the failing test**

```python
def test_shot_prompt_parse_rejects_duplicate_keys_and_hashes_exact_bytes():
    with pytest.raises(ShotPromptCanonicalError, match="duplicate JSON key"):
        parse_shot_prompt_json('{"schema_version":"shot-prompt-set-v1","schema_version":"shot-prompt-set-v1"}')
    value = {"schema_version": "shot-prompt-set-v1", "render_language": "zh-Hans"}
    data = serialize_shot_prompt_json(value)
    assert data == b'{"render_language":"zh-Hans","schema_version":"shot-prompt-set-v1"}'
    assert shot_prompt_content_hash(value) == hashlib.sha256(data).hexdigest()
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_parser.py::test_shot_prompt_parse_rejects_duplicate_keys_and_hashes_exact_bytes -q
```

Expected:

```text
FAIL with ImportError for ai_drama_runtime.shot_prompt_canonical
```

- [ ] **Step 3: Implement the minimal production change**

```python
SCHEMA_VERSION = "shot-prompt-set-v1"
CONTENT_PROFILE = "shot-prompt-set-v1"
SERIALIZATION_VERSION = "canonical-json-v1"
CANONICAL_PARSER_VERSION = "shot-prompt-canonical-json-v1"

class ShotPromptCanonicalError(ValueError):
    def __init__(self, code, message):
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.safe_message = message

def parse_shot_prompt_json(raw):
    return json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)

def serialize_shot_prompt_json(value):
    normalized = _normalize(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def shot_prompt_content_hash(value):
    return hashlib.sha256(serialize_shot_prompt_json(value)).hexdigest()
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_parser.py::test_shot_prompt_parse_rejects_duplicate_keys_and_hashes_exact_bytes -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_storyboard_canonical_serialization.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_parser.py tests/fixtures/shot_prompt_canonical/invalid_duplicate_key.json
git commit -m "feat: add shot prompt canonical parser bytes"
```

### Task 9: Root Schema Renderer Lock Draft Formal

**Depends on:** Task 8

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_canonical.py`
- Create: `tests/fixtures/shot_prompt_canonical/valid_draft_shared_only.json`
- Create: `tests/fixtures/shot_prompt_canonical/valid_formal_mixed_modalities.json`
- Test: `tests/test_shot_prompt_canonical_parser.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_parser.py::test_root_renderer_lock_and_profile_validation -q`

**Design requirements covered:**
- Acceptance Criteria 3-7
- P03 root schema and renderer exact lock

- [ ] **Step 1: Write the failing test**

```python
def test_root_renderer_lock_and_profile_validation():
    draft = _fixture("valid_draft_shared_only.json")
    validate_shot_prompt_canonical(draft, profile="draft")
    with pytest.raises(ShotPromptCanonicalError, match="FORMAL_MODALITY_REQUIRED"):
        validate_shot_prompt_canonical(draft, profile="formal")
    formal = _fixture("valid_formal_mixed_modalities.json")
    validate_shot_prompt_canonical(formal, profile="formal")
    assert formal["renderer"] == {"profile_id": "shot-prompt-renderer-v1", "version": "1.0.0"}
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_parser.py::test_root_renderer_lock_and_profile_validation -q
```

Expected:

```text
FAIL because validate_shot_prompt_canonical is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
REQUIRED_ROOT_KEYS = ["schema_version", "render_language", "renderer", "source", "set_defaults", "shots"]

def validate_shot_prompt_canonical(data, *, profile):
    _require_object(data, "shot_prompt_set")
    _require_required_keys(data, REQUIRED_ROOT_KEYS, "shot_prompt_set")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ShotPromptCanonicalError("CANONICAL_SCHEMA_INVALID", "schema_version must be %s" % SCHEMA_VERSION)
    if data["render_language"] not in {"zh-Hans", "en"}:
        raise ShotPromptCanonicalError("RENDER_LANGUAGE_INVALID", "render_language is invalid")
    _require_required_keys(data["renderer"], ["profile_id", "version"], "renderer")
    if data["renderer"] != {"profile_id": "shot-prompt-renderer-v1", "version": "1.0.0"}:
        raise ShotPromptCanonicalError("RENDERER_PROFILE_INVALID", "renderer profile/version is invalid")
    _validate_source(data["source"])
    _validate_shots(data["shots"], profile=profile)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_parser.py::test_root_renderer_lock_and_profile_validation -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_parser.py tests/test_storyboard_canonical_serialization.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_parser.py tests/fixtures/shot_prompt_canonical/valid_draft_shared_only.json tests/fixtures/shot_prompt_canonical/valid_formal_mixed_modalities.json
git commit -m "feat: validate shot prompt root renderer profiles"
```

### Task 10: Shot Shared Image Video Intent Schemas

**Depends on:** Task 9

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_canonical.py`
- Create: `tests/test_shot_prompt_canonical_schema.py`
- Test: `tests/test_shot_prompt_canonical_schema.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_shot_intents_validate_modality_outputs -q`

**Design requirements covered:**
- Acceptance Criteria 8 and 10
- P03 shot/shared/image/video intent schema

- [ ] **Step 1: Write the failing test**

```python
def test_shot_intents_validate_modality_outputs():
    data = _fixture("valid_formal_mixed_modalities.json")
    validate_shot_prompt_canonical(data, profile="formal")
    assert output_modalities_for_shot(data["shots"][0]) == {"image"}
    assert output_modalities_for_shot(data["shots"][1]) == {"video"}
    data["shots"][0]["source_shot_id"] = data["shots"][0]["shot_id"]
    with pytest.raises(ShotPromptCanonicalError, match="source_shot_id"):
        validate_shot_prompt_canonical(data, profile="formal")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_shot_intents_validate_modality_outputs -q
```

Expected:

```text
FAIL because output_modalities_for_shot is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
SHOT_ALLOWED_KEYS = {"shot_id", "shared_intent", "image_intent", "video_intent", "dialogue", "continuity", "asset_reference_slots", "negative_constraints"}

def output_modalities_for_shot(shot):
    result = set()
    if "image_intent" in shot:
        result.add("image")
    if "video_intent" in shot:
        result.add("video")
    return result

def _validate_shot(shot, path, *, profile):
    _require_object(shot, path)
    _reject_extra_keys(shot, SHOT_ALLOWED_KEYS, path)
    _require_string(shot["shot_id"], path + ".shot_id")
    if profile == "formal" and not output_modalities_for_shot(shot):
        raise ShotPromptCanonicalError("FORMAL_MODALITY_REQUIRED", "%s needs image_intent or video_intent" % path)
    if "shared_intent" in shot:
        _validate_intent(shot["shared_intent"], path + ".shared_intent")
    if "image_intent" in shot:
        _validate_intent(shot["image_intent"], path + ".image_intent")
    if "video_intent" in shot:
        _validate_intent(shot["video_intent"], path + ".video_intent")
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_shot_intents_validate_modality_outputs -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_parser.py tests/test_shot_prompt_canonical_schema.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_schema.py
git commit -m "feat: validate shot prompt intent schemas"
```

### Task 11: Dialogue Schema

**Depends on:** Task 10

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_canonical.py`
- Modify: `tests/test_shot_prompt_canonical_schema.py`
- Test: `tests/test_shot_prompt_canonical_schema.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_dialogue_schema_requires_video_and_strict_fields -q`

**Design requirements covered:**
- Acceptance Criteria 18-19
- P03 dialogue schema and strict coverage

- [ ] **Step 1: Write the failing test**

```python
def test_dialogue_schema_requires_video_and_strict_fields():
    data = _fixture("valid_formal_mixed_modalities.json")
    image_shot = data["shots"][0]
    image_shot["dialogue"] = [{"source_dialogue_ref": "D1", "relative_timing": "during", "post_dialogue_hold": "short", "lip_sync_required": True}]
    with pytest.raises(ShotPromptCanonicalError, match="IMAGE_DIALOGUE_FORBIDDEN"):
        validate_shot_prompt_canonical(data, profile="formal")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_dialogue_schema_requires_video_and_strict_fields -q
```

Expected:

```text
FAIL because image-only shots accept dialogue
```

- [ ] **Step 3: Implement the minimal production change**

```python
DIALOGUE_KEYS = {"source_dialogue_ref", "relative_timing", "post_dialogue_hold", "lip_sync_required"}
RELATIVE_TIMING = {"before", "during", "after"}

def _validate_dialogue_items(shot, path):
    items = shot.get("dialogue", [])
    _require_array(items, path)
    if items and "video_intent" not in shot:
        raise ShotPromptCanonicalError("IMAGE_DIALOGUE_FORBIDDEN", "image-only shot cannot contain dialogue")
    for index, item in enumerate(items):
        item_path = "%s[%d]" % (path, index)
        _require_required_keys(item, DIALOGUE_KEYS, item_path)
        _require_string(item["source_dialogue_ref"], item_path + ".source_dialogue_ref")
        if item["relative_timing"] not in RELATIVE_TIMING:
            raise ShotPromptCanonicalError("DIALOGUE_TIMING_INVALID", item_path)
        _require_string(item["post_dialogue_hold"], item_path + ".post_dialogue_hold")
        if not isinstance(item["lip_sync_required"], bool):
            raise ShotPromptCanonicalError("DIALOGUE_LIP_SYNC_INVALID", item_path)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_dialogue_schema_requires_video_and_strict_fields -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_schema.py
git commit -m "feat: validate shot prompt dialogue contract"
```

### Task 12: Continuity Schema

**Depends on:** Task 11

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_canonical.py`
- Modify: `tests/test_shot_prompt_canonical_schema.py`
- Test: `tests/test_shot_prompt_canonical_schema.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_continuity_scope_and_specific_shot_direction -q`

**Design requirements covered:**
- Acceptance Criteria 16-17
- P03 continuity schema

- [ ] **Step 1: Write the failing test**

```python
def test_continuity_scope_and_specific_shot_direction():
    data = _fixture("valid_formal_mixed_modalities.json")
    data["shots"][0]["continuity"] = [{"entity_id": "CHAR_A", "purpose": "identity", "requirement": "required", "source_scope": "specific_shot", "source_shot_id": data["shots"][0]["shot_id"], "modality_usage": ["video"]}]
    with pytest.raises(ShotPromptCanonicalError, match="CONTINUITY_SOURCE_SHOT_INVALID"):
        validate_shot_prompt_canonical(data, profile="formal")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_continuity_scope_and_specific_shot_direction -q
```

Expected:

```text
FAIL because continuity source direction is not validated
```

- [ ] **Step 3: Implement the minimal production change**

```python
CONTINUITY_SOURCE_SCOPES = {"set_baseline", "previous_occurrence", "specific_shot"}
CONTINUITY_REQUIREMENTS = {"required", "optional"}

def _validate_continuity_items(shots):
    order = {shot["shot_id"]: index for index, shot in enumerate(shots)}
    for shot in shots:
        for item in shot.get("continuity", []):
            if item["requirement"] not in CONTINUITY_REQUIREMENTS:
                raise ShotPromptCanonicalError("CONTINUITY_REQUIREMENT_INVALID", shot["shot_id"])
            if item["source_scope"] not in CONTINUITY_SOURCE_SCOPES:
                raise ShotPromptCanonicalError("CONTINUITY_SOURCE_SCOPE_INVALID", shot["shot_id"])
            if item["source_scope"] == "specific_shot":
                source_id = item.get("source_shot_id")
                if not source_id or order[source_id] >= order[shot["shot_id"]]:
                    raise ShotPromptCanonicalError("CONTINUITY_SOURCE_SHOT_INVALID", shot["shot_id"])
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_continuity_scope_and_specific_shot_direction -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_schema.py
git commit -m "feat: validate shot prompt continuity contract"
```

### Task 13: Asset Slot Schema And Derived Slot ID

**Depends on:** Task 12

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_canonical.py`
- Create: `tests/fixtures/shot_prompt_canonical/invalid_slot_id_authored.json`
- Modify: `tests/test_shot_prompt_canonical_schema.py`
- Test: `tests/test_shot_prompt_canonical_schema.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_asset_slot_schema_and_derived_slot_id -q`

**Design requirements covered:**
- Acceptance Criteria 11-15
- P03 asset slot schema and derived `slot_id` helper

- [ ] **Step 1: Write the failing test**

```python
def test_asset_slot_schema_and_derived_slot_id():
    data = _fixture("valid_formal_mixed_modalities.json")
    slot = data["shots"][0]["asset_reference_slots"][0]
    assert "slot_id" not in slot
    assert derive_slot_id(data["source"]["storyboard_revision_id"], data["shots"][0]["shot_id"], slot["entity_type"], slot["entity_id"]).startswith("slot_")
    slot["slot_id"] = "slot_authored"
    with pytest.raises(ShotPromptCanonicalError, match="slot_id"):
        validate_shot_prompt_canonical(data, profile="formal")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_asset_slot_schema_and_derived_slot_id -q
```

Expected:

```text
FAIL because derive_slot_id is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
ASSET_PURPOSES = {"identity", "costume", "scene_layout", "prop_identity", "prop_state", "keyframe_reference", "other"}

def derive_slot_id(source_storyboard_revision_id, shot_id, entity_type, entity_id):
    payload = serialize_shot_prompt_json([source_storyboard_revision_id, shot_id, entity_type, entity_id])
    return "slot_" + hashlib.sha256(payload).hexdigest()[:24]

def _validate_asset_slots(slots, path):
    seen = set()
    for slot in slots:
        if "slot_id" in slot or "shot_id" in slot:
            raise ShotPromptCanonicalError("ASSET_SLOT_DERIVED_FIELD_FORBIDDEN", path)
        key = (slot["entity_type"], slot["entity_id"])
        if key in seen:
            raise ShotPromptCanonicalError("ASSET_SLOT_DUPLICATE", path)
        seen.add(key)
        purposes = set()
        for purpose in slot["purposes"]:
            if purpose["purpose"] not in ASSET_PURPOSES:
                raise ShotPromptCanonicalError("ASSET_PURPOSE_INVALID", path)
            if purpose["purpose"] == "other" and not purpose.get("usage_note"):
                raise ShotPromptCanonicalError("ASSET_PURPOSE_USAGE_NOTE_REQUIRED", path)
            if purpose["purpose"] in purposes:
                raise ShotPromptCanonicalError("ASSET_PURPOSE_DUPLICATE", path)
            purposes.add(purpose["purpose"])
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_asset_slot_schema_and_derived_slot_id -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py tests/test_shot_prompt_canonical_parser.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_schema.py tests/fixtures/shot_prompt_canonical/invalid_slot_id_authored.json
git commit -m "feat: validate shot prompt asset slots"
```

### Task 14: Negative Constraints And Set Defaults

**Depends on:** Task 13

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_canonical.py`
- Modify: `tests/test_shot_prompt_canonical_schema.py`
- Test: `tests/test_shot_prompt_canonical_schema.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_set_defaults_merge_policies_and_negative_boundaries -q`

**Design requirements covered:**
- Acceptance Criteria 20-22
- P03 negative constraints and set defaults

- [ ] **Step 1: Write the failing test**

```python
def test_set_defaults_merge_policies_and_negative_boundaries():
    data = _fixture("valid_formal_mixed_modalities.json")
    data["negative_constraints"] = []
    with pytest.raises(ShotPromptCanonicalError, match="additional property"):
        validate_shot_prompt_canonical(data, profile="formal")
    merged = append_dedup([" keep ", "keep", "Keep"])
    assert merged == ["keep", "Keep"]
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_set_defaults_merge_policies_and_negative_boundaries -q
```

Expected:

```text
FAIL because append_dedup is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
MERGE_POLICIES = {"replace", "append_dedup", "invariant"}

def append_dedup(values):
    result = []
    seen = set()
    for value in values:
        normalized = unicodedata.normalize("NFC", value.strip())
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result

def merge_set_default(default_value, shot_value, policy):
    if policy == "replace":
        return shot_value if shot_value is not None else default_value
    if policy == "append_dedup":
        return append_dedup(list(default_value or []) + list(shot_value or []))
    if policy == "invariant":
        if shot_value in (None, default_value):
            return default_value
        raise ShotPromptCanonicalError("INVARIANT_CONFLICT", "set default invariant conflict")
    raise ShotPromptCanonicalError("MERGE_POLICY_INVALID", policy)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py::test_set_defaults_merge_policies_and_negative_boundaries -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_canonical.py tests/test_shot_prompt_canonical_schema.py
git commit -m "feat: validate shot prompt defaults and negatives"
```

### Task 15: Source Eligibility And Binding Validators

**Depends on:** Task 14

**Files:**
- Modify: `ai_drama_runtime/validators.py`
- Create: `tests/test_shot_prompt_validators.py`
- Test: `tests/test_shot_prompt_validators.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_validators.py::test_source_eligibility_and_dependency_binding_persist_results -q`

**Design requirements covered:**
- Acceptance Criteria 1, 2, 9, 38
- P03 validators source eligibility, dependency binding, full shot coverage, fact read-only

- [ ] **Step 1: Write the failing test**

```python
def test_source_eligibility_and_dependency_binding_persist_results(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_shot_prompt_revision(service, source_status="pending")
        results = run_declared_validators(service.store, _shot_prompt_skill(), revision, REPO_ROOT, repo_root=REPO_ROOT)
        by_id = {item.validator_id: item for item in results}
        assert by_id["shot_prompt_source_eligibility"].status == "FAIL"
        assert by_id["shot_prompt_source_eligibility"].error_code == "SOURCE_STORYBOARD_NOT_APPROVED"
        assert service.store.validation_results(revision.revision_id)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_source_eligibility_and_dependency_binding_persist_results -q
```

Expected:

```text
FAIL because shot_prompt_source_eligibility is not dispatched
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _run_native_shot_prompt_validator(store, revision, validator):
    if _revision_content_profile(revision) != "shot-prompt-set-v1":
        return None
    handlers = {
        "shot_prompt_source_eligibility": _validate_shot_prompt_source_eligibility,
        "shot_prompt_dependency_binding": _validate_shot_prompt_dependency_binding,
        "shot_prompt_full_shot_coverage": _validate_shot_prompt_full_shot_coverage,
        "shot_prompt_storyboard_fact_read_only": _validate_shot_prompt_storyboard_fact_read_only,
        "shot_prompt_current_shot_membership": _validate_shot_prompt_current_shot_membership,
    }
    handler = handlers.get(validator.validator_id)
    if handler is None:
        return None
    return _run_native_handler(store, revision, validator, handler)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_source_eligibility_and_dependency_binding_persist_results -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_validators_approval_export.py tests/test_storyboard_canonical_workflow.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/validators.py tests/test_shot_prompt_validators.py
git commit -m "feat: add shot prompt source validators"
```

### Task 16: Modality And Dialogue Validators

**Depends on:** Task 15

**Files:**
- Modify: `ai_drama_runtime/validators.py`
- Modify: `tests/test_shot_prompt_validators.py`
- Test: `tests/test_shot_prompt_validators.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_validators.py::test_modality_and_dialogue_validators_persist_failures -q`

**Design requirements covered:**
- Acceptance Criteria 7-8 and 18-19
- P03 validators modality completeness, dialogue coverage, dialogue consistency

- [ ] **Step 1: Write the failing test**

```python
def test_modality_and_dialogue_validators_persist_failures(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_shot_prompt_revision(service, fixture="dialogue_missing_source_ref")
        results = run_declared_validators(service.store, _shot_prompt_skill(), revision, REPO_ROOT, repo_root=REPO_ROOT)
        by_id = {item.validator_id: item for item in results}
        assert by_id["shot_prompt_modality_completeness"].status == "PASS"
        assert by_id["shot_prompt_dialogue_coverage"].status == "FAIL"
        assert by_id["shot_prompt_dialogue_consistency"].status == "FAIL"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_modality_and_dialogue_validators_persist_failures -q
```

Expected:

```text
FAIL because dialogue validators are not dispatched
```

- [ ] **Step 3: Implement the minimal production change**

```python
handlers.update(
    {
        "shot_prompt_modality_completeness": _validate_shot_prompt_modality_completeness,
        "shot_prompt_dialogue_coverage": _validate_shot_prompt_dialogue_coverage,
        "shot_prompt_dialogue_consistency": _validate_shot_prompt_dialogue_consistency,
    }
)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_modality_and_dialogue_validators_persist_failures -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/validators.py tests/test_shot_prompt_validators.py
git commit -m "feat: add shot prompt modality dialogue validators"
```

### Task 17: Continuity And Asset Validators

**Depends on:** Task 16

**Files:**
- Modify: `ai_drama_runtime/validators.py`
- Modify: `tests/test_shot_prompt_validators.py`
- Test: `tests/test_shot_prompt_validators.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_validators.py::test_continuity_and_asset_slot_validators_persist_results -q`

**Design requirements covered:**
- Acceptance Criteria 11-17
- P03 validators continuity and asset slots

- [ ] **Step 1: Write the failing test**

```python
def test_continuity_and_asset_slot_validators_persist_results(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_shot_prompt_revision(service, fixture="asset_entity_not_in_shot")
        results = run_declared_validators(service.store, _shot_prompt_skill(), revision, REPO_ROOT, repo_root=REPO_ROOT)
        by_id = {item.validator_id: item for item in results}
        assert by_id["shot_prompt_continuity"].status == "PASS"
        assert by_id["shot_prompt_asset_slots"].status == "FAIL"
        assert by_id["shot_prompt_asset_slots"].error_code == "ASSET_ENTITY_NOT_IN_SHOT"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_continuity_and_asset_slot_validators_persist_results -q
```

Expected:

```text
FAIL because asset slot validator is not dispatched
```

- [ ] **Step 3: Implement the minimal production change**

```python
handlers.update(
    {
        "shot_prompt_continuity": _validate_shot_prompt_continuity,
        "shot_prompt_asset_slots": _validate_shot_prompt_asset_slots,
    }
)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_continuity_and_asset_slot_validators_persist_results -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/validators.py tests/test_shot_prompt_validators.py
git commit -m "feat: add shot prompt continuity asset validators"
```

### Task 18: Platform Neutrality Lint And Warning Validators

**Depends on:** Task 17

**Files:**
- Modify: `ai_drama_runtime/validators.py`
- Modify: `tests/test_shot_prompt_validators.py`
- Test: `tests/test_shot_prompt_validators.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_validators.py::test_language_lint_and_high_risk_asset_warning_do_not_block -q`

**Design requirements covered:**
- Acceptance Criteria 22-23
- P03 validators platform neutrality, forbidden fields, language lint, high-risk asset warning

- [ ] **Step 1: Write the failing test**

```python
def test_language_lint_and_high_risk_asset_warning_do_not_block(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_shot_prompt_revision(service, fixture="language_mixed_high_risk_asset")
        results = run_declared_validators(service.store, _shot_prompt_skill(), revision, REPO_ROOT, repo_root=REPO_ROOT)
        by_id = {item.validator_id: item for item in results}
        assert by_id["shot_prompt_language_consistency_lint"].required is False
        assert by_id["shot_prompt_language_consistency_lint"].status == "WARNING"
        assert by_id["shot_prompt_high_risk_asset_warning"].status == "WARNING"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_language_lint_and_high_risk_asset_warning_do_not_block -q
```

Expected:

```text
FAIL because warning validators are not dispatched
```

- [ ] **Step 3: Implement the minimal production change**

```python
handlers.update(
    {
        "shot_prompt_platform_neutrality": _validate_shot_prompt_platform_neutrality,
        "shot_prompt_forbidden_fields": _validate_shot_prompt_forbidden_fields,
        "shot_prompt_language_consistency_lint": _validate_shot_prompt_language_consistency_lint,
        "shot_prompt_high_risk_asset_warning": _validate_shot_prompt_high_risk_asset_warning,
    }
)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py::test_language_lint_and_high_risk_asset_warning_do_not_block -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_validators.py tests/test_validator_inventory.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/validators.py tests/test_shot_prompt_validators.py
git commit -m "feat: add shot prompt lint validators"
```

### Task 19: Renderer Registry And Effective Intent Merge

**Depends on:** Task 14

**Files:**
- Create: `ai_drama_runtime/shot_prompt_renderer.py`
- Create: `tests/test_shot_prompt_renderer.py`
- Test: `tests/test_shot_prompt_renderer.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_renderer.py::test_renderer_registry_requires_exact_profile_and_merge_is_deterministic -q`

**Design requirements covered:**
- Acceptance Criteria 4 and 20-21
- P03 renderer exact registry and effective intent merge

- [ ] **Step 1: Write the failing test**

```python
def test_renderer_registry_requires_exact_profile_and_merge_is_deterministic():
    canonical = _fixture("valid_formal_mixed_modalities.json")
    renderer = resolve_renderer(canonical["renderer"]["profile_id"], canonical["renderer"]["version"])
    assert renderer.renderer_id == "shot-prompt-renderer"
    with pytest.raises(ShotPromptRenderError, match="RENDERER_PROFILE_UNAVAILABLE"):
        resolve_renderer("shot-prompt-renderer-v1", "9.9.9")
    merged = effective_intent(canonical["set_defaults"], canonical["shots"][0], "image")
    assert merged["modality"] == "image"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_renderer_registry_requires_exact_profile_and_merge_is_deterministic -q
```

Expected:

```text
FAIL with ImportError for shot_prompt_renderer
```

- [ ] **Step 3: Implement the minimal production change**

```python
RENDERER_ID = "shot-prompt-renderer"
RENDERER_VERSION = "1.0.0"
RENDERER_PROFILE_ID = "shot-prompt-renderer-v1"
RENDERER_PROFILE_VERSION = "1.0.0"

@dataclass(frozen=True)
class ShotPromptRenderer:
    renderer_id: str
    renderer_version: str
    profile_id: str
    profile_version: str

def resolve_renderer(profile_id, profile_version):
    if (profile_id, profile_version) != (RENDERER_PROFILE_ID, RENDERER_PROFILE_VERSION):
        raise ShotPromptRenderError("RENDERER_PROFILE_UNAVAILABLE", "renderer profile/version unavailable")
    return ShotPromptRenderer(RENDERER_ID, RENDERER_VERSION, profile_id, profile_version)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_renderer_registry_requires_exact_profile_and_merge_is_deterministic -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py tests/test_storyboard_renderer.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_renderer.py tests/test_shot_prompt_renderer.py
git commit -m "feat: add shot prompt renderer registry merge"
```

### Task 20: Positive Image And Video Renderers

**Depends on:** Task 19

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_renderer.py`
- Create: `tests/golden/shot_prompt_renderer/rendered-positive-prompts.json`
- Modify: `tests/test_shot_prompt_renderer.py`
- Test: `tests/test_shot_prompt_renderer.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_renderer.py::test_positive_prompt_rendering_matches_golden -q`

**Design requirements covered:**
- Acceptance Criteria 8 and 18-19
- P03 positive image renderer, positive video renderer, dialogue renderer

- [ ] **Step 1: Write the failing test**

```python
def test_positive_prompt_rendering_matches_golden():
    canonical = _fixture("valid_formal_mixed_modalities.json")
    rendered = render_positive_prompts(canonical)
    expected = _golden_json("rendered-positive-prompts.json")
    assert rendered == expected
    assert [item["shot_id"] for item in rendered["items"]] == [shot["shot_id"] for shot in canonical["shots"]]
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_positive_prompt_rendering_matches_golden -q
```

Expected:

```text
FAIL because render_positive_prompts is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def render_positive_prompts(canonical):
    validate_shot_prompt_canonical(canonical, profile="formal")
    items = []
    for shot in canonical["shots"]:
        if "image_intent" in shot:
            items.append(_positive_item(canonical, shot, "image"))
        if "video_intent" in shot:
            items.append(_positive_item(canonical, shot, "video"))
    return {"schema_version": "shot-prompt-positive-prompts-v1", "items": items}

def _positive_item(canonical, shot, modality):
    intent = effective_intent(canonical["set_defaults"], shot, modality)
    return {"shot_id": shot["shot_id"], "modality": modality, "prompt": _prompt_text(intent, shot, modality)}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_positive_prompt_rendering_matches_golden -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_renderer.py tests/test_shot_prompt_renderer.py tests/golden/shot_prompt_renderer/rendered-positive-prompts.json
git commit -m "feat: render shot prompt positive outputs"
```

### Task 21: Negative Renderer And Fixed Fact Invariants

**Depends on:** Task 20

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_renderer.py`
- Create: `tests/golden/shot_prompt_renderer/rendered-negative-prompts.json`
- Modify: `tests/test_shot_prompt_renderer.py`
- Test: `tests/test_shot_prompt_renderer.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_renderer.py::test_negative_prompt_rendering_uses_explicit_constraints_and_invariants -q`

**Design requirements covered:**
- Acceptance Criterion 22
- P03 negative renderer and fixed fact invariants

- [ ] **Step 1: Write the failing test**

```python
def test_negative_prompt_rendering_uses_explicit_constraints_and_invariants():
    canonical = _fixture("valid_formal_mixed_modalities.json")
    rendered = render_negative_prompts(canonical)
    assert rendered == _golden_json("rendered-negative-prompts.json")
    assert rendered["invariant_set"] == {"id": "shot-prompt-fact-protection", "version": "1.0.0"}
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_negative_prompt_rendering_uses_explicit_constraints_and_invariants -q
```

Expected:

```text
FAIL because render_negative_prompts is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
INVARIANT_SET_ID = "shot-prompt-fact-protection"
INVARIANT_SET_VERSION = "1.0.0"
FACT_INVARIANTS = [
    "preserve source shot identity",
    "preserve named entity identity and role",
    "preserve source dialogue meaning",
    "preserve validated continuity requirements",
]

def render_negative_prompts(canonical):
    validate_shot_prompt_canonical(canonical, profile="formal")
    return {
        "schema_version": "shot-prompt-negative-prompts-v1",
        "invariant_set": {"id": INVARIANT_SET_ID, "version": INVARIANT_SET_VERSION},
        "items": [_negative_item(canonical, shot, modality) for shot in canonical["shots"] for modality in sorted(output_modalities_for_shot(shot))],
    }
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_negative_prompt_rendering_uses_explicit_constraints_and_invariants -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_renderer.py tests/test_shot_prompt_renderer.py tests/golden/shot_prompt_renderer/rendered-negative-prompts.json
git commit -m "feat: render shot prompt negative outputs"
```

### Task 22: Asset Requirements Provenance And Review Markdown

**Depends on:** Task 21

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_renderer.py`
- Create: `tests/golden/shot_prompt_renderer/asset-requirements.json`
- Create: `tests/golden/shot_prompt_renderer/render-provenance.json`
- Create: `tests/golden/shot_prompt_renderer/review.md`
- Modify: `tests/test_shot_prompt_renderer.py`
- Test: `tests/test_shot_prompt_renderer.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_renderer.py::test_asset_requirements_provenance_and_review_golden_outputs -q`

**Design requirements covered:**
- Acceptance Criteria 15, 24, 31, 38
- P03 asset requirements renderer, render provenance, review markdown
- P06 skill provenance values from loader metadata

- [ ] **Step 1: Write the failing test**

```python
def test_asset_requirements_provenance_and_review_golden_outputs():
    canonical = _fixture("valid_formal_mixed_modalities.json")
    assert render_asset_requirements(canonical) == _golden_json("asset-requirements.json")
    provenance = render_provenance(canonical, _candidate_hashes())
    assert provenance == _golden_json("render-provenance.json")
    assert "bundle_manifest_hash" not in provenance
    assert render_review_markdown(canonical) == _golden_text("review.md")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_asset_requirements_provenance_and_review_golden_outputs -q
```

Expected:

```text
FAIL because render_asset_requirements is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def render_asset_requirements(canonical):
    items = []
    for shot in canonical["shots"]:
        for slot in shot.get("asset_reference_slots", []):
            items.append({
                "shot_id": shot["shot_id"],
                "slot_id": derive_slot_id(canonical["source"]["storyboard_revision_id"], shot["shot_id"], slot["entity_type"], slot["entity_id"]),
                "entity_type": slot["entity_type"],
                "entity_id": slot["entity_id"],
                "purposes": slot["purposes"],
            })
    return {"schema_version": "shot-prompt-asset-requirements-v1", "items": items}

def render_provenance(canonical, rendered_output_hashes):
    return {
        "schema_version": "shot-prompt-render-provenance-v1",
        "renderer_id": RENDERER_ID,
        "renderer_version": RENDERER_VERSION,
        "source_storyboard_revision_id": canonical["source"]["storyboard_revision_id"],
        "shot_prompt_revision_id": canonical.get("revision_id", ""),
        "canonical_content_hash": shot_prompt_content_hash(canonical),
        "renderer_profile_id": RENDERER_PROFILE_ID,
        "renderer_profile_version": RENDERER_PROFILE_VERSION,
        "invariant_set_id": INVARIANT_SET_ID,
        "invariant_set_version": INVARIANT_SET_VERSION,
        "rendered_output_hashes": rendered_output_hashes,
    }
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py::test_asset_requirements_provenance_and_review_golden_outputs -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_renderer.py tests/test_shot_prompt_renderer.py tests/golden/shot_prompt_renderer/asset-requirements.json tests/golden/shot_prompt_renderer/render-provenance.json tests/golden/shot_prompt_renderer/review.md
git commit -m "feat: render shot prompt assets provenance review"
```

### Task 23: Candidate Object Contract

**Depends on:** Task 22

**Files:**
- Create: `ai_drama_runtime/shot_prompt_bundle.py`
- Create: `tests/test_shot_prompt_bundle.py`
- Test: `tests/test_shot_prompt_bundle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_bundle.py::test_render_writes_candidate_objects_without_revision_outputs -q`

**Design requirements covered:**
- Acceptance Criteria 25-26
- P04 candidate object contract

- [ ] **Step 1: Write the failing test**

```python
def test_render_writes_candidate_objects_without_revision_outputs(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_formal_shot_prompt_revision(service)
        candidate_set = service.render_shot_prompt_candidates(revision.revision_id)
        assert {item.filename for item in candidate_set.objects} == REQUIRED_RENDER_CANDIDATE_FILENAMES
        assert service.store.revision_outputs(revision.revision_id) == []
        for item in candidate_set.objects:
            assert item.object_id == item.content_hash
            assert item.canonical_content_hash == revision.content_hash
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_render_writes_candidate_objects_without_revision_outputs -q
```

Expected:

```text
FAIL because render_shot_prompt_candidates is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
REQUIRED_RENDER_CANDIDATE_FILENAMES = {
    "rendered-positive-prompts.json",
    "rendered-negative-prompts.json",
    "asset-requirements.json",
    "render-provenance.json",
    "review.md",
}

@dataclass(frozen=True)
class ShotPromptCandidateSet:
    revision_id: str
    canonical_content_hash: str
    objects: tuple[ShotPromptCandidateObject, ...]
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_render_writes_candidate_objects_without_revision_outputs -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_renderer.py tests/test_shot_prompt_bundle.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_bundle.py tests/test_shot_prompt_bundle.py
git commit -m "feat: define shot prompt candidate objects"
```

### Task 24: Render Validation And Validation Report Candidate

**Depends on:** Task 23

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_bundle.py`
- Modify: `ai_drama_runtime/validators.py`
- Modify: `tests/test_shot_prompt_bundle.py`
- Test: `tests/test_shot_prompt_bundle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_bundle.py::test_render_validation_checks_members_hashes_and_report_candidate -q`

**Design requirements covered:**
- Acceptance Criteria 25-26 and 32
- P04 render validation and validation report

- [ ] **Step 1: Write the failing test**

```python
def test_render_validation_checks_members_hashes_and_report_candidate(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_formal_shot_prompt_revision(service)
        candidates = service.render_shot_prompt_candidates(revision.revision_id)
        report_candidate = service.validate_shot_prompt_render(revision.revision_id, candidates)
        assert report_candidate.filename == "validation-report.json"
        assert service.store.revision_outputs(revision.revision_id) == []
        tampered = _replace_candidate_hash(candidates, "rendered-positive-prompts.json", "0" * 64)
        with pytest.raises(BundleError, match="CANDIDATE_HASH_MISMATCH"):
            service.validate_shot_prompt_render(revision.revision_id, tampered)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_render_validation_checks_members_hashes_and_report_candidate -q
```

Expected:

```text
FAIL because validate_shot_prompt_render is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def validate_render_candidates(store, revision, candidate_set):
    filenames = {item.filename for item in candidate_set.objects}
    missing = REQUIRED_RENDER_CANDIDATE_FILENAMES - filenames
    if missing:
        raise BundleError("RENDER_CANDIDATE_MISSING", ",".join(sorted(missing)))
    for item in candidate_set.objects:
        data = store.read_bytes_object(item.object_id)
        actual = hashlib.sha256(data).hexdigest()
        if actual != item.content_hash or actual != item.object_id:
            raise BundleError("CANDIDATE_HASH_MISMATCH", item.filename)
        if item.canonical_content_hash != revision.content_hash:
            raise BundleError("CANDIDATE_CANONICAL_HASH_MISMATCH", item.filename)
    report = {"schema_version": "shot-prompt-validation-report-v1", "status": "PASS", "candidate_count": len(candidate_set.objects)}
    return report
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_render_validation_checks_members_hashes_and_report_candidate -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py tests/test_shot_prompt_validators.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_bundle.py ai_drama_runtime/validators.py tests/test_shot_prompt_bundle.py
git commit -m "feat: validate shot prompt render candidates"
```

### Task 25: Content Bundle Materialization

**Depends on:** Task 24

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_bundle.py`
- Modify: `ai_drama_runtime/store.py`
- Modify: `tests/test_shot_prompt_bundle.py`
- Test: `tests/test_shot_prompt_bundle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_bundle.py::test_bundle_materialization_inserts_all_rows_atomically -q`

**Design requirements covered:**
- Acceptance Criteria 27-31
- P04 bundle materialization

- [ ] **Step 1: Write the failing test**

```python
def test_bundle_materialization_inserts_all_rows_atomically(tmp_path, monkeypatch):
    with _shot_prompt_service(tmp_path) as service:
        revision = _insert_formal_shot_prompt_revision(service)
        candidates = service.render_shot_prompt_candidates(revision.revision_id)
        report = service.validate_shot_prompt_render(revision.revision_id, candidates)
        result = service.materialize_shot_prompt_bundle(revision.revision_id, candidates, report)
        assert result["status"] == "MATERIALIZED"
        assert {row.logical_type for row in service.store.revision_outputs(revision.revision_id)} == PHASE3_REVISION_OUTPUT_TYPES
        assert service.store.get_revision_output(revision.revision_id, "shot_prompt_validation_report")
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_bundle_materialization_inserts_all_rows_atomically -q
```

Expected:

```text
FAIL because materialize_shot_prompt_bundle is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def build_bundle_manifest(revision, candidate_set, validation_report_candidate):
    members = [{"filename": "canonical-content.json", "content_hash": revision.content_hash, "logical_type": ""}]
    for item in sorted(candidate_set.objects + (validation_report_candidate,), key=lambda obj: obj.filename):
        members.append({"filename": item.filename, "content_hash": item.content_hash, "logical_type": LOGICAL_TYPE_BY_FILENAME[item.filename]})
    business_preimage = {"schema_version": "shot-prompt-bundle-manifest-v1", "canonical_content_hash": revision.content_hash, "members": members}
    manifest_hash = hashlib.sha256(canonical_json_bytes(business_preimage)).hexdigest()
    return {**business_preimage, "revision_id": revision.revision_id, "bundle_manifest_hash": manifest_hash}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_bundle_materialization_inserts_all_rows_atomically -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_bundle.py ai_drama_runtime/store.py tests/test_shot_prompt_bundle.py
git commit -m "feat: materialize shot prompt bundle"
```

### Task 26: Bundle Integrity

**Depends on:** Task 25

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_bundle.py`
- Modify: `ai_drama_runtime/validators.py`
- Modify: `tests/test_shot_prompt_bundle.py`
- Test: `tests/test_shot_prompt_bundle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_bundle.py::test_bundle_integrity_detects_missing_extra_tampered_members -q`

**Design requirements covered:**
- Acceptance Criteria 28-32 and 39
- P04 bundle integrity
- H02 no validators to services import

- [ ] **Step 1: Write the failing test**

```python
def test_bundle_integrity_detects_missing_extra_tampered_members(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _materialized_shot_prompt_revision(service)
        assert service.check_shot_prompt_bundle_integrity(revision.revision_id)["status"] == "PASS"
        output = service.store.get_revision_output(revision.revision_id, "shot_prompt_positive_prompts")
        service.store.object_path(output.object_id).write_bytes(b"tampered")
        with pytest.raises(BundleError, match="REVISION_OUTPUT_HASH_MISMATCH"):
            service.check_shot_prompt_bundle_integrity(revision.revision_id)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_bundle_integrity_detects_missing_extra_tampered_members -q
```

Expected:

```text
FAIL because check_shot_prompt_bundle_integrity is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def check_shot_prompt_bundle_integrity(store, revision):
    outputs = store.revision_outputs(revision.revision_id)
    by_type = {item.logical_type: item for item in outputs}
    if set(by_type) != PHASE3_REVISION_OUTPUT_TYPES or len(outputs) != len(PHASE3_REVISION_OUTPUT_TYPES):
        raise BundleError("REVISION_OUTPUT_COMBINATION_INVALID", "Phase 3 output set is incomplete or conflicting")
    for output in outputs:
        data = store.read_bytes_object(output.object_id)
        actual = hashlib.sha256(data).hexdigest()
        if actual != output.object_id or actual != output.content_hash:
            raise BundleError("REVISION_OUTPUT_HASH_MISMATCH", output.logical_type)
    manifest = json.loads(store.read_text(by_type["bundle_manifest"].object_id))
    _assert_manifest_matches_outputs(manifest, revision, by_type)
    return {"status": "PASS", "bundle_manifest_hash": manifest["bundle_manifest_hash"]}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py::test_bundle_integrity_detects_missing_extra_tampered_members -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_bundle.py tests/test_validators_approval_export.py tests/test_storyboard_renderer.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_bundle.py ai_drama_runtime/validators.py tests/test_shot_prompt_bundle.py
git commit -m "feat: verify shot prompt bundle integrity"
```

### Task 27: Review Records And Events

**Depends on:** Task 6

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Modify: `tests/test_shot_prompt_review_records.py`
- Test: `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_events_compute_current_status_by_created_at_and_event_id -q`

**Design requirements covered:**
- Acceptance Criteria 33-34
- P05 review record creation, event append, current status, open blocking count

- [ ] **Step 1: Write the failing test**

```python
def test_review_events_compute_current_status_by_created_at_and_event_id(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _materialized_shot_prompt_revision(service)
        review = service.open_shot_prompt_review(revision.revision_id, scope="set", shot_id=None, reviewer="qa", body="needs check", blocking=True)
        service.append_shot_prompt_review_event(review["review_id"], "resolved", reviewer="qa", note="ok", created_at="2026-07-03T00:00:00Z", event_id="b")
        service.append_shot_prompt_review_event(review["review_id"], "reopened", reviewer="qa", note="again", created_at="2026-07-03T00:00:00Z", event_id="c")
        assert service.shot_prompt_review_status(review["review_id"])["status"] == "open"
        assert service.open_blocking_shot_prompt_review_count(revision.revision_id) == 1
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_events_compute_current_status_by_created_at_and_event_id -q
```

Expected:

```text
FAIL because open_shot_prompt_review is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def insert_review_record(self, **values):
    values.setdefault("review_id", uuid.uuid4().hex)
    values.setdefault("created_at", now_iso())
    values["body_object_id"] = self.write_text_object(values.pop("body"))
    self._insert("review_records", values)
    self.insert_review_event(review_id=values["review_id"], event_type="opened", reviewer=values["reviewer"], note="", created_at=values["created_at"])
    return self.review_record(values["review_id"])

def insert_review_event(self, **values):
    values.setdefault("event_id", uuid.uuid4().hex)
    values.setdefault("created_at", now_iso())
    self._insert("review_record_events", values)
    return self.review_events(values["review_id"])[-1]
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_events_compute_current_status_by_created_at_and_event_id -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/services.py tests/test_shot_prompt_review_records.py
git commit -m "feat: add shot prompt review records"
```

### Task 28: Approval Qualification Report

**Depends on:** Task 26, Task 27

**Files:**
- Modify: `ai_drama_runtime/services.py`
- Create: `tests/test_shot_prompt_approval_lifecycle.py`
- Test: `tests/test_shot_prompt_approval_lifecycle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_qualification_report_is_deterministic_and_outside_bundle -q`

**Design requirements covered:**
- Acceptance Criteria 31-33 and 37
- P05 approval qualification computation, deterministic report, object persistence

- [ ] **Step 1: Write the failing test**

```python
def test_qualification_report_is_deterministic_and_outside_bundle(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _materialized_shot_prompt_revision(service)
        report = service.qualify_shot_prompt_revision(revision.revision_id)
        assert report["status"] == "QUALIFIED"
        assert report["qualification_report_hash"]
        assert service.store.get_revision_output(revision.revision_id, "qualification_report") is None
        assert "qualification-report.json" not in service.store.read_text(service.store.get_revision_output(revision.revision_id, "bundle_manifest").object_id)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_qualification_report_is_deterministic_and_outside_bundle -q
```

Expected:

```text
FAIL because qualify_shot_prompt_revision is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
QUALIFICATION_PROFILE_ID = "shot-prompt-approval-qualification-v1"
QUALIFICATION_PROFILE_VERSION = "1.0.0"

def qualify_shot_prompt_revision(self, revision_id):
    revision = self._revision_or_raise(revision_id)
    integrity = check_shot_prompt_bundle_integrity(self.store, revision)
    if self.open_blocking_shot_prompt_review_count(revision_id):
        raise BundleApprovalBlocked("OPEN_BLOCKING_REVIEW", "open blocking review records exist")
    report = {
        "schema_version": "shot-prompt-qualification-report-v1",
        "revision_id": revision_id,
        "canonical_content_hash": revision.content_hash,
        "bundle_manifest_hash": integrity["bundle_manifest_hash"],
        "qualification_profile_id": QUALIFICATION_PROFILE_ID,
        "qualification_profile_version": QUALIFICATION_PROFILE_VERSION,
        "status": "QUALIFIED",
    }
    data = self._canonical_json_v1_bytes(report)
    object_id = self.store.write_bytes_object(data)
    return {**report, "qualification_report_object_id": object_id, "qualification_report_hash": self._sha256_bytes(data)}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_qualification_report_is_deterministic_and_outside_bundle -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py tests/test_shot_prompt_bundle.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/services.py tests/test_shot_prompt_approval_lifecycle.py
git commit -m "feat: write shot prompt qualification reports"
```

### Task 29: Approval Rejection Revocation Supersession Eligibility

**Depends on:** Task 28

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/services.py`
- Modify: `tests/test_shot_prompt_approval_lifecycle.py`
- Test: `tests/test_shot_prompt_approval_lifecycle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_approval_revoke_and_live_eligibility_lifecycle -q`

**Design requirements covered:**
- Acceptance Criteria 35-39
- P05 approval, rejection, revocation, supersession, live eligibility

- [ ] **Step 1: Write the failing test**

```python
def test_approval_revoke_and_live_eligibility_lifecycle(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        revision = _qualified_shot_prompt_revision(service)
        approved = service.approve_shot_prompt_revision(revision.revision_id, reviewer="qa", note="ok")
        assert approved.approval_status == "approved"
        assert service.shot_prompt_phase4_eligibility(revision.revision_id)["eligible"] is True
        revoked = service.revoke_shot_prompt_approval(revision.revision_id, reviewer="qa", note="bad bundle")
        assert revoked.approval_status == "revoked"
        latest = service.store.latest_approval(revision.revision_id)
        assert latest.action == "shot_prompt_approval_revoked"
        assert latest.qualification_report_hash == ""
        assert latest.revoked_approval_record_id
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_approval_revoke_and_live_eligibility_lifecycle -q
```

Expected:

```text
FAIL because approve_shot_prompt_revision is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def approve_shot_prompt_in_transaction(self, revision, reviewer, note, evidence):
    with self.conn:
        self.conn.execute("UPDATE revisions SET approval_status='superseded' WHERE artifact_id=? AND approval_status='approved'", (revision.artifact_id,))
        self.conn.execute("UPDATE revisions SET approval_status='approved' WHERE revision_id=?", (revision.revision_id,))
        self.conn.execute(
            """
            INSERT INTO approval_records
            (record_id, revision_id, artifact_id, action, reviewer, note, created_at,
             source_storyboard_revision_id, canonical_content_hash, bundle_manifest_hash,
             qualification_report_hash, qualification_report_object_id, renderer_profile_id,
             renderer_profile_version, qualification_profile_id, qualification_profile_version, revoked_approval_record_id)
            VALUES (?, ?, ?, 'shot_prompt_approved', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')
            """,
            (uuid.uuid4().hex, revision.revision_id, revision.artifact_id, reviewer, note or "", now_iso(), *evidence),
        )
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_approval_revoke_and_live_eligibility_lifecycle -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py tests/test_validators_approval_export.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/store.py ai_drama_runtime/services.py tests/test_shot_prompt_approval_lifecycle.py
git commit -m "feat: add shot prompt approval lifecycle"
```

### Task 30: Runtime Service Orchestration

**Depends on:** Task 18, Task 26, Task 29

**Files:**
- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_runtime/request.py`
- Modify: `ai_drama_runtime/runtime.py`
- Modify: `tests/test_shot_prompt_approval_lifecycle.py`
- Test: `tests/test_shot_prompt_approval_lifecycle.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_create_revision_stores_exact_canonical_bytes_and_skill_provenance -q`

**Design requirements covered:**
- Acceptance Criteria 1-2 and 38
- P06 canonical bytes, hash, and skill provenance

- [ ] **Step 1: Write the failing test**

```python
def test_create_revision_stores_exact_canonical_bytes_and_skill_provenance(tmp_path):
    package = load_skill_package(SHOT_PROMPT_SKILL_ROOT)
    with _shot_prompt_service(tmp_path) as service:
        source = _approved_storyboard_revision(service)
        result = service.create_shot_prompt_revision(package, source.revision_id, _authoring_json(), runtime="mock", model="mock-shot-prompt")
        stored_bytes = service.store.read_bytes_object(result.revision.content_object_id)
        canonical = parse_shot_prompt_json(stored_bytes)
        assert result.revision.content_hash == hashlib.sha256(stored_bytes).hexdigest()
        assert result.revision.skill_package_hash == package.content_hash
        assert result.revision.runtime_provider == "mock"
        assert result.revision.runtime_model == "mock-shot-prompt"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_create_revision_stores_exact_canonical_bytes_and_skill_provenance -q
```

Expected:

```text
FAIL because create_shot_prompt_revision is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def create_shot_prompt_revision(self, skill, source_storyboard_revision_id, authoring_json, runtime, model):
    source = self._revision_or_raise(source_storyboard_revision_id)
    artifact = self.store.ensure_shot_prompt_artifact(source.revision_id, source.project_id, source.chapter_id)
    canonical = parse_shot_prompt_json(authoring_json)
    validate_shot_prompt_canonical(canonical, profile="draft")
    canonical_bytes = serialize_shot_prompt_json(canonical)
    object_id = self.store.write_bytes_object(canonical_bytes)
    content_hash = self._sha256_bytes(canonical_bytes)
    run = self.store.create_run(
        artifact_id=artifact["artifact_id"], project_id=source.project_id, chapter_id=source.chapter_id,
        skill_id=skill.skill_id, skill_version=skill.version, skill_hash=skill.content_hash,
        runtime=runtime, provider=runtime, model=model or "", status="SUCCEEDED",
        request_object_id=self.store.write_text_object(authoring_json), response_object_id=object_id, input_hash=content_hash,
    )
    revision = self.store.insert_revision(
        artifact_id=artifact["artifact_id"], artifact_type="shot_prompt_set", project_id=source.project_id, chapter_id=source.chapter_id,
        run_id=run.run_id, skill_id=skill.skill_id, skill_version=skill.version, skill_package_hash=skill.content_hash,
        runtime_provider=runtime, runtime_model=model or "", content_object_id=object_id, content_hash=content_hash,
        raw_response_object_id=object_id, parser_version=CANONICAL_PARSER_VERSION, content_profile=CONTENT_PROFILE,
    )
    return RunResult(run=run, revision=revision, validation_results=[])
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py::test_create_revision_stores_exact_canonical_bytes_and_skill_provenance -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_runtime_lifecycle.py tests/test_storyboard_canonical_workflow.py tests/test_shot_prompt_approval_lifecycle.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/services.py ai_drama_runtime/request.py ai_drama_runtime/runtime.py tests/test_shot_prompt_approval_lifecycle.py
git commit -m "feat: orchestrate shot prompt runtime services"
```

### Task 31: CLI Surface

**Depends on:** Task 30

**Files:**
- Modify: `ai_drama_runtime/cli.py`
- Create: `tests/test_shot_prompt_cli.py`
- Test: `tests/test_shot_prompt_cli.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_cli.py -q`

**Design requirements covered:**
- Design Section 16 CLI surface
- P07 complete CLI surface

- [ ] **Step 1: Write the failing test**

```python
def test_shot_prompt_cli_surface_json_exit_codes_and_rejected_options(tmp_path):
    bad = _cli(tmp_path, "shot-prompts", "create-revision", "--source-storyboard-revision", "rev", "--asset-id", "asset", check=False)
    assert bad.returncode == 2
    created = _create_revision_via_cli(tmp_path)
    assert created["revision_id"]
    assert json.loads(_cli(tmp_path, "shot-prompts", "validate", "--profile", "draft", "--revision", created["revision_id"]).stdout)["status"] in {"PASS", "FAIL"}
    blocked = json.loads(_cli(tmp_path, "shot-prompts", "export-execution", "--revision", created["revision_id"], "--output", tmp_path / "exec").stdout)
    assert blocked["status"] == "BLOCKED"
    assert blocked["error_code"] == "EXPORT_NOT_EXECUTION_READY"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_cli.py::test_shot_prompt_cli_surface_json_exit_codes_and_rejected_options -q
```

Expected:

```text
FAIL because the shot-prompts parser does not exist
```

- [ ] **Step 3: Implement the minimal production change**

```python
shot_prompts = sub.add_parser("shot-prompts")
shot_sub = shot_prompts.add_subparsers(dest="shot_prompts_command", required=True)
for name, func in [
    ("create-revision", _shot_prompts_create_revision),
    ("validate", _shot_prompts_validate),
    ("render", _shot_prompts_render),
    ("validate-render", _shot_prompts_validate_render),
    ("materialize-bundle", _shot_prompts_materialize_bundle),
    ("check-integrity", _shot_prompts_check_integrity),
    ("review-open", _shot_prompts_review_open),
    ("review-event", _shot_prompts_review_event),
    ("review-status", _shot_prompts_review_status),
    ("qualify", _shot_prompts_qualify),
    ("approve", _shot_prompts_approve),
    ("reject", _shot_prompts_reject),
    ("revoke", _shot_prompts_revoke),
    ("eligibility", _shot_prompts_eligibility),
    ("export-formal", _shot_prompts_export_formal),
    ("export-diagnostic", _shot_prompts_export_diagnostic),
    ("export-execution", _shot_prompts_export_execution),
]:
    p = shot_sub.add_parser(name)
    p.set_defaults(func=func)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_cli.py::test_shot_prompt_cli_surface_json_exit_codes_and_rejected_options -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_cli.py tests/test_shot_prompt_cli.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/cli.py tests/test_shot_prompt_cli.py
git commit -m "feat: add shot prompt cli commands"
```

### Task 32: Skill Package

**Depends on:** Task 18

**Files:**
- Modify: `ai_drama_runtime/manifest.py`
- Create: `tests/test_shot_prompt_skill_package.py`
- Create: `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/skill.json`
- Create: `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/SKILL.md`
- Create: `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/README.md`
- Create: `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/contracts/shot-prompt-canonical-contract-v1.md`
- Create: `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/schemas/shot-prompt-canonical.schema.json`
- Create: `skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/validators/runtime_native.py`
- Test: `tests/test_shot_prompt_skill_package.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_skill_package.py tests/test_manifest.py -q`

**Design requirements covered:**
- P08 skill package plan
- Skill provenance and package hash

- [ ] **Step 1: Write the failing test**

```python
def test_shot_prompt_skill_package_matches_loader_and_declares_all_runtime_validators():
    package = load_skill_package(SHOT_PROMPT_SKILL_ROOT)
    assert package.skill_id == "ai-drama-shot-prompt-canonical-skill"
    assert package.execution_profiles[0]["profile_id"] == "shot-prompt-set-v1"
    validators = {item.validator_id: item for item in package.validators}
    assert set(SHOT_PROMPT_VALIDATORS) <= set(validators)
    for validator_id in SHOT_PROMPT_VALIDATORS:
        assert validators[validator_id].expected_exit_behavior == "runtime_native"
        assert validators[validator_id].entrypoint.name == "runtime_native.py"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_skill_package.py::test_shot_prompt_skill_package_matches_loader_and_declares_all_runtime_validators -q
```

Expected:

```text
FAIL because the Phase 3 skill package does not exist
```

- [ ] **Step 3: Implement the minimal production change**

```json
{
  "package_format_version": "1",
  "skill_id": "ai-drama-shot-prompt-canonical-skill",
  "version": "v0.1.0",
  "display_name": "AI Drama Shot Prompt Canonical Skill",
  "description": "Creates Phase 3 Shot Prompt Set canonical JSON from approved Storyboard revisions.",
  "package_status": "active",
  "instructions_entry": "SKILL.md",
  "context_files": ["README.md", "schemas/shot-prompt-canonical.schema.json", "contracts/shot-prompt-canonical-contract-v1.md"],
  "input_types": ["approved_storyboard_revision"],
  "output_types": ["shot_prompt_set_revision"],
  "schemas": ["schemas/shot-prompt-canonical.schema.json"],
  "contracts": ["contracts/shot-prompt-canonical-contract-v1.md"],
  "validator_support_files": [],
  "validators": [],
  "runtime_requirements": {"python": ">=3.9"},
  "dependency_requirements": [],
  "provenance": {"source": "phase_3_shot_prompt_canonical_foundation"},
  "execution_profiles": [
    {
      "profile_id": "shot-prompt-set-v1",
      "output_artifact_type": "shot_prompt_set_revision",
      "output_format": "json",
      "parser_version": "shot-prompt-canonical-json-v1",
      "required_schema_version": "shot-prompt-set-v1",
      "renderer_id": "shot-prompt-renderer",
      "renderer_version": "1.0.0",
      "qualification_profile_id": "shot-prompt-approval-qualification-v1",
      "qualification_profile_version": "1.0.0",
      "phase4_handoff": "PHASE4_NOT_AUTHORIZED"
    }
  ]
}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_skill_package.py::test_shot_prompt_skill_package_matches_loader_and_declares_all_runtime_validators -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_manifest.py tests/test_validator_inventory.py tests/test_shot_prompt_skill_package.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/manifest.py tests/test_shot_prompt_skill_package.py skills/ai-drama-shot-prompt-canonical-skill/v0.1.0
git commit -m "feat: add shot prompt canonical skill package"
```

### Task 33: End-To-End Phase 3 Flow

**Depends on:** Task 31, Task 32

**Files:**
- Create: `tests/test_shot_prompt_end_to_end.py`
- Test: `tests/test_shot_prompt_end_to_end.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_end_to_end.py -q`

**Design requirements covered:**
- Acceptance Criteria 1-39 integrated behavior
- H03 end-to-end naming and behavior

- [ ] **Step 1: Write the failing test**

```python
def test_end_to_end_happy_path_supersede_revoke_stale_tamper_and_eligibility(tmp_path):
    with _shot_prompt_service(tmp_path) as service:
        first = _create_render_bundle_qualify_approve(service)
        assert service.shot_prompt_phase4_eligibility(first.revision_id)["eligible"] is True
        second = _create_render_bundle_qualify_approve(service)
        assert service.store.get_revision(first.revision_id).approval_status == "superseded"
        service.revoke_shot_prompt_approval(second.revision_id, reviewer="qa", note="withdraw")
        assert service.shot_prompt_phase4_eligibility(second.revision_id)["eligible"] is False
        third = _create_render_bundle_qualify_approve(service)
        _make_source_stale(service, third.revision_id)
        assert service.shot_prompt_phase4_eligibility(third.revision_id)["reason"] == "SOURCE_STALE"
        fourth = _create_render_bundle_qualify_approve(service)
        _tamper_bundle(service, fourth.revision_id)
        assert service.shot_prompt_phase4_eligibility(fourth.revision_id)["reason"] == "BUNDLE_INTEGRITY_FAILED"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_end_to_end.py::test_end_to_end_happy_path_supersede_revoke_stale_tamper_and_eligibility -q
```

Expected:

```text
FAIL because one or more Phase 3 orchestration helpers are incomplete
```

- [ ] **Step 3: Implement the minimal production change**

```python
def shot_prompt_phase4_eligibility(self, revision_id):
    revision = self._revision_or_raise(revision_id)
    if revision.approval_status != "approved":
        return {"eligible": False, "reason": "REVISION_NOT_APPROVED"}
    if recursive_freshness_status(self.store, revision_id) != "FRESH":
        return {"eligible": False, "reason": "SOURCE_STALE"}
    try:
        check_shot_prompt_bundle_integrity(self.store, revision)
    except BundleError:
        return {"eligible": False, "reason": "BUNDLE_INTEGRITY_FAILED"}
    if self.open_blocking_shot_prompt_review_count(revision_id):
        return {"eligible": False, "reason": "OPEN_BLOCKING_REVIEW"}
    if not _approval_evidence_matches(self.store, revision):
        return {"eligible": False, "reason": "APPROVAL_EVIDENCE_MISMATCH"}
    return {"eligible": True, "reason": "ELIGIBLE"}
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_end_to_end.py::test_end_to_end_happy_path_supersede_revoke_stale_tamper_and_eligibility -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest tests/test_shot_prompt_end_to_end.py tests/test_cli.py tests/test_shot_prompt_cli.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_end_to_end.py ai_drama_runtime/services.py
git commit -m "test: add shot prompt end to end coverage"
```

### Task 34: Final Verifier And Verification Reports

**Depends on:** Task 33

**Files:**
- Modify: `tools/verify_phase3_shot_prompt_canonical_foundation.py`
- Modify: `tests/test_phase3_verifier.py`
- Create: `reports/phase3-shot-prompt-canonical-verification.json`
- Create: `reports/phase3-shot-prompt-canonical-verification.md`
- Test: `tests/test_phase3_verifier.py`
- Verify: `python3 tools/verify_phase3_shot_prompt_canonical_foundation.py --mode final --execution-start-commit <IMPLEMENTATION_AUTHORIZATION_COMMIT>`

**Design requirements covered:**
- P09 final verifier and verification report
- Final acceptance evidence

- [ ] **Step 1: Write the failing test**

```python
def test_final_verifier_runs_required_test_groups_and_writes_reports(monkeypatch, tmp_path):
    verifier = _load_verifier_module()
    calls = []
    monkeypatch.setattr(verifier, "_run", lambda args, **kwargs: _fake_success(args, calls))
    code = verifier.main(["--mode", "final", "--execution-start-commit", "abc123", "--report-json", str(tmp_path / "report.json"), "--report-md", str(tmp_path / "report.md")])
    assert code == 0
    command_text = "\n".join(" ".join(call) for call in calls)
    assert "tests/test_shot_prompt_store_migration.py" in command_text
    assert "tests/test_shot_prompt_end_to_end.py" in command_text
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.md").exists()
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m pytest tests/test_phase3_verifier.py::test_final_verifier_runs_required_test_groups_and_writes_reports -q
```

Expected:

```text
FAIL because reports are not written
```

- [ ] **Step 3: Implement the minimal production change**

```python
TEST_COMMANDS = [
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_store_migration.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_canonical_parser.py", "tests/test_shot_prompt_canonical_schema.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_validators.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_renderer.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_bundle.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_review_records.py", "tests/test_shot_prompt_approval_lifecycle.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_shot_prompt_cli.py", "tests/test_shot_prompt_skill_package.py", "-q"],
    [sys.executable, "-m", "pytest", "tests/test_cli.py", "tests/test_phase1_verifier.py", "tests/test_phase2_verifier.py", "-q"],
    [sys.executable, "-m", "pytest", "-q"],
]

def write_reports(results, args):
    payload = {"verifier_version": "1.0.0", "execution_start_commit": args.execution_start_commit, "results": [item.__dict__ for item in results], "no_phase4_execution": True}
    Path(args.report_json).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    Path(args.report_md).write_text("# Phase 3 Shot Prompt Canonical Verification\n\nstatus: %s\n" % ("PASS" if all(item.ok for item in results) else "FAIL"), encoding="utf-8")
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_phase3_verifier.py::test_final_verifier_runs_required_test_groups_and_writes_reports -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regression tests**

Run:

```bash
python3 -m pytest -q
python3 tools/verify_phase3_shot_prompt_canonical_foundation.py --mode portable
python3 tools/verify_phase3_shot_prompt_canonical_foundation.py --mode final --execution-start-commit <IMPLEMENTATION_AUTHORIZATION_COMMIT>
```

Expected:

```text
all selected tests pass
PHASE3_SHOT_PROMPT_CANONICAL_FOUNDATION: PASS
```

- [ ] **Step 6: Commit**

```bash
git add tools/verify_phase3_shot_prompt_canonical_foundation.py tests/test_phase3_verifier.py reports/phase3-shot-prompt-canonical-verification.json reports/phase3-shot-prompt-canonical-verification.md
git commit -m "test: add shot prompt final verification"
```

## Verification Matrix

| Criterion | Task | Test name | Validator ID | Service or CLI | Verification command | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| AC01 artifact identity | Task 2 | `test_artifact_business_key_migration_preserves_legacy_rows` | `shot_prompt_dependency_binding` | `RuntimeStore.ensure_shot_prompt_artifact` | `python3 -m pytest tests/test_shot_prompt_store_migration.py -q` | one source maps to one artifact |
| AC02 multiple Revisions | Task 33 | `test_end_to_end_happy_path_supersede_revoke_stale_tamper_and_eligibility` | `shot_prompt_source_eligibility` | `create_shot_prompt_revision` | `python3 -m pytest tests/test_shot_prompt_end_to_end.py -q` | same artifact has multiple revisions |
| AC03 set scope only | Task 9 | `test_root_renderer_lock_and_profile_validation` | `shot_prompt_forbidden_fields` | `shot-prompts validate` | `python3 -m pytest tests/test_shot_prompt_canonical_parser.py -q` | non-set scope rejected |
| AC04 renderer lock | Task 9, Task 19 | `test_renderer_registry_requires_exact_profile_and_merge_is_deterministic` | `shot_prompt_forbidden_fields` | `resolve_renderer` | `python3 -m pytest tests/test_shot_prompt_renderer.py -q` | exact profile/version required |
| AC05 root authority | Task 14 | `test_set_defaults_merge_policies_and_negative_boundaries` | `shot_prompt_forbidden_fields` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | root negative and asset authority rejected |
| AC06 draft shared-only | Task 9 | `test_root_renderer_lock_and_profile_validation` | `shot_prompt_modality_completeness` | `shot-prompts validate --profile draft` | `python3 -m pytest tests/test_shot_prompt_canonical_parser.py -q` | Draft PASS |
| AC07 formal shared-only | Task 9 | `test_root_renderer_lock_and_profile_validation` | `shot_prompt_modality_completeness` | `shot-prompts validate --profile formal` | `python3 -m pytest tests/test_shot_prompt_canonical_parser.py -q` | Formal FAIL |
| AC08 modality outputs | Task 10, Task 20 | `test_positive_prompt_rendering_matches_golden` | `shot_prompt_modality_completeness` | `render_positive_prompts` | `python3 -m pytest tests/test_shot_prompt_renderer.py -q` | image/video coverage matches intents |
| AC09 source binding | Task 15 | `test_source_eligibility_and_dependency_binding_persist_results` | `shot_prompt_dependency_binding` | `run_declared_validators` | `python3 -m pytest tests/test_shot_prompt_validators.py -q` | invalid source refs FAIL |
| AC10 shot identity | Task 10 | `test_shot_intents_validate_modality_outputs` | `shot_prompt_forbidden_fields` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | no duplicate source shot authority |
| AC11 empty asset slots | Task 13 | `test_asset_slot_schema_and_derived_slot_id` | `shot_prompt_asset_slots` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | no empty slot requirement |
| AC12 slot shot_id forbidden | Task 13 | `test_asset_slot_schema_and_derived_slot_id` | `shot_prompt_asset_slots` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | authored `shot_id` in slot rejected |
| AC13 one slot per entity | Task 13 | `test_asset_slot_schema_and_derived_slot_id` | `shot_prompt_asset_slots` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | duplicate slot FAIL |
| AC14 purpose enum | Task 13 | `test_asset_slot_schema_and_derived_slot_id` | `shot_prompt_asset_slots` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | small enum enforced |
| AC15 slot_id derived | Task 13, Task 22 | `test_asset_requirements_provenance_and_review_golden_outputs` | `shot_prompt_asset_slots` | `render_asset_requirements` | `python3 -m pytest tests/test_shot_prompt_renderer.py -q` | `slot_id` only in asset requirements |
| AC16 continuity requirement | Task 12 | `test_continuity_scope_and_specific_shot_direction` | `shot_prompt_continuity` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | required/optional and scopes enforced |
| AC17 continuity direction | Task 12 | `test_continuity_scope_and_specific_shot_direction` | `shot_prompt_continuity` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | no current/future specific shot |
| AC18 dialogue fields | Task 11, Task 16 | `test_dialogue_schema_requires_video_and_strict_fields` | `shot_prompt_dialogue_consistency` | `validate_shot_prompt_canonical` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | dialogue fields validated |
| AC19 dialogue coverage | Task 16 | `test_modality_and_dialogue_validators_persist_failures` | `shot_prompt_dialogue_coverage` | `run_declared_validators` | `python3 -m pytest tests/test_shot_prompt_validators.py -q` | strict video dialogue coverage |
| AC20 merge policies | Task 14 | `test_set_defaults_merge_policies_and_negative_boundaries` | `shot_prompt_forbidden_fields` | `merge_set_default` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | only three policies |
| AC21 append_dedup | Task 14 | `test_set_defaults_merge_policies_and_negative_boundaries` | `shot_prompt_forbidden_fields` | `append_dedup` | `python3 -m pytest tests/test_shot_prompt_canonical_schema.py -q` | NFC trim first occurrence |
| AC22 negative rendering | Task 21 | `test_negative_prompt_rendering_uses_explicit_constraints_and_invariants` | `shot_prompt_render_validation` | `render_negative_prompts` | `python3 -m pytest tests/test_shot_prompt_renderer.py -q` | explicit constraints plus invariants |
| AC23 language lint | Task 18 | `test_language_lint_and_high_risk_asset_warning_do_not_block` | `shot_prompt_language_consistency_lint` | `run_declared_validators` | `python3 -m pytest tests/test_shot_prompt_validators.py -q` | warning non-blocking |
| AC24 provenance | Task 22 | `test_asset_requirements_provenance_and_review_golden_outputs` | `shot_prompt_render_validation` | `render_provenance` | `python3 -m pytest tests/test_shot_prompt_renderer.py -q` | excluded hashes absent |
| AC25 validation report | Task 24 | `test_render_validation_checks_members_hashes_and_report_candidate` | `shot_prompt_render_validation` | `validate_shot_prompt_render` | `python3 -m pytest tests/test_shot_prompt_bundle.py -q` | report from orchestrator |
| AC26 no formal rows after render validation | Task 24 | `test_render_validation_checks_members_hashes_and_report_candidate` | `shot_prompt_render_validation` | `validate_shot_prompt_render` | `python3 -m pytest tests/test_shot_prompt_bundle.py -q` | no `revision_outputs` rows |
| AC27 atomicity | Task 25 | `test_bundle_materialization_inserts_all_rows_atomically` | `shot_prompt_bundle_integrity` | `materialize_shot_prompt_bundle` | `python3 -m pytest tests/test_shot_prompt_bundle.py -q` | failure leaves zero rows |
| AC28 conflicts | Task 26 | `test_bundle_integrity_detects_missing_extra_tampered_members` | `shot_prompt_bundle_integrity` | `check_shot_prompt_bundle_integrity` | `python3 -m pytest tests/test_shot_prompt_bundle.py -q` | partial/conflicting rows fail |
| AC29 output mapping | Task 3, Task 25 | `test_revision_outputs_rebuild_preserves_rows_and_adds_phase3_types` | `shot_prompt_bundle_integrity` | `RuntimeStore.revision_outputs` | `python3 -m pytest tests/test_shot_prompt_store_migration.py -q` | exact logical types |
| AC30 canonical source member | Task 25 | `test_bundle_materialization_inserts_all_rows_atomically` | `shot_prompt_bundle_integrity` | `build_bundle_manifest` | `python3 -m pytest tests/test_shot_prompt_bundle.py -q` | no canonical output row |
| AC31 qualification outside bundle | Task 28 | `test_qualification_report_is_deterministic_and_outside_bundle` | `shot_prompt_approval_qualification` | `qualify_shot_prompt_revision` | `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py -q` | no output row or manifest member |
| AC32 four layers | Task 24, Task 26, Task 28 | `test_qualification_report_is_deterministic_and_outside_bundle` | `shot_prompt_approval_qualification` | validation/render/integrity/qualification services | `python3 -m pytest tests/test_shot_prompt_bundle.py tests/test_shot_prompt_approval_lifecycle.py -q` | independent failure evidence |
| AC33 review blocking | Task 27, Task 28 | `test_review_events_compute_current_status_by_created_at_and_event_id` | `shot_prompt_approval_qualification` | `open_blocking_shot_prompt_review_count` | `python3 -m pytest tests/test_shot_prompt_review_records.py -q` | open blocking review blocks qualification |
| AC34 event ordering | Task 27 | `test_review_events_compute_current_status_by_created_at_and_event_id` | none | `shot_prompt_review_status` | `python3 -m pytest tests/test_shot_prompt_review_records.py -q` | `(created_at,event_id)` ordering |
| AC35 supersession | Task 29, Task 33 | `test_end_to_end_happy_path_supersede_revoke_stale_tamper_and_eligibility` | `shot_prompt_approval_qualification` | `approve_shot_prompt_revision` | `python3 -m pytest tests/test_shot_prompt_end_to_end.py -q` | old approved superseded |
| AC36 revocation | Task 29 | `test_approval_revoke_and_live_eligibility_lifecycle` | none | `revoke_shot_prompt_approval` | `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py -q` | status revoked and revoke record |
| AC37 approval evidence | Task 29 | `test_approval_revoke_and_live_eligibility_lifecycle` | `shot_prompt_approval_qualification` | `approve_shot_prompt_revision` | `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py -q` | evidence columns populated |
| AC38 schema injection | Task 30 | `test_create_revision_stores_exact_canonical_bytes_and_skill_provenance` | `shot_prompt_forbidden_fields` | `create_shot_prompt_revision` | `python3 -m pytest tests/test_shot_prompt_approval_lifecycle.py -q` | stored bytes are exact canonical bytes |
| AC39 live eligibility | Task 29, Task 33 | `test_end_to_end_happy_path_supersede_revoke_stale_tamper_and_eligibility` | `shot_prompt_bundle_integrity` | `shot_prompt_phase4_eligibility` | `python3 -m pytest tests/test_shot_prompt_end_to_end.py -q` | stale or tamper makes ineligible |
| Migration legacy replay | Task 7 | `test_phase3_migration_apply_replay_and_rollback` | none | `apply_phase3_store_migration` | `python3 -m pytest tests/test_shot_prompt_store_migration.py -q` | idempotent replay and rollback |
| Candidate object contract | Task 23 | `test_render_writes_candidate_objects_without_revision_outputs` | `shot_prompt_render_validation` | `render_shot_prompt_candidates` | `python3 -m pytest tests/test_shot_prompt_bundle.py -q` | candidate metadata complete |
| CLI complete surface | Task 31 | `test_shot_prompt_cli_surface_json_exit_codes_and_rejected_options` | multiple | `shot-prompts ...` | `python3 -m pytest tests/test_shot_prompt_cli.py -q` | explicit commands and rejected inputs |
| Skill package consistency | Task 32 | `test_shot_prompt_skill_package_matches_loader_and_declares_all_runtime_validators` | all Phase 3 validators | `load_skill_package` | `python3 -m pytest tests/test_shot_prompt_skill_package.py -q` | package hash and declarations consistent |
| Portable/final verifier | Task 34 | `test_final_verifier_runs_required_test_groups_and_writes_reports` | none | verifier script | `python3 -m pytest tests/test_phase3_verifier.py -q` | portable/final reports written |

## Boundary Check

- Phase 3 v1 defines no platform adapter.
- Phase 3 v1 defines no external `asset_id` binding, URL binding, filesystem path binding, or upload ID binding.
- Phase 3 v1 defines no waiver mechanics.
- Phase 3 v1 defines no Hard/Soft Rule Registry.
- Phase 3 v1 defines no Cross-Revision Review Resolution.
- Phase 3 v1 defines no partial selector, partial set approval, exact timecode contract, generation run, or Execution DAG.
- Execution export is blocked and audited through `shot-prompts export-execution`; it does not produce an execution package.

## Self-Review

- P01 fixed: Source Baseline separates Design Approval Baseline, Implementation Plan Baseline, and runtime-supplied Future Implementation Start Commit; verifier final mode requires the explicit parameter and has allowlist, protected files, branch, clean tree, ancestor, pytest, report, JSON/text output, and exit-code behavior.
- P02 fixed: migration tasks use SQLite inventory, deterministic preview, real table rebuild order, FK check, idempotent apply, rollback, and Store reopen tests.
- P03 fixed: canonical, validator, and renderer work is split into parser, root, intent, dialogue, continuity, asset, negative/default, validator groups, and renderer output tasks.
- P04 fixed: candidate objects, render validation, validation report, bundle materialization, and integrity are separate contracts and tasks.
- P05 fixed: review, qualification, approval, rejection, revocation, supersession, and eligibility are separate tasks; revoke evidence no longer requires qualification evidence.
- P06 fixed: create Revision writes exact deterministic canonical bytes and hashes the same bytes; skill provenance comes from the loader and no empty provider/model placeholders are used.
- P07 fixed: full `shot-prompts` CLI surface is listed and tested with JSON stdout, stderr, exit code, Store side effects, execution export blocking, and rejected v1 options.
- P08 fixed: skill package task follows the actual loader shape with top-level `execution_profiles`, real validator entrypoint files, declared runtime-native validators, schema, contract, and package hash.
- P09 fixed: final verifier executes tests, static checks, allowlist, protected-file checks, Phase 4 leakage scan, and writes deterministic reports without self-referential final HEAD requirements.
- H01 fixed: task dependencies and Mermaid graph match; shared-file writer order is numeric and parallel rules forbid simultaneous writes to a shared file.
- H02 fixed: dependency direction is frozen with no `validators.py -> services.py` import.
- H03 fixed: end-to-end test name covers approval, revoke, supersession, source stale, bundle tamper, and live eligibility.
- Undefined symbol review: every code snippet references symbols defined in the same task or an earlier task.
- Placeholder review: the plan contains no placeholder markers.
- Scope review: the File Map, Task Files, Verifier Allowlist, Protected Files, Commit Strategy, and Verification Matrix are aligned.

## Execution Handoff

Plan revision is saved to `docs/superpowers/plans/2026-07-02-phase3-shot-prompt-canonical-implementation.md`.

Future implementation remains blocked until user review explicitly changes authorization state.

Final state remains:

```text
IMPLEMENTATION_PLAN_PENDING_USER_REVIEW
IMPLEMENTATION_NOT_AUTHORIZED
PHASE4_NOT_AUTHORIZED
```
