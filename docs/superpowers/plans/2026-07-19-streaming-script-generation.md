# 剧本正文流式生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Aixora 成功响应无法归一化的问题，并让剧本 Skill 生成的 Markdown 正文在中央剧本编辑区可恢复、exactly-once 地流式显示。

**Architecture:** 先在同步 Worker 边界增加脱敏响应形状证据，取得真实响应契约后用 fixture 修复同步解析。随后以版本化 Worker NDJSON 帧、持久化剧本生成会话和本地 SSE 构建流式链路；正式剧本 revision 仍只由现有 parser 和 Skill validators 生成。

**Tech Stack:** Python 3、FastAPI、SQLite、Node.js Worker、TypeScript supplier adapters、React 18、TanStack Query、Ant Design、Vitest、Playwright、pytest。

## Global Constraints

- 权威设计：`docs/superpowers/specs/2026-07-19-streaming-script-generation-design.md`，状态必须为 `APPROVED`。
- 继续使用 `ai-drama-script-adaptation-skill@v0.6.1-rc2.4`、`parse_script_response` 和声明的 validators。
- `AI_DRAMA_SCRIPT_STREAMING_ENABLED=false` 为默认值；开启流式还要求 `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=true`。
- 浏览器只能连接本地 AI Drama API，不得直连 Aixora，不得接收 credential、Authorization、Base URL 或签名 URL。
- Adapter 只能使用注入 helper；禁止原生 fetch、process、require、import、文件系统和环境变量。
- 一次用户点击最多提交一次 Provider 请求；重连、刷新、API 重启和 malformed frame 均不得自动 resubmit。
- 流式正文是临时草稿；完成解析与 Skill 校验前不得创建正式剧本 revision。
- reasoning、SSE 协议和 JSON 包装不得显示在中央剧本区。
- 默认测试、CI、verifier 和审阅必须保持真实请求数为 0。
- 每项任务遵循 red test → focused green → affected regression → review → commit。

## File Structure

- `worker/src/response-shape.mjs`：生成字段名、类型、数量和字节数的脱敏响应形状。
- `worker/src/sse-parser.mjs`：有界解析 Provider SSE。
- `worker/src/protocol.ts`、`worker/src/worker.ts`：Worker v1/v2 与 NDJSON 流帧。
- `ai_drama_web/suppliers/custom_adapters/aixora.ts`：Aixora 同步提取和 `textStream`。
- `ai_drama_web/suppliers/worker.py`、`execution.py`：Python 流式子进程和 snapshot 路由。
- `ai_drama_web/store.py`：剧本生成会话、持久化 event/chunk、sequence、状态和恢复迁移。
- `ai_drama_runtime/services.py`：将同步剧本运行拆成 prepare/finalize，保持 parser/validator 语义。
- `ai_drama_web/services/script_generation_stream.py`：持久化 runner 和 exactly-once 提交。
- `ai_drama_web/routers/scripts.py`、`schemas/workflows.py`：start/status/SSE API。
- `web/src/features/script/useScriptGenerationStream.ts`：EventSource、sequence 去重和重连。
- `SourceTab.tsx`、`ChapterWorkspace.tsx`、`ScriptTab.tsx`：中央正文流式 UI。
- `tools/verify_streaming_script_generation.py`：语义 verifier。

---

### Task 1: Persist sanitized response-shape evidence on synchronous failures

**Files:**

- Create: `worker/src/response-shape.mjs`
- Create: `worker/src/response-shape.test.ts`
- Modify: `worker/src/worker.ts`
- Modify: `ai_drama_web/suppliers/worker.py`
- Modify: `ai_drama_web/services/m6_generation.py`
- Create: `tests/web/test_streaming_response_evidence.py`

**Interfaces:**

- Consumes: `helpers.http.request`, `SupplierWorkerError`, `supplier_text_runs.evidence_object_id`。
- Produces: `describeResponseShape(input) -> SafeResponseShape`；`SupplierWorkerError.evidence`；失败 text run 的 sanitized evidence。

- [ ] **Step 1: Write the Worker red test**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { describeResponseShape } from "./response-shape.mjs";

test("response shape records structure without values", () => {
  const shape = describeResponseShape({
    statusCode: 200,
    contentType: "application/json",
    byteLength: 321,
    parsed: {
      id: "private-id",
      output: [{ type: "message", content: [{ type: "output_text", text: "private script" }] }],
      usage: { input_tokens: 10, output_tokens: 20 },
      signed_url: "https://example.test/result?signature=secret",
    },
  });
  assert.deepEqual(shape.topLevelKeys, ["id", "output", "signed_url", "usage"]);
  assert.deepEqual(shape.outputItemTypes, ["message"]);
  assert.deepEqual(shape.contentItemTypes, ["output_text"]);
  assert.equal(JSON.stringify(shape).includes("private script"), false);
  assert.equal(JSON.stringify(shape).includes("private-id"), false);
  assert.equal(JSON.stringify(shape).includes("secret"), false);
});
```

- [ ] **Step 2: Run the test to verify red**

Run: `npm --prefix worker test -- --test-name-pattern="response shape"`

Expected: FAIL because `response-shape.mjs` does not exist.

- [ ] **Step 3: Implement the pure shape extractor**

```js
const valueType = value => Array.isArray(value) ? "array" : value === null ? "null" : typeof value;

export function describeResponseShape({ statusCode, contentType, byteLength, parsed }) {
  const output = Array.isArray(parsed?.output) ? parsed.output : [];
  const content = output.flatMap(item => Array.isArray(item?.content) ? item.content : []);
  return Object.freeze({
    schema: "provider-response-shape-v1",
    httpStatus: Number(statusCode || 0),
    contentType: String(contentType || "").split(";", 1)[0].toLowerCase(),
    byteLength: Number(byteLength || 0),
    bodyType: valueType(parsed),
    topLevelKeys: parsed && typeof parsed === "object" && !Array.isArray(parsed) ? Object.keys(parsed).sort() : [],
    statusType: valueType(parsed?.status),
    outputCount: output.length,
    outputItemTypes: output.map(item => String(item?.type || valueType(item))),
    contentItemTypes: content.map(item => String(item?.type || valueType(item))),
    contentFieldNames: [...new Set(content.flatMap(item => item && typeof item === "object" ? Object.keys(item) : []))].sort(),
    usageFieldNames: parsed?.usage && typeof parsed.usage === "object" ? Object.keys(parsed.usage).sort() : [],
  });
}
```

- [ ] **Step 4: Attach only host-owned evidence to Worker errors**

In `worker/src/worker.ts`, set `lastProviderResponseShape` after host JSON parsing and include it in the final error frame:

```js
let lastProviderResponseShape = null;
lastProviderResponseShape = describeResponseShape({
  statusCode: response.statusCode,
  contentType: response.headers["content-type"],
  byteLength: buffer.length,
  parsed,
});

error: {
  code: error?.code || "SUPPLIER_EXECUTION_FAILED",
  message: error?.code || "supplier operation failed",
  evidence: lastProviderResponseShape,
}
```

Never copy an adapter-supplied evidence object; only the host HTTP broker may create it.

- [ ] **Step 5: Carry evidence through Python and persist it**

```python
class SupplierWorkerError(RuntimeError):
    def __init__(self, code, message, *, evidence=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.evidence = evidence if isinstance(evidence, dict) else {}

# Worker failure branch
raise SupplierWorkerError(
    error.get("code", "SUPPLIER_EXECUTION_FAILED"),
    str(error.get("message", "supplier operation failed"))[:299],
    evidence=error.get("evidence"),
)

# Coordinator failure branch
safe = sanitize_evidence(getattr(exc, "evidence", {}))
evidence_object_id = self.runtime.write_text_object(
    json.dumps(safe, sort_keys=True, separators=(",", ":"))
) if safe else ""
self.store.fail_supplier_text_run(
    run["run_id"], error_code=getattr(exc, "code", "SUPPLIER_EXECUTION_FAILED"),
    evidence_object_id=evidence_object_id,
)
```

- [ ] **Step 6: Add Python redaction assertions**

```python
def test_malformed_response_persists_shape_without_values(app):
    run_id = app.execute_malformed({"output": [{"type": "message", "content": []}], "secret": "hidden"})
    run = app.store.get_supplier_text_run(run_id)
    evidence = json.loads(app.runtime.read_text(run["evidence_object_id"]))
    assert evidence["topLevelKeys"] == ["output", "secret"]
    assert "hidden" not in json.dumps(evidence)
    assert run["error_code"] == "PROVIDER_RESPONSE_MALFORMED"
```

- [ ] **Step 7: Run focused green tests**

```bash
npm --prefix worker test
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/web/test_streaming_response_evidence.py \
  tests/web/test_m6c_adapter_cutover.py \
  tests/web/test_aixora_adapter.py
```

Expected: PASS; real request count remains 0.

- [ ] **Step 8: Commit Task 1**

```bash
git add worker/src/response-shape.mjs worker/src/response-shape.test.ts worker/src/worker.ts \
  ai_drama_web/suppliers/worker.py ai_drama_web/services/m6_generation.py \
  tests/web/test_streaming_response_evidence.py
git commit -m "fix: persist sanitized supplier response shape"
```

### Task 2: Freeze the observed Aixora success shape and repair synchronous parsing

**Files:**

- Create: `tests/fixtures/aixora/responses-success-shape.json`
- Create: `tests/fixtures/aixora/responses-success-body.json`
- Modify: `tests/web/test_aixora_adapter.py`
- Modify: `ai_drama_web/suppliers/custom_adapters/aixora.ts`

**Interfaces:**

- Consumes: Task 1 sanitized evidence and `responseText(raw)`。
- Produces: one fixture-backed, non-retrying parser path for the exact observed wrapper。

- [ ] **Step 1: Obtain one explicitly authorized diagnostic record**

After Task 1 is running locally, pause and request `AUTHORIZE_ONE_REAL_AIXORA_RESPONSE_SHAPE_TEST`. The token permits one local user click on `保存并生成剧本`, and nothing else. Read only `provider-response-shape-v1`; never print or commit raw response, prompt, credential, Provider id or URL.

Expected gate:

```text
REAL_TEXT_REQUEST_COUNT=1
EVIDENCE_SCHEMA=provider-response-shape-v1
RAW_RESPONSE_COMMITTED=false
```

- [ ] **Step 2: Create a synthetic body fixture with the observed keys and types**

Use constant fake text. Standard Responses fixture:

```json
{
  "output": [{
    "type": "message",
    "content": [{"type": "output_text", "text": "# 第一场\n\n测试剧本正文。"}]
  }],
  "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
}
```

If evidence shows exactly one host wrapper, nest this body under that exact key. Do not add unobserved fallbacks.

- [ ] **Step 3: Write the red adapter tests**

```python
def test_text_extracts_observed_aixora_success_shape(artifact):
    raw = json.loads((FIXTURES / "responses-success-body.json").read_text())
    result = invoke(artifact, "textRequest", payload("gpt-5.6-sol"), [raw])
    assert result["ok"] is True
    assert result["result"]["output"] == "# 第一场\n\n测试剧本正文。"
    assert len(result["calls"]) == 1

def test_text_does_not_promote_reasoning_or_retry(artifact):
    raw = {"output": [{"type": "reasoning", "summary": [{"text": "private"}]}], "usage": {}}
    result = invoke(artifact, "textRequest", payload("gpt-5.6-sol"), [raw])
    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_RESPONSE_MALFORMED"
    assert len(result["calls"]) == 1
```

- [ ] **Step 4: Run red test**

Run: `python3 -m pytest -q tests/web/test_aixora_adapter.py::test_text_extracts_observed_aixora_success_shape`

Expected: FAIL with `PROVIDER_RESPONSE_MALFORMED`.

- [ ] **Step 5: Implement only the observed unwrap path**

```ts
function responseBody(raw: any): any {
  if (raw && typeof raw === "object" && raw.response && typeof raw.response === "object") {
    return raw.response;
  }
  return raw;
}

function responseText(raw: any): string {
  const body = responseBody(raw);
  if (typeof body?.output_text === "string" && body.output_text) return body.output_text;
  const parts: string[] = [];
  for (const item of Array.isArray(body?.output) ? body.output : []) {
    if (item?.type !== "message") continue;
    for (const content of Array.isArray(item?.content) ? item.content : []) {
      if (content?.type === "output_text" && typeof content?.text === "string") parts.push(content.text);
    }
  }
  if (!parts.length) fail("PROVIDER_RESPONSE_MALFORMED");
  return parts.join("");
}
```

The `response` key in this code block is executable only when Task 1 evidence records that exact key. If the evidence records a different single wrapper key, revise this plan and its synthetic fixture in a focused docs commit before changing production code. If evidence is standard, add no wrapper and use the fixture to locate the first local boundary that changes the body. This is a hard evidence gate, not permission to guess a key.

- [ ] **Step 6: Run affected tests and save immutable supplier version**

```bash
python3 -m pytest -q tests/web/test_aixora_adapter.py \
  tests/web/test_streaming_response_evidence.py \
  tests/acceptance/test_source_to_script_fake_provider.py
npm --prefix worker test
```

Persist the adapter through the loopback API with ETag protection and verify credential/model overlays are unchanged.

- [ ] **Step 7: Commit Task 2**

```bash
git add ai_drama_web/suppliers/custom_adapters/aixora.ts tests/web/test_aixora_adapter.py \
  tests/fixtures/aixora/responses-success-shape.json tests/fixtures/aixora/responses-success-body.json
git commit -m "fix: normalize observed Aixora response shape"
```

### Task 3: Add versioned Worker streaming frames and host-owned SSE parsing

**Files:**

- Modify: `worker/src/protocol.ts`
- Modify: `worker/src/worker.ts`
- Create: `worker/src/sse-parser.mjs`
- Create: `worker/src/sse-parser.test.ts`
- Modify: `worker/src/compiler.mjs`
- Modify: `ai_drama_web/suppliers/custom_adapters/aixora.ts`
- Create: `tests/fixtures/aixora/responses-stream.ndjson`

**Interfaces:**

- Consumes: Task 2 response contract and current network policy。
- Produces: `textStream`；`helpers.http.stream(options)`；ordered NDJSON frames。

- [ ] **Step 1: Write fragmented SSE red test**

```js
test("parser joins fragmented Responses deltas", () => {
  const parser = createSseParser();
  const events = [
    ...parser.push(Buffer.from("event: response.output_text.delta\ndata: {\"delta\":\"# 第一")),
    ...parser.push(Buffer.from("场\"}\n\nevent: response.output_text.delta\ndata: {\"delta\":\"\\n正文\"}\n\n")),
    ...parser.finish(),
  ];
  assert.deepEqual(events.map(event => event.data.delta), ["# 第一场", "\n正文"]);
});
```

- [ ] **Step 2: Run red test**

Run: `npm --prefix worker test -- --test-name-pattern="fragmented Responses"`

Expected: FAIL because `createSseParser` is missing.

- [ ] **Step 3: Implement bounded SSE parser**

```js
export function createSseParser({ maxEventBytes = 256 * 1024 } = {}) {
  let pending = "";
  return {
    push(chunk) {
      pending += chunk.toString("utf8");
      if (Buffer.byteLength(pending, "utf8") > maxEventBytes) throw Object.assign(new Error(), { code: "PROVIDER_STREAM_EVENT_TOO_LARGE" });
      const events = [];
      for (;;) {
        const boundary = pending.indexOf("\n\n");
        if (boundary < 0) break;
        const block = pending.slice(0, boundary);
        pending = pending.slice(boundary + 2);
        const event = block.split("\n").find(line => line.startsWith("event:"))?.slice(6).trim() || "message";
        const data = block.split("\n").filter(line => line.startsWith("data:")).map(line => line.slice(5).trim()).join("\n");
        if (data && data !== "[DONE]") events.push({ event, data: JSON.parse(data) });
      }
      return events;
    },
    finish() {
      if (pending.trim()) throw Object.assign(new Error(), { code: "PROVIDER_STREAM_MALFORMED" });
      return [];
    },
  };
}
```

- [ ] **Step 4: Define protocol v2 frames**

```ts
export type SupplierStreamFrame =
  | { type: "started"; sequence: 0 }
  | { type: "text_delta"; sequence: number; text: string }
  | { type: "usage"; sequence: number; usage: Record<string, number> }
  | { type: "completed"; sequence: number; evidence: Record<string, unknown> }
  | { type: "failed"; sequence: number; errorCode: string; evidence: Record<string, unknown> };
```

Write one JSON object per stdout line. Adapter strings may only appear inside validated `text_delta.text`.

- [ ] **Step 5: Add host stream helper and Aixora operation**

```ts
export async function textStream(payload: SupplierPayload, helpers: SupplierHelpers) {
  return helpers.http.stream({
    method: "POST",
    url: `${baseUrl(payload)}/responses`,
    headers: authorization(payload),
    body: {
      model: payload.model,
      input: responsesInput(payload),
      reasoning: { effort: reasoningEffort(payload) },
      stream: true,
      store: false,
    },
    eventMap: {
      delta: "response.output_text.delta",
      completed: "response.completed",
      failed: "response.failed",
    },
  });
}
```

Host code reuses DNS pinning, peer-IP checks, redirect denial and output limits. Reasoning events never become text deltas.

- [ ] **Step 6: Version compiler/runtime contracts**

New stream-capable artifacts use Worker protocol `2` and helper `ai-drama-helper-v3`. Compiler accepts `textStream` only for text suppliers and still requires `textRequest` for rollback. Historical v1 snapshots stay executable only through v1.

- [ ] **Step 7: Run Worker/compiler tests**

```bash
npm --prefix worker test
python3 -m pytest -q tests/web/test_supplier_compiler.py tests/web/test_aixora_adapter.py
```

Expected: PASS; validation mode returns `NETWORK_DISABLED_DURING_VALIDATION`.

- [ ] **Step 8: Commit Task 3**

```bash
git add worker/src/protocol.ts worker/src/worker.ts worker/src/compiler.mjs \
  worker/src/sse-parser.mjs worker/src/sse-parser.test.ts \
  ai_drama_web/suppliers/custom_adapters/aixora.ts tests/fixtures/aixora/responses-stream.ndjson
git commit -m "feat: add isolated supplier text streaming protocol"
```

### Task 4: Implement Python streaming process control and snapshot routing

**Files:**

- Modify: `ai_drama_web/suppliers/worker.py`
- Modify: `ai_drama_web/suppliers/execution.py`
- Create: `tests/suppliers/test_worker_streaming.py`
- Modify: `tests/web/test_execution_snapshot.py`

**Interfaces:**

- Consumes: Task 3 NDJSON frames and frozen runtime fingerprints。
- Produces: `SupplierWorker.invoke_stream(...)` and `SnapshotExecutionGateway.invoke_stream(...)`。

- [ ] **Step 1: Write ordered/duplicate red tests**

```python
def test_worker_stream_yields_ordered_frames(tmp_path):
    worker = SupplierWorker(worker_entrypoint=fixture_worker("ordered-stream"))
    frames = list(worker.invoke_stream(stream_artifact(tmp_path), "textStream", {"prompt": "x"}))
    assert [frame["type"] for frame in frames] == ["started", "text_delta", "text_delta", "completed"]
    assert [frame["sequence"] for frame in frames] == [0, 1, 2, 3]

def test_worker_stream_rejects_duplicate_sequence(tmp_path):
    worker = SupplierWorker(worker_entrypoint=fixture_worker("duplicate-sequence"))
    with pytest.raises(SupplierWorkerError, match="SUPPLIER_WORKER_PROTOCOL_ERROR"):
        list(worker.invoke_stream(stream_artifact(tmp_path), "textStream", {}))
```

- [ ] **Step 2: Run red test**

Run: `python3 -m pytest -q tests/suppliers/test_worker_streaming.py`

Expected: FAIL because `invoke_stream` is undefined.

- [ ] **Step 3: Implement bounded frame iteration**

```python
def invoke_stream(self, artifact, operation, payload, *, mode="execution", limits=None):
    process = self._start_process(artifact, operation, payload, mode=mode, limits=limits, protocol="2")
    expected_sequence = 0
    try:
        for raw_line in self._iter_lines_until_deadline(process, limits):
            frame = json.loads(raw_line)
            if frame.get("sequence") != expected_sequence:
                raise SupplierWorkerError("SUPPLIER_WORKER_PROTOCOL_ERROR", "stream sequence mismatch")
            expected_sequence += 1
            yield frame
            if frame.get("type") in {"completed", "failed"}:
                break
    finally:
        self._terminate_process_group(process)
```

Refactor request serialization, clean environment, byte accounting, monotonic deadline and process-group termination into helpers shared with `invoke`.

- [ ] **Step 4: Add exact snapshot routing**

```python
def invoke_stream(self, snapshot_hash, operation, request):
    snapshot, artifact, payload = self._load_invocation(snapshot_hash, request)
    if snapshot.worker_protocol_version != "2" or snapshot.helper_api_version != "ai-drama-helper-v3":
        raise SupplierExecutionError("SUPPLIER_RUNTIME_UNAVAILABLE")
    yield from self.worker.invoke_stream(
        artifact, operation, payload, mode="execution",
        limits=WorkerLimits(**snapshot.worker_limits),
    )
```

- [ ] **Step 5: Prove frozen artifact/config/model/credential**

```python
def test_stream_uses_frozen_snapshot(snapshot_store):
    list(snapshot_store.gateway.invoke_stream(snapshot_store.old_hash, "textStream", {"prompt": "x"}))
    assert snapshot_store.worker.seen_payload["model"] == "frozen-model"
    assert snapshot_store.worker.seen_payload["config"] == {"base_url": "https://frozen.example/v1"}
    assert snapshot_store.worker.seen_payload["credential"] == "frozen-credential"
```

- [ ] **Step 6: Run focused/security regression**

```bash
python3 -m pytest -q tests/suppliers/test_worker_streaming.py \
  tests/suppliers/test_worker_isolation.py tests/web/test_execution_snapshot.py
```

- [ ] **Step 7: Commit Task 4**

```bash
git add ai_drama_web/suppliers/worker.py ai_drama_web/suppliers/execution.py \
  tests/suppliers/test_worker_streaming.py tests/web/test_execution_snapshot.py
git commit -m "feat: route supplier text streams by snapshot"
```

### Task 5: Add durable script-generation sessions and chunks

**Files:**

- Modify: `ai_drama_web/store.py`
- Create: `tests/web/test_script_stream_store.py`
- Modify: `tests/web/test_supplier_migration.py`
- Modify: `migration/tools/verify_migration.py`

**Interfaces:**

- Consumes: runtime object store, execution snapshots and supplier text runs。
- Produces: additive session/chunk tables and atomic store methods。

- [ ] **Step 1: Write migration/state red tests**

```python
def test_script_stream_migration_is_additive_and_replay_safe(tmp_path):
    store = open_m6_database(tmp_path)
    assert table_columns(store, "script_generation_runs") >= {
        "run_id", "runtime_run_id", "supplier_text_run_id", "snapshot_hash",
        "status", "last_sequence", "revision_id", "error_code",
    }
    store.close()
    reopened = open_m6_database(tmp_path)
    assert migration_count(reopened, "streaming_script_generation_v1") == 1

def test_duplicate_event_must_have_same_hash(store):
    store.append_script_generation_event("run-1", sequence=1, event_type="text_delta", payload={"text": "# 第一场"})
    store.append_script_generation_event("run-1", sequence=1, event_type="text_delta", payload={"text": "# 第一场"})
    with pytest.raises(ScriptGenerationConflict, match="STREAM_SEQUENCE_CONFLICT"):
        store.append_script_generation_event("run-1", sequence=1, event_type="text_delta", payload={"text": "different"})
```

- [ ] **Step 2: Run red test**

Run: `python3 -m pytest -q tests/web/test_script_stream_store.py tests/web/test_supplier_migration.py`

Expected: FAIL because tables/methods are missing.

- [ ] **Step 3: Add additive schema**

```sql
CREATE TABLE script_generation_runs (
  run_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL,
  source_revision_id TEXT NOT NULL,
  runtime_run_id TEXT NOT NULL UNIQUE,
  supplier_text_run_id TEXT NOT NULL DEFAULT '',
  snapshot_hash TEXT NOT NULL DEFAULT '',
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('prepared','submitting','streaming','finalizing','completed','failed','unknown_outcome')),
  last_sequence INTEGER NOT NULL DEFAULT 0,
  character_count INTEGER NOT NULL DEFAULT 0,
  revision_id TEXT NOT NULL DEFAULT '',
  error_code TEXT NOT NULL DEFAULT '',
  evidence_object_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE script_generation_events (
  run_id TEXT NOT NULL REFERENCES script_generation_runs(run_id) ON DELETE RESTRICT,
  sequence INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('stage','text_delta','usage','failed','revision_completed')),
  payload_object_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  byte_length INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, sequence)
);
```

- [ ] **Step 4: Implement exact store interfaces**

```python
create_script_generation_run(*, run_id, project_id, chapter_id, source_revision_id,
                             runtime_run_id, idempotency_key) -> dict
claim_script_generation_run(run_id) -> dict | None
bind_script_generation_snapshot(run_id, supplier_text_run_id, snapshot_hash) -> dict
append_script_generation_event(run_id, *, sequence, event_type, payload) -> dict
list_script_generation_events(run_id, *, after_sequence=0) -> list[dict]
transition_script_generation_run(run_id, *, expected_statuses, status,
                                 revision_id="", error_code="", evidence_object_id="") -> dict
get_script_generation_run(run_id) -> dict | None
```

Use `BEGIN IMMEDIATE` and compare-and-set statuses. Event payloads, including text deltas, go to object store; SQL stores event type/object id/hash/size only.

- [ ] **Step 5: Prove restart unknown-outcome behavior**

```python
def test_recovery_marks_orphaned_submitting_unknown(store):
    create_prepared_run(store, "run-1")
    assert store.claim_script_generation_run("run-1")["status"] == "submitting"
    assert store.recover_script_generation_runs()["unknown_outcome"] == 1
    assert store.get_script_generation_run("run-1")["status"] == "unknown_outcome"
```

- [ ] **Step 6: Run migration/store green tests**

```bash
python3 -m pytest -q tests/web/test_script_stream_store.py \
  tests/web/test_supplier_migration.py tests/web/test_m6b_migration.py
python3 migration/tools/verify_migration.py
```

- [ ] **Step 7: Commit Task 5**

```bash
git add ai_drama_web/store.py tests/web/test_script_stream_store.py \
  tests/web/test_supplier_migration.py migration/tools/verify_migration.py
git commit -m "feat: persist streaming script generation sessions"
```

### Task 6: Split runtime prepare/finalize and build the durable runner

**Files:**

- Modify: `ai_drama_runtime/services.py`
- Modify: `ai_drama_web/services/script_workflow.py`
- Modify: `ai_drama_web/services/m6_generation.py`
- Create: `ai_drama_web/services/script_generation_stream.py`
- Create: `tests/web/test_script_generation_runner.py`
- Modify: `tests/web/test_script_workflow_api.py`

**Interfaces:**

- Consumes: Task 4 stream gateway and Task 5 store methods。
- Produces: `PreparedScriptExecution`、`prepare_script_inputs`、`finalize_prepared_script`、`M6GenerationCoordinator.prepare_text_stream`、`ScriptGenerationRunner.run_cycle`。

- [ ] **Step 1: Write prepare-before-network and exactly-once red tests**

```python
def test_runner_persists_run_and_snapshot_before_provider(app):
    app.gateway.before_invoke = lambda: assert_prepared_rows(app.store)
    app.workflow.start_script_generation("chapter-1", idempotency_key="click-1")
    result = app.runner.run_cycle()
    assert result.started == 1
    assert app.gateway.submit_count == 1

def test_restart_does_not_resubmit_streaming_session(app):
    session = seed_streaming_session(app.store)
    restarted = ScriptGenerationRunner.from_app(app)
    assert restarted.run_cycle().started == 0
    assert restarted.gateway.submit_count == 0
    assert app.store.get_script_generation_run(session["run_id"])["status"] == "unknown_outcome"
```

- [ ] **Step 2: Run red test**

Run: `python3 -m pytest -q tests/web/test_script_generation_runner.py`

Expected: FAIL because runner and prepare/finalize APIs are missing.

- [ ] **Step 3: Extract preparation while preserving legacy behavior**

```python
@dataclass(frozen=True)
class PreparedScriptExecution:
    run_id: str
    runtime_request: RuntimeRequest
    request_object_id: str
    skill: object
    validation_root: Path

def prepare_script_inputs(self, skill, artifact_id, project_id, chapter_id, inputs, runtime, model):
    runtime_request = build_runtime_request_from_inputs(skill, inputs, runtime, model or "")
    return self._prepare_script_request(
        skill=skill, artifact_id=artifact_id, project_id=project_id,
        chapter_id=chapter_id, runtime=runtime, resolved_model=model,
        runtime_request=runtime_request,
        input_snapshots=self._input_snapshots_from_request(runtime_request),
        validation_root=skill.root,
    )
```

Refactor current `_execute_script_request` so legacy `run_script_inputs` calls prepare → synchronous Provider → finalize. Existing request JSON, hashes and statuses must stay unchanged.

`M6GenerationCoordinator.prepare_text_stream` normalizes the RuntimeRequest, resolves the current binding/credential, freezes the snapshot and calls one ProductStore transaction that inserts execution snapshot、supplier text run and script generation session. It returns:

```python
@dataclass(frozen=True)
class PreparedTextStream:
    session_run_id: str
    supplier_text_run_id: str
    snapshot_hash: str
    request_object_id: str
```

The transaction uses snapshot-aware request hash and idempotency conflict rules before any network call.

- [ ] **Step 4: Finalize through the existing parser and validators**

```python
def finalize_prepared_script(self, prepared, *, output, usage, provider, model, duration_ms):
    response_object_id = self.store.write_text_object(output)
    script_text = parse_script_response(output)
    content_object_id = self.store.write_text_object(script_text)
    revision = self._insert_script_revision_from_prepared(
        prepared, content_object_id=content_object_id,
        raw_response_object_id=response_object_id, provider=provider,
        model=model, usage=usage, duration_ms=duration_ms,
    )
    validations = run_declared_validators(
        self.store, prepared.skill, revision, prepared.validation_root, repo_root=self.repo_root,
    )
    self._apply_required_validation_status(prepared.run_id, validations)
    return RunResult(run=self.store.get_run(prepared.run_id), revision=revision,
                     validation_results=validations,
                     adapter_request_json=prepared.runtime_request.to_json())
```

On parse failure, preserve assembled response, mark `PARSE_FAILED`, and create no revision.

- [ ] **Step 5: Implement one-cycle durable runner**

```python
def run_cycle(self):
    self.store.recover_script_generation_runs()
    session = self.store.next_prepared_script_generation_run()
    if session is None:
        return ScriptGenerationCycleResult()
    claimed = self.store.claim_script_generation_run(session["run_id"])
    try:
        for frame in self.gateway.invoke_stream(claimed["snapshot_hash"], "textStream", self._request(claimed)):
            self._apply_frame(claimed, frame)
    except Exception as exc:
        self._fail_without_retry(claimed, exc)
    return ScriptGenerationCycleResult(started=1)
```

Persist each `text_delta` before visibility. `completed` assembles chunks once, calls finalizer, writes `revision_id`, and cannot be replayed into a second revision.

- [ ] **Step 6: Prove Skill inputs and target duration remain present**

```python
def test_streaming_prepare_keeps_skill_inputs_and_duration(app):
    prepared = app.workflow.start_script_generation(
        "chapter-1", idempotency_key="click-1", target_duration_minutes=4,
    )
    request = json.loads(app.runtime.read_text(prepared["request_object_id"]))
    assert request["skill"]["version"] == "v0.6.1-rc2.4"
    inputs = {item["logical_type"]: item["content"] for item in request["inputs"]}
    assert "本次改编目标时长：4 分钟" in inputs["production_brief"]
    assert {"source_chapter", "series_canon", "characters", "production_brief"} <= inputs.keys()
```

- [ ] **Step 7: Run focused and legacy regression**

```bash
python3 -m pytest -q tests/web/test_script_generation_runner.py \
  tests/web/test_script_workflow_api.py \
  tests/acceptance/test_source_to_script_fake_provider.py tests/test_manual_revision.py
```

- [ ] **Step 8: Commit Task 6**

```bash
git add ai_drama_runtime/services.py ai_drama_web/services/script_workflow.py \
  ai_drama_web/services/m6_generation.py \
  ai_drama_web/services/script_generation_stream.py \
  tests/web/test_script_generation_runner.py tests/web/test_script_workflow_api.py
git commit -m "feat: run durable streaming script generations"
```

### Task 7: Expose start, status and reconnectable local SSE APIs

**Files:**

- Modify: `ai_drama_web/config.py`
- Modify: `ai_drama_web/app.py`
- Modify: `ai_drama_web/routers/scripts.py`
- Modify: `ai_drama_web/schemas/workflows.py`
- Create: `tests/web/test_script_stream_api.py`
- Modify: `tests/acceptance/test_m6e_rollout_rollback.py`

**Interfaces:**

- Consumes: Task 6 workflow/runner and Task 5 sequences。
- Produces: start/status/event APIs and lifecycle-managed runner。

- [ ] **Step 1: Write API red tests**

```python
def test_start_returns_202_before_provider_completion(client):
    response = client.post(
        "/api/chapters/chapter-1/script/generations",
        headers={"Idempotency-Key": "click-1"},
        json={"target_duration_minutes": 4},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "prepared"
    assert response.json()["last_sequence"] == 0

def test_events_replay_only_after_cursor(client, completed_stream):
    response = client.get(f"/api/script-generation-runs/{completed_stream}/events?after_sequence=1")
    assert "id: 2" in response.text
    assert "id: 1" not in response.text
    assert "event: revision_completed" in response.text
```

- [ ] **Step 2: Run red test**

Run: `python3 -m pytest -q tests/web/test_script_stream_api.py`

Expected: 404 for missing routes.

- [ ] **Step 3: Add schema and feature flag**

```python
class ScriptGenerationRunRead(BaseModel):
    run_id: str
    status: str
    last_sequence: int
    character_count: int
    revision_id: str = ""
    error_code: str = ""

class Settings(BaseSettings):
    script_streaming_enabled: bool = False
```

The existing prefix exposes `AI_DRAMA_SCRIPT_STREAMING_ENABLED`.

- [ ] **Step 4: Implement 202 start endpoint**

```python
@router.post("/chapters/{chapter_id}/script/generations", status_code=202,
             response_model=ScriptGenerationRunRead)
async def start_script_generation(
    chapter_id: str, request: Request,
    payload: ScriptGenerationRequest = Body(default_factory=ScriptGenerationRequest),
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    if not request.app.state.settings.script_streaming_enabled:
        return _error(409, "SCRIPT_STREAMING_DISABLED", "script streaming is disabled")
    return request.app.state.script_streaming_workflow.start_script_generation(
        chapter_id, idempotency_key=idempotency_key,
        target_duration_minutes=payload.target_duration_minutes,
    )
```

- [ ] **Step 5: Implement replay-then-follow SSE**

```python
async def event_stream(run_id: str, after_sequence: int):
    cursor = after_sequence
    while True:
        for event in store.list_script_generation_events(run_id, after_sequence=cursor):
            cursor = event["sequence"]
            yield encode_sse(event)
        current = store.get_script_generation_run(run_id)
        if current["status"] in {"completed", "failed", "unknown_outcome"}:
            return
        await asyncio.sleep(0.25)
```

Set `Cache-Control: no-store`, `X-Accel-Buffering: no`, bounded heartbeat, same-origin access and application-layer loopback enforcement.

- [ ] **Step 6: Start/stop runner in app lifespan**

Create runner only when both flags are true. Recovery runs before new work. Shutdown marks unprovable in-flight submissions `unknown_outcome` without resubmission.

- [ ] **Step 7: Prove flag rollback**

```python
def test_streaming_flag_off_keeps_legacy_endpoint(client):
    assert client.post("/api/chapters/chapter-1/script/generations",
                       headers={"Idempotency-Key": "x"}).status_code == 409
    assert client.post("/api/chapters/chapter-1/script/generate").status_code == 200
```

- [ ] **Step 8: Run focused tests**

```bash
python3 -m pytest -q tests/web/test_script_stream_api.py \
  tests/acceptance/test_m6e_rollout_rollback.py tests/web/test_script_workflow_api.py
```

- [ ] **Step 9: Commit Task 7**

```bash
git add ai_drama_web/config.py ai_drama_web/app.py ai_drama_web/routers/scripts.py \
  ai_drama_web/schemas/workflows.py tests/web/test_script_stream_api.py \
  tests/acceptance/test_m6e_rollout_rollback.py
git commit -m "feat: expose reconnectable script generation stream"
```

### Task 8: Add frontend stream client and central live-draft UI

**Files:**

- Modify: `web/src/features/script/api.ts`
- Create: `web/src/features/script/streaming.ts`
- Create: `web/src/features/script/useScriptGenerationStream.ts`
- Modify: `web/src/features/chapter/SourceTab.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`
- Modify: `web/src/features/script/ScriptTab.tsx`
- Modify: `web/src/features/script/ScriptTab.test.tsx`
- Modify: `web/src/app/app.css`

**Interfaces:**

- Consumes: Task 7 API and existing source/script workbench tokens。
- Produces: central `实时草稿` with cursor, progress, reconnect, failure retention and revision handoff。

- [ ] **Step 1: Write actual-text streaming red tests**

```tsx
test("opens script tab and appends deltas in the central editor", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "保存并生成剧本" }));
  expect(await screen.findByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
  emitScriptEvent({ type: "text_delta", sequence: 1, text: "# 第一场\n" });
  emitScriptEvent({ type: "text_delta", sequence: 2, text: "沈清荷醒来。" });
  expect(await screen.findByLabelText("实时剧本草稿")).toHaveValue("# 第一场\n沈清荷醒来。");
});

test("keeps partial text on failure and disables approval", async () => {
  seedActiveRun("run-1");
  emitScriptEvent({ type: "text_delta", sequence: 1, text: "# 第一场" });
  emitScriptEvent({ type: "failed", sequence: 2, error_code: "PROVIDER_STREAM_MALFORMED" });
  expect(await screen.findByText("生成中断 · 该内容尚未保存为正式剧本版本")).toBeInTheDocument();
  expect(screen.getByLabelText("实时剧本草稿")).toHaveValue("# 第一场");
  expect(screen.getByRole("button", { name: "确认剧本" })).toBeDisabled();
});
```

- [ ] **Step 2: Run red test**

Run: `npm --prefix web run test -- --run web/src/features/script/ScriptTab.test.tsx`

Expected: FAIL because stream API/hook/UI are missing.

- [ ] **Step 3: Add API types and idempotent start**

```ts
export type ScriptGenerationRunRead = {
  run_id: string;
  status: "prepared" | "submitting" | "streaming" | "finalizing" | "completed" | "failed" | "unknown_outcome";
  last_sequence: number;
  character_count: number;
  revision_id: string;
  error_code: string;
};

export async function startScriptGeneration(chapterId: string, minutes: number, key: string) {
  const response = await apiClient.post<ScriptGenerationRunRead>(
    `/chapters/${chapterId}/script/generations`,
    { target_duration_minutes: minutes },
    { headers: { "Idempotency-Key": key } },
  );
  return response.data;
}
```

Generate `crypto.randomUUID()` once per user click and retain it through HTTP retries. Explicit `重新生成` gets a new key.

- [ ] **Step 4: Implement sequence-deduplicated EventSource hook**

```ts
export type StreamStatus = "idle" | "prepared" | "submitting" | "streaming" |
  "finalizing" | "completed" | "failed" | "unknown_outcome";
export type StreamState = {
  active: boolean;
  status: StreamStatus;
  connection: "connected" | "reconnecting";
  text: string;
  lastSequence: number;
  revisionId: string;
  errorCode: string;
  startedAt: number;
};
export const initialStreamState: StreamState = {
  active: false, status: "idle", connection: "connected", text: "",
  lastSequence: 0, revisionId: "", errorCode: "", startedAt: 0,
};

export function useScriptGenerationStream(runId: string) {
  const [state, setState] = useState<StreamState>(initialStreamState);
  const lastSequence = useRef(0);
  useEffect(() => {
    if (!runId) return;
    const source = new EventSource(`/api/script-generation-runs/${runId}/events?after_sequence=${lastSequence.current}`);
    source.addEventListener("text_delta", event => {
      const frame = JSON.parse((event as MessageEvent).data) as TextDeltaFrame;
      if (frame.sequence <= lastSequence.current) return;
      lastSequence.current = frame.sequence;
      setState(current => ({ ...current, status: "streaming", text: current.text + frame.text }));
    });
    source.onerror = () => setState(current => ({ ...current, connection: "reconnecting" }));
    return () => source.close();
  }, [runId]);
  return state;
}
```

Add handlers for stages, failed and `revision_completed`. Never POST from the reconnect handler.

- [ ] **Step 5: Pass active run through ChapterWorkspace**

```tsx
const [activeScriptRunId, setActiveScriptRunId] = useState("");

<SourceTab chapter={chapter} onScriptGenerationStarted={(run) => {
  setActiveScriptRunId(run.run_id);
  setActiveTab("script");
}} />
<ScriptTab chapter={chapter} activeRunId={activeScriptRunId} />
```

SourceTab starts the async session after save/binding mutations and switches tabs on the 202 response.

- [ ] **Step 6: Render the live draft in central ScriptTab**

```tsx
{stream.active ? (
  <section className="script-live-draft" aria-label="剧本实时生成">
    <header>
      <Tag color="processing">实时草稿</Tag>
      <span aria-live="polite">{stageLabel(stream.status)}</span>
      <span>已接收 {countReadableCharacters(stream.text).toLocaleString("zh-CN")} 字</span>
      <span>{formatElapsed(stream.startedAt)}</span>
    </header>
    <Input.TextArea aria-label="实时剧本草稿" className="script-live-draft-editor"
                    readOnly value={stream.text} />
    {new Set(["failed", "unknown_outcome"]).has(stream.status)
      ? <Alert type="error" message="生成中断 · 该内容尚未保存为正式剧本版本" />
      : null}
  </section>
) : null}
```

Wrap the current `revisions.length === 0 ? ... : ...` revision block in `!stream.active && (...)`; do not move or rewrite its save/approve/reject semantics. On `revision_completed`, invalidate revisions, load that revision, clear live state, then enable current actions.

- [ ] **Step 7: Add follow-scroll and matching styles**

Autoscroll only within 80px of bottom. User upward scroll shows `回到生成末尾`. Reuse current blue inspector, borders, typography and spacing. Respect `prefers-reduced-motion`; `aria-live` announces stages only.

- [ ] **Step 8: Run frontend green tests/build**

```bash
npm --prefix web run test -- --run web/src/features/script/ScriptTab.test.tsx
npm --prefix web run test -- --run
npm --prefix web run build
```

- [ ] **Step 9: Commit Task 8**

```bash
git add web/src/features/script/api.ts web/src/features/script/streaming.ts \
  web/src/features/script/useScriptGenerationStream.ts \
  web/src/features/chapter/SourceTab.tsx web/src/features/chapter/ChapterWorkspace.tsx \
  web/src/features/script/ScriptTab.tsx web/src/features/script/ScriptTab.test.tsx web/src/app/app.css
git commit -m "feat: stream script text in the central editor"
```

### Task 9: Complete fake-provider E2E, restart recovery and verifier

**Files:**

- Create: `tests/acceptance/test_streaming_script_fake_provider.py`
- Create: `web/e2e/script-streaming.spec.ts`
- Create: `tools/verify_streaming_script_generation.py`
- Modify: `migration/tools/verify_migration.py`

**Interfaces:**

- Consumes: Tasks 1–8 complete chain。
- Produces: deterministic acceptance evidence with zero real requests。

- [ ] **Step 1: Add deterministic fake gateway**

```python
class FakeStreamingGateway:
    def __init__(self):
        self.submit_count = 0

    def invoke_stream(self, snapshot_hash, operation, request):
        self.submit_count += 1
        assert operation == "textStream"
        script = _mock_script("fake-stream")
        split_at = len(script) // 2
        yield {"type": "started", "sequence": 0}
        yield {"type": "text_delta", "sequence": 1, "text": script[:split_at]}
        yield {"type": "text_delta", "sequence": 2, "text": script[split_at:]}
        yield {"type": "usage", "sequence": 3, "usage": {"total_tokens": 3}}
        yield {"type": "completed", "sequence": 4, "evidence": {"schema": "fake-v1"}}
```

- [ ] **Step 2: Prove one validated revision and one submit**

```python
def test_fake_stream_creates_one_validated_revision(app):
    session = start_stream(app.client, idempotency_key="click-1")
    app.runner.run_cycle()
    app.runner.run_cycle()
    final = app.client.get(f"/api/script-generation-runs/{session['run_id']}").json()
    assert final["status"] == "completed"
    assert final["revision_id"]
    assert app.gateway.submit_count == 1
    revision = latest_script_revision(app.client)
    assert revision["content"].startswith("# 第一场")
    assert all(row["status"] == "PASS" for row in revision["validation_results"] if row["required"])
```

- [ ] **Step 3: Cover restart, malformed, duplicate and rollback**

Required scenarios:

```text
prepared restart → one submit
submitting restart → unknown_outcome and zero resubmit
browser reconnect → chunk replay and zero duplicate text
duplicate frame → protocol failure and zero resubmit
completed replay → same revision_id
feature flag off → legacy synchronous endpoint
tracked secret scan → clean
real request counter → 0
```

- [ ] **Step 4: Add Playwright central-editor test**

```ts
test("shows streamed script in the central editor", async ({ page }) => {
  await page.goto("/projects/project-1/chapters/chapter-1");
  await page.getByRole("button", { name: "保存并生成剧本" }).click();
  await expect(page.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByLabel("实时剧本草稿")).toHaveValue(/# 第一场/);
  await expect(page.getByText("实时草稿")).toBeVisible();
});
```

- [ ] **Step 5: Implement semantic verifier**

`tools/verify_streaming_script_generation.py` reports:

```text
STREAM-001 sanitized malformed evidence
STREAM-002 exact Aixora response fixture
STREAM-003 Worker v2 ordered frames
STREAM-004 snapshot-routed textStream
STREAM-005 pre-submit durable session
STREAM-006 exactly-once submit
STREAM-007 reconnect chunk replay
STREAM-008 central editor text deltas
STREAM-009 parser and Skill validators
STREAM-010 feature-flag rollback
STREAM-011 tracked secret scan
STREAM-012 zero real provider requests
```

- [ ] **Step 6: Run complete fake acceptance**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
npm --prefix worker test
python3 tools/verify_m3_agnes_generation.py
python3 tools/verify_m4_chapter_rehearsal.py
python3 tools/verify_m6b_model_catalog_binding.py
python3 tools/verify_m6c_adapter_cutover.py
python3 tools/verify_streaming_script_generation.py
python3 migration/tools/verify_migration.py
git diff --check
```

Expected: PASS; `REAL_PROVIDER_REQUESTS=false`.

- [ ] **Step 7: Commit Task 9**

```bash
git add tests/acceptance/test_streaming_script_fake_provider.py web/e2e/script-streaming.spec.ts \
  tools/verify_streaming_script_generation.py migration/tools/verify_migration.py
git commit -m "test: verify streaming script generation end to end"
```

### Task 10: Design QA, reviews, report and separately authorized real acceptance

**Files:**

- Create: `docs/superpowers/reports/2026-07-19-streaming-script-generation-verification.md`
- Modify only for review defects: files from Tasks 1–9.

**Interfaces:**

- Consumes: complete fake-verified implementation。
- Produces: review-ready branch, report and exact real-request accounting。

- [ ] **Step 1: Run Product Design comparison**

Capture `starting`、multiline `streaming`、`reconnecting`、partial `failed` and `completed` at `1440×1024`、`1180×800`、`768×1024`. Compare with the existing source-to-script workbench reference and tokens. Fix cropping, page-level horizontal overflow, invisible status, footer overlap and auto-scroll traps.

- [ ] **Step 2: Run accessibility checks**

Verify keyboard order, focus after automatic tab switch, stage-only `aria-live`, disabled approval, reconnect visibility, 4.5:1 status contrast and reduced-motion cursor.

- [ ] **Step 3: Perform two independent read-only reviews**

Required outputs:

```text
SPECIFICATION_PRODUCT_REVIEW=PASS
TECHNICAL_SECURITY_REVIEW=PASS
BLOCKERS=NONE
HIGH_FINDINGS=NONE
REAL_PROVIDER_REQUESTS=false
```

Fix every blocker/high and rerun Task 9 verification.

- [ ] **Step 4: Write verification report**

Record branch/commit, schema migration, fake submit count, restart/reconnect evidence, viewport evidence, parser/Skill validators, flags, secret scan and exact real counters.

- [ ] **Step 5: Stop at real acceptance gate**

Ask for `AUTHORIZE_ONE_REAL_AIXORA_STREAMING_SCRIPT_TEST`. This permits exactly one local `gpt-5.6-sol` streaming script generation. It does not permit retry, Luna, images, video, batch work or another request.

- [ ] **Step 6: If authorized, run exactly one real acceptance**

Acceptance requires one Provider submit, visible first delta, incremental central Markdown, successful final parse, required Skill validators, one formal revision, no secret/raw response leakage and no retry. On failure, save only stable error and sanitized evidence; do not submit again.

- [ ] **Step 7: Run closure and commit report**

```bash
git diff --check
git status --short
git add docs/superpowers/reports/2026-07-19-streaming-script-generation-verification.md
git commit -m "docs: verify streaming script generation"
```

Push current branch without force and update/create the review handoff according to `AGENTS.md`.

## Self-Review Result

- Spec coverage: diagnostics、no-guess parsing、Worker isolation/versioning、snapshot routing、durable chunks、exactly-once、restart/reconnect、local SSE、central editor streaming、Skill/parser/validators、rollback、fake E2E、visual/accessibility QA and real gate each map to a task.
- Placeholder scan: clean; every code-changing task includes an exact interface, red test, implementation shape, green command and commit boundary.
- Type consistency: identifiers are `run_id`; ordering is `sequence`; resume uses `after_sequence`; completion exposes `revision_id`; failure uses `error_code`.
- Scope check: subsystems are sequentially dependent through one protocol, so one plan with independently reviewable commits is safer than separate plans that can drift.
