import json


PARSER_VERSION = "drama-script-markdown-v1"


class ParseError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def parse_script_response(raw):
    if not raw or not raw.strip():
        raise ParseError("PARSER_EMPTY_OUTPUT", "empty runtime response")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        text = raw
    else:
        text = data.get("script_markdown") if isinstance(data, dict) else None
        if text is None and isinstance(data, dict):
            choices = data.get("choices") or []
            if choices and isinstance(choices[0], dict):
                text = (choices[0].get("message") or {}).get("content")
    if not isinstance(text, str) or not text.strip():
        raise ParseError("PARSER_INVALID_OUTPUT", "runtime response does not contain script_markdown")
    if not text.lstrip().startswith("#"):
        raise ParseError("PARSER_INVALID_OUTPUT", "script_markdown does not match Markdown script contract")
    return text
