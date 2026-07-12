# Toonflow-Style Supplier And Project Model Configuration Design

**Status:** Revised design for review

**Date:** 2026-07-12

**Target milestone:** Future M6; implementation is not authorized under current M5 governance

## 1. Product Goal

AI Drama will provide a Toonflow-style local supplier experience while preserving the current durable run/job model:

- the product structure remains `Supplier -> Models`;
- each supplier has one TypeScript adapter, one configuration form, one credential, and one model catalog in M6;
- supplier code can be edited in the browser and saved without restarting the application;
- a project selects default text, image, and video models;
- individual workflow operations may override project defaults;
- secrets are entered in the browser, masked after save, and never returned as plaintext;
- new work uses the latest saved supplier/model/config revisions;
- existing work continues using its creation-time execution fingerprint.

The first built-in suppliers are Agnes, OpenAI, DeepSeek, Anthropic, and xAI.

## 2. M6 Product Scope

M6 delivers this minimum product loop:

1. Supplier list and enable/disable state.
2. One configuration set per supplier: one API key, Base URL, and non-secret fields.
3. Browser TypeScript editor with local compile and contract validation.
4. Stable text, image, and video model identities and immutable model revisions.
5. Browser add/edit/disable actions for supplier models.
6. Project defaults for text, image, and video.
7. Optional operation-level model overrides.
8. Runtime resolution and immutable execution evidence.
9. Existing OpenAI-compatible text and Agnes image/video paths migrated to the supplier interface.
10. Fake-provider end-to-end acceptance with default real-network denial.

M6 does not include:

- multiple accounts under one supplier;
- supplier duplication;
- ZIP or Git supplier installation;
- a supplier marketplace or digital signatures;
- automatic model discovery;
- automatic failover;
- weighted routing or load balancing;
- billing and quota dashboards;
- remote multi-user permissions;
- supported exposure of supplier management beyond loopback;
- real provider model-test buttons in default verification.

## 3. Product Model

The user-visible structure is deliberately two-level:

```text
Supplier
  -> Models

Project
  -> Text default
  -> Image default
  -> Video default
  -> Optional operation overrides
```

There is no separate ProviderType/ProviderConnection hierarchy in M6.

A supplier is:

```text
TypeScript adapter code
+ configuration field schema
+ one set of configuration values
+ one current credential
+ stable model records and revisions
+ enabled/disabled state
```

`POST /api/suppliers` creates a new custom supplier from the empty supplier template. It does not duplicate an existing supplier, copy credentials, or implement the deferred supplier-duplication feature.

## 4. Supplier TypeScript Contract

### 4.1 Manifest

Each supplier script exports `vendor`:

```typescript
interface VendorManifest {
  id: string;
  version: string;
  name: string;
  author: string;
  description?: string;
  icon?: string;
  adapterContractVersion: "ai-drama-supplier-v1";
  helperApiVersion: "ai-drama-helper-v1";
  rateLimitBucketKey: string;
  inputs: VendorInput[];
  inputValues: Record<string, string>;
  models: SupplierModelDeclaration[];
}
```

`inputs` supports `text`, `password`, and `url`. `inputValues` contains safe defaults only. Persisted user values are stored outside supplier source.

`rateLimitBucketKey` must match a strict identifier pattern, is validated during save, and is persisted in the immutable manifest and execution snapshot. Runtime adapter code cannot return or dynamically change the bucket key.

### 4.2 Runtime Exports

The single-file editing experience uses a restart-safe asynchronous contract:

```typescript
exports.vendor = vendor;
exports.textRequest = textRequest;
exports.imageRequest = imageRequest;
exports.videoSubmit = videoSubmit;
exports.videoPoll = videoPoll;
exports.videoFetch = videoFetch;
```

`textRequest` returns normalized text and usage data.

`imageRequest` returns bytes/base64 or a provider URL. AI Drama persists a generation job before calling it and stores final bytes in the existing object store.

`videoSubmit` submits exactly once and returns the provider query identifier plus sanitized evidence. `videoPoll` performs one status query. `videoFetch` retrieves one completed result. Supplier scripts must not contain an internal poll-until-complete loop.

Agnes `videoPoll` uses `video_id`, never `task_id`.

## 5. Stable Model Identity And Revisions

### 5.1 Model Record

Every model has a stable database identity independent of display/upstream names:

```text
supplier_model_id: stable UUID
supplier_id
current_model_revision_id
source: built_in | overlay
enabled
created_at
updated_at
```

Project bindings and model APIs use `supplier_model_id`. A model name is never a primary key, URL identifier, or binding identity.

### 5.2 Immutable Model Revision

Every model definition version is immutable:

```text
model_revision_id: UUID
supplier_model_id
provider_model_name
display_name
capability: text | image | video
definition_object_id
definition_hash
created_at
```

Changing `display_name`, `provider_model_name`, capability metadata, modes, limits, durations, resolutions, or audio support creates a new `model_revision_id` and atomically advances the model's current revision.

An execution snapshot freezes both `supplier_model_id` and the resolved `model_revision_id` plus `provider_model_name`.

### 5.3 Base And Overlay Merge

Manifest base model declarations include a stable `supplierModelId`. Existing built-in manifests without IDs receive deterministic UUIDv5 identities during initial migration; normalized built-in manifests persist those IDs thereafter.

Overlay models receive UUIDv4 identities. The effective catalog is the union of stable identities, not a merge by name.

- A manifest declaration updates only the same `supplierModelId` and creates a new revision.
- An overlay never silently replaces a base model because its `provider_model_name` matches.
- Duplicate `(capability, provider_model_name)` values across different active IDs are rejected unless one record is disabled.
- Editing a bound model requires the current model ETag and an explicit acknowledgement containing the number of affected project bindings; new tasks use the new revision, while existing snapshots remain unchanged.
- A model referenced by a project binding or execution snapshot cannot be physically deleted. It may be disabled.
- A disabled model cannot resolve new work.

Model catalog mutation has its own monotonic `model_catalog_revision` and ETag. It is independent from ordinary supplier configuration revision so concurrent model editing does not conflict with an unrelated Base URL/config form save. Both revision IDs are captured independently in the execution snapshot.

## 6. Browser Experience

### 6.1 Supplier Page

The main navigation adds `模型供应商`.

Each supplier shows:

- name, author, version, capabilities, and enabled state;
- API Key status and masked suffix;
- Base URL and manifest-defined fields;
- text, image, and video models;
- TypeScript code editor;
- `校验并保存` and `恢复内置版本` actions.

Saving performs local compile and contract validation only. It does not call a provider.

### 6.2 Secret Interaction

- API keys are entered in a masked input.
- An eye control reveals only the unsaved value currently in the input.
- Successful save clears the input.
- Stored values are shown only as `已配置 ....ABCD`.
- Stored secrets can be replaced or deleted but never retrieved through an API.
- Secret plaintext is absent from supplier TypeScript, SQLite value columns, logs, errors, browser query cache, and execution evidence.

### 6.3 Project Model Page

Each project shows text, image, and video defaults. Operations inherit a default or select an explicit stable model ID.

Initial text operations:

```text
source_segmentation
script_adaptation
material_extraction
character_bible
scene_bible
prop_bible
storyboard_design
visual_anchor_planning
image_prompt_generation
shot_prompt_generation
```

Initial image operations:

```text
character_reference_image
scene_reference_image
prop_reference_image
storyboard_keyframe_image
```

Initial video operation:

```text
shot_video_generation
```

The UI filters by capability and never permits a text model to bind to an image/video operation.

## 7. Save, Compile, And Hot-Reload Semantics

Saving supplier code performs:

```text
parse and compile TypeScript
-> validate imports and forbidden globals
-> run manifest validation with network-disabled helpers
-> validate required exports
-> canonicalize manifest
-> store source and compiled artifacts
-> calculate source, compiled, manifest, compiler-options hashes
-> create immutable supplier version
-> atomically advance current_version_id using If-Match
```

Every successful save creates a new internal supplier version even when user-visible `vendor.version` is unchanged.

New tasks use the new current version. Existing draft, queued, submitting, submitted, or polling jobs retain their original version.

Editing an included supplier creates a local override version. `恢复内置版本` only moves `current_version_id` to the preserved built-in version. It never deletes local or historical versions.

## 8. TypeScript Worker Isolation Model

### 8.1 Process And VM Boundary

Python delegates compilation, validation, and execution to a dedicated local Node worker process using a versioned JSON protocol and a controlled VM context.

Supplier adapter code cannot access:

- `process` or environment variables;
- `require`, dynamic `import()`, static `import`, or Node's module loader;
- Node built-in modules;
- native `fetch`, WebSocket, raw sockets, DNS, child processes, or worker threads;
- filesystem APIs;
- Python process memory, SQLite, object store paths, or other suppliers' configuration/secrets.

M6 prohibits all imports in supplier source. The compiler rejects `ImportDeclaration`, `ImportExpression`, `require`, and equivalent module-loading constructs. A future fixed import allowlist requires a new helper/contract version and separate review.

The VM exposes only the helper API named by `helper_api_version`. The helper object is frozen and capability-based. It includes normalized HTTP, bounded logging, media conversion, and provider-neutral utility calls; it does not expose raw native globals.

### 8.2 Validation Mode

Validation runs in a fresh VM context with no secret and no live network helper. Every helper function capable of network access throws exactly:

```text
NETWORK_DISABLED_DURING_VALIDATION
```

Top-level network work therefore fails save validation. Compile success alone is not sufficient.

### 8.3 Execution Mode

Execution runs the immutable compiled artifact selected by the snapshot. Network access is available only through the injected, versioned HTTP helper. The worker receives only the selected supplier config/credential and current request; it never receives other suppliers' values.

The worker starts from an allowlisted environment constructed by Python. It does not inherit `AI_DRAMA_*`, Agnes keys, other provider keys, shell credentials, proxy variables, home-directory variables, or unrelated environment state. Only runtime essentials such as a fixed locale/timezone and explicitly selected Node executable configuration are passed.

### 8.4 Resource And Failure Limits

Every operation has a Python-enforced wall-clock timeout, maximum protocol message size, maximum log size, and capability-specific result limit. Initial hard limits are part of worker configuration and snapshot evidence:

- validation/status/text protocol response: 4 MiB;
- sanitized provider response evidence: 1 MiB;
- accumulated worker logs: 256 KiB;
- image base64 result: 25 MiB; larger media must use the bounded download helper;
- provider/result URL: 16 KiB;
- validation/text/poll call: 30 seconds;
- submit/image/fetch call: 120 seconds.

Python launches the worker in a terminable process group. Timeout, oversized output, malformed JSON, protocol-version mismatch, unexpected exit, or heartbeat failure causes Python to terminate the worker process group, discard it, and create a clean worker for the next call. The job records a stable sanitized error. A stuck worker cannot block the poller indefinitely.

`trusted local code` means the local operator is allowed to author supplier logic and intentionally make provider requests. It does not grant supplier code access to the full host process, filesystem, environment, or unrelated secrets.

## 9. Application-Layer Loopback Enforcement

Loopback-only management is enforced in FastAPI application code, not only by Uvicorn, FRP, Nginx, or firewall configuration.

The guard applies to:

- all `/api/suppliers` routes, including code, config, secret, restore, and models;
- project model-binding mutations and reads;
- project model-resolution previews;
- future supplier worker-management endpoints.

By default, the direct TCP peer address must be `127.0.0.1` or `::1`. Arbitrary `X-Forwarded-For`, `Forwarded`, or similar headers are ignored.

Forwarded headers are interpreted only when an explicit trusted-proxy CIDR configuration exists and the direct peer belongs to that allowlist. The application then validates the complete trusted proxy chain and resolved client address. Merely sending a forwarded header never grants local status.

Non-loopback access receives HTTP 403:

```json
{"error_code":"LOCAL_MANAGEMENT_ONLY","error_message":"supplier and project model management is available only from the local machine"}
```

The current public gateway allowlist remains limited to `/healthz` and signed `/public/assets/...` delivery. It must not proxy supplier, code, secret, model, project binding, or resolution APIs.

## 10. Configuration And Credential Revisions

The UI presents one supplier configuration, while the backend preserves immutable revisions:

- supplier code save creates `supplier_version_id`;
- non-secret config save creates `config_revision_id` and `config_hash`;
- model save creates an independent `model_catalog_revision` and `model_revision_id`;
- API key replacement creates `credential_version_id`;
- active submitted/polling work retains its original credential version;
- new work uses current revisions unless explicit rerun semantics say otherwise.

Old credential versions are retained only while referenced by non-terminal jobs or an unfinished credential journal. They are deleted after those references are terminal/finalized. Rerun does not retain old credentials by default.

Deleting an active credential requires an explicit force action. Force deletion cancels draft/queued work and marks submitted/polling work locally failed with `credential_revoked`; it does not imply provider-side cancellation.

Disabling a supplier blocks new work and allows existing work to drain using stored revisions.

## 11. Execution Snapshot And Reproducibility Fingerprint

Every new Web project run and generation job persists an immutable `ExecutionSnapshot` before any provider request:

```text
snapshot_schema_version
supplier_id
supplier_version_id
supplier_source_hash
manifest_hash
compiled_artifact_object_id
compiled_artifact_hash
adapter_contract_version
worker_protocol_version
worker_runtime_version
compiler_name
compiler_version
compiler_options_hash
helper_api_version
rate_limit_bucket_key
supplier_model_id
model_revision_id
provider_model_name
capability
operation_key
binding_source
config_revision_id
config_hash
model_catalog_revision
credential_resolution_mode
resolved_credential_version_id
resolved_constraints
worker_limits_hash
source_snapshot_hash: optional, rerun only
source_supplier_version_id: optional, rerun only
source_config_revision_id: optional, rerun only
source_model_revision_id: optional, rerun only
created_at
```

The snapshot excludes plaintext secrets. Its object is stored in the content-addressed object store, and its object ID is recorded on the run/job row.

The source and compiled artifact are stored together as immutable objects. Historical work loads `compiled_artifact_object_id`; it never recompiles current supplier source or substitutes a current compiled artifact.

An incompatible helper change requires a new `helper_api_version`. Worker protocol, runtime, compiler, compiler options, helper API, and limits are resolved and fingerprinted before request persistence.

If the exact compiled artifact, compatible worker protocol/runtime, or helper API is unavailable, execution fails closed with:

```text
SUPPLIER_RUNTIME_UNAVAILABLE
```

It never guesses with the current runtime.

For runtime `runs`, `resolved_snapshot_object_id` is added to the run record and request hash. For `generation_jobs`, the same column is added to the job record and generation request hash.

Terminal legacy records may keep an empty snapshot. Active legacy Agnes jobs are backfilled before poller startup with an explicit `legacy_agnes_v1` version derived from legacy endpoint, model, credential reference, and runtime fingerprint. They are never routed through current project bindings.

## 12. Project Binding Resolution And Concurrency

Resolution order is:

```text
operation override
-> project capability default
-> MODEL_BINDING_MISSING
```

There is no automatic fallback. Bindings reference `supplier_model_id`.

The complete binding set has a monotonic `binding_set_revision`. Reads return an ETag; updates require matching `If-Match`. Stale pages receive HTTP 409 and must reload.

All mutations use concurrency preconditions:

- create uses `If-None-Match: *` plus an idempotency key;
- supplier code/config/enable/restore use the current supplier/version ETag;
- secret replace/delete uses the credential ETag;
- model create/update/disable/delete uses the model-catalog/model ETag;
- project bindings use `binding_set_revision` through `If-Match`.

## 13. Idempotency

Generation idempotency is scoped by:

```text
UNIQUE(supplier_id, capability, idempotency_key)
```

The request hash includes the normalized provider-neutral request and execution snapshot hash.

- Same scope, key, and hash returns the existing job.
- Same scope/key with a different request or snapshot returns `IDEMPOTENCY_CONFLICT`.
- Config/model/code changes therefore require a new idempotency key.
- Different suppliers may reuse a key.
- Legacy rows retain existing `(provider, idempotency_key)` behavior through compatibility code.

## 14. Persistent Image/Video Work And Rate Limits

Image generation moves into existing `generation_jobs`, which already supports `job_type=image`:

```text
resolve binding
-> persist request + snapshot + draft job in one database transaction
-> transition to submitting
-> call TypeScript imageRequest
-> persist sanitized response and result
-> create generated asset referencing local job
```

A failed provider call leaves a failed job with request and snapshot.

Video jobs use the same pre-submit persistence. The poller calls `videoSubmit`, `videoPoll`, and `videoFetch` through the job snapshot, not one global backend.

Rate limiting uses the validated `rate_limit_bucket_key` frozen in the snapshot. The default is the supplier ID. Runtime script output cannot change the bucket. Changing the manifest bucket creates a new supplier version and affects only new snapshots.

## 15. Rerun And Credential Resolution

Two explicit actions exist.

### 15.1 Default `重新运行`

The new job inherits from the source:

- `supplier_version_id`;
- `config_revision_id`;
- `supplier_model_id` and `model_revision_id`;
- `provider_model_name`;
- resolved constraints;
- runtime/compiler/helper fingerprint where still available.

It does not inherit the historical credential. It resolves the supplier's current credential and creates a new snapshot containing:

```text
source_snapshot_hash
source_supplier_version_id
source_config_revision_id
source_model_revision_id
credential_resolution_mode=current
resolved_credential_version_id
```

If the current credential is absent, rerun fails before job creation with `CREDENTIAL_MISSING`.

### 15.2 `使用当前项目模型重新运行`

This explicitly resolves current project binding, supplier version, config, model revision, constraints, current credential, and runtime fingerprint. It records source/new snapshot hashes.

### 15.3 Historical Credential

The backend contract may accept `credential_resolution_mode=historical` only when the referenced historical credential still exists. M6 UI does not expose this action. Historical credentials are not retained indefinitely for possible reruns.

Submitted/polling jobs continue using their original credential version. Force deletion behavior remains as defined in Section 10.

## 16. Local Validation And Real Provider Requests

`校验并保存` is local and performs no provider request.

M6 does not add a generic online verification endpoint. Real text/image/video calls occur only through explicit workflow actions and remain governed by provider authorization rules.

Existing Agnes governance remains binding. Current M5 authorization does not authorize supplier abstraction or schema expansion. M6 governance must define branches and exact real-provider authorization before implementation/execution.

Every real provider smoke test requires a separate, explicit authorization scoped to provider and capability. Default tests and verifier deny real network at the transport/helper layer.

## 17. Credential Storage Crash Recovery

Credential file and database state use a recoverable journal protocol.

For create/replace:

1. Create a credential migration-journal record with operation ID and target credential version.
2. Write a same-directory temporary secret file and `fsync` its contents.
3. Apply/verify mode `0600`, compute the internal content hash, and `fsync` the parent directory.
4. In one SQLite transaction, insert the credential version with its internal `content_hash` and state `pending_finalize`, update the supplier's current credential pointer, and update the journal.
5. Atomically rename the temporary file to its versioned final path and `fsync` the parent directory.
6. In a second SQLite transaction, mark credential and journal `ready`.
7. On startup, before worker/poller start, scan `pending_finalize` records and idempotently finish rename/ready transition when recoverable.
8. Remove temporary orphan files with no database/journal reference after a safe grace period.
9. If a database reference exists but neither valid final nor recoverable temporary file exists, mark `credential_storage_corrupt`; block affected work with `CREDENTIAL_STORAGE_CORRUPT` and never fall back to another credential.

Delete/retire operations use the same journal principle: database state first becomes `pending_delete`, active-reference checks are enforced, file removal is finalized idempotently, and startup recovery completes or reports corruption.

## 18. Database Migration

Migration uses a `schema_migrations` ledger. Database schema/data changes are transactional; credential files use Section 17 recovery.

Migration creates:

- supplier/version tables and immutable initial built-in artifacts;
- model/model-revision tables with stable IDs;
- configuration, credential, journal, binding, and snapshot references;
- one Agnes supplier/config from legacy settings and secret reference;
- one OpenAI-compatible supplier when legacy environment config is complete;
- explicit project bindings only when legacy selection is deterministic;
- active legacy Agnes snapshots before poller startup.

Terminal history remains unchanged and readable through compatibility code.

## 19. API Surface

All routes below, except public health/signed assets outside this list, are covered by loopback enforcement where they manage supplier/model/binding state.

```text
GET    /api/suppliers
POST   /api/suppliers
GET    /api/suppliers/{supplier_id}
PATCH  /api/suppliers/{supplier_id}
GET    /api/suppliers/{supplier_id}/code
PUT    /api/suppliers/{supplier_id}/code
POST   /api/suppliers/{supplier_id}/restore-built-in
PUT    /api/suppliers/{supplier_id}/config
PUT    /api/suppliers/{supplier_id}/secret
DELETE /api/suppliers/{supplier_id}/secret
GET    /api/suppliers/{supplier_id}/models
POST   /api/suppliers/{supplier_id}/models
GET    /api/models/{supplier_model_id}
PATCH  /api/models/{supplier_model_id}
DELETE /api/models/{supplier_model_id}

GET    /api/projects/{project_id}/model-bindings
PUT    /api/projects/{project_id}/model-bindings
GET    /api/projects/{project_id}/model-resolution/{operation_key}
```

No GET returns secret plaintext. All mutations follow Section 12 ETag/precondition rules.

## 20. Test Plan

### 20.1 Worker Isolation And Fingerprint

- reject static/dynamic imports, `require`, `process`, native fetch, Node built-ins, filesystem, environment, sockets, child processes, and worker threads;
- assert validation network helpers throw `NETWORK_DISABLED_DURING_VALIDATION`;
- assert execution network calls can occur only through injected helper API;
- assert worker environment excludes all secrets/proxy/home variables;
- terminate/rebuild worker after timeout, oversized output, malformed protocol, crash, or heartbeat failure;
- verify operation limits and process-group termination;
- persist source/compiled artifacts and complete runtime/compiler/helper fingerprint;
- fail with `SUPPLIER_RUNTIME_UNAVAILABLE` when historical runtime/helper/artifact is unavailable;
- prove historical work never recompiles current source.

### 20.2 Application Loopback Guard

- accept direct `127.0.0.1` and `::1` management access;
- reject non-loopback direct peers with `LOCAL_MANAGEMENT_ONLY`;
- ignore spoofed `X-Forwarded-For` by default;
- parse forwarded headers only from configured trusted proxy CIDRs;
- reject FRP/reverse-proxy access to supplier/code/secret/model/binding/resolution routes;
- assert public gateway routing exposes only `/healthz` and signed asset paths.

### 20.3 Model Identity And Binding

- assign stable UUIDs and immutable revisions;
- bind projects by `supplier_model_id`;
- rename display/provider names without changing stable ID;
- ensure existing snapshots retain old revision/name;
- reject name-based silent overlay replacement;
- reject physical deletion of bound/snapshotted models;
- require acknowledgement and ETag for bound model edits;
- verify independent model-catalog and config revisions;
- verify operation override/default resolution and stale binding conflicts.

### 20.4 Hot Reload, Snapshot, Idempotency, Rate Limit

- new work uses newly saved code/config/model revisions;
- queued/submitted work uses old immutable artifacts/fingerprint;
- restore switches pointer without deleting history;
- rate bucket is validated/frozen and cannot be changed by runtime output;
- same idempotency scope/hash returns existing job;
- changed snapshot under same key conflicts.

### 20.5 Job, Rerun, And Credential Lifecycle

- image request/job/snapshot persist before worker invocation;
- failed image calls remain auditable;
- video submit/poll/fetch survive restart;
- active legacy jobs route through `legacy_agnes_v1`;
- default rerun inherits code/config/model/constraints but resolves current credential;
- missing current credential returns `CREDENTIAL_MISSING`;
- historical credential mode is unavailable in M6 UI;
- active submitted/polling work uses original credential version;
- force deletion cancels/fails defined active states;
- Agnes polls by `video_id`.

### 20.6 Credential Crash Recovery

Inject process crashes after each protocol boundary:

- journal creation;
- temporary write;
- file/data fsync;
- pending-finalize database commit;
- atomic rename;
- ready commit;
- pending-delete commit;
- final file deletion.

For every boundary, restart recovery must converge to `ready`, completed deletion, or explicit `credential_storage_corrupt`; it must not expose plaintext, select another credential, or leave an active task using an unknown file.

### 20.7 Frontend And Browser

- supplier list/config/code/model management;
- TypeScript safe line/column diagnostics;
- code save affects next fake task;
- model identity/revision behavior and affected-binding warning;
- project defaults/overrides and inherited labels;
- loopback error rendering;
- fake text/image/video Playwright flow.

### 20.8 Default Network And Real Authorization

- pytest, Vitest, Playwright, worker tests, and verifier fail on unexpected real network;
- validation performs zero HTTP requests;
- no real provider request occurs without separate explicit authorization;
- real smoke-test evidence is separate from fake acceptance.

## 21. M6 Acceptance Criteria

| ID | Criterion |
|---|---|
| SUP-001 | Built-in Agnes, OpenAI, DeepSeek, Anthropic, and xAI suppliers exist with one config each. |
| SUP-002 | Product structure remains Supplier -> Models with no M6 multi-account hierarchy. |
| SUP-003 | Browser TypeScript save validates locally and creates immutable source/compiled versions. |
| SUP-004 | New work uses the saved version; existing work uses its frozen fingerprint. |
| SUP-005 | Worker denies host process/module/filesystem/environment access and exposes only versioned helpers. |
| SUP-006 | Worker timeout/output/protocol failure is terminable and recoverable. |
| SUP-007 | Validation network helpers always raise NETWORK_DISABLED_DURING_VALIDATION. |
| SUP-008 | Management APIs enforce loopback from the direct peer and reject spoofed proxy headers. |
| SUP-009 | FRP/public gateway cannot access supplier/model/binding management. |
| SUP-010 | Models use stable UUIDs and immutable revisions; bindings use supplier_model_id. |
| SUP-011 | Model edits cannot silently replace overlay/base identity or mutate old snapshots. |
| SUP-012 | Model/config/binding/supplier mutations enforce independent ETag revisions. |
| SUP-013 | Execution snapshots include compiled/runtime/compiler/helper/model/config/credential fingerprints. |
| SUP-014 | Missing historical runtime fails with SUPPLIER_RUNTIME_UNAVAILABLE. |
| SUP-015 | Rate-limit bucket is validated and frozen in the snapshot. |
| SUP-016 | Image/video request and snapshot persist before provider submission. |
| SUP-017 | Poller routes by immutable job snapshot rather than a global backend. |
| SUP-018 | Idempotency rejects changed snapshots under the same supplier/capability key. |
| SUP-019 | Default rerun inherits supplier/config/model constraints and resolves current credential. |
| SUP-020 | Missing current rerun credential returns CREDENTIAL_MISSING without creating a job. |
| SUP-021 | Active jobs retain original credentials; old credentials are not retained indefinitely for reruns. |
| SUP-022 | Credential journal recovers every tested crash boundary or fails closed as corrupt. |
| SUP-023 | Built-in restore changes current pointer without deleting history. |
| SUP-024 | POST /api/suppliers creates a new custom empty-template supplier, not a duplicate. |
| SUP-025 | Active legacy Agnes jobs use explicit legacy snapshot routing. |
| SUP-026 | Default verification performs zero real provider requests. |
| SUP-027 | Real smoke tests require separate explicit authorization. |
| SUP-028 | Existing M1-M5 history, results, and safety gates remain readable and do not regress. |

## 22. M6 Implementation Plan Decomposition

Every stage below produces an independently reviewable branch/commit series, uses default real-network denial, and does not submit a real provider request during normal tests.

### M6A Supplier Core

**Goal:** Establish schemas, immutable supplier/config/credential versions, Node worker protocol, isolated execution, compilation fingerprints, and loopback management guard.

**Not in scope:** Project bindings, provider adapter cutover, management UI beyond API fixtures, real provider requests.

**Migration boundary:** Add supplier/version/config/credential/journal/migration-ledger schema without changing existing runtime/provider selection.

**Acceptance:** Worker isolation/fingerprint, ETag supplier/config mutations, credential crash recovery, loopback guard, and zero-network tests pass.

**Rollback point:** Disable new supplier routes/worker, restore pre-M6 schema backup, and leave existing global backend paths unchanged.

### M6B Model Catalog And Binding

**Goal:** Add stable model identities/revisions, model overlays, project defaults/operation overrides, resolver, independent ETags, and snapshot value object.

**Not in scope:** Existing provider cutover, poller routing, browser code editor, real provider requests.

**Migration boundary:** Add model/model-revision/binding tables and deterministic built-in UUID mapping; do not modify historical jobs/runs.

**Acceptance:** Model identity, overlay, deletion/disable, binding resolution, ETag, request hash, and idempotency tests pass with fake adapters.

**Rollback point:** Stop writing bindings/snapshots, remove unreferenced M6B rows through the migration rollback procedure, and retain M6A supplier data.

### M6C Adapter Cutover

**Goal:** Move OpenAI-compatible text and Agnes image/video to TypeScript supplier contracts; route image/video jobs and poller by immutable snapshot; preserve legacy compatibility.

**Not in scope:** Management UI, new real DeepSeek/Anthropic/xAI validation, real smoke requests.

**Migration boundary:** Add run/job snapshot references, create legacy Agnes snapshot/runtime records, and move image generation into durable jobs before switching code paths.

**Acceptance:** Fake text/image/video execution, restart polling, `video_id`, rerun/credential semantics, legacy active-job routing, M1-M5 regression, and zero-network tests pass.

**Rollback point:** Feature-flag resolver/worker execution off and return to legacy OpenAI/Agnes adapters while preserving new snapshot evidence for audit.

### M6D Management UI

**Goal:** Deliver supplier list/config/secret/code editor/model management and project binding pages with loopback error handling.

**Not in scope:** Marketplace, supplier duplication, multiple accounts, remote management, real model-test buttons.

**Migration boundary:** No new production data migration; UI consumes M6A-M6C APIs and existing migrated rows.

**Acceptance:** Vitest and Playwright cover config/secret/code/model/binding workflows, ETag conflicts, local-only errors, restore, and fake execution.

**Rollback point:** Remove/disable M6 UI routes while leaving backend data and legacy UI/API behavior intact.

### M6E Migration And Acceptance

**Goal:** Finalize migration recovery, fake-provider E2E, verifier/report, Playwright, and complete M1-M5 regression evidence.

**Not in scope:** New provider capabilities, batch generation, production rollout, or real provider requests without a separate later authorization.

**Migration boundary:** Exercise fresh and legacy stores, credential crash journals, active legacy jobs, replay/idempotency, and final cutover readiness; no irreversible deletion of legacy fields.

**Acceptance:** All SUP-001..SUP-028 criteria, full Python/Web/build/E2E suites, migration replay/recovery, and deterministic JSON/Markdown verifier reports pass.

**Rollback point:** Keep M6 execution feature flags disabled, retain migration evidence, and continue existing M1-M5 runtime paths until a separately approved cutover.

## 23. Final Verification Contract

```bash
python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
python3 tools/verify_supplier_model_configuration.py
git diff --check
```

The verifier emits JSON and Markdown with `PASS`, `FAIL`, or `SKIPPED` per criterion and uses semantic success checks rather than a fixed test count.

No implementation begins before the revised design and M6 governance are approved.
