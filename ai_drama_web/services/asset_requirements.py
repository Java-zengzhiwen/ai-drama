import json

from ai_drama_runtime.storyboard_canonical import (
    CONTENT_PROFILE,
    CanonicalStoryboardError,
    canonical_storyboard_hash,
    parse_canonical_json,
    validate_storyboard_canonical,
)
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


READY = "ready"
MISSING_ASSETS = "missing_assets"
ASSET_GENERATION_IN_PROGRESS = "asset_generation_in_progress"
ASSET_REVIEW_REQUIRED = "asset_review_required"


class StoryboardNotApproved(Exception):
    pass


class AssetRequirementsNotAnalyzed(Exception):
    pass


class AssetRequirementService:
    def __init__(self, product_store: ProductStore, runtime_store: RuntimeStore):
        self.product_store = product_store
        self.runtime_store = runtime_store

    def analyze(self, chapter_id: str):
        chapter = self._chapter_or_raise(chapter_id)
        revision = self._approved_storyboard_or_raise(chapter_id)
        canonical = self._canonical_storyboard_or_raise(chapter.project_id, chapter.chapter_id, revision)
        payload = self._analyze_payload(chapter.project_id, chapter.chapter_id, revision, canonical)
        record = self.product_store.create_asset_requirement_set(
            chapter_id=chapter.chapter_id,
            storyboard_revision_id=revision.revision_id,
            payload=payload,
        )
        return self._read_requirement_set(record)

    def latest(self, chapter_id: str):
        self._chapter_or_raise(chapter_id)
        record = self.product_store.latest_asset_requirement_set(chapter_id)
        if record is None:
            raise AssetRequirementsNotAnalyzed
        return self._read_requirement_set(record)

    def _analyze_payload(self, project_id: str, chapter_id: str, revision, canonical: dict):
        profiles = self._profiles(project_id, chapter_id)
        scenes_by_id = {scene["scene_id"]: scene for scene in canonical["scenes"]}
        shot_rows = []
        for shot in canonical["shots"]:
            scene = scenes_by_id[shot["scene_id"]]
            needs = self._shot_needs(shot, scene, profiles)
            evaluated = [self._evaluate_need(project_id, chapter_id, need) for need in needs]
            shot_rows.append(self._shot_row(shot["shot_id"], evaluated))
        return {
            "status": _overall_status([row["status"] for row in shot_rows]),
            "storyboard_content_hash": revision.content_hash,
            "shot_rows": shot_rows,
            "missing_assets": _flatten(shot_rows, MISSING_ASSETS),
            "asset_generation_in_progress": _flatten(shot_rows, ASSET_GENERATION_IN_PROGRESS),
            "asset_review_required": _flatten(shot_rows, ASSET_REVIEW_REQUIRED),
        }

    def _profiles(self, project_id: str, chapter_id: str):
        profiles = [
            record
            for record in self.product_store.list_production_profiles(project_id)
            if record.chapter_id in {"", chapter_id}
        ]
        payloads = {
            record.profile_id: json.loads(self.runtime_store.read_text(record.payload_object_id))
            for record in profiles
        }
        by_type = {"character": [], "scene": [], "prop": []}
        for record in profiles:
            if record.profile_type in by_type:
                by_type[record.profile_type].append((record, payloads[record.profile_id]))
        for items in by_type.values():
            items.sort(key=lambda item: 0 if item[0].chapter_id == chapter_id else 1)
        return by_type

    def _shot_needs(self, shot: dict, scene: dict, profiles: dict):
        needs = []
        for character_id in _shot_character_ids(shot, scene):
            profile = _match_profile(profiles["character"], character_id)
            needs.append(
                _need(
                    "character_asset",
                    "character",
                    profile.profile_id if profile is not None else character_id,
                    "primary_reference",
                    "character_reference",
                )
            )
        scene_profile = _match_profile(profiles["scene"], scene["scene_id"], scene.get("location"))
        needs.append(
            _need(
                "scene_asset",
                "scene",
                scene_profile.profile_id if scene_profile is not None else scene["scene_id"],
                "layout_reference",
                "scene_reference",
            )
        )
        shot_text = json.dumps({"shot": shot, "scene": scene}, ensure_ascii=False)
        for profile, payload in profiles["prop"]:
            names = {profile.profile_id, profile.name, payload.get("name", "")}
            if any(name and name in shot_text for name in names):
                needs.append(_need("prop_asset", "prop", profile.profile_id, "handling_reference", "prop_reference"))
        needs.append(_need("shot_keyframe", "shot", shot["shot_id"], "keyframe", "shot_keyframe"))
        return needs

    def _evaluate_need(self, project_id: str, chapter_id: str, need: dict):
        bindings = self.product_store.asset_bindings_for_requirement(
            project_id=project_id,
            chapter_id=chapter_id,
            target_type=need["target_type"],
            target_id=need["target_id"],
            role=need["role"],
            asset_type=need["asset_type"],
        )
        ready = next((item for item in bindings if item["status"] == "usable" and item["is_current"] == 1), None)
        if ready is not None:
            return {**need, "asset_id": ready["asset_id"], "status": READY}
        generating = next((item for item in bindings if item["status"] == "generating"), None)
        if generating is not None:
            return {**need, "asset_id": generating["asset_id"], "status": ASSET_GENERATION_IN_PROGRESS}
        review = next((item for item in bindings if item["status"] in {"draft", "failed", "rejected", "usable"}), None)
        if review is not None:
            return {**need, "asset_id": review["asset_id"], "status": ASSET_REVIEW_REQUIRED}
        return {**need, "status": MISSING_ASSETS}

    def _shot_row(self, shot_id: str, evaluated: list[dict]):
        return {
            "shot_id": shot_id,
            "status": _overall_status([item["status"] for item in evaluated]),
            "ready": [item for item in evaluated if item["status"] == READY],
            "missing_assets": [item for item in evaluated if item["status"] == MISSING_ASSETS],
            "asset_generation_in_progress": [
                item for item in evaluated if item["status"] == ASSET_GENERATION_IN_PROGRESS
            ],
            "asset_review_required": [item for item in evaluated if item["status"] == ASSET_REVIEW_REQUIRED],
        }

    def _read_requirement_set(self, record: dict):
        payload = record["payload"]
        return {
            "requirement_set_id": record["requirement_set_id"],
            "chapter_id": record["chapter_id"],
            "storyboard_revision_id": record["storyboard_revision_id"],
            "storyboard_content_hash": payload["storyboard_content_hash"],
            "content_object_id": record["content_object_id"],
            "content_hash": record["content_hash"],
            "created_at": record["created_at"],
            "status": payload["status"],
            "shot_rows": payload["shot_rows"],
            "missing_assets": payload["missing_assets"],
            "asset_generation_in_progress": payload["asset_generation_in_progress"],
            "asset_review_required": payload["asset_review_required"],
        }

    def _chapter_or_raise(self, chapter_id: str):
        chapter = self.product_store.get_chapter(chapter_id)
        if chapter is None:
            raise MissingRecord
        return chapter

    def _approved_storyboard_or_raise(self, chapter_id: str):
        revision = self.runtime_store.current_approved(f"{chapter_id}:script:storyboard")
        if revision is None or revision.content_profile != CONTENT_PROFILE:
            raise StoryboardNotApproved
        return revision

    def _canonical_storyboard_or_raise(self, project_id: str, chapter_id: str, revision):
        try:
            canonical = parse_canonical_json(self.runtime_store.read_text(revision.content_object_id))
            validate_storyboard_canonical(canonical)
        except CanonicalStoryboardError as exc:
            raise StoryboardNotApproved from exc
        if canonical.get("project_id") != project_id:
            raise StoryboardNotApproved
        if canonical.get("chapter_id") != chapter_id:
            raise StoryboardNotApproved
        if canonical.get("source", {}).get("script_artifact_id") != f"{chapter_id}:script":
            raise StoryboardNotApproved
        if canonical_storyboard_hash(canonical) != revision.content_hash:
            raise StoryboardNotApproved
        return canonical


def _need(need_type, target_type, target_id, role, asset_type):
    return {
        "need_type": need_type,
        "target_type": target_type,
        "target_id": target_id,
        "role": role,
        "asset_type": asset_type,
    }


def _shot_character_ids(shot: dict, scene: dict):
    character_ids = []
    for character_id in scene["characters"]:
        _append_once(character_ids, character_id)
    for item in shot["character_positions"]:
        _append_once(character_ids, item["character_id"])
    for item in shot["character_actions"]:
        _append_once(character_ids, item["character_id"])
    for item in shot["emotion_performance"]:
        _append_once(character_ids, item["character_id"])
    for item in shot["dialogue"]:
        _append_once(character_ids, item["speaker_character_id"])
    return character_ids


def _append_once(items, value):
    if value not in items:
        items.append(value)


def _match_profile(candidates, *values):
    wanted = {value for value in values if value}
    for profile, payload in candidates:
        names = {profile.profile_id, profile.name, payload.get("name", "")}
        if wanted & names:
            return profile
    return None


def _overall_status(statuses):
    if any(status == ASSET_GENERATION_IN_PROGRESS for status in statuses):
        return ASSET_GENERATION_IN_PROGRESS
    if any(status == ASSET_REVIEW_REQUIRED for status in statuses):
        return ASSET_REVIEW_REQUIRED
    if any(status == MISSING_ASSETS for status in statuses):
        return MISSING_ASSETS
    return READY


def _flatten(shot_rows, key):
    items = []
    for row in shot_rows:
        items.extend(row[key])
    return items
