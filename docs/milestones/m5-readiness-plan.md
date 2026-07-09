# M5 Readiness Plan

## Purpose

M5 does not mean full production launch.

M5 means one explicitly authorized real Agnes smoke test can be run safely,
inspected, persisted, reported, and reviewed.

This readiness plan prepares the checklist, gate, scenario, evidence model,
failure taxonomy, and operator decision template for that future smoke test. It
does not execute the smoke test, configure a real API key, modify provider
execution code, modify UI, add backend APIs, or expand the database schema.

`M5_READINESS_PLAN_READY_FOR_REVIEW` does not authorize real provider
execution. A real Agnes request still requires a separate user message that
contains exactly:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

## M5 Scope

M5 readiness covers:

- real provider readiness checklist;
- public HTTPS asset delivery readiness;
- Agnes API key readiness;
- runtime provider switching readiness;
- signed asset URL reachability check;
- dry-run safety verification;
- one-shot real smoke-test gate design;
- expected success evidence;
- failure classification;
- rollback and cleanup guidance;
- report separation between mock evidence and real provider evidence.

The readiness stage may prepare a future smoke-test plan. It must not run the
real smoke test until the user separately authorizes it.

## Non-Scope

M5 readiness does not include:

- no automatic real Agnes request without authorization;
- no batch production;
- no full chapter production;
- no video quality benchmark;
- no LibTV execution;
- no subtitles / BGM / final timeline export;
- no provider abstraction rewrite;
- no database schema expansion unless separately approved later;
- no production launch;
- no frontend UI modification in this planning task;
- no new backend API in this planning task;
- no real smoke-test execution code in this planning task.

## Current Baseline

Repository baseline:

- Active milestone: M5, Real Provider Readiness and Agnes Smoke Test.
- Historical baseline: M3 and M4 are complete and must not regress.
- `main` and `origin/main` were updated to
  `158cd44316094db8bc0bc88a321bb89ed966e0c6`, which includes M5 governance.
  The original task expected `6c79dc83a57fe45d2a870bb578903c4588c8c4cd`; the
  current authoritative repository state is the newer `origin/main`.
- The requested `docs/milestones/m3-real-provider-readiness.md` path does not
  exist in the current tree. The current M3 real-provider readiness document is
  `docs/m3-real-provider-readiness.md` and was used as the M3 readiness
  baseline.

Implementation baseline:

- `AI_DRAMA_RUNTIME_PROVIDER` defaults to `mock`.
- Agnes backend wiring requires `AI_DRAMA_RUNTIME_PROVIDER=agnes` and an Agnes
  API key in `LocalSecretStore`.
- `LocalSecretStore` stores the key outside git-tracked files and the settings
  endpoint returns only configured status plus a masked suffix.
- `AssetDeliveryService` generates signed asset URLs, rejects invalid
  signatures, rejects expired signatures, rejects non-image assets, and rejects
  non-provider-reachable public base URLs.
- Generation request records persist `asset_ids`, not temporary signed URLs.
  Signed URLs are materialized only at provider submission time.
- Duration mapping is explicit: `5s -> 121 frames at 24 fps` and
  `10s -> 241 frames at 24 fps`.
- Provider submission requires `video_id` from Agnes and does not silently use
  `task_id` as the submitted provider job id.
- Result bytes are downloaded and persisted locally before the local content
  endpoint serves them.
- The poller handles queued, submitting, submitted, polling, completed, failed,
  cancelled, and `submission_outcome_unknown` paths.
- M4 rehearsal remains mock-provider only and reports
  `real_agnes_request_made = false`.
- M4.3 visibility panel is read-only and labels mock rehearsal separately from
  real provider validation.

Official Agnes Video V2.0 documentation snapshot:

- Model: `agnes-video-v2.0`.
- Create task: `POST https://apihub.agnes-ai.com/v1/videos`.
- Recommended result query:
  `GET https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>`.
- Image-to-video requires publicly accessible image URLs.
- `num_frames` must follow the `8n + 1` rule and be `<= 441`.

This documentation snapshot must be rechecked immediately before any real smoke
test implementation or execution. A conflict with current implementation is a
NO-GO until reviewed.

## Multi-Agent Review

### Product Agent

Findings:

- M5 product goal is not launch. It is one explicitly authorized real Agnes
  smoke test that can be submitted, inspected, persisted, reported, and
  reviewed.
- User acceptance requires a reviewed readiness plan, dry-run verification,
  explicit smoke-test authorization, evidence separation, and no secret leakage.
- A passed real smoke test means a single short job reaches a classified
  terminal outcome and leaves inspectable evidence.

Risks:

- Operators may confuse M4 mock rehearsal evidence with M5 real provider
  evidence.
- A READY planning decision may be misread as execution authorization.
- Full chapter production may be attempted before the single-shot smoke gate is
  proven.

Required checklist items:

- State that M5 is not production launch.
- State that readiness READY does not authorize execution.
- Require report sections for mock M4 evidence and real M5 evidence.
- Require user review of this plan before any real smoke test.

Go / no-go criteria:

- GO for planning review only when the document contains all required sections.
- NO-GO for real execution unless the plan is accepted, all checklist groups are
  GO, and the user sends the exact authorization token.

### Backend Agent

Findings:

- Agnes video provider has explicit submit, status, result download, status
  normalization, and raw-response sanitization paths.
- Asset delivery validates public base URL shape and produces signed HTTPS
  asset URLs.
- Canonical generation request persistence stores `asset_ids`; temporary signed
  URLs are produced at submission time.
- Provider parameter surface is narrow. Rerun allows only `mode` and `seed` in
  addition to canonical frame timing.
- Duration mapping is implemented as `5 -> 121/24` and `10 -> 241/24`.
- Local result bytes are persisted and exposed through
  `/api/results/{result_id}/content`.

Risks:

- App startup starts the poller when an Agnes backend exists. If a real key is
  configured and queued Agnes jobs already exist, startup can submit work.
- Provider output URL and provider metadata are persisted for audit and should
  be treated as temporary provider evidence, not public distribution URLs.
- Broad submit exceptions become `unknown_provider_error`, which is safe for
  users but can reduce operator diagnostics.
- Current provider contract must be compared with the latest official Agnes
  documentation before GO.

Required checklist items:

- Confirm no pre-existing queued Agnes jobs before enabling the real provider.
- Confirm provider payload uses fresh signed URLs and strict allowlisted fields.
- Confirm provider response metadata is sanitized.
- Confirm result bytes persist locally and local content endpoint works.
- Confirm canonical request object contains `asset_ids` and no signed URL query
  parameters.

Go / no-go criteria:

- GO only if provider contract, timing, payload, result persistence, poller, and
  content endpoint checks pass.
- NO-GO if provider docs conflict, queued jobs could auto-submit, asset URLs are
  persisted in canonical requests, result persistence fails, or the user has not
  authorized the real request.

### Ops Agent

Findings:

- Required environment variables are documented:
  `AI_DRAMA_RUNTIME_PROVIDER=agnes`, `AI_DRAMA_PUBLIC_BASE_URL`,
  `AI_DRAMA_AGNES_VIDEO_RPM`, and `AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS`.
- Defaults are `mock`, empty public base URL, RPM `1`, and poll interval `5.0`.
- Public base URL validation rejects non-HTTPS, userinfo, localhost, loopback,
  private IP, link-local, reserved, and unspecified IP hosts.
- Validation is syntactic and IP-safety oriented; it does not prove actual
  external reachability from Agnes.

Risks:

- A syntactically valid HTTPS URL may still be unreachable by Agnes.
- Positive RPM/poll interval validation is not enough for operational sanity.
- Real-provider cleanup after partial submit, timeout, or failed download is not
  yet a dedicated runbook.

Required checklist items:

- Explicitly set and record provider env values before smoke.
- Use `AI_DRAMA_AGNES_VIDEO_RPM=1` for the one-shot smoke.
- Use `AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS=5` unless separately approved.
- Verify the signed image URL from an external network before submission.
- Define cleanup for queued, submitting, submitted, completed, failed,
  cancelled, and unknown-outcome jobs.

Go / no-go criteria:

- GO only if environment, public URL, rate limits, poll interval, reachability,
  and cleanup ownership are all accepted.
- NO-GO if public base URL is missing, invalid, not externally reachable, or
  operator cleanup rules are unclear.

### QA Agent

Findings:

- M3 verifier uses a fake video backend and prints `M3_AGNES_GENERATION_PASS`.
- M4 verifier uses a mock rehearsal backend, writes reports, and records
  `real_agnes_request_made = false`.
- Default Agnes provider tests use mocked HTTP through `respx`.
- Migration verifier is file/hash validation.
- Full pytest can generate `runtime-data/reports` through M4 tool tests.

Risks:

- Running the full suite may create runtime report artifacts that must not be
  confused with source changes.
- Failure category coverage is broader in M5 than M4's current mock rehearsal
  coverage.
- Default tests are mock-safe, but inherited real provider env must be
  controlled before regression runs.

Required checklist items:

- Run M3 verifier, M4 verifier, pytest, web tests, web build, web e2e, migration
  verifier, and `git diff --check` before real execution.
- For this docs-only task, run focused document validation, safety grep,
  `git diff --check`, status, and changed-file checks.
- Confirm default tests and CI do not call real Agnes.
- Require a failure-category matrix for all M5 categories.

Go / no-go criteria:

- GO for planning if document validation and single-file diff checks pass.
- GO for smoke only if full baseline passes immediately before execution.
- NO-GO if any default verification path can make a real provider request.

### Security Agent

Findings:

- `LocalSecretStore` stores the Agnes key outside git-tracked files with `0600`
  file permissions.
- `/api/settings/agnes` returns configured/unconfigured status and a masked
  suffix only.
- Provider raw metadata sanitizes authorization, API-key-like, token-like, and
  secret-like fields.
- Signed asset URLs use HMAC and constant-time signature comparison.
- Safety grep hits are expected in docs, current provider implementation,
  settings paths, test mocks/assertions, and deferred-token UI copy.

Risks:

- Provider result URLs and signed asset URLs should be treated as temporary
  operational evidence and redacted from public artifacts where needed.
- A real API key must never be pasted into command output, reports, browser
  responses, exceptions, test snapshots, or git history.
- Binary `__pycache__` files can match grep patterns but are not source
  evidence.

Required checklist items:

- Confirm API key exists in `LocalSecretStore` without printing the key.
- Confirm settings endpoint does not return the key.
- Confirm signed URL does not contain Agnes API key.
- Confirm reports redact secrets and distinguish signed asset URLs from
  provider credentials.
- Run safety grep and classify allowed versus disallowed hits.

Go / no-go criteria:

- GO only if no secret value is exposed and safety grep finds no new unguarded
  real provider path.
- NO-GO if a key appears in browser payloads, logs, reports, artifacts,
  exceptions, snapshots, or git history.

### Orchestrator

Findings:

- M5 readiness can be reviewed as a documentation artifact.
- Current implementation appears capable of one controlled real-provider smoke
  path, but the real smoke test is not ready until environment, secret, public
  reachability, safety, and full verification are all GO.
- The automatic poller startup risk is the strongest operational gate: before
  any future real-provider window, the operator must prove that only the
  authorized smoke job can submit.

Risks:

- Starting an Agnes-configured app with queued jobs could submit more than the
  intended one-shot request.
- Official Agnes API details can change and must be rechecked before execution.
- Mock evidence may be overstated as real-provider evidence.

Required checklist items:

- Keep this plan as the review artifact.
- Do not run any real Agnes request during planning.
- Before future execution, rerun full baseline and recheck official Agnes docs.
- Require a single authorized job, explicit idempotency key, and no pre-existing
  queued Agnes jobs.

Go / no-go criteria:

- Planning decision: ready for review if this document validates and is the only
  source change.
- Real smoke decision: NOT READY until all future checklist groups are GO and
  the user sends the exact authorization token.

## Readiness Checklist

### Repository readiness

- [ ] `main` is clean before creating the smoke-test execution branch.
- [ ] M3 verifier passes:
  `python3 tools/verify_m3_agnes_generation.py`.
- [ ] M4 verifier passes:
  `python3 tools/verify_m4_chapter_rehearsal.py`.
- [ ] Python tests pass: `python3 -m pytest -q`.
- [ ] Web tests pass: `npm --prefix web run test -- --run`.
- [ ] Web build passes: `npm --prefix web run build`.
- [ ] Web e2e passes: `npm --prefix web run test:e2e`.
- [ ] Migration verifier passes:
  `python3 migration/tools/verify_migration.py`.
- [ ] `git diff --check` passes.
- [ ] Default verification environment has `AI_DRAMA_RUNTIME_PROVIDER` unset or
  set to `mock`, except for explicitly scoped real-provider preflight.
- [ ] No default test or CI path calls real Agnes.

### Environment readiness

- [ ] `AI_DRAMA_RUNTIME_PROVIDER=agnes`.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` configured.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` uses HTTPS.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` is not localhost.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` is not loopback.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` is not private IP.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` is not link-local, reserved, or unspecified IP.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` is not a file path.
- [ ] `AI_DRAMA_PUBLIC_BASE_URL` has no userinfo.
- [ ] `AI_DRAMA_AGNES_VIDEO_RPM` is explicitly set and sane; recommended smoke
  value: `1`.
- [ ] `AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS` is explicitly set and sane;
  recommended smoke value: `5`.
- [ ] Official Agnes docs have been rechecked for endpoint, request, status, and
  result contract.

### Secret readiness

- [ ] Agnes API key exists in `LocalSecretStore`.
- [ ] Key presence is checked without printing the key.
- [ ] Key is not committed.
- [ ] Key is not stored in `.env`, scripts, README, snapshots, reports, or git
  history.
- [ ] Key is not returned to browser.
- [ ] `/api/settings/agnes` exposes configured/unconfigured status only, plus a
  masked suffix when configured.
- [ ] Logs and reports redact Authorization headers and API-key-like fields.
- [ ] Provider raw metadata contains no key or bearer token.

### Public asset readiness

- [ ] One existing usable image asset is selected.
- [ ] Signed asset URL is generated.
- [ ] Signed asset URL is HTTPS.
- [ ] Invalid signature is rejected.
- [ ] Expired signature is rejected.
- [ ] Non-image asset is rejected.
- [ ] Signed URL does not contain Agnes API key.
- [ ] Signed URL is externally reachable before submission.
- [ ] Provider-unreachable URLs are rejected.
- [ ] The readiness report records the reachability result without exposing
  secrets.

### Provider readiness

- [ ] Explicit video submit endpoint is used only after authorization.
- [ ] Explicit video status/result path is used.
- [ ] `video_id` is required and is not silently replaced by `task_id`.
- [ ] Duration mapping: `5s -> 121 frames at 24 fps`.
- [ ] Duration mapping: `10s -> 241 frames at 24 fps`.
- [ ] `num_frames` follows the Agnes `8n + 1` rule.
- [ ] Provider params allowlist remains strict.
- [ ] Canonical request stores asset IDs, not temporary signed URLs.
- [ ] Provider payload uses fresh signed URLs at submit time.
- [ ] Local result persistence is enabled.
- [ ] Provider result bytes are downloaded and stored locally.
- [ ] Previous result versions are retained.
- [ ] Current result selection is explicit.
- [ ] Poller handles queued, submitting, submitted, polling, completed, failed,
  cancelled, and `submission_outcome_unknown`.
- [ ] No pre-existing queued Agnes jobs can auto-submit when provider is enabled.

### Safety readiness

- [ ] Dry-run mode makes no real Agnes request.
- [ ] Real smoke test requires exact token:
  `AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST`.
- [ ] No retries beyond approved single smoke request.
- [ ] No default test calls real Agnes.
- [ ] No CI job calls real Agnes by default.
- [ ] No API key leakage.
- [ ] Mock M4 evidence is separated from real M5 smoke-test evidence.
- [ ] Safety grep has been run and reviewed.
- [ ] Report explicitly states whether a real Agnes request was made.

## Environment Requirements

Use explicit runtime configuration outside git-tracked files:

```bash
AI_DRAMA_RUNTIME_PROVIDER=agnes
AI_DRAMA_PUBLIC_BASE_URL=https://<provider-reachable-domain>
AI_DRAMA_AGNES_VIDEO_RPM=1
AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS=5
```

Before real execution, record only the presence and non-secret shape of these
values:

- provider value equals `agnes`;
- public base URL host and scheme are acceptable;
- RPM is `1` unless separately approved;
- poll interval is positive and sane, recommended `5`;
- no API key value is printed.

## Secret Management

The Agnes API key must be configured through `LocalSecretStore` or the existing
`/api/settings/agnes` endpoint. The real key must never be stored in git-tracked
files or printed in command output.

Allowed checks:

- call `GET /api/settings/agnes` and record `configured: true` or `false`;
- inspect that the secret file exists without printing its contents;
- confirm permissions are owner-only where applicable;
- confirm provider metadata and reports redact key-like fields.

Forbidden checks:

- echoing the key;
- adding the key to `.env`, scripts, docs, reports, snapshots, exceptions, or
  git history;
- returning the full key to browser;
- accepting the key in generation request bodies.

## Public Asset Delivery Requirements

The real smoke test requires one existing usable image asset. Before submission:

1. Generate a fresh signed asset URL.
2. Confirm the URL is HTTPS.
3. Confirm the URL host is not localhost, loopback, private, link-local,
   reserved, unspecified, file-based, or userinfo-bearing.
4. Confirm invalid signatures fail.
5. Confirm expired signatures fail.
6. Confirm non-image assets fail.
7. Confirm the URL does not contain an Agnes API key.
8. Confirm the URL is externally reachable from a network path that approximates
   provider reachability.

If external reachability cannot be proven, the smoke test is NO-GO.

## Real Agnes Smoke Test Gate

No real Agnes request may be made unless the user explicitly sends:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

The readiness plan may conclude READY, but READY still does not execute the
smoke test. The real smoke test needs a separate user authorization message.

The token authorizes at most one controlled real Agnes smoke request, and only
after all readiness categories are GO. If a new provider submission is needed
after a failure, the operator must request explicit user authorization again
unless a later approved smoke-test plan says otherwise.

## Smoke Test Scenario

Input:

- one existing usable image asset;
- one short video generation job;
- `duration_seconds = 5`;
- `provider = agnes`;
- one idempotency key;
- one shot id.

Expected flow:

1. Create signed asset URL.
2. Verify signed asset URL is externally reachable.
3. Submit Agnes video request.
4. Receive provider job/video id.
5. Persist internal generation job id.
6. Poll provider status.
7. Receive completed URL or failed status.
8. Download mp4 if completed.
9. Persist local result bytes.
10. Persist result metadata.
11. Expose `/api/results/{result_id}/content`.
12. Show result in existing generation results UI.
13. Show evidence in M4.3 visibility panel or its existing generation visibility
    surfaces without changing UI in this planning task.
14. Write smoke test report.

The scenario is intentionally one shot and one request. It is not a batch, full
chapter, quality benchmark, or production export.

## Expected Success Evidence

A successful real smoke test should leave:

- provider job id / video id;
- internal generation job id;
- result id;
- local object id;
- local content URL;
- poll status timeline;
- downloaded mp4 byte size;
- result selection state;
- no secret leakage confirmation;
- report path;
- UI visibility confirmation;
- explicit statement that this was a single authorized real provider smoke test.

The report must contain separate sections for:

- mock M4 rehearsal evidence;
- real M5 smoke-test evidence.

Mock evidence must never be presented as real provider validation.

## Failure Categories

Default rule: any new real provider submission requires explicit user
authorization again unless the approved smoke-test plan says otherwise.

| Category | Meaning | Operator action | Retry allowed? | Fresh authorization required? |
| --- | --- | --- | --- | --- |
| `missing_api_key` | `LocalSecretStore` has no Agnes key or backend cannot load it. | Configure the key through approved settings flow without printing it; rerun secret readiness. | No provider retry; no request was made. | Yes before any later real submission. |
| `invalid_public_base_url` | Public base URL is missing, non-HTTPS, localhost, loopback, private, file-based, userinfo-bearing, or otherwise invalid. | Fix public HTTPS hosting; rerun URL and signed asset checks. | No provider retry; no request was made. | Yes before any later real submission. |
| `input_asset_unreachable` | Signed asset URL cannot be reached by provider-like external network or asset serving rejects it. | Fix hosting, asset status, media type, signature, or TTL; regenerate signed URL. | No provider retry until fixed. | Yes before any later real submission. |
| `provider_submit_failed` | Agnes submit request returned authentication, rate limit, invalid request, busy, timeout, or unknown submit error. | Record sanitized response; check key, payload, endpoint, rate limit, and official docs. | No automatic retry. | Yes for another submission. |
| `provider_poll_failed` | Status polling failed due network, timeout, malformed response, or provider error. | Preserve provider id; record timeline; inspect sanitized status response. | Poll-only retry may be allowed if it does not submit a new job and operator approves. | Required only if a new submission is made. |
| `provider_failed` | Provider returned a terminal failed status. | Record provider failure response; classify provider code if available; do not resubmit automatically. | No automatic retry. | Yes for another submission. |
| `provider_timeout` | Submit, poll, or download exceeded timeout. | Record phase and timeout; decide whether existing provider id can be polled without new submission. | Poll-only retry may be allowed for an existing job; no submit retry. | Required for another submission. |
| `result_download_failed` | Completed provider result URL cannot be downloaded, expired, empty, non-video, or unavailable. | Preserve provider id and URL state in sanitized report; check if provider offers a still-valid result URL. | Download retry may be allowed for same result URL if no new submission occurs. | Required for another submission. |
| `local_persistence_failed` | Result bytes or metadata could not be written locally. | Stop; preserve sanitized provider state; inspect local storage and runtime store. | No provider retry until persistence is fixed. | Required for another submission. |
| `ui_visibility_failed` | Persisted result is not visible through existing results UI or M4.3 visibility surfaces. | Keep local result evidence; inspect API/UI data mapping; do not resubmit. | Not a provider retry. | Not required unless another provider submission is made. |
| `secret_leak_detected` | Key, bearer token, or secret-like value appears in browser, logs, report, artifact, exception, snapshot, or git history. | Stop immediately; rotate key; remove artifact; report incident; do not proceed. | No. | Yes, after remediation and review. |
| `unexpected_real_request` | Any real Agnes request happened without the exact authorization token or outside the approved single request. | Stop immediately; preserve audit trail; report incident; do not continue. | No. | Yes, after governance review. |
| `unknown` | Failure cannot be classified with available sanitized evidence. | Stop; capture non-secret diagnostics; classify before retry. | No automatic retry. | Yes for another submission. |

## Safety Rules

- No real Agnes request before the exact authorization token.
- No real request from this planning branch.
- No real API key configuration in this planning task.
- No provider main-chain changes in this planning task.
- No new smoke-test execution code in this planning task.
- No database schema changes in this planning task.
- No frontend UI changes in this planning task.
- No new backend APIs in this planning task.
- No batch, full chapter, LibTV, subtitles, BGM, timeline, export, or production
  launch work.
- Do not expose secrets to browser, logs, reports, artifacts, exceptions,
  snapshots, or git history.
- Signed asset URLs must not contain provider secrets.
- Real smoke reports must state whether a real Agnes request was made.
- Mock M4 evidence and real M5 evidence must remain separate.
- Before enabling Agnes provider, confirm no stale queued Agnes jobs can submit
  outside the authorized one-shot window.

Safety grep:

```bash
grep -RniE 'apihub.agnes-ai.com|AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST|AI_DRAMA_PUBLIC_BASE_URL|LocalSecretStore|AgnesImageBackend' \
  docs tools tests ai_drama_web web/src
```

Allowed hits:

- docs/readiness checklist;
- existing Agnes provider implementation;
- settings UI/backend;
- test mocks/assertions;
- deferred-token docs/UI copy.

Disallowed hits:

- new unguarded real Agnes execution;
- API key printed to logs;
- API key committed;
- real request path outside explicit authorization;
- browser path that directly calls real Agnes.

## Verification Commands

For this docs-only readiness planning task:

```bash
grep -RniE 'apihub.agnes-ai.com|AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST|AI_DRAMA_PUBLIC_BASE_URL|LocalSecretStore|AgnesImageBackend' \
  docs tools tests ai_drama_web web/src
git diff --check
git status --short
git diff --name-only origin/main...HEAD
```

Expected changed file for this task:

```text
docs/milestones/m5-readiness-plan.md
```

Before any future real smoke-test implementation or execution, rerun the full
baseline:

```bash
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m3_agnes_generation.py
python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
python3 migration/tools/verify_migration.py
git diff --check
```

Full baseline is intentionally deferred from this docs-only planning task unless
the reviewer asks for it now. It must run immediately before any real
smoke-test implementation or execution.

## Go / No-Go Decision Template

```text
M5 Readiness Decision:
- Repository readiness: GO / NO-GO
- Environment readiness: GO / NO-GO
- Secret readiness: GO / NO-GO
- Public asset readiness: GO / NO-GO
- Provider readiness: GO / NO-GO
- Safety readiness: GO / NO-GO

Overall:
- M5_REAL_PROVIDER_SMOKE_TEST_READY
or
- M5_REAL_PROVIDER_SMOKE_TEST_NOT_READY

Reason:
...

Required fixes:
...
```

Current planning-time real smoke-test decision:

```text
M5_REAL_PROVIDER_SMOKE_TEST_NOT_READY
```

Reason: this task prepares the readiness plan only. Environment, secret, public
asset reachability, full baseline verification, official docs recheck, and
separate user authorization are still required before real execution.

## User Acceptance Gate

The agent team may prepare the plan and checklist.

The agent team may run dry-run verification only.

The agent team must not execute a real Agnes request.

The user must review the readiness plan.

The user must explicitly approve before any M5 real smoke test.

Approval for this document is not approval to run Agnes. The real smoke test
requires a later user message containing exactly:

```text
AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST
```

## Deferred Items

- Full verification baseline immediately before future execution.
- Official Agnes Video documentation recheck immediately before future
  execution.
- Real environment setup outside git.
- Agnes API key configuration through `LocalSecretStore`.
- External signed asset URL reachability check.
- A real smoke-test report writer or operator report path, if separately
  approved later.
- Any implementation needed to enforce the single-request authorization gate in
  code, if separately approved later.
- Real smoke-test execution after explicit authorization.
- Key rotation and cleanup procedure after the smoke window, if the operator
  chooses to remove local credentials.
