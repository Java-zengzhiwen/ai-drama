# Phase 2 Minimal Bundle Foundation Design

## 1. Status and Decision

Design Status: APPROVED AND FROZEN
Implementation Planning: AUTHORIZED
Implementation: NOT AUTHORIZED

Date: 2026-06-29
Repository: `Java-zengzhiwen/ai-drama`
Branch: `test/phase2-minimal-bundle-foundation`
Required baseline: `d9f13967d90ae0b2829c3182dd0aebe85c495daf`
Baseline test result: `135 passed`

This document refines the frozen Phase 1 foundation with the minimal bundle layer needed for Storyboard output materialization and atomic export. It keeps the unified export audit model, avoids a separate bundle-export table, and adds only the storage and runtime contracts necessary to make bundle membership and export provenance deterministic.

## 2. Problem Statement

Phase 1 established canonical Storyboard JSON as the authority and kept Markdown derived. Phase 2 needs a minimal bundle foundation so the runtime can persist derived outputs, validate bundle integrity, and export a complete bundle atomically without turning bundle state into a new business entity.

The bundle layer must stay narrow:

- `revision_outputs` stores only bundle members, not a graph or execution plan;
- `export_records` remains the single export audit trail;
- Storyboard bundle semantics are limited to rendered Markdown plus a manifest;
- historical v0.2.0 canonical revisions are supported without mutating the skill package or backfilling validator rows;
- v0.2.1 makes bundle integrity required during normal creation.

## 3. Design Decisions

### 3.1 Skill version strategy

- `v0.1.0` remains read-only.
- `v0.2.0` remains read-only.
- add `v0.2.1`.
- `v0.2.1` uses the same `storyboard-canonical-v1` profile, schema, renderer ID, and renderer version as `v0.2.0`.
- `v0.2.1` declares required runtime-native `storyboard_bundle_integrity`.
- Phase 2 does not mutate the `v0.2.0` package or its validator declarations.

### 3.2 Materialization compatibility

- new `v0.2.1` Storyboard revisions auto-materialize bundle outputs before validation completes.
- if the canonical Revision remains persisted after a failed materialization attempt, `approval_status` remains `pending`.
- if the failed DB output transaction leaves zero `revision_outputs` rows, the `Run` becomes `VALIDATION_FAILED`.
- no automatic retry or automatic approval occurs.
- explicit `materialize-bundle` may repair later.
- transaction failure uses `BUNDLE_NOT_MATERIALIZED`.
- pre-existing partial or conflicting rows use `BUNDLE_OUTPUT_CONFLICT`.
- existing `v0.2.0` canonical revisions require explicit `materialize-bundle`.
- zero existing rows means the runtime creates both outputs transactionally.
- exact complete rows mean `ALREADY_MATERIALIZED`.
- no revision rewrite, output overwrite, approval change, or auto-approval is allowed.

### 3.3 Hash separation

- `bundle_manifest_hash` is the business hash.
- it excludes `revision_id` and `bundle_manifest_hash`.
- `revision_outputs.content_hash` is the exact full object-byte hash.
- the two hashes are not required to be equal.
- manifest outputs excludes `bundle_manifest` itself.

### 3.4 Export-record semantics

- `export_records.content_hash` remains `revision.content_hash`.
- `export_records.bundle_manifest_hash` stores the business manifest hash.
- blocked execution attempts store the requested destination, canonical content hash, manifest hash, provenance, and error code.
- export auditing stays unified in `export_records`; bundle export is not a separate business entity.
- `export-provenance.json` is not `revision_outputs`.
- `export-provenance.json` is not included in the Bundle Manifest.
- `export-provenance.json` is not included in `bundle_manifest_hash`.

### 3.5 Approval compatibility

- existing approved Phase 1 revisions are not retroactively revoked.
- future approvals of canonical Storyboard revisions, including old unapproved v0.2.0 revisions, require materialized bundle integrity `PASS`.
- formal-review export of previously approved revisions also requires materialization and bundle integrity `PASS`.

### 3.6 Bundle integrity architecture

- `storyboard_bundle_integrity` is a declared required runtime-native validator in `v0.2.1`.
- the same integrity logic is also exposed as a Runtime service checker for historical `v0.2.0` materialization, approval, and export.
- `v0.2.0` remains unmodified.

### 3.7 Transaction boundary

- immutable objects may be written before the SQLite transaction.
- both `revision_outputs` rows are inserted in one DB transaction.
- a failed DB transaction leaves zero output rows.
- unreferenced object-store blobs are tolerated.
- no object GC is performed in Phase 2.

### 3.8 Atomic export

- no `--force` option exists in Phase 2.
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

### 3.9 Exact export gates

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

## 4. Authority Hierarchy

If there is any conflict, use this order:

1. Frozen Foundation Design
2. Frozen Phase 2 Design
3. Frozen Phase 2 Agent Execution & Acceptance Contract
4. AGENTS.md
5. approved Phase 2 Implementation Plan
6. repository code at Execution Start Commit
7. Phase 1 supporting documents
8. Codex engineering judgment

No Phase 2 document may override the frozen Foundation.

## 5. Exact Database Contracts

### 5.1 `revision_outputs`

`revision_outputs` is the only bundle-member persistence table.

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
- indexes:
  - `revision_outputs_content_hash_idx` on `content_hash`
  - `revision_outputs_object_id_idx` on `object_id`

Storyboard legal outputs are exactly:

- `rendered_markdown`
- `bundle_manifest`

Shot Prompt legal outputs are not implemented in Phase 2.

Exact output metadata:

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

Object identity rules:

- `object_id = SHA256(exact bytes)`.
- `content_hash = SHA256(exact bytes)`.
- valid rows therefore have `object_id == content_hash`.
- `content_hash` is the exact object-byte hash, not a business hash.

Bundle Manifest v1 full schema:

```json
{
  "schema_version": "bundle-manifest-v1",
  "revision_id": "REVISION_ID",
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
  ],
  "bundle_manifest_hash": "SHA256"
}
```

Manifest rules:

- `schema_version` is exactly `bundle-manifest-v1`.
- the manifest object is stored as canonical-json-v1 bytes with no trailing newline.
- the full stored manifest includes `revision_id` and `bundle_manifest_hash`.
- the business hash preimage is exactly the JSON object above without `revision_id` and `bundle_manifest_hash`.
- the business hash is SHA-256 over canonical-json-v1 bytes of that preimage.
- `outputs` is sorted by `logical_type`.
- `outputs` excludes `bundle_manifest` itself.
- `canonical_content_hash` references `revision.content_hash`.
- `bundle_manifest_hash` in the stored manifest is the exact business hash.

### 5.2 `export_records`

`export_records` remains the single unified export audit table.

Existing columns remain in place, and additive Phase 2 columns are:

- `export_kind TEXT NOT NULL DEFAULT 'legacy_single' CHECK (export_kind IN ('legacy_single', 'formal_review', 'diagnostic', 'execution'))`
- `freshness_status TEXT NOT NULL DEFAULT '' CHECK (freshness_status IN ('', 'FRESH', 'STALE'))`
- `diagnostic_only INTEGER NOT NULL DEFAULT 0 CHECK (diagnostic_only IN (0, 1))`
- `not_an_execution_package INTEGER NOT NULL DEFAULT 1 CHECK (not_an_execution_package IN (0, 1))`
- `execution_ready INTEGER NOT NULL DEFAULT 0 CHECK (execution_ready IN (0, 1))`
- `bundle_manifest_hash TEXT NOT NULL DEFAULT ''`
- `error_code TEXT NOT NULL DEFAULT ''`

Backfill rules for legacy rows:

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
- blocked execution attempts still persist the requested destination, canonical content hash, bundle manifest hash, provenance object reference, and error code.
- migration is idempotent.
- reopening an already migrated database must not change or duplicate schema state.

### 5.3 `export-provenance`

`export-provenance.json` uses `export-provenance-v1` and is separate from bundle membership and bundle hashing.

Exact stored contract:

```json
{
  "schema_version": "export-provenance-v1",
  "export_id": "EXPORT_ID",
  "export_kind": "formal_review|diagnostic|execution",
  "artifact_id": "ARTIFACT_ID",
  "revision_id": "REVISION_ID",
  "canonical_content_hash": "SHA256",
  "bundle_manifest_hash": "",
  "bundle_status": "verified|not_materialized|invalid",
  "freshness_status": "FRESH|STALE|",
  "diagnostic_only": false,
  "not_an_execution_package": true,
  "execution_ready": false,
  "requested_destination": "OUTPUT_DIR",
  "export_time": "TIMESTAMP",
  "error_code": ""
}
```

Rules:

- `export-provenance.json` is not `revision_outputs`.
- `export-provenance.json` is not included in Bundle Manifest.
- `export-provenance.json` is not included in `bundle_manifest_hash`.

## 6. Bundle Manifest Rules

- business manifest hash excludes `revision_id` and `bundle_manifest_hash`.
- business manifest hash excludes paths, approval state, readiness state, freshness metadata, clock data, and platform data.
- the stored manifest includes `revision_id` and `bundle_manifest_hash`.
- the business preimage excludes `revision_id` and `bundle_manifest_hash`.

## 7. Bundle Materialization Rules

- materialization is idempotent at the business level.
- `v0.2.1` revisions auto-materialize before validation.
- historical `v0.2.0` revisions require explicit `materialize-bundle`.
- zero rows means create both outputs in one DB transaction.
- exact complete rows mean `ALREADY_MATERIALIZED`.
- partial or conflicting rows mean `BUNDLE_OUTPUT_CONFLICT`.
- materialization never rewrites the revision, overwrites outputs, changes approval, or auto-approves.

## 8. Bundle Integrity Rules

- the required runtime-native checker is `storyboard_bundle_integrity`.
- the checker validates allowed output set, output hashes, renderer bytes, renderer metadata, and manifest contents/hashes.
- the checker is runtime-native and store-aware.
- failures use the stable code `BUNDLE_INTEGRITY_FAILED`.
- `v0.2.1` declares the validator in the skill package.
- `v0.2.0` uses live Runtime service checks during materialization, approval, and export, without mutating the skill package or requiring backfilled `ValidationResult` rows.

## 9. Atomic Export Rules

Atomic export writes exactly these files in this order:

1. `canonical-content.json` from exact canonical object bytes.
2. `rendered-markdown.md` from exact revision output bytes.
3. `export-provenance.json` generated for the export.
4. `bundle-manifest.json` written last from exact revision output bytes.
5. verify hashes, then atomic rename.

Additional rules:

- the staging directory must be on the same filesystem as the final destination.
- `EXPORT_DESTINATION_EXISTS` is raised if the final destination already exists.
- any failure removes staging and leaves no partial final directory.
- execution export never implicitly materializes.
- execution export never performs filesystem staging.
- execution export never writes a final directory regardless of bundle state.
- if a verified bundle exists, execution export stores `bundle_manifest_hash` and `bundle_status=verified`.
- if missing, execution export stores `bundle_manifest_hash=""` and `bundle_status=not_materialized`.
- if invalid, execution export stores `bundle_manifest_hash=""` and `bundle_status=invalid`.
- provenance records `bundle_status`.

## 10. CLI Contracts

The exact Phase 2 CLI contracts are:

- `ai-drama artifacts outputs --revision REVISION_ID`
- `ai-drama artifacts materialize-bundle --revision REVISION_ID`
- `ai-drama artifacts export-bundle --revision REVISION_ID --kind formal-review|diagnostic|execution --output OUTPUT_DIR`

Rules:

- no `--force` option in Phase 2.
- preserve existing CLI behavior outside the new bundle commands.
- exact JSON response contracts are frozen here and are not deferred to the Implementation Plan.

## 11. Verifier Model

The unified Phase 2 verifier must support:

- `preflight`
- `portable`
- `final`

Preflight checks include branch, exact baseline ancestry, clean tree, and baseline test count.
Portable checks run pytest-only verification without git-state assertions.
Final checks re-run git-state verification, `git diff --check`, the full suite, and the final gate.

## 12. Acceptance Matrix

- `P2-001..005`: baseline, branch, ancestry, clean tree, baseline pytest
- `P2-006..009`: reserved
- `P2-010..019`: `revision_outputs` schema and migration
- `P2-020..029`: materialization compatibility and auto-materialize rules
- `P2-030..039`: hash separation and manifest rules
- `P2-040..049`: bundle integrity validator and runtime service checks
- `P2-050..059`: approval compatibility
- `P2-060..069`: export audit and blocked execution records
- `P2-070..079`: atomic export behavior
- `P2-080..089`: CLI contract coverage
- `P2-090..110`: negative, migration, atomicity, and adversarial verification

## 13. Foundation Conflicts

None. This design is additive to the frozen Phase 1 foundation and does not introduce Shot Prompt, asset binding, execution planning, target adapters, LibTV, Agnes, or `execution_ready=true`.

## 14. Unresolved Design Questions

None at the architecture level.

## 15. Final State

Design Status: APPROVED AND FROZEN
Implementation Planning: AUTHORIZED
Implementation: NOT AUTHORIZED
