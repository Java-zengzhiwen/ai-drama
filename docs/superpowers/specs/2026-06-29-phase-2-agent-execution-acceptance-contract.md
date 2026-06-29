# Phase 2 Minimal Bundle Foundation Agent Execution & Acceptance Contract

## 1. Status

```text
Design Status: APPROVED AND FROZEN
Contract Status: APPROVED AND FROZEN
Implementation Planning: AUTHORIZED
Implementation: NOT AUTHORIZED
```

This document freezes the execution contract for Phase 2 bundle foundation work. It does not authorize implementation.

---

## 2. Purpose

This contract constrains a later Codex run so it can implement the frozen Phase 2 design with minimal human back-and-forth, while staying inside the narrow bundle-only scope and preserving Phase 1 behavior.

Execution sequence:

```text
Context Loading
→ Repository Analysis
→ Clarification Check
→ Implementation Plan
→ Test-First Execution
→ Self-Repair
→ Independent Agent Review
→ Deterministic Verification
→ Commit and Push
```

This document does not redesign the foundation. It only freezes the acceptance rules for the Phase 2 minimal bundle layer.

---

## 3. Authority Hierarchy

If conflicts arise, use this order:

1. Frozen Foundation Design
2. Frozen Phase 2 Design
3. Frozen Phase 2 Agent Execution & Acceptance Contract
4. AGENTS.md
5. approved Phase 2 Implementation Plan
6. repository code at Execution Start Commit
7. Phase 1 supporting documents
8. Codex engineering judgment

Rules:

- do not modify frozen documents to fit implementation preferences;
- no Phase 2 document may override the frozen Foundation;
- do not reconsider frozen Phase 1 decisions;
- any ambiguity not resolved here must be treated as a contract defect, not a justification to expand scope;
- the Implementation Plan may map frozen requirements to tasks and files, but may not define new schema, hash, CLI, error, migration, provenance, or lifecycle semantics.

---

## 4. Frozen Baseline

### Repository

```text
Repository: Java-zengzhiwen/ai-drama
Branch: test/phase2-minimal-bundle-foundation
Foundation Baseline Commit: d9f13967d90ae0b2829c3182dd0aebe85c495daf
```

### Preparation Commit Sequence

```text
Phase 1 Final Baseline
d9f13967d90ae0b2829c3182dd0aebe85c495daf

→ Phase 2 Design Baseline Commit
f933182a3db4b3f03de31b4241da29e5be9e3fdd
containing only the two approved Phase 2 specification files

→ Phase 2 Planning Baseline Commit
containing exactly:
- tests/acceptance/test_storyboard_workflow_acceptance.py
- docs/superpowers/specs/2026-06-29-phase-2-agent-execution-acceptance-contract.md

→ Phase 2 Execution Start Commit
adding only:
- docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md
```

### Existing Test Baseline

```text
python3 -m pytest -q
Expected baseline: 135 passed
```

Before implementation starts, the following must be true:

```bash
git rev-parse HEAD
git branch --show-current
git status --short
python3 -m pytest -q
```

Conditions:

1. `HEAD` must equal the execution start commit supplied by the launch prompt.
2. `d9f13967d90ae0b2829c3182dd0aebe85c495daf` must be an ancestor of `HEAD`.
3. `f933182a3db4b3f03de31b4241da29e5be9e3fdd` must be an ancestor of `HEAD`.
4. The launch prompt identifies the exact Phase 2 Planning Baseline.
5. The diff from Design Baseline to Planning Baseline contains exactly the two portability-correction files.
6. The diff from Planning Baseline to Execution Start Commit contains exactly the approved Implementation Plan.
7. The working tree must be clean.
8. The baseline test suite must report `135 passed`.

If any condition fails, stop and report.

---

## 5. Phase 2 Goal

The only business goal is:

```text
Add minimal bundle persistence and atomic export on top of canonical Storyboard revisions
without introducing a separate bundle-export table or Phase 3 execution machinery.
```

Final authority relationship:

```text
revision.content_object_id
= canonical Storyboard JSON authority

revision_outputs
= derived bundle-member persistence

export_records
= unified export audit trail
```

Phase 2 must support:

1. `revision_outputs` for Storyboard bundle members;
2. deterministic `rendered_markdown` and `bundle_manifest` outputs;
3. bundle materialization compatibility for `v0.2.0` and `v0.2.1`;
4. bundle integrity validation;
5. atomic formal-review, diagnostic, and blocked execution export semantics;
6. unified export audit tracking.

Historical `v0.2.0` revisions use live Runtime Service bundle integrity checks during materialization, approval, and export. They are not mutated and do not require backfilled declared-validator `ValidationResult` rows.

`v0.2.1` revisions persist the declared required `storyboard_bundle_integrity` `ValidationResult` during normal creation.

---

## 6. In Scope

### 6.1 Schema and migration

- `revision_outputs` additive schema and migration.
- `export_records` additive metadata columns.
- backfill rules for legacy exports.
- additive-only changes to support bundle persistence.

### 6.2 Materialization

- Storyboard output materialization.
- `v0.2.1` auto-materialization before validation.
- explicit `materialize-bundle` for historical `v0.2.0` revisions.
- zero-row creation, already-materialized, and conflict handling.

### 6.3 Bundle integrity

- `storyboard_bundle_integrity` runtime-native checker.
- runtime service checker for historical revisions.
- allowed-output verification, hash verification, renderer verification, manifest verification.

### 6.4 Export

- formal-review bundle export.
- diagnostic bundle export.
- blocked execution export record.
- atomic output staging and rename.
- no separate export-table design.

### 6.5 CLI and verifier

- bundle CLI commands.
- unified Phase 2 verifier.
- preflight / portable / final modes.
- changed-file allowlist checks.

### 6.6 Execution model

- Main Agent is the sole writer.
- Agents A-F are read-only.
- Agent A: Repository Mapper.
- Agent B: Schema & Migration Reviewer.
- Agent C: Manifest & Hash Reviewer.
- Agent D: Atomic Export Reviewer.
- Agent E: Final Contract Reviewer.
- Agent F: Adversarial Tester.
- test-first implementation.
- green vertical-slice commits only.
- no red intermediate commit.
- Agents E and F run after implementation and before final acceptance.

---

## 7. Out of Scope

- Shot Prompt Canonical.
- Shot-to-Unit generation.
- positive/negative prompt generation.
- asset binding.
- `bind-assets`.
- asset registry.
- approval inheritance.
- execution planning.
- target adapters.
- LibTV.
- Agnes.
- `execution_ready=true` as a real execution state.
- web UI.
- remote API.
- unrelated refactors.

---

## 8. Protected Decisions

### 8.1 Skill version strategy

- `v0.1.0` is read-only.
- `v0.2.0` is read-only.
- `v0.2.1` is added.
- `v0.2.1` uses the same `storyboard-canonical-v1` profile, schema, renderer ID, and renderer version.
- `v0.2.1` declares required runtime-native `storyboard_bundle_integrity`.
- do not mutate `v0.2.0`.

### 8.2 Materialization compatibility

- `v0.2.1` revisions auto-materialize before validation.
- the canonical Revision may remain persisted.
- `approval_status` remains pending.
- the Run becomes `VALIDATION_FAILED`.
- the failed DB output transaction leaves zero `revision_outputs` rows.
- no automatic retry.
- no automatic approval.
- explicit `materialize-bundle` may repair later.
- transaction failure uses `BUNDLE_NOT_MATERIALIZED`.
- pre-existing partial or conflicting rows use `BUNDLE_OUTPUT_CONFLICT`.
- historical `v0.2.0` revisions require explicit `materialize-bundle`.
- zero rows create both outputs in one DB transaction.
- exact complete rows return `ALREADY_MATERIALIZED`.
- no revision rewrite, output overwrite, approval change, or auto-approval.

### 8.3 Hash separation

- `bundle_manifest_hash` is the business hash.
- it excludes `revision_id` and `bundle_manifest_hash`.
- `revision_outputs.content_hash` is the exact full object-byte hash.
- these hashes are not required to be equal.
- manifest outputs excludes `bundle_manifest` itself.

### 8.4 Export-record semantics

- `export_records.content_hash` remains `revision.content_hash`.
- `export_records.bundle_manifest_hash` stores the business manifest hash.
- blocked execution attempts store requested destination, canonical content hash, manifest hash, provenance, and error code.
- `export-provenance.json` is not `revision_outputs`.
- `export-provenance.json` is not included in Bundle Manifest.
- `export-provenance.json` is not included in `bundle_manifest_hash`.

### 8.5 Approval compatibility

- existing approved Phase 1 revisions are not retroactively revoked.
- future approvals of canonical Storyboard revisions, including old unapproved `v0.2.0` revisions, require materialized bundle integrity `PASS`.
- formal-review export of previously approved revisions also requires materialization and bundle integrity `PASS`.

### 8.6 Bundle integrity architecture

- declared required runtime-native validator in `v0.2.1`.
- also exposed as a Runtime service checker for historical `v0.2.0` materialization, approval, and export.
- do not mutate `v0.2.0`.

### 8.7 Transaction boundary

- immutable objects may be written before the SQLite transaction.
- both `revision_outputs` rows are inserted in one DB transaction.
- a failed DB transaction leaves zero output rows.
- unreferenced object-store blobs are tolerated.
- no object GC in Phase 2.

### 8.8 Atomic export

- no `--force` option in Phase 2.
- an existing final destination fails with `EXPORT_DESTINATION_EXISTS`.
- staging must be on the same filesystem.
- `bundle-manifest.json` is written last.
- rename is performed last.
- any failure removes staging and leaves no partial final directory.
- execution export never implicitly materializes.
- execution export never performs filesystem staging.
- execution export never writes a final directory regardless of bundle state.
- if a verified bundle exists, execution export stores `bundle_manifest_hash` and `bundle_status=verified`.
- if missing, execution export stores `bundle_manifest_hash=""` and `bundle_status=not_materialized`.
- if invalid, execution export stores `bundle_manifest_hash=""` and `bundle_status=invalid`.
- provenance records `bundle_status`.

### 8.9 Exact export gates

- formal-review: approved + FRESH + validators PASS + bundle integrity PASS.
- diagnostic: explicit + STALE + bundle integrity PASS.
- diagnostic on a FRESH revision fails closed.
- diagnostic export itself may succeed when its export gates pass.
- execution: always blocked, records the attempt, creates no directory, returns `EXPORT_NOT_EXECUTION_READY`.
- formal-review `BUNDLE_NOT_MATERIALIZED` means the formal-review bundle does not exist.
- formal-review `BUNDLE_INTEGRITY_FAILED` means the bundle exists but integrity verification fails.
- `FORMAL_REVIEW_EXPORT_BLOCKED` means the revision is unapproved, STALE, or another required non-bundle validator has not passed.
- approval without bundle integrity PASS fails with `BUNDLE_NOT_MATERIALIZED` or `BUNDLE_INTEGRITY_FAILED`.
- approval never performs implicit materialization.
- already-approved revisions remain approved.
- the dependency-creation entrypoint must reject any attempt to use a diagnostic export record as a dependency parent, returning `DIAGNOSTIC_EXPORT_NOT_PARENTABLE`.

### 8.10 Exact CLI contracts

- `ai-drama artifacts outputs --revision REVISION_ID`
- `ai-drama artifacts materialize-bundle --revision REVISION_ID`
- `ai-drama artifacts export-bundle --revision REVISION_ID --kind formal-review|diagnostic|execution --output OUTPUT_DIR`
- each command returns a frozen JSON response contract that is frozen here and not deferred to the Implementation Plan.

#### `artifacts outputs` success

```json
{
  "revision_id": "REVISION_ID",
  "artifact_type": "storyboard",
  "content_profile": "storyboard-canonical-v1",
  "materialization_status": "NOT_MATERIALIZED|MATERIALIZED|CONFLICT",
  "bundle_integrity": "PASS|FAIL|NOT_CHECKED",
  "bundle_manifest_hash": "",
  "outputs": [
    {
      "revision_output_id": "OUTPUT_ID",
      "logical_type": "rendered_markdown|bundle_manifest",
      "object_id": "SHA256",
      "content_hash": "SHA256",
      "media_type": "MEDIA_TYPE",
      "generator": "GENERATOR",
      "generator_version": "VERSION",
      "created_at": "TIMESTAMP"
    }
  ]
}
```

#### `artifacts materialize-bundle` success

```json
{
  "status": "MATERIALIZED|ALREADY_MATERIALIZED",
  "revision_id": "REVISION_ID",
  "rendered_markdown_output_id": "OUTPUT_ID",
  "bundle_manifest_output_id": "OUTPUT_ID",
  "bundle_manifest_hash": "SHA256",
  "bundle_integrity": "PASS",
  "approval_status": "pending|approved|rejected|superseded"
}
```

#### `artifacts export-bundle` success

```json
{
  "status": "EXPORTED",
  "export_id": "EXPORT_ID",
  "revision_id": "REVISION_ID",
  "export_kind": "formal_review|diagnostic",
  "destination": "OUTPUT_DIR",
  "bundle_manifest_hash": "SHA256",
  "freshness_status": "FRESH|STALE",
  "diagnostic_only": false,
  "not_an_execution_package": true,
  "execution_ready": false
}
```

For diagnostic export, `diagnostic_only=true`.

#### `artifacts export-bundle` blocked execution

```json
{
  "status": "BLOCKED",
  "export_id": "EXPORT_ID",
  "revision_id": "REVISION_ID",
  "export_kind": "execution",
  "bundle_status": "verified|not_materialized|invalid",
  "bundle_manifest_hash": "",
  "error_code": "EXPORT_NOT_EXECUTION_READY",
  "error_message": "..."
}
```

When `bundle_status=verified`, `bundle_manifest_hash` contains the verified business manifest hash.

Preserve the existing global CLI exit-code classes.

### 8.11 Exact output metadata

- `rendered_markdown`
  - `media_type=text/markdown`
  - `generator=storyboard-canonical-markdown-renderer`
  - `generator_version=1.0.0`
  - exact deterministic renderer bytes
- `bundle_manifest`
  - `media_type=application/json`
  - `generator=bundle-manifest-builder`
  - `generator_version=1`
  - canonical-json-v1 full bytes
  - no trailing newline

### 8.12 Bundle Manifest v1 schema

Business hash preimage:

```json
{
  "schema_version": "bundle-manifest-v1",
  "artifact_type": "storyboard",
  "canonical_content_hash": "SHA256",
  "outputs": [
    {
      "logical_type": "rendered_markdown",
      "content_hash": "SHA256",
      "media_type": "text/markdown",
      "generator": "storyboard-canonical-markdown-renderer",
      "generator_version": "1.0.0"
    }
  ]
}
```

Rules:

- `schema_version` is exactly `bundle-manifest-v1`.
- the manifest is stored as canonical-json-v1 bytes with no trailing newline.
- the manifest business hash is SHA-256 over the canonical-json-v1 bytes of the business-hash preimage.
- `revision_id` and `bundle_manifest_hash` are present only in the full stored manifest, not in the business preimage.
- `outputs` is sorted by `logical_type`.
- `outputs` excludes `bundle_manifest` itself.
- `canonical_content_hash` points to `revision.content_hash`.
- `export-provenance.json` is not `revision_outputs`.
- `export-provenance.json` is not included in the Bundle Manifest.
- `export-provenance.json` is not included in `bundle_manifest_hash`.

### 8.13 Object-store identity

- `object_id = SHA256(exact bytes)`.
- `content_hash = SHA256(exact bytes)`.
- valid rows therefore have `object_id == content_hash`.

---

## 9. Exact Database Contracts

### 9.1 `revision_outputs`

Allowed columns:

- `revision_output_id`
- `revision_id`
- `logical_type`
- `object_id`
- `content_hash`
- `media_type`
- `generator`
- `generator_version`
- `created_at`

Constraints:

- `revision_output_id TEXT PRIMARY KEY`
- `revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT`
- `logical_type TEXT NOT NULL CHECK (logical_type IN ('rendered_positive_prompt', 'rendered_negative_prompt', 'rendered_markdown', 'bundle_manifest'))`
- `object_id TEXT NOT NULL`
- `content_hash TEXT NOT NULL`
- `media_type TEXT NOT NULL`
- `generator TEXT NOT NULL`
- `generator_version TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `UNIQUE(revision_id, logical_type)`
- normal business flow forbids UPDATE and DELETE
- `revision_outputs_content_hash_idx` on `content_hash`
- `revision_outputs_object_id_idx` on `object_id`

Database logical_type CHECK contains exactly:

- `rendered_positive_prompt`
- `rendered_negative_prompt`
- `rendered_markdown`
- `bundle_manifest`

Application-level Storyboard legal outputs are exactly:

- `rendered_markdown`
- `bundle_manifest`

Application-level Storyboard mapping rules:

- `rendered_markdown` uses `media_type=text/markdown`, `generator=storyboard-canonical-markdown-renderer`, `generator_version=1.0.0`.
- `bundle_manifest` uses `media_type=application/json`, `generator=bundle-manifest-builder`, `generator_version=1`.
- `object_id` equals `content_hash` for valid stored rows.

### 9.2 `export_records`

Existing columns remain, plus additive columns:

- `export_kind TEXT NOT NULL DEFAULT 'legacy_single' CHECK (export_kind IN ('legacy_single', 'formal_review', 'diagnostic', 'execution'))`
- `freshness_status TEXT NOT NULL DEFAULT '' CHECK (freshness_status IN ('', 'FRESH', 'STALE'))`
- `diagnostic_only INTEGER NOT NULL DEFAULT 0 CHECK (diagnostic_only IN (0, 1))`
- `not_an_execution_package INTEGER NOT NULL DEFAULT 1 CHECK (not_an_execution_package IN (0, 1))`
- `execution_ready INTEGER NOT NULL DEFAULT 0 CHECK (execution_ready IN (0, 1))`
- `bundle_manifest_hash TEXT NOT NULL DEFAULT ''`
- `error_code TEXT NOT NULL DEFAULT ''`

Backfill legacy rows conservatively:

- `export_kind = legacy_single`
- `diagnostic_only = 0`
- `not_an_execution_package = 1`
- `execution_ready = 0`
- `freshness_status = ''`
- `bundle_manifest_hash = ''`
- `error_code = ''`

Semantics:

- `export_records.content_hash` remains `revision.content_hash`.
- `export_records.bundle_manifest_hash` stores the business manifest hash.
- export records for blocked execution attempts must still persist requested destination, canonical content hash, bundle manifest hash, provenance object reference, and error code.
- execution export records must persist `bundle_status` in provenance and use `EXPORT_NOT_EXECUTION_READY`.
- migration is idempotent.
- reopening an already migrated database must not change or duplicate schema state.

---

## 10. Stop Conditions

Implementation must stop and report if any of the following occur:

1. The branch or baseline checks fail.
2. The runtime needs a new table for bundle export audit.
3. The implementation requires mutating `v0.2.0` skill metadata or validator declarations.
4. The design would require changing the frozen Phase 1 docs.
5. The implementation would need to auto-approve or auto-promote a bundle revision.
6. The implementation would need to add `execution_ready=true` as a real execution state.
7. The implementation would need to weaken the changed-file allowlist or verifier gates.
8. The implementation would need to introduce any Phase 3 execution machinery.
9. The implementation would need to deviate from the frozen error-code matrix below.

## 11. Stable Error-Code Matrix

| Code | Exact trigger |
|---|---|
| `BUNDLE_PROFILE_UNSUPPORTED` | the requested revision or skill profile is not one of the frozen bundle-capable Storyboard profiles |
| `BUNDLE_NOT_MATERIALIZED` | approval or export requires a bundle but no valid bundle outputs exist |
| `BUNDLE_OUTPUT_CONFLICT` | materialization finds partial rows, wrong output types, or rows that do not match the expected bundle membership |
| `BUNDLE_INTEGRITY_FAILED` | allowed outputs exist but output hashes, renderer bytes, renderer metadata, or manifest contents/hashes fail verification |
| `REVISION_OUTPUT_HASH_MISMATCH` | a stored revision output row’s object hash does not match the exact object bytes |
| `REVISION_OUTPUT_COMBINATION_INVALID` | the stored output set is legal in isolation but not a legal Storyboard bundle combination |
| `EXPORT_DESTINATION_EXISTS` | final export destination already exists |
| `FORMAL_REVIEW_EXPORT_BLOCKED` | the revision is unapproved, STALE, or another required non-bundle validator has not passed |
| `DIAGNOSTIC_EXPORT_REQUIRES_STALE` | a diagnostic export is requested for a revision that is not STALE |
| `DIAGNOSTIC_EXPORT_NOT_PARENTABLE` | a dependency-creation entrypoint attempts to use a diagnostic export record as a dependency parent |
| `EXPORT_NOT_EXECUTION_READY` | execution export is requested; it is always blocked and records the attempt |

---

## 12. Verifier and Test Strategy

### 12.1 Verifier modes

- `preflight`
  - branch
  - exact baseline ancestry
  - clean tree
  - baseline test count
- `portable`
  - pytest-only verification
  - no git-state assertions
- `final`
  - branch recheck
  - ancestry recheck
  - clean-tree recheck
  - `git diff --check`
  - full suite
  - final gate
  - enforce changed-file allowlist identical to the approved Implementation Plan

### 12.2 Test strategy

- positive materialization tests
- negative and adversarial bundle integrity tests
- migration tests for schema and export backfill
- atomic export tests for staging and rename behavior
- CLI tests for the exact contracts
- verifier tests for all modes and allowlist checks
- adversarial bundle-integrity and export-blocking tests
- materialization repair tests

---

## 13. Acceptance Matrix

| acceptance_id | requirement | evidence_or_test | expected_result | symbolic_error_code | verifier_mode |
|---|---|---|---|---|---|
| P2-001 | verify baseline branch, baseline commit, and clean-tree preflight | git preflight checks | pass | N/A | preflight |
| P2-002 | verify baseline test count is 135 passed before implementation | `python3 -m pytest -q` | `135 passed` | N/A | preflight |
| P2-003 | verify the Phase 2 design/contract baseline contains only the two draft docs | git diff name-only against Phase 1 baseline | only the two spec files | N/A | preflight |
| P2-004 | verify the Planning Baseline contains exactly the two authorized verification-portability files and the Execution Start Commit adds only the approved Implementation Plan | two git diff name-only checks: Design Baseline..Planning Baseline and Planning Baseline..Execution Start Commit | exact corrective pair followed by exact plan file | N/A | preflight |
| P2-005 | verify the final verifier checks the exact changed-file allowlist | final verifier allowlist check | allowlist match | N/A | final |
| P2-006 | RESERVED | N/A | RESERVED | N/A | N/A |
| P2-007 | RESERVED | N/A | RESERVED | N/A | N/A |
| P2-008 | RESERVED | N/A | RESERVED | N/A | N/A |
| P2-009 | RESERVED | N/A | RESERVED | N/A | N/A |
| P2-010 | `revision_outputs` schema exists with frozen columns | schema introspection | columns present | N/A | final |
| P2-011 | `revision_outputs` logical_type CHECK contains the frozen enum | DDL inspection | exact CHECK values | N/A | final |
| P2-012 | Storyboard legal outputs are exactly `rendered_markdown` and `bundle_manifest` | schema and service tests | exact legal outputs | N/A | final |
| P2-013 | `revision_outputs.object_id` and `content_hash` identity rules are enforced | materialization and hash tests | equal on valid rows | N/A | final |
| P2-014 | `rendered_markdown` metadata is frozen exactly | output row tests | exact metadata | N/A | final |
| P2-015 | `bundle_manifest` metadata is frozen exactly | output row tests | exact metadata | N/A | final |
| P2-016 | `revision_outputs` rows are append-only and update/delete are rejected | mutation tests | rejects mutation | N/A | final |
| P2-017 | migration preserves existing revisions and legacy exports | migration tests | no data loss | N/A | final |
| P2-018 | revision output backfill path creates no bundle table drift | migration replay tests | idempotent replay | N/A | final |
| P2-019 | schema verification rejects missing constraints and wrong types | negative migration tests | reject invalid schema | N/A | final |
| P2-020 | `v0.2.1` auto-materializes before validation and failure lifecycle is pending/VALIDATION_FAILED/BUNDLE_NOT_MATERIALIZED | run creation tests | auto-materialized bundle or pending failure state | BUNDLE_NOT_MATERIALIZED | final |
| P2-021 | historical `v0.2.0` requires explicit `materialize-bundle` | CLI and service tests | explicit materialize required | BUNDLE_NOT_MATERIALIZED | final |
| P2-022 | zero rows create both outputs transactionally | materialization tests | two rows created | N/A | final |
| P2-023 | exact complete rows return `ALREADY_MATERIALIZED` | repeated materialization test | already-materialized status | N/A | final |
| P2-024 | partial rows return `BUNDLE_OUTPUT_CONFLICT` | conflict tests | conflict rejected | BUNDLE_OUTPUT_CONFLICT | final |
| P2-025 | conflicting rows return `BUNDLE_OUTPUT_CONFLICT` | conflict tests | conflict rejected | BUNDLE_OUTPUT_CONFLICT | final |
| P2-026 | failed transaction leaves zero `revision_outputs` rows and Run becomes `VALIDATION_FAILED` | failure injection test | zero persisted rows and failed run | BUNDLE_NOT_MATERIALIZED | final |
| P2-027 | no revision rewrite occurs during materialization | immutability tests | revision unchanged | N/A | final |
| P2-028 | no output overwrite occurs during materialization | overwrite tests | no overwrite | N/A | final |
| P2-029 | no auto-retry and no auto-approval occur during materialization | materialization lifecycle tests | no retry and no approval | N/A | final |
| P2-030 | bundle manifest business hash excludes `revision_id` | hash tests | stable business hash | N/A | final |
| P2-031 | bundle manifest business hash excludes self hash | hash tests | stable business hash | N/A | final |
| P2-032 | `bundle_manifest` output is excluded from business hash inputs | manifest hash tests | business hash stable | N/A | final |
| P2-033 | manifest full stored bytes are canonical-json-v1 without trailing newline | byte-for-byte tests | exact bytes | N/A | final |
| P2-034 | `bundle_manifest_hash` is the business hash, not the full object-byte hash | hash separation tests | hashes differ only by definition | N/A | final |
| P2-035 | `revision_outputs.content_hash` equals exact full object bytes | object-store hash tests | exact byte hash | N/A | final |
| P2-036 | `object_id == content_hash` on valid rows | storage tests | equal hashes | N/A | final |
| P2-037 | manifest outputs are sorted by `logical_type` | manifest tests | deterministic order | N/A | final |
| P2-038 | manifest contents include the frozen output metadata | manifest tests | exact metadata | N/A | final |
| P2-039 | hash separation rejects mixed full-hash/business-hash confusion | negative hash tests | reject confusion | REVISION_OUTPUT_HASH_MISMATCH | final |
| P2-040 | bundle integrity passes on valid canonical Storyboard output | integrity tests | PASS | N/A | final |
| P2-041 | bundle integrity fails on missing bundle outputs | integrity tests | FAIL | BUNDLE_NOT_MATERIALIZED | final |
| P2-042 | bundle integrity fails on wrong output hashes | integrity tests | FAIL | REVISION_OUTPUT_HASH_MISMATCH | final |
| P2-043 | bundle integrity fails on wrong renderer bytes or metadata | integrity tests | FAIL | BUNDLE_INTEGRITY_FAILED | final |
| P2-044 | bundle integrity fails on invalid manifest contents | integrity tests | FAIL | BUNDLE_INTEGRITY_FAILED | final |
| P2-045 | `storyboard_bundle_integrity` is declared required in `v0.2.1` | skill manifest test | required validator present | N/A | final |
| P2-046 | historical `v0.2.0` uses live service checks for integrity | service tests | live check invoked | N/A | final |
| P2-047 | approval path blocks when bundle is not materialized | approval tests | block approval | BUNDLE_NOT_MATERIALIZED | final |
| P2-048 | approval path blocks when bundle integrity fails | approval tests | block approval | BUNDLE_INTEGRITY_FAILED | final |
| P2-049 | bundle integrity service checker returns stable symbolic codes | service tests | stable code returned | BUNDLE_INTEGRITY_FAILED | final |
| P2-050 | already-approved Phase 1 revisions remain approved | approval regression tests | approved remains approved | N/A | final |
| P2-051 | future approvals require bundle integrity PASS | approval tests | PASS required | BUNDLE_INTEGRITY_FAILED | final |
| P2-052 | historical unapproved `v0.2.0` revisions require bundle integrity before approval | approval tests | bundle required | BUNDLE_NOT_MATERIALIZED | final |
| P2-053 | formal-review export succeeds only when the revision is approved, FRESH, all required validators pass, and bundle integrity passes | positive formal-review export test | status=EXPORTED | N/A | final |
| P2-054 | formal-review export blocks when bundle is missing | export tests | block export | BUNDLE_NOT_MATERIALIZED | final |
| P2-055 | formal-review export blocks when bundle integrity fails | export tests | block export | BUNDLE_INTEGRITY_FAILED | final |
| P2-056 | approval never implicitly materializes | approval tests | no auto materialization | N/A | final |
| P2-057 | approval failure emits `BUNDLE_NOT_MATERIALIZED` or `BUNDLE_INTEGRITY_FAILED` | approval tests | expected code | BUNDLE_NOT_MATERIALIZED / BUNDLE_INTEGRITY_FAILED | final |
| P2-058 | formal-review export is blocked when the revision is unapproved, STALE, or a required non-bundle validator has not passed | formal-review gate failure tests | export blocked without final directory | FORMAL_REVIEW_EXPORT_BLOCKED | final |
| P2-059 | approval/export preserves existing approved revisions | regression tests | approved revisions unchanged | N/A | final |
| P2-060 | export_records additive metadata exists and is backfilled conservatively | migration tests | backfill correct | N/A | final |
| P2-061 | export_records.content_hash remains revision.content_hash | export tests | exact content hash retained | N/A | final |
| P2-062 | export_records.bundle_manifest_hash stores the business manifest hash | export tests | business hash retained | N/A | final |
| P2-063 | blocked execution exports persist requested destination | blocked export tests | destination stored | EXPORT_NOT_EXECUTION_READY | final |
| P2-064 | blocked execution exports persist canonical content hash | blocked export tests | canonical hash stored | EXPORT_NOT_EXECUTION_READY | final |
| P2-065 | blocked execution exports persist bundle manifest hash and provenance | blocked export tests | provenance stored | EXPORT_NOT_EXECUTION_READY | final |
| P2-066 | blocked execution exports always use `EXPORT_NOT_EXECUTION_READY` | blocked export tests | blocked with code | EXPORT_NOT_EXECUTION_READY | final |
| P2-067 | diagnostic export on FRESH revision fails closed | export tests | reject FRESH diagnostic | DIAGNOSTIC_EXPORT_REQUIRES_STALE | final |
| P2-068 | diagnostic export on STALE revision succeeds when bundle integrity passes | export tests | diagnostic export succeeds | N/A | final |
| P2-069 | diagnostic export record cannot be used as a dependency parent | dependency-creation tests | reject parent usage | DIAGNOSTIC_EXPORT_NOT_PARENTABLE | final |
| P2-070 | atomic export rejects existing final destination | export tests | destination conflict | EXPORT_DESTINATION_EXISTS | final |
| P2-071 | atomic export stages on the same filesystem | export tests | same-filesystem staging | N/A | final |
| P2-072 | atomic export writes manifest last | export tests | manifest last | N/A | final |
| P2-073 | atomic export renames last | export tests | final rename last | N/A | final |
| P2-074 | atomic export leaves no partial final directory on failure | export tests | no partial output | N/A | final |
| P2-075 | atomic export writes canonical-content.json from canonical bytes | export tests | exact file bytes | N/A | final |
| P2-076 | atomic export writes rendered-markdown.md from revision output bytes | export tests | exact file bytes | N/A | final |
| P2-077 | atomic export writes export-provenance.json and excludes it from bundle hashing | export tests | provenance separate | N/A | final |
| P2-078 | atomic export writes bundle-manifest.json from exact manifest bytes | export tests | exact file bytes | N/A | final |
| P2-079 | atomic export records blocked execution attempts without directory creation | blocked export tests | record only, no dir | EXPORT_NOT_EXECUTION_READY | final |
| P2-080 | CLI outputs command returns frozen JSON response | CLI tests | exact outputs JSON | N/A | final |
| P2-081 | CLI materialize-bundle returns frozen JSON response | CLI tests | exact materialize JSON | N/A | final |
| P2-082 | CLI export-bundle returns frozen JSON response | CLI tests | exact export JSON | N/A | final |
| P2-083 | CLI preserves global exit-code behavior | CLI tests | same exit codes | N/A | final |
| P2-084 | CLI rejects unsupported export kinds or profiles with stable codes | CLI tests | stable rejection | BUNDLE_PROFILE_UNSUPPORTED | final |
| P2-085 | CLI command parsing matches exact frozen contracts | CLI tests | exact parsing | N/A | final |
| P2-086 | CLI responses report bundle status and hashes | CLI tests | status and hashes present | N/A | final |
| P2-087 | CLI responses are deterministic across repeated runs | CLI tests | byte-stable JSON | N/A | final |
| P2-088 | CLI regression coverage preserves existing behavior | regression tests | no behavior drift | N/A | final |
| P2-089 | CLI output files are produced only where allowed | CLI tests | files created only when allowed | N/A | final |
| P2-090 | preflight verifier rejects wrong branch or wrong baseline | preflight verifier tests | fail preflight | N/A | preflight |
| P2-091 | preflight verifier rejects a dirty working tree | preflight verifier tests | fail preflight | N/A | preflight |
| P2-092 | preflight verifier rejects a baseline test regression | preflight verifier tests | fail preflight | N/A | preflight |
| P2-093 | portable verifier runs pytest-only checks successfully | portable verifier tests | PASS | N/A | portable |
| P2-094 | final verifier checks diff and allowlist successfully | final verifier tests | PASS | N/A | final |
| P2-095 | final verifier rejects undocumented changed files | final verifier tests | fail final | N/A | final |
| P2-096 | final verifier enforces frozen docs unchanged | final verifier tests | frozen docs unchanged | N/A | final |
| P2-097 | final verifier enforces v0.1.0 and v0.2.0 unchanged | final verifier tests | unchanged packages | N/A | final |
| P2-098 | adversarial materialization cases return `BUNDLE_OUTPUT_CONFLICT` | adversarial tests | reject conflict | BUNDLE_OUTPUT_CONFLICT | final |
| P2-099 | adversarial malformed manifest, renderer-byte, or renderer-metadata cases return BUNDLE_INTEGRITY_FAILED | adversarial integrity tests excluding missing output, exact hash mismatch, and invalid output-combination cases | reject malformed bundle | BUNDLE_INTEGRITY_FAILED | final |
| P2-100 | adversarial export destination collisions return `EXPORT_DESTINATION_EXISTS` | adversarial tests | reject collision | EXPORT_DESTINATION_EXISTS | final |
| P2-101 | adversarial approval-without-bundle cases return `BUNDLE_NOT_MATERIALIZED` | adversarial tests | reject missing bundle | BUNDLE_NOT_MATERIALIZED | final |
| P2-102 | adversarial approval-with-bad-bundle cases return `BUNDLE_INTEGRITY_FAILED` | adversarial tests | reject bad bundle | BUNDLE_INTEGRITY_FAILED | final |
| P2-103 | adversarial diagnostic-on-FRESH cases return `DIAGNOSTIC_EXPORT_REQUIRES_STALE` | adversarial tests | reject FRESH diagnostic | DIAGNOSTIC_EXPORT_REQUIRES_STALE | final |
| P2-104 | adversarial execution export cases return `EXPORT_NOT_EXECUTION_READY` | adversarial tests | always blocked | EXPORT_NOT_EXECUTION_READY | final |
| P2-105 | adversarial bundle profile cases return `BUNDLE_PROFILE_UNSUPPORTED` | adversarial tests | reject unsupported profile | BUNDLE_PROFILE_UNSUPPORTED | final |
| P2-106 | adversarial bad revision output hash cases return `REVISION_OUTPUT_HASH_MISMATCH` | adversarial tests | reject bad hash | REVISION_OUTPUT_HASH_MISMATCH | final |
| P2-107 | adversarial invalid output combination cases return `REVISION_OUTPUT_COMBINATION_INVALID` | adversarial tests | reject invalid combination | REVISION_OUTPUT_COMBINATION_INVALID | final |
| P2-108 | dependency-creation entrypoint rejects diagnostic export parent usage | adversarial tests | reject parent use | DIAGNOSTIC_EXPORT_NOT_PARENTABLE | final |
| P2-109 | adversarial formal-review blocked cases return `FORMAL_REVIEW_EXPORT_BLOCKED` | adversarial tests | block formal review for unapproved, STALE, or non-bundle-validator failures | FORMAL_REVIEW_EXPORT_BLOCKED | final |
| P2-110 | end-to-end final acceptance passes only when all frozen checks pass | end-to-end verifier | full PASS | N/A | final |

---

## 14. Exact Changed-File Allowlist Process

A later implementation run must verify that only the files required by the approved plan and tests are changed. The approved Implementation Plan must contain the exact allowlist, and the Phase 2 verifier must duplicate and enforce that exact allowlist. Frozen Design, Contract, Plan, v0.1.0, and v0.2.0 are outside the implementation allowlist. Broad undocumented paths are forbidden.

The allowlist must be explicit, deterministic, and printed in final verification output.

---

## 15. Final Codex Output Format

A later implementation run must end with a concise machine-readable summary that includes:

- phase
- status
- acceptance
- phase1_baseline_commit
- phase2_design_baseline_commit
- execution_start_commit
- implementation_commit
- verification_report_commit
- final_commit
- externally_verified_branch_head
- branch
- pushed
- working_tree_clean
- existing_tests
- new_tests
- total_tests
- portable_verifier
- final_verifier
- acceptance_passed
- acceptance_failed
- blocker_count
- major_count
- minor_count
- changed_files
- protected_decisions_changed
- phase_3_scope_implemented
- known_limitations
- next_gate

Do not embed the verification report commit SHA inside the report itself.

---

## 16. Unresolved Design Questions

None at the architecture level.

---

## 17. Post-Freeze Corrective Addendum - Verification Portability

This addendum corrects verification portability only. It does not authorize Phase 2 implementation.

Frozen facts:

1. The Phase 2 Design Baseline Commit remains `f933182a3db4b3f03de31b4241da29e5be9e3fdd`.
2. A separate Phase 2 Planning Baseline Commit is permitted after that Design Baseline solely to correct a pre-existing Phase 1 acceptance-test portability defect.
3. The corrective diff from the Design Baseline to the Planning Baseline may contain exactly:
   - `tests/acceptance/test_storyboard_workflow_acceptance.py`
   - `docs/superpowers/specs/2026-06-29-phase-2-agent-execution-acceptance-contract.md`
4. The correction must preserve the historical Phase 1 report unchanged, remove current-branch equality from historical report validation, replace fixed pytest counts with semantic successful-run checks, and make no Runtime, Skill, workflow, verifier, or Phase 2 implementation change.
5. The future preparation sequence is:

   ```text
   Phase 1 Final Baseline
   d9f13967d90ae0b2829c3182dd0aebe85c495daf

   → Phase 2 Design Baseline
   f933182a3db4b3f03de31b4241da29e5be9e3fdd

   → Phase 2 Planning Baseline
   verification portability correction only

   → Phase 2 Execution Start Commit
   adds only the approved Phase 2 Implementation Plan
   ```

6. Future preflight must verify:
   - Phase 1 Final Baseline is an ancestor;
   - Phase 2 Design Baseline is an ancestor;
   - the launch prompt supplies the exact Planning Baseline Commit;
   - the diff from Phase 2 Design Baseline to Planning Baseline contains exactly the two corrective files above;
   - the diff from Planning Baseline to Execution Start Commit contains exactly the approved Phase 2 Implementation Plan;
   - the working tree is clean;
   - the baseline suite is green.
7. This addendum corrects verification portability only. It does not authorize Phase 2 implementation.

Final statuses remain:

```text
Design Status: APPROVED AND FROZEN
Contract Status: APPROVED AND FROZEN
Implementation Planning: AUTHORIZED AFTER PORTABILITY CORRECTION PASSES FULL LOCAL AND GITHUB CI VERIFICATION
Implementation: NOT AUTHORIZED
```

---

## 18. Foundation Conflicts

None. This contract stays additive to the frozen Phase 1 foundation and does not authorize Shot Prompt, asset binding, execution planning, target adapters, LibTV, Agnes, or `execution_ready=true`.

---

## 19. Final State

Design Status: APPROVED AND FROZEN
Contract Status: APPROVED AND FROZEN
Implementation Planning: AUTHORIZED AFTER PORTABILITY CORRECTION PASSES FULL LOCAL AND GITHUB CI VERIFICATION
Implementation: NOT AUTHORIZED
