from __future__ import annotations

import hashlib
import json
import math
import unicodedata


SCHEMA_VERSION = "shot-prompt-canonical-v1"
CONTENT_PROFILE = "shot-prompt-canonical-v1"
SERIALIZATION_VERSION = "canonical-json-v1"
CANONICAL_PARSER_VERSION = "shot-prompt-canonical-json-v1"

TOP_LEVEL_KEYS = ["schema_version", "project_id", "chapter_id", "source_storyboard_revision_id", "shots"]
SHOT_KEYS = [
    "shot_id",
    "shot_order",
    "duration_seconds",
    "scene_id",
    "character_ids",
    "prop_ids",
    "asset_refs",
    "camera",
    "action",
    "emotion",
    "dialogue",
    "positive_prompt",
    "negative_prompt",
    "continuity_notes",
    "agnes_video_params",
]


class CanonicalShotPromptError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.safe_message = message


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "duplicate JSON key: %s" % key)
        result[key] = value
    return result


def _reject_constant(value):
    raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "non-finite number is not allowed: %s" % value)


def parse_shot_prompt_json(raw: str | bytes):
    if isinstance(raw, bytes):
        if raw.startswith(b"\xef\xbb\xbf"):
            raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "UTF-8 BOM is not allowed")
        raw = raw.decode("utf-8")
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)
    except CanonicalShotPromptError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", str(exc)) from exc


def _normalize(value):
    if isinstance(value, str):
        if value == "":
            raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "empty string is not allowed")
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", str(key)): _normalize(item) for key, item in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "non-finite number is not allowed")
    return value


def serialize_shot_prompt_json(data) -> bytes:
    normalized = _normalize(data)
    try:
        text = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except ValueError as exc:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", str(exc)) from exc
    return text.encode("utf-8")


def shot_prompt_content_hash(data) -> str:
    validate_shot_prompt_canonical(data)
    return hashlib.sha256(serialize_shot_prompt_json(data)).hexdigest()


def _require_object(value, path):
    if not isinstance(value, dict):
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s must be an object" % path)


def _require_array(value, path):
    if not isinstance(value, list):
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s must be an array" % path)


def _require_string(value, path):
    if not isinstance(value, str) or not value:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s must be a non-empty string" % path)


def _require_int(value, path):
    if not isinstance(value, int) or isinstance(value, bool):
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s must be an integer" % path)


def _require_required_keys(obj, keys, path):
    missing = [key for key in keys if key not in obj]
    if missing:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s missing required keys: %s" % (path, ",".join(missing)))
    extra = [key for key in obj if key not in keys]
    if extra:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s additional property not allowed: %s" % (path, ",".join(extra)))


def _validate_string_list(value, path, *, allow_empty: bool = True):
    _require_array(value, path)
    if not allow_empty and not value:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "%s must not be empty" % path)
    for index, item in enumerate(value):
        _require_string(item, "%s[%d]" % (path, index))


def validate_shot_prompt_canonical(data) -> None:
    _require_object(data, "shot_prompt")
    _require_required_keys(data, TOP_LEVEL_KEYS, "shot_prompt")
    if data["schema_version"] != SCHEMA_VERSION:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "schema_version must be %s" % SCHEMA_VERSION)
    _require_string(data["project_id"], "project_id")
    _require_string(data["chapter_id"], "chapter_id")
    _require_string(data["source_storyboard_revision_id"], "source_storyboard_revision_id")
    _validate_shots(data["shots"])


def _validate_shots(shots):
    _require_array(shots, "shots")
    if not shots:
        raise CanonicalShotPromptError("CANONICAL_SCHEMA_INVALID", "shots must not be empty")
    seen_ids = set()
    order_by_scene = {}
    for index, shot in enumerate(shots):
        path = "shots[%d]" % index
        _require_object(shot, path)
        _require_required_keys(shot, SHOT_KEYS, path)
        _require_string(shot["shot_id"], path + ".shot_id")
        shot_id = unicodedata.normalize("NFC", shot["shot_id"])
        if shot_id in seen_ids:
            raise CanonicalShotPromptError("SHOT_ID_INVALID", "%s.shot_id is duplicated" % path)
        seen_ids.add(shot_id)
        _require_int(shot["shot_order"], path + ".shot_order")
        _require_int(shot["duration_seconds"], path + ".duration_seconds")
        if not 5 <= shot["duration_seconds"] <= 15:
            raise CanonicalShotPromptError("SHOT_PROMPT_DURATION_INVALID", "%s.duration_seconds must be 5-15" % path)
        _require_string(shot["scene_id"], path + ".scene_id")
        scene_id = unicodedata.normalize("NFC", shot["scene_id"])
        previous_order = order_by_scene.get(scene_id, 0)
        if shot["shot_order"] <= previous_order:
            raise CanonicalShotPromptError("SHOT_ORDER_INVALID", "%s.shot_order must strictly increase in scene" % path)
        order_by_scene[scene_id] = shot["shot_order"]
        _validate_string_list(shot["character_ids"], path + ".character_ids")
        _validate_string_list(shot["prop_ids"], path + ".prop_ids")
        _validate_string_list(shot["asset_refs"], path + ".asset_refs", allow_empty=False)
        _require_object(shot["camera"], path + ".camera")
        _require_string(shot["action"], path + ".action")
        _require_string(shot["emotion"], path + ".emotion")
        _require_array(shot["dialogue"], path + ".dialogue")
        _require_string(shot["positive_prompt"], path + ".positive_prompt")
        _require_string(shot["negative_prompt"], path + ".negative_prompt")
        _validate_string_list(shot["continuity_notes"], path + ".continuity_notes")
        _require_object(shot["agnes_video_params"], path + ".agnes_video_params")
