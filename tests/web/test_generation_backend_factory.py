import pytest
from fastapi.testclient import TestClient

from ai_drama_web.app import create_app
from ai_drama_web.providers.agnes import AgnesImageBackend
from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.secrets import LocalSecretStore


def test_app_wires_agnes_backend_when_provider_is_agnes(tmp_path, monkeypatch):
    data_root = tmp_path / "runtime-data"
    LocalSecretStore(data_root).set_agnes_api_key("agnes-secret")
    monkeypatch.setenv("AI_DRAMA_RUNTIME_PROVIDER", "agnes")

    app = create_app(data_root=data_root, skills_root="skills")
    with TestClient(app):
        assert isinstance(app.state.generation_backend, AgnesImageBackend)


def test_app_does_not_silently_fallback_when_agnes_key_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_RUNTIME_PROVIDER", "agnes")

    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    with pytest.raises(RuntimeError, match="Agnes API key is not configured"):
        with TestClient(app):
            pass


def test_explicit_test_backend_injection_still_works(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_RUNTIME_PROVIDER", "agnes")
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    injected = FakeGenerationBackend()
    app.state.generation_backend = injected

    with TestClient(app):
        assert app.state.generation_backend is injected
