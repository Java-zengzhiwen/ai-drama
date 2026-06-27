from dataclasses import dataclass
import json
import os
import time


class RuntimeErrorBase(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.safe_message = message


@dataclass(frozen=True)
class RuntimeResponse:
    raw: str
    provider: str
    model: str
    usage: dict
    duration_ms: int


def _mock_script(model):
    return """# Mock Drama Script Revision

runtime_model: %s
source_basis: manifest

## Scene 1

【画面】
女主在清晨醒来，意识到命运重启。

【动作】
她检查身边物件，确认眼前不是幻觉。

【台词】
女主：这一世，我要先看清局。

## Scene 2

【画面】
账册摊开，旧日线索重新浮现。

【动作】
她整理证据，把危险关系和家族账目分开标记。

【台词】
女主：账不会骗人，人心才会。
""" % model


def run_runtime(runtime, model, request_text, skill_instructions, mock_mode="success", timeout_seconds=60):
    started = time.time()
    if runtime == "mock":
        if mock_mode == "runtime_failure":
            raise RuntimeErrorBase("MOCK_RUNTIME_FAILURE", "mock runtime failure")
        if mock_mode == "empty_response":
            raw = ""
        elif mock_mode == "parse_failure":
            raw = json.dumps({"not_script": "bad"}, ensure_ascii=False)
        else:
            raw = json.dumps({"script_markdown": _mock_script(model)}, ensure_ascii=False)
        return RuntimeResponse(
            raw=raw,
            provider="mock",
            model=model,
            usage={"prompt_chars": len(request_text), "completion_chars": len(raw)},
            duration_ms=int((time.time() - started) * 1000),
        )
    if runtime == "openai-compatible":
        return _run_openai_compatible(model, request_text, skill_instructions, timeout_seconds, started)
    raise RuntimeErrorBase("UNKNOWN_RUNTIME", "unknown runtime: %s" % runtime)


def _run_openai_compatible(model, request_text, skill_instructions, timeout_seconds, started):
    api_key = os.environ.get("AI_DRAMA_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeErrorBase("CONFIG_MISSING_API_KEY", "API key is required")
    model = model or os.environ.get("AI_DRAMA_MODEL")
    if not model:
        raise RuntimeErrorBase("CONFIG_MISSING_MODEL", "model is required")
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeErrorBase("OPENAI_SDK_MISSING", "openai package is required") from exc
    base_url = os.environ.get("AI_DRAMA_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or None
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Follow the skill instructions and return only the creator-facing Markdown script.",
                },
                {"role": "user", "content": skill_instructions + "\n\n" + request_text},
            ],
        )
    except Exception as exc:
        raise RuntimeErrorBase("OPENAI_RUNTIME_ERROR", "openai-compatible runtime failed") from exc
    usage = getattr(response, "usage", None)
    return RuntimeResponse(
        raw=response.model_dump_json(),
        provider="openai-compatible",
        model=model,
        usage=usage.model_dump() if usage else {},
        duration_ms=int((time.time() - started) * 1000),
    )
