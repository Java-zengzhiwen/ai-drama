from fastapi.testclient import TestClient

from ai_drama_web.app import create_app
from ai_drama_web.config import Settings
from ai_drama_web.operations.backup_restore import semantic_store_summary
from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.suppliers.resolution import ModelBindingService


class ForbiddenGateway:
    def __init__(self):
        self.calls = 0

    def invoke(self, *_args, **_kwargs):
        self.calls += 1
        raise AssertionError("supplier gateway must remain disabled")


class LocalTextGateway:
    def __init__(self):
        self.calls = []

    def invoke(self, snapshot_hash, operation, payload):
        self.calls.append((snapshot_hash, operation, payload))
        assert operation == "textRequest"
        return {"output": "M6E_FLAG_ON_LOCAL_FAKE", "usage": {"input_tokens": 0, "output_tokens": 0}}


class CountingLegacyBackend(FakeGenerationBackend):
    def __init__(self):
        super().__init__()
        self.submit_count = 0
        self.poll_count = 0

    def create_video_job(self, request):
        self.submit_count += 1
        return super().create_video_job(request)

    def get_video_job_status(self, provider_job_id):
        self.poll_count += 1
        return super().get_video_job_status(provider_job_id)


def _project_fixture(client):
    project = client.post(
        "/api/projects",
        json={
            "name": "M6E rollback",
            "description": "offline drill",
            "series_canon": "",
            "characters_context": "",
            "production_brief": "",
        },
    ).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "Rollback", "position": 1},
    ).json()
    source = client.post(
        f"/api/chapters/{chapter['chapter_id']}/source-revisions",
        json={"content": "本地回滚演练，不访问真实供应商。"},
    )
    assert source.status_code == 200
    return project, chapter


def _create_flag_on_work(app, project_id, chapter_id):
    store = app.state.product_store
    suppliers = {item.slug: item for item in store.list_suppliers()}
    openai = suppliers["openai"]
    agnes = suppliers["agnes"]
    app.state.supplier_credential_store.replace(
        openai.supplier_id, "local-openai-fake", expected_revision=0
    )
    app.state.supplier_credential_store.replace(
        agnes.supplier_id, "local-agnes-fake", expected_revision=0
    )
    text_model = next(
        model
        for model in store.list_supplier_models(openai.supplier_id)
        if store.get_supplier_model_revision(model.current_model_revision_id).capability == "text"
    )
    video_model = next(
        model
        for model in store.list_supplier_models(agnes.supplier_id)
        if store.get_supplier_model_revision(model.current_model_revision_id).capability == "video"
    )
    ModelBindingService(store).replace(
        project_id,
        defaults={"text": text_model.supplier_model_id, "image": "", "video": video_model.supplier_model_id},
        overrides={},
        expected_revision=0,
    )
    gateway = LocalTextGateway()
    app.state.m6_generation_coordinator.gateway = gateway
    text = app.state.m6_generation_coordinator.execute_text(
        project_id=project_id,
        operation_key="script_adaptation",
        idempotency_key="m6e-flag-on-text",
        request={"prompt": "offline"},
    )
    queued, _ = app.state.m6_generation_coordinator.enqueue_video(
        project_id=project_id, chapter_id=chapter_id, shot_id="rollback-queued",
        prompt_revision_id="rollback-prompt", idempotency_key="rollback-queued",
        request={"prompt": "freeze queued", "asset_ids": [], "parameters": {}},
    )
    polling, _ = app.state.m6_generation_coordinator.enqueue_video(
        project_id=project_id, chapter_id=chapter_id, shot_id="rollback-polling",
        prompt_revision_id="rollback-prompt", idempotency_key="rollback-polling",
        request={"prompt": "freeze polling", "asset_ids": [], "parameters": {}},
    )
    store.transition_generation_job(polling.job_id, "submitting")
    store.record_submission_attempt(
        polling.job_id, state="accepted", provider_job_id="m6e-frozen-provider-id"
    )
    store.commit_accepted_submission(polling.job_id)
    store.transition_generation_job(polling.job_id, "polling", next_poll_at="2000-01-01T00:00:00Z")
    return {
        "text": text,
        "gateway_calls": len(gateway.calls),
        "queued_job_id": queued.job_id,
        "polling_job_id": polling.job_id,
    }


def test_off_on_off_restart_preserves_history_and_off_uses_no_supplier_gateway(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", raising=False)
    monkeypatch.setenv("AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS", "3600")
    assert Settings().m6_supplier_execution_enabled is False

    with TestClient(create_app(data_root=tmp_path)) as off_client:
        project, chapter = _project_fixture(off_client)
        forbidden = ForbiddenGateway()
        off_client.app.state.m6_generation_coordinator.gateway = forbidden
        generated = off_client.post(f"/api/chapters/{chapter['chapter_id']}/script/generate")
        assert generated.status_code == 200, generated.text
        assert forbidden.calls == 0
        before = off_client.portal.call(
            lambda: semantic_store_summary(off_client.app.state.product_store)
        )
        revision_id = generated.json()["revision_id"]

    monkeypatch.setenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", "true")
    with TestClient(create_app(data_root=tmp_path)) as on_client:
        assert on_client.app.state.settings.m6_supplier_execution_enabled is True
        during = on_client.portal.call(
            lambda: semantic_store_summary(on_client.app.state.product_store)
        )
        assert set(before["identities"]["projects"]) <= set(during["identities"]["projects"])
        revision_ids = on_client.portal.call(
            lambda: {
                row["revision_id"]
                for row in on_client.app.state.runtime_store.conn.execute(
                    "SELECT revision_id FROM revisions"
                ).fetchall()
            }
        )
        assert revision_id in revision_ids
        flag_on = on_client.portal.call(
            lambda: _create_flag_on_work(
                on_client.app, project["project_id"], chapter["chapter_id"]
            )
        )
        assert flag_on["text"]["output"] == "M6E_FLAG_ON_LOCAL_FAKE"
        assert flag_on["gateway_calls"] == 1
        during = on_client.portal.call(
            lambda: semantic_store_summary(on_client.app.state.product_store)
        )

    monkeypatch.setenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", "false")
    rollback_app = create_app(data_root=tmp_path)
    legacy_backend = CountingLegacyBackend()
    rollback_app.state.generation_backend = legacy_backend
    with TestClient(rollback_app) as rolled_back:
        assert rolled_back.app.state.settings.m6_supplier_execution_enabled is False
        after = rolled_back.portal.call(
            lambda: semantic_store_summary(rolled_back.app.state.product_store)
        )
        for kind in ("projects", "suppliers", "models", "jobs", "results", "snapshots", "objects"):
            assert set(during["identities"][kind]) <= set(after["identities"][kind])
        revisions = rolled_back.get(f"/api/chapters/{chapter['chapter_id']}/script/revisions")
        assert revisions.status_code == 200
        assert revision_id in {item["revision_id"] for item in revisions.json()}
        cycle = rolled_back.portal.call(rolled_back.app.state.generation_poller.run_cycle)
        assert (cycle.submitted, cycle.polled) == (0, 0)
        assert cycle.skipped >= 2
        assert (legacy_backend.submit_count, legacy_backend.poll_count) == (0, 0)
        frozen = rolled_back.portal.call(
            lambda: (
                rolled_back.app.state.product_store.get_generation_job(flag_on["queued_job_id"]),
                rolled_back.app.state.product_store.get_generation_job(flag_on["polling_job_id"]),
            )
        )
        assert (frozen[0].internal_status, frozen[1].internal_status) == ("queued", "polling")

    monkeypatch.delenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", raising=False)
    monkeypatch.delenv("AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS", raising=False)
    assert Settings().m6_supplier_execution_enabled is False
