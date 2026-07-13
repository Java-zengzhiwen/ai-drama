from pathlib import Path

from ai_drama_runtime.registry import SkillNotFoundError, SkillRegistry
from ai_drama_runtime.services import RuntimeService, WorkflowGateError
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.validators import run_declared_validators
from ai_drama_web.config import Settings
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


SCRIPT_SKILL_REF = "ai-drama-script-adaptation-skill@v0.6.1-rc2.4"


class WorkflowExecutionError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.status_code = status_code


class ScriptWorkflowService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        settings: Settings,
        repo_root: Path,
        supplier_text_executor=None,
    ):
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.settings = settings
        self.repo_root = Path(repo_root).resolve()
        self.runtime_service = RuntimeService(runtime_store, repo_root=self.repo_root, supplier_text_executor=supplier_text_executor)

    def generate_script(self, chapter_id: str):
        chapter = self._chapter_or_raise(chapter_id)
        project = self.product_store.get_project(chapter.project_id)
        if project is None:
            raise MissingRecord
        source_text = self._source_text_or_gate(chapter)
        skill = self._script_skill()
        inputs = {
            "source_chapter": source_text,
            "series_canon": project.series_canon,
            "characters": project.characters_context,
            "production_brief": project.production_brief,
        }
        result = self.runtime_service.run_script_inputs(
            skill,
            artifact_id=self._artifact_id(chapter_id),
            project_id=chapter.project_id,
            chapter_id=chapter_id,
            inputs=inputs,
            runtime=self.settings.runtime_provider,
            model=self.settings.runtime_model,
        )
        if result.revision is None:
            raise WorkflowExecutionError(
                result.run.error_code or result.run.status,
                result.run.error_message or result.run.status,
            )
        return self._read_revision(result.revision.revision_id)

    def list_revisions(self, chapter_id: str):
        self._chapter_or_raise(chapter_id)
        return [self._read_revision(item.revision_id) for item in self.runtime_store.revisions_for_artifact(self._artifact_id(chapter_id))]

    def create_manual_revision(self, revision_id: str, content: str):
        if self.runtime_store.get_revision(revision_id) is None:
            raise MissingRecord
        revision = self.runtime_service.create_manual_revision(revision_id, content, actor="local-user")
        skill = self._script_skill()
        run_declared_validators(
            self.runtime_store,
            skill,
            revision,
            skill.root,
            repo_root=self.runtime_service.repo_root,
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

    def _script_skill(self):
        try:
            return SkillRegistry.scan([self.settings.skills_root]).get_ref(SCRIPT_SKILL_REF)
        except SkillNotFoundError as exc:
            raise WorkflowExecutionError("SKILL_NOT_FOUND", str(exc), status_code=503) from exc

    def _chapter_or_raise(self, chapter_id: str):
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord
        return chapter

    def _source_text_or_gate(self, chapter):
        if not chapter.current_source_revision_id:
            raise WorkflowGateError(
                "SOURCE_REVISION_REQUIRED",
                "chapter source revision is required",
                target_artifact_id=self._artifact_id(chapter.chapter_id),
                request_reference=chapter.chapter_id,
            )
        source = self.product_store.get_source_revision(chapter.current_source_revision_id)
        if source is None:
            raise WorkflowGateError(
                "SOURCE_REVISION_REQUIRED",
                "chapter source revision is required",
                target_artifact_id=self._artifact_id(chapter.chapter_id),
                request_reference=chapter.chapter_id,
            )
        return self.runtime_store.read_text(source.object_id)

    def _artifact_id(self, chapter_id: str) -> str:
        return f"{chapter_id}:script"
