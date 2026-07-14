# Model-Level Real Provider Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add loopback-only, model-row real text/image tests with durable submit-once execution, sanitized local results, and an AI Drama-native Chinese supplier adapter template.

**Architecture:** A new `supplier_model_test_runs` record and private request object are persisted with an immutable M6 execution snapshot before an asynchronous executor claims the run. The executor invokes the existing snapshot-aware Supplier Worker gateway exactly once, stores normalized text or image bytes separately from project assets/jobs, and exposes only sanitized loopback APIs. The React model table opens a confirmation modal, persists only run/key identifiers in session storage, and polls local state.

**Tech Stack:** Python 3, FastAPI, SQLite, existing content-addressed runtime store, isolated Node/TypeScript Supplier Worker, React, TypeScript, Ant Design, TanStack Query, Vitest, Playwright, pytest.

---

## Scope And File Map

Create:

- `ai_drama_web/suppliers/model_tests.py`: direct resolution, request hashing, durable claim-once execution, recovery, sanitization, and safe projections.
- `ai_drama_web/routers/model_tests.py`: loopback-only create/recover/read/content endpoints.
- `ai_drama_web/schemas/model_tests.py`: request and response schemas.
- `web/src/features/suppliers/ModelTestDialog.tsx`: confirmation, local polling, text/image result rendering, and session recovery.
- `web/src/features/suppliers/ModelTestDialog.test.tsx`: focused modal behavior tests.
- `tests/web/test_supplier_model_tests.py`: store/service/executor/API/restart/security tests.
- `tools/verify_model_level_provider_tests.py`: semantic verifier with fake-only execution.
- `tests/tools/test_verify_model_level_provider_tests.py`: verifier contract tests.
- `docs/superpowers/reports/2026-07-14-model-level-provider-tests-verification.md`: final evidence and review report.

Modify:

- `ai_drama_web/store.py`: additive table/index creation and model-test CRUD/CAS methods.
- `ai_drama_web/app.py`: feature flag, router registration, test executor startup/recovery, and shutdown.
- `ai_drama_web/middleware/local_management.py`: classify all model-test routes as management-only.
- `ai_drama_web/suppliers/builtin_adapters.py`: Chinese comments only; preserve adapter behavior.
- `web/src/features/suppliers/api.ts`: model-test API types and functions.
- `web/src/features/suppliers/api.test.ts`: request/header/response tests.
- `web/src/features/suppliers/SupplierModelsPanel.tsx`: final row action and dialog ownership.
- `web/src/features/suppliers/SupplierModelsPanel.test.tsx`: eligibility/order/disable tests.
- `web/src/app/app.css`: compact modal/result styles with stable dimensions.
- `tests/web/test_supplier_api.py`: new-custom-supplier Chinese template contract.
- `tests/web/test_supplier_builtin_adapters.py`: comment-only behavioral equivalence assertions.
- `migration/tools/verify_migration.py`: fresh/upgraded/replay checks for the additive table.
- `AGENTS.md`: post-M6 feature flag, real-network denial, and user-click authorization boundary.

Do not modify project generation-job/result/asset schemas or real-provider smoke scripts.

### Task 1: Add Model-Test Persistence And CAS State Machine

**Files:** `ai_drama_web/store.py`, `tests/web/test_supplier_model_tests.py`, `tests/web/test_supplier_credentials.py`, `migration/tools/verify_migration.py`

- [ ] **Step 1: Write failing store tests for additive schema and round-trip**

```python
def test_model_test_run_round_trip_is_separate_from_generation_tables(product_store, runtime_store, snapshot):
    request_object_id = runtime_store.write_text_object('{"prompt":"hello"}')
    run, created = product_store.create_supplier_model_test_run(
        test_run_id="test-run-1", supplier_id=snapshot.supplier_id,
        supplier_model_id=snapshot.supplier_model_id, snapshot=snapshot,
        capability="text", idempotency_key="model-test-key-1",
        request_hash="request-hash-1", request_object_id=request_object_id,
    )
    assert created is True
    assert run["status"] == "queued"
    assert run["attempt_count"] == 0
    assert product_store.conn.execute("SELECT count(*) FROM generation_jobs").fetchone()[0] == 0
    assert product_store.conn.execute("SELECT count(*) FROM assets").fetchone()[0] == 0
```

Add tests for same-key replay, changed-hash conflict, atomic claim, concurrent losing claim, completion, failure, and unknown recovery.

- [ ] **Step 2: Run the focused tests and confirm red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py -k 'round_trip or idempotency or claim'
```

Expected: FAIL because the table and store methods do not exist.

- [ ] **Step 3: Add the additive table and indexes**

```sql
CREATE TABLE IF NOT EXISTS supplier_model_test_runs (
  test_run_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL,
  supplier_model_id TEXT NOT NULL,
  snapshot_hash TEXT NOT NULL,
  snapshot_object_id TEXT NOT NULL,
  capability TEXT NOT NULL CHECK(capability IN ('text','image')),
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  request_object_id TEXT NOT NULL,
  status TEXT NOT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  lease_owner TEXT NOT NULL DEFAULT '',
  lease_expires_at TEXT NOT NULL DEFAULT '',
  normalized_result_object_id TEXT NOT NULL DEFAULT '',
  sanitized_evidence_object_id TEXT NOT NULL DEFAULT '',
  content_object_id TEXT NOT NULL DEFAULT '',
  media_type TEXT NOT NULL DEFAULT '',
  byte_size INTEGER NOT NULL DEFAULT 0,
  error_code TEXT NOT NULL DEFAULT '',
  error_message TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT '',
  finished_at TEXT NOT NULL DEFAULT '',
  UNIQUE(supplier_model_id, capability, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_supplier_model_test_runs_status
ON supplier_model_test_runs(status, created_at, test_run_id);
```

- [ ] **Step 4: Implement store methods with transactional semantics**

```python
create_supplier_model_test_run(...) -> tuple[dict, bool]
get_supplier_model_test_run(test_run_id: str) -> dict | None
get_supplier_model_test_run_by_key(supplier_model_id: str, idempotency_key: str) -> dict | None
claim_supplier_model_test_run(test_run_id: str, lease_owner: str, lease_expires_at: str) -> dict | None
complete_supplier_model_test_run(test_run_id: str, *, normalized_result_object_id: str,
                                 sanitized_evidence_object_id: str, content_object_id: str = "",
                                 media_type: str = "", byte_size: int = 0) -> dict
fail_supplier_model_test_run(test_run_id: str, *, error_code: str, error_message: str,
                             sanitized_evidence_object_id: str = "") -> dict
mark_interrupted_model_tests_unknown() -> int
list_queued_supplier_model_tests(limit: int = 20) -> list[dict]
count_active_model_tests_for_credential(credential_version_id: str) -> int
```

The claim is one `UPDATE ... WHERE status='queued' AND attempt_count=0` that also sets attempt count, lease, status, and start time.

- [ ] **Step 5: Add credential active-reference and force-delete tests**

Normal deletion conflicts for queued/submitting snapshots. Force deletion fails queued work with `CREDENTIAL_REVOKED` and marks submitting work `submission_outcome_unknown` without changing attempt count.

- [ ] **Step 6: Extend migration verification**

Assert fresh DB, upgraded M6 DB, and replay contain the table/indexes without rewriting generation/history rows.

- [ ] **Step 7: Run green verification**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py tests/web/test_supplier_credentials.py
python3 migration/tools/verify_migration.py
```

Expected: selected tests pass and verifier exits 0.

- [ ] **Step 8: Commit**

```bash
git add ai_drama_web/store.py tests/web/test_supplier_model_tests.py \
  tests/web/test_supplier_credentials.py migration/tools/verify_migration.py
git commit -m "feat: persist model-level test runs"
```

### Task 2: Implement Direct Resolution And Submit-Once Executor

**Files:** `ai_drama_web/suppliers/model_tests.py`, `tests/web/test_supplier_model_tests.py`, `ai_drama_web/suppliers/credentials.py`

- [ ] **Step 1: Write failing preflight tests**

```python
@pytest.mark.parametrize("mutation,code", [
    ("disable_supplier", "SUPPLIER_DISABLED"),
    ("disable_model", "MODEL_DISABLED"),
    ("remove_credential", "CREDENTIAL_MISSING"),
    ("corrupt_credential", "CREDENTIAL_STORAGE_CORRUPT"),
    ("remove_export", "SUPPLIER_OPERATION_UNAVAILABLE"),
])
def test_model_test_preflight_fails_before_gateway(mutation, code, harness):
    harness.apply(mutation)
    with pytest.raises(ModelTestError, match=code):
        harness.service.create_model_test(**harness.request())
    assert harness.gateway.calls == []
```

Add video rejection; prompt 1/4000 text and 1/2000 image boundaries; model-defined image-size resolution; the `1024x768` fallback; and a check that the snapshot-frozen rate-limit bucket is used.

- [ ] **Step 2: Run the preflight selection and confirm red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py -k 'preflight or prompt or video'
```

Expected: FAIL because `ModelTestService` is absent.

- [ ] **Step 3: Implement direct resolution and immutable creation**

```python
class ModelTestError(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code

class ModelTestService:
    def create_model_test(self, *, supplier_model_id: str, prompt: str,
                          idempotency_key: str, expected_model_revision: int) -> dict: ...
    def safe_read(self, test_run_id: str) -> dict: ...
    def safe_read_by_key(self, supplier_model_id: str, idempotency_key: str) -> dict: ...
```

Use `SnapshotBuilder` with `operation_key="supplier_model_test"`, `binding_source="direct_model_test"`, and `credential_resolution_mode="current"`. Resolve image size from the model definition and fall back to `1024x768`. Persist normalized request plus snapshot/run together and retain the validated snapshot rate-limit bucket.

- [ ] **Step 4: Write failing executor tests**

```python
def test_executor_claims_and_invokes_text_once(harness):
    run = harness.create_text()
    harness.executor.execute(run["test_run_id"])
    harness.executor.execute(run["test_run_id"])
    assert harness.gateway.operations == ["textRequest"]
    assert harness.read(run)["status"] == "completed"
```

Add image bytes/media, sanitization, URL removal, timeout/failure, concurrent claim, queued restart, submitting restart, and no project side effects.

- [ ] **Step 5: Run executor tests and confirm red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py -k 'executor or restart or sanitize'
```

Expected: FAIL because `ModelTestExecutor` is absent.

- [ ] **Step 6: Implement the executor through the existing snapshot gateway**

```python
class ModelTestExecutor:
    def execute(self, test_run_id: str) -> dict: ...
    def recover_startup(self) -> dict: ...
    def drain_queued(self, limit: int = 20) -> int: ...
```

Sequence: CAS claim, exact snapshot/request load, acquire the existing limiter with the snapshot-frozen bucket, invoke one `textRequest` or `imageRequest`, sanitize, persist normalized text or bounded image bytes, and complete atomically. Any ambiguous failure after claim becomes `SUBMISSION_OUTCOME_UNKNOWN`; it never returns to queued.

- [ ] **Step 7: Run service regression**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py tests/web/test_m6c_adapter_cutover.py
```

Expected: all pass with a fake submit counter of one.

- [ ] **Step 8: Commit**

```bash
git add ai_drama_web/suppliers/model_tests.py ai_drama_web/suppliers/credentials.py \
  tests/web/test_supplier_model_tests.py
git commit -m "feat: execute model tests from frozen snapshots"
```

### Task 3: Add Loopback API, Feature Flag, And Recovery

**Files:** `ai_drama_web/schemas/model_tests.py`, `ai_drama_web/routers/model_tests.py`, `ai_drama_web/app.py`, `ai_drama_web/middleware/local_management.py`, `tests/web/test_supplier_model_tests.py`, `tests/web/test_local_management_guard.py`, `tests/web/test_app_lifecycle.py`, `AGENTS.md`

- [ ] **Step 1: Write failing API and guard tests**

```python
response = client.post(
    f"/api/models/{model_id}/tests",
    headers={"Idempotency-Key": "test-key", "If-Match": model_etag},
    json={"prompt": "hello"},
)
assert response.status_code == 202
assert response.json()["status"] == "queued"
```

Cover missing headers, stale ETag, validation, flag off, recovery-by-key header, status, image content headers, text content 404, non-loopback/FRP/spoofed forwarding, and safe errors.

- [ ] **Step 2: Run API tests and confirm red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py tests/web/test_local_management_guard.py -k 'api or model_test'
```

Expected: FAIL with 404 routes.

- [ ] **Step 3: Add request/read schemas and routes**

Define `ModelTestCreate(prompt: str)` and safe read models. Implement:

```text
POST /api/models/{supplier_model_id}/tests
GET  /api/models/{supplier_model_id}/tests/by-idempotency-key
GET  /api/model-tests/{test_run_id}
GET  /api/model-tests/{test_run_id}/content
```

Create returns after durable queueing. Content sends `nosniff`, `private, no-store`, and exact length. No response includes prompt, credential, provider URL, or raw evidence.

- [ ] **Step 4: Wire flag and lifecycle**

Read `AI_DRAMA_MODEL_TESTS_ENABLED`, default false. When true, startup marks interrupted submitting rows unknown, starts one bounded drain loop, and processes queued work. Shutdown cancels/awaits it. When false, create returns `MODEL_TESTS_DISABLED`; local reads remain available.

- [ ] **Step 5: Extend loopback classification and AGENTS governance**

Protect both route families unconditionally. Record the exact per-click authorization and automated zero-network boundary without weakening M5/M6 gates.

- [ ] **Step 6: Run API/lifecycle green**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py \
  tests/web/test_local_management_guard.py tests/web/test_app_lifecycle.py
```

Expected: all pass and fake submission count remains one.

- [ ] **Step 7: Commit**

```bash
git add AGENTS.md ai_drama_web/app.py ai_drama_web/middleware/local_management.py \
  ai_drama_web/routers/model_tests.py ai_drama_web/schemas/model_tests.py \
  tests/web/test_supplier_model_tests.py tests/web/test_local_management_guard.py \
  tests/web/test_app_lifecycle.py
git commit -m "feat: expose loopback-only model test API"
```

### Task 4: Add Model-Row Dialog And Results

**Files:** `web/src/features/suppliers/api.ts`, `web/src/features/suppliers/api.test.ts`, `web/src/features/suppliers/ModelTestDialog.tsx`, `web/src/features/suppliers/ModelTestDialog.test.tsx`, `web/src/features/suppliers/SupplierModelsPanel.tsx`, `web/src/features/suppliers/SupplierModelsPanel.test.tsx`, `web/src/app/app.css`, `web/e2e/supplier-management.spec.ts`

- [ ] **Step 1: Write failing API-client and component tests**

Assert create headers, header-based recovery, blob content, text/image eligibility, action order, no video action, modal defaults/warning, cancel-zero-call, double-click lock, session recovery, all states, text usage, image preview, and sanitized errors.

- [ ] **Step 2: Run Vitest and confirm red**

```bash
npm --prefix web run test -- --run \
  src/features/suppliers/api.test.ts \
  src/features/suppliers/SupplierModelsPanel.test.tsx \
  src/features/suppliers/ModelTestDialog.test.tsx
```

Expected: FAIL because APIs/dialog are absent.

- [ ] **Step 3: Implement API types and functions**

```typescript
export type ModelTestStatus = "queued" | "submitting" | "completed" | "failed" | "submission_outcome_unknown";
export type ModelTestRead = { test_run_id: string; supplier_model_id: string; capability: "text" | "image"; status: ModelTestStatus; output?: string; usage?: Record<string, number>; media_type?: string; byte_size?: number; elapsed_ms?: number; error_code?: string; error_message?: string };
export function createModelTest(modelId: string, prompt: string, modelEtag: string, key: string): Promise<ModelTestRead>;
export function recoverModelTest(modelId: string, key: string): Promise<ModelTestRead>;
export function getModelTest(runId: string): Promise<ModelTestRead>;
export function getModelTestContent(runId: string): Promise<Blob>;
```

- [ ] **Step 4: Implement `ModelTestDialog` and final row action**

Use Ant Design Modal/TextArea/Alert/Spin/Image. Store only key/run ID in session storage, recover lost create responses, poll terminally, revoke blob URLs, and render `测试` after `删除` for text/image only. Use an icon and tooltip for disabled reasons.

- [ ] **Step 5: Add responsive styles and fake Playwright flow**

Keep modal bounded, preview ratio stable, long names wrapped, and actions non-overlapping. Browser tests assert one create, polling, text output, and image preview using fake execution only.

- [ ] **Step 6: Run Web green**

```bash
npm --prefix web run test -- --run \
  src/features/suppliers/api.test.ts \
  src/features/suppliers/SupplierModelsPanel.test.tsx \
  src/features/suppliers/ModelTestDialog.test.tsx
npm --prefix web run build
npm --prefix web run test:e2e -- --grep "model test"
```

Expected: focused tests, build, and fake browser flow pass.

- [ ] **Step 7: Commit**

```bash
git add web/src/features/suppliers/api.ts web/src/features/suppliers/api.test.ts \
  web/src/features/suppliers/ModelTestDialog.tsx \
  web/src/features/suppliers/ModelTestDialog.test.tsx \
  web/src/features/suppliers/SupplierModelsPanel.tsx \
  web/src/features/suppliers/SupplierModelsPanel.test.tsx web/src/app/app.css \
  web/e2e/supplier-management.spec.ts
git commit -m "feat: add model-row real test dialog"
```

### Task 5: Add Chinese Template And Built-In Comments

**Files:** `ai_drama_web/store.py`, `ai_drama_web/suppliers/builtin_adapters.py`, `tests/web/test_supplier_api.py`, `tests/web/test_supplier_builtin_adapters.py`

- [ ] **Step 1: Write failing new-template and equivalence tests**

```python
assert "export const vendor" in source
assert "AI 生成适配代码步骤" in source
assert "helpers.http.request" in source
assert "不要提供真实 API Key" in source
assert "video_id" in source and "task_id" in source
assert "exports.vendor" not in executable_source
compile_supplier(source, runtime_store=runtime_store)
```

Assert empty default models, safe skeleton exports, Chinese built-in guidance, identical manifests, unchanged OpenAI/Agnes requests, and Agnes polling by `video_id`.

- [ ] **Step 2: Run focused tests and confirm red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_api.py tests/web/test_supplier_builtin_adapters.py -k 'template or comments or equivalent'
```

Expected: FAIL because guidance is absent.

- [ ] **Step 3: Replace only the new-custom-supplier template**

Generate valid ESM source with the approved Chinese guide, safe empty manifest, commented stable-model/config examples, normalized returns, and skeleton operations throwing `SUPPLIER_OPERATION_NOT_CONFIGURED`. Existing custom versions are untouched.

- [ ] **Step 4: Add comment-only built-in documentation**

Document manifest/model identity, config/credential, helper HTTP, normalization, image download, keyframes, and `video_id`. Do not change endpoints, models, bodies, image rules, outputs, or error codes.

Advance the built-in source version marker only for this documented immutable revision and update installation/migration logic so existing installations point to the new source version without deleting or recompiling historical snapshot artifacts. Add a migration replay test proving the pointer advance is idempotent.

- [ ] **Step 5: Run equivalence and compiler green**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_api.py \
  tests/web/test_supplier_builtin_adapters.py tests/web/test_supplier_compiler.py \
  tests/web/test_m6c_adapter_cutover.py
npm --prefix worker test
```

Expected: all pass and Agnes fixtures poll by `video_id`.

- [ ] **Step 6: Commit**

```bash
git add ai_drama_web/store.py ai_drama_web/suppliers/builtin_adapters.py \
  tests/web/test_supplier_api.py tests/web/test_supplier_builtin_adapters.py
git commit -m "docs: add Chinese supplier adapter guidance"
```

### Task 6: Add Verifier, Full Regression, Reviews, And Handoff

**Files:** `tools/verify_model_level_provider_tests.py`, `tests/tools/test_verify_model_level_provider_tests.py`, `docs/superpowers/reports/2026-07-14-model-level-provider-tests-verification.md`

- [ ] **Step 1: Write failing verifier tests**

Require checks MTEST-001 through MTEST-015 for eligibility, confirmation, snapshot, submit-once, restart, text, image, loopback, idempotency, credential lifecycle, sanitization, project isolation, Chinese template, zero real requests, and M1-M6 regression.

- [ ] **Step 2: Run verifier tests and confirm red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/tools/test_verify_model_level_provider_tests.py
```

Expected: FAIL because verifier is absent.

- [ ] **Step 3: Implement fake-only verifier and run green**

Use temporary database/runtime, fake counters, and transport denial. Emit JSON/Markdown plus exact zero counters.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/tools/test_verify_model_level_provider_tests.py
python3 tools/verify_model_level_provider_tests.py
```

- [ ] **Step 4: Run the complete baseline**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_m3_agnes_generation.py
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m6b_model_catalog_binding.py
python3 tools/verify_m6c_adapter_cutover.py
python3 tools/verify_m6d_management_ui.py
python3 tools/verify_m6e_migration_acceptance.py
python3 tools/verify_model_level_provider_tests.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: every command exits 0. Never run a real-provider smoke script.

- [ ] **Step 5: Run security and tracked-data checks**

Scan tracked files/report for keys, Bearer values, signed query values, databases, runtime-data, private outputs, unexpected endpoint calls, and flag defaults. Confirm:

```text
PRODUCTION_MODEL_TEST_FLAG_ENABLED=false
REAL_PROVIDER_REQUESTS=false
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

- [ ] **Step 6: Perform two independent read-only reviews**

Review 1 covers specification/acceptance. Review 2 covers architecture, idempotency, credentials, Worker isolation, SSRF/loopback, redaction, migrations, release, and rollback. Fix all blocker/high findings and rerun the baseline.

- [ ] **Step 7: Write report, commit, and publish**

Record red/green evidence, complete commands, verifier, reviews, security scan, flag, and counters.

```bash
git add tools/verify_model_level_provider_tests.py \
  tests/tools/test_verify_model_level_provider_tests.py \
  docs/superpowers/reports/2026-07-14-model-level-provider-tests-verification.md
git commit -m "docs: verify model-level provider tests"
git diff --check
git status --short
git push -u origin feat/model-level-provider-tests
```

Create or update a PR with base `main`. Do not merge without explicit user approval.

## Execution Mode

Use `superpowers:executing-plans` inline in the current task. Repository instructions prohibit writable subagents without a separately approved contract, so the main agent performs implementation writes. Two independent agents are used only for the final required read-only reviews.

## Stop Conditions

Stop instead of improvising if a step requires a real provider request; a credential, signed URL, private result, database, or runtime-data file would enter Git; exact snapshot execution cannot be reused; durable claim-once requires changing the approved state model; management APIs would be exposed beyond loopback; an unrelated M1-M6 failure cannot be isolated; or a blocker/high review finding remains unresolved.
