# Phase 1 Storyboard Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The main agent is the sole code writer. All subagents are read-only.

**Goal:** Convert Storyboard from Markdown-first runtime behavior to canonical-JSON-first runtime behavior without adding Phase 2 bundle persistence, Shot Prompt, asset binding, or execution readiness.

**Execution model:** `executing-plans`; the main agent writes code, tests, docs, and verification artifacts. Subagents are read-only and only provide analysis.

**Architecture:** `v0.1.0` remains `storyboard-markdown-mvp-v1` and is read-only. Add `v0.2.0` as `storyboard-canonical-v1`. Canonical model responses are direct Canonical JSON. Markdown parsing is legacy migration only.

**Tech Stack:** Existing Python runtime, SQLite store, pytest, CLI entrypoints, deterministic JSON canonicalization, and local file fixtures/goldens.

---

## Summary
- Keep `run create` as the main entrypoint shape, but make storyboard creation profile-aware and canonical-JSON-first.
- Add canonical schema/serialization/hash/rendering/migration logic in runtime code, with additive DB support only.
- Keep legacy Markdown storyboard revisions readable and migratable, but never mutate them in place.
- Keep Phase 2+ surfaces out of scope: no bundle persistence, Shot Prompt, asset binding, execution planning, LibTV, Agnes, or `execution_readiness = ready`.

## Key Changes
- **Store / schema:** add additive revision metadata needed for canonical storyboard revisions, especially `content_profile` and `derivation_type`; keep `revisions` as the one logical artifact lineage table and keep current-approved uniqueness unchanged.
- **Canonical runtime modules:** add canonical Storyboard JSON schema validation, canonical serialization, canonical hash computation, and canonical revision construction from approved script source.
- **Renderer module:** add deterministic canonical JSON -> Markdown rendering with fixed output rules and byte-stable parity checks.
- **Legacy migration flow:** add explicit `storyboard migrate-legacy` flow that previews a canonical candidate, verifies the candidate hash, and creates a pending canonical revision only after explicit confirmation; never auto-approve or auto-promote.
- **CLI and verifier:** extend CLI for canonical render/migrate flows and add a unified Phase 1 verifier entrypoint that exercises the whole canonical path plus regression checks.
- **Validators:** keep legacy Markdown validators unchanged, add canonical validators for canonical JSON, and route runtime-native source coverage / freshness / renderer parity by `artifact_type + content_profile`.

## File-by-file Change Plan
- `ai_drama_runtime/store.py`
  - Add additive revision metadata for canonical storyboard revisions.
  - Add idempotent migration/backfill support for `revisions.content_profile` and `revisions.derivation_type`.
  - Preserve current-approved uniqueness and legacy revision history.
  - Update `RevisionRecord` read/write paths to carry the new fields.
- `ai_drama_runtime/services.py`
  - Split storyboard creation into canonical revision creation, deterministic rendering, validation, migration, approval, and export.
  - Keep approval separate from freshness.
  - Ensure stale canonical revisions cannot be approved or exported.
  - Implement profile-aware compare/export behavior and recursive freshness traversal.
- `ai_drama_runtime/request.py`
  - Route runtime requests by execution profile metadata.
  - Preserve markdown request shape for legacy `v0.1.0`.
  - Emit canonical JSON request/response shape for `v0.2.0`.
- `ai_drama_runtime/parser.py`
  - Parse canonical JSON for `v0.2.0`.
  - Keep Markdown parsing only for legacy migration preview/confirm.
- `ai_drama_runtime/runtime.py`
  - Add canonical Mock Runtime responses for `v0.2.0`.
  - Add negative modes for invalid JSON, duplicate key, invalid schema, and missing source coverage.
  - Preserve legacy markdown mock behavior for `v0.1.0`.
- `ai_drama_runtime/validators.py`
  - Add profile-aware routing keyed by `artifact_type + content_profile`.
  - Keep legacy Markdown validators unchanged.
  - Route source coverage, recursive freshness, and renderer parity through Runtime-native store-aware validators.
- `ai_drama_runtime/cli.py`
  - Keep existing CLI shape.
  - Freeze exact `storyboard render` and `storyboard migrate-legacy` command contracts and outputs.
- `ai_drama_runtime/manifest.py`
  - Validate canonical profile metadata: `profile_id`, `output_format`, `parser_version`, `required_schema_version`, `renderer_id`, `renderer_version`.
  - Change only if renderer/profile metadata validation requires it.
- `ai_drama_runtime/storyboard_canonical.py`
  - Canonical Storyboard schema, serialization, hash helper, and canonical validation helpers.
- `ai_drama_runtime/storyboard_renderer.py`
  - Deterministic renderer from canonical JSON to Markdown.
- `ai_drama_runtime/storyboard_migration.py`
  - Two-step legacy Markdown -> canonical candidate -> confirm -> pending canonical revision flow.
- `tools/verify_phase1_storyboard_canonicalization.py`
  - New unified Phase 1 verifier with preflight, portable, and final modes.
- `tools/verify_storyboard_workflow.py`
  - Keep as regression-oriented verifier unless reused for shared checks.
- `docs/superpowers/reports/2026-06-29-phase-1-storyboard-canonicalization-verification.md`
  - Required final verification report artifact.
- `skills/ai-drama-storyboard-design-skill/v0.2.0/**`
  - Canonical Skill package tree, including `SKILL.md`, `skill.json`, canonical schemas, contracts, validator entrypoints, support files, and any other package-local files required by `skill.json`.
- `tests/test_storyboard_workflow.py`
  - Preserve markdown regression coverage while canonical path lands.
- `tests/test_validators_approval_export.py`
  - Preserve approval/export regression coverage.
- `tests/test_cli.py`
  - Add canonical create/render/migrate/compare coverage.
- `tests/test_storyboard_canonical_schema.py`
- `tests/test_storyboard_canonical_serialization.py`
- `tests/test_storyboard_canonical_hash.py`
- `tests/test_storyboard_renderer.py`
- `tests/test_storyboard_legacy_migration.py`
- `tests/test_storyboard_canonical_validators.py`
- `tests/fixtures/storyboard_canonical/**`
- `tests/golden/storyboard_renderer/**`

## Database Migration Strategy
- Add `revisions.content_profile` and `revisions.derivation_type`.
- Backfill rules:
  - existing Script revisions -> `markdown-script-mvp-v1`, `model_generation`
  - existing Storyboard revisions -> `storyboard-markdown-mvp-v1`, `model_generation`
  - canonical Storyboard revisions -> `storyboard-canonical-v1`, `model_generation` or `legacy_migration` as appropriate
- Migration must be idempotent.
- `RevisionRecord` read/write paths must understand the new fields.
- Add upgrade tests against a pre-Phase-1 database snapshot.

## Skill Version Strategy
- `v0.1.0` remains the markdown storyboard skill/package/profile and is read-only.
- `v0.2.0` introduces the canonical storyboard skill/package/profile.
- Canonical responses are direct Canonical JSON.
- Markdown parsing is used only for legacy migration preview/confirm.

## Profile-aware Behavior
- Legacy markdown validators remain unchanged.
- Canonical validators operate on canonical JSON.
- Source coverage reads the actual parent Script Revision.
- Freshness walks the dependency graph recursively.
- Renderer parity uses renderer ID/version in the check.
- Compare/export are profile-aware:
  - canonical export renders Markdown without `revision_outputs`
  - legacy/canonical comparison uses rendered Markdown where needed
  - provenance includes `content_profile`, canonical hash, renderer ID/version

## Validator Architecture
- Pure canonical content validators remain Skill-declared subprocess validators.
- Source coverage, recursive freshness, and renderer parity are Runtime-native store-aware validators.
- Routing key is `artifact_type + content_profile`.
- Legacy Markdown validators remain unchanged and only apply to the legacy profile.

## Verifier Modes
- `preflight`: exact branch, exact launch HEAD, clean tree, baseline ancestor, baseline 92.
- `portable`: pytest-only suite for canonical unit/integration coverage; no git-state assertions.
- `final`: exact branch/clean-tree recheck plus HEAD descendant-of-the Execution Start Commit, `git diff --check`, full suite, final gate.
- Exact branch, launch HEAD, and clean-tree assertions live only in `preflight` and `final`.

## CLI Contract
- `ai-drama storyboard render --revision REVISION_ID --output OUTPUT_PATH`
  - emits JSON with `status=RENDERED`, `revision_id`, `content_profile`, `canonical_hash`, `renderer_id`, `renderer_version`, `output_path`
  - renders Markdown only; no revision creation
- `ai-drama storyboard migrate-legacy --source-revision REVISION_ID --preview --output OUTPUT_PATH`
  - emits JSON with `status=PREVIEW`, `candidate_hash`, `canonical_candidate_path`, `rendered_markdown_path`, no Revision created
- `ai-drama storyboard migrate-legacy --source-revision REVISION_ID --confirm-candidate-hash HASH --output OUTPUT_PATH`
  - emits JSON with `status=PENDING_CANONICAL_REVISION`, `revision_id`, `candidate_hash`, `content_profile=storyboard-canonical-v1`, `approval_status=pending`
  - never auto-approves or auto-promotes

## Error-Code Compatibility
- Canonical profile paths emit frozen canonical symbolic codes.
- Legacy Markdown paths keep legacy codes unchanged.
- Compatibility mapping for surfaced failures:
  - `ERR_STRUCTURE` -> `CANONICAL_SCHEMA_INVALID` or `SHOT_MAPPING_INVALID` by failure class
  - `ERR_DURATION` -> `STORYBOARD_DURATION_INVALID`
  - `ERR_SOURCE_COVERAGE` -> `SHOT_COVERAGE_INCOMPLETE`
  - `ERR_CONTINUITY` -> `SHOT_MAPPING_INVALID`
- `SOURCE_REVISION_NOT_FOUND`, `SOURCE_ARTIFACT_TYPE_INVALID`, `SOURCE_STALE`, and `DEPENDENCY_CYCLE_DETECTED` stay stable.
- Canonical codes are preferred in verifier output; legacy codes remain for `v0.1.0` migration and regression paths.

## Legacy Migration
- Step 1: preview candidate + candidate hash, no Revision created.
- Step 2: explicit candidate-hash confirmation creates a pending Canonical Revision.
- Never auto-approve or auto-promote.
- Fail closed with `LEGACY_MIGRATION_REQUIRES_REVIEW` when fidelity is not proven.

## Test Plan
- Start with failing tests for serialization and schema.
- Add hash stability tests next.
- Add deterministic renderer golden tests next.
- Add canonical revision creation and freshness tests next.
- Add legacy migration fail-closed tests next.
- Add CLI canonical command tests next.
- Add unified verifier assertions last.
- Baseline existing tests = `92`.
- All original tests must keep passing.
- Final total = `92 + new Phase 1 tests`.
- TDD is still failing-test -> minimal implementation, but only green vertical-slice commits may be pushed.
- Local red tests are allowed during development; no known-failing commit may be pushed.

## Acceptance Matrix Mapping
| IDs | Implementation location | Test location | Verification evidence | Dependency |
|---|---|---|---|---|
| P1-001..005 | launch preflight + verifier | `tools/verify_phase1_storyboard_canonicalization.py`, final gate | branch, exact launch HEAD, ancestor, clean tree, baseline `92` | none |
| P1-010..018 | canonical schema/serialization | `tests/test_storyboard_canonical_schema.py`, `tests/test_storyboard_canonical_serialization.py` | valid canonical JSON accepted; missing/null/duplicate-key/NaN/order cases rejected | P1-001..005 |
| P1-020..027 | identity/order validation | `tests/test_storyboard_canonical_validators.py` | `scene_id`/`shot_id` regex, duplicate IDs, strict order, action order | P1-010..018 |
| P1-030..034 | duration validation | `tests/test_storyboard_canonical_validators.py` | integer 5-15 second duration enforcement | P1-020..027 |
| P1-040..047 | source coverage + freshness + migration | `tests/test_storyboard_legacy_migration.py`, `tests/test_storyboard_canonical_validators.py` | approved fresh source required; stale/missing source fails closed; coverage enforced | P1-030..034 |
| P1-050..055 | canonical hashing | `tests/test_storyboard_canonical_hash.py` | same canonical bytes/hash across equivalent inputs; metadata/path ignored | P1-040..047 |
| P1-060..067 | deterministic renderer + parity | `tests/test_storyboard_renderer.py` | byte-identical render, LF, one trailing newline, no env/locale/path dependency | P1-050..055 |
| P1-070..077 | canonical revision storage + export | `tests/test_storyboard_workflow.py`, new canonical revision test file | canonical revision authoritative; dependency to approved Script; no auto-approval | P1-060..067 |
| P1-080..087 | legacy migration confirm flow | `tests/test_storyboard_legacy_migration.py` | preview/candidate-hash confirm, legacy bytes unchanged, no auto-approval/current-approved | P1-070..077 |
| P1-090..095 | CLI integration | `tests/test_cli.py` | canonical create/render/migrate commands, symbolic errors preserved, no regression | P1-080..087 |
| P1-100..105 | unified verifier + final gate | `tools/verify_phase1_storyboard_canonicalization.py`, final report | unified PASS script, `git diff --check`, clean tree, full pytest, no Phase 2 drift | P1-090..095 |

## Unified Verification Script Design
- Add `python3 tools/verify_phase1_storyboard_canonicalization.py`.
- Modes:
  - `preflight`: branch, exact launch HEAD, ancestry, clean tree, baseline 92
  - `portable`: pytest-only suite for canonical and regression coverage
  - `final`: branch/HEAD/clean-tree recheck, `git diff --check`, full suite, final gate
- It must be repeatable, offline, temp-dir based, and non-mutating to production data.
- It must verify:
  - canonical schema tests
  - canonical serialization tests
  - canonical hash tests
  - renderer determinism and parity
  - canonical revision creation and freshness
  - legacy migration fail-closed
  - CLI canonical command coverage
  - regression suite still passes
- It must print `PHASE1_STORYBOARD_CANONICALIZATION: PASS` only when all checks pass.

## Rollback Strategy
- All schema changes must be additive.
- No legacy revision content is rewritten.
- If canonicalization fails, keep Markdown-first behavior intact behind existing paths until the new tests and verifier pass.
- Do not introduce bundle persistence or execution readiness as a fallback.

## Proposed Commit Sequence
- Green vertical-slice commits only.
- Each pushed commit must be green.
- No commit with known-failing tests may be pushed.
- Suggested slices:
  1. canonical schema + serialization tests
  2. canonical runtime/model + renderer
  3. migration + recursive freshness + validator routing
  4. CLI + verifier + regression updates

## Assumptions
- No `revision_outputs` table in Phase 1.
- No Phase 2 bundle/export/readiness surfaces.
- Canonical skill/package versioning is additive, not destructive.
- `manifest.py` changes only if renderer/profile metadata validation actually needs it.
- Agent E and Agent F remain deferred until implementation is complete.
- Phase 2+ vocabulary in docs/skill metadata is treated as drift risk, not scope to implement.
