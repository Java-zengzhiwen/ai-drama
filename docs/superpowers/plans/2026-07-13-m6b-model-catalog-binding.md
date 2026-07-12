# M6B Model Catalog And Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable supplier model identities, immutable model revisions, project defaults and operation overrides, fail-closed resolution, immutable provider-neutral execution snapshots, and snapshot-aware idempotency contracts without cutting over production providers.

**Architecture:** `ProductStore` owns additive SQLite persistence and atomic compare-and-swap updates. Focused supplier modules own catalog rules, operation resolution, canonical snapshot construction, and request hashing; thin loopback-guarded FastAPI routers expose those contracts. M6B persists provider-neutral evidence only and does not modify the generation poller, production adapters, or legacy generation idempotency path.

**Tech Stack:** Python 3.11+, SQLite, FastAPI, Pydantic, content-addressed `RuntimeStore`, pytest.

## Global Constraints

- Follow `AGENTS.md`, the M6 governance contract, the approved design, and the M6B execution prompt.
- Use focused red-green-refactor cycles and one focused commit per task.
- Only the main agent writes. Review agents are read-only.
- Default tests deny real network; no text, image, or video Provider request is authorized.
- Do not modify production adapter selection, `GenerationPoller`, existing generation routing, UI, secret UI, or legacy job/result data.
- Preserve M1-M5 and M6A behavior and the M6B rollback point.

---

### Task 1: Additive Model Catalog And Binding Schema

**Files:**
- Modify: `ai_drama_web/store.py`
- Modify: `ai_drama_web/suppliers/models.py`
- Create: `tests/web/test_m6b_migration.py`
- Create: `tests/web/test_supplier_model_store.py`

**Interfaces:**
- Produces immutable records `SupplierModelRecord`, `SupplierModelRevisionRecord`, `ProjectModelBindingRecord`, and `ExecutionSnapshotRecord`.
- Produces deterministic `built_in_model_id(supplier_id, declaration_key)` using UUIDv5 and additive migration `m6b_model_catalog_binding_v1`.

- [ ] **Step 1: Write failing migration and record tests** for fresh DB, M6A upgrade, replay, deterministic UUIDv5 IDs, independent `model_catalog_revision`, required indexes/FKs, and unchanged M1-M5 rows.
- [ ] **Step 2: Run** `python3 -m pytest tests/web/test_m6b_migration.py tests/web/test_supplier_model_store.py -q` **and confirm failures are missing M6B tables/types.**
- [ ] **Step 3: Add immutable dataclasses and additive tables** for `supplier_models`, `supplier_model_revisions`, `project_model_bindings`, `project_model_operation_overrides`, `execution_snapshots`, `model_creation_requests`, and `supplier_idempotency_records`; add `model_catalog_revision` to suppliers through the existing column migration helper.
- [ ] **Step 4: Seed only normalized declarations present in immutable supplier manifests.** Legacy declarations without stable IDs use UUIDv5 over the supplier identity and declaration key; empty M6A built-in manifests remain valid empty catalogs.
- [ ] **Step 5: Re-run focused tests twice plus** `python3 migration/tools/verify_migration.py`; **expect deterministic replay and no legacy data changes.**
- [ ] **Step 6: Commit** `feat: add m6b model catalog schema`.

### Task 2: Stable Catalog And Immutable Revision Service

**Files:**
- Create: `ai_drama_web/suppliers/model_catalog.py`
- Modify: `ai_drama_web/store.py`
- Modify: `tests/web/test_supplier_model_store.py`
- Create: `tests/web/test_model_catalog.py`

**Interfaces:**
- Produces `ModelCatalogService.list_models`, `create_overlay`, `revise_model`, `set_enabled`, and `delete_overlay`.
- Catalog ETag is `model-catalog-{revision}`; model ETag contains stable ID and current revision identity.

- [ ] **Step 1: Write failing behavior tests** for UUIDv4 overlay identity, stable identity across rename, immutable old revision/name, active duplicate `(capability, provider_model_name)` rejection, base/overlay union by stable ID, and config/catalog revision independence.
- [ ] **Step 2: Write failing concurrency/deletion tests** for catalog CAS, model revision CAS, built-in physical-delete rejection, and bound/snapshotted physical-delete rejection.
- [ ] **Step 3: Run** `python3 -m pytest tests/web/test_supplier_model_store.py tests/web/test_model_catalog.py -q` **and confirm expected missing methods/errors.**
- [ ] **Step 4: Implement atomic store transactions and catalog policy.** Every semantic edit inserts a new immutable revision and advances current pointers with `WHERE ... revision = ?`; losing races leave only content-addressed objects eligible for future GC, not committed model revisions.
- [ ] **Step 5: Implement idempotent create** scoped to supplier plus idempotency key and canonical body hash; same key/hash replays, changed hash raises `IDEMPOTENCY_CONFLICT`.
- [ ] **Step 6: Re-run focused tests and affected M6A supplier tests.**
- [ ] **Step 7: Commit** `feat: manage stable supplier model revisions`.

### Task 3: Project Binding Set And Fail-Closed Resolver

**Files:**
- Create: `ai_drama_web/suppliers/operations.py`
- Create: `ai_drama_web/suppliers/resolution.py`
- Modify: `ai_drama_web/store.py`
- Create: `tests/web/test_model_bindings.py`
- Create: `tests/web/test_model_resolution.py`

**Interfaces:**
- Produces fixed operation registry mapping each approved `operation_key` to `text`, `image`, or `video`.
- Produces `ModelResolver.resolve(project_id, operation_key) -> ResolvedModel` with binding source `operation_override` or `capability_default`.

- [ ] **Step 1: Write failing binding-set tests** for three capability defaults, complete replacement semantics, operation overrides, monotonic `binding_set_revision`, atomic CAS, and stale update conflict.
- [ ] **Step 2: Write failing resolver tests** for override precedence, default fallback, `MODEL_BINDING_MISSING`, `MODEL_CAPABILITY_MISMATCH`, `SUPPLIER_DISABLED`, `MODEL_DISABLED`, unknown operation key, and no worker/network/store mutation side effects.
- [ ] **Step 3: Run** `python3 -m pytest tests/web/test_model_bindings.py tests/web/test_model_resolution.py -q` **and confirm expected missing interfaces.**
- [ ] **Step 4: Implement complete binding-set persistence** with stable model IDs, FK/reference validation, operation capability validation, and one transaction/CAS unit.
- [ ] **Step 5: Implement the pure fail-closed resolver** that reads exact current supplier/model revisions without fallback or Provider invocation.
- [ ] **Step 6: Re-run focused tests and project/store regressions.**
- [ ] **Step 7: Commit** `feat: resolve project model bindings`.

### Task 4: Immutable Execution Snapshot And Request Idempotency Contracts

**Files:**
- Create: `ai_drama_web/suppliers/snapshots.py`
- Create: `ai_drama_web/suppliers/idempotency.py`
- Modify: `ai_drama_web/store.py`
- Create: `tests/web/test_execution_snapshot.py`
- Create: `tests/web/test_supplier_idempotency.py`

**Interfaces:**
- Produces frozen `ExecutionSnapshot`, `SnapshotBuilder.build(resolution, ...)`, `persist_snapshot`, `load_snapshot`, `canonical_request_hash(request, snapshot_hash)`, and `SupplierIdempotencyStore.claim(...)`.

- [ ] **Step 1: Write failing snapshot tests** for canonical JSON, stable hash/object ID, exact supplier/model/config/catalog/runtime/compiler/helper/rate-limit/credential/constraints/worker-limit fingerprint, no secret plaintext, and hash changes for each material fingerprint.
- [ ] **Step 2: Write failing historical tests** proving an old snapshot retains old `model_revision_id` and `provider_model_name`, missing referenced object/runtime fails `SUPPLIER_RUNTIME_UNAVAILABLE`, and snapshotted models cannot be deleted.
- [ ] **Step 3: Write failing request-hash/idempotency tests** for normalized provider-neutral request plus snapshot hash, same supplier/capability/key/hash replay, changed snapshot conflict, different supplier key reuse, and unchanged legacy `(provider, idempotency_key)` behavior.
- [ ] **Step 4: Run** `python3 -m pytest tests/web/test_execution_snapshot.py tests/web/test_supplier_idempotency.py -q` **and confirm expected missing contracts.**
- [ ] **Step 5: Implement canonical serialization with sorted keys, compact separators, UTF-8, finite JSON only, content-addressed storage, and immutable snapshot index rows.** Do not add snapshot routing to runs/jobs in M6B.
- [ ] **Step 6: Implement generic scoped idempotency records** separate from legacy generation-job uniqueness and verify no generation route or poller call site changes.
- [ ] **Step 7: Re-run focused tests and existing generation idempotency regressions.**
- [ ] **Step 8: Commit** `feat: persist model execution snapshots`.

### Task 5: Loopback-Only Model And Binding APIs

**Files:**
- Create: `ai_drama_web/schemas/models.py`
- Create: `ai_drama_web/routers/models.py`
- Create: `ai_drama_web/routers/model_bindings.py`
- Modify: `ai_drama_web/app.py`
- Modify: `ai_drama_web/middleware/local_management.py`
- Create: `tests/web/test_model_api.py`
- Create: `tests/web/test_model_binding_api.py`

**Interfaces:**
- Implements the eight M6B routes from design Section 19 using stable IDs, stable error payloads, ETags, `If-Match`, `If-None-Match: *`, and idempotency keys.

- [ ] **Step 1: Write failing API tests** for list/create/get/patch/delete, stable-ID paths, secret absence, create replay/conflict, catalog/model ETags, precondition required, stale 409, and stable deletion errors.
- [ ] **Step 2: Write failing binding/resolution API tests** for GET/PUT ETags, full-set CAS, unknown operation/capability mismatch, resolution preview, direct non-loopback rejection, and spoofed forwarded-header rejection.
- [ ] **Step 3: Run** `python3 -m pytest tests/web/test_model_api.py tests/web/test_model_binding_api.py tests/web/test_local_management_guard.py -q` **and confirm 404/missing route failures.**
- [ ] **Step 4: Implement thin schemas/routers** over Task 2-4 services; register project model routes under the existing application-layer management guard without adding public gateway exceptions.
- [ ] **Step 5: Re-run focused tests plus M6A supplier API, app health, project API, and loopback regressions.**
- [ ] **Step 6: Commit** `feat: expose local model binding api`.

### Task 6: M6B Verifier, Migration Evidence, And Review Handoff

**Files:**
- Create: `tools/verify_m6b_model_catalog_binding.py`
- Create: `tests/test_verify_m6b_model_catalog_binding.py`
- Create: `docs/superpowers/reports/2026-07-13-m6b-model-catalog-binding-verification.md`

- [ ] **Step 1: Write a failing verifier contract test** requiring sanitized JSON and Markdown evidence for stable identities, revisions, base/overlay isolation, catalog ETag, project defaults/override, fail-closed resolution, snapshot/hash, idempotency conflict, loopback, migration, zero real network, and M1-M5 regression.
- [ ] **Step 2: Run** `python3 -m pytest tests/test_verify_m6b_model_catalog_binding.py -q` **and confirm the verifier is absent.**
- [ ] **Step 3: Implement a deterministic fake-data verifier** using temporary stores and local test clients only; it must never instantiate or call a real Provider backend.
- [ ] **Step 4: Run focused M6B suites, the verifier, migration replay, and the full governance verification matrix.**
- [ ] **Step 5: Scan the full base-to-head diff** for secrets, signed URLs, Provider endpoints, accidental adapter/poller changes, runtime data, databases, and private outputs.
- [ ] **Step 6: Dispatch two independent read-only reviewers** against the verified commit candidate: specification compliance and technical/security. Reproduce and fix every blocker/high finding with a red test, rerun affected/full verification, and obtain two final PASS results.
- [ ] **Step 7: Write the sanitized verification report** with approved base/head SHAs, commands/results, reviewer findings/corrections/PASS, zero real-request counters, known warnings, and rollback procedure.
- [ ] **Step 8: Commit** `test: verify m6b model catalog binding`, **push** `feat/m6b-model-catalog-binding`, and provide the Review Handoff block with compare/PR URL.

## Plan Self-Review

- Spec coverage: Tasks 1-5 cover every allowed M6B data, resolver, snapshot, idempotency, API, migration, and loopback contract; Task 6 covers the required verifier, regression matrix, reviews, report, and push.
- Scope boundary: No task edits production provider adapters, poller routing, generation routes, Web UI, secrets UI, legacy fields, or real Provider execution.
- Type consistency: Bindings and APIs use `supplier_model_id`; revisions use `model_revision_id`; catalog/config/binding revisions remain independent; snapshots freeze exact revision identities.
- Placeholder scan: all implementation actions and expected outcomes are concrete. Explicit M6C/M6D exclusions are scope controls, not incomplete M6B work.
- Rollback: M6B is additive; rollback stops M6B writes/routes, deploys M6A, preserves M6B rows for audit or restores the pre-M6B schema backup, and leaves legacy runtime routing unchanged.
