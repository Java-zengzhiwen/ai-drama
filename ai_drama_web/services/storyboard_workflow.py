from pathlib import Path

from ai_drama_runtime.registry import DuplicateSkillError, SkillNotFoundError, SkillRegistry
from ai_drama_runtime.services import RuntimeService, WorkflowGateError
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.storyboard_canonical import CONTENT_PROFILE as STORYBOARD_CANONICAL_PROFILE
from ai_drama_runtime.validators import run_declared_validators
from ai_drama_web.config import Settings
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.services.script_workflow import WorkflowExecutionError
from ai_drama_web.store import ProductStore


STORYBOARD_SKILL_REF = "ai-drama-storyboard-design-skill@v0.2.1"
STORYBOARD_FALLBACK_SKILL_REF = "ai-drama-storyboard-design-skill@v0.2.0"


class StoryboardWorkflowService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        settings: Settings,
        repo_root: Path,
    ):
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.settings = settings
        self.repo_root = Path(repo_root).resolve()
        self.runtime_service = RuntimeService(runtime_store, repo_root=self.repo_root)

    def generate_storyboard(self, chapter_id: str):
        self._chapter_or_raise(chapter_id)
        skill = self._storyboard_skill()
        source_revision = self._source_script_revision_or_gate(chapter_id)
        result = self.runtime_service.run_storyboard(
            skill,
            source_revision.revision_id,
            runtime=self.settings.runtime_provider,
            model=self.settings.runtime_model,
        )
        if result.revision is None:
            raise WorkflowExecutionError(
                result.run.error_code or result.run.status,
                result.run.error_message or result.run.status,
            )
        if result.revision.content_profile == STORYBOARD_CANONICAL_PROFILE:
            self.runtime_service.materialize_storyboard_bundle(result.revision.revision_id)
        return self._read_revision(result.revision.revision_id)

    def list_revisions(self, chapter_id: str):
        self._chapter_or_raise(chapter_id)
        return [
            self._read_revision(item.revision_id)
            for item in self.runtime_store.revisions_for_artifact(self._artifact_id(chapter_id))
        ]

    def create_manual_revision(self, revision_id: str, content: str):
        if self.runtime_store.get_revision(revision_id) is None:
            raise MissingRecord
        skill = self._storyboard_skill()
        revision = self.runtime_service.create_manual_revision(revision_id, content, actor="local-user")
        if revision.content_profile == STORYBOARD_CANONICAL_PROFILE:
            self.runtime_service.materialize_storyboard_bundle(revision.revision_id)
        run_declared_validators(
            self.runtime_store,
            skill,
            revision,
            self.repo_root,
            repo_root=self.repo_root,
        )
        return self._read_revision(revision.revision_id)

    def validate_revision(self, revision_id: str):
        revision = self.runtime_store.get_revision(revision_id)
        if revision is None:
            raise MissingRecord
        skill = self._storyboard_skill()
        if revision.content_profile == STORYBOARD_CANONICAL_PROFILE:
            self.runtime_service.materialize_storyboard_bundle(revision.revision_id)
        run_declared_validators(
            self.runtime_store,
            skill,
            revision,
            self.repo_root,
            repo_root=self.repo_root,
        )
        return self._read_revision(revision.revision_id)

    def approve_revision(self, revision_id: str, reviewer: str, note: str = ""):
        if self.runtime_store.get_revision(revision_id) is None:
            raise MissingRecord
        revision = self.runtime_service.approve_revision(revision_id, reviewer, note)
        return self._read_revision(revision.revision_id)

    def reject_revision(self, revision_id: str, reviewer: str, note: str = ""):
        if self.runtime_store.get_revision(revision_id) is None:
            raise MissingRecord
        revision = self.runtime_service.reject_revision(revision_id, reviewer, note)
        return self._read_revision(revision.revision_id)

    def _read_revision(self, revision_id: str) -> dict:
        revision = self.runtime_store.get_revision(revision_id)
        if revision is None:
            raise MissingRecord
        current = self.runtime_store.current_approved(revision.artifact_id)
        return {
            "revision_id": revision.revision_id,
            "artifact_id": revision.artifact_id,
            "chapter_id": revision.chapter_id,
            "number": revision.number,
            "approval_status": revision.approval_status,
            "current": bool(current and current.revision_id == revision.revision_id),
            "content": self.runtime_store.read_text(revision.content_object_id),
            "validation_results": self.runtime_store.validation_results(revision.revision_id),
        }

    def _storyboard_skill(self):
        try:
            registry = SkillRegistry.scan([self.settings.skills_root])
            return registry.get_ref(STORYBOARD_SKILL_REF)
        except SkillNotFoundError:
            try:
                return registry.get_ref(STORYBOARD_FALLBACK_SKILL_REF)
            except SkillNotFoundError as exc:
                raise WorkflowExecutionError("SKILL_NOT_FOUND", str(exc), status_code=503) from exc
        except DuplicateSkillError as exc:
            raise WorkflowExecutionError("SKILL_CONFIG_INVALID", str(exc), status_code=503) from exc

    def _chapter_or_raise(self, chapter_id: str):
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord
        return chapter

    def _source_script_revision_or_gate(self, chapter_id: str):
        script_artifact_id = self._script_artifact_id(chapter_id)
        current = self.runtime_store.current_approved(script_artifact_id)
        if current is not None:
            return current
        revisions = self.runtime_store.revisions_for_artifact(script_artifact_id)
        if revisions:
            return revisions[-1]
        raise WorkflowGateError(
            "SOURCE_REVISION_NOT_APPROVED",
            "source revision is not approved",
            target_artifact_id=self._artifact_id(chapter_id),
            request_reference=chapter_id,
        )

    def _script_artifact_id(self, chapter_id: str) -> str:
        return f"{chapter_id}:script"

    def _artifact_id(self, chapter_id: str) -> str:
        return f"{self._script_artifact_id(chapter_id)}:storyboard"
