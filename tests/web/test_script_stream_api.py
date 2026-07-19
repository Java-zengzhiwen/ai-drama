from fastapi.testclient import TestClient

from ai_drama_web.app import create_app
from ai_drama_web.routers.scripts import get_service


class FakeStreamingWorkflow:
    def start_script_generation(
        self, chapter_id, *, idempotency_key, target_duration_minutes
    ):
        assert chapter_id == "chapter-1"
        assert idempotency_key == "click-1"
        assert target_duration_minutes == 4
        return {
            "run_id": "run-1",
            "status": "prepared",
            "last_sequence": 0,
            "character_count": 0,
            "revision_id": "",
            "error_code": "",
        }


def test_start_returns_202_before_provider_completion(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AI_DRAMA_SCRIPT_STREAMING_ENABLED", "true")
    app = create_app(data_root=tmp_path / "runtime-data")
    app.dependency_overrides[get_service] = lambda: FakeStreamingWorkflow()

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.post(
            "/api/chapters/chapter-1/script/generations",
            headers={"Idempotency-Key": "click-1"},
            json={"target_duration_minutes": 4},
        )

    assert response.status_code == 202
    assert response.json() == {
        "run_id": "run-1",
        "status": "prepared",
        "last_sequence": 0,
        "character_count": 0,
        "revision_id": "",
        "error_code": "",
    }


def test_events_replay_only_after_cursor(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data")
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        def seed():
            store = app.state.product_store
            project = store.create_project(name="Replay")
            chapter = store.create_chapter(project.project_id, "第一章", 1)
            source = store.create_source_revision(chapter.chapter_id, "原文")
            store.create_script_generation_run(
                run_id="run-replay",
                project_id=project.project_id,
                chapter_id=chapter.chapter_id,
                source_revision_id=source.source_revision_id,
                runtime_run_id="runtime-replay",
                idempotency_key="replay-1",
            )
            store.append_script_generation_event(
                "run-replay",
                sequence=1,
                event_type="text_delta",
                payload={"text": "第一"},
            )
            store.append_script_generation_event(
                "run-replay",
                sequence=2,
                event_type="revision_completed",
                payload={"revision_id": "revision-1"},
            )
            store.transition_script_generation_run(
                "run-replay",
                expected_statuses=("prepared",),
                status="completed",
                revision_id="revision-1",
            )

        client.portal.call(seed)
        response = client.get(
            "/api/script-generation-runs/run-replay/events?after_sequence=1"
        )

    assert response.status_code == 200
    assert "id: 2" in response.text
    assert "id: 1" not in response.text
    assert "event: revision_completed" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-accel-buffering"] == "no"


def test_streaming_flag_off_keeps_legacy_endpoint(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data")
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        disabled = client.post(
            "/api/chapters/missing/script/generations",
            headers={"Idempotency-Key": "x"},
            json={},
        )

    assert disabled.status_code == 409
    assert disabled.json()["error_code"] == "SCRIPT_STREAMING_DISABLED"


def test_script_stream_management_rejects_non_loopback(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data")
    with TestClient(app, client=("203.0.113.10", 50000)) as client:
        response = client.get("/api/script-generation-runs/run-1")

    assert response.status_code == 403
    assert response.json()["error_code"] == "LOCAL_MANAGEMENT_ONLY"
