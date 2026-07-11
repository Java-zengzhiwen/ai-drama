# Provider Model Management Design

**Status:** Approved design draft for user review

**Date:** 2026-07-12

**Scope:** Provider catalog, connection management, model profiles, project model bindings, runtime resolution, migration, testing, and acceptance

**Out of scope:** Dynamic plugin loading, automatic failover, production batch generation, billing aggregation, and unrestricted real-provider calls

## 1. Product Goal

AI Drama must let an operator configure multiple model providers in one place and choose which provider connection and model each project uses for text, image, and video work.

The system must support:

- project-level default text, image, and video models;
- optional per-operation model overrides;
- multiple connections for the same provider;
- built-in provider templates plus manually managed model profiles;
- provider-specific adapters behind a provider-neutral configuration and resolution layer;
- safe browser-based secret management;
- deterministic, auditable model selection for every run and generation job.

The first built-in provider templates are:

- Agnes;
- OpenAI / ChatGPT;
- DeepSeek;
- Anthropic Claude API;
- xAI Grok.

## 2. Confirmed Decisions

The design freezes the following user-approved choices:

1. A project has one default model per capability and may override individual workflow operations.
2. A provider can have multiple named connections, such as test and production accounts.
3. The model catalog combines built-in templates with manually added, edited, and disabled model profiles. Automatic provider discovery may be added later where supported.
4. `Anthropic` means the Anthropic Claude API, not the Claude Code CLI.
5. Delivery is phased: establish the unified configuration and resolution core first, then add provider-specific adapters in independently testable batches.
6. Resolution fails closed. The system never silently changes provider or model.
7. The architecture uses a unified provider catalog and capability adapters, not provider-specific settings silos and not a dynamic plugin system.
8. API keys are configured in the browser, masked during input, and never returned after storage.
9. xAI is modeled as supporting text, image, and video. Its exact model IDs, endpoints, request fields, and asynchronous status contract must be pinned from current official xAI documentation before each adapter is implemented.

## 3. Current-System Problem

The current implementation has separate configuration paths:

- Agnes has a dedicated `/api/settings/agnes` secret endpoint and settings page.
- Agnes image and video model identifiers are process settings.
- the Web application creates one global generation backend at startup;
- text runs accept `provider` and `model` per request and may fall back to process environment variables;
- project records do not own model bindings;
- existing run and generation records persist provider/model evidence, but there is no shared resolution layer.

Adding another provider through the current pattern would duplicate settings pages, environment variables, factories, request rules, and error handling. The new design replaces these separate entry points with one configuration domain while preserving existing run history.

## 4. Architecture

The configuration and execution flow is:

```text
ProviderType registry
  -> ProviderConnection
  -> ModelProfile
  -> ProjectModelBinding
  -> ModelResolver
  -> ResolvedModelSnapshot
  -> capability adapter
  -> existing runtime/job persistence
```

### 4.1 ProviderType

`ProviderType` is a code-owned registry entry describing an integration family. It is not an operator-created database row.

Each entry defines:

- stable key, such as `agnes`, `openai`, `deepseek`, `anthropic`, or `xai`;
- display name;
- supported capabilities: `text`, `image`, and/or `video`;
- adapter keys per capability;
- connection-field schema;
- safe default Base URL where applicable;
- whether no-cost online verification is available;
- whether each capability adapter is executable in the current release.

Provider templates remain visible even when an adapter is not implemented. A non-executable capability is labeled `adapter_unavailable` and cannot be selected in a project binding.

### 4.2 ProviderConnection

`ProviderConnection` is an operator-managed account or endpoint configuration.

Required fields:

```text
connection_id
provider_type_key
display_name
base_url
secret_ref
status: enabled | disabled
config_object_id
created_at
updated_at
```

`secret_ref` is an opaque reference. It never contains the secret value. Provider-specific non-secret settings use a validated structured object stored through the existing content-addressed object store.

Multiple connections may reference the same provider type. Connection names must be unique within one provider type.

### 4.3 ModelProfile

`ModelProfile` represents one configured upstream model on one connection.

Required fields:

```text
model_profile_id
connection_id
display_name
upstream_model_id
capability: text | image | video
adapter_key
defaults_object_id
constraints_object_id
status: enabled | disabled
created_at
updated_at
```

Connection scope is intentional: two accounts can expose the same upstream model with different access, endpoint, defaults, or constraints.

Built-in model templates seed profiles when an operator creates a connection. Operators may add, edit, or disable profiles. The first release does not require automatic model discovery.

### 4.4 ProjectModelBinding

Bindings select a `ModelProfile` for a project. There are two scopes:

- `capability_default`: one default for `text`, `image`, or `video`;
- `operation_override`: an optional override for one registered workflow operation.

Required fields:

```text
project_id
scope_type: capability_default | operation_override
capability
operation_key: nullable for capability_default
model_profile_id
created_at
updated_at
```

Uniqueness rules allow one binding for each project/capability default and one binding for each project/operation override.

Project bindings select models only. Provider/model defaults and task request data supply parameters in the first release. Arbitrary project-level parameter overrides are deferred to avoid an unvalidated parameter editor.

### 4.5 ResolvedModelSnapshot

`ResolvedModelSnapshot` is an immutable value object persisted with each newly created run or generation request. It is not a mutable settings table.

It contains:

```text
provider_type_key
connection_id
model_profile_id
upstream_model_id
capability
operation_key
binding_source: operation_override | capability_default
adapter_key
resolved_defaults
resolved_constraints
configuration_updated_at
```

It excludes API keys, authorization headers, signed asset URLs, and other credentials. Existing provider/model fields remain populated for backward compatibility and reporting.

Changing a connection, model profile, or project binding affects only future runs. Existing runs, jobs, reruns, and results continue using their creation-time snapshot.

## 5. Capability And Operation Registry

The operation registry is code-owned and prevents arbitrary operation strings from bypassing capability validation.

### 5.1 Text Operations

```text
source_segmentation       Original text splitting
script_adaptation         Script adaptation
material_extraction       Character, scene, and prop material extraction
character_bible           Character bible generation
scene_bible               Scene bible generation
prop_bible                Prop bible generation
storyboard_design         Storyboard design
visual_anchor_planning    Visual reference planning
image_prompt_generation   Image prompt generation
shot_prompt_generation    Video/shot prompt generation
```

### 5.2 Image Operations

```text
character_reference_image
scene_reference_image
prop_reference_image
storyboard_keyframe_image
```

### 5.3 Video Operations

```text
shot_video_generation
```

New operations require a registry change and tests. They do not require a database schema migration.

## 6. Resolution And Execution

The resolver uses this exact order:

```text
operation override
  -> project capability default
  -> MODEL_BINDING_MISSING
```

There is no automatic cross-provider fallback and no runtime environment fallback for new resolved tasks.

Before a provider request, the resolver and preflight layer verify:

1. the project exists;
2. the operation is registered and maps to the requested capability;
3. the binding exists;
4. the connection exists and is enabled;
5. the secret is configured when required;
6. the model profile exists and is enabled;
7. the model capability matches the operation;
8. the provider type declares the capability;
9. the adapter is executable;
10. input count, media type, and parameters satisfy model constraints.

Only after all checks pass may the adapter be called. The resolved snapshot is created before network submission so failed provider calls remain auditable.

Provider adapters translate the provider-neutral request into an upstream request. Text, image, and video adapters have separate protocols. A provider may implement one, two, or all three.

Asynchronous video adapters persist the provider-defined query identifier. Agnes polling uses `video_id`, never `task_id`.

## 7. Built-In Capability Matrix

| Provider | Text | Image | Video |
|---|---:|---:|---:|
| Agnes | Yes | Yes | Yes |
| OpenAI / ChatGPT | Yes | Yes | Not enabled in initial scope |
| DeepSeek | Yes | No | No |
| Anthropic Claude | Yes | No | No |
| xAI Grok | Yes | Yes | Yes |

The matrix expresses product capability targets. Actual project selection additionally requires an executable adapter and an enabled model profile.

Exact model IDs are data, not schema enums. Built-in model templates may be updated without changing project binding semantics.

## 8. API Design

### 8.1 Provider Types And Connections

```text
GET    /api/provider-types
GET    /api/provider-connections
POST   /api/provider-connections
GET    /api/provider-connections/{connection_id}
PATCH  /api/provider-connections/{connection_id}
DELETE /api/provider-connections/{connection_id}
PUT    /api/provider-connections/{connection_id}/secret
DELETE /api/provider-connections/{connection_id}/secret
POST   /api/provider-connections/{connection_id}/verify
```

Connection responses return `secret_configured` and `masked_suffix`; they never return a secret or secret reference path.

Deletion returns HTTP 409 when models or project bindings still reference the connection. The first release uses explicit disable/delete operations and never cascades.

`verify` uses a no-cost authentication or model-list endpoint when the provider offers one. Otherwise it performs local configuration validation and returns `online_verification: unavailable`. It must not call a text, image, or video generation endpoint.

### 8.2 Model Profiles

```text
GET    /api/provider-connections/{connection_id}/models
POST   /api/provider-connections/{connection_id}/models
GET    /api/models/{model_profile_id}
PATCH  /api/models/{model_profile_id}
DELETE /api/models/{model_profile_id}
```

Deletion returns HTTP 409 while any project binding references the profile.

### 8.3 Project Bindings And Resolution Preview

```text
GET /api/projects/{project_id}/model-bindings
PUT /api/projects/{project_id}/model-bindings
GET /api/projects/{project_id}/model-resolution/{operation_key}
```

The binding update is atomic: either the complete submitted binding set is valid and saved, or no binding changes are applied.

The resolution preview calls the same resolver used by execution. It returns the selected connection and model metadata, binding source, readiness, and safe blocking reasons.

## 9. Browser Experience

### 9.1 Global Provider Management

The main navigation adds `Model Providers` / `模型供应商`.

The page shows:

- provider templates and capability badges;
- connections grouped by provider;
- connection name, Base URL, enabled state, secret status, and verification state;
- connection-specific text, image, and video model profiles;
- adapter availability and configuration blockers.

Operators can create multiple connections for one provider, manage model profiles, validate a connection, and disable or delete unused configuration.

### 9.2 Project Model Configuration

Each project adds a `模型配置` view.

It shows:

- three project defaults: text, image, and video;
- operation overrides grouped by capability;
- `继承项目默认` for operations without an override;
- connection/model options filtered by capability and executable adapter status;
- a readiness summary with actionable blocking reasons;
- the resolution preview for each operation.

The UI cannot bind a text model to an image/video operation or bind a disabled/unavailable model.

### 9.3 Secret Interaction

Secrets are fully manageable in the browser under these rules:

- the input is masked by default;
- an eye icon may reveal only the value currently typed and not yet submitted;
- saving clears the input immediately;
- stored secrets are displayed only as `已配置 ....ABCD`;
- a stored secret cannot be retrieved or revealed, only replaced or deleted;
- the raw secret must not appear in the DOM after save, query cache, API responses, errors, logs, database, or persisted snapshots;
- replacement and deletion show the connection name and affected project count;
- remote browser access, if enabled later, must require HTTPS for secret submission.

## 10. Errors And Security

Stable configuration and provider error codes include:

```text
MODEL_BINDING_MISSING
PROVIDER_CONNECTION_DISABLED
PROVIDER_SECRET_MISSING
MODEL_PROFILE_DISABLED
MODEL_CAPABILITY_MISMATCH
PROVIDER_ADAPTER_UNAVAILABLE
PROVIDER_AUTHENTICATION
PROVIDER_RATE_LIMITED
PROVIDER_QUOTA_EXCEEDED
PROVIDER_INVALID_REQUEST
PROVIDER_TIMEOUT
PROVIDER_BUSY
PROVIDER_UNKNOWN
```

Configuration errors are detected before network submission. Provider errors preserve sanitized evidence without raw authorization data or signed URLs.

The generalized local secret store uses one opaque secret file per connection, atomic replacement, and file mode `0600`. Secret paths are derived from validated opaque IDs, never user-supplied path fragments.

Base URLs must use HTTPS except explicit loopback development endpoints. URLs containing embedded credentials are rejected. Provider-specific URL validation must not weaken existing public asset delivery checks.

## 11. Migration

Migration is additive, transactional, and idempotent.

### 11.1 Agnes

- Create one `Agnes Default` connection when legacy Agnes configuration exists.
- Reference the existing Agnes secret through the generalized secret store migration without copying plaintext into SQLite.
- Create image and video model profiles from current Agnes settings.
- Preserve all existing generation jobs, provider IDs, results, reviews, and reruns unchanged.

### 11.2 Legacy Text Runtime

- Create a read-only `Legacy OpenAI-compatible` connection when complete environment-backed text runtime configuration exists.
- Its credential source may remain an environment reference during migration; the secret value is not copied into SQLite.
- Create a model profile from the configured legacy model.
- Create explicit project text defaults only when the legacy configuration is complete and deterministic.
- When legacy configuration is incomplete, leave the project visibly blocked instead of inventing a binding.

### 11.3 Cutover

After migration, all newly created Web tasks resolve through `ModelResolver`. Existing historical records remain readable without a resolved snapshot. Environment variables remain migration inputs and compatibility references, not silent selection fallbacks for new tasks.

Migration tests compare fresh and upgraded schemas, replay the migration, and verify rollback on injected failure.

## 12. Delivery Phases

### Phase 1: Unified Configuration And Existing-Adapter Closure

Deliver:

- provider registry;
- connection, model profile, binding, resolver, snapshot, and secret APIs;
- provider management and project model configuration UI;
- migration from current Agnes and environment-backed text configuration;
- existing OpenAI-compatible text execution through the resolver;
- existing Agnes image/video execution through the resolver;
- fake-provider end-to-end acceptance;
- no real provider calls in default verification.

All five provider templates are visible. Capabilities without an implemented adapter are not bindable.

### Phase 2: Independent Provider Adapter Batches

Implement and accept separately:

1. Agnes text;
2. OpenAI image;
3. DeepSeek text;
4. Anthropic text;
5. xAI text;
6. xAI image;
7. xAI video.

Each batch requires current official documentation review, a pinned contract, fake HTTP contract tests, error mapping, secret redaction, full regression, and a separately authorized real smoke test.

The xAI batches may not freeze endpoint paths, model names, request fields, or polling identifiers until official xAI documentation is reachable and reviewed. Live retrieval from the current environment timed out on 2026-07-12; this design therefore freezes capability intent, not an unverified wire contract.

## 13. Test Plan

### 13.1 Store And Migration Tests

Verify:

- fresh and migrated schemas are equivalent;
- migration replay creates no duplicates;
- connection/model/binding constraints hold;
- deletion conflicts do not cascade;
- existing history is byte-for-byte unchanged where applicable;
- secret values never enter SQLite;
- injected migration failures roll back atomically.

### 13.2 Resolver Unit Tests

Verify:

- operation override wins over capability default;
- capability default is inherited when no override exists;
- missing bindings fail closed;
- disabled connections/models fail before adapter invocation;
- missing secrets fail before adapter invocation;
- capability mismatches fail deterministically;
- unavailable adapters cannot resolve executable work;
- configuration changes do not mutate existing snapshots;
- preview and execution call the same resolver.

### 13.3 API And Secret Tests

Verify:

- multiple connections per provider;
- connection/model/binding CRUD and validation;
- atomic binding updates;
- secret create, replace, and delete;
- secret responses contain status and mask only;
- no raw secret in response bodies, tracebacks, logs, SQLite, object storage, or snapshots;
- `verify` never calls a paid generation endpoint;
- referenced connections/models return HTTP 409 on delete.

### 13.4 Adapter Contract Tests

Use `respx` or local fakes; default tests have no real internet access.

For each adapter, verify:

- endpoint, method, authentication, and request mapping;
- model ID and capability mapping;
- input count, media type, and parameter constraints;
- success response parsing;
- timeout, authentication, rate limit, quota, invalid-input, busy, and unknown-error mapping;
- response/evidence sanitization;
- asynchronous job identifier persistence and polling;
- Agnes video polling uses `video_id`.

### 13.5 Frontend Component Tests

Use Vitest and Testing Library to verify:

- provider, connection, model, and project binding views;
- secret masking, local reveal, post-save clearing, replacement, and deletion;
- full secrets never remain in the DOM or query cache;
- capability-filtered model selection;
- inherited and overridden labels;
- loading, empty, blocked, conflict, and save-failure states;
- readiness and resolution preview rendering.

### 13.6 Browser End-To-End Tests

Use Playwright with fake providers to execute:

```text
create two connections for one provider
  -> configure masked secrets in the browser
  -> add text/image/video model profiles
  -> set project defaults
  -> set a storyboard text override
  -> reload and verify persistence
  -> execute fake text/image/video tasks
  -> verify immutable resolved snapshots
  -> disable the selected connection
  -> verify new work is blocked before provider invocation
```

### 13.7 Real Smoke Tests

Real tests are opt-in, one controlled request per authorized adapter/capability, and excluded from default test commands.

Before each real request:

- current official documentation contract is recorded;
- configuration and no-cost verification are ready;
- rate/cost limits are set;
- an exact provider/capability authorization is present;
- no unrelated batch or retry is enabled.

Without authorization, the test reports `SKIPPED` and makes no request. Existing Agnes governance and authorization requirements remain binding.

## 14. Acceptance Matrix

### 14.1 Phase 1 Product Acceptance

| ID | Criterion |
|---|---|
| PMM-001 | Agnes, OpenAI, DeepSeek, Anthropic, and xAI provider templates are visible. |
| PMM-002 | xAI declares text, image, and video product capabilities. |
| PMM-003 | One provider supports multiple named connections. |
| PMM-004 | Operators manage connection secrets entirely in the browser. |
| PMM-005 | Stored secrets can be replaced/deleted but never retrieved. |
| PMM-006 | Operators manage connection-scoped text/image/video model profiles. |
| PMM-007 | A project can select text, image, and video defaults. |
| PMM-008 | Every registered operation can inherit or override its capability default. |
| PMM-009 | Resolution preview and execution resolve the same model. |
| PMM-010 | Existing OpenAI-compatible text runs use resolved configuration. |
| PMM-011 | Existing Agnes image/video jobs use resolved configuration. |
| PMM-012 | Invalid or unavailable configuration fails before a provider request. |
| PMM-013 | No automatic provider/model fallback occurs. |
| PMM-014 | Existing run/job/result history remains readable and unchanged. |
| PMM-015 | Configuration changes affect new work only. |

### 14.2 Security Acceptance

| ID | Criterion |
|---|---|
| PMM-SEC-001 | Full secrets are absent from GET responses and persisted records. |
| PMM-SEC-002 | Secret files use atomic writes and mode `0600`. |
| PMM-SEC-003 | The frontend clears submitted secret input and renders only a mask. |
| PMM-SEC-004 | Logs, errors, reports, and snapshots redact credentials and signed URLs. |
| PMM-SEC-005 | Connection verification never submits paid generation. |
| PMM-SEC-006 | Referenced configuration cannot be deleted by cascade. |

### 14.3 Quality Acceptance

| ID | Criterion |
|---|---|
| PMM-QA-001 | Migration is transactional, idempotent, and covered for fresh/legacy stores. |
| PMM-QA-002 | Unit, API, contract, frontend, build, and Playwright suites pass. |
| PMM-QA-003 | Default verification makes zero real provider requests. |
| PMM-QA-004 | Acceptance uses semantic pass/fail checks, not a fixed test count. |
| PMM-QA-005 | A verifier emits JSON and Markdown with PASS/FAIL/SKIPPED per criterion. |
| PMM-QA-006 | Existing M1-M5 behavior and safety gates do not regress. |

### 14.4 Phase 2 Adapter Acceptance

| ID | Criterion |
|---|---|
| PMM-ADP-001 | Current official provider documentation is linked and contract-reviewed. |
| PMM-ADP-002 | Fake HTTP contract and error mapping tests pass. |
| PMM-ADP-003 | Provider evidence contains no secret. |
| PMM-ADP-004 | Full regression passes before real testing. |
| PMM-ADP-005 | One explicit authorization permits only one scoped smoke request. |
| PMM-ADP-006 | The real result records provider, connection, model, query ID, and timing. |
| PMM-ADP-007 | Missing authorization produces SKIPPED with zero network submission. |

## 15. Verification Commands

The implementation plans must preserve these final gates:

```bash
python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
python3 tools/verify_provider_model_management.py
git diff --check
```

`tools/verify_provider_model_management.py` will emit deterministic JSON and Markdown reports with `PASS`, `FAIL`, or `SKIPPED` for each acceptance criterion. Default execution must not require credentials and must not contact a real provider.

## 16. Non-Goals

The initial design does not include:

- automatic provider failover;
- weighted routing or load balancing;
- dynamic Python/JavaScript plugin installation;
- provider billing dashboards or budget enforcement;
- project-level arbitrary parameter editors;
- team roles or multi-user secret sharing;
- batch real-provider acceptance;
- automatic model discovery as a release requirement;
- Claude Code CLI as a model provider.

These can be designed independently after the core resolution contract is stable.

## 17. Implementation Planning Boundary

This design is intentionally broader than one safe implementation batch. After user review, implementation planning must be split into:

1. Phase 1 core configuration, migration, UI, resolver, and existing-adapter closure;
2. one separate Phase 2 plan per provider capability adapter.

Phase 1 must be complete and accepted before any Phase 2 adapter changes the production execution path.
