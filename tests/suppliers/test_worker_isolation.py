from dataclasses import replace
from pathlib import Path

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.worker import SupplierWorker, SupplierWorkerError, WorkerLimits


SOURCE = """
export const vendor = {
  id: "worker-test",
  version: "1.0.0",
  name: "Worker Test",
  author: "Local",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "worker-test",
  inputs: [],
  inputValues: {},
  models: []
};
export async function textRequest(request: { prompt: string }) {
  return { text: request.prompt };
}
""".strip()


def _artifact(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    return compile_supplier(SOURCE, runtime_store=runtime)


def _with_code(artifact, body):
    return replace(
        artifact,
        compiled_code="module.exports.textRequest = async function(payload, helpers) { %s };" % body,
    )


def test_worker_invokes_compiled_supplier_in_fresh_process(tmp_path):
    worker = SupplierWorker()

    first = worker.invoke(_artifact(tmp_path), "textRequest", {"prompt": "first"})
    second = worker.invoke(_artifact(tmp_path), "textRequest", {"prompt": "second"})

    assert first.value == {"text": "first"}
    assert second.value == {"text": "second"}
    assert first.worker_protocol_version == "1"
    assert first.helper_api_version == "ai-drama-helper-v1"


@pytest.mark.parametrize(
    "body,expected",
    [
        ("return typeof process;", "undefined"),
        ("return typeof require;", "undefined"),
        ("return typeof fetch;", "undefined"),
        ("return typeof WebSocket;", "undefined"),
    ],
)
def test_worker_does_not_expose_host_globals(tmp_path, body, expected):
    result = SupplierWorker().invoke(_with_code(_artifact(tmp_path), body), "textRequest", {})

    assert result.value == expected


@pytest.mark.parametrize(
    "body",
    [
        "return module.constructor.constructor('return process')();",
        "return helpers.http.request.constructor('return process')();",
    ],
)
def test_worker_blocks_constructor_chain_sandbox_escape(tmp_path, body):
    with pytest.raises(SupplierWorkerError) as exc_info:
        SupplierWorker().invoke(_with_code(_artifact(tmp_path), body), "textRequest", {})

    assert exc_info.value.code == "SUPPLIER_EXECUTION_FAILED"


def test_validation_network_helper_fails_with_stable_error(tmp_path):
    artifact = _with_code(
        _artifact(tmp_path),
        "return await helpers.http.request({ url: 'https://example.invalid' });",
    )

    with pytest.raises(SupplierWorkerError) as exc_info:
        SupplierWorker().invoke(artifact, "textRequest", {}, mode="validation")

    assert exc_info.value.code == "NETWORK_DISABLED_DURING_VALIDATION"


def test_execution_has_no_native_network_and_only_injected_helper(tmp_path):
    direct = _with_code(_artifact(tmp_path), "return await fetch('https://example.invalid');")
    helper = _with_code(
        _artifact(tmp_path),
        "return await helpers.http.request({ url: 'https://example.invalid' });",
    )

    with pytest.raises(SupplierWorkerError) as direct_error:
        SupplierWorker().invoke(direct, "textRequest", {}, mode="execution")
    with pytest.raises(SupplierWorkerError) as helper_error:
        SupplierWorker().invoke(helper, "textRequest", {}, mode="execution")

    assert direct_error.value.code == "SUPPLIER_EXECUTION_FAILED"
    assert helper_error.value.code == "NETWORK_HELPER_UNAVAILABLE"


def test_worker_terminates_timeout_and_recovers_for_next_call(tmp_path):
    worker = SupplierWorker()
    stuck = _with_code(_artifact(tmp_path), "while (true) {}")

    with pytest.raises(SupplierWorkerError) as exc_info:
        worker.invoke(stuck, "textRequest", {}, limits=WorkerLimits(timeout_seconds=0.2))

    assert exc_info.value.code == "SUPPLIER_WORKER_TIMEOUT"
    assert worker.invoke(_artifact(tmp_path), "textRequest", {"prompt": "recovered"}).value == {
        "text": "recovered"
    }


def test_worker_rejects_oversized_result(tmp_path):
    artifact = _with_code(_artifact(tmp_path), "return 'x'.repeat(2048);")

    with pytest.raises(SupplierWorkerError) as exc_info:
        SupplierWorker().invoke(
            artifact,
            "textRequest",
            {},
            limits=WorkerLimits(max_output_bytes=1024),
        )

    assert exc_info.value.code == "SUPPLIER_WORKER_OUTPUT_TOO_LARGE"


def test_worker_rejects_malformed_protocol_and_recovers(tmp_path):
    broken = tmp_path / "broken-worker.mjs"
    broken.write_text("process.stdout.write('{broken');", encoding="utf-8")
    worker = SupplierWorker(worker_entrypoint=broken)

    with pytest.raises(SupplierWorkerError) as exc_info:
        worker.invoke(_artifact(tmp_path), "textRequest", {})

    assert exc_info.value.code == "SUPPLIER_WORKER_PROTOCOL_ERROR"


def test_worker_child_environment_is_allowlisted(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_AGNES_API_KEY", "must-not-cross-boundary")
    artifact = _with_code(_artifact(tmp_path), "return typeof process;")

    result = SupplierWorker().invoke(artifact, "textRequest", {})

    assert result.value == "undefined"
    assert "must-not-cross-boundary" not in repr(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("helper_api_version", "ai-drama-helper-v999"),
        ("worker_runtime_version", "v0.0.0-unavailable"),
    ],
)
def test_worker_fails_closed_for_incompatible_runtime_fingerprint(tmp_path, field, value):
    artifact = replace(_artifact(tmp_path), **{field: value})

    with pytest.raises(SupplierWorkerError) as exc_info:
        SupplierWorker().invoke(artifact, "textRequest", {})

    assert exc_info.value.code == "SUPPLIER_RUNTIME_UNAVAILABLE"
