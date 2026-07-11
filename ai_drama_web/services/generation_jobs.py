import json
from hashlib import sha256

from ai_drama_runtime.shot_prompt_canonical import (
    CONTENT_PROFILE,
    CanonicalShotPromptError,
    parse_shot_prompt_json,
    validate_shot_prompt_canonical,
)
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import AssetDeliveryService
from ai_drama_web.store import ProductStore


class GenerationJobBlocked(Exception):
    pass


class GenerationIdempotencyConflict(Exception):
    pass


class GenerationInvalidRequest(Exception):
    pass


def video_timing_for_duration(duration_seconds: int) -> dict:
    if duration_seconds == 5:
        return {"frame_rate": 24, "num_frames": 121}
    if duration_seconds == 10:
        return {"frame_rate": 24, "num_frames": 241}
    raise GenerationInvalidRequest("unsupported video duration")


class GenerationJobService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        secret_store: LocalSecretStore,
        *,
        public_base_url: str,
    ) -> None:
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.asset_delivery = AssetDeliveryService(
            product_store,
            runtime_store,
            secret_store,
            public_base_url=public_base_url,
        )

    def queue_video_job(
        self,
        *,
        prompt_revision_id: str,
        shot_id: str,
        idempotency_key: str,
        expected_chapter_id: str | None = None,
        explicit_rerun: bool = False,
        overrides: dict | None = None,
    ):
        revision = self._shot_prompt_revision(prompt_revision_id)
        if expected_chapter_id is not None and revision.chapter_id != expected_chapter_id:
            raise GenerationJobBlocked("shot prompt revision is not available")
        existing = self.product_store._generation_job_by_idempotency("agnes", idempotency_key)
        if existing is not None and (
            existing.chapter_id != revision.chapter_id
            or existing.shot_id != shot_id
            or existing.prompt_revision_id != revision.revision_id
            or existing.job_type != "video"
        ):
            raise GenerationIdempotencyConflict("idempotency key was already used for a different request")
        canonical = self._canonical_for_revision(revision)
        shot = self._ready_shot(revision.revision_id, canonical, shot_id)
        request = self._request_for_shot(shot, overrides or {})
        request_text = _canonical_json(request)
        request_hash = sha256(request_text.encode("utf-8")).hexdigest()
        request_object_id = self.runtime_store.write_text_object(request_text)
        attempt_number = 1
        if explicit_rerun:
            attempt_number = self.product_store.next_generation_attempt_number(
                chapter_id=revision.chapter_id,
                shot_id=shot_id,
                provider="agnes",
                job_type="video",
            )
        job = self.product_store.create_generation_job(
            provider="agnes",
            job_type="video",
            project_id=revision.project_id,
            chapter_id=revision.chapter_id,
            shot_id=shot_id,
            prompt_revision_id=revision.revision_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            request_object_id=request_object_id,
            attempt_number=attempt_number,
        )
        if job.request_hash != request_hash:
            raise GenerationIdempotencyConflict("idempotency key was already used for a different request")
        if job.internal_status == "draft":
            return self.product_store.transition_generation_job(job.job_id, "queued")
        return job

    def _shot_prompt_revision(self, revision_id: str):
        revision = self.runtime_store.get_revision(revision_id)
        if revision is None or revision.artifact_type != "shot_prompt_set" or revision.content_profile != CONTENT_PROFILE:
            raise GenerationJobBlocked("shot prompt revision is not available")
        return revision

    def _canonical_for_revision(self, revision) -> dict:
        try:
            canonical = parse_shot_prompt_json(self.runtime_store.read_text(revision.content_object_id))
            validate_shot_prompt_canonical(canonical)
        except CanonicalShotPromptError as exc:
            raise GenerationJobBlocked("shot prompt revision is invalid") from exc
        return canonical

    def _ready_shot(self, revision_id: str, canonical: dict, shot_id: str) -> dict:
        shot = next((item for item in canonical["shots"] if item["shot_id"] == shot_id), None)
        if shot is None or self._shot_readiness(revision_id, shot_id) != "ready":
            raise GenerationJobBlocked("shot prompt is not ready")
        return shot

    def _shot_readiness(self, revision_id: str, shot_id: str) -> str:
        rows = self.runtime_store.conn.execute(
            """
            SELECT body
            FROM review_records
            WHERE revision_id = ? AND scope = 'shot' AND shot_id = ?
            ORDER BY created_at DESC, review_id DESC
            """,
            (revision_id, shot_id),
        ).fetchall()
        for row in rows:
            try:
                body = json.loads(row["body"])
            except json.JSONDecodeError:
                continue
            if body.get("schema_version") == "shot-prompt-readiness-v1":
                return body.get("status", "draft")
        return "draft"

    def _request_for_shot(self, shot: dict, overrides: dict) -> dict:
        asset_ids = overrides.get("asset_ids") or shot["asset_refs"]
        assets = []
        for asset_id in asset_ids:
            asset = self.product_store.get_asset(asset_id)
            if asset is None:
                raise GenerationJobBlocked("asset is missing")
            if asset.status != "usable":
                raise GenerationJobBlocked("asset is not usable")
            if not asset.media_type.startswith("image/"):
                raise GenerationJobBlocked("asset is not an image")
            assets.append(asset)
        duration_seconds = overrides.get("duration_seconds") or shot["duration_seconds"]
        parameters = dict(shot["agnes_video_params"])
        if "duration_seconds" in overrides:
            parameters.pop("frame_rate", None)
            parameters.pop("num_frames", None)
            parameters.update(video_timing_for_duration(duration_seconds))
        else:
            expected_timing = video_timing_for_duration(duration_seconds)
            for field, expected_value in expected_timing.items():
                if field in parameters and parameters[field] != expected_value:
                    raise GenerationInvalidRequest("duration timing conflicts with provider parameters")
            parameters.update(expected_timing)
        for key, value in dict(overrides.get("parameters") or {}).items():
            if key in {"mode", "seed"}:
                parameters[key] = value
            else:
                raise GenerationInvalidRequest("unsupported video parameter")
        mode = parameters.get("mode")
        shot_keyframes = [asset for asset in assets if asset.asset_type == "shot_keyframe"]
        if mode == "keyframes":
            if not 2 <= len(assets) <= 3 or len(shot_keyframes) != len(assets):
                raise GenerationInvalidRequest(
                    "keyframes video requires two or three ordered shot keyframes"
                )
        elif len(shot_keyframes) > 1:
            raise GenerationInvalidRequest("standard video accepts one shot keyframe")
        return {
            "shot_id": shot["shot_id"],
            "prompt": overrides.get("prompt") or shot["positive_prompt"],
            "negative_prompt": overrides.get("negative_prompt") or shot["negative_prompt"],
            "duration_seconds": duration_seconds,
            "asset_ids": list(asset_ids),
            "parameters": parameters,
        }


def _canonical_json(payload: dict) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
