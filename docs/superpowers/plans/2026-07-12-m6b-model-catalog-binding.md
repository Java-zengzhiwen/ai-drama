# M6B Model Catalog And Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable supplier model identities/revisions, project defaults and operation overrides, deterministic resolution, and immutable execution snapshot values without cutting over providers.

**Architecture:** Catalog identity (`supplier_model_id`) is separate from immutable definitions (`model_revision_id`). A pure resolver produces a provider-neutral `ResolvedExecutionSnapshot` from explicit project bindings and frozen supplier/model/config/runtime inputs.

**Tech Stack:** Python, SQLite, FastAPI/Pydantic, pytest.

## Global Constraints

- M6A is an approved dependency; default real-network denial remains active.
- Implement SUP-010..SUP-015, SUP-018, SUP-024, SUP-026..SUP-028.
- No production adapter/poller routing or management UI in M6B.

---

### Task 1: Stable Model Catalog And Revisions

**Files:**
- Modify: `ai_drama_web/store.py`
- Create: `ai_drama_web/suppliers/catalog.py`
- Modify: `ai_drama_web/suppliers/models.py`
- Test: `tests/web/test_supplier_model_catalog.py`

**Interfaces:**
- Produces: `SupplierModelRecord`, `ModelRevisionRecord`; catalog create/update/disable/delete APIs keyed by UUID.

- [ ] Write red tests for stable UUIDs, immutable revisions, provider/display rename, source `built_in|overlay`, deterministic built-in IDs, disable, and referenced-delete rejection.
- [ ] Run focused tests and confirm missing schema/API failures.
- [ ] Add model/model_revision tables, independent catalog revision, merge rules by stable identity, typed store/catalog services, and ETag conflicts.
- [ ] Re-run tests and migration verifier; assert old revisions remain readable.
- [ ] Commit `feat: add stable supplier model catalog`.

### Task 2: Project Binding Sets And Resolver

**Files:**
- Create: `ai_drama_web/suppliers/resolution.py`
- Create: `ai_drama_web/routers/model_bindings.py`
- Create: `ai_drama_web/schemas/model_bindings.py`
- Modify: `ai_drama_web/app.py`
- Test: `tests/web/test_model_binding_resolution.py`
- Test: `tests/web/test_model_binding_api.py`

**Interfaces:**
- Produces: `resolve_model_binding(project_id, capability, operation_key) -> ResolvedModelBinding`; resolution order operation override -> capability default -> `MODEL_BINDING_MISSING`.

- [ ] Write red tests for defaults, overrides, missing binding, disabled model/supplier, stale ETag, loopback guard, and no implicit fallback.
- [ ] Run focused tests; expect missing resolver/routes.
- [ ] Implement binding-set tables/revision, pure resolver, conditional GET/PUT routes, and resolution evidence.
- [ ] Run focused tests plus M6A loopback tests.
- [ ] Commit `feat: add project model binding resolution`.

### Task 3: Immutable Execution Snapshot Value

**Files:**
- Create: `ai_drama_web/suppliers/snapshots.py`
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_web/store.py`
- Test: `tests/web/test_execution_snapshot.py`

**Interfaces:**
- Produces: `ResolvedExecutionSnapshot`, `build_execution_snapshot(...)`, `snapshot_hash(snapshot)`, object-store persistence and run/job reference columns.

- [ ] Write red tests for every design fingerprint field, canonical JSON, stable hash, compiled artifact reference, no plaintext secret, and fail-closed missing runtime.
- [ ] Run tests; expect missing types/columns.
- [ ] Implement frozen value object, canonical serializer, content-addressed storage, nullable legacy references, and `SUPPLIER_RUNTIME_UNAVAILABLE` validation.
- [ ] Run focused tests and migration replay tests.
- [ ] Commit `feat: persist supplier execution snapshots`.

### Task 4: Snapshot-Aware Idempotency And Rate Bucket

**Files:**
- Create: `ai_drama_web/suppliers/idempotency.py`
- Modify: `ai_drama_web/services/generation_jobs.py`
- Test: `tests/web/test_supplier_idempotency.py`

**Interfaces:**
- Produces: canonical request hash including snapshot hash; scope `(supplier_id, capability, idempotency_key)`; frozen `rate_limit_bucket_key`.

- [ ] Write red tests for same hash reuse, changed snapshot conflict, cross-supplier key reuse, validated manifest bucket, and runtime output unable to alter bucket.
- [ ] Run focused tests; verify current behavior fails changed-snapshot cases.
- [ ] Implement scoped idempotency helper and snapshot-frozen bucket without activating new routing.
- [ ] Run focused tests plus current generation idempotency regressions.
- [ ] Commit `feat: scope supplier idempotency by snapshot`.

### Task 5: M6B Verification

**Files:**
- Create: `docs/superpowers/reports/2026-07-12-m6b-model-catalog-binding-verification.md`

- [ ] Run catalog, binding, snapshot, idempotency, M6A, migration, and full baseline tests.
- [ ] Map results to SUP-010..SUP-015 and SUP-018.
- [ ] Verify rollback stops binding/snapshot writes while retaining M6A data and legacy paths.
- [ ] Run placeholder/secret/network/diff scans.
- [ ] Commit `test: verify m6b model binding` and push `feat/m6b-model-catalog-binding`.
