# Model Parameter Selects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace free-form reasoning configuration with model-aware selects and add effective GPT Image 2 size and quality defaults plus per-test overrides that reach immutable project and model-test execution snapshots.

**Architecture:** Extend the supplier manifest with validated select metadata, resolve provider-neutral reasoning/image controls before snapshot creation, and let the existing isolated Worker consume only frozen values. Supplier config supplies defaults; model-test requests may override them once. Existing SQLite objects and revision fields are sufficient, so no migration is added.

**Tech Stack:** Python 3, FastAPI/Pydantic, SQLite-backed ProductStore, TypeScript supplier adapters and Worker compiler, React/TypeScript, Ant Design, pytest, Vitest/Testing Library, Playwright.

## Global Constraints

- Work only on `feat/model-parameter-selects`; do not mutate `main` during implementation.
- Automated implementation and verification make zero real Provider requests.
- GPT-5.6-family reasoning values are exactly `none`, `low`, `medium`, `high`, `xhigh`, `max`.
- GPT-5.5 reasoning values are exactly `none`, `low`, `medium`, `high`, `xhigh`.
- GPT Image 2 sizes are exactly `auto`, `1024x1024`, `1024x1536`, `1536x1024`; legacy non-GPT models preserve their declared Provider-specific size values.
- GPT Image 2 qualities are exactly `auto`, `low`, `medium`, `high`.
- Do not expose `2K`, `4K`, arbitrary dimensions, retry, or model fallback.
- Supplier config is the default; a request override wins and is frozen in the immutable snapshot.
- Existing credentials, stable model IDs, model revisions, jobs, test runs, and runtime history remain readable.
- Model-test and supplier-management APIs remain application-layer loopback-only and ETag/idempotency conditional.
- Credentials, Provider URLs, runtime databases, runtime objects, and private results never enter Git.

## File Map

- Modify `worker/src/compiler.mjs`: validate manifest select declarations before a supplier version can be saved.
- Modify `tests/web/test_supplier_compiler.py`: cover valid and malformed select manifests.
- Modify `ai_drama_web/routers/suppliers.py`: reject config values outside declared select options.
- Modify `tests/web/test_supplier_api.py`: cover server-side config-select enforcement.
- Modify `web/src/features/suppliers/api.ts`: type manifest options and expanded model-test fields.
- Modify `web/src/features/suppliers/SupplierConfigForm.tsx`: render manifest-driven selects and validate legacy values.
- Modify `web/src/features/suppliers/SupplierDetailPage.test.tsx`: cover select rendering, save, and invalid-state behavior.
- Modify `ai_drama_web/suppliers/reasoning.py`: expand model-aware reasoning values and supplier-default precedence.
- Create `ai_drama_web/suppliers/image_options.py`: validate and resolve image size and quality.
- Modify `ai_drama_web/services/m6_generation.py`: freeze text and image controls before project execution.
- Modify `tests/web/test_m6c_adapter_cutover.py`: cover project resolution and immutable Worker payloads.
- Modify `ai_drama_web/schemas/model_tests.py`, `ai_drama_web/routers/model_tests.py`, and `ai_drama_web/suppliers/model_tests.py`: accept, persist, recover, and safely return model-test overrides.
- Modify `tests/web/test_supplier_model_tests.py`: cover image options, reasoning sets, idempotency, and compatibility.
- Modify `ai_drama_web/suppliers/custom_adapters/aixora.ts`: publish select metadata and consume exact frozen values.
- Modify `tests/web/test_aixora_adapter.py`: cover manifest values and exact Provider request payloads.
- Modify `web/src/features/suppliers/ModelTestDialog.tsx`: render model-aware text and image controls.
- Modify `web/src/features/suppliers/ModelTestDialog.test.tsx` and `web/src/features/suppliers/api.test.ts`: cover submission and recovery.
- Modify `web/src/app/app.css`: align select controls with the existing management UI.
- Modify `docs/superpowers/specs/2026-07-19-model-parameter-selects-design.md` only if implementation uncovers a reviewed contract correction.

---

### Task 1: Manifest Selects And Supplier Config Enforcement

**Files:**
- Modify: `worker/src/compiler.mjs`
- Modify: `tests/web/test_supplier_compiler.py`
- Modify: `ai_drama_web/routers/suppliers.py`
- Modify: `tests/web/test_supplier_api.py`
- Modify: `web/src/features/suppliers/api.ts`
- Modify: `web/src/features/suppliers/SupplierConfigForm.tsx`
- Modify: `web/src/features/suppliers/SupplierDetailPage.test.tsx`

**Interfaces:**
- Consumes: `vendor.inputs[]` objects from the compiled supplier manifest.
- Produces: `SupplierInput.options?: Array<{value: string; label: string; description?: string}>`.
- Produces: local/compiler error `INVALID_VENDOR_MANIFEST` and API error `INVALID_SUPPLIER_CONFIG_VALUE`.

- [ ] **Step 1: Write failing compiler, API, and Web tests**

Add a compiler fixture containing a valid select and malformed fixtures with duplicate/empty values. Add an API test that saves an undeclared value and asserts HTTP 422 without a new config revision. Add a Web test that renders a select and submits its selected string.

```python
def test_supplier_config_rejects_value_outside_manifest_select(client, supplier):
    response = client.put(
        f"/api/suppliers/{supplier['supplier_id']}/config",
        headers={"If-Match": '"config-1"'},
        json={"values": {"reasoning_effort": "turbo"}},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "INVALID_SUPPLIER_CONFIG_VALUE"
```

```typescript
expect(screen.getByRole("combobox", { name: "默认思考深度" })).toHaveValue("medium");
fireEvent.change(screen.getByRole("combobox", { name: "默认思考深度" }), {
  target: { value: "high" },
});
expect(put).toHaveBeenCalledWith(
  "/suppliers/supplier-1/config",
  { values: expect.objectContaining({ reasoning_effort: "high" }) },
  expect.any(Object),
);
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_compiler.py tests/web/test_supplier_api.py
npm --prefix web run test -- --run src/features/suppliers/SupplierDetailPage.test.tsx
```

Expected: failures because select options are neither validated nor rendered.

- [ ] **Step 3: Implement the compiler and server validators**

In the Worker compiler, validate every select input:

```javascript
function validInput(input) {
  if (!input || typeof input !== "object") return false;
  if (typeof input.key !== "string" || !input.key) return false;
  if (input.type !== "select") return true;
  if (!Array.isArray(input.options) || input.options.length === 0) return false;
  const values = input.options.map(option => option?.value);
  return values.every(value => typeof value === "string" && value.length > 0)
    && new Set(values).size === values.length
    && input.options.every(option => typeof option?.label === "string" && option.label.length > 0);
}
```

Require `vendor.inputs.every(validInput)` in `validateVendor`. In the supplier router, read the current immutable manifest, build an allowed-value map for `type=select`, validate the merged config before writing its object, and raise:

```python
raise HTTPException(
    422,
    detail={"error_code": "INVALID_SUPPLIER_CONFIG_VALUE", "field": key},
)
```

- [ ] **Step 4: Render select inputs without changing legacy text behavior**

Extend the API types and render:

```tsx
{field.type === "select" && Array.isArray(field.options) ? (
  <select
    aria-label={label}
    required={Boolean(field.required)}
    value={values[key] ?? supplier.input_values[key] ?? ""}
    onChange={(event) => setValues(current => ({ ...current, [key]: event.target.value }))}
  >
    {field.options.map(option => (
      <option key={option.value} value={option.value}>{option.label}</option>
    ))}
  </select>
) : (
  <Input
    aria-label={label}
    required={Boolean(field.required)}
    value={values[key] ?? supplier.input_values[key] ?? ""}
    onChange={(event) =>
      setValues(current => ({ ...current, [key]: event.target.value }))
    }
  />
)}
```

If a stored legacy value is not present, show an inline error and disable save until the user chooses a valid option. Do not silently change the value.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 commands. Expected: all selected tests pass.

- [ ] **Step 6: Commit the select infrastructure**

```bash
git add worker/src/compiler.mjs tests/web/test_supplier_compiler.py \
  ai_drama_web/routers/suppliers.py tests/web/test_supplier_api.py \
  web/src/features/suppliers/api.ts web/src/features/suppliers/SupplierConfigForm.tsx \
  web/src/features/suppliers/SupplierDetailPage.test.tsx
git commit -m "feat: add manifest driven supplier selects"
```

### Task 2: Provider-Neutral Parameter Resolution For Project Work

**Files:**
- Modify: `ai_drama_web/suppliers/reasoning.py`
- Create: `ai_drama_web/suppliers/image_options.py`
- Modify: `ai_drama_web/services/m6_generation.py`
- Modify: `tests/web/test_m6c_adapter_cutover.py`
- Modify: `tests/web/test_execution_snapshot.py`

**Interfaces:**
- Produces: `supported_reasoning_efforts(model_definition) -> tuple[str, ...]`.
- Produces: `resolve_reasoning_effort(*, request, model_definition, supplier_config) -> str`.
- Produces: `resolve_image_options(*, request, model_definition, supplier_config) -> dict[str, str]`.
- Consumes: immutable model definition and selected config revision.

- [ ] **Step 1: Write failing resolution and project-execution tests**

Cover supplier default over model default, request override over supplier default, GPT-5.5 rejection of `max`, image fallback, invalid image values, and `generate_image` freezing both fields before the Worker call.

```python
assert resolve_image_options(
    request={"size": "1024x1536"},
    model_definition={
        "default_size": "1024x1024",
        "constraints": {
            "supported_sizes": ["auto", "1024x1024", "1024x1536", "1536x1024"],
            "default_quality": "auto",
            "supported_qualities": ["auto", "low", "medium", "high"],
        },
    },
    supplier_config={"image_size": "1536x1024", "image_quality": "high"},
) == {"size": "1024x1536", "quality": "high"}
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_m6c_adapter_cutover.py tests/web/test_execution_snapshot.py
```

Expected: old three-value reasoning contract, old precedence, and missing image resolver fail.

- [ ] **Step 3: Implement model-aware resolvers**

Use immutable declaration lists when present and conservative fallback lists for legacy models:

```python
REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})
IMAGE_SIZES = frozenset({"auto", "1024x1024", "1024x1536", "1536x1024"})
IMAGE_QUALITIES = frozenset({"auto", "low", "medium", "high"})
```

Resolve explicit request, then supplier config, then model default, then safety default. Validate GPT-style values against the model-declared supported set. When a legacy or non-GPT image model has no supported-size list, preserve its existing non-empty Provider-specific size instead of imposing GPT Image 2 dimensions globally.

- [ ] **Step 4: Freeze controls in project snapshots**

In `_resolve_snapshot`, load definition/config once and branch by capability. Text freezes `reasoning_effort`; image freezes `size` and `quality`. Change `generate_image` to call:

```python
snapshot = self._resolve_snapshot(
    project_id,
    "storyboard_keyframe_image",
    request=request,
)
```

The original request and snapshot constraints both enter existing idempotency comparison. Do not add a schema field or read current config after enqueue.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass and fake gateway payloads contain only frozen constraints.

- [ ] **Step 6: Commit project parameter resolution**

```bash
git add ai_drama_web/suppliers/reasoning.py ai_drama_web/suppliers/image_options.py \
  ai_drama_web/services/m6_generation.py tests/web/test_m6c_adapter_cutover.py \
  tests/web/test_execution_snapshot.py
git commit -m "feat: freeze generation parameters in snapshots"
```

### Task 3: Model-Test API, Idempotency, And Recovery

**Files:**
- Modify: `ai_drama_web/schemas/model_tests.py`
- Modify: `ai_drama_web/routers/model_tests.py`
- Modify: `ai_drama_web/suppliers/model_tests.py`
- Modify: `tests/web/test_supplier_model_tests.py`

**Interfaces:**
- Consumes: Task 2 resolvers.
- Produces: optional create fields `reasoning_effort`, `size`, and `quality`.
- Produces: safe read fields `reasoning_effort`, `size`, and `quality`.

- [ ] **Step 1: Write failing service and router tests**

Cover text and image overrides, unsupported values, capability mismatch, effective-value reads, changed-override idempotency conflicts, and missing-value compatibility.

```python
run, created = service.create_model_test(
    supplier_model_id=image_model.supplier_model_id,
    prompt="a cup",
    size="1024x1536",
    quality="high",
    idempotency_key="image-options-1",
    expected_model_revision=image_model.revision,
)
assert created is True
snapshot = load_snapshot(store, run["snapshot_hash"])
assert snapshot.resolved_constraints == {"size": "1024x1536", "quality": "high"}
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_supplier_model_tests.py
```

Expected: schema/service signatures and image metadata are missing.

- [ ] **Step 3: Extend schema and service**

Use string fields with bounded lengths so service-level model declarations remain authoritative:

```python
class ModelTestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=4000)
    reasoning_effort: str | None = Field(default=None, min_length=1, max_length=16)
    size: str | None = Field(default=None, min_length=1, max_length=24)
    quality: str | None = Field(default=None, min_length=1, max_length=16)
```

Reject image fields on text and reasoning on image before writing request/snapshot/run objects. Build the canonical image request using the effective values from Task 2. Return safe effective metadata from the snapshot.

- [ ] **Step 4: Map stable local errors**

Map `INVALID_IMAGE_SIZE`, `INVALID_IMAGE_QUALITY`, and `MODEL_TEST_IMAGE_OPTIONS_UNSUPPORTED` to HTTP 422 with Chinese messages. Keep one-confirmation/one-submit behavior and existing ambiguous-outcome recovery unchanged.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all model-test tests pass and fake submission counters remain one.

- [ ] **Step 6: Commit the model-test contract**

```bash
git add ai_drama_web/schemas/model_tests.py ai_drama_web/routers/model_tests.py \
  ai_drama_web/suppliers/model_tests.py tests/web/test_supplier_model_tests.py
git commit -m "feat: add model test generation parameters"
```

### Task 4: Aixora Manifest And Exact Adapter Requests

**Files:**
- Modify: `ai_drama_web/suppliers/custom_adapters/aixora.ts`
- Modify: `tests/web/test_aixora_adapter.py`

**Interfaces:**
- Consumes: frozen Worker `constraints` and supplier config values.
- Produces: select metadata, model-specific supported lists, and exact OpenAI-compatible request fields.

- [ ] **Step 1: Write failing adapter tests**

Assert manifest options/order/defaults, GPT-5.5 omission of `max`, GPT-5.6-family inclusion of `max`, image capability lists, and exact generation/edit request bodies.

```python
assert request["body"]["size"] == "1024x1536"
assert request["body"]["quality"] == "high"
assert "2K" not in json.dumps(request)
assert "4K" not in json.dumps(request)
```

- [ ] **Step 2: Run the adapter tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_aixora_adapter.py
```

Expected: old text input metadata and missing config/default fields fail.

- [ ] **Step 3: Update the manifest**

Declare three select inputs with the exact values in the approved spec. Add immutable supported lists to each model definition. Extend `SupplierPayload.config` with `image_size` and `image_quality`.

- [ ] **Step 4: Resolve exact adapter fields**

Resolve image values without guessing:

```typescript
const size = String(
  payload.request?.size || payload.constraints?.size || payload.config?.image_size || "1024x1024"
);
const quality = String(
  payload.request?.quality || payload.constraints?.quality || payload.config?.image_quality || "auto"
);
if (!IMAGE_SIZES.has(size)) fail("INVALID_IMAGE_SIZE");
if (!IMAGE_QUALITIES.has(quality)) fail("INVALID_IMAGE_QUALITY");
```

Always include validated `size` and `quality` in generation and edit requests. Preserve credential injection, media helpers, response normalization, and URL sanitization.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all adapter tests pass with no network.

- [ ] **Step 6: Commit the adapter contract**

```bash
git add ai_drama_web/suppliers/custom_adapters/aixora.ts tests/web/test_aixora_adapter.py
git commit -m "feat: declare Aixora generation controls"
```

### Task 5: Model-Aware Test Dialog

**Files:**
- Modify: `web/src/features/suppliers/api.ts`
- Modify: `web/src/features/suppliers/api.test.ts`
- Modify: `web/src/features/suppliers/ModelTestDialog.tsx`
- Modify: `web/src/features/suppliers/ModelTestDialog.test.tsx`
- Modify: `web/src/app/app.css`

**Interfaces:**
- Consumes: immutable model definition supported lists and Task 3 API fields.
- Produces: model-specific selects, request-local overrides, and refresh-safe session recovery.

- [ ] **Step 1: Write failing API and dialog tests**

Cover GPT-5.5/GPT-5.6 option differences, follow-default state, image controls, exact API body, locked selections after submit, recovery after reload, and effective result metadata.

```typescript
expect(screen.getByRole("option", { name: "最大" })).toBeInTheDocument();
fireEvent.change(screen.getByLabelText("本次图片尺寸"), {
  target: { value: "1024x1536" },
});
fireEvent.change(screen.getByLabelText("本次图片质量"), {
  target: { value: "high" },
});
expect(api.createModelTest).toHaveBeenCalledWith(
  imageModel.supplier_model_id,
  expect.any(String),
  { reasoning_effort: null, size: "1024x1536", quality: "high" },
  expect.any(String),
  expect.any(String),
);
```

- [ ] **Step 2: Run focused Web tests and verify RED**

```bash
npm --prefix web run test -- --run \
  src/features/suppliers/api.test.ts \
  src/features/suppliers/ModelTestDialog.test.tsx
```

Expected: expanded unions, image selects, API payload, and recovery fields are missing.

- [ ] **Step 3: Implement model-aware options**

Read `supported_reasoning_efforts`, `supported_sizes`, and `supported_qualities` from `model.definition.constraints`. Fall back to the existing conservative text list or square/auto image defaults for legacy models. Labels are:

```typescript
const REASONING_LABELS = {
  none: "无额外推理", low: "低", medium: "中", high: "高", xhigh: "超高", max: "最大",
};
```

Image labels include orientation and exact API dimensions. Do not include 2K/4K.

- [ ] **Step 4: Extend create and recovery state**

Change `createModelTest` to accept one options object and only serialize non-null fields. Store `reasoningEffort`, `size`, and `quality` with the idempotency key; restore and lock all three. Completed image results display `实际尺寸` and `实际质量`.

- [ ] **Step 5: Run focused Web tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass.

- [ ] **Step 6: Commit the dialog**

```bash
git add web/src/features/suppliers/api.ts web/src/features/suppliers/api.test.ts \
  web/src/features/suppliers/ModelTestDialog.tsx \
  web/src/features/suppliers/ModelTestDialog.test.tsx web/src/app/app.css
git commit -m "feat: add model parameter test selects"
```

### Task 6: Full Verification And Local Runtime Synchronization

**Files:**
- Modify in Git: focused test/report files only if verification finds a confirmed contract gap.
- Modify at runtime only: immutable supplier source/config objects for local `aixora` and `aixora-image`.
- Never modify at runtime: either supplier credential version or secret file.

**Interfaces:**
- Consumes: completed code from Tasks 1-5.
- Produces: verified branch plus locally updated configuration manifests without a Provider request.

- [ ] **Step 1: Run complete automated verification**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_m6_supplier_model_management.py
python3 tools/verify_model_level_provider_tests.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: all commands pass and automated real request counters remain zero.

- [ ] **Step 2: Run repository safety checks**

```bash
git ls-files | rg '(^|/)(runtime-data|.*\.db|secrets?)(/|$)' && exit 1 || true
git grep -nEI '(Authorization: Bearer|api[_-]?key[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_-]{20,})' -- . \
  ':(exclude)docs/superpowers/specs/2026-07-19-model-parameter-selects-design.md'
git status --short
```

Expected: no credential, runtime data, database, or private result is tracked.

- [ ] **Step 3: Synchronize local supplier code through loopback management APIs**

Before updating, record only safe identities: supplier ID, supplier/config revisions, model IDs, and boolean credential-configured state. Read each supplier's current source, apply the reviewed manifest/type/resolution changes while preserving its current manifest ID, rate-limit bucket, and every `supplierModelId`, then save through:

```text
PUT /api/suppliers/{supplier_id}/code
If-Match: "supplier-{revision}"
```

Save missing non-secret defaults through:

```text
PUT /api/suppliers/{supplier_id}/config
If-Match: "config-{revision}"

reasoning_effort=medium
image_size=1024x1024
image_quality=auto
```

The operation must not read, print, replace, or delete either credential and must not call a Provider endpoint.

- [ ] **Step 4: Verify runtime state and UI behavior**

Read both supplier details and assert:

```text
credential.configured unchanged
credential_revision unchanged
model IDs unchanged
model count unchanged
config selects visible
defaults medium / 1024x1024 / auto
```

Open the local supplier pages and model-test dialogs without clicking `确认并测试`. Verify GPT-5.5 omits `最大`, GPT-5.6 Sol includes it, and GPT Image 2 shows size/quality selects.

- [ ] **Step 5: Close any final test-only corrections**

If verification finds a confirmed gap, return to the owning task, add its exact failing test, make the minimum correction, rerun that task's focused command and Step 1, and commit it with that task's listed file set. If no gap exists, make no extra commit.

```bash
git status --short
```

Expected: empty after the owning task's correction commit, or already empty when no correction was needed.

- [ ] **Step 6: Final branch evidence**

```bash
git log --oneline --decorate -8
git status --short --branch
git diff --check main...HEAD
```

Expected: the feature branch is clean, all commits are focused, and `main` remains unchanged by feature implementation.

## Self-Review Result

- Spec coverage: supplier defaults, per-test overrides, project snapshots, model-specific values, exact image enums, idempotency, recovery, runtime synchronization, and zero-real-request rules are each assigned to a task.
- Placeholder scan: no unfinished marker, cross-task shorthand, or unspecified error-handling step remains.
- Type consistency: Web fields `reasoning_effort`, `size`, and `quality` match Pydantic/service request fields and snapshot keys; adapter config keys are `reasoning_effort`, `image_size`, and `image_quality`.
- Scope check: no database migration, Provider discovery, 2K/4K guessing, retry, fallback, video control, or secret handling was introduced.
