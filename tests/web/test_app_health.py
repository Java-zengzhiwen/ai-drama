from fastapi.testclient import TestClient

from ai_drama_web.app import create_app, main


def test_health_returns_ok(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_main_disables_access_log_to_protect_signed_asset_urls(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)

    main()

    assert captured["kwargs"]["access_log"] is False
