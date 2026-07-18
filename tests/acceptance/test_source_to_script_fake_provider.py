import json

from fastapi.testclient import TestClient

from ai_drama_runtime.runtime import _mock_script
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app
from ai_drama_web.services.m6_generation import M6GenerationCoordinator
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.credentials import SupplierCredentialStore
from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from ai_drama_web.suppliers.snapshots import load_snapshot
from ai_drama_web.store import ProductStore


FAKE_SOURCE = """
export const vendor = {
  id: "source-script-fake", version: "1.0.0", name: "Source Script Fake", author: "Acceptance",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "source-script-fake-local", inputs: [], inputValues: {}, models: []
};
export async function textRequest() { return { output: "unused", usage: {} }; }
""".strip()


class FakeScriptGateway:
    def __init__(self, store):
        self.store = store
        self.calls = []

    def invoke(self, snapshot_hash, operation, request):
        snapshot = load_snapshot(self.store, snapshot_hash)
        self.calls.append((snapshot_hash, operation, snapshot.provider_model_name, request))
        return {
            "output": json.dumps(
                {"script_markdown": _mock_script("fake-project-model")},
                ensure_ascii=False,
            ),
            "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        }


def _install_fake_text_supplier(data_root):
    runtime = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    store = ProductStore(runtime)
    supplier = store.create_supplier(slug="source-script-fake", display_name="Source Script Fake")
    artifact = compile_supplier(FAKE_SOURCE, runtime_store=store.runtime)
    store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id=artifact.source_object_id,
        source_hash=artifact.source_hash,
        compiled_artifact_object_id=artifact.compiled_artifact_object_id,
        compiled_artifact_hash=artifact.compiled_artifact_hash,
        manifest_hash=artifact.manifest_hash,
        manifest=artifact.vendor,
        adapter_contract_version=artifact.adapter_contract_version,
        worker_protocol_version="1",
        worker_runtime_version=artifact.worker_runtime_version,
        compiler_name=artifact.compiler_name,
        compiler_version=artifact.compiler_version,
        compiler_options_hash=artifact.compiler_options_hash,
        helper_api_version=artifact.helper_api_version,
        rate_limit_bucket_key=artifact.vendor["rateLimitBucketKey"],
        expected_revision=supplier.revision,
    )
    SupplierCredentialStore(store, data_root).replace(
        supplier.supplier_id,
        "local-fake-credential",
        expected_revision=0,
    )
    model, _ = ModelCatalogService(store).create_overlay(
        supplier.supplier_id,
        provider_model_name="fake-project-model",
        display_name="Fake Project Text",
        capability="text",
        definition={"constraints": {"offline": True}},
        expected_catalog_revision=0,
        idempotency_key="source-script-fake-text",
    )
    model_id = model.supplier_model_id
    runtime.close()
    return model_id


def test_project_model_binding_drives_source_to_script_with_local_fake_provider(tmp_path):
    data_root = tmp_path / "runtime-data"
    model_id = _install_fake_text_supplier(data_root)
    app = create_app(data_root=data_root, skills_root="skills")
    app.state.settings.m6_supplier_execution_enabled = True

    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        gateway = FakeScriptGateway(app.state.product_store)
        app.state.m6_generation_coordinator = M6GenerationCoordinator(
            app.state.product_store,
            app.state.runtime_store,
            app.state.supplier_credential_store,
            gateway,
        )
        project = client.post(
            "/api/projects",
            json={"name": "Fake source-to-script acceptance"},
        ).json()
        chapter = client.post(
            f"/api/projects/{project['project_id']}/chapters",
            json={"title": "第一章", "position": 1},
        ).json()

        current_bindings = client.get(
            f"/api/projects/{project['project_id']}/model-bindings",
        )
        saved_bindings = client.put(
            f"/api/projects/{project['project_id']}/model-bindings",
            headers={"If-Match": current_bindings.headers["etag"]},
            json={
                "defaults": {"text": "", "image": "", "video": ""},
                "operation_overrides": {"script_adaptation": model_id},
            },
        )
        source = client.post(
            f"/api/chapters/{chapter['chapter_id']}/source-revisions",
            json={"content": "沈清荷重生后重新翻开账册，决定改写命运。"},
        )
        generated = client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate")

    assert saved_bindings.status_code == 200
    assert source.status_code == 200
    assert generated.status_code == 200
    assert "Mock Drama Script Revision" in generated.json()["content"]
    assert len(gateway.calls) == 1
    assert gateway.calls[0][1] == "textRequest"
    assert gateway.calls[0][2] == "fake-project-model"
