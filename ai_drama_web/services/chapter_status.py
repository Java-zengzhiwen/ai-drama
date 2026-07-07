import json

from ai_drama_runtime.shot_prompt_canonical import CanonicalShotPromptError, parse_shot_prompt_json
from ai_drama_runtime.storyboard_canonical import (
    CONTENT_PROFILE as STORYBOARD_CANONICAL_PROFILE,
    CanonicalStoryboardError,
    parse_canonical_json,
    validate_storyboard_canonical,
)
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


READINESS_SCHEMA_VERSION = "shot-prompt-readiness-v1"


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

        approved_storyboard = self.runtime_store.current_approved(storyboard_artifact_id)
        if approved_storyboard is not None:
            return self._m2_status(chapter_id, approved_storyboard)
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

    def _m2_status(self, chapter_id: str, approved_storyboard) -> dict[str, str]:
        if not self._is_canonical_storyboard(approved_storyboard):
            return self._result(
                "assets_incomplete",
                "current approved canonical storyboard is required",
                "approve_storyboard",
            )
        latest_requirements = self.product_store.latest_asset_requirement_set(chapter_id)
        if (
            latest_requirements is None
            or latest_requirements["storyboard_revision_id"] != approved_storyboard.revision_id
            or latest_requirements["payload"].get("storyboard_content_hash") != approved_storyboard.content_hash
            or latest_requirements["payload"].get("status") != "ready"
        ):
            return self._result(
                "assets_incomplete",
                "asset requirements are not ready",
                "analyze_assets",
            )

        latest_prompt = self._latest_shot_prompt_revision(chapter_id, approved_storyboard.revision_id)
        if latest_prompt is None:
            return self._result("assets_ready", "", "generate_shot_prompts")

        if self._all_shot_prompts_ready(latest_prompt):
            return self._result("prompts_ready", "", "m2_complete")
        return self._result("prompts_draft", "", "mark_shot_prompts_ready")

    def _is_canonical_storyboard(self, revision) -> bool:
        if revision.content_profile != STORYBOARD_CANONICAL_PROFILE:
            return False
        try:
            canonical = parse_canonical_json(self.runtime_store.read_text(revision.content_object_id))
            validate_storyboard_canonical(canonical)
        except CanonicalStoryboardError:
            return False
        return (
            canonical.get("project_id") == revision.project_id
            and canonical.get("chapter_id") == revision.chapter_id
            and canonical.get("source", {}).get("script_artifact_id") == f"{revision.chapter_id}:script"
        )

    def _latest_shot_prompt_revision(self, chapter_id: str, storyboard_revision_id: str):
        rows = self.runtime_store.conn.execute(
            """
            SELECT revision_id
            FROM revisions
            WHERE chapter_id = ? AND artifact_type = 'shot_prompt_set'
            ORDER BY created_at DESC, number DESC, revision_id DESC
            """,
            (chapter_id,),
        ).fetchall()
        for row in rows:
            revision = self.runtime_store.get_revision(row["revision_id"])
            if revision is not None and self._shot_prompt_source_revision_id(revision) == storyboard_revision_id:
                return revision
        return None

    def _shot_prompt_source_revision_id(self, revision) -> str:
        try:
            canonical = parse_shot_prompt_json(self.runtime_store.read_text(revision.content_object_id))
        except CanonicalShotPromptError:
            return ""
        return canonical.get("source_storyboard_revision_id", "")

    def _all_shot_prompts_ready(self, revision) -> bool:
        try:
            canonical = parse_shot_prompt_json(self.runtime_store.read_text(revision.content_object_id))
        except CanonicalShotPromptError:
            return False
        shots = canonical.get("shots", [])
        if not shots:
            return False
        latest = self._latest_readiness_by_shot(revision.revision_id)
        return all(latest.get(shot.get("shot_id")) == "ready" for shot in shots)

    def _latest_readiness_by_shot(self, revision_id: str) -> dict[str, str]:
        rows = self.runtime_store.conn.execute(
            """
            SELECT shot_id, body, created_at, review_id
            FROM review_records
            WHERE revision_id = ? AND scope = 'shot'
            ORDER BY created_at ASC, review_id ASC
            """,
            (revision_id,),
        ).fetchall()
        latest = {}
        for row in rows:
            if not row["shot_id"]:
                continue
            try:
                body = json.loads(row["body"])
            except json.JSONDecodeError:
                continue
            if body.get("schema_version") == READINESS_SCHEMA_VERSION:
                latest[row["shot_id"]] = body.get("status", "draft")
        return latest

    def _result(self, status: str, blocking_reason: str, next_action: str) -> dict[str, str]:
        return {
            "status": status,
            "blocking_reason": blocking_reason,
            "next_action": next_action,
        }
