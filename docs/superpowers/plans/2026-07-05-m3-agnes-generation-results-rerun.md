# Milestone 3 — Agnes Video Generation, Results, and Rerun Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Submit ready shots to Agnes Video, persist and recover asynchronous jobs, preview versioned results, normalize failures, and create explicit reruns without overwriting prior generations.

**Architecture:** Add generation-job/result tables to the product store, implement Agnes video request/poll/result calls behind `AgnesBackend`, add a single-process SQLite-backed poller, add controlled asset delivery for URL-only inputs, and expose generation/results/rerun APIs and Web tabs.

**Tech Stack:** FastAPI lifespan/background task, SQLite, HTTPX/RESpx, local object storage, signed temporary asset URLs, React Query polling, HTML5 video preview.

---

### Task 1: Add generation job and result persistence

**Files:**
- Modify: `ai_drama_web/models.py`
- Modify: `ai_drama_web/store.py`
- Create: `tests/web/test_generation_store.py`

- [ ] **Step 1: Write failing persistence/versioning tests**

Verify job creation, provider ID attachment, state transitions, result insertion, one selected result per shot, and rerun attempt increment.

- [ ] **Step 2: Add tables**

```sql
CREATE TABLE IF NOT EXISTS generation_jobs (
  job_id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  job_type TEXT NOT NULL CHECK (job_type IN ('image','video')),
  project_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL,
  shot_id TEXT NOT NULL DEFAULT '',
  prompt_revision_id TEXT NOT NULL DEFAULT '',
  provider_job_id TEXT NOT NULL DEFAULT '',
  provider_result_id TEXT NOT NULL DEFAULT '',
  internal_status TEXT NOT NULL CHECK (internal_status IN ('draft','queued','submitting','submitted','polling','completed','failed','cancelled')),
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  request_object_id TEXT NOT NULL,
  response_object_id TEXT NOT NULL DEFAULT '',
  attempt_number INTEGER NOT NULL,
  error_code TEXT NOT NULL DEFAULT '',
  error_message TEXT NOT NULL DEFAULT '',
  submitted_at TEXT NOT NULL DEFAULT '',
  next_poll_at TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(provider, idempotency_key)
);
CREATE TABLE IF NOT EXISTS generation_results (
  result_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
  chapter_id TEXT NOT NULL,
  shot_id TEXT NOT NULL,
  object_id TEXT NOT NULL,
  media_type TEXT NOT NULL,
  source_url TEXT NOT NULL,
  metadata_object_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shot_result_selections (
  chapter_id TEXT NOT NULL,
  shot_id TEXT NOT NULL,
  result_id TEXT NOT NULL REFERENCES generation_results(result_id) ON DELETE RESTRICT,
  selected_at TEXT NOT NULL,
  PRIMARY KEY(chapter_id, shot_id)
);
CREATE TABLE IF NOT EXISTS result_reviews (
  review_id TEXT PRIMARY KEY,
  result_id TEXT NOT NULL REFERENCES generation_results(result_id) ON DELETE RESTRICT,
  decision TEXT NOT NULL CHECK (decision IN ('passed','failed')),
  failure_category TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rerun_records (
  rerun_id TEXT PRIMARY KEY,
  source_job_id TEXT NOT NULL REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
  new_job_id TEXT NOT NULL REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
  overrides_object_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

- [ ] **Step 3: Enforce transitions**

```text
draft -> queued
queued -> submitting | cancelled
submitting -> submitted | failed
submitted -> polling | completed | failed
polling -> polling | completed | failed
failed/completed/cancelled -> terminal
```

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/web/test_generation_store.py -q
git add ai_drama_web tests/web/test_generation_store.py
git commit -m "feat: persist generation jobs and results"
```

### Task 2: Implement controlled temporary asset delivery

**Files:**
- Create: `ai_drama_web/services/asset_delivery.py`
- Create: `ai_drama_web/routers/asset_delivery.py`
- Modify: `ai_drama_web/config.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_asset_delivery.py`

- [ ] **Step 1: Write failing signature/expiry tests**

Verify valid fetch, altered asset rejection, expiry rejection, and non-image rejection.

- [ ] **Step 2: Implement HMAC signature**

```python
hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
```

Use `hmac.compare_digest()`.

- [ ] **Step 3: Add route**

```text
GET /public/assets/{asset_id}?expires=...&signature=...
```

Use `AI_DRAMA_PUBLIC_BASE_URL`; reject localhost for Agnes video submissions. Read the API key only through `LocalSecretStore` created in Milestone 2; never accept a key in generation request bodies.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/web/test_asset_delivery.py -q
git add ai_drama_web tests/web/test_asset_delivery.py
git commit -m "feat: add signed asset delivery urls"
```

### Task 3: Implement Agnes video submission

**Files:**
- Modify: `ai_drama_web/providers/agnes.py`
- Create: `tests/providers/test_agnes_video_submission.py`

- [ ] **Step 1: Write mocked contract tests**

At implementation time verify current official endpoint/payload. Assert model `agnes-video-v2.0`, signed image URLs, duration/prompt preservation, returned `video_id` as provider job ID, and `task_id` only in raw metadata.

- [ ] **Step 2: Implement submission**

```python
ProviderJob(provider_job_id=video_id, status="submitted", raw=response_json)
```

Raise typed contract error if `video_id` is absent.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m pytest tests/providers/test_agnes_video_submission.py -q
git add ai_drama_web/providers tests/providers/test_agnes_video_submission.py
git commit -m "feat: submit agnes video jobs"
```

### Task 4: Implement Agnes polling and result fetch

**Files:**
- Modify: `ai_drama_web/providers/agnes.py`
- Create: `tests/providers/test_agnes_video_polling.py`

- [ ] **Step 1: Write mocked polling tests**

Cover queued, processing, completed, failed, malformed response, 429, timeout, and expired result URL.

- [ ] **Step 2: Query by `video_id` and normalize**

```text
submitted
polling
completed
failed
```

- [ ] **Step 3: Implement `fetch_result()`**

Return provider URL and raw metadata; application service downloads exact bytes.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/providers/test_agnes_video_polling.py -q
git add ai_drama_web/providers tests/providers/test_agnes_video_polling.py
git commit -m "feat: poll and fetch agnes videos"
```

### Task 5: Add idempotent GenerationJobService

**Files:**
- Create: `ai_drama_web/services/generation_jobs.py`
- Create: `tests/web/test_generation_job_service.py`

- [ ] **Step 1: Write duplicate-submission tests**

Same chapter/shot/prompt/request hash/idempotency key returns same job; explicit rerun creates attempt 2.

- [ ] **Step 2: Implement canonical request hash**

```python
json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
```

- [ ] **Step 3: Implement queue validation**

Require ready prompt, usable assets, provider-reachable signed URL, and unique idempotency key. Persist `queued` before return.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/web/test_generation_job_service.py -q
git add ai_drama_web tests/web/test_generation_job_service.py
git commit -m "feat: add idempotent generation job service"
```

### Task 6: Add persistent single-process poller

**Files:**
- Create: `ai_drama_web/jobs/poller.py`
- Create: `ai_drama_web/jobs/rate_limit.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/integration/test_generation_recovery.py`
- Create: `tests/integration/test_generation_rate_limit.py`

- [ ] **Step 1: Write restart recovery test**

Create queued/submitted/polling jobs, restart app on same data root, run one cycle, and verify no duplicate submission.

- [ ] **Step 2: Implement configurable limiter**

```text
AI_DRAMA_AGNES_VIDEO_RPM
AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS
```

Default video submission: one token per 60 seconds.

- [ ] **Step 3: Implement cycles**

```python
async def submit_due_jobs(context) -> int: ...
async def poll_due_jobs(context) -> int: ...
async def run_one_cycle(context) -> dict[str, int]: ...
```

Persist `submitting` before network call. Recover `submitting` using saved provider ID; otherwise fail with `submission_outcome_unknown` instead of blind resubmit.

- [ ] **Step 4: Start via FastAPI lifespan, verify, commit**

```bash
python3 -m pytest tests/integration/test_generation_recovery.py tests/integration/test_generation_rate_limit.py -q
git add ai_drama_web tests/integration
git commit -m "feat: add persistent agnes job poller"
```

### Task 7: Add result persistence and selection

**Files:**
- Create: `ai_drama_web/services/results.py`
- Create: `tests/web/test_results_service.py`

- [ ] **Step 1: Write tests**

Verify download persistence, old result retention, one selection per shot, provider error mapping, and expired URL handling.

- [ ] **Step 2: Normalize provider errors**

```text
authentication
rate_limited
invalid_request
input_unreachable
provider_busy
generation_failed
timeout
result_expired
unknown_provider_error
submission_outcome_unknown
```

- [ ] **Step 3: Implement selection and verify**

Selection updates only `shot_result_selections`; never delete prior results.

```bash
python3 -m pytest tests/web/test_results_service.py -q
git add ai_drama_web tests/web/test_results_service.py
git commit -m "feat: persist and select generation results"
```

### Task 8: Add rerun workflow

**Files:**
- Create: `ai_drama_web/services/reruns.py`
- Create: `tests/web/test_rerun_service.py`

- [ ] **Step 1: Write rerun tests**

Change prompt, negative prompt, assets, mode, and duration; create new job and keep source job/result unchanged.

- [ ] **Step 2: Implement rerun record**

Save override JSON and create `RerunRecord(source_job_id, new_job_id, overrides_object_id)`.

- [ ] **Step 3: Verify and commit**

```bash
python3 -m pytest tests/web/test_rerun_service.py -q
git add ai_drama_web tests/web/test_rerun_service.py
git commit -m "feat: add immutable video reruns"
```

### Task 9: Add generation/results APIs

**Files:**
- Create: `ai_drama_web/schemas/generation.py`
- Create: `ai_drama_web/routers/generation.py`
- Create: `ai_drama_web/routers/results.py`
- Modify: `ai_drama_web/app.py`
- Create: `tests/web/test_generation_api.py`

- [ ] **Step 1: Write endpoint tests**

Cover batch submit, list, refresh, results, select, persisted result review category, and rerun.

- [ ] **Step 2: Add routes**

```text
POST /api/chapters/{chapter_id}/generation/video-jobs
GET  /api/chapters/{chapter_id}/generation/jobs
GET  /api/generation/jobs/{job_id}
POST /api/generation/jobs/{job_id}/refresh
GET  /api/chapters/{chapter_id}/results
POST /api/shots/{shot_id}/results/{result_id}/select
POST /api/results/{result_id}/review
POST /api/generation/jobs/{job_id}/rerun
```

- [ ] **Step 3: Map UI states and verify**

```text
draft/queued -> waiting
submitting/submitted/polling -> generating
completed -> success
failed/cancelled -> failed
```

```bash
python3 -m pytest tests/web/test_generation_api.py -q
git add ai_drama_web tests/web/test_generation_api.py
git commit -m "feat: expose generation result and rerun api"
```

### Task 10: Implement Generation UI

**Files:**
- Create: `web/src/features/generation/GenerationTab.tsx`
- Create: `web/src/features/generation/ShotGenerationTable.tsx`
- Create: `web/src/features/generation/api.ts`
- Create: `web/src/features/generation/GenerationTab.test.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`

- [ ] **Step 1: Write UI tests**

Test ready selection, batch submission, overrides, statuses, refresh, and duplicate-click protection.

- [ ] **Step 2: Implement React Query polling**

Poll every five seconds only while a nonterminal job exists.

- [ ] **Step 3: Verify and commit**

```bash
npm --prefix web run test -- --run
git add web/src
git commit -m "feat: add agnes generation workspace"
```

### Task 11: Implement Results and Rerun UI

**Files:**
- Create: `web/src/features/results/ResultsTab.tsx`
- Create: `web/src/features/results/VideoResultCard.tsx`
- Create: `web/src/features/results/RerunDrawer.tsx`
- Create: `web/src/features/results/api.ts`
- Create: `web/src/features/results/ResultsTab.test.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`

- [ ] **Step 1: Write UI tests**

Test preview, version history, selection, failure category, source inputs, rerun, and prior-version retention.

- [ ] **Step 2: Implement result cards and rerun drawer**

Do not autoplay. Prepopulate exact source job inputs and permit only approved override fields.

- [ ] **Step 3: Verify and commit**

```bash
npm --prefix web run test -- --run
git add web/src
git commit -m "feat: add video results and rerun ui"
```

### Task 12: Add Milestone 3 verification

**Files:**
- Create: `tools/verify_m3_agnes_generation.py`
- Create: `web/tests/m3-generation-results.spec.ts`
- Modify: `README.md`

- [ ] **Step 1: Add fake-provider verifier**

Test submit, poll, complete, selection, failure, rerun, and restart recovery. Extend chapter status derivation through `videos_generating`, `videos_ready`, and `needs_rerun`. Print `M3_AGNES_GENERATION_PASS`.

- [ ] **Step 2: Add browser flow**

Submit two shots, complete one, fail one, select completed result, and rerun failed shot.

- [ ] **Step 3: Run gate and commit**

```bash
python3 tools/verify_m3_agnes_generation.py
python3 migration/tools/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
git add tools web/tests README.md
git commit -m "test: verify agnes generation milestone"
```
