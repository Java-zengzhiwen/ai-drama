from dataclasses import dataclass
import difflib
import hashlib
from pathlib import Path

from .acceptance import load_acceptance_bundle
from .runtime import run_runtime
from .validators import run_declared_validators


class ApprovalBlocked(RuntimeError):
    pass


class NotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class RunResult:
    run: object
    revision: object
    validation_results: list


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RuntimeService:
    def __init__(self, store, repo_root=None):
        self.store = store
        self.repo_root = Path(repo_root or Path.cwd()).resolve()

    def run_acceptance(self, skill, acceptance_root, runtime, model):
        bundle = load_acceptance_bundle(acceptance_root)
        request_text = bundle.to_runtime_request_text()
        skill_instructions = skill.instructions_entry.read_text(encoding="utf-8")
        response = run_runtime(runtime, model, request_text, skill_instructions)

        request_object_id = self.store.write_text_object(request_text)
        response_object_id = self.store.write_text_object(response.raw)
        content_object_id = self.store.write_text_object(response.text)
        run = self.store.insert_run(
            artifact_id=bundle.manifest["id"],
            skill_id=skill.skill_id,
            skill_version=skill.version,
            skill_hash=skill.content_hash,
            runtime=runtime,
            model=response.model,
            status="succeeded",
            request_object_id=request_object_id,
            response_object_id=response_object_id,
            input_hash=_sha256_text(request_text),
        )
        revision = self.store.insert_revision(
            artifact_id=bundle.manifest["id"],
            run_id=run.run_id,
            content_object_id=content_object_id,
            content_hash=_sha256_text(response.text),
        )
        validations = run_declared_validators(
            self.store,
            skill,
            revision,
            bundle.root,
            repo_root=self.repo_root,
        )
        return RunResult(run=run, revision=revision, validation_results=validations)

    def approve_revision(self, revision_id, reviewer, note=""):
        revision = self._revision_or_raise(revision_id)
        blocking = [
            result
            for result in self.store.validation_results(revision_id)
            if result.required and result.status != "passed"
        ]
        if blocking:
            names = ", ".join(result.validator_name for result in blocking)
            raise ApprovalBlocked("required validators did not pass: %s" % names)
        self.store.set_approved(revision)
        self.store.record_approval(revision_id, revision.artifact_id, "script_approved", reviewer, note)
        return self.store.get_revision(revision_id)

    def reject_revision(self, revision_id, reviewer, note=""):
        revision = self._revision_or_raise(revision_id)
        self.store.set_rejected(revision)
        self.store.record_approval(revision_id, revision.artifact_id, "script_rejected", reviewer, note)
        return self.store.get_revision(revision_id)

    def current_approved(self, artifact_id):
        revision = self.store.current_approved(artifact_id)
        if revision is None:
            raise NotFound("no approved revision for artifact %s" % artifact_id)
        return revision

    def compare_revisions(self, left_revision_id, right_revision_id):
        left = self._revision_or_raise(left_revision_id)
        right = self._revision_or_raise(right_revision_id)
        left_text = self.store.read_text(left.content_object_id).splitlines(keepends=True)
        right_text = self.store.read_text(right.content_object_id).splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                left_text,
                right_text,
                fromfile=left.revision_id,
                tofile=right.revision_id,
            )
        )

    def export_approved(self, artifact_id, output):
        revision = self.current_approved(artifact_id)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.store.read_text(revision.content_object_id), encoding="utf-8")
        return self.store.record_export(
            artifact_id=artifact_id,
            revision_id=revision.revision_id,
            content_hash=revision.content_hash,
            destination=output,
        )

    def _revision_or_raise(self, revision_id):
        revision = self.store.get_revision(revision_id)
        if revision is None:
            raise NotFound("revision not found: %s" % revision_id)
        return revision
