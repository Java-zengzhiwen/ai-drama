import copy
import json

import pytest

from ai_drama_runtime.parser import ParseError, parse_shot_prompt_canonical_response
from ai_drama_runtime.shot_prompt_canonical import (
    SCHEMA_VERSION,
    CanonicalShotPromptError,
    parse_shot_prompt_json,
    serialize_shot_prompt_json,
    shot_prompt_content_hash,
    validate_shot_prompt_canonical,
)


def _valid_payload():
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "project-001",
        "chapter_id": "chapter-001",
        "source_storyboard_revision_id": "storyboard-rev-001",
        "shots": [
            {
                "shot_id": "SHOT_001",
                "shot_order": 1,
                "duration_seconds": 8,
                "scene_id": "SCENE_001",
                "character_ids": ["CHAR_MING"],
                "prop_ids": ["PROP_RING"],
                "asset_refs": ["asset-character-ming", "asset-scene-hall"],
                "camera": {"shot_size": "medium", "movement": "slow push in"},
                "action": "Ming closes the ring box before anyone notices.",
                "emotion": "contained panic",
                "dialogue": [{"speaker_character_id": "CHAR_MING", "text": "Not now."}],
                "positive_prompt": "Live action medium shot of Ming hiding a ring box in a bright hall.",
                "negative_prompt": "cartoon, face drift, costume change",
                "continuity_notes": ["Preserve Ming's blue jacket and left-to-right screen direction."],
                "agnes_video_params": {"duration_seconds": 8, "aspect_ratio": "16:9"},
            }
        ],
    }


def _chat_completion(content):
    return json.dumps(
        {
            "id": "chatcmpl-shot-prompt-test",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }
    )


def test_valid_payload_serializes_deterministically_and_hash_is_stable():
    left = _valid_payload()
    right = {
        "shots": copy.deepcopy(left["shots"]),
        "source_storyboard_revision_id": "storyboard-rev-001",
        "chapter_id": "chapter-001",
        "project_id": "project-001",
        "schema_version": SCHEMA_VERSION,
    }
    decomposed = copy.deepcopy(left)
    decomposed["shots"][0]["positive_prompt"] = "Live action medium shot of Ming hiding a ring box in a bright ha\u0301ll."
    composed = copy.deepcopy(left)
    composed["shots"][0]["positive_prompt"] = "Live action medium shot of Ming hiding a ring box in a bright h\u00e1ll."

    assert serialize_shot_prompt_json(left) == serialize_shot_prompt_json(right)
    assert serialize_shot_prompt_json(decomposed) == serialize_shot_prompt_json(composed)
    assert shot_prompt_content_hash(left) == shot_prompt_content_hash(right)
    assert len(shot_prompt_content_hash(left)) == 64


def test_duplicate_shot_id_is_rejected():
    payload = _valid_payload()
    duplicate = copy.deepcopy(payload["shots"][0])
    duplicate["shot_order"] = 2
    payload["shots"].append(duplicate)

    with pytest.raises(CanonicalShotPromptError, match="duplicated"):
        validate_shot_prompt_canonical(payload)


def test_duplicate_shot_id_after_nfc_normalization_is_rejected():
    payload = _valid_payload()
    second = copy.deepcopy(payload["shots"][0])
    payload["shots"][0]["shot_id"] = "SHOT_\u00c9"
    second["shot_id"] = "SHOT_E\u0301"
    second["shot_order"] = 2
    payload["shots"].append(second)

    with pytest.raises(CanonicalShotPromptError, match="duplicated"):
        validate_shot_prompt_canonical(payload)


@pytest.mark.parametrize("second_order", [1, 0])
def test_shot_order_must_strictly_increase_within_scene(second_order):
    payload = _valid_payload()
    second = copy.deepcopy(payload["shots"][0])
    second["shot_id"] = "SHOT_002"
    second["shot_order"] = second_order
    payload["shots"].append(second)

    with pytest.raises(CanonicalShotPromptError) as exc:
        validate_shot_prompt_canonical(payload)

    assert exc.value.code == "SHOT_ORDER_INVALID"


def test_duplicate_json_key_is_rejected():
    raw = '{"schema_version":"shot-prompt-canonical-v1","schema_version":"shot-prompt-canonical-v1"}'

    with pytest.raises(CanonicalShotPromptError, match="duplicate JSON key"):
        parse_shot_prompt_json(raw)


@pytest.mark.parametrize("duration", [4, 16])
def test_duration_must_be_between_five_and_fifteen_seconds(duration):
    payload = _valid_payload()
    payload["shots"][0]["duration_seconds"] = duration

    with pytest.raises(CanonicalShotPromptError, match="duration_seconds"):
        validate_shot_prompt_canonical(payload)


def test_missing_positive_prompt_is_rejected():
    payload = _valid_payload()
    del payload["shots"][0]["positive_prompt"]

    with pytest.raises(CanonicalShotPromptError, match="positive_prompt"):
        validate_shot_prompt_canonical(payload)


@pytest.mark.parametrize("asset_refs", [None, []])
def test_missing_or_empty_asset_refs_are_rejected(asset_refs):
    payload = _valid_payload()
    if asset_refs is None:
        del payload["shots"][0]["asset_refs"]
    else:
        payload["shots"][0]["asset_refs"] = asset_refs

    with pytest.raises(CanonicalShotPromptError, match="asset_refs"):
        validate_shot_prompt_canonical(payload)


def test_extra_top_level_or_shot_fields_are_rejected():
    payload = _valid_payload()
    payload["unexpected"] = True
    with pytest.raises(CanonicalShotPromptError, match="additional property"):
        validate_shot_prompt_canonical(payload)

    payload = _valid_payload()
    payload["shots"][0]["unexpected"] = True
    with pytest.raises(CanonicalShotPromptError, match="additional property"):
        validate_shot_prompt_canonical(payload)


def test_parser_accepts_direct_json_and_openai_chat_completion_content():
    canonical_text = serialize_shot_prompt_json(_valid_payload()).decode("utf-8")

    direct = json.loads(parse_shot_prompt_canonical_response(canonical_text))
    wrapped = json.loads(parse_shot_prompt_canonical_response(_chat_completion(canonical_text)))

    assert direct == wrapped
    assert direct["schema_version"] == "shot-prompt-canonical-v1"
    assert direct["shots"][0]["shot_id"] == "SHOT_001"


def test_parser_rejects_duplicate_keys_inside_openai_content():
    duplicate_content = '{"schema_version":"shot-prompt-canonical-v1","schema_version":"shot-prompt-canonical-v1"}'

    with pytest.raises(ParseError) as exc:
        parse_shot_prompt_canonical_response(_chat_completion(duplicate_content))

    assert exc.value.code == "CANONICAL_SCHEMA_INVALID"
    assert "duplicate JSON key" in str(exc.value)
