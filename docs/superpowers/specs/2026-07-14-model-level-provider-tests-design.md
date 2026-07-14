# Model-Level Real Provider Tests And Supplier Adapter Template Design

Status: approved product design, implementation not started

Date: 2026-07-14

Repository: `Java-zengzhiwen/ai-drama`

## 1. Purpose

Add a model-level `测试` action to the existing supplier model catalog so a local operator can confirm that one configured text or image model can make a real provider request before binding it to project work.

The same increment also replaces the minimal custom-supplier source with an AI Drama-native TypeScript template that contains detailed Chinese comments and a practical AI-assisted adapter-authoring guide. Built-in OpenAI-compatible and Agnes adapter source receives equivalent Chinese comments without changing its provider request semantics.

This is an additive post-M6 feature. The M6 supplier, model, configuration, credential, immutable snapshot, isolated Worker, loopback-only management, and default real-network-denial contracts remain authoritative.

## 2. Confirmed Product Decisions

- Use the recommended model-row flow, not a supplier-wide test center.
- Put `测试` at the end of the existing action group for each eligible model row.
- Phase 1 supports text and image models only.
- Video models do not show a test button in Phase 1.
- Clicking `测试` opens a confirmation modal; it never sends a request immediately.
- The modal clearly identifies the supplier, model, capability, editable prompt, real-request nature, and possible provider charge.
- Confirming the modal authorizes exactly one provider generation submission for that model test.
- No automatic retry, fallback model, batch request, or project workflow is allowed.
- A text success shows normalized output, token usage when supplied, and elapsed time.
- An image success shows a locally served preview, media type, byte size, and elapsed time.
- Test runs are separate audit records. They do not create project assets, generation jobs, chapter runs, or project binding changes.
- The supplier adapter template follows the Toonflow-style guided authoring experience, but it uses the AI Drama runtime contract rather than Toonflow runtime globals or exports.

## 3. Scope

### 3.1 In Scope

- model-row test button for enabled text and image models;
- real-request confirmation modal and result states;
- one direct model test API and read APIs;
- immutable direct-test execution snapshot;
- durable, sanitized model-test audit record;
- text `textRequest` execution;
- image `imageRequest` execution and bounded result download;
- current supplier version, current config revision, current model revision, and current ready credential resolution;
- idempotent submission and restart-safe outcome handling;
- AI Drama-native Chinese custom-supplier template;
- detailed Chinese comments in built-in OpenAI-compatible and Agnes adapter sources;
- fake-provider TDD, browser tests, migration verification, and security checks.

### 3.2 Out Of Scope

- video model tests;
- supplier-level `测试全部`;
- automatic model discovery;
- model benchmarking, quality scoring, or comparison;
- test history page, search, export, or bulk deletion UI;
- automatic retry, provider fallback, or connection failover;
- saving test images into the project asset library;
- changing project model bindings;
- sending a real provider request from implementation, CI, verifier, or automated tests;
- copying Toonflow globals such as `axios`, `logger`, `pollTask`, or `createOpenAI` into the AI Drama Worker;
- relaxing Worker isolation, loopback enforcement, credential storage, or egress policy.

## 4. Browser Experience

### 4.1 Model Row

For an enabled text or image model, the operation order is:

```text
查看  编辑  停用  删除  测试
```

`测试` is a normal command button placed after the current actions, matching the compact table style. The button uses a familiar experiment/play icon from the existing icon library when available and exposes an accessible label such as `测试 Agnes Image`.

The button is absent for video capability. It is disabled while the same row has an in-flight test or when the supplier/model is disabled. A disabled control has a tooltip naming the reason.

### 4.2 Confirmation Modal

The modal title is `测试模型连接`. It contains:

- supplier display name;
- model display name and provider model name;
- capability label;
- one editable prompt with a safe default;
- a warning: `将向真实供应商提交 1 次生成请求，可能产生费用。`;
- `取消` and `确认并测试` actions.

Default prompts:

```text
text: 请只回复：连接测试成功
image: 一只白色陶瓷杯放在木桌上，柔和自然光，简洁写实，无文字
```

The image test uses a provider-neutral size resolved from the model definition. If the model does not declare a supported default, the backend uses `1024x768`. Phase 1 does not expose advanced parameters.

Double-click protection disables `确认并测试` immediately after the first accepted click. Closing or refreshing the browser never creates a second submission.

Before calling the create API, the browser stores the idempotency key in `sessionStorage`, namespaced by `supplier_model_id`; after acceptance it adds `test_run_id`. It keeps those identifiers only until the run is terminal. It does not store the prompt, provider response, credential, config, Authorization data, or result URL. When a response was lost before the run ID arrived, reload uses the idempotency lookup API below; otherwise it resumes the local status read. Neither path creates another provider submission.

### 4.3 Progress And Result

After acceptance, the modal shows a stable test-run identifier and polls its local status.

States are:

```text
queued
submitting
completed
failed
submission_outcome_unknown
```

Text completion shows:

- normalized text output;
- input, output, and total tokens when present;
- total elapsed milliseconds.

Image completion shows:

- image preview from a loopback-only local content endpoint;
- media type;
- byte size;
- total elapsed milliseconds.

Failure shows a stable Chinese message and error code. It never shows Authorization data, credential text, an unredacted signed URL, or a raw provider response. `submission_outcome_unknown` explicitly tells the operator that the system will not retry because the provider may already have accepted the request.

## 5. Authorization And Network Boundary

The model test is an explicit real-provider action, distinct from `校验并保存`:

- `校验并保存` remains local-only and always has network disabled;
- opening the test modal makes no network request to the provider;
- the local operator's `确认并测试` action authorizes one generation submission for the selected supplier, model, and capability;
- an image result may require one bounded download from the provider-returned result origin after the generation submission;
- the authorization permits no retry, no second generation, no fallback, and no other model;
- another test requires another explicit modal confirmation;
- implementation work, unit tests, browser tests, verifiers, and CI continue to deny real provider traffic at the transport layer;
- Codex or another agent must not click or invoke a real model test during implementation or verification without a separate user instruction naming the provider and capability.

The APIs added by this feature are management APIs. Application-layer loopback enforcement applies to all of them. Direct non-loopback and untrusted forwarded access returns `LOCAL_MANAGEMENT_ONLY` before any run is created.

All runtime traffic goes through the existing injected, versioned `helpers.http` boundary. Model tests may not use Python HTTP clients, native Worker fetch, environment proxy inheritance, or adapter-specific escape paths. Existing endpoint, redirect, result-origin, response-size, timeout, and peer-address protections apply unchanged.

## 6. API Contract

### 6.1 Create A Test Run

```http
POST /api/models/{supplier_model_id}/tests
Idempotency-Key: <required unique key>
If-Match: <current model ETag>
Content-Type: application/json

{
  "prompt": "..."
}
```

The endpoint:

1. enforces loopback-only access;
2. validates the current model ETag, prompt length, and capability;
3. resolves the selected model directly, without a project binding;
4. resolves current immutable supplier, config, model, credential, runtime, helper, limits, and rate-limit bucket revisions;
5. persists the execution snapshot and test run before provider traffic;
6. returns `202 Accepted` with the queued run;
7. schedules local asynchronous execution.

The request cannot select or override a credential, Base URL, provider model name, supplier version, config revision, or adapter source.

Text prompts contain 1-4000 Unicode code points. Image prompts contain 1-2000 Unicode code points. Empty, oversized, or non-string input fails before a run or provider request is created. A stale model ETag returns `REVISION_CONFLICT`; the UI reloads the row and requires a new confirmation. Config or credential changes committed before the create transaction are intentionally resolved as current and are identified in the returned run snapshot metadata.

Response fields are safe metadata only:

```json
{
  "test_run_id": "uuid",
  "supplier_model_id": "uuid",
  "capability": "text",
  "status": "queued",
  "created_at": "ISO-8601"
}
```

### 6.2 Read Feature Status

```http
GET /api/model-tests/status
```

This loopback-only, non-mutating endpoint returns `{ "enabled": true | false }`. The model catalog uses it to hide all model-test actions while the rollout flag is disabled. It contains no supplier, model, configuration, credential, or runtime data.

### 6.3 Recover An Accepted Run

```http
GET /api/models/{supplier_model_id}/tests/by-idempotency-key
Idempotency-Key: <previous key>
```

This loopback-only lookup returns the safe run representation when the create response was lost after commit. It never creates, executes, or retries a run. An unknown key returns 404. The idempotency key is supplied as a header so it is not placed in URL, proxy, or browser-history logs.

### 6.4 Read A Test Run

```http
GET /api/model-tests/{test_run_id}
```

The response contains status, safe model identity, normalized text/usage or image metadata, elapsed time, sanitized error/evidence metadata, and timestamps. It does not contain a credential, provider Authorization header, raw signed URL, config secret, or raw provider body.

### 6.5 Read Image Content

```http
GET /api/model-tests/{test_run_id}/content
```

This endpoint is available only for a completed image test. It serves locally persisted bytes with a strict image media type, content-length, `nosniff`, and private/no-store cache policy. It is loopback-only and never redirects to a provider URL.

## 7. Direct Test Resolution And Snapshot

Model tests do not use or mutate project bindings. The resolver accepts only `supplier_model_id` and requires:

- supplier exists and is enabled;
- model exists, is enabled, and has capability `text` or `image`;
- current supplier version is compiled and compatible;
- the exact capability export exists (`textRequest` or `imageRequest`);
- current config revision is valid;
- current credential exists, is `ready`, and passes storage integrity checks;
- current model revision and provider model name are available;
- frozen rate-limit bucket and worker limits are valid.

The immutable snapshot uses the existing `ExecutionSnapshot` schema and adds no plaintext secret. It records:

```text
operation_key=supplier_model_test
binding_source=direct_model_test
credential_resolution_mode=current
supplier_id
supplier_version_id
config_revision_id
supplier_model_id
model_revision_id
provider_model_name
capability
resolved_credential_version_id
compiled/runtime/compiler/helper fingerprints
rate_limit_bucket_key
resolved_constraints
worker limits
```

Execution loads the exact compiled artifact and resolved credential version from this snapshot. A config, code, model, credential, or enable-state change after run creation does not change that run.

## 8. Persistence And State Machine

Add an additive `supplier_model_test_runs` table containing at least:

```text
test_run_id
supplier_id
supplier_model_id
snapshot_hash
snapshot_object_id
capability
credential_version_id
idempotency_key
request_hash
request_object_id
status
attempt_count
lease_owner
lease_expires_at
normalized_result_object_id
sanitized_evidence_object_id
content_object_id
media_type
byte_size
error_code
error_message
created_at
started_at
finished_at
```

No plaintext credential, Authorization header, raw signed URL, or unsanitized provider response is stored.

`request_object_id` points to a private local object containing only the normalized provider-neutral test input, including the prompt and resolved image size. It is runtime data, is never committed/exported, and is never placed in sanitized evidence.

State transitions are:

```text
queued -> submitting -> completed
queued -> submitting -> failed
queued -> submitting -> submission_outcome_unknown
```

Rules:

- one run has at most one provider generation submission attempt;
- the executor claims one queued row with a compare-and-swap transaction; `attempt_count` changes from 0 to 1, the lease is recorded, and status enters `submitting` in that same transaction;
- concurrent executors that lose the claim do no work and make no network request;
- a queued run may resume after restart;
- a run found in `submitting` after process restart becomes `submission_outcome_unknown` and is never automatically resubmitted;
- completed image content is written to the object store before the run becomes completed;
- failed and unknown runs retain their snapshot and sanitized evidence;
- test records are not rows in project generation job/result/asset tables;
- Phase 1 has no history screen or automatic retention cleanup; the stored audit trail remains local and is excluded from Git and exports.

`credential_version_id` duplicates the snapshot reference solely for indexed lifecycle enforcement; it never contains secret material. Queued and submitting model tests count as active references to that resolved credential version. Normal credential deletion returns the existing active-reference conflict. Force deletion fails queued tests with `CREDENTIAL_REVOKED` before network; an already submitting test becomes `submission_outcome_unknown` because local deletion cannot prove provider-side cancellation. Supplier/model disable blocks new tests but lets already persisted tests drain through their frozen snapshots, consistent with existing M6 work-drain semantics.

## 9. Idempotency And Rate Limiting

The idempotency scope is the selected model test identity:

```text
UNIQUE(supplier_model_id, capability, idempotency_key)
```

The request hash includes:

```text
snapshot_hash
normalized prompt
resolved provider-neutral image size when applicable
test contract version
```

Behavior:

- same scope, key, and hash returns the existing run;
- same scope/key with a different hash returns `IDEMPOTENCY_CONFLICT`;
- a browser timeout or refresh uses the same key/run and cannot submit again;
- the executor rejects any second attempt for a run with `attempt_count=1`;
- no automatic retry is allowed for timeout, provider 5xx, malformed response, download failure, Worker failure, or unknown outcome.

The test consumes the same snapshot-frozen supplier rate-limit bucket as normal work. Test traffic cannot define or dynamically change its own bucket key.

## 10. Error Contract

Errors are stable, sanitized, and mapped to concise Chinese UI messages.

| Error code | Meaning |
|---|---|
| `MODEL_TEST_CAPABILITY_UNSUPPORTED` | The selected model is not text or image. |
| `SUPPLIER_DISABLED` | The supplier cannot start new work. |
| `MODEL_DISABLED` | The model cannot start new work. |
| `CREDENTIAL_MISSING` | No current credential is configured. |
| `CREDENTIAL_STORAGE_CORRUPT` | Credential integrity/recovery failed. |
| `CREDENTIAL_REVOKED` | The selected credential was force-deleted before submission. |
| `CONFIG_MISSING` | Required current configuration is absent. |
| `SUPPLIER_OPERATION_UNAVAILABLE` | The exact adapter export is unavailable. |
| `SUPPLIER_RUNTIME_UNAVAILABLE` | The frozen Worker/compiler/helper runtime cannot execute. |
| `PROVIDER_HTTP_ERROR` | The provider returned a sanitized HTTP failure. |
| `PROVIDER_RESPONSE_MALFORMED` | Adapter output did not meet the contract. |
| `RESULT_DOWNLOAD_FAILED` | An image generation succeeded but bounded local download failed. |
| `MODEL_TEST_TIMEOUT` | The one allowed attempt exceeded its limit. |
| `SUBMISSION_OUTCOME_UNKNOWN` | A crash/transport boundary prevents safe determination and retry. |
| `IDEMPOTENCY_CONFLICT` | The same key was reused with different content/snapshot. |
| `LOCAL_MANAGEMENT_ONLY` | The request did not originate from an allowed loopback peer. |

Preflight errors create no test run and make no provider request. Once a run is persisted, all execution failures remain auditable on that run.

## 11. Supplier Adapter Template

### 11.1 Native Contract, Not Toonflow Runtime Compatibility

The template borrows Toonflow's guided, heavily commented authoring experience. It does not claim source compatibility.

The template must explicitly state in Chinese:

- use ESM exports: `export const vendor`, `export async function textRequest`, and equivalent image/video functions;
- never use `exports.vendor`, `module.exports`, or append `export {}` to a CommonJS-style template;
- no import, `require`, `process`, Node built-ins, native `fetch`, filesystem, environment variables, sockets, subprocesses, `axios`, `logger`, `pollTask`, or `createOpenAI`;
- all runtime network access must use injected `helpers.http.request`;
- configuration comes from `payload.config` and the selected secret comes only from `payload.credential`;
- never log, return, or persist credentials or Authorization headers;
- models use stable `supplierModelId`, `providerModelName`, `displayName`, and `capability` fields;
- text uses `textRequest(payload, helpers)`;
- image uses `imageRequest(payload, helpers)` and returns normalized bytes/metadata;
- video uses separate `videoSubmit`, `videoPoll`, and `videoFetch` exports;
- Agnes-style video polling must use `video_id`, never `task_id`;
- validation has no network and must not perform top-level HTTP work;
- local save validation and the model-row real test are different actions.

### 11.2 Template Structure

The default custom-supplier source remains locally compilable before the user adds a model. It contains:

1. a Chinese overview and safety boundary;
2. a valid `vendor` manifest with no models by default;
3. commented text/image/video model examples using stable IDs;
4. commented configuration-field examples;
5. request and normalized-return type explanations;
6. small helper examples for sanitized stable errors;
7. operation skeletons that fail with `SUPPLIER_OPERATION_NOT_CONFIGURED` until implemented;
8. the AI-assisted generation guide below.

The template must not contain a real API key, bearer value, signed URL, or provider-specific private result.

### 11.3 Chinese AI-Assisted Generation Guide

The code comment gives the operator these steps:

1. Collect the supplier's official text/image/video API documentation, authentication scheme, endpoint paths, request examples, response examples, status definitions, limits, and result-download rules.
2. Never give the AI a real API key. Use the placeholder `YOUR_API_KEY` and configure the real key later in the masked supplier secret UI.
3. Give the AI the complete current template and ask it to preserve the AI Drama manifest, helper, operation signatures, isolation restrictions, and normalized returns.
4. Name only the required capabilities. Do not ask the AI to invent unsupported text, image, or video operations.
5. Ask the AI to map provider errors to stable sanitized codes and to remove secrets and signed query values from evidence.
6. For video, require submit/poll/fetch separation and confirm the provider's stable polling identifier. For Agnes, explicitly require `video_id`.
7. Save with `校验并保存`. Fix all compile/manifest/export errors locally; this step must not contact the provider.
8. Add or verify the model entry in the model catalog, configure non-secret fields and the masked credential, then use the matching model row's `测试` button.
9. Confirm one real request, inspect the normalized result, and revise the adapter if the sanitized error identifies a contract mismatch.
10. Bind the tested model to a project only after the model-level test succeeds.

The comment also includes a ready-to-copy AI instruction block that names the AI Drama contract and asks for one complete TypeScript adapter file, but it does not embed provider documentation or any credential.

### 11.4 Built-In Adapter Comments

The built-in OpenAI-compatible and Agnes sources receive Chinese comments covering:

- manifest and model identity;
- configuration and credential sources;
- request normalization;
- injected HTTP helper usage;
- response normalization and stable errors;
- image result download;
- Agnes normal/keyframes image-count rules;
- Agnes `video_id` submit/poll/fetch flow;
- secret and signed-URL redaction expectations.

Comment-only edits must not change endpoint paths, request parameters, model names, polling identity, normalized outputs, limits, or error mapping.

## 12. Components And Ownership

Implementation should keep the feature in small units:

- `ModelTestService`: direct resolution, preflight, snapshot/run creation, idempotency;
- `ModelTestExecutor`: claim-once state transition, exact snapshot execution, normalized persistence;
- `ModelTestSanitizer`: safe evidence/error projection;
- model-test router: loopback-only create/read/content API;
- `ModelTestDialog`: prompt, confirmation, polling, results, accessible states;
- supplier template source: Chinese AI guidance and operation skeletons;
- built-in adapter source: comment-only documentation updates.

The executor reuses the existing snapshot loader, supplier execution gateway, object store, credential reader, Worker protocol, injected helper, rate limiter, and redaction rules. It must not create a parallel adapter runtime.

## 13. Migration And Compatibility

The database migration is additive:

- add `supplier_model_test_runs` and required indexes;
- preserve all M1-M6 tables and history;
- support fresh and upgraded databases;
- migration replay is idempotent;
- no backfill is required because historical model tests do not exist;
- migration rollback disables the new routes/UI and leaves the additive table unread but harmless;
- no existing provider, project binding, generation, result, asset, or credential row is rewritten.

The custom-supplier template change applies only when creating a new custom supplier. Existing custom supplier source is never overwritten. Built-in comment updates create normal immutable built-in source versions and preserve historical compiled artifacts.

## 14. Test Plan

Implementation uses TDD. Every automated test uses a local fake supplier/helper and transport-level real-network denial.

### 14.1 Backend

- eligible text/image direct resolution freezes exact current revisions;
- video, disabled supplier/model, missing config/credential/runtime/export fail before network;
- snapshot and run persist before the attempt;
- same idempotency key/hash returns the same run;
- changed request/snapshot under the same key returns `IDEMPOTENCY_CONFLICT`;
- exactly one fake provider generation submission occurs;
- queued restart resumes once;
- submitting restart becomes `submission_outcome_unknown` without resubmit;
- concurrent executor claims produce one winner and one submission;
- text output/usage normalize and persist;
- image bytes persist before completion and serve locally;
- provider URL is never returned to the browser;
- failed/unknown runs retain sanitized evidence;
- test completion creates no project asset, generation job, result, chapter run, or binding change;
- rate limiting uses the snapshot bucket;
- loopback guard rejects direct public, FRP, untrusted proxy, and spoofed forwarded access;
- secrets, Authorization values, signed query strings, and raw provider bodies do not appear in responses, logs, database text fields, or object evidence.
- normal/force credential deletion follows the active-test rules without leaking or resubmitting work.

### 14.2 Worker And Template

- new custom supplier template compiles with zero models;
- template uses ESM `vendor` export and contains required Chinese contract guidance;
- template contains no forbidden import/global/runtime escape;
- adding text/image/video manifest examples requires the matching exports;
- validation network helper always returns `NETWORK_DISABLED_DURING_VALIDATION`;
- built-in comment changes compile to contract-equivalent manifests and pass existing adapter fixtures;
- OpenAI request/usage behavior remains unchanged;
- Agnes image and video request fixtures remain unchanged;
- Agnes polling asserts `video_id` and rejects `task_id` substitution.

### 14.3 Frontend And Browser

- text/image rows show `测试` after existing actions;
- video rows do not show it;
- modal shows exact model, editable default prompt, fee warning, and explicit confirm;
- opening/cancelling the modal causes zero provider calls;
- double-click produces one create request and one fake generation submission;
- progress survives refetch and renders all states;
- text output/usage and image preview/metadata render correctly;
- disabled/in-flight controls explain their state;
- sanitized error messages render without leaking raw responses;
- `LOCAL_MANAGEMENT_ONLY` is handled consistently with existing management pages;
- responsive table/modal layout has no overlapping controls or clipped text.

### 14.4 Regression And Real-Network Denial

- Python tests;
- Web Vitest and build;
- Playwright with a fake provider;
- Worker tests;
- migration verifier;
- M3-M6 verifiers;
- tracked-secret and signed-URL scan;
- `git diff --check`;
- explicit counters remain:

```text
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

No automated verification clicks the real-test confirmation against a real provider.

## 15. Acceptance Criteria

| ID | Criterion |
|---|---|
| MTEST-001 | Enabled text and image model rows show a final `测试` action; video rows do not. |
| MTEST-002 | Opening/cancelling the modal performs zero provider traffic. |
| MTEST-003 | Each confirmation authorizes at most one real generation submission for the exact selected model. |
| MTEST-004 | Text completion shows normalized output, usage when present, and elapsed time. |
| MTEST-005 | Image completion shows locally persisted content, media type, byte size, and elapsed time without exposing provider URLs. |
| MTEST-006 | Test execution freezes supplier/config/model/credential/runtime/helper/limit/bucket identity before network. |
| MTEST-007 | Refresh, timeout, double-click, replay, and restart never cause a second submission. |
| MTEST-008 | Ambiguous submitting recovery fails closed as `SUBMISSION_OUTCOME_UNKNOWN` without retry. |
| MTEST-009 | Missing or disabled prerequisites fail before network with stable errors. |
| MTEST-010 | Test records never create project assets, formal generation jobs/results, runs, or binding changes. |
| MTEST-011 | All model-test APIs enforce application-layer loopback-only access. |
| MTEST-012 | Browser, logs, persistence, and evidence contain no credential, Authorization header, raw signed URL, or unsanitized provider body. |
| MTEST-013 | Default automated verification performs zero real provider requests. |
| MTEST-014 | New custom suppliers receive the compilable AI Drama-native Chinese template and AI-assisted generation guide. |
| MTEST-015 | Built-in OpenAI-compatible and Agnes sources contain detailed Chinese comments with contract-equivalent runtime behavior. |
| MTEST-016 | Existing M1-M6 workflow, history, adapter, binding, migration, and rollback behavior does not regress. |

## 16. Rollback

The feature is guarded by a default-off `AI_DRAMA_MODEL_TESTS_ENABLED` flag during implementation and rollout.

Rollback consists of:

1. set the flag false;
2. hide the model-row actions;
3. return `MODEL_TESTS_DISABLED` from the create route while keeping loopback-only status/read/content available for existing local audit records;
4. stop claiming queued test runs;
5. leave existing local audit rows and object bytes intact;
6. keep all normal supplier, project binding, and generation paths unchanged.

Rollback does not revert supplier code/config/model/credential revisions and does not delete test evidence automatically.

## 17. Implementation Gate

This document authorizes design review only. It does not authorize production-code changes or any real provider request.

After written-spec approval, the next step is a separate implementation plan using TDD. The plan must define focused commits, migration order, feature-flag rollout, fake-provider verification, two independent read-only reviews, and a final report/PR handoff. Any real provider smoke test remains a separately requested user action after implementation review.
