from dataclasses import dataclass
import json
import os


class RuntimeErrorBase(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeResponse:
    text: str
    raw: str
    model: str


def _mock_script(request_text, model):
    source_hint = "source"
    for line in request_text.splitlines():
        if line.startswith("Acceptance manifest:"):
            source_hint = "manifest"
            break
    body = """# Mock Drama Script Revision

runtime_model: %s
source_basis: %s

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
""" % (model, source_hint)
    return body


def run_runtime(runtime, model, request_text, skill_instructions):
    if runtime == "mock":
        text = _mock_script(request_text, model)
        return RuntimeResponse(
            text=text,
            raw=json.dumps({"script_markdown": text}, ensure_ascii=False),
            model=model,
        )
    if runtime in {"openai", "openai-compatible"}:
        return _run_openai_compatible(model, request_text, skill_instructions)
    raise RuntimeErrorBase("unknown runtime: %s" % runtime)


def _run_openai_compatible(model, request_text, skill_instructions):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeErrorBase("OPENAI_API_KEY is required for openai-compatible runtime")
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeErrorBase("openai package is required for openai-compatible runtime") from exc

    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )
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
    text = response.choices[0].message.content or ""
    return RuntimeResponse(text=text, raw=response.model_dump_json(), model=model)
