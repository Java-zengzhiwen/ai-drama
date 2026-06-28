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

## Scene: 1-1

【画面】
女主在清晨醒来，意识到命运重启。

【动作】
她检查身边物件，确认眼前不是幻觉。

【台词】
女主：这一世，我要先看清局。

## Scene: 1-2

【画面】
账册摊开，旧日线索重新浮现。

【动作】
她整理证据，把危险关系和家族账目分开标记。

【台词】
女主：账不会骗人，人心才会。
""" % model


def _mock_storyboard(model):
    return """# Mock Storyboard Revision

runtime_model: %s
source_basis: approved_script_revision
source_script_revision_id: mock-source-revision
source_script_artifact_id: mock-source-artifact
source_script_content_hash: mock-source-hash
source_script_approval_record_id: mock-approval-record
source_script_approval_action: script_approved

## 场次：1-1

### 镜头 1
- scene_id: 1-1
- shot_id: 1-1-01
- shot_order: 1
- source_scene_reference: 1-1
- duration_seconds: 6
- shot_size: close
- camera_angle: eye-level
- camera_movement: still
- visual_composition: 茶盏位于前景，人物压在画面左侧
- character_positions: 沈清荷左前，顾长渊右后
- character_actions: 沈清荷毒发，顾长渊冷眼旁观
- emotion_performance: 惊恐到绝望
- dialogue: 沈清荷质问顾长渊
- sound_notes: 茶盏碎裂，丫鬟哭喊
- continuity_in: 茶水未尽
- continuity_out: 茶盏落地破碎

### 镜头 2
- scene_id: 1-1
- shot_id: 1-1-02
- shot_order: 2
- source_scene_reference: 1-1
- duration_seconds: 7
- shot_size: medium
- camera_angle: slight_high
- camera_movement: slow_push
- visual_composition: 林婉兮进入画面，形成压迫三角构图
- character_positions: 林婉兮前景居中，顾长渊右后，沈清荷下位
- character_actions: 林婉兮揭露真相，顾长渊转身离开
- emotion_performance: 冷笑与背叛
- dialogue: 顾长渊承认借沈家铺路
- sound_notes: 脚步声远去，室内静默
- continuity_in: 破碎茶盏
- continuity_out: 黑场切换

## 场次：1-2

### 镜头 3
- scene_id: 1-2
- shot_id: 1-2-01
- shot_order: 1
- source_scene_reference: 1-2
- duration_seconds: 8
- shot_size: medium
- camera_angle: eye-level
- camera_movement: still
- visual_composition: 青色帐幔与茉莉花形成时间锚点
- character_positions: 沈清荷中心独立站立
- character_actions: 她摸喉咙，确认自己醒来
- emotion_performance: 惊疑转向清醒
- dialogue: 沈清荷确认自己没死
- sound_notes: 清晨风声，窗外安静
- continuity_in: 熟悉的闺房陈设
- continuity_out: 她走向铜镜

### 镜头 4
- scene_id: 1-2
- shot_id: 1-2-02
- shot_order: 2
- source_scene_reference: 1-2
- duration_seconds: 6
- shot_size: close
- camera_angle: eye-level
- camera_movement: still
- visual_composition: 铜镜反射她的脸与身后帐幔
- character_positions: 沈清荷贴近镜面
- character_actions: 她确认时间点
- emotion_performance: 从恐惧转为决意
- dialogue: 她意识到自己回到过去
- sound_notes: 轻微衣料摩擦
- continuity_in: 铜镜反光
- continuity_out: 继续确认旧物
""" % model


def run_runtime(runtime_request, mock_mode="success"):
    started = time.time()
    request_json = runtime_request.to_json()
    config = runtime_request.to_dict()["runtime_config"]
    runtime = config["provider"]
    model = config["model"]
    timeout_seconds = config["timeout_seconds"]
    if runtime == "mock":
        profile = runtime_request.to_dict().get("skill", {}).get("execution_profile", "")
        if mock_mode == "runtime_failure":
            raise RuntimeErrorBase("RUNTIME_PROVIDER_ERROR", "mock runtime failure")
        if mock_mode == "empty_response":
            raw = ""
        elif mock_mode == "parse_failure":
            raw = json.dumps({"not_script": "bad"}, ensure_ascii=False)
        elif profile == "storyboard-markdown-mvp-v1":
            raw = json.dumps({"storyboard_markdown": _mock_storyboard(model)}, ensure_ascii=False)
        else:
            raw = json.dumps({"script_markdown": _mock_script(model)}, ensure_ascii=False)
        return RuntimeResponse(
            raw=raw,
            provider="mock",
            model=model,
            usage={
                "usage_status": "PROVIDED",
                "prompt_tokens": len(request_json) // 4,
                "completion_tokens": len(raw) // 4,
                "total_tokens": (len(request_json) + len(raw)) // 4,
                "raw": {"prompt_chars": len(request_json), "completion_chars": len(raw)},
            },
            duration_ms=int((time.time() - started) * 1000),
        )
    if runtime == "openai-compatible":
        return _run_openai_compatible(runtime_request, started)
    raise RuntimeErrorBase("RUNTIME_PROVIDER_ERROR", "unknown runtime: %s" % runtime)


def _run_openai_compatible(runtime_request, started):
    config = runtime_request.to_dict()["runtime_config"]
    model = config["model"]
    timeout_seconds = config["timeout_seconds"]
    api_key = os.environ.get("AI_DRAMA_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeErrorBase("CONFIG_MISSING_API_KEY", "API key is required")
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
            messages=runtime_request.model_messages(),
        )
    except Exception as exc:
        name = exc.__class__.__name__.lower()
        code = "RUNTIME_PROVIDER_ERROR"
        if "timeout" in name:
            code = "RUNTIME_TIMEOUT"
        elif "rate" in name:
            code = "RUNTIME_RATE_LIMITED"
        elif "auth" in name or "permission" in name:
            code = "RUNTIME_AUTHENTICATION_FAILED"
        raise RuntimeErrorBase(code, "openai-compatible runtime failed") from exc
    usage = getattr(response, "usage", None)
    raw_usage = usage.model_dump() if usage else {}
    return RuntimeResponse(
        raw=response.model_dump_json(),
        provider="openai-compatible",
        model=model,
        usage={
            "usage_status": "PROVIDED" if usage else "NOT_PROVIDED",
            "prompt_tokens": int(raw_usage.get("prompt_tokens") or 0),
            "completion_tokens": int(raw_usage.get("completion_tokens") or 0),
            "total_tokens": int(raw_usage.get("total_tokens") or 0),
            "raw": raw_usage,
        },
        duration_ms=int((time.time() - started) * 1000),
    )
