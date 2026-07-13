import json
from pathlib import Path

from ai_drama_runtime.registry import DuplicateSkillError, SkillNotFoundError, SkillRegistry
from ai_drama_runtime.services import RuntimeService, WorkflowGateError
from ai_drama_runtime.shot_prompt_canonical import (
    CANONICAL_PARSER_VERSION,
    CONTENT_PROFILE,
    CanonicalShotPromptError,
    parse_shot_prompt_json,
    serialize_shot_prompt_json,
    shot_prompt_content_hash,
    validate_shot_prompt_canonical,
)
from ai_drama_runtime.store import RuntimeStore, now_iso
from ai_drama_runtime.validators import run_declared_validators
from ai_drama_web.config import Settings
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.services.script_workflow import WorkflowExecutionError
from ai_drama_web.store import ProductStore


SHOT_PROMPT_SKILL_REF = "ai-drama-shot-prompt-skill@v0.1.0"
READINESS_SCOPE = "shot"
READINESS_SCHEMA_VERSION = "shot-prompt-readiness-v1"


class ShotPromptInvalidContent(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.safe_message = message


class ShotPromptShotNotFound(Exception):
    pass


class ShotPromptReadinessBlocked(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.status_code = status_code


class ShotPromptService:
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

    def generate(self, chapter_id: str) -> dict:
        self._chapter_or_raise(chapter_id)
        source = self.runtime_store.current_approved(f"{chapter_id}:script:storyboard")
        if source is None:
            raise WorkflowGateError(
                "SOURCE_REVISION_NOT_APPROVED",
                "source revision is not approved",
                request_reference=chapter_id,
            )
        result = self.runtime_service.run_shot_prompt(
            self._shot_prompt_skill(),
            source.revision_id,
            runtime=self.settings.runtime_provider,
            model=self.settings.runtime_model,
        )
        if result.revision is None:
            raise WorkflowExecutionError(
                result.run.error_code or result.run.status,
                result.run.error_message or result.run.status,
                status_code=502,
            )
        return self._read_revision(result.revision.revision_id)

    def list_revisions(self, chapter_id: str) -> list[dict]:
        self._chapter_or_raise(chapter_id)
        rows = self.runtime_store.conn.execute(
            """
            SELECT revision_id
            FROM revisions
            WHERE chapter_id = ? AND artifact_type = 'shot_prompt_set'
            ORDER BY created_at ASC, number ASC, revision_id ASC
            """,
            (chapter_id,),
        ).fetchall()
        return [self._read_revision(row["revision_id"]) for row in rows]

    def create_manual_revision(self, revision_id: str, content: str) -> dict:
        source = self._shot_prompt_revision_or_raise(revision_id)
        canonical = self._parse_and_validate_content(content)
        self._assert_source_identity_matches(source, canonical)
        if canonical.get("chapter_id") != source.chapter_id:
            raise ShotPromptInvalidContent("INVALID_REVISION_CONTENT", "chapter_id does not match source revision")
        new_revision = self._insert_revision_from_canonical(
            source,
            canonical,
            derivation_type="manual_edit",
            actor="manual-editor",
            request_payload={
                "manual_edit": {
                    "source_revision_id": source.revision_id,
                    "actor": "local-user",
                }
            },
        )
        self._run_validators(new_revision)
        return self._read_revision(new_revision.revision_id)

    def regenerate_shot(self, revision_id: str, shot_id: str) -> dict:
        source = self._shot_prompt_revision_or_raise(revision_id)
        canonical = self._canonical_for_revision(source)
        shot = self._shot_or_raise(canonical, shot_id)
        shot["positive_prompt"] = "%s regenerated for %s" % (shot["positive_prompt"].rstrip(), shot_id)
        new_revision = self._insert_revision_from_canonical(
            source,
            canonical,
            derivation_type="model_regeneration",
            actor="shot-regenerator",
            request_payload={
                "single_shot_regenerate": {
                    "source_revision_id": source.revision_id,
                    "shot_id": shot_id,
                    "strategy": "deterministic-positive-prompt-refresh",
                }
            },
        )
        self._run_validators(new_revision)
        return self._read_revision(new_revision.revision_id)

    def mark_ready(self, revision_id: str, shot_id: str) -> dict:
        revision = self._shot_prompt_revision_or_raise(revision_id)
        canonical = self._canonical_for_revision(revision)
        shot = self._shot_or_raise(canonical, shot_id)
        self._assert_required_validators_passed(revision)
        self._assert_shot_ready(revision, canonical, shot)
        body = json.dumps(
            {
                "schema_version": READINESS_SCHEMA_VERSION,
                "status": "ready",
                "revision_id": revision.revision_id,
                "shot_id": shot_id,
                "content_hash": revision.content_hash,
                "marked_at": now_iso(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self.runtime_store.insert_review_record_with_opened_event(
            artifact_id=revision.artifact_id,
            revision_id=revision.revision_id,
            scope=READINESS_SCOPE,
            shot_id=shot_id,
            body=body,
            blocking=False,
            created_by="local-user",
            note="marked shot prompt ready",
        )
        return self._read_revision(revision.revision_id)

    def agnes_preview(self, revision_id: str, shot_id: str) -> dict:
        revision = self._shot_prompt_revision_or_raise(revision_id)
        canonical = self._canonical_for_revision(revision)
        shot = self._shot_or_raise(canonical, shot_id)
        return {
            "shot_id": shot["shot_id"],
            "positive_prompt": shot["positive_prompt"],
            "negative_prompt": shot["negative_prompt"],
            "asset_refs": shot["asset_refs"],
            "continuity_notes": shot["continuity_notes"],
            "agnes_video_params": shot["agnes_video_params"],
        }

    def _insert_revision_from_canonical(
        self,
        source,
        canonical: dict,
        *,
        derivation_type: str,
        actor: str,
        request_payload: dict,
    ):
        canonical_text = serialize_shot_prompt_json(canonical).decode("utf-8")
        content_hash = shot_prompt_content_hash(canonical)
        content_object_id = self.runtime_store.write_text_object(canonical_text)
        request_object_id = self.runtime_store.write_text_object(
            json.dumps(request_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        response_object_id = self.runtime_store.write_text_object(canonical_text)
        run = self.runtime_store.create_run(
            artifact_id=source.artifact_id,
            project_id=source.project_id,
            chapter_id=source.chapter_id,
            skill_id=actor,
            skill_version="1",
            skill_hash="",
            runtime="manual",
            provider=actor,
            model=derivation_type,
            status="SUCCEEDED",
            request_object_id=request_object_id,
            response_object_id=response_object_id,
            input_hash=content_hash,
            request_hash=content_hash,
            duration_ms=0,
        )
        revision = self.runtime_store.insert_revision(
            artifact_id=source.artifact_id,
            artifact_type=source.artifact_type,
            project_id=source.project_id,
            chapter_id=source.chapter_id,
            run_id=run.run_id,
            skill_id=actor,
            skill_version="1",
            skill_package_hash="",
            runtime_provider="manual",
            runtime_model=derivation_type,
            content_object_id=content_object_id,
            content_hash=content_hash,
            raw_response_object_id=response_object_id,
            parser_version=CANONICAL_PARSER_VERSION,
            content_profile=CONTENT_PROFILE,
            derivation_type=derivation_type,
            supersedes_revision_id=source.revision_id,
        )
        for dependency in self.runtime_store.revision_dependencies(source.revision_id):
            self.runtime_store.insert_revision_dependency(
                child_revision_id=revision.revision_id,
                parent_revision_id=dependency.parent_revision_id,
                relation_type=dependency.relation_type,
                parent_content_hash=dependency.parent_content_hash,
                parent_approval_record_id=dependency.parent_approval_record_id,
            )
        return revision

    def _run_validators(self, revision):
        return run_declared_validators(
            self.runtime_store,
            self._shot_prompt_skill(),
            revision,
            self.repo_root,
            repo_root=self.repo_root,
        )

    def _assert_shot_ready(self, revision, canonical: dict, shot: dict) -> None:
        if not 5 <= shot["duration_seconds"] <= 15:
            raise ShotPromptReadinessBlocked(
                "SHOT_PROMPT_DURATION_INVALID",
                "shot duration must be between 5 and 15 seconds",
                status_code=422,
            )
        requirement = self._latest_requirement_for_revision(revision, canonical)
        if requirement is None:
            raise ShotPromptReadinessBlocked("ASSET_REQUIREMENTS_NOT_READY", "asset requirements are not ready")
        payload = requirement["payload"]
        row = next((item for item in payload.get("shot_rows", []) if item.get("shot_id") == shot["shot_id"]), None)
        if row is None or row.get("status") != "ready":
            raise ShotPromptReadinessBlocked("ASSET_REQUIREMENTS_NOT_READY", "asset requirements are not ready")
        ready_by_asset_id = {
            item.get("asset_id"): item
            for item in row.get("ready", [])
            if item.get("asset_id")
        }
        shot_asset_refs = set(shot["asset_refs"])
        ready_asset_ids = set(ready_by_asset_id)
        if shot_asset_refs != ready_asset_ids:
            raise ShotPromptReadinessBlocked(
                "ASSET_MISSING",
                "shot asset_refs must match ready requirements",
            )
        for asset_id, need in ready_by_asset_id.items():
            if asset_id not in shot_asset_refs:
                raise ShotPromptReadinessBlocked("ASSET_MISSING", "shot references an asset outside ready requirements")
            asset = self.product_store.get_asset(asset_id)
            if asset is None:
                raise ShotPromptReadinessBlocked("ASSET_MISSING", "shot references a missing asset")
            if asset.status != "usable":
                raise ShotPromptReadinessBlocked("ASSET_NOT_USABLE", "shot references an asset that is not usable")
            if not self._asset_is_current_for_need(asset, need, revision.chapter_id):
                raise ShotPromptReadinessBlocked("ASSET_NOT_CURRENT", "shot references an asset that is not current")

    def _asset_is_current_for_need(self, asset, need: dict, chapter_id: str) -> bool:
        bindings = self.product_store.asset_bindings_for_requirement(
            project_id=asset.project_id,
            chapter_id=chapter_id,
            target_type=need["target_type"],
            target_id=need["target_id"],
            role=need["role"],
            asset_type=need["asset_type"],
        )
        return any(
            item["asset_id"] == asset.asset_id
            and item["status"] == "usable"
            and item["is_current"] == 1
            for item in bindings
        )

    def _assert_source_identity_matches(self, source, canonical: dict) -> None:
        source_canonical = self._canonical_for_revision(source)
        for key in ("project_id", "chapter_id", "source_storyboard_revision_id"):
            if canonical.get(key) != source_canonical.get(key):
                raise ShotPromptInvalidContent("INVALID_REVISION_CONTENT", "%s does not match source revision" % key)

    def _assert_required_validators_passed(self, revision) -> None:
        latest = self.runtime_store.latest_validation_results(revision.revision_id)
        required = [item for item in latest.values() if item.required]
        if not required:
            raise ShotPromptReadinessBlocked(
                "VALIDATION_REQUIRED_FAILED",
                "required validators have not run",
                status_code=422,
            )
        blocking = [item.validator_id for item in required if item.status != "PASS"]
        if blocking:
            raise ShotPromptReadinessBlocked(
                "VALIDATION_REQUIRED_FAILED",
                "required validators did not pass: %s" % ", ".join(sorted(blocking)),
                status_code=422,
            )

    def _latest_requirement_for_revision(self, revision, canonical: dict):
        source_revision_id = canonical.get("source_storyboard_revision_id")
        source = self.runtime_store.get_revision(source_revision_id)
        if source is None:
            return None
        latest = self.product_store.latest_asset_requirement_set(revision.chapter_id)
        if latest is None:
            return None
        payload = latest.get("payload") or {}
        if latest.get("storyboard_revision_id") != source_revision_id:
            return None
        if payload.get("storyboard_content_hash") != source.content_hash:
            return None
        if payload.get("status") != "ready":
            return None
        return latest

    def _read_revision(self, revision_id: str) -> dict:
        revision = self._shot_prompt_revision_or_raise(revision_id)
        canonical = self._canonical_for_revision(revision)
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
            "source_storyboard_revision_id": canonical["source_storyboard_revision_id"],
            "shots": canonical["shots"],
            "readiness": self._readiness_map(revision, canonical),
        }

    def _readiness_map(self, revision, canonical: dict) -> dict:
        latest = self._latest_readiness_by_shot(revision.revision_id)
        result = {}
        for shot in canonical["shots"]:
            status = "draft"
            record = latest.get(shot["shot_id"])
            if record is not None:
                try:
                    body = json.loads(record["body"])
                except json.JSONDecodeError:
                    body = {}
                if body.get("schema_version") == READINESS_SCHEMA_VERSION:
                    status = body.get("status", "draft")
            result[shot["shot_id"]] = {"status": status}
        return result

    def _latest_readiness_by_shot(self, revision_id: str) -> dict:
        rows = self.runtime_store.conn.execute(
            """
            SELECT shot_id, body, created_at, review_id
            FROM review_records
            WHERE revision_id = ? AND scope = ?
            ORDER BY created_at ASC, review_id ASC
            """,
            (revision_id, READINESS_SCOPE),
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
                latest[row["shot_id"]] = dict(row)
        return latest

    def _canonical_for_revision(self, revision) -> dict:
        try:
            canonical = parse_shot_prompt_json(self.runtime_store.read_text(revision.content_object_id))
            validate_shot_prompt_canonical(canonical)
        except CanonicalShotPromptError as exc:
            raise ShotPromptInvalidContent("CANONICAL_VALIDATION_FAILED", exc.safe_message) from exc
        return canonical

    def _parse_and_validate_content(self, content: str) -> dict:
        try:
            canonical = parse_shot_prompt_json(content)
            validate_shot_prompt_canonical(canonical)
        except CanonicalShotPromptError as exc:
            raise ShotPromptInvalidContent("INVALID_REVISION_CONTENT", exc.safe_message) from exc
        return canonical

    def _shot_or_raise(self, canonical: dict, shot_id: str) -> dict:
        for shot in canonical["shots"]:
            if shot["shot_id"] == shot_id:
                return shot
        raise ShotPromptShotNotFound

    def _shot_prompt_revision_or_raise(self, revision_id: str):
        revision = self.runtime_store.get_revision(revision_id)
        if revision is None:
            raise MissingRecord
        if revision.artifact_type != "shot_prompt_set" or revision.content_profile != CONTENT_PROFILE:
            raise MissingRecord
        return revision

    def _chapter_or_raise(self, chapter_id: str):
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord
        return chapter

    def _shot_prompt_skill(self):
        try:
            registry = SkillRegistry.scan([self.settings.skills_root])
            return registry.get_ref(SHOT_PROMPT_SKILL_REF)
        except SkillNotFoundError as exc:
            raise WorkflowExecutionError("SKILL_NOT_FOUND", str(exc), status_code=503) from exc
        except DuplicateSkillError as exc:
            raise WorkflowExecutionError("SKILL_CONFIG_INVALID", str(exc), status_code=503) from exc
