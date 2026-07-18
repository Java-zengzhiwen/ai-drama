# AIXORA Model Reasoning Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add model-level reasoning defaults and one-test overrides for AIXORA text models, add the plain `gpt-5.6` model, and safely disable the unavailable `gpt-image-2` declaration without deleting history.

**Architecture:** Resolve reasoning once at the provider-neutral service boundary and freeze it in `ExecutionSnapshot.resolved_constraints`; the Worker receives that immutable constraint and the AIXORA adapter translates it to the Provider request. Reuse immutable model definition revisions, existing manifest reconciliation, existing model-test durability, and existing loopback-only APIs; no database migration or alternate image route is introduced.

**Tech Stack:** Python 3, FastAPI/Pydantic, SQLite-backed ProductStore, TypeScript supplier adapters, React/TypeScript, Vitest/Testing Library, pytest, Playwright.

## Global Constraints

- Automated implementation and verification make zero real Provider requests.
- Exposed reasoning values are exactly `low`, `medium`, and `high`.
- Resolution precedence is request override, model revision default, supplier config default, then `medium`.
- The effective value is frozen in `ExecutionSnapshot.resolved_constraints.reasoning_effort` before submission.
- Existing snapshots, model revisions, test history, credentials, and stable model IDs remain readable.
- `gpt-image-2` is disabled through manifest reconciliation; it is not physically deleted or automatically substituted.
- All model-test and supplier-management APIs remain loopback-only and revision/ETag conditional.
- A confirmed model test authorizes exactly one submission; no automatic retry or fallback is added.
- The main agent is the sole writer and committer. After verification, two independent read-only agents review specification compliance and technical/security quality.

## File Map

- Create `ai_drama_web/suppliers/reasoning.py`: provider-neutral validation and precedence resolution.
- Modify `ai_drama_web/services/m6_generation.py`: resolve model-definition reasoning before snapshot creation.
- Modify `ai_drama_web/suppliers/execution.py`: pass immutable snapshot constraints to the Worker.
- Modify `ai_drama_web/suppliers/model_tests.py`: validate model-test override, freeze it, hash it, and return it safely.
- Modify `ai_drama_web/schemas/model_tests.py` and `ai_drama_web/routers/model_tests.py`: accept and expose the optional reasoning field.
- Modify `ai_drama_web/suppliers/custom_adapters/aixora.ts`: five-model text manifest and frozen-constraint consumption.
- Modify `web/src/features/suppliers/SupplierModelsPanel.tsx`: AIXORA text-model default select.
- Modify `web/src/features/suppliers/ModelTestDialog.tsx` and `web/src/features/suppliers/api.ts`: one-test override, recovery, and result display.
- Modify focused Python and Web tests plus the existing AIXORA verifier/report.

---

### Task 1: Provider-Neutral Reasoning Resolution And Snapshot Payload

**Files:**
- Create: `ai_drama_web/suppliers/reasoning.py`
- Modify: `ai_drama_web/services/m6_generation.py`
- Modify: `ai_drama_web/suppliers/execution.py`
- Test: `tests/web/test_m6c_adapter_cutover.py`
- Test: `tests/web/test_execution_snapshot.py`

**Interfaces:**
- Produces: `resolve_reasoning_effort(*, request, model_definition, supplier_config) -> str`.
- Produces: Worker payload key `constraints: dict` copied from the immutable snapshot.
- Consumes: model definition objects from `model_revision.definition_object_id` and config objects from `config_revision.config_object_id`.

- [ ] **Step 1: Write failing resolution and execution-payload tests**

Add table-driven tests asserting request > model > supplier > `medium`, invalid values raise `INVALID_REASONING_EFFORT`, `execute_text` freezes the model default, and `SnapshotExecutionGateway.invoke` sends `snapshot.resolved_constraints` rather than reading a current model definition.

```python
@pytest.mark.parametrize(
    ("request", "definition", "config", "expected"),
    [
        ({"parameters": {"reasoning_effort": "high"}}, {"constraints": {"reasoning_effort": "low"}}, {"reasoning_effort": "medium"}, "high"),
        ({}, {"constraints": {"reasoning_effort": "low"}}, {"reasoning_effort": "high"}, "low"),
        ({}, {}, {"reasoning_effort": "high"}, "high"),
        ({}, {}, {}, "medium"),
    ],
)
def test_reasoning_resolution_precedence(request, definition, config, expected):
    assert resolve_reasoning_effort(
        request=request, model_definition=definition, supplier_config=config
    ) == expected
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_m6c_adapter_cutover.py tests/web/test_execution_snapshot.py
```

Expected: failure because `reasoning.py` and Worker `constraints` do not exist.

- [ ] **Step 3: Implement the minimal resolver and snapshot propagation**

Create the validator without Provider-specific branching:

```python
REASONING_EFFORTS = frozenset({"low", "medium", "high"})


class ReasoningEffortError(RuntimeError):
    code = "INVALID_REASONING_EFFORT"


def resolve_reasoning_effort(*, request, model_definition, supplier_config):
    parameters = request.get("parameters") if isinstance(request, dict) else {}
    constraints = (
        model_definition.get("constraints")
        if isinstance(model_definition, dict)
        else {}
    )
    value = (
        (parameters or {}).get("reasoning_effort")
        or (constraints or {}).get("reasoning_effort")
        or (supplier_config or {}).get("reasoning_effort")
        or "medium"
    )
    if value not in REASONING_EFFORTS:
        raise ReasoningEffortError(value)
    return value
```

In `execute_text`, read the resolved immutable model definition and selected config, resolve the value, and pass `{"reasoning_effort": value}` to `_resolve_snapshot`. In `SnapshotExecutionGateway`, add:

```python
payload = {
    "request": request,
    "model": snapshot.provider_model_name,
    "config": config_value,
    "constraints": dict(snapshot.resolved_constraints),
    "credential": credential,
}
```

Translate `ReasoningEffortError` to `M6GenerationError("INVALID_REASONING_EFFORT")` before persisting or invoking.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass and fake Worker payload contains the frozen effort.

- [ ] **Step 5: Commit the provider-neutral execution slice**

```bash
git add ai_drama_web/suppliers/reasoning.py ai_drama_web/services/m6_generation.py \
  ai_drama_web/suppliers/execution.py tests/web/test_m6c_adapter_cutover.py \
  tests/web/test_execution_snapshot.py
git commit -m "feat: freeze model reasoning in execution snapshots"
```

### Task 2: Model-Test API, Idempotency, And Audit Contract

**Files:**
- Modify: `ai_drama_web/schemas/model_tests.py`
- Modify: `ai_drama_web/routers/model_tests.py`
- Modify: `ai_drama_web/suppliers/model_tests.py`
- Test: `tests/web/test_supplier_model_tests.py`

**Interfaces:**
- Consumes: `resolve_reasoning_effort` and `REASONING_EFFORTS` from Task 1.
- Produces: `ModelTestCreate.reasoning_effort: Literal["low", "medium", "high"] | None`.
- Produces: `ModelTestRead.reasoning_effort: str` with the effective frozen value for text tests and an empty string for image tests.

- [ ] **Step 1: Write failing service and router tests**

Cover omitted override using model default, explicit override winning, invalid value returning 422/`INVALID_REASONING_EFFORT`, image override returning `MODEL_TEST_REASONING_UNSUPPORTED` before row creation, safe reads exposing the effective value, and the same idempotency key with a changed effort returning `IDEMPOTENCY_CONFLICT`.

```python
run, created = service.create_model_test(
    supplier_model_id=model.supplier_model_id,
    prompt="explain this scene",
    reasoning_effort="high",
    idempotency_key="reasoning-test-1",
    expected_model_revision=model.revision,
)
assert created is True
snapshot = load_snapshot(store, run["snapshot_hash"])
assert snapshot.resolved_constraints["reasoning_effort"] == "high"
assert service.safe_read(run["test_run_id"])["reasoning_effort"] == "high"
```

- [ ] **Step 2: Run the model-test suite and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py
```

Expected: failures for the new argument, schema field, and response field.

- [ ] **Step 3: Implement validation, persistence, and safe reads**

Extend the schema and service signature:

```python
ReasoningEffort = Literal["low", "medium", "high"]

class ModelTestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=4000)
    reasoning_effort: ReasoningEffort | None = None
```

For text tests, put an explicit override in `request.parameters`, resolve against the model definition and config, and freeze it in `resolved_constraints`. For image tests, reject any non-`None` override before writing a request object, snapshot, or run. Include the request parameters and snapshot hash in the existing canonical request hash. In `safe_read`, load the snapshot and return:

```python
result["reasoning_effort"] = str(
    snapshot.resolved_constraints.get("reasoning_effort") or ""
)
```

Pass `payload.reasoning_effort` through the router. Map the explicit service validation codes to HTTP 422 without waking the runner.

- [ ] **Step 4: Run the model-test suite and verify GREEN**

Run the Step 2 command. Expected: all model-test tests pass and fake gateway invocation remains exactly once.

- [ ] **Step 5: Commit the model-test contract**

```bash
git add ai_drama_web/schemas/model_tests.py ai_drama_web/routers/model_tests.py \
  ai_drama_web/suppliers/model_tests.py tests/web/test_supplier_model_tests.py
git commit -m "feat: add reasoning overrides to model tests"
```

### Task 3: AIXORA Manifest And Adapter Cutover

**Files:**
- Modify: `ai_drama_web/suppliers/custom_adapters/aixora.ts`
- Modify: `tests/web/test_aixora_adapter.py`
- Modify: `tests/web/test_supplier_models.py`

**Interfaces:**
- Consumes: Worker payload `constraints.reasoning_effort` from Task 1.
- Produces: exactly five enabled built-in AIXORA text declarations, including stable ID `07c95486e414569bb18f694431f3ad4f` for `gpt-5.6`.

- [ ] **Step 1: Write failing adapter and reconciliation tests**

Assert the manifest has five text models, every definition contains `constraints.reasoning_effort == "medium"`, no current image declaration exists, and reconciliation turns an existing built-in `gpt-image-2` row off while preserving its ID/revision. Assert adapter precedence is request > frozen constraints > config > medium.

```python
assert [model["provider_model_name"] for model in artifact.vendor["models"]] == [
    "gpt-5.5", "gpt-5.6", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.6-terra"
]
assert all(
    model["definition"]["constraints"]["reasoning_effort"] == "medium"
    for model in artifact.vendor["models"]
)
```

- [ ] **Step 2: Run focused adapter/catalog tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_aixora_adapter.py tests/web/test_supplier_models.py
```

Expected: old four-text-plus-image manifest and missing frozen-constraint fallback fail.

- [ ] **Step 3: Update the manifest and adapter**

Add `constraints?: { reasoning_effort?: string }` to the payload type. Define each text model with an immutable ID and:

```typescript
definition: { constraints: { reasoning_effort: "medium" } }
```

Add plain `gpt-5.6` with stable ID `07c95486e414569bb18f694431f3ad4f`. Remove only the current `gpt-image-2` declaration. Resolve:

```typescript
const reasoningEffort = validateReasoningEffort(
  payload.request?.parameters?.reasoning_effort
    || payload.constraints?.reasoning_effort
    || payload.config?.reasoning_effort
    || "medium",
);
```

Do not add discovery, fallback, or a replacement image route.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass; no network is used.

- [ ] **Step 5: Commit the AIXORA artifact**

```bash
git add ai_drama_web/suppliers/custom_adapters/aixora.ts \
  tests/web/test_aixora_adapter.py tests/web/test_supplier_models.py
git commit -m "feat: update AIXORA text model manifest"
```

### Task 4: Model Management And Model-Test UI

**Files:**
- Modify: `web/src/features/suppliers/api.ts`
- Modify: `web/src/features/suppliers/api.test.ts`
- Modify: `web/src/features/suppliers/SupplierModelsPanel.tsx`
- Modify: `web/src/features/suppliers/SupplierModelsPanel.test.tsx`
- Modify: `web/src/features/suppliers/ModelTestDialog.tsx`
- Modify: `web/src/features/suppliers/ModelTestDialog.test.tsx`

**Interfaces:**
- Consumes: model definition `constraints.reasoning_effort` and model-test fields from Task 2.
- Produces: AIXORA text-model default selector and optional one-test override with refresh-safe recovery.

- [ ] **Step 1: Write failing API and component tests**

Test that the AIXORA text editor shows `默认思考深度`, changes only `definition.constraints.reasoning_effort`, and preserves unrelated JSON; image/video editors hide it. Test that the text test dialog shows `跟随模型默认（当前：中）`, submits an explicit choice, persists it with idempotency state, restores it after remount, locks it after confirmation, and displays the effective result. Disabled models remain untestable.

```typescript
expect(api.createModelTest).toHaveBeenCalledWith(
  model.supplier_model_id,
  prompt,
  "high",
  model.etag,
  expect.any(String),
);
```

- [ ] **Step 2: Run focused Web tests and verify RED**

```bash
npm --prefix web run test -- --run \
  src/features/suppliers/api.test.ts \
  src/features/suppliers/SupplierModelsPanel.test.tsx \
  src/features/suppliers/ModelTestDialog.test.tsx
```

Expected: missing select, API argument, recovery field, and result rendering failures.

- [ ] **Step 3: Implement model editor select without clobbering JSON**

Parse the draft definition into an object, update only:

```typescript
definition.constraints = {
  ...(definition.constraints ?? {}),
  reasoning_effort: value,
};
```

Show the select only when `supplier.slug === "aixora" && draft.capability === "text"`. Values are `low`, `medium`, `high`, with Chinese labels `低`, `中`, `高`. Existing missing values display `中`.

- [ ] **Step 4: Implement test override, API payload, and recovery**

Change `createModelTest` to accept `reasoningEffort: "low" | "medium" | "high" | null` and omit the JSON field when it is `null`. Extend saved session state to:

```typescript
type RecoveryState = {
  idempotencyKey: string;
  testRunId?: string;
  reasoningEffort: "low" | "medium" | "high" | null;
};
```

Restore the value before recovery polling, disable the select once submission starts, and render `实际思考深度：低/中/高` from `result.reasoning_effort`.

- [ ] **Step 5: Run focused Web tests and verify GREEN**

Run the Step 2 command. Expected: all selected Vitest tests pass.

- [ ] **Step 6: Commit the UI slice**

```bash
git add web/src/features/suppliers/api.ts web/src/features/suppliers/api.test.ts \
  web/src/features/suppliers/SupplierModelsPanel.tsx \
  web/src/features/suppliers/SupplierModelsPanel.test.tsx \
  web/src/features/suppliers/ModelTestDialog.tsx \
  web/src/features/suppliers/ModelTestDialog.test.tsx
git commit -m "feat: expose AIXORA reasoning controls"
```

### Task 5: Runtime Reconciliation, Verification, And Review Handoff

**Files:**
- Modify: `tools/verify_aixora_adapter_models.py`
- Modify: `docs/superpowers/reports/2026-07-17-aixora-adapter-model-archive-verification.md`
- Test: `tests/tools/test_verify_aixora_adapter_models.py`

**Interfaces:**
- Consumes: all Task 1-4 contracts.
- Produces: machine-checkable zero-real-request evidence and a report suitable for the required two-reviewer handoff.

- [ ] **Step 1: Write failing semantic-verifier assertions**

Require the five enabled text models, disabled preserved image row, supported UI effort set, snapshot constraint propagation, model-test override/audit behavior, idempotency conflict, and zero real network. Do not bind acceptance to a fixed total test count.

- [ ] **Step 2: Run the verifier test and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/tools/test_verify_aixora_adapter_models.py
```

Expected: missing new semantic checks fail.

- [ ] **Step 3: Update the verifier and report contract**

The verifier must print stable check IDs and:

```text
REAL_PROVIDER_REQUESTS=false
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

Update the report with exact commands, pass/fail evidence, model reconciliation result, production flag state, and explicit statement that no real generation request was executed during implementation.

- [ ] **Step 4: Run focused and full verification**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_m3_agnes_generation.py
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m6c_adapter_cutover.py
python3 tools/verify_m6d_management_ui.py
python3 tools/verify_m6e_migration_acceptance.py
python3 tools/verify_aixora_adapter_models.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: every command exits 0, real request counts remain zero, and the production M6 execution flag remains false unless the existing local test service explicitly enables its already-approved fake/runtime path.

- [ ] **Step 5: Apply the built-in manifest to local runtime and inspect safely**

Restart the existing local service through its checked-in/LaunchAgent mechanism, then use only loopback management reads to confirm five enabled AIXORA text models and one preserved disabled `gpt-image-2` row. Do not press the real-test confirmation button and do not invoke any Provider endpoint.

- [ ] **Step 6: Request two independent read-only reviews**

Reviewer 1 checks the approved design and acceptance contract. Reviewer 2 checks architecture, security, idempotency, snapshot determinism, and regression risk. Both review the exact implementation commit and must report `BLOCKERS=NONE` and `HIGH_FINDINGS=NONE`; fix any blocker/high finding with a new TDD commit and rerun Step 4.

- [ ] **Step 7: Commit the verification descendant**

```bash
git add tools/verify_aixora_adapter_models.py \
  tests/tools/test_verify_aixora_adapter_models.py \
  docs/superpowers/reports/2026-07-17-aixora-adapter-model-archive-verification.md
git commit -m "docs: verify AIXORA reasoning controls"
```

- [ ] **Step 8: Push the reviewed branch and prepare handoff**

```bash
git push origin feat/aixora-adapter-model-archive
```

Provide repository, branch, final commit SHA, repository-relative report path, and PR or compare URL. Do not merge to `main` without separate user approval.
