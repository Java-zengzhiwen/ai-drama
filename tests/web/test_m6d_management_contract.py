from ai_drama_web.suppliers.snapshots import load_snapshot


TEXT_MODEL_ID = "66666666-6666-4666-8666-666666666666"
VIDEO_MODEL_ID = "77777777-7777-4777-8777-777777777777"


def _source(version, marker):
    return f"""
export const vendor = {{
  id: "m6d-runtime", version: "{version}", name: "M6D Runtime", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "m6d-runtime", inputs: [], inputValues: {{}},
  models: [
    {{ supplierModelId: "{TEXT_MODEL_ID}", providerModelName: "m6d-text", displayName: "M6D Text", capability: "text" }},
    {{ supplierModelId: "{VIDEO_MODEL_ID}", providerModelName: "m6d-video", displayName: "M6D Video", capability: "video" }}
  ]
}};
export async function textRequest() {{
  return {{ output: "{marker}", usage: {{ input_tokens: 0, output_tokens: 0 }} }};
}}
export async function videoSubmit() {{ return {{ video_id: "local-video" }}; }}
export async function videoPoll(payload) {{ return {{ video_id: payload.request.video_id, status: "completed" }}; }}
export async function videoFetch() {{ return {{ media_type: "video/mp4", bytes: "local" }}; }}
""".strip()


def test_saved_supplier_version_affects_only_future_execution_snapshots(client):
    created = client.post(
        "/api/suppliers",
        json={"slug": "m6d-runtime", "display_name": "M6D Runtime"},
        headers={"If-None-Match": "*", "Idempotency-Key": "m6d-runtime"},
    )
    assert created.status_code == 201
    supplier_id = created.json()["supplier_id"]
    first = client.put(
        f"/api/suppliers/{supplier_id}/code",
        json={"source": _source("1.0.0", "M6D_VERSION_1")},
        headers={"If-Match": '"supplier-1"'},
    )
    assert first.status_code == 200, first.text
    first_version_id = first.json()["supplier_version_id"]
    secret = client.put(
        f"/api/suppliers/{supplier_id}/secret",
        json={"credential": "local-fake-credential"},
        headers={"If-Match": '"credential-0"'},
    )
    assert secret.status_code == 200

    models = client.get(f"/api/suppliers/{supplier_id}/models").json()
    text_model_id = next(item["supplier_model_id"] for item in models if item["capability"] == "text")
    video_model_id = next(item["supplier_model_id"] for item in models if item["capability"] == "video")
    project = client.post(
        "/api/projects",
        json={
            "name": "M6D runtime project",
            "description": "local fake only",
            "series_canon": "",
            "characters_context": "",
            "production_brief": "",
        },
    ).json()
    binding = client.put(
        f"/api/projects/{project['project_id']}/model-bindings",
        json={
            "defaults": {"text": text_model_id, "image": "", "video": video_model_id},
            "operation_overrides": {},
        },
        headers={"If-Match": '"binding-set-0"'},
    )
    assert binding.status_code == 200, binding.text

    coordinator = client.app.state.m6_generation_coordinator
    first_text = client.portal.call(
        lambda: coordinator.execute_text(
            project_id=project["project_id"],
            operation_key="script_adaptation",
            idempotency_key="m6d-text-v1",
            request={"prompt": "offline"},
        )
    )
    old_job, old_created = client.portal.call(
        lambda: coordinator.enqueue_video(
            project_id=project["project_id"],
            chapter_id="chapter",
            shot_id="shot-old",
            prompt_revision_id="prompt-old",
            idempotency_key="m6d-video-old",
            request={"prompt": "offline old"},
        )
    )
    assert old_created is True
    old_snapshot = client.portal.call(
        lambda: load_snapshot(client.app.state.product_store, old_job.snapshot_hash)
    )

    second = client.put(
        f"/api/suppliers/{supplier_id}/code",
        json={"source": _source("2.0.0", "M6D_VERSION_2")},
        headers={"If-Match": '"supplier-2"'},
    )
    assert second.status_code == 200, second.text
    second_version_id = second.json()["supplier_version_id"]
    second_text = client.portal.call(
        lambda: coordinator.execute_text(
            project_id=project["project_id"],
            operation_key="script_adaptation",
            idempotency_key="m6d-text-v2",
            request={"prompt": "offline"},
        )
    )
    new_job, new_created = client.portal.call(
        lambda: coordinator.enqueue_video(
            project_id=project["project_id"],
            chapter_id="chapter",
            shot_id="shot-new",
            prompt_revision_id="prompt-new",
            idempotency_key="m6d-video-new",
            request={"prompt": "offline new"},
        )
    )
    assert new_created is True
    new_snapshot = client.portal.call(
        lambda: load_snapshot(client.app.state.product_store, new_job.snapshot_hash)
    )

    assert first_text["output"] == "M6D_VERSION_1"
    assert second_text["output"] == "M6D_VERSION_2"
    assert old_job.internal_status == "queued"
    assert old_snapshot.supplier_version_id == first_version_id
    assert new_snapshot.supplier_version_id == second_version_id
    assert old_snapshot.supplier_version_id != new_snapshot.supplier_version_id

    blocked = client.delete(
        f"/api/suppliers/{supplier_id}/secret",
        headers={"If-Match": '"credential-1"'},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == {
        "error_code": "CREDENTIAL_IN_USE",
        "active_job_count": 2,
    }
    forced = client.delete(
        f"/api/suppliers/{supplier_id}/secret?force=true",
        headers={"If-Match": '"credential-1"'},
    )
    assert forced.status_code == 200, forced.text
    assert client.portal.call(
        lambda: client.app.state.product_store.get_generation_job(old_job.job_id).internal_status
    ) == "cancelled"
    assert client.portal.call(
        lambda: client.app.state.product_store.get_generation_job(new_job.job_id).internal_status
    ) == "cancelled"
