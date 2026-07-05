from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import uuid
from .store import now_iso

from .acceptance import load_acceptance_bundle
from .parser import (
    PARSER_VERSION,
    STORYBOARD_CANONICAL_PARSER_VERSION,
    STORYBOARD_PARSER_VERSION,
    ParseError,
    parse_script_response,
    parse_storyboard_canonical_response,
    parse_storyboard_response,
)
from .request import build_runtime_request, build_runtime_request_from_inputs, build_storyboard_runtime_request
from .runtime import RuntimeErrorBase, run_runtime
from .validators import recursive_freshness_status, run_declared_validators
from .storyboard_canonical import CONTENT_PROFILE as STORYBOARD_CANONICAL_PROFILE, canonical_storyboard_hash, parse_canonical_json, serialize_canonical_json
from .storyboard_migration import StoryboardMigrationError, legacy_markdown_to_canonical, write_migration_preview
from .storyboard_renderer import RENDERER_ID, RENDERER_VERSION, render_storyboard_markdown


class ApprovalBlocked(RuntimeError):
    pass


class ExportConflict(RuntimeError):
    pass


class BundleError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.safe_message = message


class BundleExportError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.safe_message = message


class BundleApprovalBlocked(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.safe_message = message


class DiagnosticParentError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.safe_message = message


class NotFound(RuntimeError):
    pass


class WorkflowGateError(RuntimeError):
    def __init__(self, code, message, target_artifact_id="", source_revision_id="", request_reference=""):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.target_artifact_id = target_artifact_id
        self.source_revision_id = source_revision_id
        self.request_reference = request_reference


def _gate_failure(store, *, run_id="", skill=None, target_artifact_id="", source_revision_id="", error_code="", error_message="", request_reference=""):
    if skill is not None:
        store.insert_workflow_gate_record(
            run_id=run_id,
            target_skill_id=skill.skill_id,
            target_skill_version=skill.version,
            target_artifact_id=target_artifact_id,
            source_revision_id=source_revision_id,
            request_reference=request_reference,
            error_code=error_code,
            error_message=error_message,
        )


@dataclass(frozen=True)
class RunResult:
    run: object
    revision: object
    validation_results: list
    adapter_request_json: str = ""


def _approved_approval_record(store, revision_id):
    approval = store.latest_approval(revision_id)
    return approval.__dict__ if approval else {}


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _skill_profile_id(skill):
    return ((skill.metadata.get("execution_profiles") or [{}])[0]).get("profile_id", "")


def _required_input_types(skill):
    return list(skill.input_types)


def _validate_skill_input_mode(skill, provided_mode):
    if not provided_mode:
        raise WorkflowGateError("INPUT_MODE_REQUIRED", "input mode is required")
    required = _required_input_types(skill)
    if provided_mode == "input":
        if "source_chapter" not in required:
            raise WorkflowGateError("SKILL_INPUT_TYPE_MISMATCH", "skill expects --source-revision")
        return "source_chapter"
    if provided_mode == "source_revision":
        if "approved_script_revision" not in required:
            raise WorkflowGateError("SKILL_INPUT_TYPE_MISMATCH", "skill expects --input")
        return "approved_script_revision"
    raise WorkflowGateError("INPUT_MODE_CONFLICT", "input mode is invalid")


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

    def _sha256_bytes(self, data):
        return hashlib.sha256(data).hexdigest()

    def _canonical_json_v1_bytes(self, value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def _rendered_markdown_output(self, canonical):
        data = render_storyboard_markdown(canonical).encode("utf-8")
        return {
            "logical_type": "rendered_markdown",
            "bytes": data,
            "content_hash": self._sha256_bytes(data),
            "media_type": "text/markdown",
            "generator": RENDERER_ID,
            "generator_version": RENDERER_VERSION,
        }

    def _build_storyboard_bundle_manifest(self, *, revision_id, canonical_content_hash, rendered_markdown_hash):
        output = {
            "logical_type": "rendered_markdown",
            "content_hash": rendered_markdown_hash,
            "media_type": "text/markdown",
            "generator": RENDERER_ID,
            "generator_version": RENDERER_VERSION,
        }
        business_preimage = {
            "schema_version": "bundle-manifest-v1",
            "artifact_type": "storyboard",
            "canonical_content_hash": canonical_content_hash,
            "outputs": [output],
        }
        bundle_manifest_hash = self._sha256_bytes(self._canonical_json_v1_bytes(business_preimage))
        manifest = {
            "schema_version": "bundle-manifest-v1",
            "revision_id": revision_id,
            "artifact_type": "storyboard",
            "canonical_content_hash": canonical_content_hash,
            "outputs": [output],
            "bundle_manifest_hash": bundle_manifest_hash,
        }
        data = self._canonical_json_v1_bytes(manifest)
        return {
            "logical_type": "bundle_manifest",
            "bytes": data,
            "content_hash": self._sha256_bytes(data),
            "media_type": "application/json",
            "generator": "bundle-manifest-builder",
            "generator_version": "1",
            "business_preimage": business_preimage,
            "bundle_manifest_hash": bundle_manifest_hash,
            "manifest": manifest,
        }

    def _storyboard_bundle_payloads(self, revision):
        canonical = parse_canonical_json(self.store.read_text(revision.content_object_id))
        rendered = self._rendered_markdown_output(canonical)
        manifest = self._build_storyboard_bundle_manifest(
            revision_id=revision.revision_id,
            canonical_content_hash=revision.content_hash,
            rendered_markdown_hash=rendered["content_hash"],
        )
        return rendered, manifest

    def _materialized_bundle_response(self, revision, status, outputs):
        by_type = {item.logical_type: item for item in outputs}
        manifest = json.loads(self.store.read_text(by_type["bundle_manifest"].object_id))
        integrity = self.check_storyboard_bundle_integrity(revision.revision_id)
        return {
            "status": status,
            "revision_id": revision.revision_id,
            "rendered_markdown_output_id": by_type["rendered_markdown"].revision_output_id,
            "bundle_manifest_output_id": by_type["bundle_manifest"].revision_output_id,
            "bundle_manifest_hash": manifest["bundle_manifest_hash"],
            "bundle_integrity": integrity["status"],
            "approval_status": revision.approval_status,
        }

    def _bundle_output_map_or_raise(self, revision_id):
        outputs = self.store.revision_outputs(revision_id)
        if not outputs:
            raise BundleError("BUNDLE_NOT_MATERIALIZED", "Storyboard bundle is not materialized")
        by_type = {item.logical_type: item for item in outputs}
        if len(outputs) != len(by_type) or set(by_type) != {"rendered_markdown", "bundle_manifest"}:
            raise BundleError("REVISION_OUTPUT_COMBINATION_INVALID", "Storyboard revision output combination is invalid")
        return by_type

    def check_storyboard_bundle_integrity(self, revision_id):
        revision = self._revision_or_raise(revision_id)
        if revision.artifact_type != "storyboard" or revision.content_profile != STORYBOARD_CANONICAL_PROFILE:
            raise BundleError("BUNDLE_PROFILE_UNSUPPORTED", "revision does not use the Storyboard canonical bundle profile")
        by_type = self._bundle_output_map_or_raise(revision.revision_id)
        output_bytes = {}
        for output in by_type.values():
            try:
                data = self.store.read_bytes_object(output.object_id)
            except (FileNotFoundError, RuntimeError) as exc:
                raise BundleError("REVISION_OUTPUT_HASH_MISMATCH", "revision output object is missing") from exc
            actual = self._sha256_bytes(data)
            if actual != output.object_id or actual != output.content_hash:
                raise BundleError("REVISION_OUTPUT_HASH_MISMATCH", "revision output hash does not match exact bytes")
            output_bytes[output.logical_type] = data

        canonical = parse_canonical_json(self.store.read_text(revision.content_object_id))
        expected_rendered = self._rendered_markdown_output(canonical)
        rendered = by_type["rendered_markdown"]
        if (
            rendered.media_type != expected_rendered["media_type"]
            or rendered.generator != expected_rendered["generator"]
            or rendered.generator_version != expected_rendered["generator_version"]
            or output_bytes["rendered_markdown"] != expected_rendered["bytes"]
        ):
            raise BundleError("BUNDLE_INTEGRITY_FAILED", "rendered Markdown output does not match frozen renderer contract")

        manifest_output = by_type["bundle_manifest"]
        if (
            manifest_output.media_type != "application/json"
            or manifest_output.generator != "bundle-manifest-builder"
            or manifest_output.generator_version != "1"
        ):
            raise BundleError("BUNDLE_INTEGRITY_FAILED", "bundle manifest metadata does not match frozen contract")
        try:
            manifest = json.loads(output_bytes["bundle_manifest"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleError("BUNDLE_INTEGRITY_FAILED", "bundle manifest is not valid canonical JSON") from exc
        expected_manifest = self._build_storyboard_bundle_manifest(
            revision_id=revision.revision_id,
            canonical_content_hash=revision.content_hash,
            rendered_markdown_hash=rendered.content_hash,
        )
        if manifest != expected_manifest["manifest"]:
            raise BundleError("BUNDLE_INTEGRITY_FAILED", "bundle manifest contents do not match frozen contract")
        if output_bytes["bundle_manifest"] != expected_manifest["bytes"]:
            raise BundleError("BUNDLE_INTEGRITY_FAILED", "bundle manifest bytes are not canonical-json-v1")
        return {
            "status": "PASS",
            "revision_id": revision.revision_id,
            "bundle_manifest_hash": expected_manifest["bundle_manifest_hash"],
        }

    def _bundle_integrity_failure_code(self, code):
        if code == "BUNDLE_NOT_MATERIALIZED":
            return code
        return "BUNDLE_INTEGRITY_FAILED"

    def _normalize_bundle_integrity_error(self, exc):
        if exc.code == "BUNDLE_NOT_MATERIALIZED":
            return exc
        return BundleError("BUNDLE_INTEGRITY_FAILED", exc.safe_message)

    def bundle_outputs(self, revision_id):
        revision = self._revision_or_raise(revision_id)
        if revision.artifact_type != "storyboard" or revision.content_profile != STORYBOARD_CANONICAL_PROFILE:
            raise BundleError("BUNDLE_PROFILE_UNSUPPORTED", "revision does not use the Storyboard canonical bundle profile")
        outputs = self.store.revision_outputs(revision.revision_id)
        materialization_status = "NOT_MATERIALIZED"
        bundle_integrity = "NOT_CHECKED"
        bundle_manifest_hash = ""
        if outputs:
            types = {item.logical_type for item in outputs}
            if types == {"rendered_markdown", "bundle_manifest"} and len(outputs) == 2:
                materialization_status = "MATERIALIZED"
                try:
                    integrity = self.check_storyboard_bundle_integrity(revision.revision_id)
                    bundle_integrity = "PASS"
                    bundle_manifest_hash = integrity["bundle_manifest_hash"]
                except BundleError:
                    bundle_integrity = "FAIL"
            else:
                materialization_status = "CONFLICT"
                bundle_integrity = "FAIL"
        return {
            "revision_id": revision.revision_id,
            "artifact_type": revision.artifact_type,
            "content_profile": revision.content_profile,
            "materialization_status": materialization_status,
            "bundle_integrity": bundle_integrity,
            "bundle_manifest_hash": bundle_manifest_hash,
            "outputs": [
                {
                    "revision_output_id": item.revision_output_id,
                    "logical_type": item.logical_type,
                    "object_id": item.object_id,
                    "content_hash": item.content_hash,
                    "media_type": item.media_type,
                    "generator": item.generator,
                    "generator_version": item.generator_version,
                    "created_at": item.created_at,
                }
                for item in outputs
            ],
        }

    def materialize_storyboard_bundle(self, revision_id):
        revision = self._revision_or_raise(revision_id)
        if revision.artifact_type != "storyboard" or revision.content_profile != STORYBOARD_CANONICAL_PROFILE:
            raise BundleError("BUNDLE_PROFILE_UNSUPPORTED", "revision does not use the Storyboard canonical bundle profile")
        existing = self.store.revision_outputs(revision.revision_id)
        existing_types = {item.logical_type for item in existing}
        if existing_types == {"rendered_markdown", "bundle_manifest"} and len(existing) == 2:
            return self._materialized_bundle_response(revision, "ALREADY_MATERIALIZED", existing)
        if existing:
            raise BundleError("BUNDLE_OUTPUT_CONFLICT", "revision outputs are partial or conflicting")

        rendered, manifest = self._storyboard_bundle_payloads(revision)
        rendered_object_id = self.store.write_bytes_object(rendered["bytes"])
        manifest_object_id = self.store.write_bytes_object(manifest["bytes"])
        rows = [
            {
                "revision_id": revision.revision_id,
                "logical_type": rendered["logical_type"],
                "object_id": rendered_object_id,
                "content_hash": rendered["content_hash"],
                "media_type": rendered["media_type"],
                "generator": rendered["generator"],
                "generator_version": rendered["generator_version"],
            },
            {
                "revision_id": revision.revision_id,
                "logical_type": manifest["logical_type"],
                "object_id": manifest_object_id,
                "content_hash": manifest["content_hash"],
                "media_type": manifest["media_type"],
                "generator": manifest["generator"],
                "generator_version": manifest["generator_version"],
            },
        ]
        with self.store.conn:
            outputs = self.store.insert_revision_outputs_transaction(rows)
        return self._materialized_bundle_response(revision, "MATERIALIZED", outputs)

    def _bundle_export_payloads(self, revision):
        by_type = self._bundle_output_map_or_raise(revision.revision_id)
        integrity = self.check_storyboard_bundle_integrity(revision.revision_id)
        return by_type, integrity

    def _export_provenance(self, *, export_id, export_kind, revision, bundle_manifest_hash, bundle_status, freshness_status, diagnostic_only, destination, error_code=""):
        return {
            "schema_version": "export-provenance-v1",
            "export_id": export_id,
            "export_kind": export_kind,
            "artifact_id": revision.artifact_id,
            "revision_id": revision.revision_id,
            "canonical_content_hash": revision.content_hash,
            "bundle_manifest_hash": bundle_manifest_hash,
            "bundle_status": bundle_status,
            "freshness_status": freshness_status,
            "diagnostic_only": diagnostic_only,
            "not_an_execution_package": True,
            "execution_ready": False,
            "requested_destination": str(destination),
            "export_time": now_iso(),
            "error_code": error_code,
        }

    def _write_bundle_export_files(self, revision, by_type, provenance, staging):
        staging = Path(staging)
        canonical_bytes = self.store.read_bytes_object(revision.content_object_id)
        markdown_bytes = self.store.read_bytes_object(by_type["rendered_markdown"].object_id)
        provenance_bytes = self._canonical_json_v1_bytes(provenance)
        manifest_bytes = self.store.read_bytes_object(by_type["bundle_manifest"].object_id)
        staging.joinpath("canonical-content.json").write_bytes(canonical_bytes)
        staging.joinpath("rendered-markdown.md").write_bytes(markdown_bytes)
        staging.joinpath("export-provenance.json").write_bytes(provenance_bytes)
        staging.joinpath("bundle-manifest.json").write_bytes(manifest_bytes)
        if staging.joinpath("canonical-content.json").read_bytes() != canonical_bytes:
            raise BundleExportError("BUNDLE_INTEGRITY_FAILED", "canonical export bytes changed during write")
        if staging.joinpath("rendered-markdown.md").read_bytes() != markdown_bytes:
            raise BundleExportError("BUNDLE_INTEGRITY_FAILED", "rendered Markdown export bytes changed during write")
        if staging.joinpath("export-provenance.json").read_bytes() != provenance_bytes:
            raise BundleExportError("BUNDLE_INTEGRITY_FAILED", "export provenance bytes changed during write")
        if staging.joinpath("bundle-manifest.json").read_bytes() != manifest_bytes:
            raise BundleExportError("BUNDLE_INTEGRITY_FAILED", "bundle manifest export bytes changed during write")
        return provenance_bytes

    def _commit_export_transaction(self):
        self.store.conn.commit()

    def _atomic_successful_bundle_export(self, *, revision, output, by_type, integrity, export_kind, freshness, diagnostic_only):
        output = Path(output)
        if output.exists():
            raise BundleExportError("EXPORT_DESTINATION_EXISTS", "export destination already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.parent / (".%s.%s.staging" % (output.name, uuid.uuid4().hex))
        staging.mkdir()
        export_id = uuid.uuid4().hex
        provenance = self._export_provenance(
            export_id=export_id,
            export_kind=export_kind,
            revision=revision,
            bundle_manifest_hash=integrity["bundle_manifest_hash"],
            bundle_status="verified",
            freshness_status=freshness,
            diagnostic_only=diagnostic_only,
            destination=output,
        )
        final_exists = False
        try:
            provenance_bytes = self._write_bundle_export_files(revision, by_type, provenance, staging)
            provenance_object_id = self.store.write_bytes_object(provenance_bytes)
            self.store.conn.execute("BEGIN")
            export = self.store.insert_export_record_in_transaction(
                export_id=export_id,
                artifact_id=revision.artifact_id,
                revision_id=revision.revision_id,
                run_id=revision.run_id,
                content_hash=revision.content_hash,
                destination=str(output),
                provenance_object_id=provenance_object_id,
                export_kind=export_kind,
                freshness_status=freshness,
                diagnostic_only=1 if diagnostic_only else 0,
                not_an_execution_package=1,
                execution_ready=0,
                bundle_manifest_hash=integrity["bundle_manifest_hash"],
                error_code="",
            )
            os.replace(staging, output)
            final_exists = True
            self._commit_export_transaction()
        except Exception as exc:
            try:
                self.store.conn.rollback()
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
                if final_exists and output.exists():
                    shutil.rmtree(output)
            if isinstance(exc, BundleExportError):
                raise
            raise BundleExportError("FORMAL_REVIEW_EXPORT_BLOCKED", str(exc)) from exc
        return {
            "status": "EXPORTED",
            "export_id": export.export_id,
            "revision_id": revision.revision_id,
            "export_kind": export_kind,
            "destination": str(output),
            "bundle_manifest_hash": integrity["bundle_manifest_hash"],
            "freshness_status": freshness,
            "diagnostic_only": diagnostic_only,
            "not_an_execution_package": True,
            "execution_ready": False,
        }

    def _export_storyboard_formal_review(self, revision, output):
        try:
            by_type, integrity = self._bundle_export_payloads(revision)
        except BundleError as exc:
            raise BundleError(self._bundle_integrity_failure_code(exc.code), exc.safe_message) from exc
        freshness = self.revision_freshness(revision.revision_id)
        results = self.store.validation_results(revision.revision_id)
        blocking = [
            item
            for item in results
            if item.required and item.validator_id != "storyboard_bundle_integrity" and item.status != "PASS"
        ]
        if revision.approval_status != "approved" or freshness != "FRESH" or blocking:
            raise BundleExportError("FORMAL_REVIEW_EXPORT_BLOCKED", "formal-review export gates did not pass")
        return self._atomic_successful_bundle_export(
            revision=revision,
            output=output,
            by_type=by_type,
            integrity=integrity,
            export_kind="formal_review",
            freshness=freshness,
            diagnostic_only=False,
        )

    def _export_storyboard_diagnostic(self, revision, output):
        try:
            by_type, integrity = self._bundle_export_payloads(revision)
        except BundleError as exc:
            raise BundleError(self._bundle_integrity_failure_code(exc.code), exc.safe_message) from exc
        freshness = self.revision_freshness(revision.revision_id)
        if freshness != "STALE":
            raise BundleExportError("DIAGNOSTIC_EXPORT_REQUIRES_STALE", "diagnostic export requires a STALE revision")
        return self._atomic_successful_bundle_export(
            revision=revision,
            output=output,
            by_type=by_type,
            integrity=integrity,
            export_kind="diagnostic",
            freshness=freshness,
            diagnostic_only=True,
        )

    def _execution_bundle_status(self, revision):
        try:
            integrity = self.check_storyboard_bundle_integrity(revision.revision_id)
            return "verified", integrity["bundle_manifest_hash"]
        except BundleError as exc:
            if exc.code == "BUNDLE_NOT_MATERIALIZED":
                return "not_materialized", ""
            if exc.code == "REVISION_OUTPUT_HASH_MISMATCH":
                return "invalid", ""
            return "invalid", ""

    def _record_storyboard_execution_block(self, revision, output):
        bundle_status, bundle_manifest_hash = self._execution_bundle_status(revision)
        export_id = uuid.uuid4().hex
        provenance = self._export_provenance(
            export_id=export_id,
            export_kind="execution",
            revision=revision,
            bundle_manifest_hash=bundle_manifest_hash,
            bundle_status=bundle_status,
            freshness_status="",
            diagnostic_only=False,
            destination=output,
            error_code="EXPORT_NOT_EXECUTION_READY",
        )
        provenance_object_id = self.store.write_bytes_object(self._canonical_json_v1_bytes(provenance))
        export = self.store.insert_export_record(
            export_id=export_id,
            artifact_id=revision.artifact_id,
            revision_id=revision.revision_id,
            run_id=revision.run_id,
            content_hash=revision.content_hash,
            destination=str(output),
            provenance_object_id=provenance_object_id,
            export_kind="execution",
            freshness_status="",
            diagnostic_only=0,
            not_an_execution_package=1,
            execution_ready=0,
            bundle_manifest_hash=bundle_manifest_hash,
            error_code="EXPORT_NOT_EXECUTION_READY",
        )
        return {
            "status": "BLOCKED",
            "export_id": export.export_id,
            "revision_id": revision.revision_id,
            "export_kind": "execution",
            "bundle_status": bundle_status,
            "bundle_manifest_hash": bundle_manifest_hash,
            "error_code": "EXPORT_NOT_EXECUTION_READY",
            "error_message": "Storyboard bundle export is not execution-ready in Phase 2",
        }

    def export_storyboard_bundle(self, revision_id, export_kind, output):
        revision = self._revision_or_raise(revision_id)
        if revision.artifact_type != "storyboard" or revision.content_profile != STORYBOARD_CANONICAL_PROFILE:
            raise BundleError("BUNDLE_PROFILE_UNSUPPORTED", "revision does not use the Storyboard canonical bundle profile")
        normalized = export_kind.replace("_", "-")
        if normalized == "formal-review":
            return self._export_storyboard_formal_review(revision, output)
        if normalized == "diagnostic":
            return self._export_storyboard_diagnostic(revision, output)
        if normalized == "execution":
            return self._record_storyboard_execution_block(revision, output)
        raise BundleExportError("EXPORT_NOT_EXECUTION_READY", "unsupported bundle export kind")

    def attach_export_dependency(self, child_revision_id, parent_export_id, relation_type):
        export = self.store.get_export_record(parent_export_id)
        if export is None:
            raise NotFound("export not found: %s" % parent_export_id)
        if export.export_kind == "diagnostic":
            raise DiagnosticParentError("DIAGNOSTIC_EXPORT_NOT_PARENTABLE", "diagnostic exports cannot be dependency parents")
        return self.store.insert_revision_dependency(
            child_revision_id=child_revision_id,
            parent_revision_id=export.revision_id,
            relation_type=relation_type,
            parent_content_hash=export.content_hash,
            parent_approval_record_id="",
        )

    def _execute_script_request(
        self,
        *,
        skill,
        artifact_id,
        project_id,
        chapter_id,
        runtime,
        resolved_model,
        runtime_request,
        input_snapshots,
        validation_root,
        started,
        mock_mode,
    ):
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
            model=resolved_model or "",
            status="RUNNING",
            request_object_id=request_object_id,
            input_hash=runtime_request.sha256,
            request_hash=runtime_request.sha256,
        )
        for item in input_snapshots:
            self.store.insert_input_snapshot(
                run.run_id,
                logical_type=item["logical_type"],
                source_relative_path=item["source_relative_path"],
                source_path=item["source_path"],
                text=item["text"],
            )
        try:
            response = run_runtime(runtime_request, mock_mode=mock_mode)
        except RuntimeErrorBase as exc:
            run = self.store.update_run(
                run.run_id,
                status="RUNTIME_FAILED",
                provider=runtime,
                model=resolved_model or "",
                duration_ms=int((time.time() - started) * 1000),
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
        validations = run_declared_validators(self.store, skill, revision, validation_root, repo_root=self.repo_root)
        blocking = [item for item in validations if item.required and item.status not in {"PASS"}]
        if blocking:
            validator_ids = ", ".join(item.validator_id for item in blocking)
            run = self.store.update_run(
                run.run_id,
                status="VALIDATION_FAILED",
                error_code="VALIDATION_REQUIRED_FAILED",
                error_message="required validators did not pass: %s" % validator_ids,
            )
        return RunResult(run=run, revision=revision, validation_results=validations, adapter_request_json=request_json)

    def run_acceptance(self, skill, acceptance_root, runtime, model, mock_mode="success"):
        _validate_skill_input_mode(skill, "input")
        started = time.time()
        bundle = load_acceptance_bundle(acceptance_root)
        artifact_id = bundle.manifest["id"]
        project_id = bundle.manifest.get("project_id") or artifact_id
        chapter_id = bundle.manifest.get("chapter_id") or artifact_id
        self.store.ensure_artifact(artifact_id, "drama_script", project_id, chapter_id)
        resolved_model = model or (os.environ.get("AI_DRAMA_MODEL") if runtime == "openai-compatible" else model)
        runtime_request = build_runtime_request(skill, acceptance_root, runtime, resolved_model or "")
        return self._execute_script_request(
            skill=skill,
            artifact_id=artifact_id,
            project_id=project_id,
            chapter_id=chapter_id,
            runtime=runtime,
            resolved_model=resolved_model or "",
            runtime_request=runtime_request,
            input_snapshots=[
                {
                    "logical_type": key,
                    "source_relative_path": item.relative_path,
                    "source_path": item.path,
                    "text": item.text,
                }
                for key, item in bundle.input_files.items()
            ],
            validation_root=bundle.root,
            started=started,
            mock_mode=mock_mode,
        )

    def run_script_inputs(self, skill, artifact_id, project_id, chapter_id, inputs, runtime, model, mock_mode="success"):
        _validate_skill_input_mode(skill, "input")
        started = time.time()
        self.store.ensure_artifact(artifact_id, "drama_script", project_id, chapter_id)
        resolved_model = model or (os.environ.get("AI_DRAMA_MODEL") if runtime == "openai-compatible" else model)
        runtime_request = build_runtime_request_from_inputs(skill, inputs, runtime, resolved_model or "")
        return self._execute_script_request(
            skill=skill,
            artifact_id=artifact_id,
            project_id=project_id,
            chapter_id=chapter_id,
            runtime=runtime,
            resolved_model=resolved_model or "",
            runtime_request=runtime_request,
            input_snapshots=[
                {
                    "logical_type": logical_type,
                    "source_relative_path": "web-inputs/%s.md" % logical_type,
                    "source_path": Path("web-inputs/%s.md" % logical_type),
                    "text": text,
                }
                for logical_type, text in sorted(inputs.items())
            ],
            validation_root=skill.root,
            started=started,
            mock_mode=mock_mode,
        )

    def create_manual_revision(self, source_revision_id, content, actor="local-user"):
        source = self._revision_or_raise(source_revision_id)
        provider = actor or "local-user"
        source_dependencies = self.store.revision_dependencies(source.revision_id)
        if source.artifact_type == "storyboard" and source.content_profile == STORYBOARD_CANONICAL_PROFILE:
            canonical = parse_canonical_json(content)
            if not source_dependencies:
                raise ValueError("storyboard source dependency is missing")
            parent = self._revision_or_raise(source_dependencies[0].parent_revision_id)
            expected_source = {
                "script_artifact_id": parent.artifact_id,
                "script_revision_id": parent.revision_id,
                "script_content_hash": parent.content_hash,
            }
            if canonical.get("source") != expected_source:
                raise ValueError("storyboard source metadata does not match stored dependency")
            content = serialize_canonical_json(canonical).decode("utf-8")
            content_hash = canonical_storyboard_hash(canonical)
        else:
            content_hash = _sha256_text(content)
        content_object_id = self.store.write_text_object(content)
        request_object_id = self.store.write_text_object(
            json.dumps(
                {
                    "manual_edit": {
                        "source_revision_id": source.revision_id,
                        "actor": provider,
                    }
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        response_object_id = self.store.write_text_object(content)
        run = self.store.create_run(
            artifact_id=source.artifact_id,
            project_id=source.project_id,
            chapter_id=source.chapter_id,
            skill_id="manual-editor",
            skill_version="1",
            skill_hash="",
            runtime="manual",
            provider=provider,
            model="manual-edit",
            status="SUCCEEDED",
            request_object_id=request_object_id,
            response_object_id=response_object_id,
            input_hash=content_hash,
            request_hash=content_hash,
            duration_ms=0,
        )
        revision = self.store.insert_revision(
            artifact_id=source.artifact_id,
            artifact_type=source.artifact_type,
            project_id=source.project_id,
            chapter_id=source.chapter_id,
            run_id=run.run_id,
            skill_id="manual-editor",
            skill_version="1",
            skill_package_hash="",
            runtime_provider="manual",
            runtime_model="manual-edit",
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=response_object_id,
            parser_version=source.parser_version,
            content_profile=source.content_profile,
            derivation_type="manual_edit",
            supersedes_revision_id=source.revision_id,
        )
        for dep in source_dependencies:
            self.store.insert_revision_dependency(
                child_revision_id=revision.revision_id,
                parent_revision_id=dep.parent_revision_id,
                relation_type=dep.relation_type,
                parent_content_hash=dep.parent_content_hash,
                parent_approval_record_id=dep.parent_approval_record_id,
            )
        return revision

    def run_storyboard(self, skill, source_revision_id, runtime, model, mock_mode="success"):
        _validate_skill_input_mode(skill, "source_revision")
        started = time.time()
        source_revision = self.store.get_revision(source_revision_id)
        if source_revision is None:
            _gate_failure(self.store, skill=skill, target_artifact_id="", source_revision_id=source_revision_id, error_code="SOURCE_REVISION_NOT_FOUND", error_message="source revision not found", request_reference=source_revision_id)
            raise WorkflowGateError("SOURCE_REVISION_NOT_FOUND", "source revision not found", request_reference=source_revision_id)
        if source_revision.artifact_type != "drama_script":
            _gate_failure(self.store, skill=skill, target_artifact_id=source_revision.artifact_id, source_revision_id=source_revision_id, error_code="SOURCE_ARTIFACT_TYPE_INVALID", error_message="source revision is not a drama script", request_reference=source_revision_id)
            raise WorkflowGateError("SOURCE_ARTIFACT_TYPE_INVALID", "source revision is not a drama script", source_revision.artifact_id, source_revision_id, source_revision_id)
        source_run = self.store.get_run(source_revision.run_id)
        snapshots = {item.logical_type: item for item in self.store.input_snapshots(source_revision.run_id)}
        required_inputs = ("series_canon", "characters", "production_brief")
        missing_context = [item for item in required_inputs if item not in snapshots]
        if missing_context:
            _gate_failure(self.store, skill=skill, target_artifact_id=source_revision.artifact_id, source_revision_id=source_revision_id, error_code="SOURCE_CONTEXT_MISSING", error_message="missing inherited context: %s" % ",".join(missing_context), request_reference=source_revision_id)
            raise WorkflowGateError("SOURCE_CONTEXT_MISSING", "missing inherited context: %s" % ",".join(missing_context), source_revision.artifact_id, source_revision_id, source_revision_id)
        if source_revision.approval_status != "approved" or not source_run:
            _gate_failure(self.store, skill=skill, target_artifact_id=source_revision.artifact_id, source_revision_id=source_revision_id, error_code="SOURCE_REVISION_NOT_APPROVED", error_message="source revision is not approved", request_reference=source_revision_id)
            raise WorkflowGateError("SOURCE_REVISION_NOT_APPROVED", "source revision is not approved", source_revision.artifact_id, source_revision_id, source_revision_id)
        current = self.store.current_approved(source_revision.artifact_id)
        if not current or current.revision_id != source_revision.revision_id:
            _gate_failure(self.store, skill=skill, target_artifact_id=source_revision.artifact_id, source_revision_id=source_revision_id, error_code="SOURCE_REVISION_NOT_CURRENT_APPROVED", error_message="source revision is not current approved", request_reference=source_revision_id)
            raise WorkflowGateError("SOURCE_REVISION_NOT_CURRENT_APPROVED", "source revision is not current approved", source_revision.artifact_id, source_revision_id, source_revision_id)
        artifact_id = source_revision.artifact_id + ":storyboard"
        project_id = source_revision.project_id
        chapter_id = source_revision.chapter_id
        self.store.ensure_artifact(artifact_id, "storyboard", project_id, chapter_id)
        resolved_model = model or (os.environ.get("AI_DRAMA_MODEL") if runtime == "openai-compatible" else model)
        try:
            runtime_request = build_storyboard_runtime_request(skill, self.store, source_revision, runtime, resolved_model or "")
        except ValueError as exc:
            _gate_failure(self.store, skill=skill, target_artifact_id=artifact_id, source_revision_id=source_revision_id, error_code="SOURCE_CONTEXT_MISSING", error_message=str(exc), request_reference=source_revision_id)
            raise WorkflowGateError("SOURCE_CONTEXT_MISSING", str(exc), artifact_id, source_revision_id, source_revision_id)
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
            model=resolved_model or "",
            status="RUNNING",
            request_object_id=request_object_id,
            input_hash=runtime_request.sha256,
            request_hash=runtime_request.sha256,
        )
        self.store.insert_input_snapshot(
            run.run_id,
            logical_type="source_revision",
            source_relative_path=source_revision.revision_id,
            source_path=Path(source_run.request_object_id),
            text=self.store.read_text(source_revision.content_object_id),
        )
        self.store.insert_input_snapshot(
            run.run_id,
            logical_type="source_script_approval",
            source_relative_path=source_revision.revision_id,
            source_path=Path(source_run.request_object_id),
            text=json.dumps(_approved_approval_record(self.store, source_revision.revision_id), ensure_ascii=False, sort_keys=True),
        )
        for logical_type in ("series_canon", "characters", "production_brief"):
            snapshot = snapshots[logical_type]
            self.store.insert_input_snapshot(
                run.run_id,
                logical_type=logical_type,
                source_relative_path=snapshot.source_relative_path,
                source_path=snapshot.source_path,
                text=self.store.read_text(snapshot.object_id),
            )
        try:
            response = run_runtime(runtime_request, mock_mode=mock_mode)
        except RuntimeErrorBase as exc:
            run = self.store.update_run(
                run.run_id,
                status="RUNTIME_FAILED",
                provider=runtime,
                model=resolved_model or "",
                duration_ms=int((time.time() - started) * 1000),
                error_code=exc.code,
                error_message=exc.safe_message,
            )
            return RunResult(run=run, revision=None, validation_results=[], adapter_request_json=request_json)
        response_object_id = self.store.write_text_object(response.raw)
        profile_id = _skill_profile_id(skill)
        try:
            if profile_id == STORYBOARD_CANONICAL_PROFILE:
                storyboard_text = parse_storyboard_canonical_response(response.raw)
            else:
                storyboard_text = parse_storyboard_response(response.raw)
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
        content_object_id = self.store.write_text_object(storyboard_text)
        content_hash = canonical_storyboard_hash(parse_canonical_json(storyboard_text)) if profile_id == STORYBOARD_CANONICAL_PROFILE else _sha256_text(storyboard_text)
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
            artifact_type="storyboard",
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
            parser_version=STORYBOARD_CANONICAL_PARSER_VERSION if profile_id == STORYBOARD_CANONICAL_PROFILE else STORYBOARD_PARSER_VERSION,
            content_profile=profile_id or "storyboard-markdown-mvp-v1",
            derivation_type="model_generation",
        )
        self.store.insert_revision_dependency(
            child_revision_id=revision.revision_id,
            parent_revision_id=source_revision.revision_id,
            relation_type="derived_from",
            parent_content_hash=source_revision.content_hash,
            parent_approval_record_id=(self.store.latest_approval(source_revision.revision_id).record_id if self.store.latest_approval(source_revision.revision_id) else ""),
        )
        if skill.version == "v0.2.1" and profile_id == STORYBOARD_CANONICAL_PROFILE:
            try:
                prevalidation = [self._auto_materialize_storyboard_bundle(revision, run.run_id)]
            except BundleError as exc:
                run = self.store.update_run(
                    run.run_id,
                    status="VALIDATION_FAILED",
                    error_code=exc.code,
                    error_message=exc.safe_message,
                )
                return RunResult(run=run, revision=revision, validation_results=[], adapter_request_json=request_json)
        else:
            prevalidation = []
        validations = run_declared_validators(self.store, skill, revision, self.repo_root, repo_root=self.repo_root)
        validations = prevalidation + [item for item in validations if item.validator_id != "storyboard_bundle_integrity"]
        blocking = [item for item in validations if item.required and item.status not in {"PASS", "NOT_APPLICABLE"}]
        if blocking:
            validator_ids = ", ".join(item.validator_id for item in blocking)
            run = self.store.update_run(
                run.run_id,
                status="VALIDATION_FAILED",
                error_code="VALIDATION_REQUIRED_FAILED",
                error_message="required validators did not pass: %s" % validator_ids,
            )
        return RunResult(run=run, revision=revision, validation_results=validations, adapter_request_json=request_json)

    def _auto_materialize_storyboard_bundle(self, revision, run_id):
        self.materialize_storyboard_bundle(revision.revision_id)
        report = json.dumps(
            {
                "validator_id": "storyboard_bundle_integrity",
                "final_status": "pass",
                "materialization_status": "MATERIALIZED",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return self.store.insert_validation(
            revision_id=revision.revision_id,
            validator_id="storyboard_bundle_integrity",
            validator_name="storyboard_bundle_integrity",
            status="PASS",
            required=1,
            exit_code=0,
            error_code="",
            duration_ms=0,
            stdout_object_id=self.store.write_text_object(""),
            stderr_object_id=self.store.write_text_object(""),
            report_object_id=self.store.write_text_object(report + "\n"),
        )

    def approve_revision(self, revision_id, reviewer, note=""):
        revision = self._revision_or_raise(revision_id)
        run = self.store.get_run(revision.run_id)
        if run.status not in {"SUCCEEDED", "VALIDATION_FAILED"}:
            raise ApprovalBlocked("run status does not allow approval: %s" % run.status)
        if revision.artifact_type == "storyboard" and self.revision_freshness(revision_id) != "FRESH":
            raise ApprovalBlocked("stale storyboard revision")
        if not self.store.read_text(revision.content_object_id).strip():
            raise ApprovalBlocked("revision content is empty")
        results = self.store.validation_results(revision_id)
        required = [item for item in results if item.required]
        if not required:
            raise ApprovalBlocked("missing required validator result")
        blocking = [item for item in required if item.validator_id != "storyboard_bundle_integrity" and item.status not in {"PASS"}]
        if blocking:
            raise ApprovalBlocked("required validators did not pass: %s" % ", ".join(item.validator_id for item in blocking))
        if revision.artifact_type == "storyboard" and getattr(revision, "content_profile", "") == STORYBOARD_CANONICAL_PROFILE:
            try:
                self.check_storyboard_bundle_integrity(revision_id)
            except BundleError as exc:
                raise self._normalize_bundle_integrity_error(exc) from exc
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

    def revision_source_approval_record(self, revision_id):
        dep = self.store.revision_dependencies(revision_id)
        if not dep:
            return {}
        record_id = dep[0].parent_approval_record_id
        if not record_id:
            return {}
        approval = self.store.approval_record(record_id)
        return approval.__dict__ if approval else {}

    def revision_source_revision_id(self, revision_id):
        deps = self.store.revision_dependencies(revision_id)
        return deps[0].parent_revision_id if deps else ""

    def revision_freshness(self, revision_id):
        revision = self._revision_or_raise(revision_id)
        if revision.artifact_type != "storyboard":
            return "FRESH"
        return recursive_freshness_status(self.store, revision_id)

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
            "freshness_status": [self.revision_freshness(left_revision_id), self.revision_freshness(right_revision_id)],
            "source_revision_id": [self.revision_source_revision_id(left_revision_id), self.revision_source_revision_id(right_revision_id)],
            "source_script_artifact_id": [
                self.store.get_revision(self.revision_source_revision_id(left_revision_id)).artifact_id if self.revision_source_revision_id(left_revision_id) else "",
                self.store.get_revision(self.revision_source_revision_id(right_revision_id)).artifact_id if self.revision_source_revision_id(right_revision_id) else "",
            ],
            "source_script_content_hash": [
                self.store.get_revision(self.revision_source_revision_id(left_revision_id)).content_hash if self.revision_source_revision_id(left_revision_id) else "",
                self.store.get_revision(self.revision_source_revision_id(right_revision_id)).content_hash if self.revision_source_revision_id(right_revision_id) else "",
            ],
            "source_script_approval_record_id": [
                self.store.revision_dependencies(left_revision_id)[0].parent_approval_record_id if self.store.revision_dependencies(left_revision_id) else "",
                self.store.revision_dependencies(right_revision_id)[0].parent_approval_record_id if self.store.revision_dependencies(right_revision_id) else "",
            ],
            "source_approval_record": [self.revision_source_approval_record(left_revision_id), self.revision_source_approval_record(right_revision_id)],
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
            "validator_status": {
                "left": {item.validator_id: item.status for item in self.store.validation_results(left.revision_id)},
                "right": {item.validator_id: item.status for item in self.store.validation_results(right.revision_id)},
            },
        }
        left_text = self._revision_display_text(left).splitlines(keepends=True)
        right_text = self._revision_display_text(right).splitlines(keepends=True)
        return "metadata:\n%s\ninput_hash_diff:\n%s\nrequest_hash_diff:\n%s\nvalidator_status:\n%s\ntext_diff:\n%s" % (
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(metadata["input_hashes"], ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(metadata["request_hash"], ensure_ascii=False, indent=2, sort_keys=True),
            json.dumps(metadata["validator_status"], ensure_ascii=False, indent=2, sort_keys=True),
            "".join(difflib.unified_diff(left_text, right_text, fromfile=left.revision_id, tofile=right.revision_id)),
        )

    def export_approved(self, artifact_id, output, force=False):
        revision = self.current_approved(artifact_id)
        if revision.artifact_type == "storyboard" and self.revision_freshness(revision.revision_id) != "FRESH":
            raise ExportConflict("cannot export stale storyboard revision")
        output = Path(output)
        sidecar = output.with_name(output.name + ".provenance.json")
        if not force and (output.exists() or sidecar.exists()):
            raise ExportConflict("output or provenance sidecar exists; use --force")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self._revision_display_text(revision), encoding="utf-8")
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
            "content_profile": getattr(revision, "content_profile", ""),
            "freshness_status": self.revision_freshness(revision.revision_id),
            "source_revision_id": self.revision_source_revision_id(revision.revision_id),
            "source_approval_record": self.revision_source_approval_record(revision.revision_id),
            "source_script_artifact_id": self._revision_or_raise(self.revision_source_revision_id(revision.revision_id)).artifact_id if self.revision_source_revision_id(revision.revision_id) else "",
            "source_script_revision_id": self.revision_source_revision_id(revision.revision_id),
            "source_script_content_hash": self.store.get_revision(self.revision_source_revision_id(revision.revision_id)).content_hash if self.revision_source_revision_id(revision.revision_id) else "",
            "source_script_approval_record_id": (self.store.revision_dependencies(revision.revision_id)[0].parent_approval_record_id if self.store.revision_dependencies(revision.revision_id) else ""),
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

    def _legacy_migration_candidate(self, source_revision_id):
        legacy = self._revision_or_raise(source_revision_id)
        if legacy.artifact_type != "storyboard" or getattr(legacy, "content_profile", "") != "storyboard-markdown-mvp-v1":
            raise WorkflowGateError("LEGACY_MIGRATION_REQUIRES_REVIEW", "source revision is not a legacy storyboard revision", legacy.artifact_id, source_revision_id, source_revision_id)
        deps = self.store.revision_dependencies(legacy.revision_id)
        if not deps:
            raise WorkflowGateError("LEGACY_MIGRATION_REQUIRES_REVIEW", "legacy storyboard has no source dependency", legacy.artifact_id, source_revision_id, source_revision_id)
        source = self._revision_or_raise(deps[0].parent_revision_id)
        try:
            candidate = legacy_markdown_to_canonical(
                self.store.read_text(legacy.content_object_id),
                source_revision=source,
                source_artifact_id=source.artifact_id,
                source_content_hash=source.content_hash,
            )
        except StoryboardMigrationError as exc:
            raise WorkflowGateError(exc.code, str(exc), legacy.artifact_id, source_revision_id, source_revision_id) from exc
        return legacy, source, deps[0], candidate

    def preview_legacy_storyboard_migration(self, source_revision_id, output):
        _, _, _, candidate = self._legacy_migration_candidate(source_revision_id)
        return write_migration_preview(candidate, Path(output))

    def confirm_legacy_storyboard_migration(self, source_revision_id, confirm_candidate_hash, output):
        legacy, source, dep, candidate = self._legacy_migration_candidate(source_revision_id)
        actual_hash = canonical_storyboard_hash(candidate)
        if actual_hash != confirm_candidate_hash:
            raise WorkflowGateError(
                "LEGACY_MIGRATION_REQUIRES_REVIEW",
                "candidate hash confirmation does not match",
                legacy.artifact_id,
                source_revision_id,
                source_revision_id,
            )
        preview = write_migration_preview(candidate, Path(output))
        request_object_id = self.store.write_text_object(json.dumps({"source_revision_id": source_revision_id, "candidate_hash": actual_hash}, ensure_ascii=False, sort_keys=True))
        canonical_text = serialize_canonical_json(candidate).decode("utf-8")
        response_object_id = self.store.write_text_object(canonical_text)
        run = self.store.create_run(
            artifact_id=legacy.artifact_id,
            project_id=legacy.project_id,
            chapter_id=legacy.chapter_id,
            skill_id=legacy.skill_id,
            skill_version="v0.2.0",
            skill_hash="",
            runtime="migration",
            provider="migration",
            model="legacy-migration",
            status="SUCCEEDED",
            request_object_id=request_object_id,
            response_object_id=response_object_id,
            input_hash=actual_hash,
            request_hash=actual_hash,
        )
        content_object_id = self.store.write_text_object(canonical_text)
        revision = self.store.insert_revision(
            artifact_id=legacy.artifact_id,
            artifact_type="storyboard",
            project_id=legacy.project_id,
            chapter_id=legacy.chapter_id,
            run_id=run.run_id,
            skill_id=legacy.skill_id,
            skill_version="v0.2.0",
            skill_package_hash="",
            runtime_provider="migration",
            runtime_model="legacy-migration",
            content_object_id=content_object_id,
            content_hash=actual_hash,
            raw_response_object_id=response_object_id,
            parser_version=STORYBOARD_CANONICAL_PARSER_VERSION,
            content_profile=STORYBOARD_CANONICAL_PROFILE,
            derivation_type="legacy_migration",
        )
        self.store.insert_revision_dependency(
            child_revision_id=revision.revision_id,
            parent_revision_id=source.revision_id,
            relation_type=dep.relation_type,
            parent_content_hash=source.content_hash,
            parent_approval_record_id=dep.parent_approval_record_id,
        )
        return {
            "status": "PENDING_CANONICAL_REVISION",
            "revision_id": revision.revision_id,
            "candidate_hash": actual_hash,
            "content_profile": STORYBOARD_CANONICAL_PROFILE,
            "approval_status": revision.approval_status,
            "canonical_candidate_path": preview["canonical_candidate_path"],
            "rendered_markdown_path": preview["rendered_markdown_path"],
        }

    def render_storyboard_revision(self, revision_id, output):
        revision = self._revision_or_raise(revision_id)
        if revision.artifact_type != "storyboard":
            raise NotFound("revision is not a storyboard: %s" % revision_id)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self._revision_display_text(revision), encoding="utf-8")
        payload = {
            "status": "RENDERED",
            "revision_id": revision.revision_id,
            "content_profile": getattr(revision, "content_profile", ""),
            "canonical_hash": revision.content_hash if getattr(revision, "content_profile", "") == STORYBOARD_CANONICAL_PROFILE else "",
            "renderer_id": "storyboard-canonical-markdown-renderer" if getattr(revision, "content_profile", "") == STORYBOARD_CANONICAL_PROFILE else "",
            "renderer_version": "1.0.0" if getattr(revision, "content_profile", "") == STORYBOARD_CANONICAL_PROFILE else "",
            "output_path": str(output),
        }
        return payload

    def _revision_or_raise(self, revision_id):
        revision = self.store.get_revision(revision_id)
        if revision is None:
            raise NotFound("revision not found: %s" % revision_id)
        return revision

    def _revision_display_text(self, revision):
        text = self.store.read_text(revision.content_object_id)
        if getattr(revision, "content_profile", "") == STORYBOARD_CANONICAL_PROFILE:
            return render_storyboard_markdown(parse_canonical_json(text))
        return text
