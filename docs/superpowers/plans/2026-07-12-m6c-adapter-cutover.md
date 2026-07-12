# M6C Adapter Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route OpenAI-compatible text and Agnes image/video work through immutable supplier snapshots while preserving legacy behavior and denying real network in default tests.

**Architecture:** Provider-neutral services resolve and persist request plus snapshot before invoking a snapshot-bound worker adapter. The poller reloads the frozen artifact/config/model/credential for each job; feature flags retain an immediate legacy rollback.

**Tech Stack:** Python/FastAPI/SQLite, isolated Node worker from M6A, pytest HTTP mocks.

## Global Constraints

- M6A and M6B interfaces are fixed dependencies.
- Implement SUP-016..SUP-021, SUP-025..SUP-028.
- No management UI or real provider request.
- Before stage handoff, at least two read-only review agents must independently return PASS: specification compliance, and technical/security with emphasis on snapshot routing, poller restart safety, legacy compatibility, rerun credentials, redaction, and rollback. The main agent resolves and re-verifies all blockers.

---

### Task 1: Provider-Neutral Supplier Runtime Adapter

**Files:**
- Create: `ai_drama_web/suppliers/runtime.py`
- Create: `ai_drama_web/suppliers/requests.py`
- Test: `tests/suppliers/test_supplier_runtime.py`

**Interfaces:**
- Produces: `SupplierRuntime.text_request`, `image_request`, `video_submit`, `video_poll`, `video_fetch`, each accepting `ResolvedExecutionSnapshot` and provider-neutral request.

- [ ] Write red fake-adapter tests for sanitized success/failure, helper-only network, strict output contracts, runtime-unavailable, and credential lookup by snapshot.
- [ ] Run focused tests; expect missing runtime.
- [ ] Implement snapshot artifact loading, helper dispatch, response validation/redaction, and stable error mapping.
- [ ] Run focused tests with a loopback-only fake provider server and assert external network rejection.
- [ ] Commit `feat: add snapshot bound supplier runtime`.

### Task 2: OpenAI-Compatible Text Cutover

**Files:**
- Modify: `ai_drama_runtime/runtime.py`
- Modify: `ai_drama_runtime/services.py`
- Test: `tests/test_supplier_text_runtime.py`

**Interfaces:**
- Consumes: M6B resolver/snapshot builder and Task 1 runtime.
- Produces: feature-flagged supplier execution for text runs with `resolved_snapshot_object_id`.

- [ ] Write red tests for snapshot-before-call, built-in OpenAI/DeepSeek/Anthropic/xAI contracts, existing run continuity, and feature-flag rollback.
- [ ] Run focused tests; confirm legacy path remains green and new flag fails.
- [ ] Implement adapter selection and snapshot persistence without deleting legacy configuration.
- [ ] Run focused tests and script/storyboard regressions.
- [ ] Commit `feat: route text runs through supplier snapshots`.

### Task 3: Durable Image Cutover

**Files:**
- Modify: `ai_drama_web/services/asset_generation.py`
- Modify: `ai_drama_web/services/generation_jobs.py`
- Modify: `ai_drama_web/routers/assets.py`
- Test: `tests/web/test_supplier_image_generation.py`

**Interfaces:**
- Produces durable image jobs with request/snapshot persisted transactionally before worker invocation and generated assets pointing to local result objects.

- [ ] Write red tests for pre-submit persistence, failed audit evidence, local bytes, idempotency, current credential, and rollback flag.
- [ ] Run focused tests; verify current direct backend path fails snapshot assertions.
- [ ] Move image execution behind supplier runtime while preserving API response compatibility.
- [ ] Run focused tests plus existing asset generation tests.
- [ ] Commit `feat: route image generation through durable supplier jobs`.

### Task 4: Agnes Video And Poller Cutover

**Files:**
- Modify: `ai_drama_web/services/generation_execution.py`
- Modify: `ai_drama_web/services/generation_poller.py`
- Modify: `ai_drama_web/services/generation_jobs.py`
- Test: `tests/web/test_supplier_video_execution.py`
- Test: `tests/web/test_supplier_poller_restart.py`

**Interfaces:**
- Produces snapshot-bound submit/poll/fetch and restart recovery; preserves `video_id`, provider input contract, result persistence, and failure redaction.

- [ ] Write red tests for snapshot routing across restart, non-global backend selection, `pending/queued/completed`, `video_id`, input asset rules, original credential, and no duplicate submit.
- [ ] Run focused tests; expect global-backend assertions to fail.
- [ ] Implement snapshot lookup/runtime invocation and frozen rate bucket in poller cycles.
- [ ] Run focused tests plus all Agnes provider, generation, poller, M3, and M4 tests.
- [ ] Commit `feat: route video jobs by supplier snapshot`.

### Task 5: Legacy Active Job Migration And Rerun

**Files:**
- Create: `ai_drama_web/suppliers/legacy.py`
- Modify: `ai_drama_web/store.py`
- Modify: `ai_drama_web/services/generation_jobs.py`
- Test: `tests/web/test_legacy_supplier_cutover.py`
- Test: `tests/web/test_supplier_rerun.py`

**Interfaces:**
- Produces `legacy_agnes_v1` active-job snapshots; default rerun inherits supplier/config/model constraints and resolves current credential.

- [ ] Write red migration/rerun tests for active vs terminal legacy jobs, current credential, missing credential no-job failure, current-project-model rerun, and historical credential backend-only mode.
- [ ] Run focused tests; expect missing legacy snapshots/rerun semantics.
- [ ] Implement idempotent startup backfill and the two explicit rerun resolution paths.
- [ ] Run focused tests, migration replay, M3 verifier, and M4 verifier.
- [ ] Commit `feat: preserve legacy jobs across supplier cutover`.

### Task 6: M6C Verification And Rollback

**Files:**
- Create: `docs/superpowers/reports/2026-07-12-m6c-adapter-cutover-verification.md`

- [ ] Run fake text/image/video E2E and all M1-M5/full baseline suites.
- [ ] Assert zero external network and no secret/signed-URL leakage.
- [ ] Exercise feature-flag rollback to legacy adapters using the same migrated store.
- [ ] Document SUP-016..SUP-021 and SUP-025 coverage with exact commands/SHAs.
- [ ] Dispatch the two mandatory read-only reviewers; record findings and resolve/retest/re-review every blocker until both return PASS.
- [ ] Commit `test: verify m6c adapter cutover` and push `feat/m6c-adapter-cutover`.
