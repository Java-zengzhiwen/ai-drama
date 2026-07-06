import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from ai_drama_web.app import create_app
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderJob, ProviderResult


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _create_project_and_chapter(client):
    project = client.post("/api/projects", json={"name": "生死"}).json()
    chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第一章", "position": 1},
    ).json()
    return project, chapter


def _upload_png(client, chapter_id):
    response = client.post(
        f"/api/chapters/{chapter_id}/assets",
        data={"asset_type": "character_reference", "name": "沈清荷参考图"},
        files={"file": ("reference.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_generate_image_creates_draft_agnes_asset_and_persists_png_content(client):
    _, chapter = _create_project_and_chapter(client)

    response = client.post(
        f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
        json={
            "asset_type": "character_reference",
            "name": "沈清荷生成参考图",
            "prompt": "locked portrait of Shen Qinghe",
            "size": "512x512",
            "metadata": {"profile_id": "CHAR_SHEN_QINGHE"},
        },
    )

    assert response.status_code == 200, response.text
    asset = response.json()
    assert asset["chapter_id"] == chapter["chapter_id"]
    assert asset["asset_type"] == "character_reference"
    assert asset["name"] == "沈清荷生成参考图"
    assert asset["status"] == "draft"
    assert asset["source_type"] == "agnes"
    assert asset["source_job_id"].startswith("fake-image-")
    assert asset["media_type"] == "image/png"
    assert asset["metadata"]["profile_id"] == "CHAR_SHEN_QINGHE"
    assert asset["metadata"]["generation"]["prompt"] == "locked portrait of Shen Qinghe"
    assert asset["metadata"]["generation"]["size"] == "512x512"
    assert asset["metadata"]["provider_job"]["status"] == "succeeded"
    assert asset["metadata"]["provider_result"]["url"] == f"fake://images/{asset['source_job_id']}.png"

    content = client.get(f"/api/assets/{asset['asset_id']}/content")
    assert content.status_code == 200, content.text
    assert content.content == PNG_BYTES
    assert content.headers["content-type"] == "image/png"

    listed = client.get(f"/api/chapters/{chapter['chapter_id']}/assets").json()
    assert [item["asset_id"] for item in listed] == [asset["asset_id"]]

    usable = client.post(f"/api/assets/{asset['asset_id']}/mark-usable")
    assert usable.status_code == 200, usable.text
    assert usable.json()["status"] == "usable"


def test_generate_image_converts_reference_assets_to_data_uris(client):
    _, chapter = _create_project_and_chapter(client)
    reference = _upload_png(client, chapter["chapter_id"])

    response = client.post(
        f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
        json={
            "asset_type": "character_outfit",
            "name": "沈清荷服装版本",
            "prompt": "new outfit based on approved portrait",
            "size": "1024x1024",
            "input_asset_ids": [reference["asset_id"]],
        },
    )

    assert response.status_code == 200, response.text
    asset = response.json()
    input_images = asset["metadata"]["provider_job"]["raw"]["request"]["input_images"]
    assert len(input_images) == 1
    assert input_images[0].startswith("data:image/png;base64,")
    assert input_images[0] != reference["object_id"]


def test_generate_image_downloads_url_only_provider_result(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    app.state.generation_backend = UrlOnlyGenerationBackend()

    with respx.mock(assert_all_called=True) as router:
        router.get("https://cdn.example.test/generated.png").mock(
            return_value=httpx.Response(200, content=PNG_BYTES, headers={"content-type": "image/png"})
        )
        with TestClient(app) as client:
            _, chapter = _create_project_and_chapter(client)
            response = client.post(
                f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
                json={
                    "asset_type": "scene_reference",
                    "name": "沈府正厅生成图",
                    "prompt": "ancestral hall",
                    "size": "1024x1024",
                },
            )

            assert response.status_code == 200, response.text
            asset = response.json()
            content = client.get(f"/api/assets/{asset['asset_id']}/content")

    assert asset["source_type"] == "agnes"
    assert asset["status"] == "draft"
    assert asset["source_job_id"] == "url-only-job"
    assert asset["metadata"]["provider_result"]["url"] == "https://cdn.example.test/generated.png"
    assert content.content == PNG_BYTES


def test_generate_image_rejects_missing_chapter_and_missing_reference_asset(client):
    missing_chapter = client.post(
        "/api/chapters/missing-chapter/assets/generate-image",
        json={
            "asset_type": "character_reference",
            "name": "缺失章节",
            "prompt": "portrait",
            "size": "512x512",
        },
    )
    assert missing_chapter.status_code == 404

    _, chapter = _create_project_and_chapter(client)
    missing_asset = client.post(
        f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
        json={
            "asset_type": "character_reference",
            "name": "缺失参考",
            "prompt": "portrait",
            "size": "512x512",
            "input_asset_ids": ["missing-asset"],
        },
    )
    assert missing_asset.status_code == 404


def test_generate_image_rejects_reference_asset_from_another_chapter(client):
    project, source_chapter = _create_project_and_chapter(client)
    other_chapter = client.post(
        f"/api/projects/{project['project_id']}/chapters",
        json={"title": "第二章", "position": 2},
    ).json()
    other_chapter_asset = _upload_png(client, other_chapter["chapter_id"])

    response = client.post(
        f"/api/chapters/{source_chapter['chapter_id']}/assets/generate-image",
        json={
            "asset_type": "character_outfit",
            "name": "跨章引用",
            "prompt": "outfit",
            "size": "512x512",
            "input_asset_ids": [other_chapter_asset["asset_id"]],
        },
    )

    assert response.status_code == 404


def test_generate_image_maps_provider_errors_without_leaking_raw_secret(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    app.state.generation_backend = FailingGenerationBackend()

    with TestClient(app) as client:
        _, chapter = _create_project_and_chapter(client)
        response = client.post(
            f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
            json={
                "asset_type": "character_reference",
                "name": "生成失败",
                "prompt": "portrait",
                "size": "512x512",
            },
        )

    assert response.status_code == 502
    assert response.json() == {
        "error_code": "provider_busy",
        "error_message": "image provider failed",
    }
    assert "provider-secret" not in response.text


def test_generate_image_provider_error_message_does_not_leak_exception_text(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    app.state.generation_backend = FailingGenerationBackend(message="provider-secret leaked in message")

    with TestClient(app) as client:
        _, chapter = _create_project_and_chapter(client)
        response = client.post(
            f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
            json={
                "asset_type": "character_reference",
                "name": "生成失败",
                "prompt": "portrait",
                "size": "512x512",
            },
        )

    assert response.status_code == 502
    assert response.json() == {
        "error_code": "provider_busy",
        "error_message": "image provider failed",
    }
    assert "provider-secret" not in response.text


def test_generate_image_does_not_hide_internal_runtime_errors(tmp_path):
    app = create_app(data_root=tmp_path / "runtime-data", skills_root="skills")
    app.state.generation_backend = BuggyGenerationBackend()

    with TestClient(app) as client:
        _, chapter = _create_project_and_chapter(client)
        with pytest.raises(RuntimeError, match="programming bug"):
            client.post(
                f"/api/chapters/{chapter['chapter_id']}/assets/generate-image",
                json={
                    "asset_type": "character_reference",
                    "name": "内部错误",
                    "prompt": "portrait",
                    "size": "512x512",
                },
            )


class FailingGenerationBackend:
    def __init__(self, *, message="image provider failed"):
        self.message = message

    def create_image_job(self, request):
        raise ProviderError(
            "provider_busy",
            self.message,
            provider="fake",
            raw={"access_token": "provider-secret", "request": json.loads(json.dumps(request.__dict__))},
        )

    def create_video_job(self, request):
        raise NotImplementedError

    def get_job_status(self, provider_job_id):
        raise KeyError(provider_job_id)

    def fetch_result(self, provider_job_id):
        raise KeyError(provider_job_id)


class UrlOnlyGenerationBackend:
    def create_image_job(self, request):
        return ProviderJob(
            provider_job_id="url-only-job",
            status="succeeded",
            raw={"provider": "url-only", "request": request.__dict__},
        )

    def create_video_job(self, request):
        raise NotImplementedError

    def get_job_status(self, provider_job_id):
        return ProviderJob(provider_job_id=provider_job_id, status="succeeded", raw={})

    def fetch_result(self, provider_job_id):
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="image/png",
            url="https://cdn.example.test/generated.png",
            content=None,
            raw={"provider": "url-only"},
        )


class BuggyGenerationBackend:
    def create_image_job(self, request):
        raise RuntimeError("programming bug")

    def create_video_job(self, request):
        raise NotImplementedError

    def get_job_status(self, provider_job_id):
        raise KeyError(provider_job_id)

    def fetch_result(self, provider_job_id):
        raise KeyError(provider_job_id)
