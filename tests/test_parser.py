import json

import pytest

from ai_drama_runtime.parser import parse_script_response, parse_storyboard_response


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
