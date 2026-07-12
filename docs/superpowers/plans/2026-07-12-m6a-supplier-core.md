# M6A Supplier Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable supplier/config/credential foundations, recoverable secret storage, an isolated TypeScript worker, and application-layer loopback enforcement without changing current provider routing.

**Architecture:** Python owns persistence, policy, compilation orchestration, and worker lifecycle. A minimal Node worker runs compiled supplier artifacts in a restricted VM and communicates over versioned JSON lines; management APIs are guarded from the direct peer before route execution.

**Tech Stack:** Python 3.11+, SQLite, FastAPI, Pydantic, Node.js, TypeScript/esbuild, `node:vm`, pytest.

## Global Constraints

- Follow `AGENTS.md`, the M6 governance contract, and SUP-001..SUP-009, SUP-013..SUP-014, SUP-022..SUP-024, SUP-026..SUP-028.
- Default tests deny real network; no provider request is authorized.
- Existing global Agnes/OpenAI runtime paths remain unchanged behind feature flags.
- Only the main agent writes; preserve the documented M6A rollback point.

---

### Task 1: Migration Ledger And Supplier Schema

**Files:**
- Modify: `ai_drama_web/store.py`
- Create: `ai_drama_web/suppliers/models.py`
- Test: `tests/web/test_supplier_store.py`
- Test: `tests/web/test_supplier_migration.py`

**Interfaces:**
- Produces: `SupplierRecord`, `SupplierVersionRecord`, `ConfigRevisionRecord`, `CredentialVersionRecord`, `CredentialJournalRecord`; `ProductStore.create_supplier(...)`, `get_supplier(...)`, `replace_supplier_version(...)`.

- [ ] **Step 1: Write red schema and replay tests** asserting stable UUIDs, immutable versions, independent revision counters, built-in rows, unique slugs, `schema_migrations`, and a second initialization with no changes.
- [ ] **Step 2: Run** `python3 -m pytest tests/web/test_supplier_store.py tests/web/test_supplier_migration.py -q` **and expect missing tables/types.**
- [ ] **Step 3: Implement** frozen dataclasses/Pydantic records and additive tables for suppliers, supplier_versions, supplier_config_revisions, credential_versions, credential_migration_journal, and migration ledger; expose typed store methods with `expected_revision` conflict checks.
- [ ] **Step 4: Re-run focused tests and** `python3 migration/tools/verify_migration.py`; **expect PASS and unchanged legacy rows.**
- [ ] **Step 5: Commit** `feat: add m6 supplier persistence core`.

### Task 2: Recoverable Credential Storage

**Files:**
- Create: `ai_drama_web/suppliers/credentials.py`
- Modify: `ai_drama_web/secrets.py`
- Modify: `ai_drama_web/app.py`
- Test: `tests/web/test_supplier_credentials.py`

**Interfaces:**
- Consumes: credential/journal store methods from Task 1.
- Produces: `SupplierCredentialStore.replace(supplier_id, plaintext, expected_revision) -> CredentialVersionRecord`, `delete(...)`, `recover() -> CredentialRecoveryReport`.

- [ ] **Step 1: Write crash-injection tests** at temporary write, fsync, pending commit, rename, ready commit, pending delete, and final delete boundaries; assert convergence or `CREDENTIAL_STORAGE_CORRUPT`.
- [ ] **Step 2: Run** `python3 -m pytest tests/web/test_supplier_credentials.py -q`; **expect import failures.**
- [ ] **Step 3: Implement** same-directory temp files, mode `0600`, content hash, journal states, atomic rename, parent fsync, idempotent startup recovery, grace-period orphan cleanup, and redacted status objects.
- [ ] **Step 4: Wire `recover()` before backend/poller startup**, then run focused tests twice to prove replay idempotency.
- [ ] **Step 5: Commit** `feat: add recoverable supplier credential storage`.

### Task 3: Supplier Contract Compiler And Immutable Artifacts

**Files:**
- Create: `ai_drama_web/suppliers/contracts.py`
- Create: `ai_drama_web/suppliers/compiler.py`
- Create: `worker/package.json`
- Create: `worker/tsconfig.json`
- Create: `worker/src/protocol.ts`
- Test: `tests/web/test_supplier_compiler.py`

**Interfaces:**
- Produces: `compile_supplier(source: str) -> CompiledSupplierArtifact` with source/artifact/manifest hashes, compiler/version/options/helper fingerprints and diagnostics.

- [ ] **Step 1: Write red tests** for manifest/export validation, deterministic artifacts, safe line/column diagnostics, forbidden imports, and object-store persistence.
- [ ] **Step 2: Run focused tests; expect compiler module missing.**
- [ ] **Step 3: Implement** a pinned esbuild invocation and provider-neutral manifest/export validation; store source and compiled artifact immutably and never include credentials.
- [ ] **Step 4: Run** focused tests and `npm --prefix worker test` (add the minimal script); **expect deterministic hashes.**
- [ ] **Step 5: Commit** `feat: compile immutable supplier adapters`.

### Task 4: Isolated Worker Protocol

**Files:**
- Create: `worker/src/worker.ts`
- Create: `ai_drama_web/suppliers/worker.py`
- Test: `tests/suppliers/test_worker_isolation.py`
- Test: `worker/src/worker.test.ts`

**Interfaces:**
- Consumes: `CompiledSupplierArtifact`.
- Produces: `SupplierWorker.invoke(artifact, operation, payload, mode, limits) -> SupplierInvocationResult` using `worker_protocol_version="1"` and `helper_api_version="1"`.

- [ ] **Step 1: Write red attacks** for `process`, `require`, imports, native fetch, filesystem, env, sockets, child processes, worker threads, infinite loop, malformed JSON, and oversized output.
- [ ] **Step 2: Run Python and Node focused tests; expect failures.**
- [ ] **Step 3: Implement** scrubbed subprocess environment, JSONL protocol, restricted `node:vm` context, no code generation/imports, versioned helpers, validation helper throwing `NETWORK_DISABLED_DURING_VALIDATION`, deadlines, output caps, process-group termination, and worker recreation.
- [ ] **Step 4: Run focused tests and verify no test can reach a non-loopback canary server.**
- [ ] **Step 5: Commit** `feat: isolate supplier typescript execution`.

### Task 5: Loopback-Only Supplier Management API

**Files:**
- Create: `ai_drama_web/middleware/local_management.py`
- Create: `ai_drama_web/routers/suppliers.py`
- Create: `ai_drama_web/schemas/suppliers.py`
- Modify: `ai_drama_web/app.py`
- Test: `tests/web/test_supplier_api.py`
- Test: `tests/web/test_local_management_guard.py`

**Interfaces:**
- Produces supplier/config/secret/code/restore endpoints from design Section 19; errors `LOCAL_MANAGEMENT_ONLY`, `REVISION_CONFLICT`, `NETWORK_DISABLED_DURING_VALIDATION`.

- [ ] **Step 1: Write red API tests** for loopback IPv4/IPv6, non-loopback rejection, spoofed forwarded headers, trusted-proxy parsing, ETags, secret masking, custom empty-template creation, save/compile, and built-in restore.
- [ ] **Step 2: Run focused tests; expect 404/missing guard.**
- [ ] **Step 3: Implement** direct-peer guard before handlers, explicit trusted proxy CIDRs, schemas/routes, conditional mutations, and compile-then-commit semantics.
- [ ] **Step 4: Run focused tests plus `python3 -m pytest tests/web/test_agnes_settings_api.py tests/web/test_app_health.py -q`.**
- [ ] **Step 5: Commit** `feat: add local supplier management api`.

### Task 6: M6A Verification And Rollback Evidence

**Files:**
- Create: `docs/superpowers/reports/2026-07-12-m6a-supplier-core-verification.md`

- [ ] **Step 1: Run focused worker, credential, migration, API, and loopback suites.**
- [ ] **Step 2: Run the M1-M5/full baseline from the governance contract.**
- [ ] **Step 3: Scan tracked diff and logs for secrets, signed URLs, unexpected endpoints, placeholders, and real-network attempts.**
- [ ] **Step 4: Document feature-flag rollback, schema-backup recovery, commands/results, and exact base/head SHAs.**
- [ ] **Step 5: Commit** `test: verify m6a supplier core` and push `feat/m6a-supplier-core`.
