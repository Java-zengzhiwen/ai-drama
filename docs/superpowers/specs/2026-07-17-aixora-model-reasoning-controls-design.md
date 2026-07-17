# AIXORA Model Reasoning Controls Design

Date: 2026-07-17

Status: `APPROVED_DIRECTION_AWAITING_WRITTEN_SPEC_CONFIRMATION`

Branch: `feat/aixora-adapter-model-archive`

## Decision

Adopt the approved option A:

1. add the AIXORA text model `gpt-5.6` with a stable model identity;
2. let every AIXORA text model define its own default reasoning effort;
3. let the model-level real-test dialog override that default for one test;
4. apply the same model default to current project text operations through the immutable execution snapshot;
5. disable the unavailable `gpt-image-2` model without deleting its revisions, test history, or snapshots.

This increment remains inside the existing `Supplier -> Models` product structure. It does not add provider discovery UI, automatic catalog synchronization, a new credential model, or a new database table.

## Confirmed Runtime Evidence

One authenticated, non-generating AIXORA metadata request was made on 2026-07-17:

```text
GET https://www.aixora.store/v1/models
HTTP_STATUS=200
MODEL_COUNT=7
GPT_MODELS=gpt-5.4,gpt-5.4-mini,gpt-5.5,gpt-5.6,gpt-5.6-luna,gpt-5.6-sol,gpt-5.6-terra
IMAGE_MODELS=none
HAS_GPT_IMAGE_2=false
```

The latest real `gpt-image-2` test returned `PROVIDER_ROUTE_OR_MODEL_NOT_FOUND`. The combination of a 404-category generation response and an authenticated model catalog with no image model means this account/gateway does not currently expose the configured image capability. The implementation must not guess another image model or endpoint.

The existing AIXORA adapter already sends the Responses API shape:

```json
{
  "reasoning": {
    "effort": "medium"
  }
}
```

The missing product contract is model-level persistence and UI/API propagation, not the final HTTP field itself.

## Model Catalog Changes

### Add `gpt-5.6`

Add one built-in manifest declaration:

```text
supplier_model_id=07c95486e414569bb18f694431f3ad4f
provider_model_name=gpt-5.6
display_name=GPT-5.6
capability=text
default_reasoning_effort=medium
```

The stable ID is immutable. Saving a later display name, Provider name, or reasoning default creates a new immutable `model_revision_id`; it never replaces historical revision objects.

### Existing text models

The following models receive an explicit model-level default of `medium` in their manifest definition:

```text
gpt-5.5
gpt-5.6
gpt-5.6-sol
gpt-5.6-luna
gpt-5.6-terra
```

The model definition stores the value under:

```json
{
  "constraints": {
    "reasoning_effort": "medium"
  }
}
```

No schema migration is required because model definitions are already immutable JSON objects referenced by model revisions.

### Disable `gpt-image-2`

Remove `gpt-image-2` from the current AIXORA manifest. Existing manifest reconciliation will set the built-in model to `enabled=false` while preserving:

- `supplier_model_id`;
- all immutable model revisions;
- model test rows and sanitized evidence;
- execution snapshots and historical reads.

The disabled row remains visible in supplier management with its test action unavailable. It is excluded from new project bindings and new execution resolution. Re-enabling requires later Provider evidence and a separately reviewed manifest revision.

## Reasoning Effort Contract

Phase 1 exposes the conservative selectable values:

```text
low
medium
high
```

The adapter may continue reading older snapshot/config values already accepted by its compatibility allowlist, but the new UI does not advertise unverified AIXORA values such as `minimal`, `none`, `xhigh`, or `max`. Expanding the UI list requires separate real Provider evidence.

Resolution precedence is deterministic:

```text
explicit request override
-> current model revision default
-> current supplier config default
-> medium
```

The resolved value is frozen into `ExecutionSnapshot.resolved_constraints.reasoning_effort` before network submission. The Worker invocation receives the frozen constraints separately from the mutable current model/config state. The AIXORA adapter resolves:

```text
payload.request.parameters.reasoning_effort
-> payload.constraints.reasoning_effort
-> payload.config.reasoning_effort
-> medium
```

Existing submitted jobs and completed runs remain tied to their original snapshot. Editing a model default affects only new work.

## API And Service Changes

### Model definition

Existing model create/edit APIs remain revision/ETag conditional. For text models, the UI writes `definition.constraints.reasoning_effort`. Invalid or unsupported values fail locally as `INVALID_REASONING_EFFORT`; no Provider request is made.

### Model test create

Extend the existing loopback-only endpoint:

```text
POST /api/models/{supplier_model_id}/tests
```

with an optional field:

```json
{
  "prompt": "...",
  "reasoning_effort": "high"
}
```

Rules:

- accepted only for `capability=text`;
- accepted values are `low`, `medium`, and `high`;
- omitted means follow the model default;
- request hash and idempotency include the effective reasoning choice;
- the immutable test snapshot records the resolved value before submission;
- safe test reads return the effective `reasoning_effort` for audit and UI display;
- image tests reject the field with `MODEL_TEST_REASONING_UNSUPPORTED`.

One confirmation still authorizes exactly one real submission. Recovery never creates a second submission.

### Project text execution

`M6GenerationCoordinator.execute_text` resolves the model revision definition before creating the run. It merges an optional request override with the model default and supplier fallback, freezes the effective value in the snapshot, and invokes the exact compiled adapter artifact. Existing project bindings continue referencing the stable `supplier_model_id`; no binding migration is needed.

### Worker payload

`SnapshotExecutionGateway` adds only the frozen provider-neutral field:

```json
{
  "constraints": {
    "reasoning_effort": "medium"
  }
}
```

Credentials, raw Provider responses, and mutable current definitions are not added to snapshots or browser responses.

## UI Design

### Model create/edit dialog

For `capability=text`, add a labeled select above the existing advanced JSON field:

```text
默认思考深度: 低 / 中 / 高
```

Changing it updates `definition.constraints.reasoning_effort` while preserving unrelated definition keys. Opening an existing model reads the value from its current immutable definition. Invalid advanced JSON continues to block save.

For image/video models, the control is hidden.

### Model test dialog

For text models, add:

```text
本次思考深度:
- 跟随模型默认（当前：中）
- 低
- 中
- 高
```

The selection locks with the prompt after confirmation and is included in recovery state so page refresh cannot accidentally change the idempotent request. The completed result displays the effective value next to elapsed time and token usage.

For disabled models, the existing disabled-test behavior remains unchanged.

## Error Handling

```text
INVALID_REASONING_EFFORT
MODEL_TEST_REASONING_UNSUPPORTED
MODEL_DISABLED
IDEMPOTENCY_CONFLICT
PROVIDER_ROUTE_OR_MODEL_NOT_FOUND
```

- Local validation errors make zero Provider requests.
- Changing reasoning effort while reusing an idempotency key returns `IDEMPOTENCY_CONFLICT`.
- A Provider rejection is sanitized and does not cause fallback to another effort or model.
- No automatic retry, model discovery, or image-model substitution is added.

## Testing Plan

All automated tests use fake/local transports and zero real Provider requests.

### Backend

- manifest contains exactly five enabled AIXORA text models including plain `gpt-5.6`;
- manifest reconciliation disables but does not delete `gpt-image-2` history;
- model definition accepts `low/medium/high` and rejects invalid values locally;
- test request override wins over model and supplier defaults;
- model default wins over supplier default;
- omitted values fall back to `medium`;
- effective effort enters snapshot and exact Worker payload;
- image test rejects reasoning effort before job creation;
- idempotency conflicts when effective reasoning changes;
- project text runs use model default and preserve existing binding IDs;
- historical snapshots remain readable and deterministic.

### Adapter And Worker

- AIXORA `textRequest` sends the frozen resolved effort;
- explicit request override wins;
- no current model definition is read during snapshot execution;
- credential and sanitized evidence contracts remain unchanged.

### Web

- text model create/edit shows the default reasoning select;
- editing preserves unrelated advanced definition JSON;
- image/video forms hide the control;
- text model test dialog shows follow-default and three explicit levels;
- submitted payload and recovery state include the selected override;
- completed result displays the effective level;
- disabled `gpt-image-2` cannot be tested or selected for a new binding.

### Regression

- full Python suite;
- Worker suite;
- Web Vitest suite and production build;
- Playwright M6D/M6E flows;
- AIXORA and model-level semantic verifiers;
- migration verifier;
- `git diff --check` and tracked-secret scan.

## Acceptance Criteria

1. AIXORA supplier catalog contains enabled `gpt-5.5`, `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-luna`, and `gpt-5.6-terra`.
2. `gpt-image-2` is disabled, remains historically readable, and cannot create a new test or binding.
3. Each text model has an immutable model-level default reasoning effort.
4. The model test dialog can follow the model default or override it with low/medium/high.
5. New project text runs use the frozen precedence contract and never read mutable current settings after snapshot creation.
6. Different effective reasoning with the same idempotency key fails closed.
7. Existing jobs, results, model test history, credentials, and project bindings remain intact.
8. Automated verification performs zero real Provider requests.
9. Any later real reasoning-level acceptance is initiated only by an explicit user model-test confirmation or a separate provider-specific authorization.

## Rollback

- Switch AIXORA to the previous immutable supplier version to remove plain `gpt-5.6` and restore the prior manifest.
- Switch affected text models to their prior immutable model revisions to remove model defaults.
- Existing snapshots continue using their frozen supplier/model/config/runtime fingerprints.
- Do not delete the disabled image identity or historical evidence during rollback.

## Out Of Scope

- automatic `/models` synchronization;
- AIXORA image endpoint/model guessing;
- enabling `gpt-5.4` or `gpt-5.4-mini`;
- exposing unverified reasoning levels;
- per-user accounts or multiple AIXORA connections;
- video models;
- retries, fallbacks, batches, or production rollout;
- real Provider calls in automated tests, CI, verifiers, or reviewers.
