from fastapi.testclient import TestClient

from ai_drama_web.app import create_app


def test_health_returns_ok(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
