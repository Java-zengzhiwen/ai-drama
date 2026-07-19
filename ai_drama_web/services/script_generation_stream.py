from dataclasses import dataclass
import json
from pathlib import Path
import time

from ai_drama_runtime.registry import SkillRegistry
from ai_drama_runtime.request import RuntimeRequest
from ai_drama_runtime.services import PreparedScriptExecution, RuntimeService

from .m6_generation import _normalize_text_request
from .script_workflow import SCRIPT_SKILL_REF
from ..suppliers.adapters import sanitize_evidence


@dataclass(frozen=True)
class ScriptGenerationCycleResult:
    started: int = 0
    completed: int = 0
    failed: int = 0


class ScriptGenerationRunner:
    """Runs one already-durable script stream without ever resubmitting it."""

    def __init__(self, store, runtime_store, *, repo_root, gateway):
        self.store = store
        self.runtime = runtime_store
        self.repo_root = Path(repo_root).resolve()
        self.gateway = gateway
        self.runtime_service = RuntimeService(runtime_store, repo_root=self.repo_root)

    def run_cycle(self):
        session = self.store.next_prepared_script_generation_run()
        if session is None:
            return ScriptGenerationCycleResult()
        claimed = self.store.claim_script_generation_run(session["run_id"])
        if claimed is None:
            return ScriptGenerationCycleResult()
        usage = {}
        try:
            prepared = self._prepared_execution(claimed)
            request = _normalize_text_request(prepared.runtime_request.to_dict())
            for frame in self.gateway.invoke_stream(
                claimed["snapshot_hash"], "textStream", request
            ):
                frame_type = frame["type"]
                if frame_type == "started":
                    self.store.transition_script_generation_run(
                        claimed["run_id"],
                        expected_statuses=("submitting",),
                        status="streaming",
                    )
                elif frame_type == "text_delta":
                    self.store.append_script_generation_event(
                        claimed["run_id"],
                        sequence=frame["sequence"],
                        event_type="text_delta",
                        payload={"text": frame["text"]},
                    )
                elif frame_type == "usage":
                    usage.update(frame["usage"])
                    self.store.append_script_generation_event(
                        claimed["run_id"],
                        sequence=frame["sequence"],
                        event_type="usage",
                        payload={"usage": dict(usage)},
                    )
                elif frame_type == "failed":
                    self._fail(
                        claimed,
                        frame.get("errorCode") or "SUPPLIER_EXECUTION_FAILED",
                        evidence=frame.get("evidence") or {},
                        sequence=frame.get("sequence", 0),
                    )
                    return ScriptGenerationCycleResult(started=1, failed=1)
                elif frame_type == "completed":
                    return self._complete(
                        claimed,
                        prepared,
                        usage,
                        frame,
                    )
            self._fail(claimed, "SUPPLIER_WORKER_PROTOCOL_ERROR")
            return ScriptGenerationCycleResult(started=1, failed=1)
        except Exception as exc:
            self._fail(
                claimed,
                getattr(exc, "code", "SUPPLIER_EXECUTION_FAILED"),
                evidence=getattr(exc, "evidence", {}),
            )
            return ScriptGenerationCycleResult(started=1, failed=1)

    def _prepared_execution(self, session):
        run = self.runtime.get_run(session["runtime_run_id"])
        if run is None or run.status != "RUNNING":
            raise RuntimeError("SCRIPT_RUNTIME_RUN_UNAVAILABLE")
        request = RuntimeRequest(
            json.loads(self.runtime.read_text(run.request_object_id))
        )
        skill = SkillRegistry.scan([self.repo_root / "skills"]).get_ref(
            SCRIPT_SKILL_REF
        )
        if (
            request.payload.get("skill", {}).get("skill_id") != skill.skill_id
            or request.payload.get("skill", {}).get("version") != skill.version
            or request.payload.get("skill", {}).get("package_hash")
            != skill.content_hash
        ):
            raise RuntimeError("SKILL_RUNTIME_UNAVAILABLE")
        return PreparedScriptExecution(
            run_id=run.run_id,
            artifact_id=run.artifact_id,
            project_id=run.project_id,
            chapter_id=run.chapter_id,
            runtime=run.runtime,
            resolved_model=run.model,
            runtime_request=request,
            request_object_id=run.request_object_id,
            skill=skill,
            validation_root=skill.root,
            started_at=time.time(),
        )

    def _complete(self, session, prepared, usage, frame):
        self.store.transition_script_generation_run(
            session["run_id"],
            expected_statuses=("submitting", "streaming"),
            status="finalizing",
        )
        chunks = self.store.list_script_generation_events(
            session["run_id"], after_sequence=0
        )
        output = "".join(
            json.loads(self.runtime.read_text(event["payload_object_id"])).get(
                "text", ""
            )
            for event in chunks
            if event["event_type"] == "text_delta"
        )
        normalized = {"output": output, "usage": dict(usage)}
        result_object_id = self.runtime.write_text_object(
            json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        )
        safe_evidence = sanitize_evidence(frame.get("evidence") or {})
        evidence_object_id = (
            self.runtime.write_text_object(
                json.dumps(safe_evidence, sort_keys=True, separators=(",", ":"))
            )
            if safe_evidence
            else ""
        )
        self.store.complete_supplier_text_run(
            session["supplier_text_run_id"],
            result_object_id=result_object_id,
            evidence_object_id=evidence_object_id,
        )
        result = self.runtime_service.finalize_prepared_script(
            prepared,
            output=output,
            usage=usage,
            provider="supplier",
            model="resolved-by-snapshot",
            duration_ms=int((time.time() - prepared.started_at) * 1000),
        )
        if result.revision is None or result.run.status != "SUCCEEDED":
            self.store.transition_script_generation_run(
                session["run_id"],
                expected_statuses=("finalizing",),
                status="failed",
                error_code=result.run.error_code or result.run.status,
                evidence_object_id=evidence_object_id,
            )
            return ScriptGenerationCycleResult(started=1, failed=1)
        current = self.store.get_script_generation_run(session["run_id"])
        event_sequence = max(int(frame["sequence"]), current["last_sequence"] + 1)
        self.store.append_script_generation_event(
            session["run_id"],
            sequence=event_sequence,
            event_type="revision_completed",
            payload={"revision_id": result.revision.revision_id},
        )
        self.store.transition_script_generation_run(
            session["run_id"],
            expected_statuses=("finalizing",),
            status="completed",
            revision_id=result.revision.revision_id,
            evidence_object_id=evidence_object_id,
        )
        return ScriptGenerationCycleResult(started=1, completed=1)

    def _fail(self, session, error_code, *, evidence=None, sequence=0):
        current = self.store.get_script_generation_run(session["run_id"])
        if current is None or current["status"] in {
            "completed",
            "failed",
            "unknown_outcome",
        }:
            return
        safe_evidence = sanitize_evidence(evidence or {})
        evidence_object_id = (
            self.runtime.write_text_object(
                json.dumps(safe_evidence, sort_keys=True, separators=(",", ":"))
            )
            if safe_evidence
            else ""
        )
        event_sequence = max(int(sequence or 0), current["last_sequence"] + 1)
        try:
            self.store.append_script_generation_event(
                session["run_id"],
                sequence=event_sequence,
                event_type="failed",
                payload={"error_code": str(error_code)},
            )
        except Exception:
            pass
        self.store.fail_supplier_text_run(
            session["supplier_text_run_id"],
            error_code=str(error_code),
            evidence_object_id=evidence_object_id,
        )
        current = self.store.get_script_generation_run(session["run_id"])
        self.store.transition_script_generation_run(
            session["run_id"],
            expected_statuses=(current["status"],),
            status="failed",
            error_code=str(error_code),
            evidence_object_id=evidence_object_id,
        )
