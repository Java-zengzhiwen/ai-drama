# Storyboard Canonical + Shot Prompt Foundation Design Specification

Date: 2026-06-28

## Baseline

- Current branch: `test/storyboard-complete-verification`
- Current HEAD: `5fdc7917cac78a96ff4ae222df562d39f453f662`
- Collected tests: `92`
- Review inputs:
  - `docs/reviews/shot-prompt-workflow-codex-analysis.md`
  - `docs/reviews/shot-prompt-workflow-deepseek-analysis.md`

This specification follows the user-frozen conclusions. When the review inputs disagree, the frozen conclusion wins.

## 1. Executive Verdict

**GO WITH PREREQUISITE**

The repo is ready to begin the foundation work, but not by extending the current Markdown-first Storyboard path. The only safe sequence is:

1. Storyboard Canonical JSON
2. Deterministic Renderer
3. Minimal `revision_outputs`
4. Shot Prompt Core
5. Asset Binding
6. Execution Planning

The current runtime can support the transition, but only if the Storyboard Markdown contract is treated as legacy migration material, not as the formal downstream contract.

## 2. Repository Evidence

### 2.1 Current runtime shape

- `README.md:3-23` says the runtime currently supports only `markdown-script-mvp-v1` and `storyboard-markdown-mvp-v1`, and explicitly does not claim Shot Prompt, LibTV, or Agnes support.
- `ai_drama_runtime/cli.py:66-109` routes `run create` only by `--input` versus `--source-revision`, which is sufficient for the current two workflow shapes but not for a future canonical bundle workflow.
- `ai_drama_runtime/services.py:103-214` and `ai_drama_runtime/services.py:216-371` show the current workflow entrypoints: script acceptance and storyboard generation from an approved script revision.

### 2.2 Current persistence model

- `ai_drama_runtime/store.py:171-307` creates the current tables: `artifacts`, `runs`, `input_snapshots`, `revisions`, `validation_results`, `approval_records`, `export_records`, `revision_dependencies`, and `workflow_gate_records`.
- Inference from `ai_drama_runtime/store.py:171-307` and `ai_drama_runtime/store.py:495-535`: there is no `revision_outputs` table yet; each revision still has a single `content_object_id`.
- `ai_drama_runtime/services.py:417-535` shows freshness, approval, compare, and export are currently layered on top of the single-revision model.

### 2.3 Current request / parser / runtime / validator behavior

- `ai_drama_runtime/request.py:133-167` builds storyboard runtime requests as Markdown-first payloads with source script markdown and approval record inputs, not as canonical JSON bundles.
- `ai_drama_runtime/parser.py:35-56` accepts storyboard Markdown by checking scene and shot markers; it does not define a canonical JSON contract.
- `ai_drama_runtime/runtime.py:1-193` still produces Markdown responses from mock runtime profiles and OpenAI-compatible chat completions.
- `ai_drama_runtime/validators.py:69-191` persists validator outputs and explicitly records `PASS`, `FAIL`, `NOT_APPLICABLE`, and `SKIPPED_DEPENDENCY_MISSING`.

### 2.4 Current Storyboard package shape

- `skills/ai-drama-storyboard-design-skill/v0.1.0/skill.json:1-196` defines the formal Storyboard package, its validators, and its current `storyboard_markdown` output shape.
- `skills/ai-drama-storyboard-design-skill/v0.1.0/SKILL.md` says the package is for storyboard design only and must not emit shot prompts, LibTV packages, or execution commands.
- `docs/storyboard/storyboard-workflow-mvp.md:1-47` and `docs/storyboard/storyboard-validator-matrix.md:1-15` describe the existing markdown-first Storyboard workflow and validator expectations.

### 2.5 Current tests

- `tests/test_storyboard_workflow.py:45-137` covers storyboard package discovery, validator execution, source coverage, freshness, approval, and export.
- `tests/test_validators_approval_export.py:65-172` covers `NOT_APPLICABLE`, required validator blocking, and provenance/export behavior.
- `tests/acceptance/test_storyboard_workflow_acceptance.py:21-83` covers the verification report contract, `tested_commit_sha`, `tested_worktree_clean`, and the recursive self-test guard.

## 3. Critical Findings

### BLOCKER

1. **Storyboard Markdown is not a valid final authority for Shot Prompt.**
   The current parser and request builder are Markdown-first (`ai_drama_runtime/parser.py:35-56`, `ai_drama_runtime/request.py:133-167`). Shot Prompt requires JSON as the unique authority, so Markdown can only survive as a legacy migration view.

2. **`revision_outputs` is missing.**
   The current store model only persists a single `content_object_id` per revision (`ai_drama_runtime/store.py:220-239`, `ai_drama_runtime/store.py:495-516`). That cannot represent canonical JSON, rendered Markdown, negative prompts, or any other bundle member independently.

3. **Approval and readiness are currently coupled.**
   `ai_drama_runtime/services.py:373-390` treats required validator pass/fail as part of approval, and `ai_drama_runtime/services.py:483-535` re-checks freshness at export time. Shot Prompt needs separate content approval and execution readiness so binding and target concerns do not contaminate creative approval.

### HIGH

1. **The current `run create` dispatcher is too coarse for the next phase.**
   `ai_drama_runtime/cli.py:66-109` is only branching by `--input` and `--source-revision`. The next phase needs explicit artifact and capability routing, not one more boolean split.

2. **Renderer boundaries do not exist yet.**
   There is no dedicated renderer layer that takes canonical JSON and deterministically emits Markdown or prompt text. Without that boundary, byte-level reproducibility is not enforceable.

3. **Asset binding cannot be externally trusted without a registry.**
   The repo has no Visual Asset Registry. A `bound` label can be a deterministic local state, but it cannot be treated as a globally trusted verification result.

### MEDIUM

1. **`execution_targets` should not live inside canonical JSON.**
   They belong in execution planning / adapter metadata, not in the canonical prompt source.

2. **Asset binding changes must produce a new revision.**
   A deterministic `bind-assets` command is fine, but it must create a derived revision when the binding set changes.

3. **Legacy Storyboard Markdown needs a read-only migration path.**
   The old markdown revisions must remain immutable and must not be silently rewritten into canonical JSON.

### LOW

1. **Genericity scanning is currently package-level, not bundle-level.**
   `ai_drama_runtime/validators.py:69-191` and the current storyboard package only validate the package shape. The future Shot Prompt package will need an explicit bundle-aware genericity validator.

## 4. Three Architecture Options

| Option | Modification range | Technical debt | Testing cost | Data reliability | Pipeline adaptation | Rollback difficulty |
|---|---|---|---|---|---|---|
| A. Directly build Shot Prompt from Storyboard Markdown | Smallest | Highest | Short-term low, long-term high | Weak | Poor | Medium |
| B. Upgrade Storyboard to Canonical JSON first | Moderate | Lowest | Moderate | Strong | Best | Low to medium |
| C. Temporary normalization inside Shot Prompt | Looks small, actually broad | High | Low initially, high later | Medium to low | Fair | High |

**Recommendation: B.**

Reason: the repo already proves the current markdown-first Storyboard flow works, but the next layer needs canonical authority, deterministic rendering, and explicit revision-member storage. B is the only path that avoids redoing the model twice.

## 5. Recommended Architecture

### 5.1 Artifact model

- `Storyboard Canonical Revision` becomes the formal source artifact for downstream prompt generation.
- `Shot Prompt Package Revision` becomes the new downstream artifact class.
- `rendered_markdown`, `rendered_prompt`, and `negative_prompt` are derived outputs, not authority.
- `execution_targets` are not part of canonical JSON; they live in execution planning records.

### 5.2 Revision model

- A revision is immutable once written.
- Any change to canonical content creates a new revision.
- Any change to asset bindings also creates a new derived revision.
- `bind-assets` is deterministic and does not re-call the model.
- If a `bind-assets` invocation is a true no-op, it can return the current revision without creating a new one; otherwise it must mint a derived revision.
- The derived revision still needs its own validation pass and approval record before export or execution.

### 5.3 Hash contract

#### Canonical JSON hash

- Definition: SHA-256 of the deterministic canonical serialization of the canonical JSON payload.
- Scope: only canonical fields.
- Exclusions: rendered Markdown, negative prompt, execution targets, timestamps, random IDs, runtime metadata, approval status, freshness status.

#### Bundle hash

- Definition: SHA-256 over the ordered list of revision output members.
- Stable input tuple for each member: `output_kind`, `member_key`, `content_hash`, `renderer_name`, `renderer_version`, `is_canonical_source`.
- Ordering rule: sort by `output_kind`, then `member_key`, then `renderer_version`.

#### Approval hash

- Definition: SHA-256 of the canonical serialization of the approval record.
- Stable fields: `record_id`, `revision_id`, `artifact_id`, `action`, `reviewer`, normalized `note`, `created_at`.
- Exclusions: SQLite sequence numbers, rowids, and other storage-specific identifiers.

### 5.4 Minimal `revision_outputs`

Use a minimal append-only table, not a generic polymorphic graph.

Recommended columns:

| column | purpose |
|---|---|
| `revision_output_id` | primary key |
| `revision_id` | owning revision |
| `output_kind` | `canonical_json`, `rendered_markdown`, `rendered_prompt`, `negative_prompt`, `approval_manifest`, `execution_plan` |
| `member_key` | stable bundle member name |
| `output_order` | stable export order |
| `content_object_id` | immutable object-store reference |
| `content_hash` | member hash |
| `renderer_name` | output producer |
| `renderer_version` | fixed renderer version |
| `is_canonical_source` | canonical authority flag |
| `created_at` | audit time |

Compatibility strategy:

- Keep `revisions.content_object_id` as a legacy rendered-Markdown mirror until migration is complete.
- Backfill only what can be deterministically proven.
- Do not auto-fabricate canonical JSON from legacy Markdown without an explicit migration command and a new revision.

### 5.5 Canonical JSON boundary

- Canonical JSON describes what is being generated, not how a platform will execute it.
- Allowed canonical data: source provenance, unit identity, source scene / shot mapping, split metadata, timing, `prompt_components`, `negative_constraints`, `reference_requirements`, and asset binding declarations.
- Disallowed canonical data: `rendered_prompt`, `rendered_negative_prompt`, `rendered_markdown`, `execution_targets`, runtime status, approval status, freshness status, `created_at`, run duration, random run ID, and `generation_strategy.mode`.
- `generation_strategy` and `frame_requirements` belong in execution planning records, not in canonical JSON.

### 5.6 Renderer boundary

- Renderer lives in Runtime, not in the Skill Package.
- Skill Package defines schema and constraints; Runtime defines byte-for-byte rendering.
- Renderer must be pure: no wall clock, no random seed drift, no environment-dependent formatting, no network calls.
- Markdown and negative prompt bytes are derived solely from canonical JSON plus a pinned renderer version.

### 5.7 Freshness model

- Freshness is dynamic and dependency-driven.
- A revision becomes stale when its source canonical revision is no longer the current approved source revision.
- Freshness is orthogonal to content approval and execution readiness.
- Legacy Markdown revisions remain read-only and can be compared or exported, but new workflow steps must consume canonical revisions.

### 5.8 Approval / readiness model

- `content_approved` means the canonical payload is semantically valid and reviewer-approved.
- `execution_ready` means the canonical payload, renderer outputs, asset binding declarations, and target-specific prerequisites all pass.
- The two states must be stored separately.
- A revision can be content-approved but execution-blocked.
- A revision can never be execution-ready if its content is not approved.

### 5.9 Asset binding model

- Allowed binding states: `pending`, `partially_bound`, `bound`.
- `pending` means required references are not yet resolved.
- `partially_bound` means some references are resolved but the binding set is incomplete.
- `bound` means the local deterministic binding declarations are complete and internally consistent.
- Without a Visual Asset Registry, `bound` is a local assertion only; it is not a globally trusted proof.
- Binding changes must create a new revision.
- `bind-assets` may only change binding-related paths and must not mutate canonical creative content.

### 5.10 Execution target model

- `execution_targets` are part of execution planning, not canonical JSON.
- The first adapter set may include `libtv` and `agnes`, but they should be adapters, not canonical fields.
- The core model stays target-neutral; targets are selected after content approval.

### 5.11 Shot Prompt / Visual Anchor / Image Prompt boundary

- Visual Anchor and Image Prompt are reference-generation layers.
- Shot Prompt consumes their outputs as references or binding inputs.
- Shot Prompt does not own visual anchor generation or still-image prompt generation.
- If a reference asset changes, a new binding-derived Shot Prompt revision is required.

### 5.12 Atomic bundle export

- Bundle export must be all-or-nothing.
- Stage all bundle members into a temp directory on the same filesystem.
- Verify hashes before the final move.
- Commit the final bundle by atomic rename only after every member and manifest entry is present.
- If any step fails, leave no partially exported final bundle behind.

## 6. Proposed Schema Skeleton

```json
{
  "schema_version": "shot-prompt-package-v1",
  "artifact_type": "shot_prompt_package",
  "package_identity": {
    "package_id": "",
    "revision_id": "",
    "revision_kind": "initial|derived_bind_assets|derived_render_only",
    "parent_revision_id": ""
  },
  "source_provenance": {
    "storyboard_revision_id": "",
    "storyboard_revision_hash": "",
    "storyboard_approval_record_id": "",
    "upstream_script_revision_id": "",
    "upstream_script_revision_hash": "",
    "upstream_script_approval_record_id": ""
  },
  "units": [
    {
      "unit_id": "",
      "unit_order": 1,
      "source_scene_id": "",
      "source_shot_id": "",
      "split_metadata": {
        "is_split": false,
        "split_group_id": "",
        "parent_unit_id": "",
        "split_index": 1,
        "split_count": 1
      },
      "timing": {
        "source_duration_seconds": 0,
        "target_duration_seconds": 0,
        "allowed_drift_seconds": 2
      },
      "prompt_components": {
        "subject": "",
        "action": "",
        "camera": "",
        "composition": "",
        "lighting": "",
        "tone": "",
        "continuity": ""
      },
      "negative_constraints": [
        {
          "constraint_id": "",
          "text": ""
        }
      ],
      "reference_requirements": [
        {
          "reference_id": "",
          "reference_type": "visual_anchor|image_prompt|asset",
          "binding_state": "pending|partially_bound|bound",
          "required": true
        }
      ],
      "asset_bindings": [
        {
          "binding_id": "",
          "asset_identifier": "",
          "asset_role": "",
          "binding_state": "pending|partially_bound|bound",
          "asset_revision_id": "",
          "asset_content_hash": "",
          "binding_proof_hash": ""
        }
      ]
    }
  ]
}
```

Notably absent from the canonical skeleton:

- `rendered_prompt`
- `rendered_negative_prompt`
- `rendered_markdown`
- `execution_targets`
- `generation_strategy`
- `frame_requirements`
- runtime status
- approval status
- freshness status
- `created_at`
- run duration
- random run ID

Execution planning metadata such as `generation_strategy`, `frame_requirements`, and `execution_targets` should be stored in `execution_plan` or adjacent `revision_outputs` members, not inside the canonical authority object.

## 7. Proposed CLI

The current `run create` dispatcher should remain only as a compatibility shim for the existing script and storyboard flows. The new foundation should use explicit namespaces.

### Suggested commands

```bash
ai-drama storyboard canonical migrate --from legacy-markdown --input path/to/storyboard.md --output path/to/revision.json
ai-drama storyboard canonical render --revision REVISION_ID --format markdown --output path/to/storyboard.md
ai-drama shot-prompt create --source-storyboard REVISION_ID
ai-drama shot-prompt bind-assets REVISION_ID --bindings path/to/bindings.json
ai-drama shot-prompt approve-content REVISION_ID
ai-drama shot-prompt readiness REVISION_ID
ai-drama shot-prompt export REVISION_ID --target libtv --output path/to/export/
```

### Stable error codes

| code | meaning |
|---|---|
| `2` | input error or workflow gate failure |
| `3` | object or revision not found |
| `4` | runtime, parser, or renderer failure |
| `5` | validation failure |
| `6` | approval blocked |
| `7` | atomic export failure |
| `8` | readiness blocked |

## 8. Validator Matrix

| validator | required | input | responsibility | failure condition |
|---|---:|---|---|---|
| `storyboard_canonical_schema` | yes | canonical storyboard JSON | validate schema, provenance, and immutability fields | schema mismatch or missing provenance |
| `storyboard_markdown_renderer_parity` | yes for migration/export | canonical storyboard JSON + renderer | ensure Markdown bytes exactly match deterministic renderer | byte mismatch or hash mismatch |
| `shot_prompt_unit_mapping` | yes | canonical storyboard + prompt units | enforce 1:1 default, allow 1:N split, forbid many-shot merge into one unit | merge detected, orphan unit, or duplicate source mapping |
| `shot_prompt_duration_window` | yes | source duration and unit durations | enforce total duration and controlled ±2s drift | duration missing or drift beyond policy |
| `shot_prompt_prompt_components` | yes | prompt components | validate required creative fields and forbid downstream execution leakage | missing required component or forbidden term |
| `shot_prompt_reference_requirements` | yes | reference requirements | validate declared reference dependencies and their roles | missing or malformed references |
| `shot_prompt_asset_binding` | yes | asset bindings | validate pending / partially_bound / bound transitions and path/hash constraints | illegal state transition or untrusted binding |
| `shot_prompt_content_freshness` | yes | source provenance | reject stale source lineage | source revision is no longer current approved |
| `shot_prompt_execution_readiness` | yes | readiness record | require content approval, renderer parity, target prerequisites, and binding completeness | any prerequisite missing or failing |
| `shot_prompt_genericity` | yes | package text | block forbidden downstream terms in the bundle/package surface | forbidden term found |

## 9. Database Migration

### New tables

1. `revision_outputs`
2. `revision_binding_records`
3. `revision_readiness_records`
4. `execution_target_records` if execution planning needs durable target history before adapters land

### Recommended indexes

- `revision_outputs(revision_id, output_kind, member_key)`
- `revision_outputs(content_hash)`
- `revision_binding_records(revision_id, binding_state)`
- `revision_readiness_records(revision_id, target_id, readiness_state)`

### Compatibility strategy

- Keep `revisions`, `approval_records`, `revision_dependencies`, and `workflow_gate_records` intact.
- Treat legacy Storyboard Markdown as immutable historical content.
- Backfill `rendered_markdown` first; only create canonical JSON during an explicit migration command that can prove fidelity.
- Do not overwrite legacy revision content in place.
- Keep read-only compare/export support for old markdown revisions while new canonical revisions are introduced.

### Rollback risk

- Low if the migration is additive and legacy markdown remains intact.
- Medium if canonical JSON backfill is attempted for all historical revisions automatically.
- High if approval and readiness are collapsed into one new table during migration.

## 10. Acceptance Test Matrix

| case | expected result |
|---|---|
| Normal canonical generation | canonical JSON, renderer output, and hashes match exactly |
| Unapproved Storyboard | gate failure before Shot Prompt creation |
| Stale Storyboard | content approval and export blocked |
| Missing scene coverage | coverage validator fails |
| Illegal merge of multiple storyboard shots into one unit | unit-mapping validator fails |
| Split order mismatch | unit order validator fails |
| Duration drift beyond ±2s | duration validator fails |
| Renderer inconsistency | renderer parity validator fails |
| `pending` binding state | execution readiness blocked |
| `partially_bound` binding state | execution readiness blocked until policy is satisfied |
| `bound` without registry proof | locally allowed state, but not globally trusted |
| `bind-assets` no-op | returns no new revision or an explicit no-op result, with no content mutation |
| `bind-assets` illegal path change | binding validator fails |
| Bundle export failure mid-write | staging directory is cleaned and no partial final bundle remains |
| Upstream reapproval of source storyboard | dependent Shot Prompt revision becomes stale |

## 11. Recommended Delivery Phases

### Phase 0: Contract freeze

- Goal: freeze canonical fields, hash rules, revision output semantics, and validator responsibilities.
- File scope: `docs/superpowers/specs/`, `docs/reviews/`, `docs/storyboard/`.
- Exit condition: the schema, hash contract, and phase boundaries no longer conflict.

### Phase 1: Storyboard Canonical JSON

- Goal: migrate the Storyboard authority from Markdown to canonical JSON.
- File scope: `ai_drama_runtime/parser.py`, `ai_drama_runtime/request.py`, `ai_drama_runtime/services.py`, `skills/ai-drama-storyboard-design-skill/v0.1.0/`, `tests/test_storyboard_workflow.py`.
- Exit condition: canonical storyboard revisions can be created, rendered, compared, and migrated without changing legacy markdown history.

### Phase 2: Deterministic Renderer

- Goal: render Markdown and other derived text strictly from canonical JSON.
- File scope: renderer runtime code, tests, and export paths.
- Exit condition: byte-for-byte renderer determinism is covered by exact-output tests.

### Phase 3: Minimal `revision_outputs`

- Goal: store every bundle member independently.
- File scope: `ai_drama_runtime/store.py`, `ai_drama_runtime/services.py`, export helpers, tests.
- Exit condition: canonical JSON, rendered Markdown, and any additional bundle member are individually addressable.

### Phase 4: Shot Prompt Core

- Goal: introduce the first Shot Prompt package revision type on top of canonical Storyboard inputs.
- File scope: new Shot Prompt skill package, request builders, validators, and CLI namespace.
- Exit condition: a Shot Prompt revision can be created, validated, approved, and exported from canonical Storyboard input.

### Phase 5: Asset Binding

- Goal: add deterministic `bind-assets` derivations and binding-state validation.
- File scope: asset binding tables, revision derivation logic, readiness checks, and tests.
- Exit condition: asset changes create new revisions and cannot mutate canonical creative content in place.

### Phase 6: Execution Planning

- Goal: separate execution planning from content approval and adapter-specific payloads.
- File scope: execution planning records, target adapters, and export orchestration.
- Exit condition: execution targets can be planned without contaminating canonical JSON.

## 12. Open Questions

Only questions that are not decidable from the repository are left open:

1. Which JSON canonicalizer implementation should be standardized for byte-level parity in phase 1?
2. Should the first execution planning slice support only `libtv` and `agnes`, or keep a more general target registry from day one?
3. What exact `prompt_components` sub-taxonomy should the first Shot Prompt family standardize beyond the minimal skeleton?
