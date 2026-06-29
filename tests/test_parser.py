import json

import pytest

from ai_drama_runtime.parser import ParseError, parse_script_response, parse_storyboard_canonical_response, parse_storyboard_response


def test_parser_accepts_openai_chat_completion_json():
    raw = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": "# Script\n\n## Scene 1\n\nBody"
                    }
                }
            ]
        }
    )

    assert parse_script_response(raw).startswith("# Script")


def test_storyboard_parser_accepts_raw_markdown_and_json():
    raw = "# Storyboard\n\n## 场次：1-1\n\nshot_id: 1-1-01\nduration_seconds: 6\ncontinuity_in: a\ncontinuity_out: b\n"
    assert parse_storyboard_response(raw).startswith("# Storyboard")

    raw_json = json.dumps({"storyboard_markdown": raw})
    assert parse_storyboard_response(raw_json).startswith("# Storyboard")


@pytest.mark.parametrize(
    "raw, error",
    [
        ("", "STORYBOARD_PARSER_EMPTY_OUTPUT"),
        ("# Storyboard\n\n## 场次：1-1\n\nno shots", "STORYBOARD_PARSER_NO_SHOTS"),
        ("# Storyboard\n\nshot_id: x", "STORYBOARD_PARSER_NO_SCENES"),
    ],
)
def test_storyboard_parser_rejects_invalid_output(raw, error):
    with pytest.raises(Exception) as exc:
        parse_storyboard_response(raw)
    assert getattr(exc.value, "code", "") == error


def _canonical_text():
    from pathlib import Path

    return Path("tests/fixtures/storyboard_canonical/valid_minimal.json").read_text(encoding="utf-8")


def _chat_completion(content):
    return json.dumps(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1800000000,
            "model": "storyboard-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        }
    )


@pytest.mark.parametrize(
    "content",
    [
        _canonical_text(),
        json.dumps({"storyboard_canonical": json.loads(_canonical_text())}, ensure_ascii=False),
    ],
)
def test_canonical_parser_accepts_openai_chat_completion_wrappers(content):
    parsed = json.loads(parse_storyboard_canonical_response(_chat_completion(content)))

    assert parsed["schema_version"] == "storyboard-canonical-v1"
    assert parsed["shots"][0]["shot_id"] == "SHOT_001"


def test_canonical_parser_rejects_duplicate_keys_inside_openai_content():
    duplicate_content = '{"schema_version":"storyboard-canonical-v1","schema_version":"storyboard-canonical-v1"}'

    with pytest.raises(ParseError) as exc:
        parse_storyboard_canonical_response(_chat_completion(duplicate_content))

    assert exc.value.code == "CANONICAL_SCHEMA_INVALID"
    assert "duplicate JSON key" in str(exc.value)


def test_canonical_parser_rejects_openai_content_markdown_without_legacy_fallback():
    with pytest.raises(ParseError) as exc:
        parse_storyboard_canonical_response(_chat_completion("# Storyboard\n\n## Scene 1\n\nshot_id: x\n"))

    assert exc.value.code == "CANONICAL_SCHEMA_INVALID"
