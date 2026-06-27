import json


PARSER_VERSION = "drama-script-markdown-v1"


class ParseError(ValueError):
    pass


def parse_script_response(raw):
    if not raw or not raw.strip():
        raise ParseError("empty runtime response")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        text = raw
    else:
        text = data.get("script_markdown") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise ParseError("runtime response does not contain script_markdown")
    if not text.lstrip().startswith("#"):
        raise ParseError("script_markdown does not match Markdown script contract")
    return text
