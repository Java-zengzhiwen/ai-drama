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


def test_delete_archives_snapshotted_overlay_and_hides_it_from_catalog(client):
    supplier = _supplier(client)
    created = client.post(
        f"/api/suppliers/{supplier['supplier_id']}/models",
        json={
            "provider_model_name": "archive-api-text",
            "display_name": "Archive API Text",
            "capability": "text",
            "definition": {},
        },
        headers={
            "If-None-Match": "*",
            "If-Match": '"model-catalog-0"',
            "Idempotency-Key": "archive-api-text",
        },
    )
    model_id = created.json()["supplier_model_id"]
    def persist_project_snapshot():
        store = client.app.state.product_store
        model = store.get_supplier_model(model_id)
        object_id = store.runtime.write_text_object('{"schema":"archive-api-test"}')
        store.conn.execute(
            """
            INSERT INTO execution_snapshots
            (snapshot_hash, snapshot_object_id, supplier_id, supplier_model_id,
             model_revision_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "archive-api-snapshot",
                object_id,
                supplier["supplier_id"],
                model_id,
                model.current_model_revision_id,
                "2026-07-15T00:00:00Z",
            ),
        )
        store.conn.commit()

    client.portal.call(persist_project_snapshot)

    deleted = client.delete(
        f"/api/models/{model_id}",
        headers={"If-Match": f'"model-{model_id}-1", "model-catalog-1"'},
    )
    listing = client.get(f"/api/suppliers/{supplier['supplier_id']}/models")
    historical = client.get(f"/api/models/{model_id}")

    assert deleted.status_code == 204, deleted.text
    assert listing.json() == []
    assert historical.status_code == 200
    assert historical.json()["archived_at"]
    assert historical.json()["archive_reason"] == "historical_snapshot"
    assert historical.json()["enabled"] == 0


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


def test_supplier_code_manifest_disables_removed_builtin_without_deleting_history(client):
    supplier = _supplier(client)
    text_id = "11111111-1111-4111-8111-111111111111"
    image_id = "22222222-2222-4222-8222-222222222222"

    def source(include_image):
        image = (
            f', {{ supplierModelId: "{image_id}", providerModelName: "gpt-image-2", '
                'displayName: "GPT Image 2", capability: "image" }'
            if include_image
            else ""
        )
        return f"""
export const vendor = {{
  id: "archive-manifest", version: "1", name: "Archive Manifest", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "archive-manifest-bucket", inputs: [], inputValues: {{}},
  models: [{{ supplierModelId: "{text_id}", providerModelName: "gpt-5.6", displayName: "GPT-5.6", capability: "text" }}{image}]
}};
export async function textRequest() {{ return {{ output: "fake", usage: {{}} }}; }}
export async function imageRequest() {{ return {{ media_type: "image/png" }}; }}
"""

    first = client.put(
        f"/api/suppliers/{supplier['supplier_id']}/code",
        json={"source": source(True)},
        headers={"If-Match": '"supplier-1"'},
    )
    assert first.status_code == 200, first.text
    before = client.get(f"/api/suppliers/{supplier['supplier_id']}/models").json()
    image_before = next(model for model in before if model["capability"] == "image")

    second = client.put(
        f"/api/suppliers/{supplier['supplier_id']}/code",
        json={"source": source(False)},
        headers={"If-Match": '"supplier-2"'},
    )
    assert second.status_code == 200, second.text
    after = client.get(f"/api/suppliers/{supplier['supplier_id']}/models").json()
    image_after = next(model for model in after if model["supplier_model_id"] == image_before["supplier_model_id"])

    assert image_after["enabled"] == 0
    assert image_after["model_revision_id"] == image_before["model_revision_id"]
    detail = client.get(f"/api/models/{image_before['supplier_model_id']}")
    assert detail.status_code == 200
    assert detail.json()["provider_model_name"] == "gpt-image-2"
