def _supplier(client):
    return client.get("/api/suppliers").json()[0]


def test_model_crud_uses_stable_ids_etags_and_idempotency(client):
    supplier = _supplier(client)
    create_headers = {
        "If-None-Match": "*",
        "If-Match": '"model-catalog-0"',
        "Idempotency-Key": "create-api-model",
    }
    payload = {
        "provider_model_name": "api-text-v1",
        "display_name": "API Text",
        "capability": "text",
        "definition": {"temperature": {"maximum": 1}},
    }
    created = client.post(
        f"/api/suppliers/{supplier['supplier_id']}/models",
        json=payload,
        headers=create_headers,
    )
    assert created.status_code == 201, created.text
    model_id = created.json()["supplier_model_id"]
    assert created.headers["etag"] == '"model-%s-1"' % model_id
    assert created.headers["x-model-catalog-etag"] == '"model-catalog-1"'
    assert "credential" not in created.text

    replay = client.post(
        f"/api/suppliers/{supplier['supplier_id']}/models",
        json=payload,
        headers=create_headers,
    )
    assert replay.status_code == 200
    assert replay.json()["supplier_model_id"] == model_id

    listing = client.get(f"/api/suppliers/{supplier['supplier_id']}/models")
    assert listing.headers["etag"] == '"model-catalog-1"'
    assert [item["supplier_model_id"] for item in listing.json()] == [model_id]
    assert listing.json()[0]["entity_revision"] == 1

    fetched = client.get(f"/api/models/{model_id}")
    assert fetched.status_code == 200
    assert fetched.headers["etag"] == '"model-%s-1"' % model_id

    updated = client.patch(
        f"/api/models/{model_id}",
        json={"display_name": "API Text Renamed", "acknowledged_binding_count": 0},
        headers={"If-Match": '"model-%s-1", "model-catalog-1"' % model_id},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "API Text Renamed"
    assert updated.json()["supplier_model_id"] == model_id
    assert updated.json()["entity_revision"] == 2
    assert updated.headers["etag"] == '"model-%s-2"' % model_id

    stale = client.patch(
        f"/api/models/{model_id}",
        json={"enabled": False},
        headers={"If-Match": '"model-%s-1", "model-catalog-1"' % model_id},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["error_code"] == "REVISION_CONFLICT"

    deleted = client.delete(
        f"/api/models/{model_id}",
        headers={"If-Match": '"model-%s-2", "model-catalog-2"' % model_id},
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/models/{model_id}").status_code == 404


def test_model_reads_include_project_binding_count_without_snapshot_inflation(client):
    supplier = _supplier(client)
    created = client.post(
        f"/api/suppliers/{supplier['supplier_id']}/models",
        json={
            "provider_model_name": "binding-count-text",
            "display_name": "Binding Count Text",
            "capability": "text",
            "definition": {},
        },
        headers={
            "If-None-Match": "*",
            "If-Match": '"model-catalog-0"',
            "Idempotency-Key": "binding-count-text",
        },
    )
    model_id = created.json()["supplier_model_id"]
    project_id = client.post(
        "/api/projects",
        json={
            "name": "Binding Count",
            "description": "",
            "series_canon": "",
            "characters_context": "",
            "production_brief": "",
        },
    ).json()["project_id"]
    saved = client.put(
        f"/api/projects/{project_id}/model-bindings",
        json={
            "defaults": {"text": model_id, "image": "", "video": ""},
            "operation_overrides": {"storyboard_design": model_id},
        },
        headers={"If-Match": '"binding-set-0"'},
    )
    assert saved.status_code == 200

    listing = client.get(f"/api/suppliers/{supplier['supplier_id']}/models")
    detail = client.get(f"/api/models/{model_id}")

    assert listing.json()[0]["binding_count"] == 2
    assert detail.json()["binding_count"] == 2


def test_model_create_requires_preconditions_and_conflicts_on_changed_replay(client):
    supplier = _supplier(client)
    path = f"/api/suppliers/{supplier['supplier_id']}/models"
    payload = {
        "provider_model_name": "precondition",
        "display_name": "Precondition",
        "capability": "image",
        "definition": {},
    }
    assert client.post(path, json=payload).status_code == 428
    headers = {
        "If-None-Match": "*",
        "If-Match": '"model-catalog-0"',
        "Idempotency-Key": "precondition",
    }
    assert client.post(path, json=payload, headers=headers).status_code == 201
    changed = {**payload, "display_name": "Changed"}
    conflict = client.post(path, json=changed, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error_code"] == "IDEMPOTENCY_CONFLICT"


def test_supplier_code_manifest_creates_and_revises_same_base_identity(client):
    supplier = _supplier(client)
    stable_id = "44444444-4444-4444-4444-444444444444"

    def source(provider_name):
        return f"""
export const vendor = {{
  id: "manifest-api", version: "1", name: "Manifest API", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "manifest-api-bucket", inputs: [], inputValues: {{}},
  models: [{{ supplierModelId: "{stable_id}", providerModelName: "{provider_name}", displayName: "Base Text", capability: "text" }}]
}};
export async function textRequest() {{ return {{ text: "fake" }}; }}
"""

    first = client.put(
        f"/api/suppliers/{supplier['supplier_id']}/code",
        json={"source": source("base-text-v1")},
        headers={"If-Match": '"supplier-1"'},
    )
    assert first.status_code == 200, first.text
    models = client.get(f"/api/suppliers/{supplier['supplier_id']}/models")
    assert models.headers["etag"] == '"model-catalog-1"'
    assert len(models.json()) == 1
    model_id = models.json()[0]["supplier_model_id"]
    assert model_id == stable_id.replace("-", "")
    assert models.json()[0]["source"] == "built_in"

    second = client.put(
        f"/api/suppliers/{supplier['supplier_id']}/code",
        json={"source": source("base-text-v2")},
        headers={"If-Match": '"supplier-2"'},
    )
    assert second.status_code == 200, second.text
    revised = client.get(f"/api/models/{model_id}").json()
    assert revised["supplier_model_id"] == model_id
    assert revised["provider_model_name"] == "base-text-v2"
    assert revised["model_revision_id"] != models.json()[0]["model_revision_id"]
