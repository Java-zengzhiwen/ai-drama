import sqlite3
import time
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore, now_iso
from ai_drama_web.app import create_app
from ai_drama_web.services.asset_delivery import AssetDeliveryService


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_PUBLIC_BASE_URL", "https://assets.example.test")
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    with TestClient(app) as test_client:
        yield test_client


def _chapter(client):
    project = client.post("/api/projects", json={"name": "Project"}).json()
    return client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "Chapter 1", "position": 1},
    ).json()


def _image_asset(client):
    chapter = _chapter(client)
    response = client.post(
        f"/api/chapters/{chapter['chapter_id']}/assets",
        files={"file": ("ref.png", PNG_BYTES, "image/png")},
        data={"asset_type": "character_reference", "name": "Reference", "metadata": "{}"},
    )
    assert response.status_code == 200
    return response.json()


def _signed_url(client, asset_id, *, ttl_seconds=60):
    service = AssetDeliveryService(
        client.app.state.product_store,
        client.app.state.runtime_store,
        client.app.state.secret_store,
        public_base_url=client.app.state.settings.public_base_url,
    )
    return service.signed_asset_url(asset_id, ttl_seconds=ttl_seconds)


def _path_and_query(url):
    parsed = urlparse(url)
    return parsed.path + "?" + parsed.query


def test_signed_public_asset_url_serves_image_asset(client):
    asset = _image_asset(client)
    url = _signed_url(client, asset["asset_id"])

    response = client.get(_path_and_query(url))

    assert response.status_code == 200
    assert response.content == PNG_BYTES
    assert response.headers["content-type"] == "image/png"
    assert url.startswith("https://assets.example.test/public/assets/")


def test_signed_public_asset_url_rejects_altered_asset_or_signature(client):
    asset = _image_asset(client)
    url = _signed_url(client, asset["asset_id"])
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    expires = query["expires"][0]
    signature = query["signature"][0]

    altered_asset_response = client.get(
        f"/public/assets/not-{asset['asset_id']}?expires={expires}&signature={signature}"
    )
    altered_expiry_response = client.get(
        f"/public/assets/{asset['asset_id']}?expires={int(expires) + 1}&signature={signature}"
    )

    assert altered_asset_response.status_code == 403
    assert altered_expiry_response.status_code == 403


def test_signed_public_asset_url_rejects_expired_url(client):
    asset = _image_asset(client)
    url = _signed_url(client, asset["asset_id"], ttl_seconds=-1)

    response = client.get(_path_and_query(url))

    assert response.status_code == 403


def test_signed_public_asset_url_rejects_non_image_assets(client):
    runtime = client.app.state.runtime_store
    chapter = _chapter(client)
    object_id = runtime.write_bytes_object(b"not image")
    metadata_object_id = runtime.write_text_object("{}")
    now = now_iso()
    asset_id = "video-asset"
    with sqlite3.connect(client.app.state.settings.data_root / "runtime.db") as conn:
        conn.execute(
            """
            INSERT INTO assets
            (asset_id, project_id, chapter_id, asset_type, name, object_id,
             media_type, width, height, status, source_type, source_job_id,
             metadata_object_id, created_at, updated_at)
            VALUES (?, ?, ?, 'shot_keyframe', 'Video Asset', ?, 'video/mp4',
                    0, 0, 'usable', 'upload', '', ?, ?, ?)
            """,
            (asset_id, chapter["project_id"], chapter["chapter_id"], object_id, metadata_object_id, now, now),
        )
    url = _signed_url(client, asset_id)

    response = client.get(_path_and_query(url))

    assert response.status_code == 415
