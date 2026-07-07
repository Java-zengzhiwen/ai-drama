import json

import httpx
import pytest
import respx

from ai_drama_web.providers.agnes import AgnesImageBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import (
    ImageGenerationRequest,
    ProviderJob,
    ProviderResult,
)


AGNES_ENDPOINT = "https://apihub.agnes-ai.com/v1/images/generations"
API_KEY = "agnes-test-secret"


def test_create_text_image_job_posts_documented_payload_without_secret_leak():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        route = router.post(AGNES_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"url": "https://cdn.example.test/generated.png"}]},
            )
        )

        job = backend.create_image_job(
            ImageGenerationRequest(
                prompt="Shen Qinghe in the ancestral hall",
                size="1024x1024",
            )
        )

    assert isinstance(job, ProviderJob)
    assert job.status == "succeeded"
    assert job.provider_job_id.startswith("agnes-image-")
    request = route.calls.last.request
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert request.headers["content-type"] == "application/json"
    payload = json.loads(request.content)
    assert payload == {
        "model": "agnes-image-2.1-flash",
        "prompt": "Shen Qinghe in the ancestral hall",
        "size": "1024x1024",
        "extra_body": {"response_format": "url"},
    }
    assert "image" not in payload
    assert "response_format" not in payload
    assert API_KEY not in json.dumps(job.raw)


def test_create_image_job_puts_input_images_in_extra_body_only():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        route = router.post(AGNES_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"url": "https://cdn.example.test/from-reference.png"}]},
            )
        )

        backend.create_image_job(
            ImageGenerationRequest(
                prompt="portrait from locked references",
                size="1024x1536",
                input_images=["asset://shen-qinghe", "asset://hall-reference"],
            )
        )

    payload = json.loads(route.calls.last.request.content)
    assert payload["extra_body"]["image"] == [
        "asset://shen-qinghe",
        "asset://hall-reference",
    ]
    assert "image" not in payload
    assert payload["extra_body"]["response_format"] == "url"
    assert "response_format" not in payload


def test_fetch_result_returns_url_png_metadata_and_sanitized_raw_copy():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"url": "https://cdn.example.test/final.png"}]},
            )
        )

        job = backend.create_image_job(ImageGenerationRequest(prompt="courtyard", size="512x512"))

    status = backend.get_job_status(job.provider_job_id)
    result = backend.fetch_result(job.provider_job_id)
    result.raw["provider_response"]["data"][0]["url"] = "mutated"

    assert status == job
    assert isinstance(result, ProviderResult)
    assert result.provider_job_id == job.provider_job_id
    assert result.media_type == "image/png"
    assert result.url == "https://cdn.example.test/final.png"
    assert result.content is None
    assert backend.fetch_result(job.provider_job_id).raw["provider_response"]["data"][0]["url"] == (
        "https://cdn.example.test/final.png"
    )
    assert API_KEY not in json.dumps(result.raw)
    assert API_KEY not in json.dumps(backend.get_job_status(job.provider_job_id).raw)


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, "authentication"),
        (403, "authentication"),
        (429, "rate_limited"),
        (400, "invalid_request"),
        (422, "invalid_request"),
        (500, "provider_busy"),
        (503, "provider_busy"),
        (418, "unknown_provider_error"),
    ],
)
def test_provider_http_errors_map_to_stable_error_codes(status_code, expected_code):
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_ENDPOINT).mock(
            return_value=httpx.Response(status_code, json={"error": {"message": "provider failed"}})
        )

        with pytest.raises(ProviderError) as exc_info:
            backend.create_image_job(ImageGenerationRequest(prompt="portrait", size="512x512"))

    assert exc_info.value.provider == "agnes"
    assert exc_info.value.code == expected_code
    assert API_KEY not in str(exc_info.value)
    assert API_KEY not in json.dumps(exc_info.value.raw)


def test_json_error_body_redacts_extended_secret_fields():
    backend = AgnesImageBackend(api_key=API_KEY)
    access_token = "access-token-should-not-leak"
    client_secret = "client-secret-should-not-leak"
    x_api_key = "x-api-key-should-not-leak"

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_ENDPOINT).mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {
                        "message": "invalid request",
                        "access_token": access_token,
                        "client_secret": client_secret,
                        "x-api-key": x_api_key,
                        "nested": {"Authorization": f"Bearer {API_KEY}"},
                    }
                },
            )
        )

        with pytest.raises(ProviderError) as exc_info:
            backend.create_image_job(ImageGenerationRequest(prompt="portrait", size="512x512"))

    raw = json.dumps(exc_info.value.raw)
    assert access_token not in raw
    assert client_secret not in raw
    assert x_api_key not in raw
    assert API_KEY not in raw
    assert "access_token" not in raw
    assert "client_secret" not in raw
    assert "x-api-key" not in raw
    assert "Authorization" not in raw


def test_non_json_error_body_uses_capped_redacted_diagnostic():
    backend = AgnesImageBackend(api_key=API_KEY)
    echoed_bearer = "Bearer echoed-provider-token"
    echoed_key = "agnes-echoed-api-key"
    long_text = f"proxy failed with {echoed_bearer} and api_key={echoed_key}; " + ("x" * 500)

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_ENDPOINT).mock(
            return_value=httpx.Response(
                502,
                content=long_text,
                headers={"content-type": "text/plain"},
            )
        )

        with pytest.raises(ProviderError) as exc_info:
            backend.create_image_job(ImageGenerationRequest(prompt="portrait", size="512x512"))

    response_raw = exc_info.value.raw["response"]
    raw = json.dumps(response_raw)
    assert echoed_bearer not in raw
    assert echoed_key not in raw
    assert API_KEY not in raw
    assert "text_excerpt" in response_raw
    assert "text" not in response_raw
    assert len(response_raw["text_excerpt"]) <= 200


def test_non_positive_timeout_is_rejected_before_http_request():
    with pytest.raises(ValueError, match="agnes timeout_seconds must be positive"):
        AgnesImageBackend(api_key=API_KEY, timeout_seconds=0)


def test_timeout_maps_to_timeout_error_code():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_ENDPOINT).mock(side_effect=httpx.TimeoutException("read timed out"))

        with pytest.raises(ProviderError) as exc_info:
            backend.create_image_job(ImageGenerationRequest(prompt="portrait", size="512x512"))

    assert exc_info.value.provider == "agnes"
    assert exc_info.value.code == "timeout"


def test_missing_response_url_maps_to_unknown_provider_error():
    backend = AgnesImageBackend(api_key=API_KEY)

    with respx.mock(assert_all_called=True) as router:
        router.post(AGNES_ENDPOINT).mock(return_value=httpx.Response(200, json={"data": [{}]}))

        with pytest.raises(ProviderError) as exc_info:
            backend.create_image_job(ImageGenerationRequest(prompt="portrait", size="512x512"))

    assert exc_info.value.code == "unknown_provider_error"


def test_unknown_jobs_remain_rejected():
    backend = AgnesImageBackend(api_key=API_KEY)

    with pytest.raises(KeyError, match="unknown provider job id: missing-job"):
        backend.get_job_status("missing-job")

    with pytest.raises(KeyError, match="unknown provider job id: missing-job"):
        backend.fetch_result("missing-job")
