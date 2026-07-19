import json
from types import SimpleNamespace

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.services.m6_generation import M6GenerationCoordinator
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import SupplierCredentialStore
from ai_drama_web.suppliers.resolution import ModelBindingService
from ai_drama_web.suppliers.worker import (
    SupplierWorker,
    SupplierWorkerError,
    current_worker_runtime_version,
)
from tests.web.model_test_support import create_model, install_test_supplier_runtime


SAFE_SHAPE = {
    "schema": "provider-response-shape-v1",
    "httpStatus": 200,
    "contentType": "application/json",
    "byteLength": 123,
    "bodyType": "object",
    "topLevelKeys": ["output", "secret"],
    "statusType": "undefined",
    "outputCount": 1,
    "outputItemTypes": ["message"],
    "contentItemTypes": [],
    "contentFieldNames": [],
    "usageFieldNames": [],
}


class _MalformedGateway:
    def invoke(self, _snapshot_hash, _operation, _request):
        raise SupplierWorkerError(
            "PROVIDER_RESPONSE_MALFORMED",
            "supplier operation failed",
            evidence={**SAFE_SHAPE, "Authorization": "Bearer hidden"},
        )


def test_supplier_worker_carries_host_error_evidence(tmp_path):
    entrypoint = tmp_path / "fixture-worker.mjs"
    entrypoint.write_text(
        """
let input = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) input += chunk;
JSON.parse(input);
process.stdout.write(JSON.stringify({
  ok: false,
  error: {
    code: "PROVIDER_RESPONSE_MALFORMED",
    message: "PROVIDER_RESPONSE_MALFORMED",
    evidence: {schema: "provider-response-shape-v1", topLevelKeys: ["output"]}
  }
}));
""".strip()
    )
    worker = SupplierWorker(worker_entrypoint=entrypoint)
    artifact = SimpleNamespace(
        helper_api_version="ai-drama-helper-v2",
        worker_runtime_version=current_worker_runtime_version(),
        compiled_code="",
    )

    with pytest.raises(SupplierWorkerError) as exc_info:
        worker.invoke(artifact, "textRequest", {})

    assert exc_info.value.evidence == {
        "schema": "provider-response-shape-v1",
        "topLevelKeys": ["output"],
    }


def _coordinator(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Streaming evidence")
    supplier = store.list_suppliers()[0]
    install_test_supplier_runtime(store, supplier)
    supplier = store.get_supplier(supplier.supplier_id)
    model = create_model(
        store,
        supplier,
        capability="text",
        name="fake-text",
        catalog_revision=0,
        key="streaming-evidence-text",
    )
    ModelBindingService(store).replace(
        project.project_id,
        defaults={"text": model.supplier_model_id, "image": "", "video": ""},
        overrides={},
        expected_revision=0,
    )
    credentials = SupplierCredentialStore(store, tmp_path / "credentials")
    credentials.replace(supplier.supplier_id, "selected-secret", expected_revision=0)
    return runtime, store, project, M6GenerationCoordinator(
        store,
        runtime,
        credentials,
        _MalformedGateway(),
    )


def test_malformed_response_persists_shape_without_values(tmp_path):
    runtime, store, project, coordinator = _coordinator(tmp_path)

    with pytest.raises(SupplierWorkerError) as exc_info:
        coordinator.execute_text(
            project_id=project.project_id,
            operation_key="script_adaptation",
            idempotency_key="malformed-shape",
            request={"prompt": "adapt"},
        )

    assert exc_info.value.code == "PROVIDER_RESPONSE_MALFORMED"
    run = store.conn.execute(
        "SELECT * FROM supplier_text_runs WHERE idempotency_key = ?",
        ("malformed-shape",),
    ).fetchone()
    assert run["status"] == "failed"
    assert run["error_code"] == "PROVIDER_RESPONSE_MALFORMED"
    evidence = json.loads(runtime.read_text(run["evidence_object_id"]))
    assert evidence["topLevelKeys"] == ["output", "secret"]
    serialized = json.dumps(evidence)
    assert "hidden" not in serialized
    assert "Authorization" not in serialized
