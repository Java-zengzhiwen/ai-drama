from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata


SCHEMA_VERSION = "storyboard-canonical-v1"
CONTENT_PROFILE = "storyboard-canonical-v1"
SERIALIZATION_VERSION = "canonical-json-v1"
CANONICAL_PARSER_VERSION = "storyboard-canonical-json-v1"

SCENE_ID_RE = re.compile(r"^SCENE_[A-Z0-9][A-Z0-9_-]*$")
SHOT_ID_RE = re.compile(r"^SHOT_[A-Z0-9][A-Z0-9_-]*$")


class CanonicalStoryboardError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.safe_message = message


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "duplicate JSON key: %s" % key)
        result[key] = value
    return result


def parse_canonical_json(raw: str | bytes):
    if isinstance(raw, bytes):
        if raw.startswith(b"\xef\xbb\xbf"):
            raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "UTF-8 BOM is not allowed")
        raw = raw.decode("utf-8")
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)
    except CanonicalStoryboardError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", str(exc)) from exc


def _reject_constant(value):
    raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "non-finite number is not allowed: %s" % value)


def _normalize(value):
    if isinstance(value, str):
        if value == "":
            raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "empty string is not allowed")
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", str(key)): _normalize(item) for key, item in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "non-finite number is not allowed")
    return value


def serialize_canonical_json(data) -> bytes:
    normalized = _normalize(data)
    try:
        text = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except ValueError as exc:
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", str(exc)) from exc
    return text.encode("utf-8")


def canonical_storyboard_hash(data) -> str:
    validate_storyboard_canonical(data)
    return hashlib.sha256(serialize_canonical_json(data)).hexdigest()


def _require_object(value, path):
    if not isinstance(value, dict):
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "%s must be an object" % path)


def _require_array(value, path):
    if not isinstance(value, list):
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "%s must be an array" % path)


def _require_string(value, path):
    if not isinstance(value, str) or not value:
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "%s must be a non-empty string" % path)


def _require_nullable_string(value, path):
    if value is not None:
        _require_string(value, path)


def _require_int(value, path):
    if not isinstance(value, int) or isinstance(value, bool):
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "%s must be an integer" % path)


def _require_required_keys(obj, keys, path):
    missing = [key for key in keys if key not in obj]
    if missing:
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "%s missing required keys: %s" % (path, ",".join(missing)))


def validate_storyboard_canonical(data) -> None:
    _require_object(data, "storyboard")
    _require_required_keys(data, ["schema_version", "project_id", "chapter_id", "source", "scenes", "shots"], "storyboard")
    if data["schema_version"] != SCHEMA_VERSION:
        raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", "schema_version must be %s" % SCHEMA_VERSION)
    _require_string(data["project_id"], "project_id")
    _require_string(data["chapter_id"], "chapter_id")
    _validate_source(data["source"])
    _validate_scenes(data["scenes"])
    _validate_shots(data["shots"], {scene["scene_id"] for scene in data["scenes"]})


def _validate_source(source):
    _require_object(source, "source")
    _require_required_keys(source, ["script_artifact_id", "script_revision_id", "script_content_hash"], "source")
    _require_string(source["script_artifact_id"], "source.script_artifact_id")
    _require_string(source["script_revision_id"], "source.script_revision_id")
    _require_string(source["script_content_hash"], "source.script_content_hash")


def _validate_scenes(scenes):
    _require_array(scenes, "scenes")
    seen_ids = set()
    previous_order = 0
    for index, scene in enumerate(scenes):
        path = "scenes[%d]" % index
        _require_object(scene, path)
        _require_required_keys(
            scene,
            ["scene_id", "scene_order", "source_scene_reference", "location", "time", "interior_exterior", "characters", "summary"],
            path,
        )
        _require_string(scene["scene_id"], path + ".scene_id")
        if not SCENE_ID_RE.match(scene["scene_id"]):
            raise CanonicalStoryboardError("SHOT_ID_INVALID", "%s.scene_id is invalid" % path)
        if scene["scene_id"] in seen_ids:
            raise CanonicalStoryboardError("SHOT_ID_INVALID", "%s.scene_id is duplicated" % path)
        seen_ids.add(scene["scene_id"])
        _require_int(scene["scene_order"], path + ".scene_order")
        if scene["scene_order"] <= previous_order:
            raise CanonicalStoryboardError("SHOT_ORDER_INVALID", "%s.scene_order must strictly increase" % path)
        previous_order = scene["scene_order"]
        _require_string(scene["source_scene_reference"], path + ".source_scene_reference")
        _require_nullable_string(scene["location"], path + ".location")
        _require_nullable_string(scene["time"], path + ".time")
        _require_nullable_string(scene["interior_exterior"], path + ".interior_exterior")
        _require_array(scene["characters"], path + ".characters")
        for character in scene["characters"]:
            _require_string(character, path + ".characters[]")
        _require_string(scene["summary"], path + ".summary")


def _validate_shots(shots, scene_ids):
    _require_array(shots, "shots")
    seen_ids = set()
    order_by_scene = {}
    action_order_by_shot = {}
    for index, shot in enumerate(shots):
        path = "shots[%d]" % index
        _require_object(shot, path)
        _require_required_keys(
            shot,
            [
                "scene_id",
                "shot_id",
                "shot_order",
                "source_scene_reference",
                "duration_seconds",
                "shot_size",
                "camera_angle",
                "camera_movement",
                "visual_composition",
                "character_positions",
                "character_actions",
                "emotion_performance",
                "dialogue",
                "sound_notes",
                "continuity_in",
                "continuity_out",
            ],
            path,
        )
        _require_string(shot["scene_id"], path + ".scene_id")
        if shot["scene_id"] not in scene_ids:
            raise CanonicalStoryboardError("SHOT_MAPPING_INVALID", "%s.scene_id does not reference an existing scene" % path)
        _require_string(shot["shot_id"], path + ".shot_id")
        if not SHOT_ID_RE.match(shot["shot_id"]):
            raise CanonicalStoryboardError("SHOT_ID_INVALID", "%s.shot_id is invalid" % path)
        if shot["shot_id"] in seen_ids:
            raise CanonicalStoryboardError("SHOT_ID_INVALID", "%s.shot_id is duplicated" % path)
        seen_ids.add(shot["shot_id"])
        _require_int(shot["shot_order"], path + ".shot_order")
        previous = order_by_scene.get(shot["scene_id"], 0)
        if shot["shot_order"] <= previous:
            raise CanonicalStoryboardError("SHOT_ORDER_INVALID", "%s.shot_order must strictly increase in scene" % path)
        order_by_scene[shot["scene_id"]] = shot["shot_order"]
        _require_string(shot["source_scene_reference"], path + ".source_scene_reference")
        _require_int(shot["duration_seconds"], path + ".duration_seconds")
        if not 5 <= shot["duration_seconds"] <= 15:
            raise CanonicalStoryboardError("STORYBOARD_DURATION_INVALID", "%s.duration_seconds must be 5-15" % path)
        _require_string(shot["shot_size"], path + ".shot_size")
        _require_string(shot["camera_angle"], path + ".camera_angle")
        if shot["camera_movement"] is not None:
            _require_object(shot["camera_movement"], path + ".camera_movement")
        _validate_visual_composition(shot["visual_composition"], path + ".visual_composition")
        _validate_character_positions(shot["character_positions"], path + ".character_positions")
        action_order_by_shot[shot["shot_id"]] = _validate_character_actions(shot["character_actions"], path + ".character_actions")
        _validate_emotion_performance(shot["emotion_performance"], path + ".emotion_performance")
        _validate_dialogue(shot["dialogue"], path + ".dialogue")
        _validate_sound_notes(shot["sound_notes"], path + ".sound_notes")
        _validate_continuity(shot["continuity_in"], path + ".continuity_in")
        _validate_continuity(shot["continuity_out"], path + ".continuity_out")


def _validate_visual_composition(value, path):
    _require_object(value, path)
    _require_required_keys(value, ["framing", "subject_focus", "background_relation", "screen_direction"], path)
    _require_string(value["framing"], path + ".framing")
    _require_string(value["subject_focus"], path + ".subject_focus")
    _require_string(value["background_relation"], path + ".background_relation")
    _require_nullable_string(value["screen_direction"], path + ".screen_direction")


def _validate_character_positions(value, path):
    _require_array(value, path)
    for index, item in enumerate(value):
        item_path = "%s[%d]" % (path, index)
        _require_object(item, item_path)
        _require_required_keys(item, ["character_id", "screen_zone", "depth", "pose", "facing"], item_path)
        _require_string(item["character_id"], item_path + ".character_id")
        _require_string(item["screen_zone"], item_path + ".screen_zone")
        _require_string(item["depth"], item_path + ".depth")
        _require_string(item["pose"], item_path + ".pose")
        _require_nullable_string(item["facing"], item_path + ".facing")


def _validate_character_actions(value, path):
    _require_array(value, path)
    previous = 0
    for index, item in enumerate(value):
        item_path = "%s[%d]" % (path, index)
        _require_object(item, item_path)
        _require_required_keys(item, ["character_id", "action_order", "action"], item_path)
        _require_string(item["character_id"], item_path + ".character_id")
        _require_int(item["action_order"], item_path + ".action_order")
        if item["action_order"] <= previous:
            raise CanonicalStoryboardError("SHOT_ORDER_INVALID", "%s.action_order must strictly increase" % item_path)
        previous = item["action_order"]
        _require_string(item["action"], item_path + ".action")
    return previous


def _validate_emotion_performance(value, path):
    _require_array(value, path)
    for index, item in enumerate(value):
        item_path = "%s[%d]" % (path, index)
        _require_object(item, item_path)
        _require_required_keys(item, ["character_id", "emotion", "intensity", "performance_note"], item_path)
        _require_string(item["character_id"], item_path + ".character_id")
        _require_string(item["emotion"], item_path + ".emotion")
        _require_string(item["intensity"], item_path + ".intensity")
        _require_nullable_string(item["performance_note"], item_path + ".performance_note")


def _validate_dialogue(value, path):
    _require_array(value, path)
    for index, item in enumerate(value):
        item_path = "%s[%d]" % (path, index)
        _require_object(item, item_path)
        _require_required_keys(item, ["speaker_character_id", "text", "lip_sync_required"], item_path)
        _require_string(item["speaker_character_id"], item_path + ".speaker_character_id")
        _require_string(item["text"], item_path + ".text")
        if not isinstance(item["lip_sync_required"], bool):
            raise CanonicalStoryboardError("CANONICAL_SCHEMA_INVALID", item_path + ".lip_sync_required must be boolean")


def _validate_sound_notes(value, path):
    _require_array(value, path)
    for item in value:
        _require_string(item, path + "[]")


def _validate_continuity(value, path):
    _require_object(value, path)
    _require_required_keys(value, ["must_preserve", "must_change", "source_unit_or_shot_id"], path)
    _require_array(value["must_preserve"], path + ".must_preserve")
    _require_array(value["must_change"], path + ".must_change")
    for item in value["must_preserve"] + value["must_change"]:
        _require_string(item, path + "[]")
    _require_nullable_string(value["source_unit_or_shot_id"], path + ".source_unit_or_shot_id")
