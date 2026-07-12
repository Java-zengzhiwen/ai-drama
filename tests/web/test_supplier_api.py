from fastapi.testclient import TestClient

from ai_drama_web.app import create_app


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
    assert response.json()["current_supplier_version_id"] == ""


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
            lambda: client.app.state.product_store.replace_supplier_version(
                supplier.supplier_id,
                source_object_id="built-in-source",
                source_hash="built-in-hash",
                compiled_artifact_object_id="built-in-compiled",
                compiled_artifact_hash="built-in-compiled-hash",
                manifest_hash="built-in-manifest-hash",
                expected_revision=1,
                built_in=True,
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
                expected_revision=2,
            )
        )

        response = client.post(
            f"/api/suppliers/{supplier.supplier_id}/restore-built-in",
            headers={"If-Match": '"supplier-3"'},
        )

        assert response.status_code == 200, response.text
        assert response.headers["etag"] == '"supplier-4"'
        assert response.json()["current_supplier_version_id"] == built_in.supplier_version_id
        assert client.portal.call(
            lambda: client.app.state.product_store.get_supplier_version(
                overlay.supplier_version_id
            ).source_hash
        ) == "overlay-hash"
