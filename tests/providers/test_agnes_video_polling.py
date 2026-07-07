import json

import httpx
import pytest
import respx

from ai_drama_web.providers.agnes import AgnesImageBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderResult


AGNES_STATUS_ENDPOINT = "https://apihub.agnes-ai.com/agnesapi"
API_KEY = "agnes-video-secret"


@pytest.mark.parametrize(
    ("provider_status", "expected_status"),
    [
        ("queued", "submitted"),
        ("in_progress", "polling"),
        ("processing", "polling"),
        ("completed", "completed"),
        ("failed", "failed"),
    ],
)
def test_get_video_job_status_queries_by_video_id_and_normalizes_status(provider_status, expected_status):
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        route = router.get(AGNES_STATUS_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "task_123",
                    "video_id": "video_456",
                    "model": "agnes-video-v2.0",
                    "object": "video",
                    "status": provider_status,
                    "progress": 50,
                },
            )
        )

        job = backend.get_job_status("video_456")

    assert job.provider_job_id == "video_456"
    assert job.status == expected_status
    assert route.calls.last.request.url.params["video_id"] == "video_456"
    assert route.calls.last.request.url.params["model_name"] == "agnes-video-v2.0"
    assert route.calls.last.request.headers["authorization"] == f"Bearer {API_KEY}"
    assert API_KEY not in json.dumps(job.raw)


def test_fetch_video_result_returns_completed_url_without_downloading_bytes():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.get(AGNES_STATUS_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "task_123",
                    "video_id": "video_456",
                    "model": "agnes-video-v2.0",
                    "object": "video",
                    "status": "completed",
                    "url": "https://platform-outputs.agnes-ai.space/videos/video_456.mp4",
                    "error": None,
                },
            )
        )

        result = backend.fetch_result("video_456")

    assert isinstance(result, ProviderResult)
    assert result.provider_job_id == "video_456"
    assert result.media_type == "video/mp4"
    assert result.url == "https://platform-outputs.agnes-ai.space/videos/video_456.mp4"
    assert result.content is None
    assert result.raw["provider_response"]["status"] == "completed"


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (429, "rate_limited"),
        (404, "unknown_provider_error"),
        (500, "provider_busy"),
    ],
)
def test_video_poll_http_errors_map_to_stable_error_codes(status_code, expected_code):
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.get(AGNES_STATUS_ENDPOINT).mock(
            return_value=httpx.Response(status_code, json={"error": {"message": "provider failed"}})
        )

        with pytest.raises(ProviderError) as exc_info:
            backend.get_job_status("video_456")

    assert exc_info.value.code == expected_code
    assert API_KEY not in json.dumps(exc_info.value.raw)


def test_video_poll_timeout_maps_to_timeout():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.get(AGNES_STATUS_ENDPOINT).mock(side_effect=httpx.TimeoutException("read timed out"))

        with pytest.raises(ProviderError) as exc_info:
            backend.get_job_status("video_456")

    assert exc_info.value.code == "timeout"


def test_video_poll_malformed_response_maps_to_unknown_provider_error():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.get(AGNES_STATUS_ENDPOINT).mock(return_value=httpx.Response(200, content="not json"))

        with pytest.raises(ProviderError) as exc_info:
            backend.get_job_status("video_456")

    assert exc_info.value.code == "unknown_provider_error"


def test_completed_video_without_url_maps_to_result_expired():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.get(AGNES_STATUS_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"video_id": "video_456", "status": "completed", "url": ""},
            )
        )

        with pytest.raises(ProviderError) as exc_info:
            backend.fetch_result("video_456")

    assert exc_info.value.code == "result_expired"
