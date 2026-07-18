from fastapi.testclient import TestClient

from ai_drama_web.app import create_app


def _client(tmp_path, host, monkeypatch=None, trusted_proxies=""):
    if monkeypatch is not None:
        monkeypatch.setenv("AI_DRAMA_TRUSTED_MANAGEMENT_PROXY_CIDRS", trusted_proxies)
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    return TestClient(app, client=(host, 50000))


def test_management_api_accepts_only_direct_loopback_by_default(tmp_path):
    with _client(tmp_path / "ipv4", "127.0.0.1") as ipv4:
        assert ipv4.get("/api/suppliers").status_code == 200
    with _client(tmp_path / "ipv6", "::1") as ipv6:
        assert ipv6.get("/api/suppliers").status_code == 200
    with _client(tmp_path / "remote", "203.0.113.10") as remote:
        response = remote.get("/api/suppliers")
        assert response.status_code == 403
        assert response.json()["error_code"] == "LOCAL_MANAGEMENT_ONLY"


def test_spoofed_forwarded_headers_are_ignored_without_trusted_proxy(tmp_path):
    with _client(tmp_path, "203.0.113.10") as client:
        response = client.get(
            "/api/suppliers",
            headers={"X-Forwarded-For": "127.0.0.1", "Forwarded": "for=127.0.0.1"},
        )

    assert response.status_code == 403
    assert response.json()["error_code"] == "LOCAL_MANAGEMENT_ONLY"


def test_trusted_proxy_must_forward_a_loopback_origin(tmp_path, monkeypatch):
    with _client(tmp_path, "10.0.0.5", monkeypatch, "10.0.0.0/8") as client:
        local = client.get("/api/suppliers", headers={"X-Forwarded-For": "127.0.0.1"})
        remote = client.get("/api/suppliers", headers={"X-Forwarded-For": "198.51.100.8"})

    assert local.status_code == 200
    assert remote.status_code == 403


def test_public_health_is_not_blocked_but_management_is(tmp_path):
    with _client(tmp_path, "203.0.113.10") as client:
        assert client.get("/api/health").status_code == 200
        response = client.get("/api/suppliers")

    assert response.status_code == 403
    assert response.json()["error_code"] == "LOCAL_MANAGEMENT_ONLY"


def test_reverse_proxy_cannot_reach_any_management_surface(tmp_path):
    paths = (
        "/api/settings/agnes",
        "/api/suppliers/example/code",
        "/api/suppliers/example/secret",
        "/api/suppliers/example/models",
        "/api/models/example",
        "/api/models/example/tests",
        "/api/model-tests/status",
        "/api/model-tests/example",
        "/api/model-tests/example/content",
        "/api/projects/project-1/model-bindings",
        "/api/projects/project-1/model-resolution/source_segmentation",
    )
    with _client(tmp_path, "198.51.100.8") as client:
        responses = [client.get(path, headers={"X-Forwarded-For": "127.0.0.1"}) for path in paths]

    assert all(response.status_code == 403 for response in responses)
    assert all(response.json()["error_code"] == "LOCAL_MANAGEMENT_ONLY" for response in responses)
