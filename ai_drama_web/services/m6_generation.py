import json
import uuid
from dataclasses import dataclass, replace

from ai_drama_web.services.generation_execution import _persisted_source_url
from ai_drama_web.suppliers.adapters import sanitize_evidence
from ai_drama_web.suppliers.idempotency import (
    SupplierIdempotencyConflict,
    canonical_request_hash,
)
from ai_drama_web.suppliers.resolution import ModelResolver, ModelResolutionError
from ai_drama_web.suppliers.snapshots import SnapshotBuilder
from ai_drama_web.suppliers.snapshots import load_snapshot, snapshot_hash
from ai_drama_web.suppliers.reasoning import (
    ReasoningEffortError,
    resolve_reasoning_effort,
)
from ai_drama_web.suppliers.image_options import ImageOptionError, resolve_image_options
from ai_drama_runtime.store import now_iso


TEXT_GENERATION_WORKER_TIMEOUT_SECONDS = 180


class M6GenerationError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PreparedTextStream:
    session_run_id: str
    supplier_text_run_id: str
    snapshot_hash: str
    request_object_id: str


def _normalize_text_request(request):
    """Convert an internal RuntimeRequest into the provider-neutral text contract.

    Model-level tests and direct callers already provide ``prompt`` or ``messages``.
    Workflow execution instead passes the complete, versioned RuntimeRequest used by
    the legacy OpenAI-compatible path. Preserve that exact payload as the user
    message so supplier adapters never receive an empty prompt and the request stays
    deterministic and auditable.
    """
    if not isinstance(request, dict):
        raise M6GenerationError("SUPPLIER_TEXT_REQUEST_INVALID")
    if request.get("prompt") is not None or request.get("messages") is not None:
        return request
    if request.get("request_format_version") != "runtime-request-v1":
        return request
    messages = []
    system_instruction = request.get("system_instruction")
    if system_instruction:
        messages.append({"role": "system", "content": str(system_instruction)})
    messages.append(
        {
            "role": "user",
            "content": json.dumps(
                request,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
    )
    return {"messages": messages}


class M6GenerationCoordinator:
    def __init__(
        self, store, runtime_store, credential_store, gateway,
        checkpoint=None, rate_limiter=None,
    ):
        self.store = store
        self.runtime = runtime_store
        self.credentials = credential_store
        self.gateway = gateway
        self.rate_limiter = rate_limiter
        self._checkpoint = checkpoint or (lambda _name: None)

    def _resolve_snapshot(self, project_id, operation_key, constraints=None, request=None):
        try:
            resolved = ModelResolver(self.store).resolve(project_id, operation_key)
        except ModelResolutionError as exc:
            raise M6GenerationError(exc.code) from exc
        supplier = resolved.supplier
        credential_id = supplier.current_credential_version_id
        if not credential_id:
            raise M6GenerationError("CREDENTIAL_MISSING")
        credential = self.store.get_credential_version(credential_id)
        if credential is None:
            raise M6GenerationError("CREDENTIAL_MISSING")
        if credential.state != "ready":
            raise M6GenerationError(
                "CREDENTIAL_STORAGE_CORRUPT"
                if credential.state == "credential_storage_corrupt"
                else "CREDENTIAL_NOT_READY"
            )
        if constraints is None and resolved.revision.capability in {"text", "image"}:
            definition = self._read_json_object(resolved.revision.definition_object_id)
            config = self.store.get_config_revision(supplier.current_config_revision_id)
            config_value = self._read_json_object(config.config_object_id) if config else {}
            if resolved.revision.capability == "text":
                try:
                    constraints = {
                        "reasoning_effort": resolve_reasoning_effort(
                            request=request or {},
                            model_definition=definition,
                            supplier_config=config_value,
                        )
                    }
                except ReasoningEffortError as exc:
                    raise M6GenerationError(exc.code) from exc
            else:
                try:
                    constraints = resolve_image_options(
                        request=request or {},
                        model_definition=definition,
                        supplier_config=config_value,
                    )
                except ImageOptionError as exc:
                    raise M6GenerationError(exc.code) from exc
        timeout_seconds = (
            TEXT_GENERATION_WORKER_TIMEOUT_SECONDS
            if resolved.revision.capability == "text"
            else 30
        )
        return SnapshotBuilder(self.store).build(
            resolved,
            credential_resolution_mode="current",
            resolved_credential_version_id=credential_id,
            resolved_constraints=constraints or {},
            worker_limits={
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": 4 * 1024 * 1024,
            },
        )

    def _read_json_object(self, object_id):
        if not object_id:
            return {}
        try:
            value = json.loads(self.runtime.read_text(object_id))
        except (OSError, ValueError, TypeError) as exc:
            raise M6GenerationError("SUPPLIER_RUNTIME_UNAVAILABLE") from exc
        return value if isinstance(value, dict) else {}

    def enqueue_video(self, *, project_id, chapter_id, shot_id, prompt_revision_id,
                      idempotency_key, request, snapshot=None, source_job_id="",
                      rerun_resolution_mode=""):
        snapshot = snapshot or self._resolve_snapshot(project_id, "shot_video_generation")
        return self.store.enqueue_generation_job_with_snapshot(
            supplier_id=snapshot.supplier_id,
            capability="video",
            provider=f"m6:{snapshot.supplier_id}:video",
            job_type="video",
            project_id=project_id,
            chapter_id=chapter_id,
            shot_id=shot_id,
            prompt_revision_id=prompt_revision_id,
            idempotency_key=idempotency_key,
            request=request,
            snapshot=snapshot,
            source_job_id=source_job_id,
            rerun_resolution_mode=rerun_resolution_mode,
        )

    def rerun_video(self, *, source_job, idempotency_key, request,
                    use_current_project_model=False):
        if use_current_project_model:
            snapshot = self._resolve_snapshot(source_job.project_id, "shot_video_generation")
            resolution_mode = "current_project_model"
        else:
            source = load_snapshot(self.store, source_job.snapshot_hash)
            supplier = self.store.get_supplier(source.supplier_id)
            credential_id = supplier.current_credential_version_id if supplier else ""
            credential = self.store.get_credential_version(credential_id) if credential_id else None
            if credential is None:
                raise M6GenerationError("CREDENTIAL_MISSING")
            if credential.state != "ready":
                raise M6GenerationError("CREDENTIAL_STORAGE_CORRUPT" if credential.state == "credential_storage_corrupt" else "CREDENTIAL_NOT_READY")
            snapshot = replace(
                source,
                credential_resolution_mode="current",
                resolved_credential_version_id=credential_id,
                source_snapshot_hash=source_job.snapshot_hash,
                source_supplier_version_id=source.supplier_version_id,
                source_config_revision_id=source.config_revision_id,
                source_model_revision_id=source.model_revision_id,
                created_at=now_iso(),
            )
            resolution_mode = "inherit_source_snapshot"
        return self.enqueue_video(
            project_id=source_job.project_id,
            chapter_id=source_job.chapter_id,
            shot_id=source_job.shot_id,
            prompt_revision_id=source_job.prompt_revision_id,
            idempotency_key=idempotency_key,
            request=request,
            snapshot=snapshot,
            source_job_id=source_job.job_id,
            rerun_resolution_mode=resolution_mode,
        )

    def execute_text(self, *, project_id, operation_key, idempotency_key, request):
        request = _normalize_text_request(request)
        snapshot = self._resolve_snapshot(project_id, operation_key, request=request)
        replay = self._matching_replay(snapshot, "text", idempotency_key, request)
        if replay is not None:
            if replay["status"] == "completed":
                payload = json.loads(self.runtime.read_text(replay["result_object_id"]))
                return {"run_id": replay["run_id"], **payload}
            raise M6GenerationError("IDEMPOTENT_RUN_NOT_COMPLETED")
        reserved = self._reserve_rate_limit(snapshot, "text", idempotency_key)
        try:
            run, created = self.store.enqueue_text_run_with_snapshot(
                project_id=project_id,
                operation_key=operation_key,
                supplier_id=snapshot.supplier_id,
                idempotency_key=idempotency_key,
                request=request,
                snapshot=snapshot,
            )
        except Exception:
            self._release_rate_limit(snapshot, reserved)
            raise
        if not created:
            self._release_rate_limit(snapshot, reserved)
            if run["status"] == "completed":
                payload = json.loads(self.runtime.read_text(run["result_object_id"]))
                return {"run_id": run["run_id"], **payload}
            raise M6GenerationError("IDEMPOTENT_RUN_NOT_COMPLETED")
        try:
            response = self.gateway.invoke(run["snapshot_hash"], "textRequest", request)
        except Exception as exc:
            safe = sanitize_evidence(getattr(exc, "evidence", {}))
            evidence_object_id = (
                self.runtime.write_text_object(
                    json.dumps(safe, sort_keys=True, separators=(",", ":"))
                )
                if safe
                else ""
            )
            self.store.fail_supplier_text_run(
                run["run_id"],
                error_code=getattr(exc, "code", "SUPPLIER_EXECUTION_FAILED"),
                evidence_object_id=evidence_object_id,
            )
            raise
        normalized = {
            "output": response.get("output", ""),
            "usage": dict(response.get("usage") or {}),
        }
        safe = sanitize_evidence(response)
        result_object_id = self.runtime.write_text_object(
            json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        )
        evidence_object_id = self.runtime.write_text_object(
            json.dumps(safe, sort_keys=True, separators=(",", ":"))
        )
        self.store.complete_supplier_text_run(
            run["run_id"], result_object_id=result_object_id,
            evidence_object_id=evidence_object_id,
        )
        return {"run_id": run["run_id"], **normalized}

    def prepare_text_stream(
        self,
        *,
        project_id,
        chapter_id,
        source_revision_id,
        runtime_run_id,
        idempotency_key,
        request,
    ):
        request = _normalize_text_request(request)
        snapshot = self._resolve_snapshot(
            project_id, "script_adaptation", request=request
        )
        supplier_key = f"script-stream:{idempotency_key}"
        replay = self._matching_replay(
            snapshot, "text", supplier_key, request
        )
        if replay is None:
            text_run, _created = self.store.enqueue_text_run_with_snapshot(
                project_id=project_id,
                operation_key="script_adaptation",
                supplier_id=snapshot.supplier_id,
                idempotency_key=supplier_key,
                request=request,
                snapshot=snapshot,
            )
        else:
            text_run = replay
        existing = self.store.get_script_generation_run_by_idempotency(
            idempotency_key
        )
        if existing is not None:
            if existing["supplier_text_run_id"] != text_run["run_id"]:
                raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
            return PreparedTextStream(
                session_run_id=existing["run_id"],
                supplier_text_run_id=existing["supplier_text_run_id"],
                snapshot_hash=existing["snapshot_hash"],
                request_object_id=text_run["request_object_id"],
            )
        session = self.store.create_script_generation_run(
            run_id=uuid.uuid4().hex,
            project_id=project_id,
            chapter_id=chapter_id,
            source_revision_id=source_revision_id,
            runtime_run_id=runtime_run_id,
            idempotency_key=idempotency_key,
        )
        session = self.store.bind_script_generation_snapshot(
            session["run_id"],
            supplier_text_run_id=text_run["run_id"],
            snapshot_hash=text_run["snapshot_hash"],
        )
        return PreparedTextStream(
            session_run_id=session["run_id"],
            supplier_text_run_id=text_run["run_id"],
            snapshot_hash=text_run["snapshot_hash"],
            request_object_id=text_run["request_object_id"],
        )

    def generate_image(self, *, project_id, chapter_id, idempotency_key, request):
        snapshot = self._resolve_snapshot(
            project_id, "storyboard_keyframe_image", request=request
        )
        job = self._matching_replay(snapshot, "image", idempotency_key, request)
        created = job is None
        reserved = False
        if created:
            reserved = self._reserve_rate_limit(snapshot, "image", idempotency_key)
            try:
                job, created = self.store.enqueue_generation_job_with_snapshot(
                    supplier_id=snapshot.supplier_id,
                    capability="image",
                    provider=f"m6:{snapshot.supplier_id}:image",
                    job_type="image",
                    project_id=project_id,
                    chapter_id=chapter_id,
                    shot_id=str(request.get("shot_id") or ""),
                    prompt_revision_id="",
                    idempotency_key=idempotency_key,
                    request=request,
                    snapshot=snapshot,
                )
            except Exception:
                self._release_rate_limit(snapshot, reserved)
                raise
        if not created:
            row = self.store.conn.execute(
                "SELECT asset_id FROM assets WHERE source_job_id = ? ORDER BY created_at, asset_id LIMIT 1",
                (job.job_id,),
            ).fetchone()
            if row is not None:
                self._release_rate_limit(snapshot, reserved)
                return self._asset(row["asset_id"], job.job_id)
            attempt = self.store.get_submission_attempt(job.job_id)
            if attempt is None or attempt["state"] != "prepared":
                self._release_rate_limit(snapshot, reserved)
                raise M6GenerationError("IDEMPOTENT_RUN_NOT_COMPLETED")
            if not reserved:
                reserved = self._acquire_rate_limit(snapshot)
        attempt = self.store.get_submission_attempt(job.job_id)
        if attempt["state"] != "prepared":
            self._release_rate_limit(snapshot, reserved)
            raise M6GenerationError("SUBMISSION_OUTCOME_UNKNOWN")
        claimed = self.store.claim_generation_submission(job.job_id)
        if claimed is None:
            self._release_rate_limit(snapshot, reserved)
            raise M6GenerationError("IDEMPOTENT_RUN_NOT_COMPLETED")
        job = claimed
        try:
            response = self.gateway.invoke(job.snapshot_hash, "imageRequest", request)
        except Exception as exc:
            self.store.record_submission_attempt(job.job_id, state="unknown_outcome")
            self.store.transition_generation_job(
                job.job_id, "failed", error_code="SUBMISSION_OUTCOME_UNKNOWN",
                error_message="image submission outcome is unknown",
            )
            raise
        content = response.get("content") or response.get("bytes")
        if isinstance(content, str):
            content = content.encode("utf-8")
        if not content:
            raise M6GenerationError("RESULT_MISSING")
        media_type = str(response.get("media_type") or "image/png")
        object_id = self.runtime.write_bytes_object(content)
        safe_response = sanitize_evidence({key: value for key, value in response.items() if key not in {"content", "bytes"}})
        safe_response["object_id"] = object_id
        evidence_object_id = self.runtime.write_text_object(
            json.dumps(safe_response, sort_keys=True, separators=(",", ":"))
        )
        provider_job_id = str(response.get("provider_job_id") or f"image-{job.job_id}")
        self.store.record_submission_attempt(
            job.job_id, state="accepted", provider_job_id=provider_job_id,
            evidence_object_id=evidence_object_id,
        )
        self._checkpoint("image_accepted_persisted")
        self.store.commit_accepted_submission(job.job_id)
        return self._finalize_image(job.job_id)

    def _matching_replay(self, snapshot, capability, idempotency_key, request):
        record = self.store.get_supplier_idempotency_record(
            snapshot.supplier_id, capability, idempotency_key
        )
        if record is None:
            return None
        if capability == "text":
            entity = self.store.get_supplier_text_run(record["existing_id"])
            stored_hash = entity["snapshot_hash"] if entity is not None else ""
        else:
            entity = self.store.get_generation_job(record["existing_id"])
            stored_hash = entity.snapshot_hash if entity is not None else ""
        if entity is None or not stored_hash:
            raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
        stored_snapshot = load_snapshot(self.store, stored_hash)
        current_with_original_time = replace(snapshot, created_at=stored_snapshot.created_at)
        if snapshot_hash(current_with_original_time) != stored_hash:
            raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
        if canonical_request_hash(request, stored_hash) != record["request_hash"]:
            raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
        return entity

    def _reserve_rate_limit(self, snapshot, capability, idempotency_key):
        if self.rate_limiter is None:
            return False
        existing = self.store.get_supplier_idempotency_record(
            snapshot.supplier_id, capability, idempotency_key
        )
        if existing is not None:
            return False
        if not self.rate_limiter.acquire(snapshot.rate_limit_bucket_key):
            existing = self.store.get_supplier_idempotency_record(
                snapshot.supplier_id, capability, idempotency_key
            )
            if existing is not None:
                return False
            raise M6GenerationError("RATE_LIMITED")
        return True

    def _acquire_rate_limit(self, snapshot):
        if self.rate_limiter is None:
            return False
        if not self.rate_limiter.acquire(snapshot.rate_limit_bucket_key):
            raise M6GenerationError("RATE_LIMITED")
        return True

    def _release_rate_limit(self, snapshot, reserved):
        if reserved and self.rate_limiter is not None:
            self.rate_limiter.release(snapshot.rate_limit_bucket_key)

    def recover_image_jobs(self):
        rows = self.store.conn.execute(
            """
            SELECT j.job_id FROM generation_jobs j
            JOIN generation_submission_attempts a ON a.job_id=j.job_id
            WHERE j.job_type='image' AND j.internal_status='submitted'
              AND a.state='committed' AND j.provider_result_id=''
            ORDER BY j.created_at, j.job_id
            """
        ).fetchall()
        for row in rows:
            self._finalize_image(row["job_id"])
        return len(rows)

    def _finalize_image(self, job_id):
        job = self.store.get_generation_job(job_id)
        attempt = self.store.get_submission_attempt(job_id)
        response = json.loads(self.runtime.read_text(attempt["evidence_object_id"]))
        request = json.loads(self.runtime.read_text(job.request_object_id))
        object_id = response["object_id"]
        media_type = str(response.get("media_type") or "image/png")
        content = self.runtime.read_bytes_object(object_id)
        source_url, source_state = _persisted_source_url(str(response.get("url") or ""))
        completed = self.store.complete_generation_job_with_result(
            job_id=job_id, object_id=object_id, media_type=media_type,
            source_url=source_url, source_url_state=source_state,
            metadata_object_id=attempt["evidence_object_id"],
        )
        existing = self.store.conn.execute(
            "SELECT asset_id FROM assets WHERE source_job_id=? ORDER BY created_at, asset_id LIMIT 1",
            (job_id,),
        ).fetchone()
        if existing is not None:
            return self._asset(existing["asset_id"], job_id)
        asset = self.store.create_generated_asset(
            project_id=job.project_id,
            chapter_id=job.chapter_id,
            asset_type=str(request["asset_type"]),
            name=str(request["name"]),
            data=content,
            media_type=media_type,
            source_job_id=job_id,
            metadata={"generation_job_id": job_id, "generation_result_id": completed.provider_result_id},
        )
        return self._asset(asset.asset_id, job_id)

    def _asset(self, asset_id, job_id):
        asset = self.store.get_asset(asset_id)
        return {
            "asset_id": asset.asset_id,
            "project_id": asset.project_id,
            "chapter_id": asset.chapter_id,
            "asset_type": asset.asset_type,
            "name": asset.name,
            "object_id": asset.object_id,
            "media_type": asset.media_type,
            "width": asset.width,
            "height": asset.height,
            "status": asset.status,
            "source_type": asset.source_type,
            "source_job_id": asset.source_job_id,
            "metadata": json.loads(self.runtime.read_text(asset.metadata_object_id)),
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
            "job_id": job_id,
        }
