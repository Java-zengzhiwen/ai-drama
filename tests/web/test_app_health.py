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


def test_serves_built_spa_without_intercepting_api_routes(tmp_path):
    dist = tmp_path / "web" / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><div id="root"></div><script type="module" src="/assets/app.js"></script>',
        encoding="utf-8",
    )
    (assets / "app.js").write_text("console.log('ai-drama')", encoding="utf-8")

    app = create_app(
        data_root=tmp_path / "runtime-data",
        skills_root="skills",
        web_dist_root=dist,
    )
    with TestClient(app) as client:
        root = client.get("/")
        projects = client.get("/projects")
        asset = client.get("/assets/app.js")
        health = client.get("/api/health")

    assert root.status_code == 200
    assert "text/html" in root.headers["content-type"]
    assert projects.status_code == 200
    assert "text/html" in projects.headers["content-type"]
    assert asset.status_code == 200
    assert "javascript" in asset.headers["content-type"]
    assert health.status_code == 200
    assert health.headers["content-type"].startswith("application/json")
    assert health.json() == {"status": "ok"}


def test_missing_spa_build_keeps_api_available_and_reports_diagnostic(tmp_path):
    app = create_app(
        data_root=tmp_path / "runtime-data",
        skills_root="skills",
        web_dist_root=tmp_path / "missing-dist",
    )
    with TestClient(app) as client:
        root = client.get("/")
        health = client.get("/api/health")

    assert root.status_code == 503
    assert root.json() == {"detail": "web build missing; run npm --prefix web run build"}
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
