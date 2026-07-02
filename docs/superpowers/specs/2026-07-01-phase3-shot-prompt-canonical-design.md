# Phase 3 Shot Prompt Canonical Foundation Design Spec

Document Status: DESIGN_SPEC_PENDING_USER_REVIEW
Review Status Addressed: DESIGN_SPEC_REVISION_REQUIRED
Design Date: 2026-07-02
Baseline Commit: 6e8adb961e32714ce5d5c36a33297072ee97473e
Implementation Planning: IMPLEMENTATION_PLANNING_NOT_AUTHORIZED
Implementation: IMPLEMENTATION_NOT_AUTHORIZED

This document is the Phase 3 design authority for Shot Prompt Canonical Foundation. It is intentionally design-only. It does not authorize code changes, database changes, migrations, skill updates, implementation planning, or remote push.

Phase 3 extends the Phase 0-2 Runtime, Store, Bundle, Gate, Validation, and Approval patterns already present in this repository. It does not create a parallel governance system.

## 1. Scope And Non-Scope

Phase 3 v1 scope is exactly `set`.

`set` means one Shot Prompt Set covers the complete approved source Storyboard Revision. It includes every shot in that Storyboard Revision and derives every prompt artifact from that single source revision.

Phase 3 v1 does not support `scene`, `shot_range`, partial set materialization, partial approval, or partial bundle eligibility. Those are deferred capabilities and must not appear in v1 canonical schema enums, validators, CLI commands, lifecycle states, or acceptance criteria.

The v1 source relationship is:

1. One approved Source Storyboard Revision is selected.
2. Runtime creates or reuses one Shot Prompt Set Artifact keyed by that source Storyboard Revision.
3. The Shot Prompt Set Artifact may have multiple Revisions.
4. Each Revision contains one complete canonical shot prompt set for the full source Storyboard Revision.
5. Approval and supersession happen at the Shot Prompt Set Revision level.

Phase 3 v1 outputs:

- canonical content for the full Shot Prompt Set;
- rendered positive prompts;
- rendered negative prompts;
- asset requirements;
- render provenance;
- review markdown;
- validation report;
- bundle manifest;
- approval qualification report outside the Content Bundle.

Phase 3 v1 explicitly preserves these boundaries:

- Storyboard facts are read-only inputs.
- Shot Prompt canonical content may reference Storyboard facts but must not mutate them.
- Draft authoring may temporarily contain only `shared_intent`.
- Formal canonical validation requires at least one modality intent: `image_intent` or `video_intent`.
- Language consistency is non-blocking lint.
- Platform-specific adapters are deferred.
- External asset binding by `asset_id`, URL, filesystem path, or upload ID is deferred.
- Waiver mechanics are deferred.
- Cross-Revision Review resolution is deferred.

## 2. Existing System Integration

Phase 3 is implemented by extending the current repository shape:

- `ai_drama_runtime/store.py` remains the Store boundary for artifacts, revisions, validation results, revision outputs, approval records, dependencies, and workflow gate records.
- `ai_drama_runtime/services.py` remains the Runtime orchestration boundary for create, validate, render, bundle, integrity, export, review, and approval flows.
- `ai_drama_runtime/validators.py` remains the validator registry and freshness-checking boundary.
- `ai_drama_runtime/storyboard_canonical.py` remains the model for canonical JSON discipline: required keys, closed objects, duplicate-key rejection, Unicode normalization, and deterministic content hashing.
- `ai_drama_runtime/storyboard_renderer.py` remains the renderer pattern for deterministic derived output.
- `ai_drama_runtime/storyboard_migration.py` remains a migration-preview pattern, not a Phase 3 execution target.
- `ai_drama_runtime/cli.py` remains the command surface boundary.
- `tools/verify_phase2_minimal_bundle_foundation.py` remains the verification pattern for bundle, gate, approval, and stale-state coverage.
- `skills/ai-drama-storyboard-design-skill/v0.2.1/skill.json` remains an upstream skill integration point and must not be edited by this design revision.

Current Store facts that Phase 3 must preserve:

- `revisions.content_object_id` is the authoritative canonical content pointer for a Revision.
- `revision_outputs` stores derived outputs and has `UNIQUE(revision_id, logical_type)`.
- Current `revision_outputs.logical_type` CHECK only allows `rendered_positive_prompt`, `rendered_negative_prompt`, `rendered_markdown`, and `bundle_manifest`.
- That CHECK is insufficient for Phase 3 because Phase 3 needs separate logical types for shot prompt positive prompts, negative prompts, asset requirements, render provenance, review markdown, and validation report.
- `revisions.approval_status` is currently text and has no DB CHECK.
- `one_current_approved_revision` is a unique index on `revisions(artifact_id) WHERE approval_status = 'approved'`.
- `approve_in_transaction` already supersedes old approved rows and approves the new row in one DB transaction.
- `approval_records.action` currently records script/storyboard action strings and is text.
- No review record tables currently exist.
- Migration definitions are repository-local; this repo uses Store DDL and migration verification files rather than an external migration framework.

Phase 3 implementation must extend these patterns. It must not introduce a second artifact registry, a second approval ledger, or a second bundle integrity mechanism.

## 3. Artifact Identity And Revision Model

The Phase 3 artifact type is `shot_prompt_set`.

Because v1 scope is exactly `set`, the artifact business key is exactly `source_storyboard_revision_id`.

Normative identity:

| Item | v1 rule |
| --- | --- |
| Artifact type | `shot_prompt_set` |
| Artifact business key type | `source_storyboard_revision_id` |
| Artifact business key value | the exact Source Storyboard Revision ID |
| Internal `artifact_id` | generated by Runtime/Store and not derived by string concatenation |
| Uniqueness | enforced by a DB unique index over artifact type and business key |
| Revision authority | each Revision has its own `revisions.content_object_id` |
| Revision count | one Shot Prompt Set Artifact may have multiple Revisions |

The migration implied by this design adds artifact business-key storage to the existing `artifacts` table:

- `business_key_type TEXT NOT NULL DEFAULT ''`;
- `business_key_value TEXT NOT NULL DEFAULT ''`;
- unique index `one_shot_prompt_set_per_source_storyboard_revision` on `(artifact_type, business_key_type, business_key_value)` where `artifact_type = 'shot_prompt_set'` and `business_key_type = 'source_storyboard_revision_id'`.

The service that creates a Shot Prompt Set Artifact must:

1. require an approved Source Storyboard Revision;
2. look up an existing `shot_prompt_set` Artifact by the business key;
3. create a generated internal `artifact_id` only when no matching Artifact exists;
4. insert a Revision for each authored canonical version;
5. record the source dependency with the existing revision dependency pattern.

Artifact identity is not a string naming convention. The unique DB index is the authority.

## 4. Canonical Content Contract

Canonical content is stored through `revisions.content_object_id`. It is not stored as an independent `revision_outputs` row.

Top-level object rules:

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | string | yes | empty no, null no | exact Phase 3 schema version; additionalProperties=false at root | invariant | identifies schema | identifies schema | blocks unknown version | no |
| `content_profile` | string | yes | empty no, null no | exact content profile | invariant | selects profile | selects profile | blocks unknown profile | no |
| `scope` | string | yes | empty no, null no | exact `set` only | invariant | included in provenance | included in provenance | blocks any other value | no |
| `source_storyboard_revision_id` | string | yes | empty no, null no | unique per artifact business key | invariant | included in provenance | included in provenance | must match artifact key | yes |
| `render_language` | string | yes | empty no, null no | enum `zh-Hans`, `en`; one formal language per Revision | invariant | controls natural-language render | controls natural-language render | language consistency lint is non-blocking | no |
| `renderer.profile_id` | string | yes | empty no, null no | exact renderer profile ID; no version range | invariant | selects renderer profile | selects renderer profile | blocks unknown profile | no |
| `renderer.version` | string | yes | empty no, null no | exact renderer version; no version range | invariant | selects renderer version | selects renderer version | blocks unavailable renderer | no |
| `shots` | array of shot objects | yes | empty no, null no | unique `shot_id`; additionalProperties=false | invariant for membership | render source order | render source order | blocks missing source shot | yes |
| `set_defaults` | object | optional | empty yes, null no | additionalProperties=false | see Section 8 | used before shot render | used before shot render | lint for unused defaults | yes when referencing facts |
| `review_policy` | object | optional | empty yes, null no | additionalProperties=false | invariant | not rendered as prompt | not rendered as prompt | lint only | no |

The root object has no `negative_constraints` field and no `asset_requirements` field. Negative constraint authority is limited to the set-default and shot-specific paths defined in Section 8. Asset reference authority is limited to `shots[].asset_reference_slots`; derived `asset-requirements.json` is output authority, not stored canonical authority.

Each `shots[]` item is closed with `additionalProperties=false` and contains:

- `shot_id`;
- `shared_intent`;
- optional `image_intent`;
- optional `video_intent`;
- optional `continuity`;
- optional shot-level `negative_constraints`;
- optional shot-level `asset_reference_slots`;
- optional `language_hint`.

`shot_id` is the exact source Storyboard shot ID. There is no separate shot-item `source_shot_id` field in stored canonical content; storing both would create duplicate shot identity authority.

Draft canonical validation may accept a shot with only `shared_intent`. Formal canonical validation requires each shot to include `image_intent`, `video_intent`, or both. If both modality intents are absent at formal validation, the Revision cannot proceed to rendering.

Authoring schema and stored canonical schema are the same contract. Runtime may reject, normalize, and serialize authoring input, but it must not inject undefined canonical business fields. Allowed Runtime transformations before storing canonical content are limited to:

- duplicate-key rejection during JSON parse;
- Unicode NFC normalization;
- deterministic object serialization for hashing and storage;
- validation of exact `renderer.profile_id` and `renderer.version`;
- rejection of derived-only fields such as `slot_id`, object hashes, bundle hashes, timestamps, external upload data, and qualification evidence.

Derived fields appear only in derived outputs, Store rows, or approval evidence. They are not hidden Runtime additions to canonical content.

### 4.1 `shared_intent`

`shared_intent` is required for every shot. It contains modality-neutral prompt intent.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `subject_emphasis` | string | yes | empty no, null no | closed parent object | replace | primary subject phrase | primary subject phrase | warns when contradicting source entities | yes |
| `performance_direction` | string | optional | empty no when present, null no | closed parent object | replace | actor expression/pose phrase | actor action/performance phrase | warns when too generic | yes |
| `composition` | string | optional | empty no when present, null no | closed parent object | replace | framing/composition phrase | framing/composition phrase | warns on camera contradiction | yes |
| `lighting` | string | optional | empty no when present, null no | closed parent object | replace | still image lighting phrase | video lighting phrase | warns on mood mismatch | yes |
| `mood` | string | optional | empty no when present, null no | closed parent object | replace | mood phrase | mood phrase | language consistency lint | optional |
| `style_tags` | array of strings | optional | empty yes, null no | unique after append_dedup normalization | append_dedup | appended as style modifiers | appended as style modifiers | warns on unsupported platform terms | no |
| `spatial_constraints` | array of strings | optional | empty yes, null no | unique after append_dedup normalization | append_dedup | appended as placement constraints | appended as movement/blocking constraints | warns on unanchored constraints | yes |

### 4.2 `image_intent`

`image_intent` is optional in Draft and required for a shot that must produce image prompts. It is closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `frame_purpose` | string | yes when object exists | empty no, null no | enum `establishing`, `character`, `action`, `detail`, `transition` | replace | selects prompt emphasis | ignored except provenance | warns if purpose mismatches shot role | yes |
| `composition_adjustment` | string | optional | empty no when present, null no | closed parent object | replace | modifies shared composition | ignored | warns when redundant | optional |
| `stillness_requirement` | string | optional | empty no when present, null no | closed parent object | replace | adds still-frame stability | ignored | warns when video-only language appears | optional |
| `detail_emphasis` | array of strings | optional | empty yes, null no | unique after append_dedup normalization | append_dedup | appended as detail clauses | ignored | warns on non-source details | yes |
| `image_only_constraints` | array of strings | optional | empty yes, null no | unique after append_dedup normalization | append_dedup | appended only to image prompt | ignored | warns on contradiction | optional |

### 4.3 `video_intent`

`video_intent` is optional in Draft and required for a shot that must produce video prompts. It is closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `motion_intent` | string | yes when object exists | empty no, null no | closed parent object | replace | ignored | primary motion phrase | warns on impossible motion | yes |
| `camera_motion_intent` | string | optional | empty no when present, null no | closed parent object | replace | ignored | camera movement phrase | warns on contradiction with source camera facts | yes |
| `performance_progression` | string | optional | empty no when present, null no | closed parent object | replace | ignored | temporal performance phrase | warns on timeline ambiguity | yes |
| `temporal_continuity` | string | optional | empty no when present, null no | closed parent object | replace | ignored | continuity bridge phrase | warns on missing source shot link | yes |
| `video_only_constraints` | array of strings | optional | empty yes, null no | unique after append_dedup normalization | append_dedup | ignored | appended only to video prompt | warns on still-image terms | optional |
| `dialogue_intents` | array of objects | optional | empty yes, null no | unique `source_dialogue_ref`; child objects closed | append_dedup by `source_dialogue_ref` | ignored | rendered as speech/performance clauses | validates source dialogue, timing, and visibility consistency | yes |

### 4.4 `dialogue_intents` And `delivery`

`dialogue_intents[]` objects are closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `source_dialogue_ref` | string | yes | empty no, null no | unique within the shot; must point to source Storyboard dialogue in this shot | append_dedup identity key | ignored | orders dialogue clause by source order | blocks duplicate or cross-shot ref | yes |
| `utterance_mode` | string | yes | empty no, null no | enum `spoken`, `narration`, `inner_voice` | replace | ignored | selects vocalization mode | blocks lip-sync mismatch | yes |
| `speaker_visibility` | string | yes | empty no, null no | enum `visible`, `partially_visible`, `off_screen`, `not_applicable` | replace | ignored | selects visibility clause | blocks invalid visibility | yes |
| `lip_sync` | boolean | optional | null no | only meaningful for `spoken` with visible speaker | replace | ignored | adds lip-sync instruction when true | blocks impossible lip-sync | yes |
| `relative_timing` | string | yes | empty no, null no | enum `immediate`, `after_brief_pause`, `after_action_cue`, `after_reaction_cue`, `after_previous_complete`, `interrupt_previous`, `overlap_previous` | replace | ignored | renders relative timing phrase | blocks missing timing | yes |
| `post_dialogue_hold` | string | optional | empty no when present, null no | enum `none`, `brief`, `sustained` | replace | ignored | renders post-dialogue hold phrase | lint for overuse | optional |
| `delivery` | object | optional | empty yes, null no | additionalProperties=false | replace | ignored | renders performance delivery | lint for over-specification | optional |

Speaker identity is derived from the referenced Storyboard dialogue. Shot Prompt Canonical does not store `speaker_entity_id` or duplicate speaker facts as editable authority.

`delivery` is closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `emotion` | string | optional | empty no when present, null no | closed parent object | replace | ignored | vocal emotion phrase | warns on source mismatch | yes |
| `pace` | string | optional | empty no when present, null no | closed parent object | replace | ignored | speech pace phrase | warns on vague pacing | optional |
| `volume` | string | optional | empty no when present, null no | closed parent object | replace | ignored | volume phrase | warns on unsupported extremes | optional |
| `articulation` | string | optional | empty no when present, null no | closed parent object | replace | ignored | articulation phrase | warns on ambiguity | optional |
| `gaze` | string | optional | empty no when present, null no | closed parent object | replace | ignored | gaze/performance phrase | validates visible speaker when required | yes |
| `expression` | string | optional | empty no when present, null no | closed parent object | replace | ignored | expression phrase | warns if contradicting emotion | yes |
| `gesture` | string | optional | empty no when present, null no | closed parent object | replace | ignored | gesture phrase | validates source entity presence | yes |

Consistency rules:

- `utterance_mode = spoken` permits `speaker_visibility` of `visible`, `partially_visible`, or `off_screen`.
- `utterance_mode = spoken` with `lip_sync = true` requires `speaker_visibility` of `visible` or `partially_visible`.
- `utterance_mode = narration` requires `speaker_visibility = not_applicable` and does not permit `lip_sync = true`.
- `utterance_mode = inner_voice` requires `speaker_visibility = not_applicable` and does not permit `lip_sync = true`.
- `speaker_visibility = off_screen` does not permit `lip_sync = true`.

### 4.5 `continuity`

Continuity is Shot/Entity level. The field named `scope` inside a continuity item is not the artifact scope; artifact scope remains exactly `set`.

Continuity item objects are closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `entity_type` | string | yes | empty no, null no | enum `shot`, `character`, `prop`, `location` | append_dedup identity component | renders continuity subject | renders continuity subject | blocks unknown type | yes |
| `entity_id` | string | yes | empty no, null no | must exist in current shot membership; for `shot`, equals current `shot_id` | append_dedup identity component | renders entity continuity | renders entity continuity | blocks global-only references | yes |
| `requirement` | string | yes | empty no, null no | closed parent object | append_dedup identity component | continuity phrase | continuity phrase | warns if vague | yes |
| `scope` | string | yes | empty no, null no | enum `set_baseline`, `previous_occurrence`, `specific_shot` | append_dedup identity component | controls continuity source | controls continuity source | blocks non-v1 values | yes |
| `source_shot_id` | string | required only when `scope = specific_shot` | empty no when present, null no | must exist in source Storyboard | append_dedup identity component | bridge reference | temporal bridge reference | blocks missing target for `specific_shot` | yes |
| `purposes` | array of strings | optional | empty yes, null no | enum values `image`, `video`, `asset_requirement`, `negative_prompt`; unique after append_dedup normalization | append_dedup value | filters image use | filters video use | warns when omitted and ambiguous | no |
| `note` | string | optional | empty no when present, null no | closed parent object | append_dedup value | not rendered unless selected by renderer profile | not rendered unless selected by renderer profile | lint only | optional |

### 4.6 `negative_constraints`

Negative constraints are explicit author constraints. They are distinct from renderer fact invariants.

Each negative constraint object is closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `constraint_id` | string | yes | empty no, null no | unique stable identity key | append_dedup identity key | orders negative clause | orders negative clause | blocks duplicates | no |
| `category` | string | yes | empty no, null no | enum `identity`, `composition`, `motion`, `text`, `artifact`, `safety`, `continuity` | append_dedup payload; divergent duplicate ID fails | groups negative prompt | groups negative prompt | warns on wrong category | optional |
| `text` | string | yes | empty no, null no | closed parent object | append_dedup payload; divergent duplicate ID fails | rendered as negative text | rendered as negative text | warns on vague or positive wording | optional |
| `modality_usage` | string | yes | empty no, null no | enum `image`, `video`, `both` | append_dedup payload; divergent duplicate ID fails | included when image or both | included when video or both | blocks impossible modality | no |

Ordering is deterministic: set defaults first, then shot-level values, preserving first occurrence after append_dedup normalization. Renderers must not sort by locale.

### 4.7 `asset_reference_slots`

Asset reference slot objects are authoring canonical. They are closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `shot_id` | string | yes | empty no, null no | must be in current set | append_dedup identity component | groups asset requirements | groups asset requirements | blocks missing shot | yes |
| `entity_type` | string | yes | empty no, null no | enum `character`, `prop`, `location` | append_dedup identity component | entity reference | entity reference | blocks unsupported entity type | yes |
| `entity_id` | string | yes | empty no, null no | must belong to current Shot membership | append_dedup identity component | entity reference | entity reference | blocks global-only reference | yes |
| `purposes` | array of objects | yes | empty no, null no | one slot may contain multiple purposes; each purpose object closed | append_dedup payload; divergent duplicate slot fails | purpose notes | purpose notes | keeps enum coarse-grained | yes |
| `notes` | array of strings | optional | empty yes, null no | unique after append_dedup normalization | append_dedup | optional note | optional note | lint only | optional |

Purpose objects are closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `purpose` | string | yes | empty no, null no | enum `identity`, `wardrobe`, `prop`, `environment`, `continuity` | append_dedup identity key within slot | purpose note | purpose note | keeps enum coarse-grained | yes |
| `requirement` | string | yes | empty no, null no | enum `required`, `optional` | append_dedup payload | requirement note | requirement note | warns on optional high-risk omission | yes |
| `modality_usage` | array of strings | yes | empty no, null no | enum values `image`, `video`; unique after append_dedup normalization | append_dedup payload | filters image use | filters video use | blocks unsupported modality | no |
| `usage_note` | string | optional | empty no when present, null no | required when intent is ambiguous | append_dedup payload | optional note | optional note | lint for vague note | optional |

Each shot may contain at most one asset reference slot for the same `(entity_type, entity_id)`. That slot contains one or more purpose objects. This avoids one-slot-per-purpose duplication.

`slot_id` is not an author-maintained canonical field and does not appear in stored canonical content. It is Runtime-owned derived output for `asset-requirements.json` only:

`slot_` + first 24 hex characters of SHA-256 over the NFC-normalized tuple:

`source_storyboard_revision_id`, `shot_id`, `entity_type`, `entity_id`.

Because `purpose` is not part of the tuple, one asset slot can carry multiple purposes without producing multiple slot IDs. Validators reject any authored `slot_id` in canonical input.

Asset slots do not require empty entries for every Storyboard entity. Only entities that need an asset reference slot appear in `asset_reference_slots`. An asset entity must belong to the current Shot membership; upstream canon may provide details for that entity, but it cannot expand the set of entities allowed for the shot.

## 5. Storyboard Fact Binding

The Source Storyboard Revision is the authority for:

- shot IDs and ordering;
- shot membership;
- characters present in each shot;
- props present in each shot;
- location or environment facts attached to the shot;
- source dialogue references;
- source camera and continuity facts already canonicalized upstream.

Shot Prompt canonical content may add rendering intent, emphasis, and constraints. It may not add a new Storyboard entity to a shot, change source facts, or silently reinterpret a source fact.

Validation must resolve every Storyboard fact reference against the Source Storyboard Revision content object. This includes shot item `shot_id`, continuity `source_shot_id`, continuity `entity_id`, `source_dialogue_ref`, and asset reference slot `entity_id`.

Speaker facts are derived from the Storyboard dialogue entry referenced by `source_dialogue_ref`. Shot Prompt Canonical does not copy speaker identity as editable prompt authority.

Upstream canon can enrich details for a referenced entity after the entity is already present in the shot. Upstream canon cannot be used to add a missing character, prop, or location to the current shot.

## 6. Modality Semantics

Phase 3 v1 supports three intent layers:

- `shared_intent`: required modality-neutral intent;
- `image_intent`: optional image-specific intent;
- `video_intent`: optional video-specific intent.

Draft validation accepts shared-only content so authors can start a Revision before committing to modality outputs.

Formal canonical validation requires:

- every shot has `shared_intent`;
- every shot has `image_intent`, `video_intent`, or both;
- image rendering only uses shots with `image_intent`;
- video rendering only uses shots with `video_intent`;
- a set intended for both modalities must satisfy both modality validations.

Output coverage is a render validation concern, not pre-render canonical validation. Canonical validation verifies authoring content and source references before render. Render validation verifies that required rendered outputs exist and match the requested modality coverage after render.

## 7. Canonical Locked Constraints And Renderer Fact Invariants

Phase 3 distinguishes two kinds of constraints.

Canonical locked constraints are persisted in canonical content. They can block canonical validation when the author contradicts them. Examples:

- artifact `scope` is exactly `set`;
- `source_storyboard_revision_id` matches the artifact business key;
- set-default fields with merge policy `invariant`;
- source shot membership rules;
- dialogue visibility and lip-sync consistency rules;
- formal validation modality requirements.

Renderer fact invariants are deterministic renderer-generated protections. They are not authored canonical fields and do not create new canonical capabilities. They are applied during rendering to protect source facts in prompts.

The v1 renderer fact invariant set is small and fixed:

- preserve named entity identity and role from the Source Storyboard Revision;
- prevent unlisted current-shot entities from appearing;
- protect current-shot location and time facts;
- protect continuity requirements already validated in canonical content;
- prevent readable text not present in source facts from being introduced.

The invariant set is versioned in render provenance by `invariant_set_id` and `invariant_set_version`. It is not a substitute for explicit `negative_constraints`; negative rendering uses explicit negative constraints plus the small fixed invariant set.

## 8. Set Defaults And Merge Semantics

`set_defaults` is an optional object that applies across the Shot Prompt Set before shot-level values are rendered.

Only three merge policies exist in v1:

- `replace`: shot-level value replaces the set default for that field;
- `append_dedup`: set default values are emitted first, then shot-level values, with deterministic deduplication;
- `invariant`: shot-level value may omit or repeat the set value, but conflicting values fail canonical validation.

`set_defaults` is closed with `additionalProperties=false`.

| Field | Type | Required | Empty/null | Enum/unique/closed | Merge policy | Image renderer | Video renderer | Authoring lint | Storyboard fact reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `shared_intent` | object | optional | empty yes, null no | only supported child paths; additionalProperties=false | child path policy | image uses merged values | video uses merged values | warns on unused defaults | optional |
| `image_intent` | object | optional | empty yes, null no | only supported child paths; additionalProperties=false | child path policy | image uses merged values | ignored | warns when no image shots exist | optional |
| `video_intent` | object | optional | empty yes, null no | only supported child paths; additionalProperties=false | child path policy | ignored | video uses merged values | warns when no video shots exist | optional |
| `continuity` | array of objects | optional | empty yes, null no | child objects additionalProperties=false; stable key unique | append_dedup | filtered by purposes | filtered by purposes | validates source facts | yes |
| `negative_constraints` | array of objects | optional | empty yes, null no | child objects additionalProperties=false; `constraint_id` unique | append_dedup | filtered by modality | filtered by modality | warns on vague text | optional |
| `review_policy` | object | optional | empty yes, null no | additionalProperties=false | invariant | not rendered | not rendered | lint only | no |

Supported set-default paths:

| Path | Value type | Merge policy | Stable identity key | Renderer behavior |
| --- | --- | --- | --- | --- |
| `shared_intent.subject_emphasis` | string | replace | field path | image and video use merged value |
| `shared_intent.performance_direction` | string | replace | field path | image and video use merged value |
| `shared_intent.composition` | string | replace | field path | image and video use merged value |
| `shared_intent.lighting` | string | replace | field path | image and video use merged value |
| `shared_intent.mood` | string | replace | field path | image and video use merged value |
| `shared_intent.style_tags` | string array | append_dedup | normalized string | image and video append merged tags |
| `shared_intent.spatial_constraints` | string array | append_dedup | normalized string | image and video append merged constraints |
| `image_intent.frame_purpose` | string enum | replace | field path | image renderer only |
| `image_intent.composition_adjustment` | string | replace | field path | image renderer only |
| `image_intent.stillness_requirement` | string | replace | field path | image renderer only |
| `image_intent.detail_emphasis` | string array | append_dedup | normalized string | image renderer only |
| `image_intent.image_only_constraints` | string array | append_dedup | normalized string | image renderer only |
| `video_intent.motion_intent` | string | replace | field path | video renderer only |
| `video_intent.camera_motion_intent` | string | replace | field path | video renderer only |
| `video_intent.performance_progression` | string | replace | field path | video renderer only |
| `video_intent.temporal_continuity` | string | replace | field path | video renderer only |
| `video_intent.video_only_constraints` | string array | append_dedup | normalized string | video renderer only |
| `continuity` | object array | append_dedup | `entity_type`, `entity_id`, `scope`, `source_shot_id`, `requirement` | filtered by `purposes` |
| `negative_constraints` | object array | append_dedup | `constraint_id` | filtered by `modality_usage` |
| `review_policy` | object | invariant | field path | not rendered |

`set_defaults.negative_constraints` is the only set-wide negative constraint location. Shot-level `negative_constraints` is the only shot-specific negative constraint location. The root object has no negative constraint field, and derived rendered negative prompts are never canonical authority.

`append_dedup` is frozen:

1. Normalize strings with Unicode NFC.
2. Trim leading and trailing whitespace.
3. Compare case-sensitively.
4. Preserve first occurrence.
5. Preserve Set default order, then Shot append order.
6. Object arrays deduplicate by the schema-defined stable identity key.
7. Do not use locale-dependent sorting.

For object arrays, exact duplicate canonical objects coalesce by stable identity key. A duplicate identity key with different payload fails canonical validation rather than silently replacing values.

Canonical validation and renderers must use the same append_dedup implementation.

## 9. Rendering Contract

Rendering is deterministic and derived. Rendered outputs never become canonical authority.

The Phase 3 renderer produces:

- `rendered-positive-prompts.json`;
- `rendered-negative-prompts.json`;
- `asset-requirements.json`;
- `render-provenance.json`;
- `review.md`.

The Validation Orchestrator produces `validation-report.json`. The Prompt Renderer does not generate validation reports.

Positive prompt rendering:

- starts from merged `shared_intent`;
- adds `image_intent` for image output;
- adds `video_intent` for video output;
- adds validated continuity requirements;
- applies dialogue rendering only for video prompts;
- includes Storyboard fact references only through validated canonical references.

Negative prompt rendering:

- starts from explicit `negative_constraints`;
- filters by `modality_usage`;
- adds the fixed renderer fact invariant set;
- preserves deterministic order;
- records invariant set metadata in render provenance.

Render provenance is minimal:

| Field | Purpose |
| --- | --- |
| `renderer_id` | renderer identity |
| `renderer_version` | renderer version |
| `source_storyboard_revision_id` | source binding |
| `shot_prompt_revision_id` | canonical revision binding |
| `canonical_content_hash` | canonical input hash |
| `renderer_profile_id` | render profile |
| `renderer_profile_version` | render profile version |
| `invariant_set_id` | renderer fact invariant set |
| `invariant_set_version` | renderer fact invariant version |
| `rendered_output_hashes` | hash per renderer-derived output, excluding `render-provenance.json`, `bundle-manifest.json`, and `qualification-report.json` |

Render provenance does not store its own hash, the Bundle Manifest hash, the Qualification Report hash, external upload information, platform adapter state, or mutable review state.

## 10. Content Bundle And Revision Outputs

The Content Bundle is materialized after canonical validation and rendering. It contains the canonical source member and the derived members required to reproduce bundle integrity.

Bundle member and `revision_outputs.logical_type` mapping is frozen:

| Bundle member | Authority | `revision_outputs.logical_type` | Bundle member | Manifest member | Notes |
| --- | --- | --- | --- | --- | --- |
| `canonical-content.json` | `revisions.content_object_id` | none | yes | yes | virtual/source member; no independent output row |
| `rendered-positive-prompts.json` | derived output | `shot_prompt_positive_prompts` | yes | yes | replaces generic positive logical type for Phase 3 |
| `rendered-negative-prompts.json` | derived output | `shot_prompt_negative_prompts` | yes | yes | replaces generic negative logical type for Phase 3 |
| `asset-requirements.json` | derived output | `shot_prompt_asset_requirements` | yes | yes | deterministic from canonical asset requirements |
| `render-provenance.json` | derived output | `shot_prompt_render_provenance` | yes | yes | minimal provenance |
| `review.md` | derived output | `shot_prompt_review_markdown` | yes | yes | derived review surface, not review state |
| `validation-report.json` | Validation Orchestrator output | `shot_prompt_validation_report` | yes | yes | formal/render validation report; not renderer output |
| `bundle-manifest.json` | derived output | `bundle_manifest` | yes | self | manifest is written to bundle but is not included in its own member hash list |
| `qualification-report.json` | Approval Evidence | none | no | no | generated after human review and bundle integrity pass |

`canonical-content.json` is a virtual/source member. Its bytes come from `revisions.content_object_id`. The manifest records its member hash and logical role, but Store does not insert a `revision_outputs` row for it.

`bundle-manifest.json` records hashes for every bundle member except itself. Its own hash can be stored on the `bundle_manifest` output row as `content_hash` and `bundle_manifest_hash`, following the existing bundle pattern.

The Phase 3 migration must expand the current `revision_outputs.logical_type` CHECK to include:

- existing values required by earlier phases;
- `shot_prompt_positive_prompts`;
- `shot_prompt_negative_prompts`;
- `shot_prompt_asset_requirements`;
- `shot_prompt_render_provenance`;
- `shot_prompt_review_markdown`;
- `shot_prompt_validation_report`;
- `bundle_manifest`.

The current CHECK is insufficient because it does not distinguish Phase 3 shot prompt outputs and cannot represent all required bundle members.

## 11. Validation And Gate Layers

Phase 3 has four separate layers. They must not be collapsed.

### 11.1 Canonical Validation

Canonical Validation runs before rendering.

It validates:

- JSON parsing with duplicate-key rejection;
- schema version and content profile;
- root `scope = set`;
- closed objects and additionalProperties=false;
- source Storyboard Revision binding;
- full source shot coverage;
- Storyboard fact references;
- draft shared-only permissiveness;
- formal modality requirement;
- merge policy validity;
- continuity and asset membership;
- dialogue visibility and lip-sync consistency;
- language consistency lint as non-blocking lint.

Canonical Validation does not validate bundle integrity. Canonical Validation does not block because of open review records. Canonical Validation does not verify rendered output coverage.

Persistence:

- blocking canonical failures are stored through `validation_results`;
- non-blocking lint appears in validation report data with non-blocking severity;
- canonical content remains authoritative only through `revisions.content_object_id`.

### 11.2 Render Validation

Render Validation runs after rendering and before bundle materialization.

It validates:

- required rendered files were produced for the requested modality coverage;
- rendered outputs match deterministic renderer expectations;
- render provenance references the expected canonical content hash;
- negative outputs include explicit constraints and renderer fact invariants;
- output files are well-formed JSON or Markdown as applicable.

Render Validation is where output coverage belongs. It is not pre-render canonical validation.

Persistence:

- render validation results are stored through `validation_results`;
- the Validation Orchestrator writes `validation-report.json` and stores it as `shot_prompt_validation_report`;
- output rows use the frozen logical types in Section 10.

### 11.3 Bundle Integrity

Bundle Integrity runs after Content Bundle materialization.

It validates:

- required bundle members exist;
- member hashes match object storage;
- manifest bytes match deterministic manifest generation;
- manifest member list excludes the manifest self-hash list;
- source canonical content hash matches `revisions.content_object_id`;
- revision output rows match the manifest.

Bundle Integrity is not Canonical Validation.

Persistence:

- bundle manifest is stored as `revision_outputs.logical_type = bundle_manifest`;
- bundle integrity results are stored through the existing validation/gate result pattern;
- export records may reference the bundle manifest hash for exports.

### 11.4 Approval Qualification

Approval Qualification runs after:

1. Canonical Validation PASS;
2. Rendering PASS;
3. Content Bundle Materialization complete;
4. Bundle Integrity PASS;
5. Human Review status has no unresolved blocking review records.

Approval Qualification validates readiness for human approval. It is not part of the Content Bundle.

It generates immutable `qualification-report.json` after the qualification check passes. That report is Approval Evidence:

- no `revision_outputs` row;
- no Content Bundle member;
- no manifest member;
- immutable object stored outside bundle outputs;
- hash bound by the approval record.

Approval binds the qualification report hash and the bundle manifest hash in the approval transaction.

Open blocking review records are an Approval Qualification failure, not a canonical validation failure and not a bundle integrity failure.

## 12. Lifecycle And State Transitions

Phase 3 v1 lifecycle states are represented through existing Revision records, validation results, revision outputs, review records, and approval records.

Lifecycle:

| Lifecycle state | Storage authority | Entry condition | Exit condition |
| --- | --- | --- | --- |
| Draft | `revisions.approval_status` not approved/rejected/superseded/revoked | Revision exists; canonical content may be shared-only | formal canonical validation requested |
| Formal-valid | `validation_results` | Canonical Validation PASS | rendering requested |
| Rendered | `revision_outputs` | Render Validation PASS | bundle materialization requested |
| Bundle-ready | `revision_outputs` plus bundle integrity result | Bundle Integrity PASS | human review requested |
| Reviewable | review records | bundle-ready and review surface exists | all blocking review records resolved |
| Approved | `revisions.approval_status = 'approved'` plus approval record | Approval Qualification PASS and approval transaction commits | superseded or revoked |
| Rejected | `revisions.approval_status = 'rejected'` plus approval record | reviewer rejects | new Revision required for another attempt |
| Superseded | `revisions.approval_status = 'superseded'` | newer Revision of same Artifact approved | terminal historical state |
| Revoked | `revisions.approval_status = 'revoked'` plus approval record | approval revoked | terminal historical state |

Superseded behavior is exact:

- use `revisions.approval_status = 'superseded'`;
- keep the existing unique index `one_current_approved_revision`;
- update old approved rows and the new approved row in one Store transaction;
- insert approval action `shot_prompt_approved` for the new approved Revision.

Revocation behavior is exact:

- add approval action `shot_prompt_approval_revoked`;
- update the current approved Revision to `revisions.approval_status = 'revoked'`;
- insert the revoke approval record in the same transaction;
- historical approval records remain immutable;
- no older Revision is automatically re-approved.

Rejection behavior is exact:

- add approval action `shot_prompt_rejected`;
- update the target Revision to `revisions.approval_status = 'rejected'`;
- insert the rejection approval record in the same transaction.

`approval_status` is not used to store Canonical Validation, Render Validation, Bundle Integrity, or Approval Qualification intermediate status.

## 13. Review Records And Approval Evidence

Human review state is stored outside the Content Bundle. It does not mutate canonical content and is not represented by `review.md`.

`review.md` is a deterministic derived review surface inside the bundle. It helps reviewers inspect the set. It is not the mutable review ledger.

The Phase 3 migration adds `review_records`:

| Column | Rule |
| --- | --- |
| `review_id` | primary key |
| `artifact_id` | existing Artifact ID |
| `revision_id` | exact current Shot Prompt Set Revision |
| `scope` | enum `set`, `shot` |
| `shot_id` | null when `scope = set`; required source shot ID when `scope = shot` |
| `body` | immutable review text |
| `body_hash` | hash of immutable body |
| `blocking` | boolean; unresolved true blocks Approval Qualification |
| `created_by` | reviewer identity string |
| `created_at` | creation timestamp |

The Phase 3 migration adds `review_record_events`:

| Column | Rule |
| --- | --- |
| `event_id` | primary key |
| `review_id` | foreign key to `review_records` |
| `event_type` | enum `opened`, `resolved`, `reopened`, `voided` |
| `actor` | actor identity string |
| `note` | optional event note |
| `created_at` | event timestamp |

Review status is computed from events:

- a new review record starts with an `opened` event;
- latest event `resolved` means resolved;
- latest event `reopened` means open;
- latest event `voided` removes the record from blocking calculations but preserves history.

Review body is immutable. Status changes are append-only events.

Set-level review records apply to the whole Revision and have `shot_id IS NULL`. Shot-level review records apply to one source shot in the current Revision and require `shot_id`.

Review records apply only to the exact current Revision they reference. A new Revision does not automatically inherit, resolve, or force prior review records. Cross-Revision Review resolution is deferred.

Approval Evidence:

- `qualification-report.json` is generated after Approval Qualification passes;
- it is stored as an immutable object outside `revision_outputs`;
- `approval_records` gains evidence columns for shot prompt approvals;
- the approval transaction stores the qualification report hash, bundle manifest hash, canonical content hash, renderer profile, qualification profile, and source Storyboard Revision ID.

Required approval record evidence columns:

| Column | Purpose |
| --- | --- |
| `source_storyboard_revision_id` | binds approval to source |
| `canonical_content_hash` | binds approval to canonical content |
| `bundle_manifest_hash` | binds approval to verified bundle |
| `qualification_report_hash` | binds approval to immutable qualification report |
| `qualification_report_object_id` | locates immutable qualification report object |
| `renderer_profile_id` | renderer profile approved |
| `renderer_profile_version` | renderer profile version approved |
| `qualification_profile_id` | qualification rule profile |
| `qualification_profile_version` | qualification rule profile version |

Approval Qualification evidence is required for `shot_prompt_approved`.

## 14. Phase 4 Eligibility Boundary

Phase 4 Eligibility remains live-computed. It is not frozen by the historical qualification report.

The live computation must check current state:

- Shot Prompt Revision is still approved;
- Source Storyboard Revision dependency is still fresh according to recursive freshness rules;
- Content Bundle integrity still passes;
- approval evidence hashes still match stored objects;
- there are no unresolved blocking review records for the current Revision;
- required render outputs still exist.

The immutable qualification report explains why approval was allowed at the approval moment. It does not replace live eligibility checks for downstream execution.

## 15. Store And Migration Requirements

This section defines schema changes required by a later implementation. This document does not execute them.

Artifact identity migration:

- add `business_key_type TEXT NOT NULL DEFAULT ''` to `artifacts`;
- add `business_key_value TEXT NOT NULL DEFAULT ''` to `artifacts`;
- add unique index `one_shot_prompt_set_per_source_storyboard_revision` on `(artifact_type, business_key_type, business_key_value)` for `shot_prompt_set` rows with `business_key_type = 'source_storyboard_revision_id'`.

Revision output migration:

- rebuild or alter `revision_outputs.logical_type` CHECK to keep earlier phase values and add the Phase 3 shot prompt values listed in Section 10;
- preserve `UNIQUE(revision_id, logical_type)`;
- preserve `revision_outputs_content_hash_idx`;
- preserve `revision_outputs_object_id_idx`.

Revision approval-state migration:

- rebuild `revisions` with approval status CHECK values `pending`, `approved`, `rejected`, `superseded`, `revoked`;
- preserve existing `one_current_approved_revision` unique index exactly on approved rows;
- do not use approval status for validation or bundle states.

Approval record migration:

- preserve current script and storyboard action values;
- add shot prompt action enum values `shot_prompt_approved`, `shot_prompt_rejected`, and `shot_prompt_approval_revoked`;
- add approval evidence columns from Section 13;
- require evidence columns for `shot_prompt_approved` at service validation level;
- keep records append-only.

Review table migration:

- create `review_records`;
- create `review_record_events`;
- enforce `review_records.scope` values `set` and `shot`;
- enforce `scope = set` with `shot_id IS NULL`;
- enforce `scope = shot` with `shot_id IS NOT NULL`;
- add index `review_records_revision_shot_idx` on `(revision_id, shot_id)`;
- add index `review_records_artifact_revision_idx` on `(artifact_id, revision_id)`;
- add index `review_record_events_review_id_created_idx` on `(review_id, created_at)`;
- enforce event types `opened`, `resolved`, `reopened`, `voided`;
- compute status from events rather than storing mutable status on `review_records`.

Transaction requirements:

- approval supersession remains one transaction;
- revocation updates `revisions.approval_status` and inserts `approval_records` in one transaction;
- rejection updates `revisions.approval_status` and inserts `approval_records` in one transaction;
- approval inserts the approval record with evidence hashes in the same transaction that sets `approved`;
- review event insertion is append-only and never rewrites review body.

## 16. CLI And Service Surface

Phase 3 CLI and service work must follow existing command and service patterns.

Required service responsibilities:

- create or locate the `shot_prompt_set` Artifact by business key;
- create a new Revision from canonical content;
- run Draft Canonical Validation;
- run Formal Canonical Validation;
- render deterministic outputs;
- materialize the Content Bundle;
- check Bundle Integrity;
- create immutable review surface output;
- create and update review records through append-only events;
- run Approval Qualification;
- write immutable qualification report outside the bundle;
- approve, reject, supersede, or revoke through Store transactions.

Required CLI shape:

- commands must be explicit about Source Storyboard Revision ID;
- commands must not accept v1 partial set selectors;
- Draft validation command may accept shared-only content;
- formal validation command must enforce modality requirements;
- bundle command must run only after render validation passes;
- approval command must run only after Approval Qualification passes;
- revoke command must use `shot_prompt_approval_revoked`.

No CLI command in v1 accepts platform adapter configuration, external upload binding, partial set approval, or waiver input.

## 17. Test And Acceptance Criteria

Acceptance criteria must be executable and must cover:

1. artifact identity: one Source Storyboard Revision maps to one Shot Prompt Set Artifact by DB unique key;
2. revisions: the Artifact may have multiple Revisions;
3. v1 scope: only `set` is valid;
4. render contract: `render_language`, `renderer.profile_id`, and `renderer.version` are required and exact;
5. authority: root has no negative constraints and no asset requirements authority;
6. draft validation: shared-only Draft passes Draft Canonical Validation;
7. formal validation: shared-only content fails Formal Canonical Validation;
8. modality validation: image-only and video-only shots render only their modality outputs;
9. source binding: invalid `shot_id`, continuity `source_shot_id`, `source_dialogue_ref`, or asset slot `entity_id` fails canonical validation;
10. shot identity: shot item does not store both `shot_id` and `source_shot_id`;
11. asset slots: no empty slots are required for unused Storyboard entities;
12. asset slots: each shot has at most one slot per entity and each slot may contain multiple purposes;
13. `slot_id`: derived only in `asset-requirements.json`, excludes purpose from the derivation tuple, and is rejected in authored canonical content;
14. purpose enum: only the coarse v1 asset purposes are valid;
15. continuity: continuity source scope is limited to `set_baseline`, `previous_occurrence`, and `specific_shot`;
16. dialogue: `source_dialogue_ref`, `relative_timing`, and `post_dialogue_hold` rules are validated, and speaker identity is derived from Storyboard dialogue;
17. merge: only `replace`, `append_dedup`, and `invariant` exist;
18. append_dedup: NFC, trim, case-sensitive, first occurrence, default-before-shot order, object identity key, and no locale sorting are covered;
19. negative rendering: explicit constraints plus renderer fact invariants are present;
20. language lint: language consistency warning does not block formal validation, rendering, bundle integrity, or approval by itself;
21. render provenance: does not contain its own hash, Bundle Manifest hash, or Qualification Report hash;
22. validation report: `validation-report.json` is generated by the Validation Orchestrator, not the Prompt Renderer;
23. output mapping: every Phase 3 output uses the exact logical type in Section 10;
24. canonical source member: `canonical-content.json` has no `revision_outputs` row;
25. qualification report: no `revision_outputs` row, no bundle member, no manifest member;
26. four layers: Canonical Validation, Render Validation, Bundle Integrity, and Approval Qualification fail independently;
27. review records: set-level and shot-level reviews are supported; open blocking review blocks Approval Qualification but not Canonical Validation or Bundle Integrity;
28. supersession: approving a new Revision supersedes the old approved Revision in one transaction;
29. revocation: revoking an approval sets `revoked` and records `shot_prompt_approval_revoked`;
30. approval evidence: approval record binds qualification report evidence;
31. authoring/stored schema: Runtime does not inject undefined canonical business fields;
32. Phase 4 Eligibility: live computation fails when source freshness or bundle integrity changes after approval.

Verification commands for the later implementation must include repository tests and a Phase 3 verification tool modeled after `tools/verify_phase2_minimal_bundle_foundation.py`.

## 18. Deferred Capabilities

The following are explicitly deferred and are not Phase 3 v1 capabilities:

- `scene` scope;
- `shot_range` scope;
- partial set materialization;
- partial set approval;
- cross-Revision Review resolution;
- platform-specific prompt adapters;
- platform upload flows;
- external asset binding by `asset_id`;
- external URL, filesystem path, or upload ID persistence for generated assets;
- waiver mechanics;
- timecode-level video segmentation;
- dependency DAG visualization beyond existing revision dependency records;
- rule tiers beyond blocking validation and non-blocking lint;
- mutable qualification reports;
- putting Approval Qualification evidence into the Content Bundle.

Deferred terms may appear in validator diagnostics, boundary documentation, and future design work. They must not be implemented or treated as Phase 3 v1 user-facing capabilities.

## Self Review

- B01 fixed: v1 scope is exactly `set`; `scene`, `shot_range`, and partial set behaviors are deferred and excluded from schema, validation, lifecycle, and acceptance.
- B02 fixed: Qualification Report is outside the Content Bundle, has no `revision_outputs` row, has no manifest member, and is bound by approval evidence after human review and bundle integrity pass.
- B03 fixed: Canonical Validation, Render Validation, Bundle Integrity, and Approval Qualification are separate layers with separate responsibilities and persistence.
- B04 fixed: conceptual schemas define `shared_intent`, `image_intent`, `video_intent`, `continuity`, `negative_constraints`, `delivery`, and `set_defaults` with closed objects, empty/null rules, enums, uniqueness, merge, renderer behavior, lint, and Storyboard fact references.
- B05 fixed: bundle member and logical type mapping is frozen, including canonical virtual/source member and qualification report exclusion.
- B06 fixed: Superseded, Revoke, Review Record, approval evidence, migration checks, event types, indices, and transaction consistency are defined against the current Store facts.
- B07 fixed: stored canonical root requires `render_language`, exact `renderer.profile_id`, and exact `renderer.version`.
- B08 fixed: negative constraint and asset reference authority no longer exists at duplicate root/set/shot positions; root has no authority fields for either.
- B09 fixed: shot item identity is only `shot_id`; item-level `source_shot_id` is removed, and asset slots are one per shot/entity with multiple purposes.
- B10 fixed: `slot_id` is derived only for `asset-requirements.json`, is not author-maintained canonical, and excludes purpose from its derivation tuple.
- B11 fixed: continuity scope is limited to `set_baseline`, `previous_occurrence`, and `specific_shot`.
- B12 fixed: dialogue intent uses `source_dialogue_ref`, relative timing, and post-dialogue hold while deriving speaker facts from Storyboard dialogue.
- B13 fixed: authoring schema and stored canonical schema are one contract; Runtime may normalize and reject but not inject undefined canonical business fields.
- H01 fixed: asset entities must belong to current Shot membership; upstream canon cannot expand current-shot membership.
- H02 fixed: `utterance_mode` and `speaker_visibility` are split and lip-sync consistency rules are explicit.
- H03 fixed: Canonical locked constraints and Renderer Fact Invariants are distinct.
- H04 fixed: append_dedup rules are frozen and shared by canonical validation and rendering.
- H05 fixed: Artifact Identity is normative with `artifact_type = shot_prompt_set`, `business_key = source_storyboard_revision_id`, generated internal ID, and DB unique key.
- H06 fixed: Review Records support both `scope = set` with `shot_id IS NULL` and `scope = shot` with required `shot_id`.
- H07 fixed: `validation-report.json` is generated by the Validation Orchestrator, and render provenance excludes self, manifest, and qualification hashes.
- No code, schema, migration, skill, or test changes are authorized by this document.
- No implementation planning is authorized by this document.
- Acceptance criteria are testable.
- Final state is DESIGN_SPEC_PENDING_USER_REVIEW.
