import json
import math
import re
from copy import deepcopy
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.errors import ProviderError
from ai_drama_web.providers.models import VideoGenerationRequest
from ai_drama_web.services.asset_delivery import AssetDeliveryInvalidPublicBaseUrl, AssetDeliveryService
from ai_drama_web.store import ProductStore


class GenerationExecutionService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        backend: GenerationBackend,
        *,
        asset_delivery: AssetDeliveryService | None = None,
        supplier_gateway=None,
        supplier_execution_enabled: bool = False,
    ) -> None:
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.backend = backend
        self.asset_delivery = asset_delivery
        self.supplier_gateway = supplier_gateway
        self.supplier_execution_enabled = supplier_execution_enabled

    def submit_queued_job(self, job_id: str):
        job = self.product_store.get_generation_job(job_id)
        if job is None:
            raise ValueError("generation job not found")
        if job.internal_status != "queued":
            raise ValueError("only queued jobs can be submitted")
        attempt = self.product_store.get_submission_attempt(job_id)
        if attempt is not None and attempt["state"] in {"submitted", "committed", "unknown"}:
            if attempt["provider_job_id"] and not job.provider_job_id:
                return self.product_store.attach_generation_provider_job(
                    job_id, provider_job_id=attempt["provider_job_id"], response_object_id=attempt["evidence_object_id"]
                )
            return job
        self.product_store.prepare_submission_attempt(job_id, attempt_number=job.attempt_number)
        submitting = self.product_store.transition_generation_job(job.job_id, "submitting")
        request = json.loads(self.runtime_store.read_text(submitting.request_object_id))
        try:
            if self.supplier_execution_enabled and submitting.snapshot_hash:
                response = self.supplier_gateway.invoke(submitting.snapshot_hash, "videoSubmit", request)
                from ai_drama_web.providers.models import ProviderJob
                video_id = response.get("video_id") or response.get("videoId")
                if not video_id:
                    raise ProviderError("PROVIDER_VIDEO_ID_MISSING", "video provider failed", provider="supplier", raw=response)
                provider_job = ProviderJob(str(video_id), "submitted", response)
            else:
                provider_job = self.backend.create_video_job(
                VideoGenerationRequest(
                    prompt=request["prompt"],
                    negative_prompt=request.get("negative_prompt", ""),
                    duration_seconds=request["duration_seconds"],
                    input_images=self._materialize_asset_urls(request),
                    parameters=dict(request.get("parameters") or {}),
                ))
        except ProviderError as exc:
            response_object_id = self._provider_error_object_id(exc)
            self.product_store.record_submission_attempt(job_id, state="unknown", evidence_object_id=response_object_id)
            return self.product_store.transition_generation_job(
                submitting.job_id,
                "failed",
                error_code=exc.code,
                error_message="video provider failed",
                response_object_id=response_object_id,
            )
        except AssetDeliveryInvalidPublicBaseUrl:
            return self.product_store.transition_generation_job(
                submitting.job_id,
                "failed",
                error_code="input_unreachable",
                error_message="video input asset is not provider reachable",
            )
        except Exception:
            self.product_store.record_submission_attempt(job_id, state="unknown")
            return self.product_store.transition_generation_job(
                submitting.job_id,
                "failed",
                error_code="unknown_provider_error",
                error_message="video provider failed",
            )
        response_object_id = self.runtime_store.write_text_object(
            json.dumps(
                _sanitize_persisted_provider_metadata(provider_job.raw),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        self.product_store.record_submission_attempt(
            job_id, state="submitted", provider_job_id=provider_job.provider_job_id, evidence_object_id=response_object_id
        )
        return self.product_store.attach_generation_provider_job(
            submitting.job_id,
            provider_job_id=provider_job.provider_job_id,
            response_object_id=response_object_id,
        )

    def refresh_job(self, job_id: str):
        job = self.product_store.get_generation_job(job_id)
        if job is None:
            raise ValueError("generation job not found")
        if job.internal_status == "queued":
            return job
        if job.internal_status in {"completed", "failed", "cancelled"}:
            return job
        if job.internal_status not in {"submitted", "polling"}:
            raise ValueError("generation job is not refreshable")
        try:
            if self.supplier_execution_enabled and job.snapshot_hash:
                response = self.supplier_gateway.invoke(job.snapshot_hash, "videoPoll", {"video_id": job.provider_job_id})
                from ai_drama_web.providers.models import ProviderJob
                provider_job = ProviderJob(job.provider_job_id, response.get("status", "failed"), response)
            elif job.job_type == "video":
                provider_job = self.backend.get_video_job_status(job.provider_job_id)
            else:
                provider_job = self.backend.get_job_status(job.provider_job_id)
            if provider_job.status in {"submitted", "queued"}:
                return job
            if provider_job.status in {"polling", "processing", "running", "in_progress"}:
                return self.product_store.transition_generation_job(job.job_id, "polling")
            if provider_job.status == "failed":
                response_object_id = self._provider_status_object_id(provider_job)
                return self.product_store.transition_generation_job(
                    job.job_id,
                    "failed",
                    error_code="generation_failed",
                    error_message="video provider failed",
                    response_object_id=response_object_id,
                )
            if provider_job.status != "completed":
                return self.product_store.transition_generation_job(
                    job.job_id,
                    "failed",
                    error_code="unknown_provider_error",
                    error_message="video provider failed",
                )
            if self.supplier_execution_enabled and job.snapshot_hash:
                fetched = self.supplier_gateway.invoke(job.snapshot_hash, "videoFetch", {"video_id": job.provider_job_id})
                from ai_drama_web.providers.models import ProviderResult
                content = fetched.get("content") or fetched.get("bytes")
                if isinstance(content, str):
                    content = content.encode("utf-8")
                result = ProviderResult(job.provider_job_id, fetched.get("media_type", "video/mp4"), fetched.get("url"), content, fetched)
            elif job.job_type == "video":
                result = self.backend.fetch_video_result(job.provider_job_id)
            else:
                result = self.backend.fetch_result(job.provider_job_id)
        except ProviderError as exc:
            response_object_id = self._provider_error_object_id(exc)
            return self.product_store.transition_generation_job(
                job.job_id,
                "failed",
                error_code=exc.code,
                error_message="video provider failed",
                response_object_id=response_object_id,
            )
        object_id = ""
        if result.content is not None:
            object_id = self.runtime_store.write_bytes_object(result.content)
        else:
            return self.product_store.transition_generation_job(
                job.job_id,
                "failed",
                error_code="result_expired",
                error_message="video provider failed",
            )
        metadata_object_id = self.runtime_store.write_text_object(
            json.dumps(
                _sanitize_persisted_provider_metadata({
                    "provider_job": provider_job.raw,
                    "provider_result": {
                        "provider_job_id": result.provider_job_id,
                        "media_type": result.media_type,
                        "url": result.url,
                        "raw": result.raw,
                    },
                }),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        source_url, source_url_state = _persisted_source_url(result.url)
        return self.product_store.complete_generation_job_with_result(
            job_id=job.job_id,
            object_id=object_id,
            media_type=result.media_type,
            source_url=source_url,
            source_url_state=source_url_state,
            metadata_object_id=metadata_object_id,
        )

    def _provider_error_object_id(self, error: ProviderError) -> str:
        evidence = _sanitize_persisted_provider_metadata(
            {
                "provider": error.provider,
                "error_code": error.code,
                "raw": error.raw,
            }
        )
        return self.runtime_store.write_text_object(
            json.dumps(
                evidence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )

    def _provider_status_object_id(self, provider_job) -> str:
        provider = provider_job.raw.get("provider", "agnes")
        evidence = _sanitize_persisted_provider_metadata(
            {
                "provider": provider,
                "status": provider_job.status,
                "raw": provider_job.raw,
            }
        )
        return self.runtime_store.write_text_object(
            json.dumps(
                evidence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )

    def _materialize_asset_urls(self, request: dict) -> list[str]:
        if "assets" in request:
            raise ProviderError(
                "invalid_request",
                "legacy inline video assets are unsupported",
                provider="agnes",
                raw={"legacy_asset_count": len(request["assets"])},
            )
        asset_ids = self._video_input_asset_ids(request)
        if self.asset_delivery is None:
            return [str(asset_id) for asset_id in asset_ids]
        return [self.asset_delivery.signed_asset_url(str(asset_id)) for asset_id in asset_ids]

    def _video_input_asset_ids(self, request: dict) -> list[str]:
        asset_ids = [str(asset_id) for asset_id in request.get("asset_ids") or []]
        assets = []
        for asset_id in asset_ids:
            asset = self.product_store.get_asset(asset_id)
            if asset is None:
                raise ProviderError(
                    "invalid_request",
                    "video input asset is missing",
                    provider="agnes",
                    raw={"asset_id": asset_id},
                )
            assets.append(asset)

        mode = dict(request.get("parameters") or {}).get("mode")
        if mode == "keyframes":
            if not 2 <= len(assets) <= 3 or any(asset.asset_type != "shot_keyframe" for asset in assets):
                raise ProviderError(
                    "invalid_request",
                    "keyframes video requires two or three ordered shot keyframes",
                    provider="agnes",
                    raw={"asset_count": len(assets), "mode": mode},
                )
            return asset_ids

        keyframe_ids = [asset.asset_id for asset in assets if asset.asset_type == "shot_keyframe"]
        if len(keyframe_ids) > 1:
            raise ProviderError(
                "invalid_request",
                "standard video accepts one shot keyframe",
                provider="agnes",
                raw={"shot_keyframe_count": len(keyframe_ids), "mode": mode},
            )
        return keyframe_ids


def _sanitize_persisted_provider_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_text = str(key)
            normalized_key = key_text.lower().replace("-", "_").replace(" ", "_")
            if any(
                fragment in normalized_key
                for fragment in (
                    "authorization",
                    "api_key",
                    "apikey",
                    "token",
                    "secret",
                    "signature",
                )
            ):
                continue
            sanitized_key = key_text
            if sanitized_key in sanitized:
                sanitized_key = f"{type(key).__name__}:{key_text}"
            sanitized[sanitized_key] = _sanitize_persisted_provider_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_persisted_provider_metadata(item) for item in value]
    if isinstance(value, str):
        redacted = re.sub(
            r"Bearer\s+[A-Za-z0-9._~+/=-]+",
            "Bearer [REDACTED]",
            value,
            flags=re.IGNORECASE,
        )
        redacted = re.sub(
            r"([?&]signature=)[^&#\s\"']+",
            r"\1[REDACTED]",
            redacted,
            flags=re.IGNORECASE,
        )
        return re.sub(
            r"((?:api[_-]?key|access[_-]?token|token|client[_-]?secret|authorization)"
            r"\s*[:=]\s*)[^\s;,&\"']+",
            r"\1[REDACTED]",
            redacted,
            flags=re.IGNORECASE,
        )
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return deepcopy(value)
    return f"<{type(value).__name__}>"


def _persisted_source_url(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    filtered_query = []
    removed_sensitive_value = bool(parsed.username or parsed.password or parsed.fragment)
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = key.lower().replace("-", "_")
        if any(
            fragment in normalized_key
            for fragment in ("authorization", "api_key", "apikey", "token", "secret", "signature")
        ):
            removed_sensitive_value = True
            continue
        filtered_query.append((key, value))
    persisted_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc.rsplit("@", 1)[-1],
            parsed.path,
            urlencode(filtered_query),
            "",
        )
    )
    state = "source_url_expired" if removed_sensitive_value else "source_url_active"
    return persisted_url, state
