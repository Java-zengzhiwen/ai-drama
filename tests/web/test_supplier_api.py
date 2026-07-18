import json

from fastapi.testclient import TestClient

from ai_drama_web.routers import suppliers as supplier_router
from ai_drama_web.app import create_app
from ai_drama_web.suppliers.builtin_adapters import install_builtin_adapters


SOURCE = """
export const vendor = {
  id: "api-test",
  version: "1.0.0",
  name: "API Test",
  author: "Local",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "api-test",
  inputs: [],
  inputValues: {},
  models: []
};
export async function textRequest(request: { prompt: string }) {
  return { text: request.prompt };
}
""".strip()


def _client(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    return TestClient(app, client=("127.0.0.1", 50000))


def test_supplier_api_creates_custom_empty_template_not_duplicate(tmp_path):
    with _client(tmp_path) as client:
        missing_precondition = client.post(
            "/api/suppliers", json={"slug": "studio", "display_name": "Studio"}
        )
        response = client.post(
            "/api/suppliers",
            json={"slug": "studio", "display_name": "Studio"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-studio"},
        )
        replay = client.post(
            "/api/suppliers",
            json={"slug": "studio", "display_name": "Studio"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-studio"},
        )
        conflict = client.post(
            "/api/suppliers",
            json={"slug": "other", "display_name": "Other"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-studio"},
        )

    assert missing_precondition.status_code == 428
    assert response.status_code == 201, response.text
    assert replay.status_code == 200
    assert replay.json()["supplier_id"] == response.json()["supplier_id"]
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert response.json()["source"] == "custom"
    assert response.json()["current_supplier_version_id"]

    with _client(tmp_path) as client:
        source = client.get(
            f"/api/suppliers/{response.json()['supplier_id']}/code"
        ).json()["source"]
    assert "AI 生成适配代码步骤" in source
    assert "不要提供真实 API Key" in source
    assert "helpers.http.request" in source
    assert "video_id" in source and "task_id" in source
    assert "export const vendor" in source
    assert "models: []" in source
    assert "module.exports" in source
    for required_guidance in (
        "YOUR_API_KEY",
        "import",
        "require",
        "process",
        "fetch",
        "Node 内建模块",
        "socket",
        "子进程",
        "axios",
        "logger",
        "pollTask",
        "createOpenAI",
        "签名查询",
        "顶层网络",
        "测试成功后再绑定项目",
    ):
        assert required_guidance in source
    assert "exports.vendor" in source
    assert "export {}" in source


def test_supplier_creation_replay_does_not_recompile_template(tmp_path, monkeypatch):
    with _client(tmp_path) as client:
        first = client.post(
            "/api/suppliers",
            json={"slug": "replay", "display_name": "Replay"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-replay"},
        )
        monkeypatch.setattr(
            supplier_router,
            "compile_supplier",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("recompiled")),
        )
        replay = client.post(
            "/api/suppliers",
            json={"slug": "replay", "display_name": "Replay"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-replay"},
        )

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["supplier_id"] == first.json()["supplier_id"]


def test_supplier_config_secret_and_code_mutations_require_matching_etags(tmp_path):
    with _client(tmp_path) as client:
        created = client.post(
            "/api/suppliers",
            json={"slug": "studio", "display_name": "Studio"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-studio"},
        ).json()
        supplier_id = created["supplier_id"]

        detail = client.get(f"/api/suppliers/{supplier_id}")
        assert detail.headers["etag"] == '"supplier-1"'
        assert detail.json()["credential"] == {"configured": False, "masked_suffix": ""}

        config = client.put(
            f"/api/suppliers/{supplier_id}/config",
            json={"values": {"base_url": "https://api.example.invalid"}},
            headers={"If-Match": '"config-1"'},
        )
        assert config.status_code == 200, config.text
        assert config.headers["etag"] == '"config-2"'

        secret_value = "local-test-secret-1234"
        secret = client.put(
            f"/api/suppliers/{supplier_id}/secret",
            json={"credential": secret_value},
            headers={"If-Match": '"credential-0"'},
        )
        assert secret.status_code == 200, secret.text
        assert secret.json() == {"configured": True, "masked_suffix": "1234"}
        assert secret_value not in secret.text

        code = client.put(
            f"/api/suppliers/{supplier_id}/code",
            json={"source": SOURCE},
            headers={"If-Match": '"supplier-1"'},
        )
        assert code.status_code == 200, code.text
        assert code.headers["etag"] == '"supplier-2"'
        assert code.json()["compiler_name"] == "esbuild"
        assert client.get(f"/api/suppliers/{supplier_id}/code").json()["source"] == SOURCE

        stale = client.put(
            f"/api/suppliers/{supplier_id}/code",
            json={"source": SOURCE},
            headers={"If-Match": '"supplier-1"'},
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["error_code"] == "REVISION_CONFLICT"

        masked = client.get(f"/api/suppliers/{supplier_id}")
        assert masked.json()["credential"] == {"configured": True, "masked_suffix": "1234"}
        assert secret_value not in masked.text

        deleted = client.delete(
            f"/api/suppliers/{supplier_id}/secret",
            headers={"If-Match": '"credential-1"'},
        )
        assert deleted.status_code == 200
        assert deleted.json() == {"configured": False, "masked_suffix": ""}
        assert deleted.headers["etag"] == '"credential-2"'

        absent = client.delete(
            f"/api/suppliers/{supplier_id}/secret",
            headers={"If-Match": '"credential-2"'},
        )
        assert absent.status_code == 200
        assert absent.headers["etag"] == '"credential-2"'


def test_supplier_management_projection_exposes_non_secret_manifest_and_config(tmp_path):
    with _client(tmp_path) as client:
        supplier = client.get("/api/suppliers").json()[0]
        supplier_id = supplier["supplier_id"]
        detail = client.get(f"/api/suppliers/{supplier_id}")

        assert detail.status_code == 200
        assert detail.headers["etag"] == f'"supplier-{supplier["revision"]}"'
        payload = detail.json()
        assert payload["author"] == "AI Drama"
        assert payload["version"]
        assert isinstance(payload["inputs"], list)
        assert isinstance(payload["input_values"], dict)
        assert isinstance(payload["config_values"], dict)
        assert isinstance(payload["capabilities"], list)
        assert payload["model_count"] == len(
            client.get(f"/api/suppliers/{supplier_id}/models").json()
        )
        assert "source" not in payload["manifest"]
        assert "credential" not in payload["config_values"]


def test_supplier_management_projection_round_trips_config_without_credential(tmp_path):
    secret_value = "m6d-never-return-this-1234"
    with _client(tmp_path) as client:
        created = client.post(
            "/api/suppliers",
            json={"slug": "m6d-local", "display_name": "M6D Local"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-m6d-local"},
        ).json()
        supplier_id = created["supplier_id"]
        config = client.put(
            f"/api/suppliers/{supplier_id}/config",
            json={"values": {"base_url": "https://local.example.invalid/v1", "region": "test"}},
            headers={"If-Match": '"config-1"'},
        )
        assert config.status_code == 200
        saved = client.put(
            f"/api/suppliers/{supplier_id}/secret",
            json={"credential": secret_value},
            headers={"If-Match": '"credential-0"'},
        )
        assert saved.status_code == 200

        listing = client.get("/api/suppliers")
        detail = client.get(f"/api/suppliers/{supplier_id}")
        payload = detail.json()
        assert payload["config_values"] == {
            "base_url": "https://local.example.invalid/v1",
            "region": "test",
        }
        assert payload["base_url_summary"] == "https://local.example.invalid/v1"
        assert payload["credential"] == {"configured": True, "masked_suffix": "1234"}
        assert secret_value not in listing.text
        assert secret_value not in detail.text


def test_supplier_management_projection_strips_url_userinfo_query_and_fragment(tmp_path):
    sensitive_url = "https://user:password@local.example.invalid:8443/v1?token=secret#private"
    with _client(tmp_path) as client:
        created = client.post(
            "/api/suppliers",
            json={"slug": "safe-url", "display_name": "Safe URL"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-safe-url"},
        ).json()
        supplier_id = created["supplier_id"]
        saved = client.put(
            f"/api/suppliers/{supplier_id}/config",
            json={"values": {"base_url": sensitive_url}},
            headers={"If-Match": '"config-1"'},
        )
        assert saved.status_code == 200
        detail = client.get(f"/api/suppliers/{supplier_id}")

    assert detail.json()["config_values"]["base_url"] == "https://local.example.invalid:8443/v1"
    assert detail.json()["base_url_summary"] == "https://local.example.invalid:8443/v1"
    assert "user" not in detail.text
    assert "password" not in detail.text
    assert "token" not in detail.text
    assert "private" not in detail.text


def test_partial_config_update_preserves_hidden_non_string_agnes_values(tmp_path):
    with _client(tmp_path) as client:
        client.portal.call(lambda: install_builtin_adapters(client.app.state.product_store))
        supplier = next(item for item in client.get("/api/suppliers").json() if item["slug"] == "agnes")
        saved = client.put(
            f"/api/suppliers/{supplier['supplier_id']}/config",
            json={"values": {"video_endpoint": "https://local.example.invalid/v1/videos"}},
            headers={"If-Match": f'"config-{supplier["config_revision"]}"'},
        )
        assert saved.status_code == 200, saved.text
        current = client.portal.call(
            lambda: client.app.state.product_store.get_supplier(
                supplier["supplier_id"]
            )
        )
        config = client.portal.call(
            lambda: client.app.state.product_store.get_config_revision(
                current.current_config_revision_id
            )
        )
        stored = client.portal.call(
            lambda: client.app.state.runtime_store.read_text(config.config_object_id)
        )

    assert json.loads(stored)["result_origins"] == [
        "https://platform-outputs.agnes-ai.space"
    ]


def test_custom_empty_supplier_management_projection_is_safe(tmp_path):
    with _client(tmp_path) as client:
        supplier = client.post(
            "/api/suppliers",
            json={"slug": "empty-ui", "display_name": "Empty UI"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-empty-ui"},
        ).json()
        detail = client.get(f"/api/suppliers/{supplier['supplier_id']}").json()

    assert detail["author"] == "AI Drama"
    assert detail["version"] == "template-1"
    assert detail["manifest"]["id"] == "empty-ui"
    assert detail["inputs"][0]["key"] == "base_url"
    assert detail["input_values"] == {"base_url": ""}
    assert detail["config_values"] == {}
    assert detail["capabilities"] == []
    assert detail["model_count"] == 0
    assert detail["base_url_summary"] == ""


def test_code_validation_is_local_and_returns_safe_diagnostic(tmp_path):
    with _client(tmp_path) as client:
        supplier = client.post(
            "/api/suppliers",
            json={"slug": "invalid", "display_name": "Invalid"},
            headers={"If-None-Match": "*", "Idempotency-Key": "create-invalid"},
        ).json()
        response = client.put(
            f"/api/suppliers/{supplier['supplier_id']}/code",
            json={"source": "import fs from 'node:fs';"},
            headers={"If-Match": '"supplier-1"'},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "FORBIDDEN_IMPORT"
    assert response.json()["detail"]["line"] == 1


def test_restore_builtin_switches_pointer_without_deleting_history(tmp_path):
    with _client(tmp_path) as client:
        supplier = client.portal.call(
            lambda: client.app.state.product_store.list_suppliers()[0]
        )
        built_in = client.portal.call(
            lambda: client.app.state.product_store.get_supplier_version(
                supplier.current_supplier_version_id
            )
        )
        overlay = client.portal.call(
            lambda: client.app.state.product_store.replace_supplier_version(
                supplier.supplier_id,
                source_object_id="overlay-source",
                source_hash="overlay-hash",
                compiled_artifact_object_id="overlay-compiled",
                compiled_artifact_hash="overlay-compiled-hash",
                manifest_hash="overlay-manifest-hash",
                expected_revision=1,
            )
        )

        response = client.post(
            f"/api/suppliers/{supplier.supplier_id}/restore-built-in",
            headers={"If-Match": '"supplier-2"'},
        )

        assert response.status_code == 200, response.text
        assert response.headers["etag"] == '"supplier-3"'
        assert response.json()["current_supplier_version_id"] == built_in.supplier_version_id
        assert client.portal.call(
            lambda: client.app.state.product_store.get_supplier_version(
                overlay.supplier_version_id
            ).source_hash
        ) == "overlay-hash"


def test_restore_builtin_synchronizes_manifest_catalog_atomically(tmp_path):
    source = """
export const vendor = {
  id: "restore", version: "1", name: "Restore", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "restore", inputs: [], inputValues: {},
  models: [{ supplierModelId: "55555555-5555-5555-5555-555555555555", providerModelName: "restore-text", displayName: "Restore Text", capability: "text" }]
};
export async function textRequest() { return { text: "fake" }; }
"""
    with _client(tmp_path) as client:
        supplier = client.get("/api/suppliers").json()[0]
        saved = client.put(
            f"/api/suppliers/{supplier['supplier_id']}/code",
            json={"source": source},
            headers={"If-Match": '"supplier-1"'},
        )
        assert saved.status_code == 200, saved.text
        before = client.get(f"/api/suppliers/{supplier['supplier_id']}/models").json()
        assert len(before) == 1 and before[0]["enabled"] == 1

        restored = client.post(
            f"/api/suppliers/{supplier['supplier_id']}/restore-built-in",
            headers={"If-Match": '"supplier-2"'},
        )
        assert restored.status_code == 200, restored.text
        after = client.get(f"/api/suppliers/{supplier['supplier_id']}/models")
        assert after.headers["etag"] == '"model-catalog-2"'
        assert len(after.json()) == 1 and after.json()[0]["enabled"] == 0
        assert after.json()[0]["model_revision_id"] == before[0]["model_revision_id"]

        stale = client.post(
            f"/api/suppliers/{supplier['supplier_id']}/restore-built-in",
            headers={"If-Match": '"supplier-2"'},
        )
        assert stale.status_code == 409
        unchanged = client.get(f"/api/suppliers/{supplier['supplier_id']}/models")
        assert unchanged.headers["etag"] == '"model-catalog-2"'
