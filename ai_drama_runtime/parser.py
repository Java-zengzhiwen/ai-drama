import json
import re


PARSER_VERSION = "drama-script-markdown-v1"
STORYBOARD_PARSER_VERSION = "storyboard-markdown-v1"
STORYBOARD_CANONICAL_PARSER_VERSION = "storyboard-canonical-json-v1"
SHOT_PROMPT_CANONICAL_PARSER_VERSION = "shot-prompt-canonical-json-v1"


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


def parse_storyboard_response(raw):
    if not raw or not raw.strip():
        raise ParseError("STORYBOARD_PARSER_EMPTY_OUTPUT", "empty runtime response")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        text = raw
    else:
        text = data.get("storyboard_markdown") if isinstance(data, dict) else None
        if text is None and isinstance(data, dict):
            choices = data.get("choices") or []
            if choices and isinstance(choices[0], dict):
                text = (choices[0].get("message") or {}).get("content")
    if not isinstance(text, str) or not text.strip():
        raise ParseError("STORYBOARD_PARSER_INVALID_OUTPUT", "runtime response does not contain storyboard_markdown")
    if not text.lstrip().startswith("#"):
        raise ParseError("STORYBOARD_PARSER_INVALID_OUTPUT", "storyboard_markdown does not match Markdown storyboard contract")
    if not re.search(r"^##\s*(场次|Scene)\b", text, flags=re.M):
        raise ParseError("STORYBOARD_PARSER_NO_SCENES", "storyboard markdown does not contain scene headings")
    if not re.search(r"\bshot_id\s*:", text) and not re.search(r"^###\s*镜头\b", text, flags=re.M):
        raise ParseError("STORYBOARD_PARSER_NO_SHOTS", "storyboard markdown does not contain shot markers")
    return text


def parse_storyboard_canonical_response(raw):
    from .storyboard_canonical import CanonicalStoryboardError, parse_canonical_json, serialize_canonical_json, validate_storyboard_canonical

    if not raw or not raw.strip():
        raise ParseError("STORYBOARD_PARSER_EMPTY_OUTPUT", "empty runtime response")
    try:
        data = parse_canonical_json(raw)
    except CanonicalStoryboardError as exc:
        raise ParseError(exc.code, exc.safe_message) from exc
    if isinstance(data, dict) and "storyboard_canonical" in data:
        data = data["storyboard_canonical"]
    elif isinstance(data, dict) and "choices" in data:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ParseError("CANONICAL_SCHEMA_INVALID", "OpenAI-compatible response does not contain choices[0].message.content") from exc
        if not isinstance(content, str) or not content.strip():
            raise ParseError("CANONICAL_SCHEMA_INVALID", "OpenAI-compatible response content must be non-empty JSON text")
        try:
            data = parse_canonical_json(content)
        except CanonicalStoryboardError as exc:
            raise ParseError(exc.code, exc.safe_message) from exc
        if isinstance(data, dict) and "storyboard_canonical" in data:
            data = data["storyboard_canonical"]
    try:
        validate_storyboard_canonical(data)
        return serialize_canonical_json(data).decode("utf-8")
    except CanonicalStoryboardError as exc:
        raise ParseError(exc.code, exc.safe_message) from exc


def parse_shot_prompt_canonical_response(raw):
    from .shot_prompt_canonical import (
        CanonicalShotPromptError,
        parse_shot_prompt_json,
        serialize_shot_prompt_json,
        validate_shot_prompt_canonical,
    )

    if not raw or not raw.strip():
        raise ParseError("SHOT_PROMPT_PARSER_EMPTY_OUTPUT", "empty runtime response")
    try:
        data = parse_shot_prompt_json(raw)
    except CanonicalShotPromptError as exc:
        raise ParseError(exc.code, exc.safe_message) from exc
    if isinstance(data, dict) and "shot_prompt_canonical" in data:
        data = data["shot_prompt_canonical"]
    elif isinstance(data, dict) and "choices" in data:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ParseError("CANONICAL_SCHEMA_INVALID", "OpenAI-compatible response does not contain choices[0].message.content") from exc
        if not isinstance(content, str) or not content.strip():
            raise ParseError("CANONICAL_SCHEMA_INVALID", "OpenAI-compatible response content must be non-empty JSON text")
        try:
            data = parse_shot_prompt_json(content)
        except CanonicalShotPromptError as exc:
            raise ParseError(exc.code, exc.safe_message) from exc
        if isinstance(data, dict) and "shot_prompt_canonical" in data:
            data = data["shot_prompt_canonical"]
    try:
        validate_shot_prompt_canonical(data)
        return serialize_shot_prompt_json(data).decode("utf-8")
    except CanonicalShotPromptError as exc:
        raise ParseError(exc.code, exc.safe_message) from exc
