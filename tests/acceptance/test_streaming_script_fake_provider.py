from pathlib import Path

from fastapi.testclient import TestClient

from ai_drama_runtime.runtime import _mock_script
from ai_drama_web.app import create_app
from ai_drama_web.services.script_generation_stream import ScriptGenerationRunner
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.model_catalog import ModelCatalogService


FAKE_STREAM_SOURCE = """
export const vendor = {
  id: "streaming-acceptance-fake",
  version: "1.0.0",
  name: "Streaming Acceptance Fake",
  author: "Acceptance",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v3",
  rateLimitBucketKey: "streaming-acceptance-local",
  inputs: [],
  inputValues: {},
  models: []
};
export async function textRequest() { return { output: "unused", usage: {} }; }
export async function textStream() { return {}; }
""".strip()


class FakeStreamingGateway:
    def __init__(self):
        self.submit_count = 0

    def invoke_stream(self, _snapshot_hash, operation, request):
        self.submit_count += 1
        assert operation == "textStream"
        assert request["messages"]
        script = _mock_script("fake-stream-acceptance")
        split_at = len(script) // 2
        yield {"type": "started", "sequence": 0}
        yield {"type": "text_delta", "sequence": 1, "text": script[:split_at]}
        yield {"type": "text_delta", "sequence": 2, "text": script[split_at:]}
        yield {
            "type": "usage",
            "sequence": 3,
            "usage": {"total_tokens": 3},
        }
        yield {
            "type": "completed",
            "sequence": 4,
            "evidence": {"schema": "fake-stream-v1"},
        }


def _install_fake_supplier(app):
    store = app.state.product_store
    supplier = store.create_supplier(
        slug="streaming-acceptance-fake",
        display_name="Streaming Acceptance Fake",
    )
    artifact = compile_supplier(FAKE_STREAM_SOURCE, runtime_store=store.runtime)
    store.replace_supplier_version(
        supplier.supplier_id,
        source_object_id=artifact.source_object_id,
        source_hash=artifact.source_hash,
        compiled_artifact_object_id=artifact.compiled_artifact_object_id,
        compiled_artifact_hash=artifact.compiled_artifact_hash,
        manifest_hash=artifact.manifest_hash,
        manifest=artifact.vendor,
        adapter_contract_version=artifact.adapter_contract_version,
        worker_protocol_version="2",
        worker_runtime_version=artifact.worker_runtime_version,
        compiler_name=artifact.compiler_name,
        compiler_version=artifact.compiler_version,
        compiler_options_hash=artifact.compiler_options_hash,
        helper_api_version=artifact.helper_api_version,
        rate_limit_bucket_key=artifact.vendor["rateLimitBucketKey"],
        expected_revision=supplier.revision,
    )
    app.state.supplier_credential_store.replace(
        supplier.supplier_id,
        "offline-fake-credential",
        expected_revision=0,
    )
    model, _ = ModelCatalogService(store).create_overlay(
        supplier.supplier_id,
        provider_model_name="fake-stream-text",
        display_name="Fake Stream Text",
        capability="text",
        definition={"constraints": {"offline": True}},
        expected_catalog_revision=0,
        idempotency_key="fake-stream-text-model",
    )
    return model.supplier_model_id


def test_fake_stream_api_creates_one_validated_revision_and_one_submit(
    tmp_path, monkeypatch
):
    repo_root = Path(__file__).resolve().parents[2]
    data_root = tmp_path / "runtime-data"
    monkeypatch.setenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AI_DRAMA_SCRIPT_STREAMING_ENABLED", "false")
    app = create_app(data_root=data_root, skills_root=repo_root / "skills")

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        model_id = client.portal.call(_install_fake_supplier, app)
        project = client.post(
            "/api/projects",
            json={
                "name": "Streaming fake acceptance",
                "series_canon": "古装商贾世界",
                "characters_context": "沈清荷",
                "production_brief": "紧凑短剧",
            },
        ).json()
        chapter = client.post(
            f"/api/projects/{project['project_id']}/chapters",
            json={"title": "第一章", "position": 1},
        ).json()
        bindings = client.get(
            f"/api/projects/{project['project_id']}/model-bindings"
        )
        saved = client.put(
            f"/api/projects/{project['project_id']}/model-bindings",
            headers={"If-Match": bindings.headers["etag"]},
            json={
                "defaults": {"text": "", "image": "", "video": ""},
                "operation_overrides": {"script_adaptation": model_id},
            },
        )
        source = client.post(
            f"/api/chapters/{chapter['chapter_id']}/source-revisions",
            json={"content": "沈清荷醒来后重新翻开账册，决定改写自己的命运。"},
        )
        app.state.settings.script_streaming_enabled = True
        started = client.post(
            f"/api/chapters/{chapter['chapter_id']}/script/generations",
            headers={"Idempotency-Key": "fake-click-1"},
            json={"target_duration_minutes": 4},
        )
        durable_session = client.portal.call(
            app.state.product_store.get_script_generation_run,
            started.json()["run_id"],
        )

        gateway = FakeStreamingGateway()
        runner = ScriptGenerationRunner(
            app.state.product_store,
            app.state.runtime_store,
            repo_root=repo_root,
            gateway=gateway,
        )
        cycle = client.portal.call(runner.run_cycle)
        final = client.get(
            f"/api/script-generation-runs/{started.json()['run_id']}"
        )
        event_stream = client.get(
            f"/api/script-generation-runs/{started.json()['run_id']}/events"
        )
        revisions = client.get(
            f"/api/chapters/{chapter['chapter_id']}/script/revisions"
        ).json()
        replay = client.post(
            f"/api/chapters/{chapter['chapter_id']}/script/generations",
            headers={"Idempotency-Key": "fake-click-1"},
            json={"target_duration_minutes": 4},
        )
        idle_cycle = client.portal.call(runner.run_cycle)

    assert saved.status_code == 200
    assert source.status_code == 200
    assert started.status_code == 202
    assert started.json()["status"] == "prepared"
    assert durable_session["supplier_text_run_id"]
    assert durable_session["snapshot_hash"]
    assert cycle.started == 1 and cycle.completed == 1
    assert final.json()["status"] == "completed"
    assert final.json()["revision_id"]
    assert replay.status_code == 202
    assert replay.json()["revision_id"] == final.json()["revision_id"]
    assert gateway.submit_count == 1
    assert idle_cycle.started == 0
    assert len(revisions) == 1
    assert revisions[0]["content"].startswith("# Mock Drama Script")
    required = [row for row in revisions[0]["validation_results"] if row["required"]]
    assert required and all(row["status"] == "PASS" for row in required)
    assert "event: text_delta" in event_stream.text
    assert "event: revision_completed" in event_stream.text


def test_fake_stream_duplicate_frame_fails_without_resubmission(tmp_path):
    from tests.web.test_script_generation_runner import _runner_fixture

    repo_root, runtime, store, _prepared = _runner_fixture(tmp_path)

    class DuplicateFrameGateway:
        def __init__(self):
            self.submit_count = 0

        def invoke_stream(self, _snapshot_hash, _operation, _request):
            self.submit_count += 1
            yield {"type": "started", "sequence": 0}
            yield {"type": "text_delta", "sequence": 1, "text": "第一段"}
            yield {"type": "text_delta", "sequence": 1, "text": "冲突段"}

    gateway = DuplicateFrameGateway()
    runner = ScriptGenerationRunner(
        store, runtime, repo_root=repo_root, gateway=gateway
    )

    result = runner.run_cycle()

    assert result.failed == 1
    assert store.get_script_generation_run("session-1")["status"] == "failed"
    assert gateway.submit_count == 1
    assert runner.run_cycle().started == 0
    assert gateway.submit_count == 1
