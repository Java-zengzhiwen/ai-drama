# Agnes Video Input Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the standard single-image Agnes path, preserve strict keyframe semantics, handle live provider statuses, restore public asset delivery, and prove one product-level smoke test.

**Architecture:** Keep all reference asset IDs in the canonical generation request for audit, derive provider video input IDs from asset roles at execution time, and retain a strict provider-side validation boundary. Reuse the existing RuntimeStore, ProductStore, AssetDeliveryService, provider adapter, and poller.

**Tech Stack:** Python 3, FastAPI, SQLite, httpx/respx, pytest, FRP, nginx.

## Global Constraints

- Only the main agent writes files.
- Default tests make no real Agnes requests.
- Real polling uses the response `video_id` field through `/agnesapi`.
- Standard video accepts zero or one provider input image.
- Keyframes accept two or three explicitly ordered images.
- No schema expansion or provider abstraction rewrite.

---

### Task 1: Provider Contract

**Files:**
- Modify: `ai_drama_web/providers/agnes.py`
- Test: `tests/providers/test_agnes_video_submission.py`
- Test: `tests/providers/test_agnes_video_polling.py`

- [ ] Replace the invalid `std` multi-image test with a failing test proving no HTTP request occurs and `invalid_request` is raised.
- [ ] Add failing count validation tests for keyframes with zero, one, or four images.
- [ ] Add `pending -> submitted` to the polling parameterized test and verify it fails.
- [ ] Implement the minimum payload guards and status mapping.
- [ ] Run both provider test files to green.

### Task 2: Product Input Selection

**Files:**
- Modify: `ai_drama_web/services/generation_execution.py`
- Test: `tests/web/test_generation_execution_service.py`

- [ ] Add a failing test showing a standard request with scene and shot assets sends only the unique `shot_keyframe` URL.
- [ ] Add a failing test showing multiple `shot_keyframe` assets fail before Agnes submission.
- [ ] Filter provider input assets by type for standard mode, including old queued request objects.
- [ ] Keep the original `asset_ids` request field unchanged for audit and rerun behavior.
- [ ] Run generation execution tests to green.

### Task 3: Sanitized Failure Evidence

**Files:**
- Modify: `ai_drama_web/services/generation_execution.py`
- Modify: `ai_drama_web/store.py`
- Test: `tests/web/test_generation_execution_service.py`

- [ ] Add failing submit and refresh tests requiring a non-empty response object with provider diagnostics.
- [ ] Include API key, bearer token, secret field, and signed URL fixtures and assert their values are absent from persisted content.
- [ ] Implement one recursive persistence sanitizer and atomic response-object attachment on failure.
- [ ] Preserve the stable browser-facing error message.
- [ ] Run execution and store tests to green.

### Task 4: Public Asset Delivery

**Files:**
- No source changes expected.

- [ ] Start `ai-drama-web` from the inner repository root with the existing data root and explicit Agnes/public URL settings.
- [ ] Verify local `/api/health` is HTTP 200.
- [ ] Verify FRPC remains connected without restarting it.
- [ ] Generate a fresh signed shot-keyframe URL through `AssetDeliveryService`.
- [ ] Verify the public URL returns HTTP 200 and an image content type.

### Task 5: Regression And Authorized Smoke

**Files:**
- Update runtime evidence only; no tracked real-output artifacts.

- [ ] Run focused provider/execution/poller tests.
- [ ] Run M3 and M4 verifiers, full pytest, migration verification, Web tests/build/e2e, and `git diff --check`.
- [ ] Confirm no active queued real jobs before starting the Agnes runtime.
- [ ] Queue one standard single-`shot_keyframe` job through the product API.
- [ ] Verify submitted/polling/completed, provider `video_id`, downloaded MP4 bytes, local object/result IDs, local content URL, and no secret leakage.
- [ ] Report exact evidence and any remaining operational limitation.
