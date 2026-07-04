# Phase 2 Minimal Bundle Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The main agent is the sole code writer. All subagents are read-only.

**Goal:** Implement Phase 2 minimal bundle persistence, deterministic bundle materialization, atomic bundle export, blocked execution export auditing, and unified Phase 2 verification without adding a separate bundle-export business entity.

**Execution model:** `executing-plans`; the main agent writes code, tests, docs, and verification artifacts. Subagents are read-only and only provide analysis.

**Architecture:** `revisions` remains the canonical artifact lineage. `revision_outputs` stores immutable derived bundle members, and `export_records` remains the unified audit table through additive metadata. `v0.2.0` stays read-only with explicit materialization and live Runtime Service integrity checks; `v0.2.1` is additive, uses the same canonical profile/schema/renderer semantics, and declares required runtime-native `storyboard_bundle_integrity`.

**Tech Stack:** Existing Python runtime, SQLite, immutable object store, pytest, local CLI JSON output, and Git-based verifier checks.

---

## 1. Status and Authority

- Plan Status: `APPROVED AND FROZEN`
- Implementation: `NOT AUTHORIZED`

Baselines:

- Phase 1 Final Baseline: `d9f13967d90ae0b2829c3182dd0aebe85c495daf`
- Phase 2 Design Baseline: `f933182a3db4b3f03de31b4241da29e5be9e3fdd`
- Phase 2 Planning Baseline: `68283d41f6db549326979120de9881c995d14a41`

Authority order:

1. Frozen Foundation Design
2. Frozen Phase 2 Design
3. Frozen Phase 2 Agent Execution & Acceptance Contract
4. AGENTS.md
5. This approved plan
6. Repository code at the Planning Baseline
7. Phase 1 supporting documents

---

## 2. Scope Boundaries

In scope:

- `revision_outputs` schema and migration
- additive `export_records` columns and conservative legacy defaults
- byte-safe object-store read/write APIs
- deterministic `rendered_markdown`
- deterministic `bundle_manifest` generation and hash separation
- `v0.2.0` explicit materialization
- `v0.2.1` auto-materialization before validation
- `storyboard_bundle_integrity`
- approval bundle gates
- formal-review export
- diagnostic export
- persistently blocked execution export
- `export-provenance-v1`
- atomic same-filesystem staging and rename
- exact CLI contracts
- unified Phase 2 verifier
- P2-001 through P2-110 acceptance coverage

Out of scope:

- Shot Prompt Canonical
- prompt generation
- asset binding
- execution planning
- target adapters
- LibTV
- Agnes
- web UI
- remote API
- `execution_ready=true`
- unrelated refactors

---

## 3. Exact Changed-File Allowlist

### A. Plan Freeze / Execution Start preparation file

- `docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md`

After the Plan Freeze / Execution Start Commit, this file is protected and is outside the implementation allowlist.

### B. Implementation files to modify

- `ai_drama_runtime/store.py`
- `ai_drama_runtime/services.py`
- `ai_drama_runtime/cli.py`
- `ai_drama_runtime/validators.py`
- `tests/test_cli.py`
- `tests/test_storyboard_canonical_workflow.py`
- `tests/test_validators_approval_export.py`
- `tests/test_storyboard_workflow.py`
- `tests/test_storyboard_legacy_migration.py`
- `tests/test_storyboard_renderer.py`

### C. Implementation files to add

- `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/README.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py`
- `tools/verify_phase2_minimal_bundle_foundation.py`
- `tests/test_phase2_verifier.py`

### D. Final verification/report files to add

- `docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md`

### E. Protected files

- `docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md`
- `ai_drama_runtime/manifest.py`
- `ai_drama_runtime/storyboard_renderer.py`
- `ai_drama_runtime/storyboard_canonical.py`
- `ai_drama_runtime/storyboard_migration.py`
- `tools/verify_phase1_storyboard_canonicalization.py`
- `tools/verify_storyboard_workflow.py`
- `tests/test_phase1_verifier.py`
- `tests/acceptance/test_storyboard_workflow_acceptance.py`
- `docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md`
- `docs/superpowers/specs/2026-06-29-phase-2-minimal-bundle-foundation-design.md`
- `docs/superpowers/specs/2026-06-29-phase-2-agent-execution-acceptance-contract.md`
- `docs/testing/storyboard-workflow-verification/storyboard-verification-report.md`
- `docs/testing/storyboard-workflow-verification/storyboard-verification-report.json`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/skill.json`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_duration.py`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_source_coverage.py`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/common.py`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_structure.py`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_continuity.py`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_genericity.py`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/templates/storyboard-outline.template.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/templates/storyboard-outline.template.json`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/SKILL.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/README.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/schemas/storyboard-outline.schema.json`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/schemas/storyboard-coverage.schema.json`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/contracts/storyboard-approval-contract-v1.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/contracts/storyboard-design-contract-v1.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/MIGRATION-NOTES.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/references/continuity-policy.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/references/source-staleness-policy.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/references/storyboard-rules.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/references/shot-boundary-policy.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/CHANGELOG.md`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/requirements.txt`
- `skills/ai-drama-storyboard-design-skill/v0.1.0/runtime-validators/forbidden-terms.txt`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/skill.json`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/SKILL.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/README.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/schemas/storyboard-canonical.schema.json`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/contracts/storyboard-canonical-contract-v1.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/common_canonical.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/native_storyboard_canonical.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/validate_storyboard_canonical_schema.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/validate_storyboard_shot_identity.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/validate_storyboard_shot_order.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/validate_storyboard_duration.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.0/validators/validate_storyboard_continuity.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/skill.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/MIGRATION-NOTES.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_markdown_json_equivalence.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_source_claim_audit.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_assumptions_and_extensions.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_handoff_contract.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_creator_presentation.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/common.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_coverage_evidence.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_artifact_integrity.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_schema.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_genericity.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_core_story_beats.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/source-conflict-policy.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/body-evidence-policy.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/emotional-progression-rules.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/creative-draft-rules.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/coverage-qc-rubric.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/adaptation-rules.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/core-story-beat-rules.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/atomic-core-story-beat-rules.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/creator-presentation-rules.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/references/production-assumption-policy.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/CHANGELOG.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/requirements.txt`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/README.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/SKILL.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/script_revision_structure.py`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/forbidden-terms.txt`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/schemas/hybrid-script.schema.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/schemas/core-story-beats.schema.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/schemas/core-story-beat-coverage.schema.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/source-conflict-registry.template.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/script-approval-presentation.template.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/core-story-beats.template.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/coverage-report.template.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/source-claim-audit.template.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/script-handoff-manifest.template.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/templates/production-assumption-log.template.json`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/contracts/script-revision-presentation-contract-v2.md`
- `skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/contracts/script-approval-creator-presentation-contract-v2.md`
- `.github/workflows/storyboard-workflow-verification.yml`

---

## 4. Repository Map

| file | exact existing class/function used | current responsibility | exact Phase 2 responsibility | status |
|---|---|---|---|---|
| `ai_drama_runtime/store.py` | `RuntimeStore._init_schema`, `RuntimeStore._ensure_columns`, `write_text_object`, `read_text`, `record_export`, `_export_from_row` | Owns SQLite schema setup, object-store text helpers, legacy export row insertion, and export row hydration. | Add append-only `revision_outputs`, additive `export_records` columns, byte object helpers, `ExportRecord` metadata hydration, and transactional bundle export insert API without a status column while retaining `record_export`. | Modify |
| `ai_drama_runtime/services.py` | `RuntimeService.run_storyboard`, `approve_revision`, `export_approved`, `revision_freshness` | Orchestrates Storyboard revision creation, approval, legacy approved export, and freshness checks. | Add materialization, auto-materialization, bundle integrity use, approval gates, atomic formal-review/diagnostic export, and blocked execution audit while leaving `export_approved` behavior unchanged. | Modify |
| `ai_drama_runtime/validators.py` | runtime-native validator dispatch, `run_declared_validators` | Dispatches declared validators and runtime-native checks during revision validation. | Add `storyboard_bundle_integrity` dispatch for `v0.2.1` and expose the live Runtime Service checker path for historical `v0.2.0` approval/export/materialization gates. | Modify |
| `ai_drama_runtime/cli.py` | `_json`, `build_parser`, `main` | Builds the CLI parser, prints JSON responses, and maps command errors to stable exit codes. | Add `artifacts outputs`, `artifacts materialize-bundle`, and `artifacts export-bundle` handlers without creating a duplicate `artifacts` group. | Modify |
| `tests/test_cli.py` | existing CLI invocation helpers and JSON assertions | Covers CLI parser behavior and JSON outputs. | Add exact JSON contract tests for outputs, materialize-bundle, formal-review/diagnostic export, blocked execution export, and unsupported profile rejection. | Modify |
| `tests/test_storyboard_canonical_workflow.py` | existing Storyboard runtime workflow fixtures | Covers canonical Storyboard creation and validation behavior. | Add explicit materialization, v0.2.1 auto-materialization, failed auto-materialization lifecycle, and conflict-row tests. | Modify |
| `tests/test_validators_approval_export.py` | existing approval/export service fixtures | Covers validator, approval, and export behavior. | Add bundle integrity, approval gates, export audit transaction, atomic export, diagnostic, blocked execution, and adversarial export tests. | Modify |
| `tests/test_storyboard_workflow.py` | existing high-level workflow assertions | Covers existing Storyboard workflow compatibility. | Add regression coverage that Phase 2 approval gates do not revoke already-approved historical Phase 1 revisions. | Modify |
| `tests/test_storyboard_legacy_migration.py` | existing migration/schema fixtures | Covers database migration and legacy row compatibility. | Add `revision_outputs` DDL, additive `export_records` backfill, idempotent replay, and append-only API tests. | Modify |
| `tests/test_storyboard_renderer.py` | existing renderer byte/golden helpers | Covers deterministic Storyboard renderer behavior. | Add bundle manifest canonical-json-v1, exact byte, and business-hash separation tests without changing the renderer module. | Modify |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json` | copied `v0.2.0` skill metadata shape | Declares skill metadata for a versioned Storyboard skill package. | Add `v0.2.1`, provenance, and required runtime-native `storyboard_bundle_integrity` while keeping canonical profile/schema/renderer semantics unchanged. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md` | copied `v0.2.0` file bytes | Skill instructions for canonical Storyboard authoring. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/README.md` | copied `v0.2.0` file bytes | Skill package README. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json` | copied `v0.2.0` file bytes | Canonical Storyboard JSON schema. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md` | copied `v0.2.0` file bytes | Canonical Storyboard contract. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py` | copied `v0.2.0` file bytes | Shared canonical validator utilities. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py` | copied `v0.2.0` file bytes | Native canonical validator entrypoint. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py` | copied `v0.2.0` file bytes | Schema validator. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py` | copied `v0.2.0` file bytes | Shot identity validator. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py` | copied `v0.2.0` file bytes | Shot order validator. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py` | copied `v0.2.0` file bytes | Duration validator. | Byte-identical copy from `v0.2.0`. | Add |
| `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py` | copied `v0.2.0` file bytes | Continuity validator. | Byte-identical copy from `v0.2.0`. | Add |
| `tools/verify_phase2_minimal_bundle_foundation.py` | no existing Phase 2 verifier | No Phase 2-specific preflight/portable/final verifier exists. | Add preflight, portable, and final verifier modes for branch, baseline, allowlist, protected-file, pytest, and GitHub Actions evidence. | Add |
| `tests/test_phase2_verifier.py` | no existing Phase 2 verifier tests | No Phase 2 verifier test module exists. | Add tests for preflight, portable, final allowlist, protected-file checks, and failure modes. | Add |
| `docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md` | no existing Phase 2 verification report | No Phase 2 implementation verification report exists. | Add final verification evidence only in Slice 12 after implementation and local/CI verification pass. | Add |
| `ai_drama_runtime/manifest.py` | existing manifest helpers | Shared manifest behavior used by the runtime. | Must remain byte-unchanged; Phase 2 bundle manifest logic belongs in allowed service code. | Protected |
| `ai_drama_runtime/storyboard_canonical.py` | existing canonical normalization helpers | Canonical Storyboard object construction and normalization. | Must remain byte-unchanged; Phase 2 reads exact canonical object bytes and does not change canonical semantics. | Protected |
| `ai_drama_runtime/storyboard_renderer.py` | existing Markdown renderer | Deterministic Storyboard Markdown rendering. | Must remain byte-unchanged; Phase 2 calls the existing renderer and verifies exact bytes. | Protected |
| `ai_drama_runtime/storyboard_migration.py` | existing Storyboard migration helpers | Phase 1 Storyboard migration behavior. | Must remain byte-unchanged; Phase 2 database migration is implemented in `RuntimeStore` schema paths. | Protected |

---

## 5. Runtime APIs and Error Objects

### RuntimeStore additions

Dataclass `RevisionOutputRecord` fields:

- `revision_output_id: str`
- `revision_id: str`
- `logical_type: str`
- `object_id: str`
- `content_hash: str`
- `media_type: str`
- `generator: str`
- `generator_version: str`
- `created_at: str`

Extended dataclass `ExportRecord` fields:

- `export_id: str`
- `artifact_id: str`
- `revision_id: str`
- `run_id: str`
- `content_hash: str`
- `destination: str`
- `provenance_object_id: str`
- `created_at: str`
- `export_kind: str`
- `freshness_status: str`
- `diagnostic_only: bool`
- `not_an_execution_package: bool`
- `execution_ready: bool`
- `bundle_manifest_hash: str`
- `error_code: str`

Methods:

- `write_bytes_object(self, data: bytes) -> str`
- `read_bytes_object(self, object_id: str) -> bytes`
- `write_text_object(self, text: str) -> str`
- `read_text(self, object_id: str) -> str`
- `insert_revision_outputs_transaction(self, rows: list[dict]) -> list[RevisionOutputRecord]`
- `revision_outputs(self, revision_id: str) -> list[RevisionOutputRecord]`
- `get_revision_output(self, revision_id: str, logical_type: str) -> RevisionOutputRecord | None`
- `get_export_record(self, export_id: str) -> ExportRecord | None`
- `insert_export_record_in_transaction(self, **values) -> ExportRecord`
- `insert_export_record(self, **values) -> ExportRecord`

`write_text_object` delegates to `write_bytes_object(text.encode("utf-8"))`. `read_text` delegates to `read_bytes_object(object_id).decode("utf-8")`.

Export audit transaction semantics:

- `RuntimeStore.record_export` remains the existing legacy export-record API.
- `RuntimeService.export_approved` remains behaviorally unchanged and continues to use `record_export`.
- `record_export` continues to support `legacy_single` export rows and relies on frozen database defaults for new Phase 2 columns.
- new bundle export paths use `insert_export_record` and `insert_export_record_in_transaction`.
- do not rename or remove `record_export`.
- do not modify the legacy `artifacts export-approved --force` contract.
- `insert_export_record_in_transaction` performs the `INSERT` and returns the hydrated `ExportRecord` but never commits.
- `insert_export_record` opens and commits its own SQLite transaction by delegating to `insert_export_record_in_transaction`.
- formal-review and diagnostic successful exports use `insert_export_record_in_transaction`.
- blocked execution uses `insert_export_record` because the attempt must always persist.
- `export_records` has no `status` column.
- The `EXPORTED` status value is a CLI response value only, not an `export_records` column or stored database value.

### RuntimeService methods

- `bundle_outputs(self, revision_id)`
- `materialize_storyboard_bundle(self, revision_id)`
- `_auto_materialize_storyboard_bundle(self, revision, run_id)`
- `check_storyboard_bundle_integrity(self, revision_id)`
- `export_storyboard_bundle(self, revision_id, export_kind, output)`
- `_export_storyboard_formal_review(self, revision, output)`
- `_export_storyboard_diagnostic(self, revision, output)`
- `_record_storyboard_execution_block(self, revision, output)`
- `attach_export_dependency(self, child_revision_id, parent_export_id, relation_type)`

Existing methods retained:

- `approve_revision(self, revision_id, reviewer, note="")`
- `export_approved(...)`

No duplicate public `validate_storyboard_bundle` method is added.

### CLI handlers

- `_artifacts_outputs`
- `_artifacts_materialize_bundle`
- `_artifacts_export_bundle`

`build_parser` modifies the existing `artifacts` group. It does not create a second `artifacts` group.

### Code-bearing exceptions and CLI exit mapping

All code-bearing exceptions expose:

- `code`
- `safe_message`

Exact exception classes:

- `BundleError(code, message)` for materialization, integrity, profile, hash, and output-combination errors
- `BundleApprovalBlocked(code, message)` for approval bundle-gate errors
- `BundleExportError(code, message)` for export gate, destination, and atomic export errors
- `DiagnosticParentError(code, message)` for diagnostic export parent rejection

CLI mapping:

- `BundleError` -> existing `EXIT_INVALID`
- `BundleApprovalBlocked` -> existing `EXIT_APPROVAL`
- `BundleExportError` -> existing `EXIT_NOT_FOUND`
- `DiagnosticParentError` -> existing `EXIT_INVALID`
- existing `WorkflowGateError` remains mapped to `EXIT_INVALID`
- existing `ApprovalBlocked` remains mapped to `EXIT_APPROVAL`
- existing `ExportConflict` remains mapped to `EXIT_NOT_FOUND`

Blocked execution export:

- prints the frozen `BLOCKED` JSON response
- exits with `0` because a blocked execution export is a successful audit-recording command, not a CLI processing failure

---

## 6. v0.2.1 Copy Semantics

Byte-identical copies from `v0.2.0`:

- `skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/README.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py`
- `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py`

Intentionally modified:

- `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`

Exact `skill.json` changes:

- `version` becomes `v0.2.1`
- provenance source becomes `phase_2_minimal_bundle_foundation`
- add required runtime-native validator `storyboard_bundle_integrity`
- canonical profile/schema/renderer fields remain semantically byte-equivalent to `v0.2.0`

`v0.2.0` is not mutated.

---

## 7. Phase 2-Specific Test Inventory

- `tests/test_storyboard_legacy_migration.py::test_revision_outputs_schema_matches_frozen_ddl`
- `tests/test_storyboard_legacy_migration.py::test_revision_outputs_public_api_is_append_only`
- `tests/test_storyboard_legacy_migration.py::test_export_records_legacy_rows_receive_frozen_defaults`
- `tests/test_storyboard_legacy_migration.py::test_phase2_migration_replay_is_idempotent`
- `tests/test_storyboard_renderer.py::test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash`
- `tests/test_storyboard_renderer.py::test_bundle_manifest_uses_canonical_json_v1_bytes`
- `tests/test_storyboard_renderer.py::test_bundle_output_metadata_matches_frozen_contract`
- `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_creates_both_outputs_transactionally`
- `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_returns_already_materialized_for_exact_rows`
- `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_partial_output_rows`
- `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_unexpected_output_combination`
- `tests/test_storyboard_canonical_workflow.py::test_v021_auto_materializes_before_declared_validation`
- `tests/test_storyboard_canonical_workflow.py::test_v021_materialization_failure_leaves_pending_revision_and_zero_rows`
- `tests/test_storyboard_canonical_workflow.py::test_v021_skill_declares_required_bundle_integrity_validator`
- `tests/test_validators_approval_export.py::test_bundle_integrity_passes_valid_bundle`
- `tests/test_validators_approval_export.py::test_bundle_integrity_reports_missing_bundle`
- `tests/test_validators_approval_export.py::test_bundle_integrity_reports_revision_output_hash_mismatch`
- `tests/test_validators_approval_export.py::test_bundle_integrity_reports_invalid_output_combination`
- `tests/test_validators_approval_export.py::test_bundle_integrity_reports_renderer_byte_or_metadata_failure`
- `tests/test_validators_approval_export.py::test_bundle_integrity_reports_manifest_semantic_failure`
- `tests/test_validators_approval_export.py::test_v020_uses_live_bundle_integrity_checker`
- `tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle`
- `tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle`
- `tests/test_validators_approval_export.py::test_approval_does_not_implicitly_materialize_bundle`
- `tests/test_validators_approval_export.py::test_existing_approved_phase1_revision_is_not_revoked`
- `tests/test_validators_approval_export.py::test_formal_review_export_is_atomic`
- `tests/test_validators_approval_export.py::test_formal_review_export_rolls_back_audit_when_rename_fails`
- `tests/test_validators_approval_export.py::test_formal_review_export_compensates_final_directory_when_commit_fails`
- `tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion`
- `tests/test_validators_approval_export.py::test_formal_review_export_blocks_missing_bundle_before_general_gate`
- `tests/test_validators_approval_export.py::test_formal_review_export_blocks_invalid_bundle_before_general_gate`
- `tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator`
- `tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination`
- `tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision`
- `tests/test_validators_approval_export.py::test_execution_export_records_block_without_filesystem_writes`
- `tests/test_validators_approval_export.py::test_execution_export_persists_blocked_attempt_without_filesystem_writes`
- `tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent`
- `tests/test_cli.py::test_artifacts_outputs_returns_frozen_json_contract`
- `tests/test_cli.py::test_artifacts_materialize_bundle_returns_frozen_json_contract`
- `tests/test_cli.py::test_artifacts_export_bundle_returns_frozen_json_contract`
- `tests/test_cli.py::test_artifacts_export_bundle_execution_returns_blocked_json_and_zero_exit`
- `tests/test_cli.py::test_artifacts_export_bundle_rejects_unsupported_profile`
- `tests/test_phase2_verifier.py::test_preflight_branch_head_and_clean_tree`
- `tests/test_phase2_verifier.py::test_portable_mode_runs_pytest_only`
- `tests/test_phase2_verifier.py::test_final_mode_enforces_allowlist_and_frozen_files`

---

## 8. Database Migration Plan

`revision_outputs` exact SQLite DDL:

```sql
CREATE TABLE IF NOT EXISTS revision_outputs (
  revision_output_id TEXT PRIMARY KEY,
  revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
  logical_type TEXT NOT NULL CHECK (logical_type IN ('rendered_positive_prompt', 'rendered_negative_prompt', 'rendered_markdown', 'bundle_manifest')),
  object_id TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  media_type TEXT NOT NULL,
  generator TEXT NOT NULL,
  generator_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(revision_id, logical_type)
);
CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx ON revision_outputs(content_hash);
CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx ON revision_outputs(object_id);
```

Exact `ALTER TABLE` statements for `export_records`:

```sql
ALTER TABLE export_records ADD COLUMN export_kind TEXT NOT NULL DEFAULT 'legacy_single' CHECK (export_kind IN ('legacy_single','formal_review','diagnostic','execution'));
ALTER TABLE export_records ADD COLUMN freshness_status TEXT NOT NULL DEFAULT '' CHECK (freshness_status IN ('','FRESH','STALE'));
ALTER TABLE export_records ADD COLUMN diagnostic_only INTEGER NOT NULL DEFAULT 0 CHECK (diagnostic_only IN (0,1));
ALTER TABLE export_records ADD COLUMN not_an_execution_package INTEGER NOT NULL DEFAULT 1 CHECK (not_an_execution_package IN (0,1));
ALTER TABLE export_records ADD COLUMN execution_ready INTEGER NOT NULL DEFAULT 0 CHECK (execution_ready IN (0,1));
ALTER TABLE export_records ADD COLUMN bundle_manifest_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE export_records ADD COLUMN error_code TEXT NOT NULL DEFAULT '';
```

Fresh database migration path:

- `_init_schema` creates all current tables.
- `_init_schema` creates `revision_outputs` with the exact DDL above.
- `_init_schema` creates `export_records` with all legacy and Phase 2 columns included.

Existing database migration path:

- `_init_schema` reads `PRAGMA table_info(export_records)`.
- Missing Phase 2 columns are added with the exact `ALTER TABLE` statements above.
- Existing rows receive the column defaults through SQLite add-column behavior and require no separate semantic rewrite.

Migration replay test setup:

- create a temporary SQLite database using the Planning Baseline schema
- seed representative legacy artifacts, runs, revisions, approvals, and export_records
- reopen through the Phase 2 `RuntimeStore`
- verify additive migration and frozen defaults
- reopen a second time and verify idempotence
- compare seeded row identities and values before and after

No new bundle-export table is created.

Append-only business enforcement:

- `revision_outputs` has one public write method: `insert_revision_outputs_transaction`
- no `RuntimeStore` update or delete method exists for `revision_outputs`
- materialization always reads existing rows before insertion
- exact rows return `ALREADY_MATERIALIZED`
- partial, unexpected, or conflicting rows return `BUNDLE_OUTPUT_CONFLICT`
- existing rows are never updated or deleted
- renderer upgrades create a new Revision
- direct maintenance SQL is outside normal business flow

---

## 9. Canonical JSON v1 and Byte Contracts

Exact canonical-json-v1 rules:

- UTF-8 without BOM
- Unicode NFC normalization
- keys sorted lexicographically
- arrays preserve business order
- separators are `,` and `:`
- `ensure_ascii=false`
- `allow_nan=false`
- no trailing newline

Exact helper:

- `RuntimeService._canonical_json_v1_bytes(self, value) -> bytes`

Byte-safe object store:

- `object_id` is SHA256 of exact bytes
- all bundle-member hashes use exact bytes
- `canonical-content.json` is exported from exact stored canonical bytes
- `rendered-markdown.md` is exported from exact `revision_outputs` bytes
- `bundle-manifest.json` is exported from exact `revision_outputs` bytes

Bundle Manifest business preimage:

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

Full stored Bundle Manifest v1:

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

### Exact Revision Output Metadata

`rendered_markdown`:

- `media_type`: `text/markdown`
- `generator`: `storyboard-canonical-markdown-renderer`
- `generator_version`: `1.0.0`
- content bytes: exact deterministic renderer bytes

`bundle_manifest`:

- `media_type`: `application/json`
- `generator`: `bundle-manifest-builder`
- `generator_version`: `1`
- content bytes: canonical-json-v1 full stored manifest bytes
- no trailing newline

Stored output combination rules:

- zero `revision_outputs` rows = not materialized
- exactly `rendered_markdown + bundle_manifest` = complete Storyboard bundle
- any non-empty subset, extra type, or unexpected combination = conflict or invalid combination according to the frozen error precedence
- rendered Markdown display may be generated in memory or exported by legacy behavior, but a one-row `revision_outputs` bundle is not complete

Error-code precedence:

- `BUNDLE_NOT_MATERIALIZED`: no valid bundle rows exist where a bundle is required
- `BUNDLE_OUTPUT_CONFLICT`: materialization encounters partial, unexpected, or conflicting existing rows
- `REVISION_OUTPUT_HASH_MISMATCH`: `object_id` or `content_hash` does not equal SHA256 of exact stored bytes
- `REVISION_OUTPUT_COMBINATION_INVALID`: stored output logical types form an illegal Storyboard combination
- `BUNDLE_INTEGRITY_FAILED`: row hashes are valid, but renderer bytes, renderer metadata, manifest contents, or business hash semantics are invalid

---

## 10. Export and CLI JSON Contracts

`export-provenance-v1`:

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

Provenance exclusion:

- `export-provenance.json` is not a `revision_outputs` row
- `export-provenance.json` is not included in Bundle Manifest
- `export-provenance.json` is not included in `bundle_manifest_hash`

Bundle outputs success:

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

Materialize-bundle success:

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

Formal-review or diagnostic export success:

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

Execution export blocked response:

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

The exported success status is frozen only as a CLI response field. It is not persisted in `export_records`, and no Phase 2 database schema contains an export status column.

---

## 11. Materialization Lifecycle

Explicit `v0.2.0` materialization control flow:

1. load `Revision`;
2. validate `artifact_type == "storyboard"` and `content_profile == "storyboard-canonical-v1"`;
3. load all `revision_outputs` for the revision;
4. when zero rows exist:
   - read exact canonical bytes from the existing canonical object;
   - render deterministic Markdown bytes through the existing renderer;
   - construct the business manifest preimage without `revision_id` and without `bundle_manifest_hash`;
   - calculate `bundle_manifest_hash`;
   - construct full canonical-json-v1 manifest bytes with no trailing newline;
   - write immutable byte objects for `rendered_markdown` and `bundle_manifest`;
   - insert both output rows in one SQLite transaction;
   - run the bundle integrity check;
   - return `MATERIALIZED`;
5. when exact valid `rendered_markdown` and `bundle_manifest` rows exist:
   - run the bundle integrity check;
   - return `ALREADY_MATERIALIZED`;
6. when partial, extra, unexpected, or conflicting rows exist:
   - raise `BUNDLE_OUTPUT_CONFLICT`;
   - never update or delete existing rows.

`v0.2.1` creation control flow:

1. `run_storyboard` persists the canonical `Revision`;
2. persist the revision dependency;
3. call `_auto_materialize_storyboard_bundle` immediately before `run_declared_validators`;
4. success continues to declared validation;
5. materialization failure leaves:
   - `Revision` persisted;
   - `approval_status=pending`;
   - Run status `VALIDATION_FAILED`;
   - transaction failure error `BUNDLE_NOT_MATERIALIZED`;
   - pre-existing conflict error `BUNDLE_OUTPUT_CONFLICT`;
   - zero rows inserted by the failed transaction;
   - no automatic retry;
   - no automatic approval;
6. explicit `artifacts materialize-bundle --revision REVISION_ID` may repair later.

Immutable object blobs written before a failed DB transaction may remain unreferenced. Phase 2 performs no object garbage collection.

---

## 12. Integrity and Approval Procedure

Bundle integrity check order:

1. require exactly `rendered_markdown` and `bundle_manifest`;
2. verify each object exists;
3. verify `SHA256(exact bytes)` equals both `object_id` and `content_hash`;
4. verify logical-type combination;
5. verify `rendered_markdown` metadata;
6. regenerate and compare exact Markdown bytes;
7. parse full manifest;
8. verify manifest shape and deterministic output ordering;
9. verify output metadata and hashes;
10. reconstruct business preimage;
11. recalculate `bundle_manifest_hash`;
12. return `PASS` after every check passes.

Error precedence:

- no rows -> `BUNDLE_NOT_MATERIALIZED`
- partial or unexpected rows during materialization -> `BUNDLE_OUTPUT_CONFLICT`
- exact byte hash mismatch -> `REVISION_OUTPUT_HASH_MISMATCH`
- illegal stored combination -> `REVISION_OUTPUT_COMBINATION_INVALID`
- valid row hashes but renderer, metadata, manifest, or business-hash failure -> `BUNDLE_INTEGRITY_FAILED`

`approve_revision` flow:

- already-approved historical revisions are not retroactively revoked;
- new Storyboard approval checks freshness;
- checks required non-bundle validators;
- calls the live bundle integrity check;
- missing bundle -> `BUNDLE_NOT_MATERIALIZED`;
- invalid bundle -> `BUNDLE_INTEGRITY_FAILED`;
- approval never creates bundle outputs;
- `approve_in_transaction` runs only after every gate passes.

---

## 13. Export and Provenance Procedure

Formal-review flow:

1. load revision and validate supported Storyboard canonical profile;
2. inspect `revision_outputs`;
3. zero rows:
   - raise `BUNDLE_NOT_MATERIALIZED`;
4. non-empty bundle:
   - run bundle integrity;
5. integrity failure:
   - raise `BUNDLE_INTEGRITY_FAILED`;
6. only after bundle presence and integrity pass:
   - require approved;
   - require `FRESH`;
   - require all required non-bundle validators `PASS`;
7. any failure in step 6:
   - raise `FORMAL_REVIEW_EXPORT_BLOCKED`;
8. reject existing final destination;
9. create a unique staging directory beside final destination;
10. generate one `export_id` and one `export_time`;
11. construct `export-provenance-v1`;
12. write `canonical-content.json`;
13. write `rendered-markdown.md`;
14. write `export-provenance.json`;
15. write `bundle-manifest.json` last;
16. reread and verify exact bytes and hashes;
17. begin SQLite transaction;
18. call `insert_export_record_in_transaction` with `error_code=""`;
19. atomically rename staging to final destination;
20. commit SQLite transaction;
21. return `EXPORTED` only after rename and commit succeed.

This order is mandatory even when the revision simultaneously has a missing bundle and is unapproved or `STALE`.

Rename failure behavior:

- rollback transaction;
- remove staging;
- leave no export record;
- leave no final directory.

DB commit failure after rename behavior:

- rollback;
- remove final directory as compensation;
- do not return `EXPORTED`;
- do not leave an apparently successful export record.

Formal-review or diagnostic gate failure never creates a successful export record.

Diagnostic export:

- must explicitly use diagnostic kind;
- revision must be `STALE`;
- bundle integrity must `PASS`;
- `diagnostic_only=true`;
- `not_an_execution_package=true`;
- `execution_ready=false`;
- reuse the same atomic export flow and transactional audit insert.

Execution export:

- never materializes;
- only inspects bundle state;
- derives `verified`, `not_materialized`, or `invalid`;
- writes provenance object;
- persists blocked attempt using `insert_export_record`;
- never creates staging;
- never creates final directory;
- returns frozen `BLOCKED` JSON;
- exits process code `0`.

Formal-review precedence:

- missing bundle -> `BUNDLE_NOT_MATERIALIZED`
- invalid bundle -> `BUNDLE_INTEGRITY_FAILED`
- unapproved, `STALE`, or failed non-bundle validator -> `FORMAL_REVIEW_EXPORT_BLOCKED`

---

## 14. Agent Execution Model

- Main Agent is the sole writer.
- Agent A: Repository Mapper.
- Agent B: Schema & Migration Reviewer.
- Agent C: Manifest & Hash Reviewer.
- Agent D: Atomic Export Reviewer.
- Agent E: Final Contract Reviewer.
- Agent F: Adversarial Tester.
- Agents A-F are read-only.
- Agents A-D may review during implementation.
- Agents E and F run after implementation and before final acceptance.
- No subagent modifies files.
- No red intermediate commit is allowed.
- Main Agent resolves findings only through green commits.

---

## 15. Vertical Implementation Slices

| slice | title | primary objective | exact files |
|---|---|---|---|
| 0 | preflight verifier scaffold | add Phase 2 verifier preflight/portable/final skeleton | `tools/verify_phase2_minimal_bundle_foundation.py`, `tests/test_phase2_verifier.py` |
| 1 | database migration and storage primitives | add `revision_outputs`, export metadata, byte APIs, records | `ai_drama_runtime/store.py`, `tests/test_storyboard_legacy_migration.py` |
| 2 | deterministic bundle builder and exact bytes | add manifest builder, canonical-json-v1 bytes, hash separation | `ai_drama_runtime/services.py`, `tests/test_storyboard_renderer.py`, `tests/test_storyboard_canonical_workflow.py` |
| 3 | explicit v0.2.0 materialization service | add explicit `materialize_storyboard_bundle` lifecycle | `ai_drama_runtime/services.py`, `tests/test_storyboard_canonical_workflow.py` |
| 4 | v0.2.1 skill package and auto-materialization lifecycle | add `v0.2.1` package and auto materialization before validation | `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`, `skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/README.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json`, `skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py`, `ai_drama_runtime/services.py`, `tests/test_storyboard_canonical_workflow.py` |
| 5 | bundle integrity checker | add runtime-native integrity checks and error precedence | `ai_drama_runtime/validators.py`, `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py` |
| 6 | approval gates and v0.2.0 compatibility | enforce approval gates and preserve historical approvals | `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py`, `tests/test_storyboard_workflow.py` |
| 7 | export audit and export-provenance-v1 | extend audit, provenance, diagnostic parent entrypoint | `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py` |
| 8 | atomic formal-review and diagnostic export | add atomic bundle export with staging and gates | `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py` |
| 9 | always-blocked execution export | add blocked execution audit with no filesystem writes | `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py` |
| 10 | exact CLI contracts | add three CLI handlers and frozen JSON responses | `ai_drama_runtime/cli.py`, `tests/test_cli.py` |
| 11 | adversarial and migration closure | close symbolic error and migration edge cases | `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, `ai_drama_runtime/validators.py`, `ai_drama_runtime/cli.py`, `tests/test_storyboard_legacy_migration.py`, `tests/test_storyboard_canonical_workflow.py`, `tests/test_validators_approval_export.py`, `tests/test_cli.py`, `tests/test_phase2_verifier.py` |
| 12 | final Phase 2 verifier and acceptance closure | run final verifier and create verification report | `docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md` |

### Slice 0: Preflight verifier scaffold

- Objective: add Phase 2 verifier preflight, portable, and final skeleton without touching Runtime behavior.
- Primary acceptance IDs: P2-001, P2-002, P2-003, P2-004, P2-090, P2-091, P2-092, P2-093.
- Exact production files: `tools/verify_phase2_minimal_bundle_foundation.py`.
- Exact test files and functions: `tests/test_phase2_verifier.py::test_preflight_branch_head_and_clean_tree`, `tests/test_phase2_verifier.py::test_portable_mode_runs_pytest_only`, `tests/test_phase2_verifier.py::test_final_mode_enforces_allowlist_and_frozen_files`.
- Exact existing functions modified: none; create verifier CLI entrypoint and helper functions in the new verifier file.
- Exact new APIs used: subprocess git/pytest command runner local to the verifier; no Runtime API.
- Failing-test command: `python3 -m pytest -q tests/test_phase2_verifier.py::test_preflight_branch_head_and_clean_tree tests/test_phase2_verifier.py::test_portable_mode_runs_pytest_only tests/test_phase2_verifier.py::test_final_mode_enforces_allowlist_and_frozen_files`.
- Expected initial failure: `ModuleNotFoundError` or missing verifier CLI behavior.
- Minimal implementation control flow: parse `--mode preflight|portable|final`, check branch/head/clean tree in preflight, make portable run full pytest only, make final enforce allowlist and protected-file diff checks.
- Targeted green command: `python3 -m pytest -q tests/test_phase2_verifier.py`.
- Expected targeted result: all Phase 2 verifier scaffold tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_phase2_verifier.py tests/test_phase1_verifier.py`.
- Commit files: `tools/verify_phase2_minimal_bundle_foundation.py`, `tests/test_phase2_verifier.py`.
- Exact commit message: `test: add phase 2 verifier scaffold`.
- Stop/rollback condition: stop if verifier requires changing Phase 1 verifier/tests, workflow YAML, frozen specs, or the Plan.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 1: Database migration and storage primitives

- Objective: add append-only `revision_outputs`, additive `export_records` columns, byte object APIs, and export audit transaction methods.
- Primary acceptance IDs: P2-010, P2-011, P2-012, P2-013, P2-016, P2-017, P2-018, P2-019, P2-060.
- Exact production files: `ai_drama_runtime/store.py`.
- Exact test files and functions: `tests/test_storyboard_legacy_migration.py::test_revision_outputs_schema_matches_frozen_ddl`, `tests/test_storyboard_legacy_migration.py::test_revision_outputs_public_api_is_append_only`, `tests/test_storyboard_legacy_migration.py::test_export_records_legacy_rows_receive_frozen_defaults`, `tests/test_storyboard_legacy_migration.py::test_phase2_migration_replay_is_idempotent`.
- Exact existing functions modified: `RuntimeStore._init_schema`, `RuntimeStore._ensure_columns`, `write_text_object`, `read_text`, `record_export`, `_export_from_row`.
- Exact new APIs used: `write_bytes_object`, `read_bytes_object`, `insert_revision_outputs_transaction`, `revision_outputs`, `get_revision_output`, `insert_export_record_in_transaction`, `insert_export_record`, `get_export_record`.
- Failing-test command: `python3 -m pytest -q tests/test_storyboard_legacy_migration.py`.
- Expected initial failure: missing `revision_outputs` table, missing additive columns, or missing Store APIs.
- Minimal implementation control flow: add DDL exactly as frozen, backfill legacy export columns conservatively, make object IDs/content hashes equal `SHA256(exact bytes)`, hydrate extended export rows, and make `insert_export_record` delegate to the non-committing transactional method.
- Targeted green command: `python3 -m pytest -q tests/test_storyboard_legacy_migration.py`.
- Expected targeted result: migration, backfill, append-only, and idempotency tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_storyboard_legacy_migration.py tests/test_storyboard_workflow.py`.
- Commit files: `ai_drama_runtime/store.py`, `tests/test_storyboard_legacy_migration.py`.
- Exact commit message: `feat: add phase 2 bundle storage migration`.
- Stop/rollback condition: stop if schema requires a new bundle-export table, an `export_records.status` column, destructive migration, or mutation of protected migration modules.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 2: Deterministic bundle builder and exact bytes

- Objective: build rendered Markdown and bundle manifest bytes deterministically with separate business and full-object hashes.
- Primary acceptance IDs: P2-014, P2-015, P2-030, P2-031, P2-032, P2-033, P2-034, P2-035, P2-036, P2-037, P2-038.
- Exact production files: `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_storyboard_renderer.py::test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash`, `tests/test_storyboard_renderer.py::test_bundle_manifest_uses_canonical_json_v1_bytes`, `tests/test_storyboard_renderer.py::test_bundle_output_metadata_matches_frozen_contract`, `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_creates_both_outputs_transactionally`.
- Exact existing functions modified: none required beyond new private helpers in `RuntimeService`.
- Exact new APIs used: `RuntimeStore.write_bytes_object`, `RuntimeStore.read_bytes_object`.
- Failing-test command: `python3 -m pytest -q tests/test_storyboard_renderer.py::test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash tests/test_storyboard_renderer.py::test_bundle_manifest_uses_canonical_json_v1_bytes tests/test_storyboard_renderer.py::test_bundle_output_metadata_matches_frozen_contract`.
- Expected initial failure: manifest builder helpers do not exist or hashes/bytes do not match frozen contracts.
- Minimal implementation control flow: read exact canonical bytes, call existing renderer without editing renderer files, serialize canonical-json-v1 with deterministic key/order policy and no trailing newline, exclude `revision_id` and `bundle_manifest_hash` from the business preimage, and exclude bundle manifest output from its own manifest output list.
- Targeted green command: `python3 -m pytest -q tests/test_storyboard_renderer.py`.
- Expected targeted result: business hash exclusion, canonical-json-v1 bytes, and frozen output metadata tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_storyboard_renderer.py tests/test_storyboard_canonical_workflow.py`.
- Commit files: `ai_drama_runtime/services.py`, `tests/test_storyboard_renderer.py`, `tests/test_storyboard_canonical_workflow.py`.
- Exact commit message: `feat: add deterministic storyboard bundle manifest`.
- Stop/rollback condition: stop if deterministic bytes require editing `ai_drama_runtime/storyboard_renderer.py`, `ai_drama_runtime/storyboard_canonical.py`, or `ai_drama_runtime/manifest.py`.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 3: Explicit v0.2.0 materialization service

- Objective: implement explicit `artifacts materialize-bundle` service lifecycle for historical `v0.2.0` revisions.
- Primary acceptance IDs: P2-021, P2-022, P2-023, P2-024, P2-025, P2-027, P2-028.
- Exact production files: `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_creates_both_outputs_transactionally`, `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_returns_already_materialized_for_exact_rows`, `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_partial_output_rows`, `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_unexpected_output_combination`.
- Exact existing functions modified: add `RuntimeService.materialize_storyboard_bundle`; no existing public approval/export semantics change in this slice.
- Exact new APIs used: `RuntimeStore.revision_outputs`, `RuntimeStore.insert_revision_outputs_transaction`, `RuntimeStore.get_revision_output`.
- Failing-test command: `python3 -m pytest -q tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_creates_both_outputs_transactionally tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_returns_already_materialized_for_exact_rows tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_partial_output_rows tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_unexpected_output_combination`.
- Expected initial failure: `materialize_storyboard_bundle` missing or returns wrong materialization/conflict behavior.
- Minimal implementation control flow: load revision, validate Storyboard canonical profile, inspect outputs, create both output rows only when zero rows exist, return `ALREADY_MATERIALIZED` for exact complete rows, and raise `BUNDLE_OUTPUT_CONFLICT` for partial/extra/conflicting rows without mutation.
- Targeted green command: `python3 -m pytest -q tests/test_storyboard_canonical_workflow.py`.
- Expected targeted result: explicit materialization lifecycle tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_storyboard_canonical_workflow.py tests/test_storyboard_renderer.py tests/test_storyboard_legacy_migration.py`.
- Commit files: `ai_drama_runtime/services.py`, `tests/test_storyboard_canonical_workflow.py`.
- Exact commit message: `feat: implement storyboard bundle materialization`.
- Stop/rollback condition: stop if implementation must rewrite revisions, overwrite outputs, change approval status, or auto-approve.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 4: v0.2.1 skill package and auto-materialization lifecycle

- Objective: add `v0.2.1` package and auto-materialize new `v0.2.1` revisions immediately before declared validation.
- Primary acceptance IDs: P2-020, P2-026, P2-029, P2-045.
- Exact production files: `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`, `skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/README.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json`, `skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py`, `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_storyboard_canonical_workflow.py::test_v021_auto_materializes_before_declared_validation`, `tests/test_storyboard_canonical_workflow.py::test_v021_materialization_failure_leaves_pending_revision_and_zero_rows`, `tests/test_storyboard_canonical_workflow.py::test_v021_skill_declares_required_bundle_integrity_validator`.
- Exact existing functions modified: `RuntimeService.run_storyboard`.
- Exact new APIs used: `RuntimeService._auto_materialize_storyboard_bundle`, `RuntimeStore.insert_revision_outputs_transaction`.
- Failing-test command: `python3 -m pytest -q tests/test_storyboard_canonical_workflow.py::test_v021_auto_materializes_before_declared_validation tests/test_storyboard_canonical_workflow.py::test_v021_materialization_failure_leaves_pending_revision_and_zero_rows`.
- Expected initial failure: `v0.2.1` package missing or `run_storyboard` validates before auto-materialization.
- Minimal implementation control flow: copy `v0.2.0` files byte-identically, modify only `v0.2.1/skill.json`, persist revision and dependency, call auto-materialization before `run_declared_validators`, persist declared `storyboard_bundle_integrity` result on success, and leave failed revisions pending with `VALIDATION_FAILED`.
- Targeted green command: `python3 -m pytest -q tests/test_storyboard_canonical_workflow.py`.
- Expected targeted result: `v0.2.1` auto-materialization and failure lifecycle tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_storyboard_canonical_workflow.py tests/test_storyboard_workflow.py`.
- Commit files: `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`, `skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/README.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json`, `skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py`, `skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py`, `ai_drama_runtime/services.py`, `tests/test_storyboard_canonical_workflow.py`.
- Exact commit message: `feat: add storyboard v0.2.1 bundle lifecycle`.
- Stop/rollback condition: stop if implementation requires mutating `v0.2.0`, backfilling declared validator rows for `v0.2.0`, or auto-approving.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 5: Bundle integrity checker

- Objective: implement runtime-native `storyboard_bundle_integrity` with frozen check order and error precedence.
- Primary acceptance IDs: P2-039, P2-040, P2-041, P2-042, P2-043, P2-044, P2-046, P2-049.
- Exact production files: `ai_drama_runtime/validators.py`, `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_validators_approval_export.py::test_bundle_integrity_passes_valid_bundle`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_missing_bundle`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_revision_output_hash_mismatch`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_invalid_output_combination`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_renderer_byte_or_metadata_failure`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_manifest_semantic_failure`, `tests/test_validators_approval_export.py::test_v020_uses_live_bundle_integrity_checker`.
- Exact existing functions modified: runtime-native validator dispatch, `run_declared_validators`; add `RuntimeService.check_storyboard_bundle_integrity`.
- Exact new APIs used: `RuntimeStore.revision_outputs`, `RuntimeStore.get_revision_output`, `RuntimeStore.read_bytes_object`.
- Failing-test command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_bundle_integrity_passes_valid_bundle tests/test_validators_approval_export.py::test_bundle_integrity_reports_missing_bundle tests/test_validators_approval_export.py::test_bundle_integrity_reports_revision_output_hash_mismatch tests/test_validators_approval_export.py::test_bundle_integrity_reports_invalid_output_combination tests/test_validators_approval_export.py::test_bundle_integrity_reports_renderer_byte_or_metadata_failure tests/test_validators_approval_export.py::test_bundle_integrity_reports_manifest_semantic_failure tests/test_validators_approval_export.py::test_v020_uses_live_bundle_integrity_checker`.
- Expected initial failure: integrity checker missing or returns wrong symbolic error.
- Minimal implementation control flow: enforce exact output set, verify objects and SHA256s, check logical combination, metadata, renderer bytes, manifest parse/shape/order/output hashes, reconstruct business preimage, then return PASS only on complete success.
- Targeted green command: `python3 -m pytest -q tests/test_validators_approval_export.py -k bundle_integrity`.
- Expected targeted result: all integrity error-precedence tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_validators_approval_export.py tests/test_storyboard_canonical_workflow.py`.
- Commit files: `ai_drama_runtime/validators.py`, `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py`.
- Exact commit message: `feat: add storyboard bundle integrity gates`.
- Stop/rollback condition: stop if required precedence conflicts with frozen stable error codes or requires mutating stored outputs.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 6: Approval gates and v0.2.0 compatibility

- Objective: require materialized bundle integrity PASS for future approvals while preserving existing approved Phase 1 revisions.
- Primary acceptance IDs: P2-047, P2-048, P2-050, P2-051, P2-052, P2-056, P2-057, P2-059.
- Exact production files: `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle`, `tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle`, `tests/test_validators_approval_export.py::test_approval_does_not_implicitly_materialize_bundle`, `tests/test_validators_approval_export.py::test_existing_approved_phase1_revision_is_not_revoked`.
- Exact existing functions modified: `RuntimeService.approve_revision`, `RuntimeService.revision_freshness`.
- Exact new APIs used: `RuntimeService.check_storyboard_bundle_integrity`.
- Failing-test command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle tests/test_validators_approval_export.py::test_approval_does_not_implicitly_materialize_bundle tests/test_validators_approval_export.py::test_existing_approved_phase1_revision_is_not_revoked`.
- Expected initial failure: approval does not require bundle integrity or attempts to materialize implicitly.
- Minimal implementation control flow: leave already-approved historical revisions unchanged, for new Storyboard approvals check freshness and non-bundle validators, call live integrity checker, map missing/invalid bundle to frozen codes, and call approval transaction only after every gate passes.
- Targeted green command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle tests/test_validators_approval_export.py::test_approval_does_not_implicitly_materialize_bundle tests/test_validators_approval_export.py::test_existing_approved_phase1_revision_is_not_revoked`.
- Expected targeted result: future approval gates pass and historical approvals remain intact.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_validators_approval_export.py tests/test_storyboard_workflow.py`.
- Commit files: `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py`, `tests/test_storyboard_workflow.py`.
- Exact commit message: `feat: enforce storyboard approval bundle gates`.
- Stop/rollback condition: stop if approval compatibility would retroactively revoke approved Phase 1 revisions or create bundle outputs.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 7: Export audit and export-provenance-v1

- Objective: extend unified export audit and provenance generation without creating a separate business entity or status column.
- Primary acceptance IDs: P2-061, P2-062, P2-069, P2-077.
- Exact production files: `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent`, `tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion`, `tests/test_validators_approval_export.py::test_formal_review_export_is_atomic`.
- Exact existing functions modified: `RuntimeStore.record_export`, `RuntimeStore._export_from_row`; add provenance helper in `RuntimeService`.
- Exact new APIs used: `RuntimeStore.insert_export_record_in_transaction`, `RuntimeStore.insert_export_record`, `RuntimeService.attach_export_dependency`.
- Failing-test command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion tests/test_validators_approval_export.py::test_formal_review_export_is_atomic`.
- Expected initial failure: provenance/audit metadata missing or diagnostic export can be used as dependency parent.
- Minimal implementation control flow: generate `export-provenance-v1`, store canonical content hash and business manifest hash in `export_records`, reject diagnostic parent use, and keep exported success status out of database state.
- Targeted green command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion tests/test_validators_approval_export.py::test_formal_review_export_is_atomic`.
- Expected targeted result: audit metadata and diagnostic parent rejection tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_validators_approval_export.py tests/test_storyboard_legacy_migration.py`.
- Commit files: `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py`.
- Exact commit message: `feat: extend export audit provenance`.
- Stop/rollback condition: stop if implementation requires a separate bundle-export table, an `export_records.status` column, or dependency-parent semantics for diagnostic exports.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 8: Atomic formal-review and diagnostic export

- Objective: implement same-filesystem atomic export with transactional audit insert, rollback, and compensation semantics.
- Primary acceptance IDs: P2-053, P2-054, P2-055, P2-058, P2-067, P2-068, P2-070, P2-071, P2-072, P2-073, P2-074, P2-075, P2-076, P2-078.
- Exact production files: `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_validators_approval_export.py::test_formal_review_export_is_atomic`, `tests/test_validators_approval_export.py::test_formal_review_export_rolls_back_audit_when_rename_fails`, `tests/test_validators_approval_export.py::test_formal_review_export_compensates_final_directory_when_commit_fails`, `tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion`, `tests/test_validators_approval_export.py::test_formal_review_export_blocks_missing_bundle_before_general_gate`, `tests/test_validators_approval_export.py::test_formal_review_export_blocks_invalid_bundle_before_general_gate`, `tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator`, `tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination`, `tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision`.
- Exact existing functions modified: `RuntimeService.export_storyboard_bundle`, `RuntimeService._export_storyboard_formal_review`, `RuntimeService._export_storyboard_diagnostic`.
- Exact new APIs used: `RuntimeStore.insert_export_record_in_transaction`, `RuntimeService.check_storyboard_bundle_integrity`.
- Failing-test command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_formal_review_export_is_atomic tests/test_validators_approval_export.py::test_formal_review_export_rolls_back_audit_when_rename_fails tests/test_validators_approval_export.py::test_formal_review_export_compensates_final_directory_when_commit_fails tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion tests/test_validators_approval_export.py::test_formal_review_export_blocks_missing_bundle_before_general_gate tests/test_validators_approval_export.py::test_formal_review_export_blocks_invalid_bundle_before_general_gate tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision`.
- Expected initial failure: export writes files non-atomically, lacks transactional audit insert, or lacks diagnostic stale gate.
- Minimal implementation control flow: load revision and validate supported Storyboard canonical profile, inspect `revision_outputs`, raise `BUNDLE_NOT_MATERIALIZED` for zero rows, run bundle integrity for non-empty bundles, raise `BUNDLE_INTEGRITY_FAILED` before general gates on integrity failure, then require approved/FRESH/non-bundle validators and raise `FORMAL_REVIEW_EXPORT_BLOCKED` for those failures, reject existing destination, create sibling staging, write canonical/markdown/provenance/manifest in frozen order, reread and hash, begin DB transaction, insert audit record with `error_code=""`, rename staging to final, commit DB transaction, and only then return CLI `EXPORTED`.
- Targeted green command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_formal_review_export_is_atomic tests/test_validators_approval_export.py::test_formal_review_export_rolls_back_audit_when_rename_fails tests/test_validators_approval_export.py::test_formal_review_export_compensates_final_directory_when_commit_fails tests/test_validators_approval_export.py::test_formal_review_export_records_success_only_after_atomic_completion tests/test_validators_approval_export.py::test_formal_review_export_blocks_missing_bundle_before_general_gate tests/test_validators_approval_export.py::test_formal_review_export_blocks_invalid_bundle_before_general_gate tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision`.
- Expected targeted result: atomic success, gate failure, rename rollback, commit compensation, destination conflict, file byte, and diagnostic tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_validators_approval_export.py tests/test_cli.py`.
- Commit files: `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py`.
- Exact commit message: `feat: add atomic storyboard export`.
- Stop/rollback condition: stop if a successful export record could remain after failed rename/commit, if final directory can remain after DB commit failure, or if staging is not on the same filesystem.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 9: Always-blocked execution export

- Objective: persist blocked execution attempts without creating files or claiming execution readiness.
- Primary acceptance IDs: P2-063, P2-064, P2-065, P2-066, P2-079.
- Exact production files: `ai_drama_runtime/services.py`.
- Exact test files and functions: `tests/test_validators_approval_export.py::test_execution_export_records_block_without_filesystem_writes`, `tests/test_validators_approval_export.py::test_execution_export_persists_blocked_attempt_without_filesystem_writes`.
- Exact existing functions modified: `RuntimeService.export_storyboard_bundle`; add `RuntimeService._record_storyboard_execution_block`.
- Exact new APIs used: `RuntimeStore.insert_export_record`.
- Failing-test command: `python3 -m pytest -q tests/test_validators_approval_export.py::test_execution_export_records_block_without_filesystem_writes tests/test_validators_approval_export.py::test_execution_export_persists_blocked_attempt_without_filesystem_writes`.
- Expected initial failure: execution export creates filesystem output, does not persist attempt, or exits as an error.
- Minimal implementation control flow: inspect bundle status only, write provenance object, call `insert_export_record` with `export_kind="execution"` and `error_code="EXPORT_NOT_EXECUTION_READY"`, skip staging/rename entirely, and return blocked response.
- Targeted green command: `python3 -m pytest -q tests/test_validators_approval_export.py -k execution_export`.
- Expected targeted result: blocked execution audit persists and no filesystem output is created.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_validators_approval_export.py tests/test_cli.py`.
- Commit files: `ai_drama_runtime/services.py`, `tests/test_validators_approval_export.py`.
- Exact commit message: `feat: block storyboard execution export`.
- Stop/rollback condition: stop if implementation needs `execution_ready=true`, target adapters, staging, final directories, or nonzero CLI exit for the blocked audit command.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 10: Exact CLI contracts

- Objective: expose frozen `artifacts outputs`, `artifacts materialize-bundle`, and `artifacts export-bundle` CLI contracts.
- Primary acceptance IDs: P2-080, P2-081, P2-082, P2-083, P2-084, P2-085, P2-086, P2-087, P2-088, P2-089.
- Exact production files: `ai_drama_runtime/cli.py`.
- Exact test files and functions: `tests/test_cli.py::test_artifacts_outputs_returns_frozen_json_contract`, `tests/test_cli.py::test_artifacts_materialize_bundle_returns_frozen_json_contract`, `tests/test_cli.py::test_artifacts_export_bundle_returns_frozen_json_contract`, `tests/test_cli.py::test_artifacts_export_bundle_execution_returns_blocked_json_and_zero_exit`, `tests/test_cli.py::test_artifacts_export_bundle_rejects_unsupported_profile`.
- Exact existing functions modified: `_json`, `build_parser`, `main`.
- Exact new APIs used: `_artifacts_outputs`, `_artifacts_materialize_bundle`, `_artifacts_export_bundle`, `RuntimeService.bundle_outputs`, `RuntimeService.materialize_storyboard_bundle`, `RuntimeService.export_storyboard_bundle`.
- Failing-test command: `python3 -m pytest -q tests/test_cli.py::test_artifacts_outputs_returns_frozen_json_contract tests/test_cli.py::test_artifacts_materialize_bundle_returns_frozen_json_contract tests/test_cli.py::test_artifacts_export_bundle_returns_frozen_json_contract tests/test_cli.py::test_artifacts_export_bundle_execution_returns_blocked_json_and_zero_exit tests/test_cli.py::test_artifacts_export_bundle_rejects_unsupported_profile`.
- Expected initial failure: parser lacks subcommands or JSON shape differs from frozen contracts.
- Minimal implementation control flow: extend the existing `artifacts` group, wire exact arguments, call service methods, print stable JSON, keep existing exit-code classes, and make blocked execution return exit code `0`.
- Targeted green command: `python3 -m pytest -q tests/test_cli.py`.
- Expected targeted result: all exact CLI contract tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q tests/test_cli.py tests/test_validators_approval_export.py`.
- Commit files: `ai_drama_runtime/cli.py`, `tests/test_cli.py`.
- Exact commit message: `feat: add storyboard bundle CLI contracts`.
- Stop/rollback condition: stop if parser changes require a second `artifacts` group or altering existing unrelated CLI contracts.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 11: Adversarial and migration closure

- Objective: close adversarial manifest, hash, migration replay, profile, and gate edge cases without adding new architecture.
- Primary acceptance IDs: P2-098, P2-099, P2-100, P2-101, P2-102, P2-103, P2-104, P2-105, P2-106, P2-107, P2-108, P2-109.
- Exact production files: `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, `ai_drama_runtime/validators.py`, `ai_drama_runtime/cli.py`.
- Exact test files and functions: `tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_partial_output_rows`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_manifest_semantic_failure`, `tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination`, `tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle`, `tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle`, `tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision`, `tests/test_validators_approval_export.py::test_execution_export_persists_blocked_attempt_without_filesystem_writes`, `tests/test_cli.py::test_artifacts_export_bundle_rejects_unsupported_profile`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_revision_output_hash_mismatch`, `tests/test_validators_approval_export.py::test_bundle_integrity_reports_invalid_output_combination`, `tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent`, `tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator`.
- Exact existing functions covered: `RuntimeStore._init_schema`, `RuntimeStore._ensure_columns`, `RuntimeStore.insert_revision_outputs_transaction`, `RuntimeStore.insert_export_record`, `RuntimeService.materialize_storyboard_bundle`, `RuntimeService.check_storyboard_bundle_integrity`, `RuntimeService.export_storyboard_bundle`, `RuntimeService.attach_export_dependency`, runtime-native validator dispatch, `_artifacts_outputs`, `_artifacts_materialize_bundle`, `_artifacts_export_bundle`.
- Exact new APIs used: no new public API beyond those frozen in this plan.
- Failing-test command: `python3 -m pytest -q tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_partial_output_rows tests/test_validators_approval_export.py::test_bundle_integrity_reports_manifest_semantic_failure tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision tests/test_validators_approval_export.py::test_execution_export_persists_blocked_attempt_without_filesystem_writes tests/test_cli.py::test_artifacts_export_bundle_rejects_unsupported_profile tests/test_validators_approval_export.py::test_bundle_integrity_reports_revision_output_hash_mismatch tests/test_validators_approval_export.py::test_bundle_integrity_reports_invalid_output_combination tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator`.
- Expected initial failure: one or more adversarial edge cases returns the wrong stable code or leaves an unsafe file/db state.
- Minimal implementation control flow: adjust existing slice implementations to satisfy frozen precedence and allowlist behavior; do not introduce new tables, schemas, CLI flags, or public methods.
- Targeted green command: `python3 -m pytest -q tests/test_storyboard_canonical_workflow.py::test_materialize_bundle_rejects_partial_output_rows tests/test_validators_approval_export.py::test_bundle_integrity_reports_manifest_semantic_failure tests/test_validators_approval_export.py::test_formal_review_export_rejects_existing_destination tests/test_validators_approval_export.py::test_approval_blocks_missing_bundle tests/test_validators_approval_export.py::test_approval_blocks_invalid_bundle tests/test_validators_approval_export.py::test_diagnostic_export_requires_stale_revision tests/test_validators_approval_export.py::test_execution_export_persists_blocked_attempt_without_filesystem_writes tests/test_cli.py::test_artifacts_export_bundle_rejects_unsupported_profile tests/test_validators_approval_export.py::test_bundle_integrity_reports_revision_output_hash_mismatch tests/test_validators_approval_export.py::test_bundle_integrity_reports_invalid_output_combination tests/test_validators_approval_export.py::test_diagnostic_export_cannot_be_dependency_parent tests/test_validators_approval_export.py::test_formal_review_export_blocks_unapproved_stale_or_failed_validator`.
- Expected targeted result: all Phase 2-specific adversarial and migration tests pass.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q`.
- Commit files: `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, `ai_drama_runtime/validators.py`, `ai_drama_runtime/cli.py`, `tests/test_storyboard_legacy_migration.py`, `tests/test_storyboard_canonical_workflow.py`, `tests/test_validators_approval_export.py`, `tests/test_cli.py`, `tests/test_phase2_verifier.py`.
- Exact commit message: `test: complete storyboard adversarial coverage`.
- Stop/rollback condition: stop if any fix requires changing protected files, weakening tests, or adding a Phase 3 execution feature.
- [ ] Write the failing tests
- [ ] Run exact tests and confirm expected failure
- [ ] Implement minimal production change
- [ ] Run targeted tests
- [ ] Run regression tests
- [ ] Review exact changed-file set
- [ ] Commit only slice files

### Slice 12: Final Phase 2 verifier and acceptance closure

- Objective: run final read-only reviews, complete local and portable/final verification, create final report, push, and verify CI.
- Primary acceptance IDs: P2-005, P2-094, P2-095, P2-096, P2-097, P2-110.
- Exact production files: none.
- Exact verification test file and function: `tests/test_phase2_verifier.py::test_final_mode_enforces_allowlist_and_frozen_files`.
- Exact existing functions modified: none; missing final-verifier behavior is a stop condition.
- Exact new APIs used: no new Runtime API.
- Failing-test command: not applicable; Slice 12 is final verification and report generation only.
- Expected initial failure: not applicable; missing final-verifier behavior is a stop condition.
- Minimal implementation control flow: run Agent E read-only contract review, run Agent F read-only adversarial review, resolve blocker/major/minor findings through green commits, run full local verification, run portable verifier, run final verifier, generate `docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md`, verify the report does not embed its own commit SHA, commit only the report, push normally, verify matching GitHub Actions run conclusion is `success`, and verify remote branch HEAD equals final commit.
- Targeted green command: `python3 -m pytest -q tests/test_phase2_verifier.py::test_final_mode_enforces_allowlist_and_frozen_files`.
- Expected targeted result: final verifier test passes without modifying production or test files.
- Regression command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q && python3 tools/verify_phase2_minimal_bundle_foundation.py --mode portable && python3 tools/verify_phase2_minimal_bundle_foundation.py --mode final`.
- Commit files: `docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md`.
- Exact commit message: `test: add phase 2 verification report`.
- Stop/rollback condition: stop if any final gate fails, report would need to include its own commit SHA, GitHub Actions is not successful for the matching final commit, or remote HEAD differs from final commit.
- [ ] Run Agent E read-only final contract review
- [ ] Run Agent F read-only adversarial review
- [ ] Resolve all accepted findings through green commits
- [ ] Run full pytest, portable verifier, and final verifier
- [ ] Generate and validate the exact verification report
- [ ] Commit only the verification report
- [ ] Push and verify matching GitHub Actions success and remote HEAD

---

## 16. Acceptance Traceability Matrix

| acceptance_id | primary_slice | secondary_regression_coverage | production_file | test_file | test_name_or_pattern | verifier_mode | expected_result | symbolic_error_code |
|---|---:|---|---|---|---|---|---|---|
| P2-001 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_preflight_branch_head_and_clean_tree` | preflight | pass | N/A |
| P2-002 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_preflight_branch_head_and_clean_tree` | preflight | existing baseline = 135 passed | N/A |
| P2-003 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | preflight | only two spec files | N/A |
| P2-004 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | preflight | exact planning diff then plan file | N/A |
| P2-005 | 12 | N/A | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | final | allowlist match | N/A |
| P2-006 | RESERVED | N/A | N/A | N/A | RESERVED | N/A | RESERVED | N/A |
| P2-007 | RESERVED | N/A | N/A | N/A | RESERVED | N/A | RESERVED | N/A |
| P2-008 | RESERVED | N/A | N/A | N/A | RESERVED | N/A | RESERVED | N/A |
| P2-009 | RESERVED | N/A | N/A | N/A | RESERVED | N/A | RESERVED | N/A |
| P2-010 | 1 | N/A | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_revision_outputs_schema_matches_frozen_ddl` | final | columns present | N/A |
| P2-011 | 1 | N/A | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_revision_outputs_schema_matches_frozen_ddl` | final | exact CHECK values | N/A |
| P2-012 | 1 | 2 | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_revision_outputs_schema_matches_frozen_ddl` | final | exact legal outputs | N/A |
| P2-013 | 1 | 2 | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_revision_outputs_schema_matches_frozen_ddl` | final | equal on valid rows | N/A |
| P2-014 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_output_metadata_matches_frozen_contract` | final | rendered_markdown metadata exact | N/A |
| P2-015 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_output_metadata_matches_frozen_contract` | final | bundle_manifest metadata exact | N/A |
| P2-016 | 1 | 3 | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_revision_outputs_public_api_is_append_only` | final | no mutation operation | N/A |
| P2-017 | 1 | N/A | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_phase2_migration_replay_is_idempotent` | final | no data loss | N/A |
| P2-018 | 1 | N/A | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_phase2_migration_replay_is_idempotent` | final | idempotent replay | N/A |
| P2-019 | 1 | N/A | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_revision_outputs_schema_matches_frozen_ddl` | final | reject invalid schema | N/A |
| P2-020 | 4 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_v021_auto_materializes_before_declared_validation` | final | pending or materialized lifecycle exact | BUNDLE_NOT_MATERIALIZED |
| P2-021 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_creates_both_outputs_transactionally` | final | explicit materialize required | BUNDLE_NOT_MATERIALIZED |
| P2-022 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_creates_both_outputs_transactionally` | final | two rows created | N/A |
| P2-023 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_returns_already_materialized_for_exact_rows` | final | already materialized | N/A |
| P2-024 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_rejects_partial_output_rows` | final | conflict rejected | BUNDLE_OUTPUT_CONFLICT |
| P2-025 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_rejects_unexpected_output_combination` | final | conflict rejected | BUNDLE_OUTPUT_CONFLICT |
| P2-026 | 4 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_v021_materialization_failure_leaves_pending_revision_and_zero_rows` | final | zero rows and failed run | BUNDLE_NOT_MATERIALIZED |
| P2-027 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_creates_both_outputs_transactionally` | final | revision unchanged | N/A |
| P2-028 | 3 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_returns_already_materialized_for_exact_rows` | final | no overwrite | N/A |
| P2-029 | 4 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_v021_materialization_failure_leaves_pending_revision_and_zero_rows` | final | no retry and no approval | N/A |
| P2-030 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash` | final | stable business hash | N/A |
| P2-031 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash` | final | stable business hash | N/A |
| P2-032 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash` | final | business hash stable | N/A |
| P2-033 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_manifest_uses_canonical_json_v1_bytes` | final | exact bytes | N/A |
| P2-034 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_manifest_business_hash_excludes_revision_id_and_self_hash` | final | separate hashes | N/A |
| P2-035 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_creates_both_outputs_transactionally` | final | exact byte hash | N/A |
| P2-036 | 2 | N/A | `ai_drama_runtime/store.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_creates_both_outputs_transactionally` | final | equal hashes | N/A |
| P2-037 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_manifest_uses_canonical_json_v1_bytes` | final | deterministic order | N/A |
| P2-038 | 2 | N/A | `ai_drama_runtime/services.py` | `tests/test_storyboard_renderer.py` | `test_bundle_output_metadata_matches_frozen_contract` | final | exact metadata | N/A |
| P2-039 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_revision_output_hash_mismatch` | final | reject confusion | REVISION_OUTPUT_HASH_MISMATCH |
| P2-040 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_passes_valid_bundle` | final | PASS | N/A |
| P2-041 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_missing_bundle` | final | FAIL | BUNDLE_NOT_MATERIALIZED |
| P2-042 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_revision_output_hash_mismatch` | final | FAIL | REVISION_OUTPUT_HASH_MISMATCH |
| P2-043 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_renderer_byte_or_metadata_failure` | final | FAIL | BUNDLE_INTEGRITY_FAILED |
| P2-044 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_manifest_semantic_failure` | final | FAIL | BUNDLE_INTEGRITY_FAILED |
| P2-045 | 4 | N/A | `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json` | `tests/test_storyboard_canonical_workflow.py` | `test_v021_skill_declares_required_bundle_integrity_validator` | final | required validator present | N/A |
| P2-046 | 5 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_v020_uses_live_bundle_integrity_checker` | final | live check invoked | N/A |
| P2-047 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_missing_bundle` | final | block approval | BUNDLE_NOT_MATERIALIZED |
| P2-048 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_invalid_bundle` | final | block approval | BUNDLE_INTEGRITY_FAILED |
| P2-049 | 5 | N/A | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_manifest_semantic_failure` | final | stable code returned | BUNDLE_INTEGRITY_FAILED |
| P2-050 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_existing_approved_phase1_revision_is_not_revoked` | final | approved remains approved | N/A |
| P2-051 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_invalid_bundle` | final | PASS required | BUNDLE_INTEGRITY_FAILED |
| P2-052 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_missing_bundle` | final | bundle required | BUNDLE_NOT_MATERIALIZED |
| P2-053 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_records_success_only_after_atomic_completion` | final | CLI EXPORTED only after rename and DB commit | N/A |
| P2-054 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_blocks_missing_bundle_before_general_gate` | final | block export | BUNDLE_NOT_MATERIALIZED |
| P2-055 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_blocks_invalid_bundle_before_general_gate` | final | block export | BUNDLE_INTEGRITY_FAILED |
| P2-056 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_does_not_implicitly_materialize_bundle` | final | no auto materialization | N/A |
| P2-057 | 6 | `test_approval_blocks_invalid_bundle` | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_missing_bundle` | final | expected code | BUNDLE_NOT_MATERIALIZED / BUNDLE_INTEGRITY_FAILED |
| P2-058 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_blocks_unapproved_stale_or_failed_validator` | final | export blocked without final directory | FORMAL_REVIEW_EXPORT_BLOCKED |
| P2-059 | 6 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_existing_approved_phase1_revision_is_not_revoked` | final | unchanged | N/A |
| P2-060 | 1 | 7 | `ai_drama_runtime/store.py` | `tests/test_storyboard_legacy_migration.py` | `test_export_records_legacy_rows_receive_frozen_defaults` | final | backfill correct | N/A |
| P2-061 | 7 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_records_success_only_after_atomic_completion` | final | exact content hash retained | N/A |
| P2-062 | 7 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_records_success_only_after_atomic_completion` | final | business hash retained | N/A |
| P2-063 | 9 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_execution_export_persists_blocked_attempt_without_filesystem_writes` | final | destination stored | EXPORT_NOT_EXECUTION_READY |
| P2-064 | 9 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_execution_export_persists_blocked_attempt_without_filesystem_writes` | final | canonical hash stored | EXPORT_NOT_EXECUTION_READY |
| P2-065 | 9 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_execution_export_persists_blocked_attempt_without_filesystem_writes` | final | provenance stored | EXPORT_NOT_EXECUTION_READY |
| P2-066 | 9 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_execution_export_persists_blocked_attempt_without_filesystem_writes` | final | blocked with code | EXPORT_NOT_EXECUTION_READY |
| P2-067 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_diagnostic_export_requires_stale_revision` | final | reject FRESH diagnostic | DIAGNOSTIC_EXPORT_REQUIRES_STALE |
| P2-068 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_diagnostic_export_requires_stale_revision` | final | succeeds | N/A |
| P2-069 | 7 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_diagnostic_export_cannot_be_dependency_parent` | final | reject parent use | DIAGNOSTIC_EXPORT_NOT_PARENTABLE |
| P2-070 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_rejects_existing_destination` | final | destination conflict | EXPORT_DESTINATION_EXISTS |
| P2-071 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_is_atomic` | final | same filesystem staging | N/A |
| P2-072 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_is_atomic` | final | manifest last | N/A |
| P2-073 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_records_success_only_after_atomic_completion` | final | final rename and DB commit both required | N/A |
| P2-074 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_rolls_back_audit_when_rename_fails` | final | no partial output and no audit on rename failure | N/A |
| P2-075 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_is_atomic` | final | exact file bytes | N/A |
| P2-076 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_is_atomic` | final | exact file bytes | N/A |
| P2-077 | 7 | 8 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_is_atomic` | final | provenance separate | N/A |
| P2-078 | 8 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_compensates_final_directory_when_commit_fails` | final | final directory removed if DB commit fails | N/A |
| P2-079 | 9 | N/A | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_execution_export_persists_blocked_attempt_without_filesystem_writes` | final | record only no dir | EXPORT_NOT_EXECUTION_READY |
| P2-080 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_outputs_returns_frozen_json_contract` | final | exact outputs JSON | N/A |
| P2-081 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_materialize_bundle_returns_frozen_json_contract` | final | exact materialize JSON | N/A |
| P2-082 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_export_bundle_returns_frozen_json_contract` | final | exact export JSON | N/A |
| P2-083 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_export_bundle_execution_returns_blocked_json_and_zero_exit` | final | same exit codes | N/A |
| P2-084 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_export_bundle_rejects_unsupported_profile` | final | stable rejection | BUNDLE_PROFILE_UNSUPPORTED |
| P2-085 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_outputs_returns_frozen_json_contract` | final | exact parsing | N/A |
| P2-086 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_outputs_returns_frozen_json_contract` | final | status and hashes present | N/A |
| P2-087 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_outputs_returns_frozen_json_contract` | final | byte-stable JSON | N/A |
| P2-088 | 10 | N/A | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_export_bundle_returns_frozen_json_contract` | final | no drift | N/A |
| P2-089 | 10 | 8 | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_export_bundle_returns_frozen_json_contract` | final | files created only when allowed | N/A |
| P2-090 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_preflight_branch_head_and_clean_tree` | preflight | fail preflight | N/A |
| P2-091 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_preflight_branch_head_and_clean_tree` | preflight | fail preflight | N/A |
| P2-092 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_preflight_branch_head_and_clean_tree` | preflight | fail preflight | N/A |
| P2-093 | 0 | 12 | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_portable_mode_runs_pytest_only` | portable | PASS | N/A |
| P2-094 | 12 | N/A | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | final | PASS | N/A |
| P2-095 | 12 | N/A | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | final | fail final | N/A |
| P2-096 | 12 | N/A | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | final | unchanged | N/A |
| P2-097 | 12 | N/A | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | final | unchanged packages | N/A |
| P2-098 | 11 | 3 | `ai_drama_runtime/services.py` | `tests/test_storyboard_canonical_workflow.py` | `test_materialize_bundle_rejects_partial_output_rows` | final | reject conflict | BUNDLE_OUTPUT_CONFLICT |
| P2-099 | 11 | 5 | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_manifest_semantic_failure` | final | reject malformed bundle | BUNDLE_INTEGRITY_FAILED |
| P2-100 | 11 | 8 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_rejects_existing_destination` | final | reject collision | EXPORT_DESTINATION_EXISTS |
| P2-101 | 11 | 6 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_missing_bundle` | final | reject missing bundle | BUNDLE_NOT_MATERIALIZED |
| P2-102 | 11 | 6 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_approval_blocks_invalid_bundle` | final | reject bad bundle | BUNDLE_INTEGRITY_FAILED |
| P2-103 | 11 | 8 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_diagnostic_export_requires_stale_revision` | final | reject FRESH diagnostic | DIAGNOSTIC_EXPORT_REQUIRES_STALE |
| P2-104 | 11 | 9 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_execution_export_persists_blocked_attempt_without_filesystem_writes` | final | always blocked | EXPORT_NOT_EXECUTION_READY |
| P2-105 | 11 | 10 | `ai_drama_runtime/cli.py` | `tests/test_cli.py` | `test_artifacts_export_bundle_rejects_unsupported_profile` | final | reject unsupported profile | BUNDLE_PROFILE_UNSUPPORTED |
| P2-106 | 11 | 5 | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_revision_output_hash_mismatch` | final | reject bad hash | REVISION_OUTPUT_HASH_MISMATCH |
| P2-107 | 11 | 5 | `ai_drama_runtime/validators.py` | `tests/test_validators_approval_export.py` | `test_bundle_integrity_reports_invalid_output_combination` | final | reject invalid combination | REVISION_OUTPUT_COMBINATION_INVALID |
| P2-108 | 11 | 7 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_diagnostic_export_cannot_be_dependency_parent` | final | reject parent use | DIAGNOSTIC_EXPORT_NOT_PARENTABLE |
| P2-109 | 11 | 8 | `ai_drama_runtime/services.py` | `tests/test_validators_approval_export.py` | `test_formal_review_export_blocks_unapproved_stale_or_failed_validator` | final | block formal review | FORMAL_REVIEW_EXPORT_BLOCKED |
| P2-110 | 12 | N/A | `tools/verify_phase2_minimal_bundle_foundation.py` | `tests/test_phase2_verifier.py` | `test_final_mode_enforces_allowlist_and_frozen_files` | final | full PASS | N/A |

---

## 17. Verification Commands

Existing baseline = `135 passed`.

Execution Start preflight:

```bash
test "$(git branch --show-current)" = "test/phase2-minimal-bundle-foundation"
test "$(git rev-parse HEAD)" = "$EXECUTION_START_COMMIT"
git merge-base --is-ancestor d9f13967d90ae0b2829c3182dd0aebe85c495daf "$EXECUTION_START_COMMIT"
git merge-base --is-ancestor f933182a3db4b3f03de31b4241da29e5be9e3fdd "$EXECUTION_START_COMMIT"
git merge-base --is-ancestor 68283d41f6db549326979120de9881c995d14a41 "$EXECUTION_START_COMMIT"
test "$(git diff --name-only 68283d41f6db549326979120de9881c995d14a41..$EXECUTION_START_COMMIT)" = "docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md"
test -z "$(git status --short)"
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
```

The existing baseline expectation is exactly `135 passed`. The final expectation is all existing and new tests pass; do not freeze a final numeric test count before Phase 2 implementation adds the new tests.

Implementation changed-file allowlist from Execution Start Commit:

```bash
python3 - "$EXECUTION_START_COMMIT" <<'PY'
import subprocess
import sys

base = sys.argv[1]
allowed = {
    "ai_drama_runtime/cli.py",
    "ai_drama_runtime/services.py",
    "ai_drama_runtime/store.py",
    "ai_drama_runtime/validators.py",
    "docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/README.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/SKILL.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/contracts/storyboard-canonical-contract-v1.md",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/schemas/storyboard-canonical.schema.json",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py",
    "skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py",
    "tests/test_cli.py",
    "tests/test_phase2_verifier.py",
    "tests/test_storyboard_canonical_workflow.py",
    "tests/test_storyboard_legacy_migration.py",
    "tests/test_storyboard_renderer.py",
    "tests/test_storyboard_workflow.py",
    "tests/test_validators_approval_export.py",
    "tools/verify_phase2_minimal_bundle_foundation.py",
}
changed = set(
    filter(
        None,
        subprocess.check_output(
            ["git", "diff", "--name-only", f"{base}..HEAD"],
            text=True,
        ).splitlines(),
    )
)
extra = sorted(changed - allowed)
if extra:
    raise SystemExit("disallowed changed files: " + ", ".join(extra))
PY
```

Protected-file checks:

```bash
git diff --quiet "$EXECUTION_START_COMMIT"..HEAD -- \
  docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md \
  docs/superpowers/specs/2026-06-29-phase-2-minimal-bundle-foundation-design.md \
  docs/superpowers/specs/2026-06-29-phase-2-agent-execution-acceptance-contract.md \
  docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md \
  docs/testing/storyboard-workflow-verification/storyboard-verification-report.md \
  docs/testing/storyboard-workflow-verification/storyboard-verification-report.json \
  ai_drama_runtime/manifest.py \
  ai_drama_runtime/storyboard_canonical.py \
  ai_drama_runtime/storyboard_renderer.py \
  ai_drama_runtime/storyboard_migration.py \
  tools/verify_phase1_storyboard_canonicalization.py \
  tools/verify_storyboard_workflow.py \
  tests/test_phase1_verifier.py \
  tests/acceptance/test_storyboard_workflow_acceptance.py \
  .github/workflows/storyboard-workflow-verification.yml
git diff --quiet "$EXECUTION_START_COMMIT"..HEAD -- skills/ai-drama-storyboard-design-skill/v0.1.0
git diff --quiet "$EXECUTION_START_COMMIT"..HEAD -- skills/ai-drama-storyboard-design-skill/v0.2.0
git diff --quiet "$EXECUTION_START_COMMIT"..HEAD -- skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4
```

Per-slice targeted tests:

```bash
python3 -m pytest -q tests/test_phase2_verifier.py
python3 -m pytest -q tests/test_storyboard_legacy_migration.py
python3 -m pytest -q tests/test_storyboard_renderer.py
python3 -m pytest -q tests/test_storyboard_canonical_workflow.py
python3 -m pytest -q tests/test_validators_approval_export.py
python3 -m pytest -q tests/test_storyboard_workflow.py
python3 -m pytest -q tests/test_cli.py
```

Migration verification:

```bash
python3 migration/tools/verify_migration.py
```

Py_compile:

```bash
python3 -m py_compile \
  migration/tools/verify_migration.py \
  tools/verify_phase2_minimal_bundle_foundation.py \
  ai_drama_runtime/__init__.py \
  ai_drama_runtime/acceptance.py \
  ai_drama_runtime/cli.py \
  ai_drama_runtime/manifest.py \
  ai_drama_runtime/parser.py \
  ai_drama_runtime/registry.py \
  ai_drama_runtime/request.py \
  ai_drama_runtime/runtime.py \
  ai_drama_runtime/script_validator.py \
  ai_drama_runtime/services.py \
  ai_drama_runtime/store.py \
  ai_drama_runtime/storyboard_canonical.py \
  ai_drama_runtime/storyboard_migration.py \
  ai_drama_runtime/storyboard_renderer.py \
  ai_drama_runtime/validators.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/common.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_artifact_integrity.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_assumptions_and_extensions.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_core_story_beats.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_coverage_evidence.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_creator_presentation.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_genericity.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_handoff_contract.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_markdown_json_equivalence.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_schema.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/validate_source_claim_audit.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/script_revision_structure.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/common.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_genericity.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_continuity.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_duration.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_source_coverage.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/validate_storyboard_structure.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/common_canonical.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/native_storyboard_canonical.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_canonical_schema.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_continuity.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_duration.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_identity.py \
  skills/ai-drama-storyboard-design-skill/v0.2.1/validators/validate_storyboard_shot_order.py
```

Full pytest:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q
```

Portable Phase 2 verifier:

```bash
python3 tools/verify_phase2_minimal_bundle_foundation.py --mode portable
```

Final Phase 2 verifier:

```bash
python3 tools/verify_phase2_minimal_bundle_foundation.py --mode final
```

Diff check:

```bash
git diff --check
```

GitHub Actions final gate:

```bash
FINAL_COMMIT="$(git rev-parse HEAD)"

git push origin test/phase2-minimal-bundle-foundation

RUN_JSON="$(
  gh run list \
    --commit "$FINAL_COMMIT" \
    --workflow storyboard-workflow-verification.yml \
    --limit 10 \
    --json databaseId,headSha,status,conclusion,url,workflowName,createdAt
)"

RUN_ID="$(
  printf '%s' "$RUN_JSON" |
  python3 -c '
import json
import sys

runs = json.load(sys.stdin)
expected = sys.argv[1]
matches = [run for run in runs if run["headSha"] == expected]
if len(matches) != 1:
    raise SystemExit(
        "expected exactly one matching workflow run, found %d" % len(matches)
    )
print(matches[0]["databaseId"])
' "$FINAL_COMMIT"
)"

test -n "$RUN_ID"
gh run watch "$RUN_ID" --exit-status

test "$(
  gh run view "$RUN_ID" --json headSha --jq .headSha
)" = "$FINAL_COMMIT"

test "$(
  gh run view "$RUN_ID" --json conclusion --jq .conclusion
)" = "success"

test "$(
  git ls-remote origin \
    refs/heads/test/phase2-minimal-bundle-foundation |
  awk '{print $1}'
)" = "$FINAL_COMMIT"
```

Final expected result:

- all existing and new tests pass

---

## 18. Commit Strategy

### A. Plan Freeze / Execution Start Commit

Only file:

- `docs/superpowers/plans/2026-06-29-phase-2-minimal-bundle-foundation-implementation-plan.md`

Commit message:

- `docs: add phase 2 minimal bundle implementation plan`

### B. Green implementation slice commits

- `test: add phase 2 verifier scaffold`
- `feat: add phase 2 bundle storage migration`
- `feat: add deterministic storyboard bundle manifest`
- `feat: implement storyboard bundle materialization`
- `feat: add storyboard v0.2.1 bundle lifecycle`
- `feat: add storyboard bundle integrity gates`
- `feat: enforce storyboard approval bundle gates`
- `feat: extend export audit provenance`
- `feat: add atomic storyboard export`
- `feat: block storyboard execution export`
- `feat: add storyboard bundle CLI contracts`
- `feat: complete storyboard adversarial coverage`

### C. Final verification report commit

Exact report file:

- `docs/superpowers/reports/2026-06-30-phase-2-minimal-bundle-foundation-verification.md`

Commit message:

- `test: add phase 2 verification report`

The report must not contain its own commit SHA.

---

## 19. Stop Conditions

Stop and report if any of the following occurs:

- a frozen contract stop condition is triggered
- a required file falls outside the approved allowlist
- the frozen schema or JSON contract is ambiguous
- the existing Runtime API cannot support the behavior without redesign
- a Phase 3 feature becomes necessary
- baseline tests regress
- any frozen document or protected Skill version changes
- implementation requires modifying `ai_drama_runtime/manifest.py`
- implementation requires modifying `v0.1.0` or `v0.2.0`
- implementation requires modifying `tools/verify_phase1_storyboard_canonicalization.py`, `tools/verify_storyboard_workflow.py`, or `tests/test_phase1_verifier.py`

---

## 20. Final Implementation Completion Output

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
