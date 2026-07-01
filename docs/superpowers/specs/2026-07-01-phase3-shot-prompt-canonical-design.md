# Phase 3 Shot Prompt Canonical Foundation Design Spec

Document Status: DESIGN_SPEC_PENDING_USER_REVIEW

Date: 2026-07-01
Phase: Phase 3 v1
Repository: `Java-zengzhiwen/ai-drama`
Branch: `test/phase2-minimal-bundle-foundation`
Authority Baseline: staged `Phase 3 v1 Revised Design Decisions`

This document is the formal Phase 3 v1 Design Spec. It is not an
Implementation Plan and does not authorize code implementation, database
migration, Phase 4 Asset Binding, execution planning, target adapters, or
generation runs.

## 1. Scope

Phase 3 v1 turns an approved and fresh Storyboard Revision into a canonical,
reviewable Shot Prompt Set:

```text
Approved + Fresh Storyboard Revision
-> Shot Prompt Set Artifact
-> Shot Prompt Set Revision
-> Validate
-> Deterministic Render
-> Bundle Materialization
-> Human Review
-> Set-level Approval
-> Phase 4 Asset Binding Gate
```

Phase 3 v1 is responsible for:

- Shot Prompt Set Artifact and Revision identity.
- Stable one-to-one coverage of every source Storyboard shot.
- Structured generation intent in Canonical JSON.
- Abstract asset requirements for Phase 4.
- Dialogue performance, lip-sync intent, and relative timing intent.
- Basic Shot/Entity-level continuity.
- Platform-neutral positive and negative prompt rendering.
- Bundle outputs, validation reports, review material, qualification evidence,
  and approval gates.

Phase 3 v1 is not responsible for concrete `asset_id`, file path, URL, file
hash, upload ID, target platform syntax, model parameters, LibTV/Agnes nodes,
execution DAGs, precise timecodes, TTS voices, generated media, Candidate Runs,
Execution Runs, or `execution_ready=true`.

Phase boundaries:

- Phase 4 binds concrete assets to Phase 3 abstract slots.
- Phase 5 compiles timing and execution planning.
- Phase 6 adapts neutral prompts to target platforms.
- Phase 7 ingests generated results and QC evidence.
- Phase 8 exposes production UI workflows.

## 2. Existing-System Integration

Phase 3 extends the current Runtime instead of creating parallel governance.
The relevant existing implementation points are:

- `ai_drama_runtime/store.py`: owns `artifacts`, `runs`, `input_snapshots`,
  `revisions`, `revision_dependencies`, `validation_results`,
  `approval_records`, `workflow_gate_records`, `revision_outputs`, and
  `export_records`.
- `ai_drama_runtime/services.py`: owns run orchestration, approval,
  recursive freshness, Storyboard bundle materialization, bundle integrity,
  formal-review export, diagnostic export, and blocked execution audit.
- `ai_drama_runtime/validators.py`: owns declared validators plus
  runtime-native validation such as source freshness and bundle integrity.
- `ai_drama_runtime/storyboard_canonical.py`: defines canonical JSON parsing,
  duplicate-key rejection, deterministic serialization, schema validation, and
  canonical content hashing for Storyboard.
- `ai_drama_runtime/storyboard_renderer.py`: defines the current deterministic
  Storyboard renderer pattern and renderer ID/version locking.
- `ai_drama_runtime/storyboard_migration.py`: defines legacy Storyboard
  migration preview and confirmation behavior.
- `ai_drama_runtime/cli.py`: exposes run, approval, materialization, export,
  and render commands.
- `tools/verify_phase2_minimal_bundle_foundation.py`: captures the Phase 2
  verification shape for branch checks, allowlists, `git diff --check`, and
  pytest.
- `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json`: declares the
  canonical Storyboard profile and required runtime-native bundle integrity
  validator.

Existing objects to reuse:

- Artifact: `artifacts` remains the logical artifact family table.
- Revision: `revisions` remains the immutable content record table.
- Revision Dependency: `revision_dependencies` records Shot Prompt ->
  Storyboard dependency with parent hash and approval record reference.
- Approval: `approval_records` remains append-only approval/rejection evidence.
- Gate: `workflow_gate_records` remains the blocked workflow gate table.
- Audit Event: current append-only audit evidence stays in `approval_records`,
  `workflow_gate_records`, `export_records`, and `runs`; Phase 3 v1 does not add
  a generic audit-event table.
- Run: `runs` remains the operation execution record for Runtime calls.
- Bundle member persistence: `revision_outputs` remains the only formal bundle
  member table.
- Export audit: `export_records` remains the single export audit trail.

Phase 3 must not duplicate these with new governance tables unless the table is
for a genuinely new domain object, such as review records.

## 3. Artifact And Revision Model

Artifact identity:

- A Shot Prompt Set Artifact represents exactly one
  `source Storyboard Revision + shot prompt scope`.
- One Shot Prompt Set Artifact may have multiple immutable Revisions.
- Prompt intent changes create a new Shot Prompt Set Revision; they do not
  require a new Storyboard Revision.
- Scope is part of Artifact identity. The recommended v1 scope enum is
  `set`, `scene`, `shot_range`, with v1 production use defaulting to `set`.

Recommended deterministic artifact identity:

```text
artifact_type = shot_prompt_set
artifact_id = shot-prompt-set:{project_id}:{chapter_id}:{source_storyboard_revision_id}:{scope_key}
```

Revision dependency:

- Each Shot Prompt Revision stores a direct `revision_dependencies` row to the
  exact source Storyboard Revision.
- The dependency stores the parent Storyboard content hash and approval record
  ID visible at creation time.
- Renderer, validator, review renderer, and Phase 4 gate load the exact source
  Storyboard Revision. They must not infer source facts from copied prompt data.

Baseline uniqueness:

- The existing `one_current_approved_revision` index enforces one approved
  Revision per Artifact.
- The Phase 4 baseline is derived, not stored as a separate authority:
  `approved + fresh + not superseded + not revoked + bundle integrity PASS +
  no open blocking review`.
- When a newer Revision in the same Artifact is approved, the older approved
  Revision is superseded by existing approval status semantics plus append-only
  approval evidence.
- When the source Storyboard approved baseline changes, recursive freshness
  makes dependent Shot Prompt Revisions stale.

## 4. Canonical Schema

Schema identity:

- `schema_version`: required, exact v1 value
  `shot-prompt-canonical-v1`.
- `content_profile`: stored on the Revision as the profile name
  `shot-prompt-canonical-v1`.
- Schema version changes are required for field removals, enum changes,
  incompatible validation changes, or renderer input contract changes.

Top-level conceptual schema:

```json
{
  "schema_version": "shot-prompt-canonical-v1",
  "source_storyboard_revision_id": "REVISION_ID",
  "render_language": "zh-Hans",
  "renderer": {
    "profile_id": "shot_prompt_standard",
    "version": "1.0.0"
  },
  "set_defaults": {},
  "items": []
}
```

Required top-level fields:

- `schema_version`: required string.
- `source_storyboard_revision_id`: required string; must match the
  `revision_dependencies` parent.
- `render_language`: required enum, initially `zh-Hans` or `en`; one formal
  language per Revision.
- `renderer.profile_id`: required string; no version range.
- `renderer.version`: required exact string.
- `set_defaults`: required object; may be empty.
- `items`: required array; one item per source Storyboard shot.

Item schema:

```json
{
  "shot_id": "SHOT_001",
  "asset_reference_slots": [],
  "shared_intent": {},
  "image_intent": {},
  "video_intent": {},
  "dialogue_intents": [],
  "continuity": [],
  "negative_constraints": []
}
```

Item fields:

- `shot_id`: required; must match the source Storyboard shot at the same
  ordinal position.
- `asset_reference_slots`: required array, possibly empty; contains only
  abstract entity requirements.
- `shared_intent`: required object; common style, performance, framing, mood,
  and fact-safe generation intent.
- `image_intent`: optional object; required before formal validation if the
  item needs image output and no `video_intent` exists.
- `video_intent`: optional object; required before formal validation if the
  item needs video output and no `image_intent` exists.
- `dialogue_intents`: required array when `video_intent` exists; otherwise
  optional empty array.
- `continuity`: required array, possibly empty; Shot/Entity-level continuity.
- `negative_constraints`: required array, possibly empty; explicit negative
  generation constraints.

Draft versus formal validation:

- Draft may temporarily contain only `shared_intent`.
- Formal validation, materialization, approval, and Phase 4 gate require each
  item to contain `image_intent` or `video_intent`.
- Formal validation requires strict coverage of all Storyboard shots in order.
- Language consistency is only lint/warning, not a blocking error.

Allowed small enums:

- `render_language`: `zh-Hans`, `en`.
- `requirement`: `required`, `optional`.
- `modality_usage`: `image`, `video`.
- `purpose`: `identity`, `costume`, `scene_layout`, `prop_identity`,
  `prop_state`, `keyframe_reference`, `other`.
- `continuity.scope`: `set_baseline`, `previous_occurrence`, `specific_shot`.
- `relative_timing`: `immediate`, `after_brief_pause`, `after_action_cue`,
  `after_reaction_cue`, `after_previous_complete`, `interrupt_previous`,
  `overlap_previous`.
- `speaker_visibility`: `visible`, `partially_visible`, `off_screen`,
  `narration`, `inner_voice`.

Forbidden Canonical fields:

- Concrete `asset_id`, URL, filesystem path, upload ID, storage object path, or
  external file hash as asset binding data.
- Platform-specific model names, sampler parameters, node IDs, LibTV/Agnes
  fields, execution graph fields, or `execution_ready`.
- Exact dialogue text copies from Storyboard.
- Exact timecodes.
- Arbitrary extension fields outside the versioned schema.
- Full editable positive or negative prompt text as business authority.

Storyboard facts that must not be copied as editable authority:

- Storyboard character list, scene facts, prop facts, core action facts,
  dialogue text, speakers, duration, narrative purpose, and frozen continuity
  facts.
- The Shot Prompt Canonical may reference `shot_id`, `source_dialogue_ref`, and
  entity IDs, but the authoritative facts remain in the source Storyboard
  Revision.

## 5. Asset Requirements

Asset slots describe abstract reference needs. They do not bind concrete assets.

Entity source validation:

- `entity_type` enum: `character`, `scene`, `prop`.
- `entity_id` must exist in the source Storyboard Revision or its approved
  upstream canon inputs as referenced by the Storyboard.
- Non-business atmosphere, such as dust, haze, or light bloom, belongs in
  generation intent, not asset slots.

Canonical slot structure:

```json
{
  "entity_type": "character",
  "entity_id": "CHAR_SHEN_QINGHE",
  "purposes": [
    {
      "purpose": "identity",
      "requirement": "required",
      "modality_usage": ["image", "video"],
      "usage_note": "stable face reference"
    }
  ]
}
```

Rules:

- v1 purpose enum is small and coarse-grained:
  `identity`, `costume`, `scene_layout`, `prop_identity`, `prop_state`,
  `keyframe_reference`, `other`.
- `other` requires `usage_note`.
- Every purpose declares `requirement` and `modality_usage`.
- Same shot plus same entity has one slot that may include multiple purposes.
- Canonical does not require empty slots for every Storyboard entity.
- Runtime may produce diagnostics for high-risk omitted entities, but absence
  of a low-risk entity slot is not itself a blocking error.

Derived `slot_id`:

```text
slot_id = shot_id + ":" + entity_type + ":" + entity_id
```

`slot_id` is deterministic Runtime output. It is not author-maintained and must
not be treated as an independent business fact.

Shot/Entity continuity:

- Continuity is Shot/Entity level, not purpose level.
- Continuity may reference affected purposes.
- `specific_shot` continuity requires `source_shot_id`.

Formal `asset-requirements.json` structure:

```json
{
  "schema_version": "asset-requirements-v1",
  "shot_prompt_revision_id": "REVISION_ID",
  "source_storyboard_revision_id": "REVISION_ID",
  "requirements": [
    {
      "shot_id": "SHOT_001",
      "slot_id": "SHOT_001:character:CHAR_SHEN_QINGHE",
      "entity_type": "character",
      "entity_id": "CHAR_SHEN_QINGHE",
      "purposes": [],
      "continuity": []
    }
  ]
}
```

Phase 4 consumption contract:

- Phase 4 reads `asset-requirements.json` as the formal abstract binding input.
- Phase 4 may add concrete asset binding data in Phase 4-owned records.
- Phase 4 must not modify Phase 3 Canonical, rendered prompts, or manifest.

## 6. Dialogue And Lip Sync

Storyboard remains the authority for dialogue text and speaker identity.
Shot Prompt stores only performance intent.

`source_dialogue_ref`:

- Required inside each `dialogue_intents` item when `video_intent` exists.
- Must identify the source Storyboard dialogue entry without copying text.
- Must not point to another shot.

Dialogue intent fields:

- `source_dialogue_ref`: required.
- `lip_sync_required`: required boolean.
- `speaker_visibility`: required enum.
- `delivery`: required object containing emotion, pace, volume, articulation,
  gaze, expression, and gesture intent.
- `relative_timing`: required enum.
- `post_dialogue_hold`: optional enum `none`, `brief`, `sustained`.

Coverage:

- If `video_intent` exists, `dialogue_intents` strictly covers all Storyboard
  dialogue entries for that shot, one-to-one and in order.
- Voiceover, narration, and inner voice are represented with
  `speaker_visibility=off_screen`, `narration`, or `inner_voice` and may set
  `lip_sync_required=false`.
- Image-only items do not require `dialogue_intents`.

Forbidden:

- Dialogue original text copies.
- TTS voice IDs.
- Audio file bindings.
- Exact timecodes.
- Platform-specific lip-sync parameters.

## 7. Set Defaults And Merge

`set_defaults` is explicit Canonical data. Hidden defaults are not allowed.

Allowed groups:

- `set_defaults.shared_intent`
- `set_defaults.image_intent`
- `set_defaults.video_intent`
- `set_defaults.negative_constraints`

v1 merge strategies are fixed by schema and renderer version:

- `replace`: item scalar replaces set default scalar.
- `append_dedup`: item list appends to set list, then stable de-duplication is
  applied.
- `invariant`: item may not override set-level hard invariant.

Field policy:

- Scalar tone, camera, performance, and style hints use `replace`.
- Constraint lists, descriptive tags, and negative constraints use
  `append_dedup`.
- Fact-protection invariants and platform-neutral safety rules use `invariant`.

Not supported in v1:

- Generic JSON Merge DSL.
- `null` deletion semantics.
- Arbitrary recursive override.
- Canonical-declared merge strategy.
- Custom merge scripts.

Rendered prompts are fully expanded. Downstream phases must not resolve
inheritance.

## 8. Deterministic Renderer

Renderer input:

- Exact Shot Prompt Canonical bytes.
- Exact source Storyboard Revision content.
- Renderer `profile_id` and exact `version`.
- Fixed schema enum maps and fixed fact-protection invariant set.

Renderer output:

- `rendered-positive-prompts.json`
- `rendered-negative-prompts.json`
- `asset-requirements.json`
- `render-provenance.json`
- `review.md`

Determinism rules:

- Fixed templates.
- Fixed field order.
- Stable shot ordering from the source Storyboard.
- Stable sorting for derived collections.
- Stable de-duplication for `append_dedup`.
- Fixed punctuation, newline, whitespace, and escaping rules.
- Canonical JSON bytes use the Runtime's deterministic serialization pattern.
- Renderer does not read current time, random values, network, mutable config,
  or external services.
- Renderer does not call a generative model.

Version locking:

- Every Revision locks `renderer.profile_id` and `renderer.version`.
- No version ranges.
- No silent fallback or auto-upgrade.
- If the locked renderer version is unavailable, materialization fails closed
  with a renderer availability error.

## 9. Negative Prompt

Phase 3 v1 negative rendering uses only:

- Canonical explicit negative constraints.
- A small fixed, versioned, non-configurable fact-protection invariant set.

Initial invariant examples:

- `INV_NO_EXTRA_DECLARED_CHARACTER`
- `INV_PRESERVE_CHARACTER_IDENTITY`
- `INV_PRESERVE_SCENE_IDENTITY`
- `INV_PRESERVE_DIALOGUE_SPEAKER`
- `INV_PRESERVE_LOCKED_ACTION_FACTS`

Rules:

- The invariant set is part of the renderer profile/version.
- Invariants appear in `render-provenance.json` and `review.md`.
- Changing the invariant set requires a renderer version change.

Not Phase 3 v1 capabilities:

- Hard/soft rule registry.
- Soft rule waiver.
- Set/Shot waiver state.
- Waiver reason workflow.
- Policy override state machine.

## 10. Revision Outputs And Bundle

Formal logical types and file responsibilities:

- `canonical-content.json`: exact Shot Prompt Canonical content bytes for the
  Revision; exported from Revision content, not a second authority.
- `rendered-positive-prompts.json`: set-level positive prompts for all shots.
- `rendered-negative-prompts.json`: set-level negative prompts for all shots.
- `asset-requirements.json`: Phase 4 abstract asset requirement handoff.
- `render-provenance.json`: minimal renderer provenance.
- `review.md`: deterministic human review surface.
- `validation-report.json`: validator result summary and lint/warning report.
- `qualification-report.json`: immutable approval qualification evidence.
- `bundle-manifest.json`: hash manifest for formal bundle members.

Current `revision_outputs` support:

- Current DB CHECK allows only `rendered_positive_prompt`,
  `rendered_negative_prompt`, `rendered_markdown`, and `bundle_manifest`.
- Current uniqueness `UNIQUE(revision_id, logical_type)` is compatible with one
  formal row per logical type.
- Phase 3 implementation will need a migration to expand the logical_type CHECK
  to the Phase 3 set. This design round does not run that migration.

Materialization sequence:

1. Validate source Storyboard dependency and Shot Prompt Canonical.
2. Render prompt outputs and derived reports into immutable object bytes.
3. Build `bundle-manifest.json` from output byte hashes.
4. Insert all `revision_outputs` rows in one DB transaction.
5. Run bundle integrity against stored object bytes and manifest.

Atomicity and integrity:

- Object blobs may be written before the DB transaction.
- A failed output transaction leaves zero formal `revision_outputs` rows.
- Existing complete rows return already materialized.
- Partial or conflicting rows fail closed.
- `revision_outputs.object_id` and `content_hash` are SHA-256 of exact bytes.
- Manifest records byte size, content hash, media type, generator, and generator
  version for each output.
- Manifest business hash excludes the manifest output itself.
- Approval after materialization forbids overwrite of formal outputs.

Export kinds:

- Formal export requires approved + fresh + validators PASS + bundle integrity
  PASS.
- Diagnostic export is explicit, marked diagnostic, and cannot be a dependency
  parent.
- Execution export remains blocked and audited until later phases.

## 11. Validation

Blocking errors:

- Source Storyboard Revision missing, unapproved, stale, or bundle integrity
  failure for formal approval.
- `source_storyboard_revision_id` does not match `revision_dependencies`.
- Shot count, order, or `shot_id` mismatch.
- Missing, duplicate, extra, split, or merged shot.
- Storyboard fact copied as editable authority or contradicted.
- Formal item lacks both `image_intent` and `video_intent`.
- Asset entity not found in source facts.
- Illegal purpose, requirement, or modality.
- Concrete asset binding data appears as a Phase 3 v1 capability.
- `video_intent` dialogue coverage is missing, duplicated, out of order, or
  cross-shot.
- Continuity scope invalid, `specific_shot` target missing, or continuity
  overwrites Storyboard facts.
- Platform-specific fields, exact timecodes, execution fields, model parameters,
  URL/path/upload IDs, or `execution_ready`.
- Locked renderer unavailable.
- Rendered output coverage incomplete.
- Bundle manifest/hash integrity failure.
- Open blocking review for the current Revision.

Warnings:

- High-risk Storyboard entity omitted from asset slots.
- Optional asset requirement missing downstream binding readiness.
- Ambiguous performance intent.
- Non-blocking review comments remain open.

Lint:

- Language consistency between controlled natural language and
  `render_language`.
- Repeated low-value phrases.
- Overly broad `other` purpose usage.
- Non-fatal prompt style consistency issues.

Language consistency must never be a blocking error in Phase 3 v1.

## 12. Lifecycle

Lifecycle states:

- `draft`: stored Revision exists, formal validation may be incomplete.
- `validated`: required formal validators pass.
- `materialized`: formal outputs are present in `revision_outputs`.
- `reviewable`: materialized, integrity PASS, and `review.md` available.
- `approved`: latest approval event marks the Revision approved.
- `stale`: derived from recursive dependency freshness.
- `superseded`: stored approval status when a newer Revision in the Artifact is
  approved.
- `revoked`: derived from latest append-only approval revoke event.

Storage model:

- `draft`, `approved`, and `superseded` align with existing `revisions` approval
  status semantics.
- `validated` derives from `validation_results`.
- `materialized` and `reviewable` derive from `revision_outputs` and bundle
  integrity.
- `stale` derives from recursive freshness over `revision_dependencies`.
- `revoked` is an append-only approval event, not row deletion.

Rules:

- A new Storyboard draft does not stale a Shot Prompt Revision.
- A newly approved Storyboard baseline stales dependent Shot Prompt Revisions
  that point to the old baseline.
- A newly approved Shot Prompt Revision supersedes the previous approved
  baseline in the same Shot Prompt Set Artifact.
- Historical Revisions remain auditable and rerenderable with their locked
  renderer version.
- Stale, superseded, and revoked Revisions cannot enter Phase 4.

## 13. Review And Approval

Review Record is outside the formal bundle and outside Canonical.

Review fields:

- `revision_id`: required.
- `scope`: `set` or `shot`.
- `shot_id`: required for shot scope.
- `severity`: `blocking` or `non_blocking`.
- `status`: `open`, `resolved`, or `dismissed`.
- `body`: required reviewer note.
- `created_at` and status-change audit fields.

Rules:

- `open + blocking` blocks only the current Revision.
- Review status changes are append-only audit events.
- Phase 3 v1 does not force unresolved Review Records to carry across
  Revisions.
- Cross-Revision Review resolution is deferred.

Approval must bind:

- Shot Prompt Revision ID.
- Bundle manifest hash.
- Canonical content hash.
- Source Storyboard Revision ID.
- Renderer profile and version.
- Qualification report hash.
- Qualification gate profile and version.
- Reviewer and approval timestamp.

Approval references qualification-report evidence. It does not copy every
dynamic qualification boolean as a new authority.

## 14. Phase 4 Gate

Phase 4 formal input eligibility:

```text
approved
+ fresh
+ not_superseded
+ not_revoked
+ source_storyboard_approved
+ source_storyboard_fresh
+ source_storyboard_integrity_pass
+ shot_prompt_validation_pass
+ shot_prompt_bundle_integrity_pass
+ open_blocking_reviews = 0
+ asset_requirements_present
+ qualification_report_valid
+ approval_hashes_match
```

Phase 4 reads:

- `canonical-content.json`
- `asset-requirements.json`
- `rendered-positive-prompts.json`
- `rendered-negative-prompts.json`
- `bundle-manifest.json`
- approval and qualification evidence

Phase 4 must not read diagnostic exports as parentable formal input and must not
modify Phase 3 Canonical or formal bundle bytes.

## 15. Migration

Phase 3 implementation will require additive migration work, but this design
round performs none.

Expected future migration:

- Add artifact type `shot_prompt_set`.
- Add content profile `shot-prompt-canonical-v1`.
- Extend `revision_outputs.logical_type` CHECK to include Phase 3 logical
  types.
- Add Review Record storage if existing approval and gate records are not
  sufficient for review comments.
- Preserve existing Phase 0-2 data without rewrite.
- Keep old Storyboard bundles valid and auditable.

Migration policy:

- Use dry-run checks before applying schema changes.
- Prefer forward-only additive migrations.
- Do not backfill Shot Prompt data for legacy Storyboard Revisions.
- Existing Phase 0-2 rows remain readable under their original profiles.
- Rollback means restoring from database backup before applying a migration,
  not destructive down-migration of production rows.

## 16. Testing Strategy

Required implementation test coverage:

- Schema unit tests for required fields, optional fields, enums, duplicate keys,
  forbidden fields, and schema versioning.
- Validator unit tests for Storyboard dependency, shot coverage, fact
  read-only boundaries, intent completeness, asset requirements, dialogue
  coverage, continuity, platform neutrality, renderer availability, output
  coverage, and bundle integrity.
- Deterministic renderer golden tests for positive prompts, negative prompts,
  asset requirements, provenance, and review markdown.
- Byte-for-byte rerender tests for identical inputs and locked renderer version.
- Merge tests for `replace`, `append_dedup`, and `invariant`.
- Dialogue coverage tests for visible speech, off-screen voice, narration, inner
  voice, lip-sync required false, and relative timing.
- Continuity tests for set baseline, previous occurrence, specific shot, and
  invalid references.
- Bundle atomicity tests for zero rows after failed output transaction.
- Integrity tamper tests for object bytes, content hash, manifest hash,
  generator metadata, and missing outputs.
- Approval gate tests for missing qualification evidence, stale dependency,
  open blocking review, revoked approval, superseded baseline, and hash mismatch.
- Freshness, superseded, and revoke lifecycle tests.
- Migration tests for logical type CHECK expansion and legacy data
  compatibility.
- End-to-end verification from approved Storyboard Revision to Phase 4 eligible
  Shot Prompt bundle.

## 17. Acceptance Criteria

Phase 3 implementation is complete only when all of the following are true:

- A Shot Prompt Set Artifact can be created from an approved and fresh
  Storyboard Revision.
- Multiple Revisions under one Shot Prompt Set Artifact are supported.
- Formal validation enforces full shot coverage and prevents Storyboard fact
  mutation or copied dialogue text.
- Draft can contain only `shared_intent`, while formal validation requires
  `image_intent` or `video_intent`.
- `slot_id` is deterministically derived and appears in
  `asset-requirements.json`.
- Asset slots are abstract and do not require empty entries for every
  Storyboard entity.
- Renderer output is byte-stable under the same Canonical, source Storyboard,
  and renderer version.
- Bundle materialization is atomic and integrity-checked.
- Review and Approval gates block Phase 4 when required evidence is missing.
- Approval references manifest hash, canonical hash, renderer version, source
  Storyboard Revision, and qualification report hash.
- Phase 4 gate can identify exactly one approved + fresh + not revoked + not
  superseded baseline per scope.
- Diagnostic exports cannot become dependency parents.
- Execution export remains blocked.
- Full test suite and Phase 3 verifier pass.

## 18. Deferred Capabilities

Deferred to Phase 3 v2 or later:

- Hard/soft rule registry.
- Soft rule waiver.
- Set/Shot waiver workflow.
- Cross-Revision Review resolution enforcement.
- Field-level render trace.
- Large character/scene/prop purpose ontology.
- Purpose-level continuity override.
- Multi-language formal bundles.
- Generic merge DSL.

Deferred to Phase 4:

- Concrete `asset_id` binding.
- Asset URL, path, file hash, upload ID, and storage location.
- Asset fallback, priority, and candidate selection.
- Binding completeness and asset continuity execution.

Deferred to Phase 5:

- Precise timecodes.
- Dialogue timeline compilation.
- Task DAG, unit split, execution grouping, and resource dependency graph.

Deferred to Phase 6:

- LibTV/Agnes platform syntax.
- Model parameters.
- Platform nodes.
- Upload protocol.
- Retry policy.
- Platform error mapping.

Deferred to QC/UI:

- Prompt diff UI.
- Field-level provenance UI.
- Result problem taxonomy.
- Auto-rerun recommendations.
- Candidate comparison and user selection workflows.

## Self Review

- The revised-decision baseline is preserved: multiple Revisions per Artifact,
  draft shared-only allowance, formal modality requirement, deterministic
  `slot_id`, no empty asset slots for every entity, small purpose enum,
  Shot/Entity continuity, limited merge, fixed negative invariants,
  non-blocking language lint, minimal provenance, deferred cross-Revision Review
  resolution, and Approval qualification evidence.
- This spec reuses existing Phase 0-2 governance objects and does not create a
  parallel governance system.
- Terms such as concrete asset IDs, URLs, paths, upload IDs, hard/soft rules,
  waiver, and cross-Revision Review appear only as boundaries, validators, or
  deferred capabilities, not Phase 3 v1 capabilities.
- No Phase 4, Phase 5, or Phase 6 implementation is authorized by this document.
