# Storyboard Canonical + Shot Prompt Foundation Design

## 1. Status and Decision

Status: FROZEN FOR IMPLEMENTATION PLANNING
Decision: GO WITH PREREQUISITE
Implementation Planning: ALLOWED

Date: 2026-06-28
Current branch: `test/storyboard-complete-verification`
Baseline HEAD: `ed7e1d534145d91ba8a6cbdf33930198eb2ce543`
Review inputs:
- `docs/reviews/shot-prompt-workflow-codex-analysis.md`
- `docs/reviews/shot-prompt-workflow-deepseek-analysis.md`
Review SHA-256:
- `08587d147169d211b17ea98ec27136e212b44daf02004c84fa8f23fe5c1ba36e`
- `2286a41023157afeb913d4cfba02215620fcf0aba01e4a9630017810405fef52`
Current test count: `92`

This document freezes the foundation architecture for Storyboard Canonical and Shot Prompt. It resolves the prior blocking issues by making JSON the authority, keeping Markdown derived, using a minimal `revision_outputs` layer, and separating content approval from execution readiness.

## 2. Problem Statement

The current runtime is still Markdown-first for Storyboard, with a single-revision content model and approval/readiness semantics that are sufficient for the present MVP but not for Shot Prompt.

The next stage needs:

- a canonical Storyboard JSON authority;
- a deterministic renderer in Runtime;
- a minimal append-only `revision_outputs` table;
- explicit Shot Prompt canonical JSON;
- dual-axis asset binding state;
- recursive freshness across dependency chains;
- content approval separated from execution readiness.

Without these boundaries, Shot Prompt would inherit Markdown parsing ambiguity, mixed approval semantics, and fragile output provenance.

## 3. Current Repository Baseline

The repository evidence that constrains this design is stable:

- `README.md:3-23` says the runtime currently supports only `markdown-script-mvp-v1` and `storyboard-markdown-mvp-v1`, and explicitly does not claim Shot Prompt, LibTV, or Agnes support.
- `ai_drama_runtime/cli.py:66-109` routes `run create` by a simple `--input` versus `--source-revision` split, which is adequate for the current two workflow shapes but not for canonical bundle dispatch.
- `ai_drama_runtime/services.py:216-535` shows the current Storyboard flow, approval gate, freshness gate, compare path, and export path built on top of Markdown Storyboard revisions.
- `ai_drama_runtime/store.py:171-535` defines the current single-content revision model and the existing tables: `artifacts`, `runs`, `input_snapshots`, `revisions`, `validation_results`, `approval_records`, `export_records`, `revision_dependencies`, and `workflow_gate_records`.
- `ai_drama_runtime/request.py:133-167` still builds a Markdown-first Storyboard runtime request.
- `ai_drama_runtime/parser.py:35-56` still parses Storyboard Markdown by scene and shot markers.
- `ai_drama_runtime/validators.py:69-191` persists validator results and already distinguishes `PASS`, `FAIL`, `NOT_APPLICABLE`, and `SKIPPED_DEPENDENCY_MISSING`.
- `skills/ai-drama-storyboard-design-skill/v0.1.0/skill.json:1-196` declares the current Storyboard package, its validator list, and its output as `storyboard_revision` / `storyboard_markdown`.

That baseline means the foundation work must be additive and compatibility-preserving.

## 4. Goals

1. Freeze Storyboard Canonical JSON as the authority for downstream work.
2. Keep Markdown as a deterministic renderer output, not the source of truth.
3. Introduce `revision_outputs` as a minimal store for bundle members.
4. Define Shot Prompt Canonical JSON on top of canonical Storyboard input.
5. Separate content approval, binding verification, freshness, and execution readiness.
6. Preserve legacy Markdown revisions without rewriting their history.
7. Keep migration additive and reversible at the schema level.

## 5. Non-Goals

- No implementation of Storyboard Canonical in this document.
- No implementation of Shot Prompt runtime generation in this document.
- No implementation of Renderer code in this document.
- No implementation of asset registry infrastructure in this document.
- No implementation of execution planning tables in this document.
- No modification of legacy Markdown revisions in place.
- No automatic approval of any business gate.
- No new web UI, API service, workflow engine, or registry service.

## 6. Architectural Principles

1. Canonical JSON is the only authority; Markdown is derived.
2. Canonical payloads exclude runtime metadata, execution targets, and approval state.
3. Hashes are computed over normalized canonical bytes, not over rendered text.
4. Output members are stored independently; no hidden bundle graph.
5. Approval is about content; readiness is about downstream execution conditions.
6. Binding changes create new revisions unless the operation is a true no-op.
7. Legacy revisions remain readable and comparable, but not silently rewritten.
8. Future platform choices stay outside canonical content so the core stays neutral.

## 7. Artifact and Revision Model

### Artifact classes

- `storyboard_legacy_markdown_revision`
- `storyboard_canonical_revision`
- `shot_prompt_package_revision`
- `shot_prompt_render_derived_revision`
- `shot_prompt_asset_binding_derived_revision`

### Revision rules

- A revision is immutable once written.
- A change to canonical content always creates a new revision.
- A change to asset bindings creates a new derived revision unless it is a no-op.
- Legacy Storyboard revisions keep their historical `content_object_id` semantics.
- New canonical revisions use the canonical JSON object as the primary `content_object_id`.
- Markdown is not the canonical object for new canonical revisions; it is a derived output stored in `revision_outputs`.

### `revision_outputs`

`revision_outputs` is the only bundle-member table in this foundation. It is append-only and minimal.

Allowed columns:

- `revision_id`
- `logical_type`
- `object_id`
- `content_hash`
- `media_type`
- `generator`
- `generator_version`
- `created_at`

Unique constraint:

- `UNIQUE(revision_id, logical_type)`

Allowed `logical_type` values:

- Storyboard: `rendered_markdown`, `bundle_manifest`
- Shot Prompt: `rendered_positive_prompt`, `rendered_negative_prompt`, `rendered_markdown`, `bundle_manifest`

Not allowed here:

- `canonical_json`
- `approval_manifest`
- `execution_plan`
- `member_key`
- `output_order`
- `is_canonical_source`
- multi-layer bundle graphs

## 8. Storyboard Canonical Schema

Storyboard Canonical JSON is the authority for downstream prompt generation.

### Top-level schema

```json
{
  "schema_version": "storyboard-canonical-v1",
  "project_id": "PROJECT_ID",
  "chapter_id": "CHAPTER_ID",
  "source": {
    "script_artifact_id": "ARTIFACT_ID",
    "script_revision_id": "REVISION_ID",
    "script_content_hash": "SHA256",
    "script_approval_record_id": "APPROVAL_RECORD_ID"
  },
  "scenes": [],
  "shots": []
}
```

### Scene object

Required and non-null:

- `scene_id`
- `scene_order`
- `source_scene_reference`
- `characters`
- `summary`

Required but nullable:

- `location`
- `time`
- `interior_exterior`

Recommended shape:

```json
{
  "scene_id": "SCENE_001",
  "scene_order": 1,
  "source_scene_reference": "SOURCE_SCENE_001",
  "location": null,
  "time": null,
  "interior_exterior": null,
  "characters": ["CHARACTER_A"],
  "summary": "Scene summary"
}
```

### Shot object

Required and non-null:

- `scene_id`
- `shot_id`
- `shot_order`
- `source_scene_reference`
- `duration_seconds`
- `shot_size`
- `camera_angle`
- `visual_composition`
- `character_positions`
- `character_actions`
- `continuity_in`
- `continuity_out`

Required but nullable:

- `camera_movement`
- `emotion_performance`
- `dialogue`
- `sound_notes`

Recommended shape:

```json
{
  "scene_id": "SCENE_001",
  "shot_id": "SHOT_001",
  "shot_order": 1,
  "source_scene_reference": "SOURCE_SCENE_001",
  "duration_seconds": 8,
  "shot_size": "medium",
  "camera_angle": "eye_level",
  "camera_movement": null,
  "visual_composition": "subject centered",
  "character_positions": [
    {
      "character_id": "CHARACTER_A",
      "screen_zone": "center",
      "depth": "foreground",
      "pose": "standing"
    }
  ],
  "character_actions": [
    {
      "character_id": "CHARACTER_A",
      "action": "looks at camera"
    }
  ],
  "emotion_performance": null,
  "dialogue": [
    {
      "speaker": "CHARACTER_A",
      "text": "Line one"
    }
  ],
  "sound_notes": null,
  "continuity_in": {
    "must_preserve": ["wardrobe", "prop_state"],
    "must_change": []
  },
  "continuity_out": {
    "must_preserve": ["wardrobe", "prop_state"],
    "must_change": []
  }
}
```

### Frozen rules

- `scene_id` regex: `^SCENE_[A-Z0-9][A-Z0-9_-]*$`
- `shot_id` regex: `^SHOT_[A-Z0-9][A-Z0-9_-]*$`
- `scene_order` and `shot_order` are strictly increasing within their parent scope.
- `duration_seconds` is an integer.
- Storyboard-layer shots stay within 5-15 seconds.
- Empty strings are not allowed as a substitute for missing data.
- Free-form Markdown cannot replace structured fields.
- Renderer output must never be written back into canonical Storyboard JSON.

## 9. Shot Prompt Canonical Schema

Shot Prompt Canonical JSON is the authority for prompt generation. It only carries content-level data and binding declarations.

### Top-level schema

```json
{
  "schema_version": "shot-prompt-package-v1",
  "source": {
    "storyboard_artifact_id": "ARTIFACT_ID",
    "storyboard_revision_id": "REVISION_ID",
    "storyboard_content_hash": "SHA256"
  },
  "content": {
    "units": []
  },
  "asset_bindings": {
    "binding_completeness": "pending",
    "binding_verification": "unverified",
    "references": []
  }
}
```

### Unit object

Required:

- `unit_id`
- `unit_order`
- `source_scene_id`
- `source_storyboard_shot_id`
- `split`
- `timing`
- `prompt_components`
- `negative_constraints`
- `reference_requirements`

`prompt_components` fields:

- `scene`
- `characters`
- `composition`
- `camera`
- `actions`
- `performance`
- `dialogue_lipsync`
- `continuity`
- `style`
- `constraints`

`reference_requirements` fields:

- `scene_identity_required`
- `character_identity_required`
- `costume_continuity_required`
- `prop_identity_required`
- `previous_unit_continuity_required`

### Split and timing

```json
{
  "unit_id": "SHOT_001-A",
  "unit_order": 1,
  "source_scene_id": "SCENE_001",
  "source_storyboard_shot_id": "SHOT_001",
  "split": {
    "is_split": true,
    "split_group_id": "SHOT_001",
    "split_index": 1,
    "split_count": 2
  },
  "timing": {
    "source_duration_seconds": 8,
    "unit_duration_seconds": 4,
    "group_duration_seconds": 8,
    "variance_seconds": 0,
    "variance_reason": null
  },
  "prompt_components": {
    "scene": "",
    "characters": "",
    "composition": "",
    "camera": "",
    "actions": "",
    "performance": "",
    "dialogue_lipsync": "",
    "continuity": "",
    "style": "",
    "constraints": ""
  },
  "negative_constraints": [],
  "reference_requirements": {
    "scene_identity_required": true,
    "character_identity_required": true,
    "costume_continuity_required": true,
    "prop_identity_required": true,
    "previous_unit_continuity_required": true
  }
}
```

### Asset binding references

Each reference entry must include:

- `reference_id`
- `unit_id`
- `requirement_role`
- `required`
- `asset_identifier`
- `asset_revision_id`
- `asset_content_hash`
- `local_evidence_hash`
- `registry_evidence_id`

Pending states may leave the asset identity and evidence fields null, but required references must still be declared.

### Frozen rules

- Default mapping is 1:1 from Storyboard Shot to Unit.
- 1:N split is allowed.
- N:1 merge is forbidden.
- A Unit can only reference one source Storyboard Shot.
- Every source Storyboard Shot must map to at least one Unit.
- Units derived from the same source Shot must remain contiguous in global order.
- `group_duration_seconds` must equal the sum of the Unit durations in the group.
- Allowed duration variance is `-2 <= variance_seconds <= 2`.
- Any non-zero variance needs an explicit reason.
- `generation_strategy`, `frame_requirements`, and future target selection fields are not canonical fields.

## 10. Canonical Serialization and Hashing

### Serialization version

`canonical-json-v1`

Frozen rules:

- UTF-8 without BOM.
- Unicode normalized to NFC before serialization.
- Object keys sorted lexicographically.
- Arrays preserve business order.
- JSON separators are `","` and `":"`.
- `ensure_ascii` is false.
- `allow_nan` is false.
- No trailing newline in the canonical byte stream.

### Storyboard hashes

- `storyboard_canonical_hash = SHA256(storyboard canonical bytes)`
- `storyboard_bundle_manifest_hash = SHA256(bundle manifest bytes without self hash)`

### Shot Prompt hashes

- `prompt_content_hash = SHA256(canonical serialization of schema_version, source, and content.units)`
- `asset_binding_hash = SHA256(canonical serialization of asset_bindings)`
- `canonical_revision_hash = SHA256(full Shot Prompt canonical JSON bytes)`
- `bundle_manifest_hash = SHA256(bundle manifest bytes without `bundle_manifest_hash`)`

### Scope rules

- `prompt_content_hash` excludes `asset_bindings`, runtime metadata, approval records, freshness, readiness, and derived outputs.
- `asset_binding_hash` includes the full `asset_bindings` object.
- `canonical_revision_hash` covers the whole canonical JSON payload.
- `bundle_manifest_hash` excludes `revision_id`, `created_at`, absolute paths, adapter payload, and the hash field itself.
- Approval hashes are evidence hashes only; they do not replace business hashes.

## 11. Deterministic Renderer Contract

The Renderer lives in Runtime, not in the Skill Package.

The Skill Manifest only declares:

- `renderer_id`
- `renderer_version`
- `required_schema_version`

Renderer contract:

- same canonical bytes + same renderer ID/version = byte-identical output
- no model calls
- no network access
- no clock access
- no randomness
- no local absolute paths
- no locale-dependent formatting
- no terminal-width-dependent wrapping
- no environment-variable-dependent text changes

Output rules:

- UTF-8 without BOM
- LF line endings
- one trailing newline for text outputs

Derived outputs:

- `rendered_positive_prompt`
- `rendered_negative_prompt`
- `rendered_markdown`

Renderer version changes create a new render-derived revision; they do not silently mutate old revisions.

Renderer parity validators must re-render and compare bytes exactly.

## 12. Minimal `revision_outputs`

`revision_outputs` stays minimal and append-only.

### Purpose

It stores bundle members independently so canonical JSON and derived outputs do not have to share one content object.

### Allowed logical types

Storyboard:

- `rendered_markdown`
- `bundle_manifest`

Shot Prompt:

- `rendered_positive_prompt`
- `rendered_negative_prompt`
- `rendered_markdown`
- `bundle_manifest`

### Disallowed expansion

- output graphs
- plugin-style logical type taxonomies
- output ordering columns
- `canonical_json` duplicated into `revision_outputs`
- approval manifests
- execution plans

### Compatibility strategy

- Legacy revisions keep their current `content_object_id` history.
- New canonical revisions use canonical JSON as the main object.
- Markdown remains exportable through deterministic renderers.
- No historical revision is rewritten in place.

## 13. Bundle Manifest

### Storyboard and Shot Prompt bundle manifest

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
      "generator": "renderer-id",
      "generator_version": "renderer-version"
    }
  ],
  "bundle_manifest_hash": "SHA256"
}
```

Rules:

- `outputs` are sorted lexicographically by `logical_type`.
- `revision_id` may appear for audit, but it is excluded from the manifest hash.
- The manifest hash excludes itself.
- No absolute paths enter the manifest hash.
- Platform payloads are not part of the manifest hash.

### Atomic export

1. Write all bundle members to a staging directory on the same filesystem.
2. Verify each member hash.
3. Write the manifest last.
4. Verify the manifest hash.
5. Atomically rename the staging directory to the final location.
6. If any step fails, remove staging and leave no partial final bundle behind.

## 14. Approval and Promotion Semantics

### Content approval

Content approval is anchored to `prompt_content_hash`.

Approval record fields:

- `revision_id`
- `artifact_id`
- `prompt_content_hash`
- `reviewer`
- `note`
- `created_at`

### Asset-only derived revision

Asset-only derived revisions may inherit approval evidence, but they do not copy or forge the old approval row.

Inheritance requires:

- same `prompt_content_hash`
- same source Storyboard revision
- same source Storyboard content hash
- source freshness is `FRESH`
- same `schema_version`
- asset path whitelist passes
- all required validators pass

Derived revision fields:

- `inherited_content_approval_record_id`
- `inherited_prompt_content_hash`
- `derivation_type = asset_binding_update`

### Promotion

An asset-only derived revision does not become current approved automatically. Promotion is explicit.

Promotion checks:

- inherited approval evidence exists
- `prompt_content_hash` matches
- source is still `FRESH`
- asset binding validators pass
- bundle integrity passes
- renderer parity passes
- revision is not rejected
- revision is not stale
- derivation is not a no-op

Illegal behavior:

- copying approval rows
- keeping the old `revision_id` after asset changes
- promoting stale revisions
- promoting rejected revisions
- inheriting approval after prompt content changes
- inheriting approval after source Storyboard changes

## 15. Asset Binding Semantics

The old single-axis `pending / partially_bound / bound` label is replaced by a dual-axis model.

### Completeness axis

- `pending`
- `partially_bound`
- `complete`

### Verification axis

- `unverified`
- `locally_verified`
- `registry_verified`

### State rules

- `pending` means no required references have valid asset identifiers.
- `partially_bound` means at least one required reference is bound but at least one required reference is missing.
- `complete` means all required references have declarations.
- `unverified` means at least one required binding lacks local or registry evidence.
- `locally_verified` means all required bindings have local immutable hash evidence.
- `registry_verified` means all required bindings have trusted registry evidence.
- `partially_bound + locally_verified` is not allowed.
- `complete + unverified` is not execution ready.
- Without a Visual Asset Registry, `registry_verified` cannot be produced.

### bind-assets rules

- `bind-assets` creates a new revision when the binding set changes.
- Identical bindings are a `BINDING_NO_OP`.
- `bind-assets` may only modify whitelisted asset-binding paths.
- `bind-assets` may not mutate prompt creative content.
- stale revisions cannot be bound.
- rejected revisions cannot be bound.
- illegal path changes yield `BINDING_PATH_NOT_ALLOWED`.

## 16. Recursive Freshness

Revisions store only direct dependencies. Runtime verifies freshness recursively across the chain:

`Script -> Storyboard -> Shot Prompt -> future Execution Planning`

For each dependency edge:

1. Parent revision exists.
2. Parent artifact exists.
3. Parent revision is still the current approved revision for its artifact.
4. Parent revision is recursively `FRESH`.
5. Stored parent content hash matches actual content hash.
6. Stored parent approval record resolves.
7. Dependency cycles fail closed.
8. Missing dependencies mark the child `STALE`.
9. If any required parent is `STALE`, the child is `STALE`.

Allowed on `STALE` revisions:

- read
- inspect
- compare
- provenance review

Not allowed on `STALE` revisions:

- content approval
- asset-only promotion
- `bind-assets`
- execution export
- execution planning
- becoming current approved

## 17. Execution Readiness Boundary

Execution readiness is dynamic and outside canonical JSON.

Frozen state for this foundation:

- `execution_readiness = blocked`
- `reason = EXECUTION_PLAN_NOT_MATERIALIZED`

Even if content is approved, bindings are complete, and freshness is `FRESH`, the revision is not execution ready in this phase.

Readiness can only become `ready` when future work introduces:

- Execution Planning Artifact
- Target Adapter
- Platform Payload
- Target Validators
- Execution Authorization

No manual `mark-ready` command is allowed.

## 18. Legacy Storyboard Migration

Legacy Markdown revisions remain readable, comparable, and exportable through explicit migration paths.

Frozen migration flow:

`legacy Markdown Revision -> explicit migration command -> parsed candidate Canonical JSON -> schema validation -> source coverage validation -> renderer round-trip review -> human confirmation -> new Canonical Storyboard Revision`

Rules:

- Legacy revisions are never rewritten in place.
- The Markdown parser stays at the legacy migration boundary only.
- Migration fails closed if fidelity cannot be proven.
- The stable error code is `LEGACY_MIGRATION_REQUIRES_REVIEW`.
- Legacy revisions are not auto-approved and do not auto-become current approved.

## 19. Export Semantics

### Formal review export

Conditions:

- content approved
- recursive freshness is `FRESH`
- required validators pass
- bundle integrity passes

Allowed even if binding is incomplete.

Provenance must mark:

- `execution_readiness = blocked`
- `not_an_execution_package = true`

### Diagnostic export

Diagnostic export is for stale revisions only and requires an explicit command. It must be clearly labeled as diagnostic and cannot be consumed by downstream execution planning.

### Execution export

Execution export is blocked in this foundation phase:

- `EXPORT_NOT_EXECUTION_READY`

## 20. Validator Matrix

### Storyboard

| validator | required | input | store access | pass condition | fail condition | N/A allowed | symbolic error code |
|---|---:|---|---|---|---|---:|---|
| `storyboard_canonical_schema` | yes | canonical Storyboard JSON | yes | schema, provenance, and immutability fields are valid | missing required field or schema mismatch | no | `CANONICAL_SCHEMA_INVALID` |
| `storyboard_shot_identity` | yes | canonical Storyboard JSON | yes | all `scene_id` / `shot_id` values match frozen regexes | invalid ID or duplicate ID | no | `SHOT_ID_INVALID` |
| `storyboard_shot_order` | yes | canonical Storyboard JSON | yes | scene and shot order are strictly increasing and stable | out-of-order or duplicate order | no | `SHOT_ORDER_INVALID` |
| `storyboard_duration` | yes | canonical Storyboard JSON | yes | each storyboard shot is an integer 5-15 seconds | missing or out-of-range duration | no | `DURATION_VARIANCE_INVALID` |
| `storyboard_source_coverage` | yes | canonical Storyboard JSON + source script | yes | every source scene/shot is covered exactly as required | missing coverage or extra coverage | no | `SHOT_COVERAGE_INCOMPLETE` |
| `storyboard_continuity` | yes | canonical Storyboard JSON | yes | continuity_in/out is complete and internally consistent | continuity mismatch | no | `SHOT_MAPPING_INVALID` |
| `storyboard_renderer_parity` | yes | canonical Storyboard JSON + renderer | no | rendered Markdown bytes match deterministic renderer | byte mismatch | no | `RENDERER_PARITY_FAILED` |
| `storyboard_source_freshness` | yes | storyboard revision + dependency chain | yes | source chain is recursively fresh | source stale or dependency missing/cycle | no | `SOURCE_STALE` / `DEPENDENCY_MISSING` / `DEPENDENCY_CYCLE_DETECTED` |
| `storyboard_bundle_integrity` | yes | bundle members + manifest | yes | hashes and manifest are internally consistent | member or manifest mismatch | no | `BUNDLE_INTEGRITY_FAILED` |

### Shot Prompt

| validator | required | input | store access | pass condition | fail condition | N/A allowed | symbolic error code |
|---|---:|---|---|---|---|---:|---|
| `shot_prompt_canonical_schema` | yes | Shot Prompt canonical JSON | yes | schema and top-level shape are valid | missing required field or schema mismatch | no | `CANONICAL_SCHEMA_INVALID` |
| `shot_prompt_source_freshness` | yes | source chain | yes | source Storyboard remains recursively fresh | source stale or dependency missing/cycle | no | `SOURCE_STALE` / `DEPENDENCY_MISSING` / `DEPENDENCY_CYCLE_DETECTED` |
| `shot_prompt_source_coverage` | yes | source Storyboard + units | yes | every source Storyboard shot is covered by at least one unit | orphan shot or orphan unit | no | `SHOT_COVERAGE_INCOMPLETE` / `SHOT_MAPPING_INVALID` |
| `shot_prompt_mapping_integrity` | yes | units + source shots | yes | 1:1 default, 1:N split, no N:1 merge | merge, duplicate mapping, or cross-scene reference | no | `SHOT_MAPPING_INVALID` / `SHOT_MERGE_FORBIDDEN` |
| `shot_prompt_split_integrity` | yes | split metadata | yes | split index/count are contiguous and consistent | invalid split sequence | no | `SPLIT_SEQUENCE_INVALID` |
| `shot_prompt_duration_integrity` | yes | timing fields | yes | group duration matches sums and drift stays within ±2s | drift outside policy or sum mismatch | no | `DURATION_VARIANCE_INVALID` |
| `shot_prompt_component_completeness` | yes | prompt_components | yes | all required components are present and non-empty | missing prompt component | no | `PROMPT_COMPONENT_INCOMPLETE` |
| `shot_prompt_reference_requirement_integrity` | yes | reference_requirements | yes | requirement roles and booleans are structurally valid | malformed requirement declaration | no | `REFERENCE_REQUIREMENT_INVALID` |
| `shot_prompt_forbidden_platform_fields` | yes | canonical JSON | no | no adapter payload or future target fields appear in canonical content | forbidden field present | no | `FORBIDDEN_PLATFORM_FIELD` |
| `shot_prompt_renderer_parity` | yes | canonical JSON + renderer | no | renderer output matches canonical bytes exactly | byte mismatch | no | `RENDERER_PARITY_FAILED` |
| `shot_prompt_bundle_integrity` | yes | bundle members + manifest | yes | member and manifest hashes match | member or manifest mismatch | no | `BUNDLE_INTEGRITY_FAILED` |

### Asset Binding

| validator | required | input | store access | pass condition | fail condition | N/A allowed | symbolic error code |
|---|---:|---|---|---|---|---:|---|
| `asset_binding_path_whitelist` | yes | binding derivation request | yes | only whitelisted binding paths change | forbidden path change | no | `BINDING_PATH_NOT_ALLOWED` |
| `asset_binding_completeness` | yes | asset_bindings state | yes | completeness state matches declared references | missing or inconsistent completeness state | no | `ASSET_BINDING_INVALID` |
| `asset_binding_verification` | yes | asset_bindings state | yes | verification state matches available evidence | missing evidence or impossible state | no | `ASSET_BINDING_UNVERIFIED` |
| `asset_binding_no_op` | conditional | binding derivation request | yes | repeated identical bindings produce no content change | identical request still creates a content-changing revision | yes | `BINDING_NO_OP` |
| `inherited_content_approval_integrity` | yes | derived revision + approval evidence | yes | inherited approval fields match frozen rules | copied approval row or mismatched hash | no | `INHERITED_APPROVAL_INVALID` |

Note: the existing package-level genericity validator remains orthogonal to the foundation bundle matrix and does not change the canonical contracts above.

## 21. State Machines

### Storyboard revision lifecycle

`legacy_markdown -> canonical_candidate -> canonical_approved -> stale`

Illegal:

- in-place rewrite of legacy content
- approval of stale canonical revision

### Shot Prompt content approval

`draft -> approved -> stale`

Illegal:

- approval without content hash binding
- approval after source Storyboard changes without revalidation

### Asset-only derived revision

`derived -> ready_for_promotion -> promoted`

Illegal:

- promotion without inherited approval evidence
- promotion of stale or rejected revision

### Binding completeness

`pending -> partially_bound -> complete`

### Binding verification

`unverified -> locally_verified -> registry_verified`

### Recursive freshness

`FRESH -> STALE / INVALID`

### Execution readiness

`blocked -> ready` is deferred to future phases only

### Export modes

`formal_review_export | diagnostic_export | execution_export_blocked`

## 22. CLI Contract Proposal

Keep the generic entrypoint and route by manifest metadata.

### Stable entrypoint

```bash
ai-drama run create \
  --skill SKILL_REF \
  --source-revision REVISION_ID
```

Future dispatch should use:

- input artifact type
- output artifact type
- runtime profile

### Suggested namespaced commands

```bash
ai-drama storyboard migrate-legacy ...
ai-drama storyboard render ...
ai-drama shot-prompts bind-assets ...
ai-drama shot-prompts promote-derived ...
ai-drama artifacts export-review-bundle ...
ai-drama artifacts export-diagnostic-bundle ...
```

`ai-drama shot-prompts mark-ready` is forbidden.

### Error code policy

This foundation preserves the existing numeric CLI exit codes and adds symbolic domain codes on top. Numeric exit-code remapping is out of scope for this document.

## 23. Symbolic Error Codes

Frozen domain symbolic codes:

- `DESIGN_INPUT_MISSING`
- `REVIEW_INPUT_MISSING`
- `SOURCE_REVISION_NOT_FOUND`
- `SOURCE_ARTIFACT_TYPE_INVALID`
- `SOURCE_NOT_APPROVED`
- `SOURCE_STALE`
- `DEPENDENCY_MISSING`
- `DEPENDENCY_CYCLE_DETECTED`
- `CANONICAL_SCHEMA_INVALID`
- `CANONICAL_HASH_MISMATCH`
- `RENDERER_PARITY_FAILED`
- `BUNDLE_INTEGRITY_FAILED`
- `SHOT_ID_INVALID`
- `SHOT_ORDER_INVALID`
- `SHOT_COVERAGE_INCOMPLETE`
- `SHOT_MAPPING_INVALID`
- `SHOT_MERGE_FORBIDDEN`
- `SPLIT_SEQUENCE_INVALID`
- `DURATION_VARIANCE_INVALID`
- `PROMPT_COMPONENT_INCOMPLETE`
- `REFERENCE_REQUIREMENT_INVALID`
- `FORBIDDEN_PLATFORM_FIELD`
- `ASSET_BINDING_INVALID`
- `ASSET_BINDING_UNVERIFIED`
- `BINDING_PATH_NOT_ALLOWED`
- `BINDING_NO_OP`
- `INHERITED_APPROVAL_INVALID`
- `PROMOTION_BLOCKED`
- `EXECUTION_PLAN_NOT_MATERIALIZED`
- `EXPORT_NOT_EXECUTION_READY`
- `LEGACY_MIGRATION_REQUIRES_REVIEW`

These are domain codes only; they are distinct from numeric CLI exit codes.

## 24. Database Migration Strategy

### Additive tables

- `revision_outputs`
- `revision_binding_records`
- `revision_readiness_records`

### Optional later table

- `execution_target_records` is deferred until execution planning lands.

### Recommended indexes

- `revision_outputs(revision_id, logical_type)`
- `revision_outputs(content_hash)`
- `revision_binding_records(revision_id, binding_completeness, binding_verification)`
- `revision_readiness_records(revision_id, readiness_state)`

### Compatibility strategy

- Preserve `revisions`, `approval_records`, `revision_dependencies`, and `workflow_gate_records`.
- Preserve all existing legacy Markdown revision content.
- Do not auto-backfill canonical JSON for historical revisions without explicit migration commands.
- Do not introduce asset registry or execution planning tables in the same migration step.
- Rollback should remove only the additive tables and indexes.

## 25. Acceptance Criteria

| case | expected result |
|---|---|
| Normal canonical generation | canonical JSON, renderer output, and hashes match exactly |
| Unapproved Storyboard | gate failure before Shot Prompt creation |
| Stale Storyboard | content approval and export blocked |
| Missing scene coverage | coverage validator fails |
| Illegal merge of multiple storyboard shots into one unit | mapping validator fails |
| Split order mismatch | split validator fails |
| Duration drift beyond ±2s | duration validator fails |
| Renderer inconsistency | renderer parity validator fails |
| `pending` binding completeness | execution readiness blocked |
| `partially_bound` binding completeness | execution readiness blocked |
| `complete + unverified` | execution readiness blocked |
| `complete + locally_verified` | allowed for content flow, still not execution-ready in this phase |
| `registry_verified` without registry | invalid |
| `bind-assets` no-op | no content-changing revision created |
| `bind-assets` illegal path change | binding validator fails |
| Bundle export failure mid-write | staging directory cleaned, no partial final bundle remains |
| Upstream reapproval of source storyboard | dependent Shot Prompt revision becomes stale |
| Formal review export | allowed only under the formal review conditions |
| Diagnostic export of stale revision | allowed only through explicit diagnostic path |
| Execution export | blocked with `EXPORT_NOT_EXECUTION_READY` |

## 26. Delivery Phases

### Phase 0 — Specification Freeze

- Goal: freeze canonical fields, hash rules, revision output semantics, and validator responsibilities.
- In scope: `docs/superpowers/specs/`, `docs/reviews/`, `docs/storyboard/`.
- Out of scope: implementation code, schema migrations, runtime behavior changes.
- Dependencies: reviewed repository evidence and frozen design decisions.
- Exit criteria: this spec is internally consistent and free of placeholder language.

### Phase 1 — Storyboard Canonicalization

- Goal: migrate Storyboard authority from Markdown to canonical JSON.
- In scope: Storyboard schema, migration command, canonical validation, renderer contract entrypoints.
- Out of scope: Shot Prompt core, asset binding, execution planning.
- Dependencies: frozen Storyboard schema and deterministic serialization rules.
- Exit criteria: canonical Storyboard revisions can be created, rendered, compared, and migrated without rewriting legacy history.

### Phase 2 — Minimal Bundle Foundation

- Goal: store bundle members independently through `revision_outputs`.
- In scope: minimal output table, bundle manifest, bundle export orchestration.
- Out of scope: asset registry, target adapters, execution planning.
- Dependencies: canonical Storyboard revision shape and renderer contract.
- Exit criteria: bundle members and bundle hashes are addressable independently.

### Phase 3 — Shot Prompt Core

- Goal: introduce Shot Prompt canonical JSON on top of canonical Storyboard input.
- In scope: Shot Prompt schema, unit mapping, timing validation, prompt component validation.
- Out of scope: asset binding promotion, execution planning, target adapters.
- Dependencies: Storyboard canonical revisions and minimal bundle foundation.
- Exit criteria: a Shot Prompt revision can be created, validated, approved, and exported from canonical Storyboard input.

### Phase 4 — Asset Binding

- Goal: add deterministic `bind-assets` derivations and binding-state validation.
- In scope: binding completeness, binding verification, derived revision rules, promotion semantics.
- Out of scope: external registry trust model, full execution planning.
- Dependencies: Shot Prompt core and revision output storage.
- Exit criteria: asset changes create new revisions and cannot mutate canonical creative content in place.

### Phase 5 — Execution Planning and Target Adapters

- Goal: separate execution planning from content approval and add adapter-specific payloads.
- In scope: execution planning records, target adapters, adapter payloads, target validators.
- Out of scope: redefinition of canonical content authority.
- Dependencies: frozen canonical payloads, renderer contract, and binding semantics.
- Exit criteria: execution targets can be planned without contaminating canonical JSON.

Renderer delivery belongs to Phases 1 and 2 as part of the foundation, not as a separate phase.

## 27. Decision Traceability Matrix

| Topic | Codex Position | DeepSeek Position | Frozen Decision | Rationale |
|---|---|---|---|---|
| Storyboard Canonical | required prerequisite | prerequisite before Shot Prompt | canonical first | removes Markdown ambiguity at the root |
| Markdown Parser | legacy boundary only | not final authority | legacy-only migration boundary | preserves compatibility without making Markdown authoritative |
| `content_object_id` | legacy revision mirror + new canonical content | keep content-addressed authority | legacy preserved; new canonical revisions use canonical JSON | avoids rewriting history while switching authority for new work |
| `revision_outputs` | minimal bundle-member table | over-abstracted if too broad | minimal append-only table only | supports bundle members without building a graph |
| Canonical JSON duplication | avoid duplicate canonical storage | avoid duplicate canonical storage | no canonical JSON duplication in `revision_outputs` | keeps one authority object |
| `rendered_prompt` | derived output | derived output | derived output | keeps prompt text deterministic and non-authoritative |
| negative prompt | derived output | derived output with deterministic rule | derived output | it must not become a second source of truth |
| Renderer location | Runtime | Runtime | Runtime | keeps byte-level determinism under one implementation boundary |
| Canonical Serialization | stdlib deterministic JSON | deterministic JSON serialization | canonical-json-v1 | gives stable bytes and stable hashes |
| Hash scope | separate content, binding, bundle hashes | same | frozen hash scoping per artifact | prevents approval hash from replacing business hashes |
| approval scope | content approval only | content approval only | approval bound to `prompt_content_hash` | keeps approval orthogonal to readiness and binding |
| inherited approval | allowed as evidence, not copy | copy is risky | allowed as evidence only | avoids fake approval rows |
| asset binding | stateful but not trusted without registry | can be locally asserted only | dual-axis completeness + verification | separates declaration from evidence |
| execution targets | not canonical | should stay out of canonical | execution planning only | keeps core target-neutral |
| generation strategy | execution planning only | should stay out of canonical | execution planning only | avoids platform pollution |
| frame requirements | execution planning only | should stay out of canonical | execution planning only | keeps canonical content platform-neutral |
| duration variance | allow ±2 seconds | allow controlled drift | ±2 seconds with explicit reason | balances continuity and practical split support |
| recursive freshness | required | required | required | prevents stale content from being promoted |
| legacy migration | explicit, fail closed | explicit, review-based | explicit migration command only | prevents silent rewriting |
| execution readiness | blocked until future planning exists | blocked in foundation | blocked | keeps execution separate from content approval |
| export semantics | formal, diagnostic, execution blocked | same split | formal review, diagnostic, execution blocked | preserves traceability and prevents accidental execution packaging |
| phase sequence | storyboard first | storyboard first | 0-5 frozen sequence | avoids reintroducing later refactors |

## 28. Deferred Decisions

The following items are deferred to later phases and are not open questions for this foundation:

- Phase 5: whether the first target set is only `libtv` and `agnes`, or whether a general target registry should be introduced from day one. The foundation stays neutral by keeping targets out of canonical JSON.
- Phase 5: adapter payload schema. The foundation avoids locking it by storing only canonical content.
- Phase 5: platform duration override policy. The foundation keeps timing variance policy inside Shot Prompt validation only.
- Phase 5: first/last frame and multi-reference execution modes. The foundation avoids locking them by keeping them out of canonical content.
- Future Asset Registry phase: external Visual Asset Registry API. The foundation avoids locking it by keeping `registry_verified` optional and impossible without a registry.
- Future Asset Registry phase: registry trust model. The foundation avoids locking it by separating local verification from registry verification.
- Future Asset Registry phase: remote asset verification. The foundation avoids locking it by keeping registry evidence optional.
- Future Asset Registry phase: cross-project asset sharing. The foundation avoids locking it by treating asset identifiers and evidence as local declarative state until the registry exists.
