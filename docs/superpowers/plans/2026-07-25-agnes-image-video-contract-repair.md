# Agnes Image And Video Contract Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the existing Agnes Image 2.1 and Video V2.0 adapter so project-bound image and Shot video generation follow the current official contract, persist local media, and survive restart without duplicate submission.

**Architecture:** Keep the existing Agnes supplier, stable model IDs, M6 snapshots, durable image jobs, and video poller. Publish a new immutable built-in Supplier Version and Model Revision, extend provider-neutral image options with optional ratio support, and normalize the official `metadata.url` video result without changing historical snapshots.

**Tech Stack:** Python 3, FastAPI, SQLite/RuntimeStore, TypeScript supplier adapters, isolated Node Worker, React/TypeScript, Vitest, Playwright, pytest.

## Global Constraints

- Do not add an Agnes text model or a second Agnes supplier.
- Preserve the stable model IDs for `agnes-image-2.1-flash` and `agnes-video-v2.0`.
- Preserve historical Supplier Versions, Model Revisions, snapshots, Jobs, and results.
- Normal video accepts zero or one `shot_keyframe`; keyframes mode accepts two or three ordered keyframes.
- Poll and fetch new video jobs with `video_id`, never `task_id`.
- Image model tests require a user click; video has no model-row test.
- Automated work sends zero real provider requests.
- `M6_SUPPLIER_EXECUTION_ENABLED` remains false by default.
- Never commit credentials, databases, `runtime-data`, signed URLs, or provider media.

## File Map

- `ai_drama_web/suppliers/builtin_adapters.py`: Agnes manifest and request/response normalization.
- `ai_drama_web/suppliers/image_options.py`: safe size, ratio, and quality resolution.
- `ai_drama_web/suppliers/model_tests.py`: freeze image test options in request and snapshot.
- `ai_drama_web/schemas/model_tests.py`, `ai_drama_web/routers/model_tests.py`: model-test ratio API.
- `ai_drama_web/schemas/assets.py`: optional project image ratio.
- `web/src/features/suppliers/api.ts`, `ModelTestDialog.tsx`: manifest-driven image test controls.
- `tests/web/test_agnes_builtin_adapter.py`: fake-helper adapter contract tests.
- Existing image, video, model-test, poller, and frontend test files: regression and E2E coverage.
- `tools/verify_agnes_image_video_contract.py`: local semantic verifier.
- `docs/superpowers/reports/2026-07-25-agnes-image-video-contract-repair-verification.md`: final evidence.

---

### Task 1: Freeze the current Agnes adapter contract

**Files:**
- Create: `tests/web/test_agnes_builtin_adapter.py`
- Modify: `ai_drama_web/suppliers/builtin_adapters.py`
- Test: `tests/web/test_m6c_adapter_cutover.py`

**Interfaces:**
- Consumes: `compile_supplier` and existing `AGNES_SOURCE` exports.
- Produces: unchanged stable model IDs and corrected `imageRequest`, `videoSubmit`, `videoPoll`, `videoFetch`.

- [ ] **Step 1: Write failing fake-helper adapter tests**

Use the isolated VM harness pattern from `tests/web/test_aixora_adapter.py` and assert:

```python
def test_image_request_uses_tier_ratio_and_extra_body_image(artifact):
    result = invoke(artifact, "imageRequest", payload(request={
        "prompt": "frame", "size": "2K", "ratio": "16:9",
        "input_images": ["https://assets.example.test/reference.png"],
    }), [IMAGE_URL_RESPONSE, MEDIA_RESPONSE])
    assert result["calls"][0]["body"] == {
        "model": "agnes-image-2.1-flash", "prompt": "frame",
        "size": "2K", "ratio": "16:9",
        "extra_body": {
            "response_format": "url",
            "image": ["https://assets.example.test/reference.png"],
        },
    }

def test_video_fetch_reads_official_metadata_url(artifact):
    result = invoke(artifact, "videoFetch", video_payload("video-1"), [
        {"status": "completed", "metadata": {"url": OUTPUT_MP4}}, MEDIA_RESPONSE,
    ])
    assert result["calls"][0]["query"] == {"video_id": "video-1"}
    assert result["calls"][1]["url"] == OUTPUT_MP4
```

Also assert the manifest has only the existing two stable model IDs; `videoSubmit` extracts `video_id`; poll uses only `video_id`; unknown status returns `PROVIDER_STATUS_INVALID`.

- [ ] **Step 2: Run tests and verify red state**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_agnes_builtin_adapter.py
```

Expected: FAIL because the manifest lacks image constraints, requests omit `ratio`, and fetch omits `metadata.url`.

- [ ] **Step 3: Implement the minimal source revision**

Add strict values and official response order:

```ts
const IMAGE_SIZES = new Set(["1K", "2K", "3K", "4K", "1024x768", "1024x1024", "768x1024"]);
const IMAGE_RATIOS = new Set(["1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"]);
const url = raw.metadata?.url || raw.url || raw.video_url || raw.data?.url || raw.data?.video_url;
```

Read image `size` and `ratio` from request, then snapshot constraints, then model defaults. Reject invalid values before network. Keep `extra_body.response_format="url"` and place reference images only in `extra_body.image`. Increment Agnes manifest version only; keep IDs, provider names, helper version, and bucket stable.

- [ ] **Step 4: Run adapter and installer regression tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_agnes_builtin_adapter.py \
  tests/web/test_m6c_adapter_cutover.py -k 'builtin and (install or immutable or user_edited)'
```

Expected: PASS; built-in revisions advance immutably and user-edited current versions remain untouched.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_web/suppliers/builtin_adapters.py tests/web/test_agnes_builtin_adapter.py tests/web/test_m6c_adapter_cutover.py
git commit -m "fix: align Agnes adapters with current contracts"
```

### Task 2: Add provider-neutral image ratio resolution

**Files:**
- Modify: `ai_drama_web/suppliers/image_options.py`
- Modify: `ai_drama_web/suppliers/model_tests.py`
- Modify: `ai_drama_web/schemas/model_tests.py`
- Modify: `ai_drama_web/routers/model_tests.py`
- Modify: `tests/web/test_supplier_model_tests.py`

**Interfaces:**
- Consumes: `default_ratio` and `constraints.supported_ratios`.
- Produces: `resolve_image_options(...) -> {size, quality, ratio?}` and `create_model_test(..., ratio=None)`.

- [ ] **Step 1: Write failing resolution and persistence tests**

Revise a fake image model to:

```python
definition={
    "default_size": "1K", "default_ratio": "1:1",
    "constraints": {
        "supported_sizes": ["1K", "2K", "3K", "4K"],
        "supported_ratios": ["1:1", "16:9", "9:16"],
    },
}
```

Assert `ratio="16:9"` appears in the request object, snapshot constraints, and safe read. Assert `5:4` returns `INVALID_IMAGE_RATIO` before writing a run, and text models reject ratio as `MODEL_TEST_IMAGE_OPTIONS_UNSUPPORTED`.

- [ ] **Step 2: Run focused tests and verify red state**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py -k 'image and ratio'
```

- [ ] **Step 3: Implement optional ratio resolution**

```python
IMAGE_RATIOS = frozenset({"1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"})
declares_ratio = "default_ratio" in definition or "supported_ratios" in constraints
if "ratio" in request or declares_ratio:
    ratio = _first_present(request, "ratio", config, "image_ratio", definition, "default_ratio", fallback="1:1")
    _validate_ratio(ratio, constraints.get("supported_ratios"))
    result["ratio"] = ratio
```

Expand safe sizes with tiers and Agnes legacy exact sizes. Add optional ratio to schemas, router, service signature, request hash input, snapshot constraints, and safe read. Do not add ratio to Aixora snapshots unless its model declares it.

- [ ] **Step 4: Run all model-test backend tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py
```

Expected: PASS with existing Aixora size/quality behavior unchanged.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_web/suppliers/image_options.py ai_drama_web/suppliers/model_tests.py \
  ai_drama_web/schemas/model_tests.py ai_drama_web/routers/model_tests.py \
  tests/web/test_supplier_model_tests.py
git commit -m "feat: resolve manifest driven image ratios"
```

### Task 3: Expose Agnes image options in the model test dialog

**Files:**
- Modify: `web/src/features/suppliers/api.ts`
- Modify: `web/src/features/suppliers/api.test.ts`
- Modify: `web/src/features/suppliers/ModelTestDialog.tsx`
- Modify: `web/src/features/suppliers/ModelTestDialog.test.tsx`

**Interfaces:**
- Consumes: image constraints from the current Model Revision.
- Produces: one model-test POST with selected size and ratio; no video Test button.

- [ ] **Step 1: Write failing Agnes dialog tests**

```ts
expect(screen.getByRole("option", { name: "2K" })).toBeInTheDocument();
expect(screen.getByRole("option", { name: "16:9" })).toBeInTheDocument();
fireEvent.change(screen.getByLabelText("本次图片尺寸"), { target: { value: "2K" } });
fireEvent.change(screen.getByLabelText("本次画幅比例"), { target: { value: "16:9" } });
fireEvent.click(screen.getByRole("button", { name: "确认并测试" }));
expect(api.createModelTest).toHaveBeenCalledWith(
  model.supplier_model_id, expect.any(String),
  { size: "2K", ratio: "16:9" }, expect.any(String), expect.any(String),
);
```

Also verify session recovery retains both selections, the completed result shows actual ratio, and video still has no model-row test.

- [ ] **Step 2: Run frontend tests and verify red state**

```bash
npm --prefix web run test -- --run src/features/suppliers/ModelTestDialog.test.tsx \
  src/features/suppliers/api.test.ts src/features/suppliers/SupplierModelsPanel.test.tsx
```

- [ ] **Step 3: Implement manifest-driven controls**

Add `ImageSize` tiers and legacy sizes, `ImageRatio`, `ratio` in read/options/POST types, storage recovery, supported-value helpers, default resolution, a conditional ratio selector, and result detail. Render quality only when the model declares supported qualities.

- [ ] **Step 4: Run supplier tests and build**

```bash
npm --prefix web run test -- --run src/features/suppliers/ModelTestDialog.test.tsx \
  src/features/suppliers/api.test.ts src/features/suppliers/SupplierModelsPanel.test.tsx
npm --prefix web run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/suppliers/api.ts web/src/features/suppliers/api.test.ts \
  web/src/features/suppliers/ModelTestDialog.tsx web/src/features/suppliers/ModelTestDialog.test.tsx
git commit -m "feat: add Agnes image test options"
```

### Task 4: Propagate ratio through durable project image jobs

**Files:**
- Modify: `ai_drama_web/schemas/assets.py`
- Modify: `tests/web/test_asset_generation_api.py`
- Modify: `web/src/features/assets/api.ts`

**Interfaces:**
- Consumes: optional client `ratio`.
- Produces: durable image request containing ratio when supplied; unchanged legacy requests when omitted.

- [ ] **Step 1: Write failing project image tests**

Post a `shot_keyframe` request with `size="2K"` and `ratio="16:9"`. With supplier execution enabled and a fake gateway, assert the `imageRequest` payload and durable request object contain ratio and the final asset links to the image Job. Post the legacy payload without ratio and assert it remains accepted.

- [ ] **Step 2: Run tests and verify red state**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_asset_generation_api.py
```

Expected: FAIL because the request schema currently forbids ratio.

- [ ] **Step 3: Add only the optional request field**

```python
class AssetGenerateImageRequest(BaseModel):
    # existing fields
    ratio: str | None = None

    @field_validator("ratio")
    @classmethod
    def validate_optional_ratio(cls, value):
        return _not_blank(value) if value is not None else value
```

Add `ratio?: string` to the frontend request type. Do not redesign `AssetGenerator` or force it to send ratio; the model snapshot default applies when absent.

- [ ] **Step 4: Run image API and snapshot regression tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_asset_generation_api.py \
  tests/web/test_m6c_adapter_cutover.py -k 'image or snapshot or binding'
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_drama_web/schemas/assets.py tests/web/test_asset_generation_api.py web/src/features/assets/api.ts
git commit -m "feat: carry image ratio through project jobs"
```

### Task 5: Lock restart-safe official video completion

**Files:**
- Modify: `tests/web/test_generation_execution_service.py`
- Modify: `tests/web/test_generation_poller.py`
- Test: `tests/web/test_generation_job_service.py`
- Modify only if a red test proves necessary: `ai_drama_web/services/generation_execution.py`

**Interfaces:**
- Consumes: `videoPoll({video_id})` and `videoFetch({video_id})`.
- Produces: one local video result without a second submit.

- [ ] **Step 1: Write fake-gateway completion and restart tests**

Use deterministic responses:

```python
responses = {
    "videoSubmit": {"video_id": "video-official-1", "status": "queued"},
    "videoPoll": {"video_id": "video-official-1", "status": "completed"},
    "videoFetch": {
        "video_id": "video-official-1", "url": OUTPUT_MP4,
        "bytes": MP4_FIXTURE, "media_type": "video/mp4",
    },
}
```

Assert the exact operation sequence `videoSubmit`, `videoPoll`, `videoFetch`; poll/fetch payloads contain only the saved `video_id`; a fresh Poller instance finishes the submitted Job without another submit; and the result object contains the MP4 fixture.

- [ ] **Step 2: Run focused video tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_generation_execution_service.py \
  tests/web/test_generation_poller.py tests/web/test_generation_job_service.py
```

- [ ] **Step 3: Make only evidence-driven service corrections**

If a red test exposes a state-machine defect, preserve the existing call shape:

```python
fetched = self.supplier_gateway.invoke(
    job.snapshot_hash, "videoFetch", {"video_id": job.provider_job_id}
)
```

Do not add retries, alternate IDs, current-binding lookup, or resubmission.

- [ ] **Step 4: Rerun Task 5 tests**

Expected: PASS and submit count exactly one.

- [ ] **Step 5: Commit**

```bash
git add tests/web/test_generation_execution_service.py tests/web/test_generation_poller.py \
  tests/web/test_generation_job_service.py
test ! -n "$(git diff --name-only -- ai_drama_web/services/generation_execution.py)" || \
  git add ai_drama_web/services/generation_execution.py
git commit -m "test: lock Agnes video restart completion"
```

### Task 6: Add semantic verification and run the complete baseline

**Files:**
- Create: `tools/verify_agnes_image_video_contract.py`
- Create: `docs/superpowers/reports/2026-07-25-agnes-image-video-contract-repair-verification.md`

**Interfaces:**
- Consumes: compiled built-in source, fake adapter calls, existing verifiers, and test results.
- Produces: machine-readable local evidence with zero real requests.

- [ ] **Step 1: Write verifier checks**

Emit these semantic checks:

```text
AGNES-IV-001 stable supplier and model identity
AGNES-IV-002 image size and ratio contract
AGNES-IV-003 image-to-image extra_body contract
AGNES-IV-004 durable image result
AGNES-IV-005 video submit exactly once
AGNES-IV-006 poll and fetch by video_id
AGNES-IV-007 metadata.url result path
AGNES-IV-008 restart-safe completion
AGNES-IV-009 snapshot and legacy compatibility
AGNES-IV-010 image model-row test only
AGNES-IV-011 sanitized evidence
AGNES-IV-012 zero real provider requests
```

Use local fixtures and fake helpers only. Fail if verifier request counters are nonzero.

- [ ] **Step 2: Run complete verification**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_m3_agnes_generation.py
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m6c_adapter_cutover.py
python3 tools/verify_agnes_image_video_contract.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: PASS. Do not execute any historical real-smoke script.

- [ ] **Step 3: Run tracked secret and runtime-artifact checks**

```bash
test -z "$(git ls-files | rg '(^|/)(runtime-data|.*\.db)$')"
! git grep -n -I -E 'Bearer[[:space:]]+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{12,}' -- .
```

Expected: no secret or runtime artifact finding. If fixture text triggers a false positive, inspect it manually and narrow the scanner only to the explicit fixture path.

- [ ] **Step 4: Write the verification report**

Record exact commands, results, branch, commits, rollback point, and:

```text
IMPLEMENTATION_STARTED=true
PRODUCTION_FLAG_ENABLED=false
REAL_PROVIDER_REQUESTS=false
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

- [ ] **Step 5: Commit verifier and report**

```bash
git diff --check
git add tools/verify_agnes_image_video_contract.py \
  docs/superpowers/reports/2026-07-25-agnes-image-video-contract-repair-verification.md
git commit -m "docs: verify Agnes image video contract repair"
```

### Task 7: Review and publish

**Files:**
- Review all implementation commits and the verification report.

**Interfaces:**
- Consumes: exact final implementation HEAD.
- Produces: review-ready remote branch and PR/compare URL.

- [ ] **Step 1: Perform specification-compliance review**

Map every design acceptance key to a test or verifier check. Confirm no Agnes text model, second supplier, video model-row test, or real automated request was introduced.

- [ ] **Step 2: Perform technical/security review**

Inspect Worker network boundaries, credential injection, signed URL redaction, immutable revisions, snapshot routing, idempotency, media validation, submit count, restart behavior, and rollback.

- [ ] **Step 3: Fix blocker/high findings and rerun Task 6 Step 2**

Expected: all verification commands PASS.

- [ ] **Step 4: Push without rewriting history**

```bash
git push -u origin feat/agnes-image-video-contract-repair
```

- [ ] **Step 5: Prepare handoff**

Report branch, final commit, report path, PR/compare URL, `PRODUCTION_FLAG_ENABLED=false`, and zero real request counts. Do not merge to `main` without a separate explicit user request.
