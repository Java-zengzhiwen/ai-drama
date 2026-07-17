# AIXORA Responses Input Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AIXORA plain-prompt text requests use canonical Responses message input so `gpt-5.6-luna` returns assistant text without adding retries or model-specific branches.

**Architecture:** Keep the change inside the provider-neutral AIXORA TypeScript adapter. A small input-normalization function converts only plain prompts; caller-supplied message arrays pass through unchanged. The existing Worker, snapshot, credential, output parser, image path, and model-test persistence contracts remain unchanged.

**Tech Stack:** Python 3, pytest, TypeScript supplier adapter compiled by the existing Node Worker, FastAPI loopback management APIs, Vitest/Node tests.

## Global Constraints

- Work only on `feat/aixora-adapter-model-archive`.
- Never print, commit, or rewrite the AIXORA credential.
- Do not add automatic retry or a Luna-only branch.
- One logical model test submits exactly one Provider request.
- Preserve current credential, config, model IDs, overlays, immutable revisions, snapshots, and history.
- Real requests are limited to the three explicitly authorized acceptance calls after offline tests pass.

---

### Task 1: Canonical Responses input

**Files:**
- Modify: `tests/web/test_aixora_adapter.py`
- Modify: `ai_drama_web/suppliers/custom_adapters/aixora.ts`

**Interfaces:**
- Consumes: `SupplierPayload.request.prompt` and optional `SupplierPayload.request.messages`.
- Produces: `responsesInput(payload): unknown`, passed as `body.input` to `/v1/responses`.

- [ ] **Step 1: Write the failing adapter tests**

Add assertions that a plain prompt produces:

```python
assert request["body"]["input"] == [
    {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "hello"}],
    }
]
```

Add a separate test with `request={"messages": messages}` and assert object equality so pre-normalized messages are not copied into another envelope.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q tests/web/test_aixora_adapter.py
```

Expected: the plain-prompt assertion fails because `body.input` is currently the string `"hello"`.

- [ ] **Step 3: Implement the minimal normalizer**

Add:

```ts
function responsesInput(payload: SupplierPayload): unknown {
  if (Array.isArray(payload.request?.messages) && payload.request.messages.length) {
    return payload.request.messages;
  }
  return [
    {
      type: "message",
      role: "user",
      content: [
        { type: "input_text", text: String(payload.request?.prompt || "") },
      ],
    },
  ];
}
```

Replace the current inline input selection with `input: responsesInput(payload)` and update the Chinese comment to explain the AIXORA compatibility boundary.

- [ ] **Step 4: Run focused GREEN verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q \
  tests/web/test_aixora_adapter.py \
  tests/web/test_supplier_compiler.py \
  tests/web/test_supplier_model_tests.py
npm --prefix worker test
```

Expected: all selected tests pass and Worker reports 26 passing tests.

- [ ] **Step 5: Commit the adapter fix**

```bash
git add ai_drama_web/suppliers/custom_adapters/aixora.ts tests/web/test_aixora_adapter.py
git commit -m "fix: normalize AIXORA Responses input"
```

### Task 2: Update the local immutable supplier version

**Files:**
- No repository file changes.

**Interfaces:**
- Consumes: loopback `GET /api/suppliers/{supplier_id}` ETag and reviewed adapter source.
- Produces: a new immutable AIXORA supplier version selected as current.

- [ ] **Step 1: Read the current supplier and model state**

Use loopback APIs to record supplier revision, current version, credential-configured boolean, config values, and the six model IDs/statuses. Do not request or print the credential.

- [ ] **Step 2: Save the reviewed source with ETag protection**

Send the complete repository adapter source to:

```text
PUT /api/suppliers/6be5792c84304af7ac07155a204fd10d/code
If-Match: "supplier-<current revision>"
```

Expected: HTTP 200 with a new `supplier_version_id`; credential revision and config revision remain unchanged.

- [ ] **Step 3: Restart and verify the local service**

Restart `gui/<uid>/fun.deltadevalex.ai-drama-m6-test`, then require:

```text
GET /suppliers = 200
GET /api/suppliers = 200
```

Confirm the AIXORA current version changed, five text models remain enabled, and the enabled `gpt-image-2` overlay remains present.

### Task 3: Real acceptance and regression closure

**Files:**
- Create: `docs/superpowers/reports/2026-07-17-aixora-responses-input-compatibility-verification.md`

**Interfaces:**
- Consumes: the loopback model-test API and stored AIXORA credential.
- Produces: sanitized durable evidence with request counts and exact test-run outcomes.

- [ ] **Step 1: Run one Luna-high model test**

Create one test for model `41f191fa614050daabefd1085cf730aa` with `reasoning_effort=high`, poll the same `test_run_id`, and require `status=completed`, non-empty output, and empty error code.

- [ ] **Step 2: Run one Sol-high regression test**

Create one test for model `a1a97eb5b16457c38a1e53ee7459c6de` with `reasoning_effort=high`, poll the same `test_run_id`, and require `status=completed`, non-empty output, and empty error code.

- [ ] **Step 3: Run one image regression test**

Create one test for model `e7dc2c3c5a205726ad2b44b583e3aeb9`, poll the same `test_run_id`, and require `status=completed`, a supported image media type, positive byte size, and HTTP 200 from `/api/model-tests/{test_run_id}/content`.

- [ ] **Step 4: Run automated verification**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix worker test
python3 tools/verify_aixora_adapter_model_archive.py
git diff --check
```

Expected: all commands exit 0; semantic verifier reports 12/12 PASS with its fake-only real-request ledger unchanged.

- [ ] **Step 5: Write the sanitized verification report**

Record exact test counts, the three newly authorized real test-run IDs and outcomes, the earlier diagnostic count, default production flag false, and no secrets/private image bytes. Do not include prompts beyond the fixed harmless smoke-test text, Provider response bodies, URLs, or credential suffixes.

- [ ] **Step 6: Commit and push**

```bash
git add docs/superpowers/reports/2026-07-17-aixora-responses-input-compatibility-verification.md
git commit -m "docs: verify AIXORA Responses compatibility"
git push origin feat/aixora-adapter-model-archive
```

Expected: local and remote branch heads match without force push.
