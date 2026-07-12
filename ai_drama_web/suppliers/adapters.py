"""Provider-neutral M6C adapter boundary.

Adapters receive an injected helper/worker in production. This module deliberately
contains no HTTP client; tests use the deterministic fake adapter below.
"""
from dataclasses import dataclass
from typing import Any, Callable
import re


class AdapterError(RuntimeError):
    def __init__(self, code: str, message: str = "adapter operation failed"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class NormalizedResponse:
    value: Any
    usage: dict
    evidence: dict


def sanitize_evidence(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): sanitize_evidence(v)
            for k, v in value.items()
            if not any(x in str(k).lower().replace("-", "_") for x in ("authorization", "bearer", "api_key", "token", "secret", "signature"))
        }
    if isinstance(value, list):
        return [sanitize_evidence(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", value)
        return value.split("?", 1)[0] if "?" in value and ("http://" in value or "https://" in value) else value
    return value


class SupplierAdapterGateway:
    def __init__(self, worker: Callable[[str, dict], Any], *, supplier_slug: str):
        self.worker = worker
        self.supplier_slug = supplier_slug

    def text_request(self, payload: dict) -> NormalizedResponse:
        result = self.worker("textRequest", payload)
        return NormalizedResponse(result.get("output", result), dict(result.get("usage") or {}), sanitize_evidence(result))

    def image_request(self, payload: dict) -> NormalizedResponse:
        result = self.worker("imageRequest", payload)
        return NormalizedResponse(result, {}, sanitize_evidence(result))

    def video_submit(self, payload: dict) -> NormalizedResponse:
        result = self.worker("videoSubmit", payload)
        video_id = result.get("video_id") or result.get("videoId")
        if not video_id:
            raise AdapterError("PROVIDER_VIDEO_ID_MISSING")
        return NormalizedResponse({"video_id": str(video_id)}, {}, sanitize_evidence(result))

    def video_poll(self, video_id: str) -> NormalizedResponse:
        result = self.worker("videoPoll", {"video_id": video_id})
        status = str(result.get("status") or "").lower()
        mapping = {"pending": "queued", "submitted": "queued", "processing": "polling", "running": "polling", "succeeded": "completed", "success": "completed", "error": "failed"}
        if status not in {"queued", "polling", "completed", "failed"}:
            status = mapping.get(status, status)
        if status not in {"queued", "polling", "completed", "failed"}:
            raise AdapterError("PROVIDER_STATUS_INVALID")
        return NormalizedResponse({"video_id": video_id, "status": status}, {}, sanitize_evidence(result))

    def video_fetch(self, video_id: str) -> NormalizedResponse:
        result = self.worker("videoFetch", {"video_id": video_id})
        return NormalizedResponse(result, {}, sanitize_evidence(result))


class FakeSupplierAdapter:
    """Deterministic, in-process adapter used by M6C tests and verifier."""
    def __init__(self):
        self.submit_count = 0
        self.poll_count = 0
        self.fetch_count = 0

    def __call__(self, operation: str, payload: dict):
        if operation == "textRequest":
            return {"output": "fake-text:" + str(payload.get("prompt", "")), "usage": {"input_tokens": 1, "output_tokens": 1}}
        if operation == "imageRequest":
            return {"media_type": "image/png", "bytes": "fake-png"}
        if operation == "videoSubmit":
            self.submit_count += 1
            return {"video_id": "fake-video-1", "task_id": "must-not-be-polled"}
        if operation == "videoPoll":
            self.poll_count += 1
            return {"status": "completed", "video_id": payload["video_id"]}
        if operation == "videoFetch":
            self.fetch_count += 1
            return {"media_type": "video/mp4", "bytes": "fake-mp4"}
        raise AdapterError("UNSUPPORTED_OPERATION")
