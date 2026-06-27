import json

from ai_drama_runtime.parser import parse_script_response


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
