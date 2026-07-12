# Toonflow-Style Supplier And Project Model Configuration Design

**Status:** Revised design for user review

**Date:** 2026-07-12

**Target milestone:** Future M6; implementation is not authorized under the current M5 governance

## 1. Goal

AI Drama will provide a Toonflow-style local supplier experience:

- each supplier owns one TypeScript adapter, one configuration form, and one model list;
- the supplier code can be edited in the browser and saved without restarting the application;
- a project selects default text, image, and video models;
- individual workflow operations may override the project defaults;
- secrets are entered in the browser, masked after save, and never returned as plaintext;
- new work uses the latest saved supplier code while existing work continues using its creation-time code version.

The first built-in suppliers are Agnes, OpenAI, DeepSeek, Anthropic, and xAI.

## 2. Phase 1 Scope

Phase 1 delivers only the minimum closed loop:

1. Supplier list and enable/disable state.
2. One configuration set per supplier: one API key, Base URL, and non-secret fields.
3. Browser TypeScript editor with compile and contract validation.
4. Text, image, and video model declarations in the supplier script.
5. Browser add/edit/disable actions for supplier models.
6. Project defaults for text, image, and video.
7. Optional operation-level model overrides.
8. Runtime resolution and immutable execution evidence.
9. Existing OpenAI-compatible text and Agnes image/video paths migrated into the new supplier interface.
10. Fake-provider end-to-end acceptance without real network access.

Phase 1 does not include:

- multiple accounts under one supplier;
- supplier duplication;
- ZIP or Git supplier installation;
- a supplier marketplace or digital signatures;
- automatic model discovery;
- automatic failover;
- weighted routing or load balancing;
- billing and quota dashboards;
- remote multi-user permissions;
- supported exposure of supplier management APIs beyond loopback;
- real provider model-test buttons in the default verification path.

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

There is no separate ProviderType/ProviderConnection hierarchy in Phase 1.

A supplier instance is:

```text
TypeScript adapter code
+ configuration field schema
+ one set of configuration values
+ one secret
+ model declarations
+ enabled/disabled state
```

If multiple accounts are needed later, supplier duplication can be designed as a separate feature.

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
  inputs: VendorInput[];
  inputValues: Record<string, string>;
  models: SupplierModel[];
}
```

`inputs` supports `text`, `password`, and `url`. `inputValues` contains safe defaults only. Persisted user values are stored outside the source code.

### 4.2 Model Capabilities

Text models declare:

```text
name, modelName, type=text, think
```

Image models declare:

```text
name, modelName, type=image
mode: text | singleImage | multiReference
reference limits
supported sizes/aspect ratios
```

Video models declare:

```text
name, modelName, type=video
mode: text | singleImage | start/end frame | multimodal references
reference limits by media type
audio support
duration/resolution combinations
```

Phase 1 omits TTS from project binding and execution. The TypeScript template may reserve a future `ttsRequest` export.

Manifest models are the supplier's base models. The browser may add or edit a small supplier model overlay without rewriting TypeScript. Effective models are merged by `(type, modelName)`, with the local overlay winning. Base models may be disabled but not physically deleted through the model form; editing the TypeScript remains the way to change or remove a base declaration. Custom overlay models may be deleted when no project binding references them.

### 4.3 Runtime Exports

AI Drama borrows Toonflow's single-file editing experience but uses a restart-safe asynchronous contract:

```typescript
exports.vendor = vendor;
exports.textRequest = textRequest;
exports.imageRequest = imageRequest;
exports.videoSubmit = videoSubmit;
exports.videoPoll = videoPoll;
exports.videoFetch = videoFetch;
```

`textRequest` returns normalized text and usage data.

`imageRequest` returns either bytes/base64 or a provider URL. AI Drama persists a generation job before calling it and stores the final bytes in the existing object store.

`videoSubmit` submits exactly once and returns the provider query identifier plus sanitized response evidence. `videoPoll` performs one status query. `videoFetch` retrieves one completed result. Supplier scripts must not contain an internal loop that polls until completion.

This separation allows queued and submitted work to survive application restart. Agnes `videoPoll` uses `video_id`, never `task_id`.

## 5. Browser Experience

### 5.1 Supplier Page

The main navigation adds `模型供应商`.

Each supplier shows:

- name, author, version, capabilities, and enabled state;
- API Key status and masked suffix;
- Base URL and other manifest-defined fields;
- text, image, and video models;
- TypeScript code editor;
- `校验并保存` and `恢复内置版本` actions.

Saving performs local compile and contract validation only. It does not call a real provider.

### 5.2 Secret Interaction

- API keys are entered in a masked input.
- An eye control may reveal only the unsaved value currently in the input.
- Successful save clears the input.
- Stored values are shown only as `已配置 ....ABCD`.
- Stored secrets can be replaced or deleted but never retrieved through the API.
- Secret values are absent from supplier TypeScript, normal SQLite columns, logs, errors, browser query cache, and execution evidence.

### 5.3 Project Model Page

Each project shows three defaults:

```text
Default text model
Default image model
Default video model
```

Operations may inherit a default or select an explicit override.

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

The UI filters models by capability and never permits a text model to bind to an image or video operation.

## 6. Save And Hot-Reload Semantics

The browser never overwrites the code used by an existing task.

Saving supplier code performs:

```text
compile TypeScript
-> execute manifest-only validation
-> validate required exports
-> canonicalize manifest
-> store source and compiled artifacts
-> calculate code_hash and manifest_hash
-> create immutable supplier version
-> atomically move current_version_id
```

Every successful save creates a new internal supplier version even when the user-visible `vendor.version` is unchanged.

During save validation, network helpers are replaced with local functions that throw `NETWORK_DISABLED_DURING_VALIDATION`. Supplier scripts must not perform top-level network calls. Real network helpers are injected only for an explicit workflow execution.

New tasks use the new current version. Draft, queued, submitting, submitted, or polling jobs retain their original supplier version.

Editing an included supplier creates a local override version. The original included source remains available for `恢复内置版本`.

## 7. Local TypeScript Worker

The Python Web service delegates TypeScript compilation, validation, and execution to a local Node worker through a versioned JSON protocol.

The worker supports:

```text
validate
text_request
image_request
video_submit
video_poll
video_fetch
```

The worker loads the exact source/compiled object identified by the execution snapshot, not the supplier's current mutable version.

Supplier scripts are treated as trusted local code. Phase 1 does not add signatures, remote approval, or a public package sandbox. The worker receives only the selected supplier's configuration and secret for the current operation.

Supplier management remains supported only while the Web service is bound to loopback. Exposing the management API through a reverse proxy or public listener is outside Phase 1 support.

## 8. Configuration And Credential Revisions

Although the UI presents one simple supplier configuration, the backend preserves minimal immutable evidence required by queued work:

- every supplier code save creates `supplier_version_id`;
- every non-secret configuration save creates `config_revision_id` and `config_hash`;
- every model overlay save advances the same configuration revision and hash;
- every API key replacement creates `credential_version_id`;
- new work uses the current three revisions;
- active work retains its selected revisions.

Old credential versions remain available only while referenced by non-terminal jobs. They can be retired after all referenced jobs become completed, failed, or cancelled.

Deleting a secret with active work requires an explicit force action. Force deletion cancels draft/queued work and marks submitted/polling work locally failed with `credential_revoked`; it does not imply provider-side cancellation.

Disabling a supplier blocks new work but allows existing work to drain using its stored revisions.

## 9. Execution Snapshot

Every new Web project run and generation job stores an immutable `ExecutionSnapshot` before any provider request:

```text
snapshot_schema_version
supplier_id
supplier_version_id
supplier_code_hash
manifest_hash
adapter_contract_version
model_name
capability
operation_key
binding_source
config_revision_id
config_hash
credential_version_id
resolved_constraints
created_at
```

The snapshot excludes plaintext secrets. The snapshot object is stored in the content-addressed object store, and its object ID is recorded on the run/job row.

For runtime `runs`, `resolved_snapshot_object_id` is added to the run record and included in the runtime request hash.

For `generation_jobs`, `resolved_snapshot_object_id` is added to the job record and included in the generation request hash.

Terminal legacy records may keep an empty snapshot. Active legacy Agnes jobs are backfilled before the poller starts with an explicit `legacy_agnes_v1` supplier version derived from the legacy endpoint, model, and credential reference. They are never routed through the project's current binding.

## 10. Project Binding Resolution

Resolution order remains:

```text
operation override
-> project capability default
-> MODEL_BINDING_MISSING
```

There is no automatic fallback.

The complete binding set has a monotonic `binding_set_revision`. Updates require `If-Match`; stale browser tabs receive HTTP 409 and must reload rather than silently overwrite newer selections.

## 11. Idempotency

Generation idempotency is scoped by:

```text
UNIQUE(supplier_id, capability, idempotency_key)
```

The canonical `request_hash` includes the normalized provider-neutral request and the execution snapshot hash.

Behavior:

- same scope, key, and request hash returns the existing job;
- same scope/key with a different request or snapshot returns `IDEMPOTENCY_CONFLICT`;
- configuration changes therefore require a new idempotency key;
- different suppliers may use the same client key.

Legacy rows keep their existing `(provider, idempotency_key)` interpretation and are read through a compatibility path.

## 12. Persistent Image And Video Work

Image generation is moved into the existing `generation_jobs` table, which already supports `job_type=image`.

The sequence is:

```text
resolve binding
-> persist request + snapshot + draft job in one database transaction
-> transition to submitting
-> call TypeScript imageRequest
-> persist sanitized response and result
-> create generated asset referencing the local job
```

A failed provider call leaves a failed job with its request and snapshot.

Video jobs use the same pre-submit persistence, then the existing poller calls `videoSubmit`, `videoPoll`, and `videoFetch` through the job's supplier snapshot.

The poller no longer owns one global backend. It resolves the worker adapter per job snapshot. Rate limiting uses a supplier-declared bucket key; the default bucket is the supplier ID.

## 13. Rerun Semantics

Two explicit actions are defined:

1. `重新运行`: default; inherits the source job's execution snapshot.
2. `使用当前项目模型重新运行`: explicitly resolves the current project binding and creates a new snapshot.

Both record:

```text
source_job_id
resolution_mode
source_snapshot_hash
new_snapshot_hash
overrides_object_id
```

## 14. Local Validation And Real Requests

`校验并保存` is always local and performs no provider request.

Phase 1 does not add a generic online verification endpoint. Real text, image, and video calls occur only through explicit workflow actions and remain governed by the active provider authorization rules.

Existing Agnes governance remains binding. The current M5 token does not authorize a provider abstraction rewrite or database expansion. Before implementation, repository governance must establish M6 scope, branches, and real-provider authorization rules.

Default tests and the acceptance verifier reject real network traffic at the transport layer.

## 15. Migration

Migration uses a `schema_migrations` ledger and a single transactional migration for database rows.

It creates:

- built-in supplier records and immutable initial versions;
- one Agnes configuration from existing settings and secret reference;
- one OpenAI-compatible text supplier configuration when legacy environment settings are complete;
- explicit project bindings only where legacy selection is deterministic;
- execution snapshots for active legacy Agnes jobs before the poller starts.

Terminal history remains unchanged and readable through compatibility code.

Secret-file writes cannot participate in SQLite transactions. Migration therefore writes and validates temporary secret files first, commits database references second, atomically renames files last, and records compensating cleanup on failure.

## 16. API Surface

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
PATCH  /api/suppliers/{supplier_id}/models/{model_name}
DELETE /api/suppliers/{supplier_id}/models/{model_name}

GET    /api/projects/{project_id}/model-bindings
PUT    /api/projects/{project_id}/model-bindings
GET    /api/projects/{project_id}/model-resolution/{operation_key}
```

Code/config/binding updates use revision or ETag preconditions. No GET endpoint returns secret plaintext.

## 17. Test Plan

### 17.1 Supplier Contract Tests

- compile valid and invalid TypeScript;
- validate manifest and required exports;
- reject duplicate supplier IDs and duplicate capability/model names;
- validate image/video input modes and limits;
- merge manifest models and local model overlays deterministically;
- prevent deletion of a base model or a bound custom model;
- verify each save creates an immutable version and hash;
- verify restore selects the included version without deleting local history.

### 17.2 Hot-Reload And Snapshot Tests

- new tasks use the newly saved supplier version;
- queued/submitted jobs continue using the old version;
- worker loads code by snapshot object ID;
- config and credential changes affect new work only;
- supplier disable blocks new work and drains active work;
- force credential deletion produces deterministic terminal states.

### 17.3 Binding And Idempotency Tests

- operation override wins over project default;
- missing binding fails before worker invocation;
- capability mismatch is rejected;
- stale `If-Match` returns conflict;
- same idempotency scope/hash returns the existing job;
- same scope/key with a changed snapshot returns conflict;
- different suppliers can reuse a key.

### 17.4 Job And Rerun Tests

- image request/snapshot/job persist before worker invocation;
- failed image calls remain auditable;
- video submit/poll/fetch survive service restart;
- poller routes active legacy jobs through `legacy_agnes_v1`;
- default rerun inherits the source snapshot;
- explicit current-model rerun resolves a new snapshot;
- Agnes polls by `video_id`.

### 17.5 Secret Tests

- browser/API never receive stored plaintext;
- submitted inputs are cleared;
- SQLite, supplier code, object metadata, logs, and errors contain no plaintext secret;
- secret files use mode `0600` and atomic writes;
- failed database/file coordination performs compensating cleanup.

### 17.6 Frontend And Browser Tests

- supplier list, enable/disable, config form, model list, and code editor;
- TypeScript validation errors include safe line/column diagnostics;
- code save takes effect for the next fake task;
- project default and operation override selection;
- inherited model labels and blocked configuration states;
- full fake text/image/video project flow through Playwright.

### 17.7 Network Safety Tests

- default pytest, Vitest, Playwright, and verifier runs fail on attempted real network access;
- local supplier validation performs zero HTTP requests;
- no test invokes Agnes or any other real provider without the required authorization.

## 18. Phase 1 Acceptance Criteria

| ID | Criterion |
|---|---|
| SUP-001 | Agnes, OpenAI, DeepSeek, Anthropic, and xAI appear as built-in suppliers. |
| SUP-002 | Each supplier has exactly one Phase 1 configuration set. |
| SUP-003 | Supplier TypeScript is editable in the browser. |
| SUP-004 | Save performs local validation and creates an immutable version. |
| SUP-005 | New work uses the saved version without application restart. |
| SUP-006 | Existing work retains its creation-time supplier version. |
| SUP-007 | Included supplier source can be restored. |
| SUP-008 | Supplier models declare and enforce text/image/video capabilities. |
| SUP-009 | Browser model management merges local model overlays with TypeScript base models. |
| SUP-010 | API keys are configurable in the browser and never retrievable. |
| SUP-011 | Projects select text/image/video defaults and operation overrides. |
| SUP-012 | Resolution is fail-closed and has no automatic fallback. |
| SUP-013 | Binding updates reject stale revisions. |
| SUP-014 | Image and video requests persist request/snapshot evidence before network submission. |
| SUP-015 | Poller routes by job snapshot rather than a global backend. |
| SUP-016 | Idempotency distinguishes suppliers and rejects changed snapshots under the same key. |
| SUP-017 | Default rerun inherits its source snapshot; current-model rerun is explicit. |
| SUP-018 | Legacy active Agnes jobs use an explicit legacy route. |
| SUP-019 | Default verification performs zero real provider requests. |
| SUP-020 | Existing M1-M5 history, results, and safety gates remain readable and do not regress. |
| SUP-021 | Supplier management remains loopback-only in the supported Phase 1 deployment. |

## 19. Final Verification

```bash
python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
python3 tools/verify_supplier_model_configuration.py
git diff --check
```

The verifier emits JSON and Markdown with `PASS`, `FAIL`, or `SKIPPED` for each criterion. It uses semantic success checks rather than a fixed test count.

## 20. Implementation Planning Boundary

After this revised design is approved:

1. update repository governance from M5 to an approved M6 scope;
2. write one Phase 1 implementation plan for the supplier core, Node worker, migration, UI, resolver, and existing adapter cutover;
3. write separate follow-up plans for real DeepSeek, Anthropic, and xAI contract verification and smoke tests.

No implementation begins before the governance and design review gates are complete.
