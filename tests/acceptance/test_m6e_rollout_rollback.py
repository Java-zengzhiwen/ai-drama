from fastapi.testclient import TestClient

from ai_drama_web.app import create_app
from ai_drama_web.config import Settings
from ai_drama_web.operations.backup_restore import semantic_store_summary


class ForbiddenGateway:
    def __init__(self):
        self.calls = 0

    def invoke(self, *_args, **_kwargs):
        self.calls += 1
        raise AssertionError("supplier gateway must remain disabled")


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


def test_off_on_off_restart_preserves_history_and_off_uses_no_supplier_gateway(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", raising=False)
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

    monkeypatch.setenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", "false")
    with TestClient(create_app(data_root=tmp_path)) as rolled_back:
        assert rolled_back.app.state.settings.m6_supplier_execution_enabled is False
        after = rolled_back.portal.call(
            lambda: semantic_store_summary(rolled_back.app.state.product_store)
        )
        for kind in ("projects", "suppliers", "models", "jobs", "results", "snapshots", "objects"):
            assert set(during["identities"][kind]) <= set(after["identities"][kind])
        revisions = rolled_back.get(f"/api/chapters/{chapter['chapter_id']}/script/revisions")
        assert revisions.status_code == 200
        assert revision_id in {item["revision_id"] for item in revisions.json()}

    monkeypatch.delenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", raising=False)
    assert Settings().m6_supplier_execution_enabled is False
