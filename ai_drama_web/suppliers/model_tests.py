import asyncio
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from .adapters import sanitize_evidence
from .idempotency import canonical_request_hash
from .models import RevisionConflict
from .resolution import ResolvedModel
from .snapshots import SnapshotBuilder, SupplierRuntimeUnavailable, load_snapshot, snapshot_hash
from .media import image_bytes_match_media_type


TEST_CONTRACT_VERSION = "model-test-v1"
AMBIGUOUS_EXECUTION_ERRORS = {
    "SUPPLIER_WORKER_TIMEOUT",
    "SUPPLIER_WORKER_EXITED",
    "SUPPLIER_WORKER_PROTOCOL_ERROR",
    "SUPPLIER_EXECUTION_FAILED",
}


class ModelTestError(RuntimeError):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


class ModelTestService:
    def __init__(self, store):
        self.store = store

    def create_model_test(
        self, *, supplier_model_id, prompt, idempotency_key, expected_model_revision
    ):
        model = self.store.get_supplier_model(supplier_model_id)
        if model is None:
            raise ModelTestError("MODEL_NOT_FOUND")
        if model.revision != expected_model_revision:
            raise RevisionConflict("model revision conflict")
        revision = self.store.get_supplier_model_revision(model.current_model_revision_id)
        if revision is None:
            raise ModelTestError("MODEL_NOT_FOUND")
        capability = revision.capability
        if capability not in {"text", "image"}:
            raise ModelTestError("MODEL_TEST_CAPABILITY_UNSUPPORTED")
        max_prompt = 4000 if capability == "text" else 2000
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > max_prompt:
            raise ModelTestError("MODEL_TEST_PROMPT_INVALID")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ModelTestError("IDEMPOTENCY_KEY_REQUIRED")
        supplier = self.store.get_supplier(model.supplier_id)
        if supplier is None or not supplier.enabled:
            raise ModelTestError("SUPPLIER_DISABLED")
        if not model.enabled:
            raise ModelTestError("MODEL_DISABLED")
        credential_id = supplier.current_credential_version_id
        credential = self.store.get_credential_version(credential_id) if credential_id else None
        if credential is None:
            raise ModelTestError("CREDENTIAL_MISSING")
        if credential.state != "ready":
            raise ModelTestError(
                "CREDENTIAL_STORAGE_CORRUPT"
                if credential.state == "credential_storage_corrupt"
                else "CREDENTIAL_REVOKED"
            )
        operation = "textRequest" if capability == "text" else "imageRequest"
        if not self._operation_available(supplier, operation):
            raise ModelTestError("SUPPLIER_OPERATION_UNAVAILABLE")
        definition = self._read_json(revision.definition_object_id)
        request = {"prompt": prompt.strip(), "test_contract_version": TEST_CONTRACT_VERSION}
        resolved_constraints = {}
        if capability == "image":
            constraints = definition.get("constraints") if isinstance(definition, dict) else {}
            declared_size = definition.get("default_size") if isinstance(definition, dict) else None
            if not declared_size and isinstance(constraints, dict):
                declared_size = constraints.get("size")
            request["size"] = str(declared_size or "1024x768")
            resolved_constraints["size"] = request["size"]
        replay = self.store.get_supplier_model_test_run_by_key(
            supplier_model_id, idempotency_key.strip()
        )
        if replay is not None:
            return self._resolve_replay(
                replay,
                request=request,
                supplier=supplier,
                model=model,
                revision=revision,
                credential_id=credential_id,
            )
        resolution = ResolvedModel(
            "",
            "supplier_model_test",
            capability,
            "direct_model_test",
            supplier,
            model,
            revision,
        )
        snapshot = SnapshotBuilder(self.store).build(
            resolution,
            credential_resolution_mode="current",
            resolved_credential_version_id=credential_id,
            resolved_constraints=resolved_constraints,
            worker_limits={
                "timeout_seconds": 30 if capability == "text" else 120,
                "max_output_bytes": 4 * 1024 * 1024,
                "max_media_bytes": 25 * 1024 * 1024,
            },
        )
        request_raw = _canonical(request)
        request_object_id = self.store.runtime.write_text_object(request_raw)
        digest = snapshot_hash(snapshot)
        request_digest = canonical_request_hash(request, digest)
        return self.store.create_supplier_model_test_run(
            test_run_id=uuid.uuid4().hex,
            supplier_id=supplier.supplier_id,
            supplier_model_id=supplier_model_id,
            credential_version_id=credential_id,
            snapshot=snapshot,
            capability=capability,
            idempotency_key=idempotency_key.strip(),
            request_hash=request_digest,
            request_object_id=request_object_id,
        )

    def _resolve_replay(
        self, replay, *, request, supplier, model, revision, credential_id
    ):
        try:
            previous_request = json.loads(
                self.store.runtime.read_text(replay["request_object_id"])
            )
            previous_snapshot = load_snapshot(self.store, replay["snapshot_hash"])
        except Exception as exc:
            raise ModelTestError("SUPPLIER_RUNTIME_UNAVAILABLE") from exc
        same_resolution = (
            previous_request == request
            and previous_snapshot.supplier_id == supplier.supplier_id
            and previous_snapshot.supplier_version_id
            == supplier.current_supplier_version_id
            and previous_snapshot.config_revision_id
            == supplier.current_config_revision_id
            and previous_snapshot.supplier_model_id == model.supplier_model_id
            and previous_snapshot.model_revision_id == revision.model_revision_id
            and previous_snapshot.resolved_credential_version_id == credential_id
        )
        if not same_resolution:
            raise RevisionConflict("IDEMPOTENCY_CONFLICT")
        return replay, False

    def safe_read(self, test_run_id):
        run = self.store.get_supplier_model_test_run(test_run_id)
        if run is None:
            raise ModelTestError("MODEL_TEST_NOT_FOUND")
        result = {
            "test_run_id": run["test_run_id"],
            "supplier_model_id": run["supplier_model_id"],
            "capability": run["capability"],
            "status": run["status"],
            "created_at": run["created_at"],
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "error_code": run["error_code"],
            "error_message": run["error_message"],
        }
        if run["normalized_result_object_id"]:
            normalized = self._read_json(run["normalized_result_object_id"])
            if run["capability"] == "text":
                result["output"] = str(normalized.get("output") or "")
                result["usage"] = dict(normalized.get("usage") or {})
        if run["capability"] == "image" and run["status"] == "completed":
            result["media_type"] = run["media_type"]
            result["byte_size"] = run["byte_size"]
        result["elapsed_ms"] = _elapsed_ms(run["started_at"], run["finished_at"])
        return result

    def safe_read_by_key(self, supplier_model_id, idempotency_key):
        run = self.store.get_supplier_model_test_run_by_key(
            supplier_model_id, idempotency_key
        )
        if run is None:
            raise ModelTestError("MODEL_TEST_NOT_FOUND")
        return self.safe_read(run["test_run_id"])

    def _operation_available(self, supplier, operation):
        version = self.store.get_supplier_version(supplier.current_supplier_version_id)
        if version is None:
            raise ModelTestError("SUPPLIER_RUNTIME_UNAVAILABLE")
        try:
            source = self.store.runtime.read_text(version.source_object_id)
        except Exception as exc:
            raise ModelTestError("SUPPLIER_RUNTIME_UNAVAILABLE") from exc
        pattern = re.compile(
            r"\bexport\s+(?:(?:async\s+)?function|const|let|var)\s+"
            + re.escape(operation)
            + r"\b"
        )
        return bool(pattern.search(source))

    def _read_json(self, object_id):
        try:
            value = json.loads(self.store.runtime.read_text(object_id))
        except (OSError, ValueError, TypeError) as exc:
            raise ModelTestError("SUPPLIER_RUNTIME_UNAVAILABLE") from exc
        return value if isinstance(value, dict) else {}


class ModelTestExecutor:
    def __init__(
        self, store, gateway, *, lease_owner="model-test-executor", rate_limiter=None
    ):
        self.store = store
        self.gateway = gateway
        self.lease_owner = lease_owner
        self.rate_limiter = rate_limiter

    def execute(self, test_run_id):
        run = self.store.get_supplier_model_test_run(test_run_id)
        if run is None:
            raise ModelTestError("MODEL_TEST_NOT_FOUND")
        if run["status"] != "queued" or run["attempt_count"] != 0:
            return run
        if self.rate_limiter is not None:
            try:
                bucket = load_snapshot(
                    self.store, run["snapshot_hash"]
                ).rate_limit_bucket_key
            except SupplierRuntimeUnavailable:
                claimed = self.store.claim_supplier_model_test_run(
                    test_run_id,
                    lease_owner=self.lease_owner,
                    lease_expires_at="",
                )
                if claimed is None:
                    return self.store.get_supplier_model_test_run(test_run_id)
                return self.store.fail_supplier_model_test_run(
                    test_run_id,
                    error_code="SUPPLIER_RUNTIME_UNAVAILABLE",
                    error_message="SUPPLIER_RUNTIME_UNAVAILABLE",
                )
            if not self.rate_limiter.acquire(bucket):
                return run
        claimed = self.store.claim_supplier_model_test_run(
            test_run_id,
            lease_owner=self.lease_owner,
            lease_expires_at="",
        )
        if claimed is None:
            return self.store.get_supplier_model_test_run(test_run_id)
        try:
            request = json.loads(self.store.runtime.read_text(claimed["request_object_id"]))
            operation = "textRequest" if claimed["capability"] == "text" else "imageRequest"
            response = self.gateway.invoke(claimed["snapshot_hash"], operation, request)
            return self._complete(claimed, response)
        except Exception as exc:
            code = _error_code(exc)
            unknown = code in AMBIGUOUS_EXECUTION_ERRORS
            final_code = "SUBMISSION_OUTCOME_UNKNOWN" if unknown else code
            evidence_id = self.store.runtime.write_text_object(
                _canonical({"error_code": final_code})
            )
            try:
                return self.store.fail_supplier_model_test_run(
                    test_run_id,
                    error_code=final_code,
                    error_message=final_code,
                    sanitized_evidence_object_id=evidence_id,
                    unknown=unknown,
                )
            except RevisionConflict:
                return self.store.get_supplier_model_test_run(test_run_id)

    def recover_startup(self):
        return {
            "unknown": self.store.mark_interrupted_model_tests_unknown(),
            "queued": len(self.store.list_queued_supplier_model_tests()),
        }

    def drain_queued(self, limit=20):
        selected_buckets = set()
        executed = 0
        for run in self.store.list_queued_supplier_model_tests(limit=limit):
            try:
                bucket = load_snapshot(
                    self.store, run["snapshot_hash"]
                ).rate_limit_bucket_key
            except SupplierRuntimeUnavailable:
                claimed = self.store.claim_supplier_model_test_run(
                    run["test_run_id"],
                    lease_owner=self.lease_owner,
                    lease_expires_at="",
                )
                if claimed:
                    self.store.fail_supplier_model_test_run(
                        run["test_run_id"],
                        error_code="SUPPLIER_RUNTIME_UNAVAILABLE",
                        error_message="SUPPLIER_RUNTIME_UNAVAILABLE",
                    )
                continue
            if self.rate_limiter is None and bucket in selected_buckets:
                continue
            selected_buckets.add(bucket)
            try:
                result = self.execute(run["test_run_id"])
            except Exception:
                continue
            if result is not None and result["status"] != "queued":
                executed += 1
        return executed

    def _complete(self, run, response):
        if not isinstance(response, dict):
            raise ModelTestError("PROVIDER_RESPONSE_MALFORMED")
        safe = sanitize_evidence(
            {key: value for key, value in response.items() if key not in {"bytes", "content"}}
        )
        evidence_id = self.store.runtime.write_text_object(_canonical(safe))
        if run["capability"] == "text":
            if "output" not in response:
                raise ModelTestError("PROVIDER_RESPONSE_MALFORMED")
            normalized = {
                "output": str(response.get("output") or ""),
                "usage": {
                    str(key): int(value)
                    for key, value in dict(response.get("usage") or {}).items()
                    if isinstance(value, (int, float))
                },
            }
            result_id = self.store.runtime.write_text_object(_canonical(normalized))
            return self.store.complete_supplier_model_test_run(
                run["test_run_id"],
                normalized_result_object_id=result_id,
                sanitized_evidence_object_id=evidence_id,
            )
        content = response.get("bytes", response.get("content"))
        if isinstance(content, str):
            content = content.encode("utf-8")
        media_type = str(response.get("media_type") or "")
        if (
            not isinstance(content, bytes)
            or not content
            or not image_bytes_match_media_type(content, media_type)
        ):
            raise ModelTestError("PROVIDER_RESPONSE_MALFORMED")
        if len(content) > 25 * 1024 * 1024:
            raise ModelTestError("SUPPLIER_WORKER_OUTPUT_TOO_LARGE")
        content_id = self.store.runtime.write_bytes_object(content)
        normalized_id = self.store.runtime.write_text_object(
            _canonical({"media_type": media_type, "byte_size": len(content)})
        )
        return self.store.complete_supplier_model_test_run(
            run["test_run_id"],
            normalized_result_object_id=normalized_id,
            sanitized_evidence_object_id=evidence_id,
            content_object_id=content_id,
            media_type=media_type,
            byte_size=len(content),
        )


def _canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _error_code(exc):
    code = str(getattr(exc, "code", "") or str(exc) or "SUPPLIER_EXECUTION_FAILED")
    return code if re.fullmatch(r"[A-Z0-9_]{3,80}", code) else "SUPPLIER_EXECUTION_FAILED"


def _elapsed_ms(started_at, finished_at):
    if not started_at or not finished_at:
        return 0
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, int((finish - start).total_seconds() * 1000))


class ModelTestRunner:
    def __init__(self, data_root, *, poll_interval_seconds=0.25, rate_limiter=None):
        self.data_root = Path(data_root)
        self.poll_interval_seconds = poll_interval_seconds
        self.rate_limiter = rate_limiter
        self._task = None
        self._stop_event = asyncio.Event()
        self._wake_event = asyncio.Event()

    async def start(self):
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._wake_event.set()
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop_event.set()
        self._wake_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def wake(self):
        self._wake_event.set()

    async def _run(self):
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._wake_event.wait(), timeout=self.poll_interval_seconds
                )
            except TimeoutError:
                pass
            self._wake_event.clear()
            if not self._stop_event.is_set():
                try:
                    await asyncio.to_thread(self._drain_once)
                except Exception:
                    continue

    def _drain_once(self):
        from ai_drama_runtime.store import RuntimeStore
        from ai_drama_web.store import ProductStore

        from .credentials import SupplierCredentialStore
        from .execution import SnapshotExecutionGateway

        runtime = RuntimeStore(
            self.data_root / "runtime.db", self.data_root / "objects"
        )
        try:
            store = ProductStore(runtime)
            credentials = SupplierCredentialStore(store, self.data_root)
            gateway = SnapshotExecutionGateway(store, credentials)
            return ModelTestExecutor(
                store, gateway, rate_limiter=self.rate_limiter
            ).drain_queued()
        finally:
            runtime.close()
