import pytest
from fastapi.testclient import TestClient

from ai_drama_web.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    with TestClient(app, client=("127.0.0.1", 50000)) as test_client:
        yield test_client
