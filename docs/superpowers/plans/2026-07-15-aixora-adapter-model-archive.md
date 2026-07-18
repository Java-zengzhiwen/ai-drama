# AIXORA Adapter And Model Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure the existing AIXORA supplier for four approved GPT text models and GPT Image 2, add bounded image generation/editing transport, and make model deletion archive immutable history instead of failing misleadingly.

**Architecture:** Extend the existing additive SQLite/store contract with archive metadata and make normal catalog/resolver paths exclude archived identities while historical reads retain them. Extend the isolated Node Worker with host-owned base64 and multipart media operations, then keep the AIXORA TypeScript adapter provider-neutral and unable to access filesystem or Node globals. Configure the existing local supplier only after offline tests pass, then execute the explicitly authorized real-call ledger without retries.

**Tech Stack:** Python 3.14, FastAPI, SQLite, React 19, TypeScript, Ant Design, Node 25 Worker VM, Vitest, Playwright, pytest.

## Global Constraints

- Work only on `feat/aixora-adapter-model-archive`, based on `feat/model-level-provider-tests` commit `fa47dba8d4803789496e6425e94b266aa58fc85d`.
- Preserve loopback-only management APIs, immutable execution snapshots, credential versioning, and feature-flag defaults.
- Automated tests, verifiers, and browser tests must make zero real provider requests.
- Never commit API keys, bearer values, signed URLs, runtime databases, runtime-data, or generated images.
- AIXORA models are exactly `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.5`, and `gpt-image-2`.
- Do not add AIXORA Grok models; the authorized live probe returned `model_not_found`.
- Reasoning effort is restricted to `none`, `low`, `medium`, `high`, `xhigh`, and `max`, defaulting to `medium`.
- Real acceptance permits four text calls, one text-to-image call, and one image-to-image call, each exactly once with no retry or fallback.
- The existing pre-implementation Grok probe remains recorded as one failed real text request.
- Implementation follows red-green-refactor and one focused commit per task.

---

## File Map

- `ai_drama_web/suppliers/models.py`: persisted model record gains archive metadata.
- `ai_drama_web/store.py`: additive schema migration, archive/reference counters, filtered listings, atomic archive mutation.
- `ai_drama_web/suppliers/model_catalog.py`: choose reject, physical delete, or archive from reference type.
- `ai_drama_web/suppliers/resolution.py`: reject archived selections and bindings.
- `ai_drama_web/routers/models.py`: expose archive metadata and retain conditional delete semantics.
- `web/src/features/suppliers/SupplierModelsPanel.tsx`: truthful archive/delete confirmation and binding explanation.
- `web/src/features/suppliers/api.ts`: extend `SupplierModelRead` with archive fields.
- `worker/src/worker.ts`: host-owned bounded base64 result and multipart input operations.
- `worker/src/media-helpers.mjs`: pure validation, decoding, multipart assembly helpers.
- `worker/src/worker.test.ts`: isolation, size, SSRF, multipart, and base64 regression coverage.
- `ai_drama_web/suppliers/custom_adapters/aixora.ts`: reviewable Chinese-commented custom supplier adapter source, without credentials.
- `tests/web/test_model_catalog.py`, `tests/web/test_model_api.py`, `tests/web/test_execution_snapshot.py`: archive domain/API/resolver coverage.
- `web/src/features/suppliers/SupplierModelsPanel.test.tsx`: UI archive behavior.
- `tests/web/test_aixora_adapter.py`: offline compiled-adapter contract tests using a fake Worker transport.
- `tests/migration/test_m6e_migration_matrix.py`: fresh/upgrade/replay archive migration assertions.
- `tools/verify_aixora_adapter_model_archive.py`: fake-only semantic verifier.
- `docs/superpowers/reports/2026-07-15-aixora-adapter-model-archive-verification.md`: sanitized automated and real acceptance evidence.

### Task 1: Archive-Aware Model Store And Migration

**Files:**
- Modify: `ai_drama_web/suppliers/models.py`
- Modify: `ai_drama_web/store.py`
- Test: `tests/web/test_model_catalog.py`
- Test: `tests/migration/test_m6e_migration_matrix.py`

**Interfaces:**
- Produces `SupplierModelRecord.archived_at: str` and `archive_reason: str`.
- Produces `ProductStore.list_supplier_models(supplier_id, *, include_archived=False)`.
- Produces `ProductStore.count_model_history_references(supplier_model_id) -> int`.
- Produces `ProductStore.archive_supplier_model(supplier_model_id, *, expected_catalog_revision, expected_model_revision, archive_reason) -> SupplierModelRecord`.

- [ ] **Step 1: Write failing store tests**

Add tests proving an overlay with an execution snapshot is archived atomically, normal lists omit it, `include_archived=True` retains it, revisions increment once, and a replay with the new revision is idempotent. Add a migration test that upgrades an M6E database with empty archive fields and survives a second open.

```python
archived = store.archive_supplier_model(
    model.supplier_model_id,
    expected_catalog_revision=1,
    expected_model_revision=1,
    archive_reason="historical_snapshot",
)
assert archived.archived_at
assert archived.archive_reason == "historical_snapshot"
assert store.list_supplier_models(supplier.supplier_id) == []
assert store.list_supplier_models(supplier.supplier_id, include_archived=True) == [archived]
```

- [ ] **Step 2: Run red tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q \
  tests/web/test_model_catalog.py -k archive \
  tests/migration/test_m6e_migration_matrix.py -k archive
```

Expected: fail because archive fields and methods do not exist.

- [ ] **Step 3: Implement additive archive storage**

Add schema columns through `_ensure_column`:

```python
self._ensure_column("supplier_models", "archived_at", "TEXT NOT NULL DEFAULT ''")
self._ensure_column("supplier_models", "archive_reason", "TEXT NOT NULL DEFAULT ''")
```

Extend the record dataclass and implement filtered listing plus an atomic conditional update that sets `enabled=0`, archive metadata, `revision=revision+1`, and supplier `model_catalog_revision=model_catalog_revision+1`. An already archived row with matching current revisions returns unchanged rather than incrementing again.

- [ ] **Step 4: Run green tests and migration verifier**

Run the focused pytest command above, then:

```bash
python3 migration/tools/verify_migration.py
```

Expected: focused tests pass; migration manifest verifier remains valid because no packaged migration artifact is modified.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_web/suppliers/models.py ai_drama_web/store.py \
  tests/web/test_model_catalog.py tests/migration/test_m6e_migration_matrix.py
git commit -m "feat: archive historically referenced supplier models"
```

### Task 2: Archive-Aware Catalog, API, Resolver, And UI

**Files:**
- Modify: `ai_drama_web/suppliers/model_catalog.py`
- Modify: `ai_drama_web/suppliers/resolution.py`
- Modify: `ai_drama_web/routers/models.py`
- Modify: `web/src/features/suppliers/api.ts`
- Modify: `web/src/features/suppliers/SupplierModelsPanel.tsx`
- Modify: `web/src/features/suppliers/managementErrors.ts`
- Test: `tests/web/test_model_api.py`
- Test: `tests/web/test_execution_snapshot.py`
- Test: `web/src/features/suppliers/SupplierModelsPanel.test.tsx`

**Interfaces:**
- `ModelCatalogService.delete_overlay(...)` physically deletes no-reference overlays and archives history-only overlays.
- `ModelBindingService` and `ModelResolver` raise `MODEL_ARCHIVED` for archived identities.
- Model JSON includes `archived_at` and `archive_reason`; normal supplier lists exclude archived rows.

- [ ] **Step 1: Write failing API/resolver/UI tests**

Add API coverage for a failed model test snapshot followed by DELETE returning 204, the normal list becoming empty, and direct historical model read showing archive metadata. Add active binding rejection and archived binding/resolution rejection. Update the component test to assert the confirmation text:

```text
没有历史引用的模型会永久删除；已有测试或任务历史的模型会归档并从可选列表隐藏。
```

and ensure a successful archive removes the row after refetch.

- [ ] **Step 2: Run red tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_model_api.py tests/web/test_execution_snapshot.py -k 'archive or archived'
npm --prefix web run test -- --run web/src/features/suppliers/SupplierModelsPanel.test.tsx
```

Expected: fail because DELETE still returns `MODEL_REFERENCED` and the UI copy is physical-delete-only.

- [ ] **Step 3: Implement archive decision and resolver guards**

Use project binding references as the hard blocker and execution snapshots as archive history:

```python
if self.store.count_project_binding_references(supplier_model_id):
    raise ModelCatalogError("MODEL_REFERENCED")
if self.store.count_model_history_references(supplier_model_id):
    return self.store.archive_supplier_model(
        supplier_model_id,
        expected_catalog_revision=expected_catalog_revision,
        expected_model_revision=expected_model_revision,
        archive_reason="historical_snapshot",
    )
return self.store.delete_supplier_model(
    supplier_model_id,
    expected_catalog_revision=expected_catalog_revision,
    expected_model_revision=expected_model_revision,
)
```

Reject archived rows before capability checks in binding validation and current resolution. Preserve historical direct reads. Update the UI copy and management error map without adding restore/history UI.

- [ ] **Step 4: Run green tests**

Run the focused Python and web commands above. Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_web/suppliers/model_catalog.py ai_drama_web/suppliers/resolution.py \
  ai_drama_web/routers/models.py web/src/features/suppliers/api.ts \
  web/src/features/suppliers/SupplierModelsPanel.tsx \
  web/src/features/suppliers/managementErrors.ts tests/web/test_model_api.py \
  tests/web/test_execution_snapshot.py \
  web/src/features/suppliers/SupplierModelsPanel.test.tsx
git commit -m "fix: make model deletion archive immutable history"
```

### Task 3: Bounded Worker Media Helpers

**Files:**
- Create: `worker/src/media-helpers.mjs`
- Modify: `worker/src/worker.ts`
- Modify: `worker/src/worker.test.ts`
- Test: `tests/suppliers/test_worker_isolation.py`

**Interfaces:**
- Adds supplier-visible `helpers.media.decodeBase64(value, mediaType)` returning the existing bounded `local_file/sha256/size/media_type` reference.
- Adds `helpers.http.request({ ..., multipart: { fields, files } })` where every file URL must exactly match a declared `payload.request.input_images` entry.
- Does not expose Buffer, filesystem, raw body, arbitrary local path, or general URL fetch to supplier code.

- [ ] **Step 1: Write pure helper and Worker red tests**

Cover valid base64, invalid base64, decoded-size overflow, deterministic multipart field encoding, exact declared input acceptance, undeclared URL rejection, private/metadata IP rejection, redirect rejection, aggregate-size overflow, and absence of Node globals in supplier context.

```javascript
const result = invoke(`
  module.exports.imageRequest = async (_payload, helpers) =>
    helpers.media.decodeBase64("ZmFrZS1wbmc=", "image/png");
`, "execution", {});
assert.equal(result.value.media_type, "image/png");
```

- [ ] **Step 2: Run red tests**

```bash
npm --prefix worker test
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/suppliers/test_worker_isolation.py
```

Expected: new tests fail because `helpers.media` and multipart are absent.

- [ ] **Step 3: Implement host-owned media operations**

Keep base64 decoding and multipart assembly outside the VM. Use strict base64 validation, random boundaries, CRLF-safe field names, fixed scalar field allowlists supplied by the adapter request, exact input URL matching, public A/AAAA checks, pinned lookup, peer-IP verification, no redirects, and existing `maxMediaBytes`/timeout limits. Write final media only into `ai-drama-worker-media-*` with mode `0600`.

- [ ] **Step 4: Run green tests**

Run the Node and Python commands above. Expected: all Worker and isolation tests pass.

- [ ] **Step 5: Commit**

```bash
git add worker/src/media-helpers.mjs worker/src/worker.ts worker/src/worker.test.ts \
  tests/suppliers/test_worker_isolation.py
git commit -m "feat: add bounded supplier media helpers"
```

### Task 4: AIXORA Adapter Artifact And Offline Contract

**Files:**
- Create: `ai_drama_web/suppliers/custom_adapters/aixora.ts`
- Create: `tests/web/test_aixora_adapter.py`
- Modify: `ai_drama_web/suppliers/templates.py`

**Interfaces:**
- Exports `vendor`, `textRequest`, and `imageRequest` under `ai-drama-supplier-v1`.
- Uses only injected `helpers.http.request` and `helpers.media.decodeBase64`.
- Returns normalized text usage and bounded image media references.

- [ ] **Step 1: Write failing compile/contract tests**

Load the TypeScript artifact, compile it through `compile_supplier`, assert the exact five stable models and two config fields, and invoke it with a deterministic fake helper harness. Cover Responses `output_text`, canonical `output[].content[]`, reasoning selection, invalid effort, image URL, image base64, and multipart edits.

```python
assert [(m["providerModelName"], m["capability"]) for m in artifact.vendor["models"]] == [
    ("gpt-5.6-terra", "text"),
    ("gpt-5.6-sol", "text"),
    ("gpt-5.6-luna", "text"),
    ("gpt-5.5", "text"),
    ("gpt-image-2", "image"),
]
```

- [ ] **Step 2: Run red test**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_aixora_adapter.py
```

Expected: fail because the artifact does not exist.

- [ ] **Step 3: Implement the Chinese-commented adapter**

Use `/responses`, `/images/generations`, and `/images/edits` exactly as frozen in the design. Normalize the Base URL, reject invalid effort locally, send `stream:false` and `store:false`, accept URL or base64 image output, and never return credentials, authorization headers, raw provider bodies, or signed query values. Update the general template comments to point authors to the same bounded media helpers.

- [ ] **Step 4: Run green contract tests and compiler tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_aixora_adapter.py tests/web/test_supplier_compiler.py
```

Expected: all selected tests pass with network denied.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_web/suppliers/custom_adapters/aixora.ts \
  ai_drama_web/suppliers/templates.py tests/web/test_aixora_adapter.py
git commit -m "feat: add AIXORA GPT adapter artifact"
```

### Task 5: Verifier, Runtime Configuration, Real Acceptance, And Handoff

**Files:**
- Create: `tools/verify_aixora_adapter_model_archive.py`
- Create: `docs/superpowers/reports/2026-07-15-aixora-adapter-model-archive-verification.md`
- Runtime-only mutation: existing local AIXORA supplier, config, and model catalog; never committed.

**Interfaces:**
- Verifier emits `AIXORA_MODEL_ARCHIVE_PASS` and fake-only semantic checks.
- Runtime supplier retains its current credential version while source/config gain immutable revisions.

- [ ] **Step 1: Write verifier assertions before production configuration**

The verifier must check archive schema/API/resolver/UI contracts, exact manifest models, reasoning allowlist, both image paths, Worker isolation, fake-only transport denial, and regression commands. It must report real request counts as zero because it never performs real acceptance itself.

- [ ] **Step 2: Run full offline verification**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_model_level_provider_tests.py
python3 tools/verify_aixora_adapter_model_archive.py
python3 tools/verify_m6e_migration_acceptance.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: all suites and verifiers pass; all automated real request counts are zero.

- [ ] **Step 3: Save the adapter and config through local management contracts**

Read `ai_drama_web/suppliers/custom_adapters/aixora.ts`, obtain current supplier/config ETags from loopback APIs, save source and `{base_url:"https://www.aixora.store/v1", reasoning_effort:"medium"}`, preserve the existing credential version, and archive the existing failed-test overlay through DELETE. Do not print or rewrite the credential.

- [ ] **Step 4: Restart the feature runtime and validate local state**

Confirm the supplier exposes exactly the five manifest models, the old overlay is absent from normal lists but readable historically, model-test feature remains enabled only in the local feature service, and production M6 execution flag is unchanged.

- [ ] **Step 5: Execute the authorized real ledger without retries**

Through the model-level test contract, make one minimal text request for each approved text model and one `gpt-image-2` text-to-image request. Exercise one image-to-image request through the exact snapshot/gateway contract with a non-sensitive generated fixture and one input image. Record status, elapsed time, normalized usage/media metadata, and sanitized error codes. Never output or persist provider URLs in the report.

Expected successful minimum:

```text
REAL_TEXT_REQUEST_COUNT=4
REAL_TEXT_TO_IMAGE_REQUEST_COUNT=1
REAL_IMAGE_TO_IMAGE_REQUEST_COUNT=1
REAL_VIDEO_REQUEST_COUNT=0
```

The earlier Grok probe is reported separately:

```text
PREIMPLEMENTATION_GROK_TEXT_PROBE_COUNT=1
PREIMPLEMENTATION_GROK_RESULT=model_not_found
```

If AIXORA rejects `gpt-image-2` or `/images/edits`, stop that capability without retry, retain the sanitized evidence, and report the provider contract gap rather than inventing parameters.

- [ ] **Step 6: Write the sanitized verification report**

Include automated suite results, real ledger counts, exact successful model names, archive behavior, production flags, reviewer results, branch/commit, and rollback. Do not include credentials, signed URLs, runtime IDs that expose private artifacts, database files, or generated images.

- [ ] **Step 7: Perform independent read-only reviews**

Run specification/acceptance and architecture/technical/security reviews against the exact candidate commit. Fix blocker/high findings, rerun the full offline verification and any explicitly necessary real check without exceeding one call per ledger item, then append both verdicts to the report.

- [ ] **Step 8: Commit, push, and verify clean handoff**

```bash
git add tools/verify_aixora_adapter_model_archive.py \
  docs/superpowers/reports/2026-07-15-aixora-adapter-model-archive-verification.md
git commit -m "docs: verify AIXORA adapter and model archive"
git push -u origin feat/aixora-adapter-model-archive
git status --short
git diff --check HEAD^ HEAD
```

Expected: remote branch equals local HEAD, worktree is clean, and the final response follows `REVIEW_HANDOFF_READY`.
