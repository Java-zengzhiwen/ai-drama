import hashlib
import json
import re
from copy import deepcopy
from typing import Any

import httpx

from ai_drama_web.config import Settings
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import (
    ImageGenerationRequest,
    ProviderJob,
    ProviderResult,
    VideoGenerationRequest,
)


class AgnesImageBackend(GenerationBackend):
    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str | None = None,
        model: str | None = None,
        video_endpoint: str | None = None,
        video_model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = Settings()
        resolved_timeout = (
            settings.agnes_timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        if resolved_timeout <= 0:
            raise ValueError("agnes timeout_seconds must be positive")
        self._api_key = api_key
        self._endpoint = endpoint or settings.agnes_image_endpoint
        self._model = model or settings.agnes_image_model
        self._video_endpoint = video_endpoint or settings.agnes_video_endpoint
        self._video_model = video_model or settings.agnes_video_model
        self._timeout_seconds = resolved_timeout
        self._jobs: dict[str, ProviderJob] = {}

    def create_image_job(self, request: ImageGenerationRequest) -> ProviderJob:
        payload = self._build_image_payload(request)
        response_body = self._post_image_generation(payload)
        image_url = self._extract_image_url(response_body)
        provider_job_id = self._image_job_id(payload, image_url)
        job = ProviderJob(
            provider_job_id=provider_job_id,
            status="succeeded",
            raw=_sanitize_raw(
                {
                    "provider": "agnes",
                    "media_type": "image",
                    "request": payload,
                    "provider_response": response_body,
                    "result_url": image_url,
                },
                secrets=(self._api_key,),
            ),
        )
        self._jobs[provider_job_id] = _copy_job(job)
        return _copy_job(job)

    def create_video_job(self, request: VideoGenerationRequest) -> ProviderJob:
        payload = self._build_video_payload(request)
        response_body = self._post_video_generation(payload)
        video_id = self._extract_video_id(response_body)
        job = ProviderJob(
            provider_job_id=video_id,
            status="submitted",
            raw=_sanitize_raw(
                {
                    "provider": "agnes",
                    "media_type": "video",
                    "request": payload,
                    "provider_response": response_body,
                    "task_id": response_body.get("task_id"),
                    "video_id": video_id,
                },
                secrets=(self._api_key,),
            ),
        )
        self._jobs[video_id] = _copy_job(job)
        return _copy_job(job)

    def get_job_status(self, provider_job_id: str) -> ProviderJob:
        try:
            return _copy_job(self._jobs[provider_job_id])
        except KeyError as exc:
            raise KeyError(f"unknown provider job id: {provider_job_id}") from exc

    def fetch_result(self, provider_job_id: str) -> ProviderResult:
        job = self.get_job_status(provider_job_id)
        image_url = job.raw.get("result_url")
        if not isinstance(image_url, str) or not image_url:
            raise ProviderError(
                "unknown_provider_error",
                "agnes image job is missing a result URL",
                provider="agnes",
                raw={"provider_job_id": provider_job_id, "job": job.raw},
            )
        return ProviderResult(
            provider_job_id=provider_job_id,
            media_type="image/png",
            url=image_url,
            content=None,
            raw=_sanitize_raw(
                {
                    "provider": "agnes",
                    "media_type": "image/png",
                    "source_job": job.raw,
                    "provider_response": job.raw.get("provider_response", {}),
                },
                secrets=(self._api_key,),
            ),
        )

    def _build_image_payload(self, request: ImageGenerationRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": request.prompt,
            "size": request.size,
            "extra_body": {"response_format": "url"},
        }
        if request.input_images:
            payload["extra_body"]["image"] = list(request.input_images)
        return payload

    def _build_video_payload(self, request: VideoGenerationRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._video_model,
            "prompt": request.prompt,
        }
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        parameters = dict(request.parameters)
        mode = parameters.pop("mode", None)
        payload.update(parameters)

        if len(request.input_images) == 1:
            payload["image"] = request.input_images[0]
        elif len(request.input_images) > 1:
            extra_body: dict[str, Any] = {"image": list(request.input_images)}
            if mode:
                extra_body["mode"] = mode
            payload["extra_body"] = extra_body
        elif mode:
            payload["extra_body"] = {"mode": mode}
        return payload

    def _post_image_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "timeout",
                "agnes image request timed out",
                provider="agnes",
                raw=_sanitize_raw({"endpoint": self._endpoint}, secrets=(self._api_key,)),
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "unknown_provider_error",
                "agnes image request failed",
                provider="agnes",
                raw=_sanitize_raw(
                    {"endpoint": self._endpoint, "error": str(exc)},
                    secrets=(self._api_key,),
                ),
            ) from exc

        if response.status_code >= 400:
            raise ProviderError(
                _http_error_code(response.status_code),
                "agnes image request was rejected",
                provider="agnes",
                raw={
                    "status_code": response.status_code,
                    "response": _safe_response_json(response, secrets=(self._api_key,)),
                },
            )

        response_body = _safe_response_json(response, secrets=(self._api_key,))
        if not isinstance(response_body, dict):
            raise ProviderError(
                "unknown_provider_error",
                "agnes image response was not a JSON object",
                provider="agnes",
                raw={"response": response_body},
            )
        return response_body

    def _post_video_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                self._video_endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "timeout",
                "agnes video request timed out",
                provider="agnes",
                raw=_sanitize_raw({"endpoint": self._video_endpoint}, secrets=(self._api_key,)),
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "unknown_provider_error",
                "agnes video request failed",
                provider="agnes",
                raw=_sanitize_raw(
                    {"endpoint": self._video_endpoint, "error": str(exc)},
                    secrets=(self._api_key,),
                ),
            ) from exc

        if response.status_code >= 400:
            raise ProviderError(
                _http_error_code(response.status_code),
                "agnes video request was rejected",
                provider="agnes",
                raw={
                    "status_code": response.status_code,
                    "response": _safe_response_json(response, secrets=(self._api_key,)),
                },
            )

        response_body = _safe_response_json(response, secrets=(self._api_key,))
        if not isinstance(response_body, dict):
            raise ProviderError(
                "unknown_provider_error",
                "agnes video response was not a JSON object",
                provider="agnes",
                raw={"response": response_body},
            )
        return response_body

    @staticmethod
    def _extract_image_url(response_body: dict[str, Any]) -> str:
        try:
            image_url = response_body["data"][0]["url"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "unknown_provider_error",
                "agnes image response did not include data[0].url",
                provider="agnes",
                raw={"provider_response": response_body},
            ) from exc
        if not isinstance(image_url, str) or not image_url:
            raise ProviderError(
                "unknown_provider_error",
                "agnes image response included an invalid result URL",
                provider="agnes",
                raw={"provider_response": response_body},
            )
        return image_url

    @staticmethod
    def _extract_video_id(response_body: dict[str, Any]) -> str:
        video_id = response_body.get("video_id")
        if not isinstance(video_id, str) or not video_id:
            raise ProviderError(
                "unknown_provider_error",
                "agnes video response did not include video_id",
                provider="agnes",
                raw={"provider_response": response_body},
            )
        return video_id

    @staticmethod
    def _image_job_id(payload: dict[str, Any], image_url: str) -> str:
        raw = {"payload": payload, "image_url": image_url}
        serialized = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"agnes-image-{digest}"


def _http_error_code(status_code: int) -> str:
    if status_code in {401, 403}:
        return "authentication"
    if status_code == 429:
        return "rate_limited"
    if status_code in {400, 422}:
        return "invalid_request"
    if 500 <= status_code <= 599:
        return "provider_busy"
    return "unknown_provider_error"


def _safe_response_json(response: httpx.Response, *, secrets: tuple[str, ...] = ()) -> Any:
    try:
        return _sanitize_raw(response.json(), secrets=secrets)
    except ValueError:
        text = _redact_text(response.text, secrets=secrets)
        max_chars = 200
        return {
            "text_excerpt": text[:max_chars],
            "truncated": len(text) > max_chars,
        }


def _copy_job(job: ProviderJob) -> ProviderJob:
    return ProviderJob(
        provider_job_id=job.provider_job_id,
        status=job.status,
        raw=deepcopy(job.raw),
    )


def _sanitize_raw(value: Any, *, secrets: tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if _is_sensitive_key(key):
                continue
            sanitized[key] = _sanitize_raw(item, secrets=secrets)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_raw(item, secrets=secrets) for item in value]
    if isinstance(value, str):
        return _redact_text(value, secrets=secrets)
    return deepcopy(value)


def _is_sensitive_key(key: Any) -> bool:
    normalized_key = str(key).lower().replace("-", "_").replace(" ", "_")
    sensitive_fragments = (
        "authorization",
        "api_key",
        "apikey",
        "x_api_key",
        "token",
        "secret",
    )
    return any(fragment in normalized_key for fragment in sensitive_fragments)


def _redact_text(value: str, *, secrets: tuple[str, ...] = ()) -> str:
    redacted = value
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = re.sub(
        r"Bearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [REDACTED]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"((?:api[_-]?key|x[_-]?api[_-]?key|access[_-]?token|client[_-]?secret)"
        r"\s*[:=]\s*)([^\s;,&]+)",
        r"\1[REDACTED]",
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted
