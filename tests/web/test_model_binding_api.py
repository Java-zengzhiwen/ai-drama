def _create_model(client, supplier_id, capability, revision):
    response = client.post(
        f"/api/suppliers/{supplier_id}/models",
        json={
            "provider_model_name": f"{capability}-api",
            "display_name": f"{capability} API",
            "capability": capability,
            "definition": {},
        },
        headers={
            "If-None-Match": "*",
            "If-Match": f'"model-catalog-{revision}"',
            "Idempotency-Key": f"create-{capability}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["supplier_model_id"]


def test_binding_api_replaces_full_set_and_previews_resolution(client):
    project_id = client.post(
        "/api/projects",
        json={
            "name": "Binding API",
            "description": "",
            "series_canon": "",
            "characters_context": "",
            "production_brief": "",
        },
    ).json()["project_id"]
    supplier_id = client.get("/api/suppliers").json()[0]["supplier_id"]
    default = _create_model(client, supplier_id, "text", 0)
    override = client.post(
        f"/api/suppliers/{supplier_id}/models",
        json={
            "provider_model_name": "text-override-api",
            "display_name": "Override API",
            "capability": "text",
            "definition": {},
        },
        headers={
            "If-None-Match": "*",
            "If-Match": '"model-catalog-1"',
            "Idempotency-Key": "create-text-override",
        },
    ).json()["supplier_model_id"]

    empty = client.get(f"/api/projects/{project_id}/model-bindings")
    assert empty.headers["etag"] == '"binding-set-0"'
    updated = client.put(
        f"/api/projects/{project_id}/model-bindings",
        json={
            "defaults": {"text": default, "image": "", "video": ""},
            "operation_overrides": {"storyboard_design": override},
        },
        headers={"If-Match": '"binding-set-0"'},
    )
    assert updated.status_code == 200, updated.text
    assert updated.headers["etag"] == '"binding-set-1"'

    override_resolution = client.get(
        f"/api/projects/{project_id}/model-resolution/storyboard_design"
    )
    assert override_resolution.json()["supplier_model_id"] == override
    assert override_resolution.json()["binding_source"] == "operation_override"
    default_resolution = client.get(
        f"/api/projects/{project_id}/model-resolution/script_adaptation"
    )
    assert default_resolution.json()["supplier_model_id"] == default
    assert default_resolution.json()["binding_source"] == "capability_default"

    stale = client.put(
        f"/api/projects/{project_id}/model-bindings",
        json={"defaults": {"text": "", "image": "", "video": ""}, "operation_overrides": {}},
        headers={"If-Match": '"binding-set-0"'},
    )
    assert stale.status_code == 409


def test_resolution_api_returns_stable_fail_closed_error(client):
    project_id = client.post(
        "/api/projects",
        json={"name": "Missing", "description": "", "series_canon": "", "characters_context": "", "production_brief": ""},
    ).json()["project_id"]
    response = client.get(f"/api/projects/{project_id}/model-resolution/shot_video_generation")
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "MODEL_BINDING_MISSING"
