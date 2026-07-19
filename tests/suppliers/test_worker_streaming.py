import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.worker import SupplierWorker, SupplierWorkerError, WorkerLimits


STREAM_SOURCE = """
export const vendor = {
  id: "stream-worker-test",
  version: "1.0.0",
  name: "Stream Worker Test",
  author: "Local",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v3",
  rateLimitBucketKey: "stream-worker-test",
  inputs: [],
  inputValues: {},
  models: [{ providerModelName: "stream-text", displayName: "Stream Text", capability: "text" }]
};
export async function textRequest() { return { output: "rollback", usage: {} }; }
export async function textStream() { return {}; }
""".strip()


def _artifact(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return compile_supplier(STREAM_SOURCE, runtime_store=runtime)


def _fixture_worker(tmp_path, name, body):
    entrypoint = tmp_path / f"{name}.mjs"
    entrypoint.write_text(
        """
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => input += chunk);
process.stdin.on("end", () => {
  JSON.parse(input);
  %s
});
""".strip()
        % body,
        encoding="utf-8",
    )
    return entrypoint


def test_worker_stream_yields_ordered_frames(tmp_path):
    entrypoint = _fixture_worker(
        tmp_path,
        "ordered-stream",
        """
for (const frame of [
  {type:"started",sequence:0},
  {type:"text_delta",sequence:1,text:"第一"},
  {type:"text_delta",sequence:2,text:"场"},
  {type:"completed",sequence:3,evidence:{schema:"provider-stream-shape-v1"}}
]) process.stdout.write(JSON.stringify(frame) + "\\n");
""".strip(),
    )
    worker = SupplierWorker(worker_entrypoint=entrypoint)

    frames = list(worker.invoke_stream(_artifact(tmp_path), "textStream", {"prompt": "x"}))

    assert [frame["type"] for frame in frames] == [
        "started",
        "text_delta",
        "text_delta",
        "completed",
    ]
    assert [frame["sequence"] for frame in frames] == [0, 1, 2, 3]


def test_worker_stream_never_forwards_adapter_supplied_evidence(tmp_path):
    artifact = _artifact(tmp_path)
    artifact = type(artifact)(
        **{
            **artifact.__dict__,
            "compiled_code": (
                "module.exports.textStream = async function() { "
                "return {evidence:{innocent:'selected-secret'}}; };"
            ),
        }
    )

    frames = list(SupplierWorker().invoke_stream(artifact, "textStream", {}))

    assert frames == [{"type": "completed", "sequence": 0, "evidence": {}}]
    assert "selected-secret" not in str(frames)


def test_worker_stream_rejects_duplicate_sequence(tmp_path):
    entrypoint = _fixture_worker(
        tmp_path,
        "duplicate-sequence",
        """
process.stdout.write(JSON.stringify({type:"started",sequence:0}) + "\\n");
process.stdout.write(JSON.stringify({type:"text_delta",sequence:0,text:"duplicate"}) + "\\n");
""".strip(),
    )
    worker = SupplierWorker(worker_entrypoint=entrypoint)

    with pytest.raises(SupplierWorkerError) as exc_info:
        list(worker.invoke_stream(_artifact(tmp_path), "textStream", {}))

    assert exc_info.value.code == "SUPPLIER_WORKER_PROTOCOL_ERROR"


def test_worker_stream_requires_one_terminal_frame(tmp_path):
    entrypoint = _fixture_worker(
        tmp_path,
        "missing-terminal",
        'process.stdout.write(JSON.stringify({type:"started",sequence:0}) + "\\n");',
    )
    worker = SupplierWorker(worker_entrypoint=entrypoint)

    with pytest.raises(SupplierWorkerError) as exc_info:
        list(worker.invoke_stream(_artifact(tmp_path), "textStream", {}))

    assert exc_info.value.code == "SUPPLIER_WORKER_PROTOCOL_ERROR"


def test_worker_stream_enforces_monotonic_deadline_and_recovers(tmp_path):
    stuck = _fixture_worker(
        tmp_path,
        "stuck-stream",
        'process.stdout.write(JSON.stringify({type:"started",sequence:0}) + "\\n"); setInterval(() => {}, 1000);',
    )
    worker = SupplierWorker(worker_entrypoint=stuck)

    with pytest.raises(SupplierWorkerError) as exc_info:
        list(
            worker.invoke_stream(
                _artifact(tmp_path),
                "textStream",
                {},
                limits=WorkerLimits(timeout_seconds=0.2),
            )
        )

    assert exc_info.value.code == "SUPPLIER_WORKER_TIMEOUT"
