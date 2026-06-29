import pytest
from pathlib import Path

from ai_drama_runtime.storyboard_canonical import (
    CanonicalStoryboardError,
    canonical_storyboard_hash,
    parse_canonical_json,
    serialize_canonical_json,
    validate_storyboard_canonical,
)


def _valid_storyboard():
    return {
        "schema_version": "storyboard-canonical-v1",
        "project_id": "project-e\u0301",
        "chapter_id": "chapter-001",
        "source": {
            "script_artifact_id": "script-artifact",
            "script_revision_id": "script-revision",
            "script_content_hash": "a" * 64,
        },
        "scenes": [
            {
                "scene_id": "SCENE_001",
                "scene_order": 1,
                "source_scene_reference": "1-1",
                "location": None,
                "time": None,
                "interior_exterior": None,
                "characters": ["CHAR_A"],
                "summary": "Opening beat",
            }
        ],
        "shots": [
            {
                "scene_id": "SCENE_001",
                "shot_id": "SHOT_001",
                "shot_order": 1,
                "source_scene_reference": "1-1",
                "duration_seconds": 8,
                "shot_size": "medium",
                "camera_angle": "eye_level",
                "camera_movement": None,
                "visual_composition": {
                    "framing": "centered",
                    "subject_focus": "CHAR_A",
                    "background_relation": "quiet room",
                    "screen_direction": None,
                },
                "character_positions": [
                    {
                        "character_id": "CHAR_A",
                        "screen_zone": "center",
                        "depth": "foreground",
                        "pose": "standing",
                        "facing": None,
                    }
                ],
                "character_actions": [
                    {"character_id": "CHAR_A", "action_order": 1, "action": "looks up"}
                ],
                "emotion_performance": [],
                "dialogue": [],
                "sound_notes": [],
                "continuity_in": {
                    "must_preserve": ["wardrobe"],
                    "must_change": [],
                    "source_unit_or_shot_id": None,
                },
                "continuity_out": {
                    "must_preserve": ["wardrobe"],
                    "must_change": [],
                    "source_unit_or_shot_id": None,
                },
            }
        ],
    }


def _fixture_text(name):
    return Path("tests/fixtures/storyboard_canonical/%s" % name).read_text(encoding="utf-8")


def test_canonical_serialization_is_nfc_and_key_order_stable():
    left = _valid_storyboard()
    right = {
        "shots": left["shots"],
        "scenes": left["scenes"],
        "source": left["source"],
        "chapter_id": "chapter-001",
        "project_id": "project-é",
        "schema_version": "storyboard-canonical-v1",
    }

    assert serialize_canonical_json(left) == serialize_canonical_json(right)
    assert canonical_storyboard_hash(left) == canonical_storyboard_hash(right)
    assert serialize_canonical_json(left).decode("utf-8").endswith("\n") is False


def test_array_business_order_changes_hash():
    left = _valid_storyboard()
    right = _valid_storyboard()
    left["shots"][0]["sound_notes"] = ["first sound", "second sound"]
    right["shots"][0]["sound_notes"] = ["second sound", "first sound"]

    assert canonical_storyboard_hash(left) != canonical_storyboard_hash(right)


def test_duplicate_json_keys_are_rejected():
    raw = '{"schema_version":"storyboard-canonical-v1","schema_version":"storyboard-canonical-v1"}'

    with pytest.raises(CanonicalStoryboardError, match="duplicate JSON key"):
        parse_canonical_json(raw)


def test_nan_is_rejected_by_canonical_serializer():
    data = _valid_storyboard()
    data["shots"][0]["duration_seconds"] = float("nan")

    with pytest.raises(CanonicalStoryboardError, match="non-finite"):
        serialize_canonical_json(data)


def test_schema_rejects_null_required_array():
    data = _valid_storyboard()
    data["shots"][0]["dialogue"] = None

    with pytest.raises(CanonicalStoryboardError, match="dialogue"):
        validate_storyboard_canonical(data)


def test_schema_rejects_invalid_duration():
    data = _valid_storyboard()
    data["shots"][0]["duration_seconds"] = 4

    with pytest.raises(CanonicalStoryboardError, match="STORYBOARD_DURATION_INVALID"):
        validate_storyboard_canonical(data)


def test_required_invalid_fixtures_are_rejected():
    with pytest.raises(CanonicalStoryboardError, match="duplicate JSON key"):
        parse_canonical_json(_fixture_text("invalid_duplicate_key.json"))
    with pytest.raises(CanonicalStoryboardError, match="STORYBOARD_DURATION_INVALID"):
        validate_storyboard_canonical(parse_canonical_json(_fixture_text("invalid_duration.json")))
    with pytest.raises(CanonicalStoryboardError, match="SHOT_ORDER_INVALID"):
        validate_storyboard_canonical(parse_canonical_json(_fixture_text("invalid_order.json")))
