from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


class ChapterStatusService:
    def __init__(self, product_store: ProductStore, runtime_store: RuntimeStore):
        self.product_store = product_store
        self.runtime_store = runtime_store

    def get_status(self, chapter_id: str) -> dict[str, str]:
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord

        if not chapter.current_source_revision_id:
            return self._result(
                "missing_source",
                "chapter source revision is required",
                "add_source",
            )

        source = self.product_store.get_source_revision(chapter.current_source_revision_id)
        if source is None:
            return self._result(
                "missing_source",
                "chapter source revision is required",
                "add_source",
            )

        script_artifact_id = f"{chapter_id}:script"
        storyboard_artifact_id = f"{script_artifact_id}:storyboard"

        if self.runtime_store.current_approved(storyboard_artifact_id) is not None:
            return self._result("storyboard_approved", "", "open_assets")
        if self._has_pending_revision(storyboard_artifact_id):
            return self._result("storyboard_draft", "", "approve_storyboard")
        if self.runtime_store.current_approved(script_artifact_id) is not None:
            return self._result("script_approved", "", "generate_storyboard")
        if self._has_pending_revision(script_artifact_id):
            return self._result("script_draft", "", "approve_script")
        return self._result("source_ready", "", "generate_script")

    def _has_pending_revision(self, artifact_id: str) -> bool:
        return any(
            revision.approval_status == "pending"
            for revision in self.runtime_store.revisions_for_artifact(artifact_id)
        )

    def _result(self, status: str, blocking_reason: str, next_action: str) -> dict[str, str]:
        return {
            "status": status,
            "blocking_reason": blocking_reason,
            "next_action": next_action,
        }
