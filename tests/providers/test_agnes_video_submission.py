import json

import httpx
import pytest
import respx

from ai_drama_web.providers.agnes import AgnesImageBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import ProviderJob, VideoGenerationRequest


AGNES_VIDEO_ENDPOINT = "https://apihub.agnes-ai.com/v1/videos"
API_KEY = "agnes-video-secret"


def test_create_video_job_posts_official_payload_and_uses_video_id_as_provider_job_id():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        route = router.post(AGNES_VIDEO_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "task_123",
                    "task_id": "task_123",
                    "video_id": "video_456",
                    "object": "video",
                    "model": "agnes-video-v2.0",
                    "status": "queued",
                    "seconds": "5.0",
                },
            )
        )

        job = backend.create_video_job(
            VideoGenerationRequest(
                prompt="Camera pushes in while Shen Qinghe turns toward the lantern.",
                negative_prompt="warped face, broken hands",
                duration_seconds=5,
                input_images=["https://assets.example.test/public/assets/asset-1?expires=1&signature=s"],
                parameters={
                    "num_frames": 121,
                    "frame_rate": 24,
                },
            )
        )

    assert isinstance(job, ProviderJob)
    assert job.provider_job_id == "video_456"
    assert job.status == "submitted"
    request = route.calls.last.request
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    payload = json.loads(request.content)
    assert payload == {
        "model": "agnes-video-v2.0",
        "prompt": "Camera pushes in while Shen Qinghe turns toward the lantern.",
        "negative_prompt": "warped face, broken hands",
        "image": "https://assets.example.test/public/assets/asset-1?expires=1&signature=s",
        "num_frames": 121,
        "frame_rate": 24,
    }
    raw = json.dumps(job.raw)
    assert "task_123" in raw
    assert "video_456" in raw
    assert API_KEY not in raw


def test_create_video_job_preserves_multi_image_keyframe_parameters():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        route = router.post(AGNES_VIDEO_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"task_id": "task_keyframes", "video_id": "video_keyframes", "status": "queued"},
            )
        )

        backend.create_video_job(
            VideoGenerationRequest(
                prompt="Generate a smooth transition between keyframes.",
                duration_seconds=5,
                input_images=[
                    "https://assets.example.test/first.png",
                    "https://assets.example.test/last.png",
                ],
                parameters={
                    "mode": "keyframes",
                    "num_frames": 121,
                    "frame_rate": 24,
                    "seed": 123,
                },
            )
        )

    payload = json.loads(route.calls.last.request.content)
    assert payload["extra_body"] == {
        "image": [
            "https://assets.example.test/first.png",
            "https://assets.example.test/last.png",
        ],
        "mode": "keyframes",
    }
    assert payload["num_frames"] == 121
    assert payload["frame_rate"] == 24
    assert payload["seed"] == 123
    assert "image" not in payload
    assert "mode" not in payload


def test_create_video_job_requires_video_id_in_provider_response():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_VIDEO_ENDPOINT).mock(
            return_value=httpx.Response(200, json={"task_id": "task_without_video_id", "status": "queued"})
        )

        with pytest.raises(ProviderError) as exc_info:
            backend.create_video_job(VideoGenerationRequest(prompt="clip", duration_seconds=5))

    assert exc_info.value.code == "unknown_provider_error"
    assert "video_id" in str(exc_info.value)
    assert API_KEY not in json.dumps(exc_info.value.raw)
