from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
from .store import now_iso

from .acceptance import load_acceptance_bundle
from .parser import PARSER_VERSION, ParseError, parse_script_response
from .request import build_runtime_request
from .runtime import RuntimeErrorBase, run_runtime
from .validators import run_declared_validators


class ApprovalBlocked(RuntimeError):
    pass


class ExportConflict(RuntimeError):
    pass


class NotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class RunResult:
    run: object
    revision: object
    validation_results: list
    adapter_request_json: str = ""


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RuntimeService:
    def __init__(self, store, repo_root=None):
        self.store = store
        self.repo_root = Path(repo_root or Path.cwd()).resolve()

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def run_acceptance(self, skill, acceptance_root, runtime, model, mock_mode="success"):
        bundle = load_acceptance_bundle(acceptance_root)
        artifact_id = bundle.manifest["id"]
        project_id = bundle.manifest.get("project_id") or artifact_id
        chapter_id = bundle.manifest.get("chapter_id") or artifact_id
        self.store.ensure_artifact(artifact_id, "drama_script", project_id, chapter_id)
        resolved_model = model or (os.environ.get("AI_DRAMA_MODEL") if runtime == "openai-compatible" else model)
        runtime_request = build_runtime_request(skill, acceptance_root, runtime, resolved_model or "")
        request_json = runtime_request.to_json()
        request_object_id = self.store.write_text_object(request_json)
        run = self.store.create_run(
            artifact_id=artifact_id,
            project_id=project_id,
            chapter_id=chapter_id,
            skill_id=skill.skill_id,
            skill_version=skill.version,
            skill_hash=skill.content_hash,
            runtime=runtime,
            provider=runtime,
            model=model or "",
            status="RUNNING",
            request_object_id=request_object_id,
            input_hash=runtime_request.sha256,
            request_hash=runtime_request.sha256,
        )
        for key, item in bundle.input_files.items():
            self.store.insert_input_snapshot(
                run.run_id,
                logical_type=key,
                source_relative_path=item.relative_path,
                source_path=item.path,
                text=item.text,
            )
        try:
            response = run_runtime(runtime, runtime_request, mock_mode=mock_mode)
        except RuntimeErrorBase as exc:
            run = self.store.update_run(
                run.run_id,
                status="RUNTIME_FAILED",
                error_code=exc.code,
                error_message=exc.safe_message,
            )
            return RunResult(run=run, revision=None, validation_results=[], adapter_request_json=request_json)

        response_object_id = self.store.write_text_object(response.raw)
        try:
            script_text = parse_script_response(response.raw)
        except ParseError as exc:
            run = self.store.update_run(
                run.run_id,
                status="PARSE_FAILED",
                response_object_id=response_object_id,
                provider=response.provider,
                model=response.model,
                duration_ms=response.duration_ms,
                usage_status=response.usage.get("usage_status", "NOT_PROVIDED"),
                prompt_tokens=int(response.usage.get("prompt_tokens") or 0),
                completion_tokens=int(response.usage.get("completion_tokens") or 0),
                total_tokens=int(response.usage.get("total_tokens") or 0),
                usage_raw_object_id=self.store.write_text_object(json.dumps(response.usage.get("raw") or {}, ensure_ascii=False, sort_keys=True)),
                error_code=exc.code,
                error_message=str(exc),
            )
            return RunResult(run=run, revision=None, validation_results=[], adapter_request_json=request_json)

        content_object_id = self.store.write_text_object(script_text)
        content_hash = _sha256_text(script_text)
        run = self.store.update_run(
            run.run_id,
            status="SUCCEEDED",
            response_object_id=response_object_id,
            provider=response.provider,
            model=response.model,
            duration_ms=response.duration_ms,
            usage_status=response.usage.get("usage_status", "NOT_PROVIDED"),
            prompt_tokens=int(response.usage.get("prompt_tokens") or 0),
            completion_tokens=int(response.usage.get("completion_tokens") or 0),
            total_tokens=int(response.usage.get("total_tokens") or 0),
            usage_raw_object_id=self.store.write_text_object(json.dumps(response.usage.get("raw") or {}, ensure_ascii=False, sort_keys=True)),
        )
        revision = self.store.insert_revision(
            artifact_id=artifact_id,
            artifact_type="drama_script",
            project_id=project_id,
            chapter_id=chapter_id,
            run_id=run.run_id,
            skill_id=skill.skill_id,
            skill_version=skill.version,
            skill_package_hash=skill.content_hash,
            runtime_provider=response.provider,
            runtime_model=response.model,
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=response_object_id,
            parser_version=PARSER_VERSION,
        )
        validations = run_declared_validators(self.store, skill, revision, bundle.root, repo_root=self.repo_root)
        if any(item.required and item.status not in {"PASS", "NOT_APPLICABLE"} for item in validations):
            run = self.store.update_run(run.run_id, status="VALIDATION_FAILED")
        return RunResult(run=run, revision=revision, validation_results=validations, adapter_request_json=request_json)

    def approve_revision(self, revision_id, reviewer, note=""):
        revision = self._revision_or_raise(revision_id)
        run = self.store.get_run(revision.run_id)
        if run.status not in {"SUCCEEDED", "VALIDATION_FAILED"}:
            raise ApprovalBlocked("run status does not allow approval: %s" % run.status)
        if not self.store.read_text(revision.content_object_id).strip():
            raise ApprovalBlocked("revision content is empty")
        results = self.store.validation_results(revision_id)
        required = [item for item in results if item.required]
        if not required:
            raise ApprovalBlocked("missing required validator result")
        blocking = [item for item in required if item.status not in {"PASS", "NOT_APPLICABLE"}]
        if blocking:
            raise ApprovalBlocked("required validators did not pass: %s" % ", ".join(item.validator_id for item in blocking))
        self.store.approve_in_transaction(revision, reviewer, note)
        return self.store.get_revision(revision_id)

    def reject_revision(self, revision_id, reviewer, note=""):
        revision = self._revision_or_raise(revision_id)
        self.store.record_rejection(revision, reviewer, note)
        return self.store.get_revision(revision_id)

    def current_approved(self, artifact_id):
        revision = self.store.current_approved(artifact_id)
        if revision is None:
            raise NotFound("no approved revision for artifact %s" % artifact_id)
        return revision

    def compare_revisions(self, left_revision_id, right_revision_id):
        left = self._revision_or_raise(left_revision_id)
        right = self._revision_or_raise(right_revision_id)
        metadata = {
            "skill": [left.skill_id, right.skill_id],
            "version": [left.skill_version, right.skill_version],
            "package_hash": [left.skill_package_hash, right.skill_package_hash],
            "provider": [left.runtime_provider, right.runtime_provider],
            "model": [left.runtime_model, right.runtime_model],
            "content_hash": [left.content_hash, right.content_hash],
            "approval_status": [left.approval_status, right.approval_status],
            "request_hash": [
                self.store.get_run(left.run_id).request_hash,
                self.store.get_run(right.run_id).request_hash,
            ],
            "input_refs": [
                {item.logical_type: item.source_relative_path for item in self.store.input_snapshots(left.run_id)},
                {item.logical_type: item.source_relative_path for item in self.store.input_snapshots(right.run_id)},
            ],
            "input_hashes": [
                {item.logical_type: item.sha256 for item in self.store.input_snapshots(left.run_id)},
                {item.logical_type: item.sha256 for item in self.store.input_snapshots(right.run_id)},
            ],
            "validator_status": [
                {item.validator_id: item.status for item in self.store.validation_results(left.revision_id)},
                {item.validator_id: item.status for item in self.store.validation_results(right.revision_id)},
            ],
        }
        left_text = self.store.read_text(left.content_object_id).splitlines(keepends=True)
        right_text = self.store.read_text(right.content_object_id).splitlines(keepends=True)
        return "metadata:\n%s\ninput_hash_diff:\n%s\nrequest_hash_diff:\n%s\nvalidator_status:\n%s\ntext_diff:\n%s" % (
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(metadata["input_hashes"], ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(metadata["request_hash"], ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(metadata["validator_status"], ensure_ascii=False, indent=2, sort_keys=True),
            "".join(difflib.unified_diff(left_text, right_text, fromfile=left.revision_id, tofile=right.revision_id)),
        )

    def export_approved(self, artifact_id, output, force=False):
        revision = self.current_approved(artifact_id)
        output = Path(output)
        sidecar = output.with_name(output.name + ".provenance.json")
        if not force and (output.exists() or sidecar.exists()):
            raise ExportConflict("output or provenance sidecar exists; use --force")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.store.read_text(revision.content_object_id), encoding="utf-8")
        approval = self.store.latest_approval(revision.revision_id)
        run = self.store.get_run(revision.run_id)
        inputs = [
            {
                "logical_type": item.logical_type,
                "relative_path": item.source_relative_path,
                "sha256": item.sha256,
            }
            for item in self.store.input_snapshots(revision.run_id)
        ]
        provenance = {
            "artifact_id": artifact_id,
            "revision_id": revision.revision_id,
            "run_id": revision.run_id,
            "skill_id": revision.skill_id,
            "skill_version": revision.skill_version,
            "package_hash": revision.skill_package_hash,
            "provider": revision.runtime_provider,
            "model": revision.runtime_model,
            "content_hash": revision.content_hash,
            "input_references": inputs,
            "request_hash": run.request_hash,
            "approval_record": approval.__dict__ if approval else None,
            "export_time": now_iso(),
        }
        sidecar_text = json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        provenance_object_id = self.store.write_text_object(sidecar_text)
        sidecar.write_text(sidecar_text, encoding="utf-8")
        return self.store.record_export(
            artifact_id=artifact_id,
            revision_id=revision.revision_id,
            run_id=revision.run_id,
            content_hash=revision.content_hash,
            destination=str(output),
            provenance_object_id=provenance_object_id,
        )

    def _revision_or_raise(self, revision_id):
        revision = self.store.get_revision(revision_id)
        if revision is None:
            raise NotFound("revision not found: %s" % revision_id)
        return revision
