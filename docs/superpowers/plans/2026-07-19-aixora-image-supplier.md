# Aixora Image Supplier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a local `aixora-image` supplier that copies the current Aixora adapter, non-secret configuration, and all six model definitions while keeping credentials and runtime history isolated.

**Architecture:** Use the existing loopback-only supplier management APIs as the sole mutation boundary. Clone only safe source/config/model data, compile the copied adapter through the normal Worker validation path, assign new supplier/model identities, and leave the new credential empty for the user to configure in the Web UI.

**Tech Stack:** FastAPI management API, Python standard-library `urllib`, SQLite-backed M6 product store, TypeScript supplier Worker, existing M6 verifiers.

## Global Constraints

- Work on `feat/aixora-image-supplier`; do not mutate `main` directly.
- Do not read, print, copy, or write the existing Aixora credential.
- Do not copy tests, generated media, jobs, snapshots, bindings, or idempotency records.
- Do not issue any real Provider request; all management traffic is loopback-only.
- Keep the original `aixora` supplier unchanged.
- The new supplier starts with no credential and no project binding.
- Runtime databases, credentials, evidence, and generated media must remain untracked by Git.

---

### Task 1: Freeze the source state and preconditions

**Files:**
- Read: `ai_drama_web/routers/suppliers.py`
- Read: `ai_drama_web/routers/models.py`
- Read: `runtime-data/runtime.db` through loopback management APIs only
- Modify: none

**Interfaces:**
- Consumes: `GET /api/suppliers`, `GET /api/suppliers/{supplier_id}`, `GET /api/suppliers/{supplier_id}/code`, `GET /api/suppliers/{supplier_id}/models`
- Produces: a safe in-memory source supplier object, adapter source, non-secret config map, and six model definitions

- [ ] **Step 1: Verify the branch and repository are clean**

Run:

```bash
git branch --show-current
git status --short
```

Expected: branch is `feat/aixora-image-supplier` and status is empty after the plan commit.

- [ ] **Step 2: Assert the local service and feature gates are ready**

Run:

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/model-tests/status
```

Expected: `{"status":"ok"}` and `{"enabled":true}`.

- [ ] **Step 3: Run a read-only preflight assertion**

Run:

```bash
python3 - <<'PY'
import json
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000/api"

def get(path):
    with urlopen(Request(BASE + path, headers={"Accept": "application/json"}), timeout=10) as response:
        return json.load(response)

suppliers = get("/suppliers")
source = next(item for item in suppliers if item["slug"] == "aixora")
assert not any(item["slug"] == "aixora-image" for item in suppliers), "AIXORA_IMAGE_ALREADY_EXISTS"
detail = get(f"/suppliers/{source['supplier_id']}")
models = get(f"/suppliers/{source['supplier_id']}/models")
assert detail["credential"]["configured"] is True
assert len(models) == 6
assert sorted(item["capability"] for item in models) == ["image", "text", "text", "text", "text", "text"]
assert {item["provider_model_name"] for item in models} == {
    "gpt-5.5", "gpt-5.6", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-image-2"
}
print("AIXORA_IMAGE_PREFLIGHT_PASS")
PY
```

Expected: `AIXORA_IMAGE_PREFLIGHT_PASS`.

### Task 2: Clone the supplier through management contracts

**Files:**
- Modify at runtime only: `runtime-data/runtime.db`
- Create at runtime only: immutable source/config/model objects under the configured object store
- Modify in Git: none

**Interfaces:**
- Consumes: safe source state from Task 1
- Produces: enabled custom supplier `aixora-image`, isolated supplier version/config revision, six overlay models, and no credential

- [ ] **Step 1: Execute the exact loopback-only clone operation**

Run:

```bash
python3 - <<'PY'
import copy
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000/api"
created_supplier_id = None

def call(method, path, payload=None, headers=None):
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(BASE + path, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, response_headers, json.loads(body) if body else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc

def get(path):
    return call("GET", path)[2]

try:
    suppliers = get("/suppliers")
    source_supplier = next(item for item in suppliers if item["slug"] == "aixora")
    if any(item["slug"] == "aixora-image" for item in suppliers):
        raise RuntimeError("AIXORA_IMAGE_ALREADY_EXISTS")

    source_id = source_supplier["supplier_id"]
    source_detail = get(f"/suppliers/{source_id}")
    source_code = get(f"/suppliers/{source_id}/code")["source"]
    source_models = get(f"/suppliers/{source_id}/models")

    status, _, clone = call(
        "POST",
        "/suppliers",
        {"slug": "aixora-image", "display_name": "aixora-image"},
        {"If-None-Match": "*", "Idempotency-Key": "aixora-image-supplier-v1"},
    )
    assert status == 201
    created_supplier_id = clone["supplier_id"]
    assert clone["credential"]["configured"] is False

    catalog_etag = '"model-catalog-0"'
    model_id_map = {}
    for source_model in sorted(source_models, key=lambda item: item["provider_model_name"]):
        definition = copy.deepcopy(source_model["definition"])
        definition.pop("supplierModelId", None)
        provider_name = source_model["provider_model_name"]
        status, response_headers, created_model = call(
            "POST",
            f"/suppliers/{created_supplier_id}/models",
            {
                "provider_model_name": provider_name,
                "display_name": source_model["display_name"],
                "capability": source_model["capability"],
                "definition": definition,
            },
            {
                "If-None-Match": "*",
                "If-Match": catalog_etag,
                "Idempotency-Key": f"aixora-image-model-{provider_name}-v1",
            },
        )
        assert status == 201
        new_model_id = created_model["supplier_model_id"]
        model_id_map[source_model["supplier_model_id"]] = new_model_id
        model_etag = response_headers["etag"]
        catalog_etag = response_headers["x-model-catalog-etag"]

        definition["supplierModelId"] = new_model_id
        status, response_headers, revised_model = call(
            "PATCH",
            f"/models/{new_model_id}",
            {"definition": definition, "acknowledged_binding_count": 0},
            {"If-Match": f"{model_etag}, {catalog_etag}"},
        )
        assert status == 200
        assert revised_model["definition"]["supplierModelId"] == new_model_id
        catalog_etag = response_headers["x-model-catalog-etag"]

    transformed_source = source_code
    exact_replacements = {
        'id: "aixora"': 'id: "aixora-image"',
        'name: "AIXORA"': 'name: "AIXORA Image"',
        'rateLimitBucketKey: "aixora-generation"': 'rateLimitBucketKey: "aixora-image-generation"',
    }
    for old, new in exact_replacements.items():
        assert transformed_source.count(old) == 1, f"EXPECTED_ONE_SOURCE_MATCH:{old}"
        transformed_source = transformed_source.replace(old, new, 1)
    for old_model_id, new_model_id in model_id_map.items():
        marker = f'supplierModelId: "{old_model_id}"'
        assert transformed_source.count(marker) == 1, f"EXPECTED_ONE_MODEL_ID_MATCH:{old_model_id}"
        transformed_source = transformed_source.replace(
            marker, f'supplierModelId: "{new_model_id}"', 1
        )

    clone = get(f"/suppliers/{created_supplier_id}")
    status, _, _ = call(
        "PUT",
        f"/suppliers/{created_supplier_id}/code",
        {"source": transformed_source},
        {"If-Match": f'"supplier-{clone["revision"]}"'},
    )
    assert status == 200

    clone = get(f"/suppliers/{created_supplier_id}")
    status, _, _ = call(
        "PUT",
        f"/suppliers/{created_supplier_id}/config",
        {"values": source_detail["config_values"]},
        {"If-Match": f'"config-{clone["config_revision"]}"'},
    )
    assert status == 200
    print(json.dumps({
        "result": "AIXORA_IMAGE_CLONE_CREATED",
        "supplier_id": created_supplier_id,
        "model_count": len(model_id_map),
        "credential_copied": False,
        "real_provider_requests": False,
    }, ensure_ascii=False))
except Exception:
    if created_supplier_id:
        try:
            clone = get(f"/suppliers/{created_supplier_id}")
            call(
                "PATCH",
                f"/suppliers/{created_supplier_id}",
                {"enabled": False},
                {"If-Match": f'"supplier-{clone["revision"]}"'},
            )
        except Exception:
            pass
    raise
PY
```

Expected: one JSON object with `result=AIXORA_IMAGE_CLONE_CREATED`, `model_count=6`, `credential_copied=false`, and `real_provider_requests=false`.

- [ ] **Step 2: Confirm validation produced no network request**

Inspect the returned supplier and model catalog only. Do not invoke `/api/models/{supplier_model_id}/tests`; adapter compilation during `PUT /code` must remain network-disabled.

Expected: the supplier remains enabled only after every mutation succeeds; any failure leaves it disabled for diagnosis.

### Task 3: Verify isolation and regression safety

**Files:**
- Read: `runtime-data/runtime.db` through management APIs
- Verify: `tools/verify_m6_supplier_model_management.py`
- Verify: `tools/verify_model_level_provider_tests.py`
- Verify: `migration/tools/verify_migration.py`
- Modify in Git: none

**Interfaces:**
- Consumes: completed `aixora-image` supplier from Task 2
- Produces: machine-checked evidence that the supplier is isolated, credential-free, and ready for Web configuration

- [ ] **Step 1: Assert supplier and model isolation**

Run:

```bash
python3 - <<'PY'
import json
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000/api"

def get(path):
    with urlopen(Request(BASE + path, headers={"Accept": "application/json"}), timeout=10) as response:
        return json.load(response)

suppliers = get("/suppliers")
source = next(item for item in suppliers if item["slug"] == "aixora")
clone = next(item for item in suppliers if item["slug"] == "aixora-image")
source_detail = get(f"/suppliers/{source['supplier_id']}")
clone_detail = get(f"/suppliers/{clone['supplier_id']}")
source_models = get(f"/suppliers/{source['supplier_id']}/models")
clone_models = get(f"/suppliers/{clone['supplier_id']}/models")

assert source_detail["enabled"] == 1
assert clone_detail["enabled"] == 1
assert source_detail["credential"]["configured"] is True
assert clone_detail["credential"]["configured"] is False
assert clone_detail["credential_active_job_count"] == 0
assert len(source_models) == len(clone_models) == 6
assert {item["provider_model_name"] for item in source_models} == {
    item["provider_model_name"] for item in clone_models
}
assert {item["supplier_model_id"] for item in source_models}.isdisjoint(
    {item["supplier_model_id"] for item in clone_models}
)
assert clone_detail["capabilities"] == ["image", "text"]
assert clone_detail["config_values"] == source_detail["config_values"]
assert clone_detail["manifest"]["id"] == "aixora-image"
assert clone_detail["manifest"]["rateLimitBucketKey"] == "aixora-image-generation"
print("AIXORA_IMAGE_ISOLATION_PASS")
PY
```

Expected: `AIXORA_IMAGE_ISOLATION_PASS`.

- [ ] **Step 2: Run focused management and migration verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q \
  tests/web/test_m6d_management_contract.py \
  tests/web/test_supplier_model_tests.py \
  tests/web/test_aixora_adapter.py
python3 tools/verify_m6_supplier_model_management.py
python3 tools/verify_model_level_provider_tests.py
python3 migration/tools/verify_migration.py
```

Expected: pytest passes; all verifiers report PASS/valid; real Provider request counts remain zero.

- [ ] **Step 3: Verify repository hygiene**

Run:

```bash
git diff --check
git status --short
git ls-files | rg '(^|/)(runtime-data|.*\.db|secrets?)(/|$)' && exit 1 || true
```

Expected: no runtime data, database, credential, or secret is tracked; only approved documentation commits exist on the branch.

- [ ] **Step 4: Hand off credential configuration**

Open `http://127.0.0.1:8000/suppliers`, select `aixora-image`, and verify the 密钥 tab reports 未配置. The user can then enter the second Key and explicitly confirm one model-level real test.

Expected: the new supplier is usable without changing or exposing the original Aixora credential.
