import json
from pathlib import Path
import subprocess

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.suppliers.compiler import compile_supplier


SOURCE = (
    Path(__file__).resolve().parents[2]
    / "ai_drama_web"
    / "suppliers"
    / "custom_adapters"
    / "aixora.ts"
)


HARNESS = r"""
import vm from "node:vm";
let raw = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) raw += chunk;
const input = JSON.parse(raw);
const context = vm.createContext({});
new vm.Script("globalThis.module={exports:{}};globalThis.exports=globalThis.module.exports;").runInContext(context);
new vm.Script(input.compiledCode).runInContext(context);
context.__payload = JSON.parse(JSON.stringify(input.payload));
context.__responses = JSON.parse(JSON.stringify(input.responses || []));
context.__calls = [];
new vm.Script(`
  globalThis.__helpers = Object.freeze({
    http: Object.freeze({request: async options => {
      globalThis.__calls.push(options);
      if (!globalThis.__responses.length) throw Object.assign(new Error("FAKE_RESPONSE_MISSING"), {code:"FAKE_RESPONSE_MISSING"});
      return globalThis.__responses.shift();
    }}),
    media: Object.freeze({decodeBase64: async (value, mediaType) => {
      globalThis.__calls.push({mediaOperation:"decodeBase64", value, mediaType});
      return {local_file:"/tmp/fake-image", sha256:"fake", size:8, media_type:mediaType};
    }}),
    log: Object.freeze({info:()=>undefined, warning:()=>undefined})
  });
`).runInContext(context);
try {
  context.__result = await context.module.exports[input.operation](context.__payload, context.__helpers);
  process.stdout.write(JSON.stringify({ok:true, result:context.__result, calls:context.__calls}));
} catch (error) {
  process.stdout.write(JSON.stringify({ok:false, error_code:error?.code || "SUPPLIER_EXECUTION_FAILED", calls:context.__calls}));
}
"""


@pytest.fixture
def artifact(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    try:
        yield compile_supplier(SOURCE.read_text(), runtime_store=runtime)
    finally:
        runtime.close()


def invoke(artifact, operation, payload, responses):
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", HARNESS],
        input=json.dumps(
            {
                "compiledCode": artifact.compiled_code,
                "operation": operation,
                "payload": payload,
                "responses": responses,
            }
        ),
        text=True,
        capture_output=True,
        check=True,
        timeout=5,
        env={"PATH": __import__("os").environ.get("PATH", ""), "LANG": "C.UTF-8", "TZ": "UTC"},
    )
    return json.loads(completed.stdout)


def payload(model, *, request=None, config=None, constraints=None):
    return {
        "model": model,
        "credential": "test-credential-not-real",
        "config": config or {
            "base_url": "https://www.aixora.store/v1",
            "reasoning_effort": "medium",
            "image_size": "1024x1024",
            "image_quality": "auto",
        },
        "request": request or {"prompt": "hello"},
        "constraints": constraints or {},
    }


def test_manifest_is_exact_and_stable(artifact):
    assert artifact.helper_api_version == "ai-drama-helper-v2"
    assert [(model["providerModelName"], model["capability"]) for model in artifact.vendor["models"]] == [
        ("gpt-5.5", "text"),
        ("gpt-5.6", "text"),
        ("gpt-5.6-sol", "text"),
        ("gpt-5.6-luna", "text"),
        ("gpt-5.6-terra", "text"),
        ("gpt-image-2", "image"),
    ]
    assert [item["key"] for item in artifact.vendor["inputs"]] == [
        "base_url",
        "reasoning_effort",
        "image_size",
        "image_quality",
    ]
    assert artifact.vendor["inputValues"] == {
        "base_url": "https://www.aixora.store/v1",
        "reasoning_effort": "medium",
        "image_size": "1024x1024",
        "image_quality": "auto",
    }
    inputs = {item["key"]: item for item in artifact.vendor["inputs"]}
    assert inputs["reasoning_effort"]["type"] == "select"
    assert [option["value"] for option in inputs["reasoning_effort"]["options"]] == [
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]
    assert [option["value"] for option in inputs["image_size"]["options"]] == [
        "auto",
        "1024x1024",
        "1024x1536",
        "1536x1024",
    ]
    assert [option["value"] for option in inputs["image_quality"]["options"]] == [
        "auto",
        "low",
        "medium",
        "high",
    ]
    assert artifact.vendor["models"][1]["supplierModelId"] == "07c95486e414569bb18f694431f3ad4f"
    image_model = next(model for model in artifact.vendor["models"] if model["capability"] == "image")
    assert image_model["default_size"] == "1024x1024"
    assert image_model["constraints"] == {
        "supported_sizes": ["auto", "1024x1024", "1024x1536", "1536x1024"],
        "default_quality": "auto",
        "supported_qualities": ["auto", "low", "medium", "high"],
    }
    text_models = {
        model["providerModelName"]: model["constraints"]
        for model in artifact.vendor["models"]
        if model["capability"] == "text"
    }
    assert text_models["gpt-5.5"]["supported_reasoning_efforts"] == [
        "none", "low", "medium", "high", "xhigh"
    ]
    assert text_models["gpt-5.6-sol"]["supported_reasoning_efforts"] == [
        "none", "low", "medium", "high", "xhigh", "max"
    ]
    assert all(model["reasoning_effort"] == "medium" for model in text_models.values())


@pytest.mark.parametrize("effort", ["none", "low", "medium", "high", "xhigh", "max"])
def test_text_responses_normalizes_output_and_reasoning_effort(artifact, effort):
    result = invoke(
        artifact,
        "textRequest",
        payload(
            "gpt-5.6-sol",
            request={"prompt": "hello", "parameters": {"reasoning_effort": effort}},
        ),
        [{"output_text": "ok", "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}}],
    )

    assert result["ok"] is True
    assert result["result"] == {
        "output": "ok",
        "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
    }
    request = result["calls"][0]
    assert request["url"] == "https://www.aixora.store/v1/responses"
    assert request["body"]["input"] == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        }
    ]
    assert request["body"]["reasoning"] == {"effort": effort}
    assert request["body"]["stream"] is False
    assert request["body"]["store"] is False


def test_text_preserves_caller_supplied_response_messages(artifact):
    messages = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        }
    ]
    result = invoke(
        artifact,
        "textRequest",
        payload("gpt-5.6-luna", request={"messages": messages}),
        [{"output_text": "ok", "usage": {}}],
    )

    assert result["calls"][0]["body"]["input"] == messages


def test_text_normalizes_string_message_content_for_responses_api(artifact):
    result = invoke(
        artifact,
        "textRequest",
        payload(
            "gpt-5.6-sol",
            request={
                "messages": [
                    {"role": "system", "content": "follow the supplied skill"},
                    {"role": "user", "content": "create the complete script"},
                ]
            },
        ),
        [{"output_text": "ok", "usage": {}}],
    )

    assert result["calls"][0]["body"]["input"] == [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "follow the supplied skill"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "create the complete script"}],
        },
    ]


def test_text_uses_canonical_response_content_and_rejects_invalid_effort(artifact):
    canonical = invoke(
        artifact,
        "textRequest",
        payload("gpt-5.5"),
        [{"output": [{"content": [{"type": "output_text", "text": "canonical"}]}], "usage": {}}],
    )
    invalid = invoke(
        artifact,
        "textRequest",
        payload("gpt-5.5", request={"prompt": "hello", "parameters": {"reasoning_effort": "turbo"}}),
        [],
    )

    assert canonical["result"]["output"] == "canonical"
    assert invalid == {"ok": False, "error_code": "INVALID_REASONING_EFFORT", "calls": []}


def test_text_reasoning_precedence_uses_frozen_constraints_before_supplier_config(artifact):
    frozen = invoke(
        artifact,
        "textRequest",
        payload(
            "gpt-5.6",
            constraints={"reasoning_effort": "low"},
            config={"base_url": "https://www.aixora.store/v1", "reasoning_effort": "high"},
        ),
        [{"output_text": "ok", "usage": {}}],
    )
    explicit = invoke(
        artifact,
        "textRequest",
        payload(
            "gpt-5.6",
            request={"prompt": "hello", "parameters": {"reasoning_effort": "high"}},
            constraints={"reasoning_effort": "low"},
        ),
        [{"output_text": "ok", "usage": {}}],
    )

    assert frozen["calls"][0]["body"]["reasoning"] == {"effort": "low"}
    assert explicit["calls"][0]["body"]["reasoning"] == {"effort": "high"}


def test_text_to_image_accepts_base64_and_url_results(artifact):
    base64_result = invoke(
        artifact,
        "imageRequest",
        payload("gpt-image-2", request={"prompt": "a cup", "size": "1024x1024", "input_images": []}),
        [{"data": [{"b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGP4DwQACfsD/fteaysAAAAASUVORK5CYII="}]}],
    )
    url_result = invoke(
        artifact,
        "imageRequest",
        payload("gpt-image-2", request={"prompt": "a cup", "size": "1024x1024", "input_images": []}),
        [{"data": [{"url": "https://cdn.example.test/result.png?sig=hidden"}]}, {"local_file": "/tmp/fake-url", "sha256": "fake", "size": 8, "media_type": "image/png"}],
    )

    assert base64_result["ok"] is True
    assert base64_result["calls"][0]["url"].endswith("/images/generations")
    assert base64_result["calls"][0]["body"]["size"] == "1024x1024"
    assert base64_result["calls"][0]["body"]["quality"] == "auto"
    assert base64_result["calls"][0]["body"]["response_format"] == "url"
    assert base64_result["calls"][1]["mediaOperation"] == "decodeBase64"
    assert url_result["calls"][1] == {
        "method": "GET",
        "url": "https://cdn.example.test/result.png?sig=hidden",
        "responseType": "bytes",
    }


def test_image_options_precedence_uses_request_then_frozen_snapshot_then_config(artifact):
    frozen = invoke(
        artifact,
        "imageRequest",
        payload(
            "gpt-image-2",
            request={"prompt": "a cup", "input_images": []},
            constraints={"size": "1024x1536", "quality": "high"},
            config={
                "base_url": "https://www.aixora.store/v1",
                "image_size": "1536x1024",
                "image_quality": "low",
            },
        ),
        [{"data": [{"b64_json": "iVBORw0KGgo="}]}],
    )
    explicit = invoke(
        artifact,
        "imageRequest",
        payload(
            "gpt-image-2",
            request={"prompt": "a cup", "size": "auto", "quality": "medium", "input_images": []},
            constraints={"size": "1024x1536", "quality": "high"},
        ),
        [{"data": [{"b64_json": "iVBORw0KGgo="}]}],
    )

    assert frozen["calls"][0]["body"]["size"] == "1024x1536"
    assert frozen["calls"][0]["body"]["quality"] == "high"
    assert explicit["calls"][0]["body"]["size"] == "auto"
    assert explicit["calls"][0]["body"]["quality"] == "medium"


def test_image_edit_uses_ordered_declared_inputs_and_safe_multipart(artifact):
    images = [
        "data:image/png;base64,ZmFrZS0x",
        "https://assets.example.test/input-2.png?sig=hidden",
    ]
    result = invoke(
        artifact,
        "imageRequest",
        payload(
            "gpt-image-2",
            request={"prompt": "edit", "size": "1024x1024", "quality": "high", "input_images": images},
        ),
        [{"data": [{"b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGP4DwQACfsD/fteaysAAAAASUVORK5CYII="}]}],
    )

    assert result["ok"] is True
    request = result["calls"][0]
    assert request["url"].endswith("/images/edits")
    assert request["multipart"]["fields"] == {
        "model": "gpt-image-2",
        "prompt": "edit",
        "size": "1024x1024",
        "quality": "high",
    }
    assert [item["url"] for item in request["multipart"]["files"]] == images
    assert all(item["fieldName"] == "image[]" for item in request["multipart"]["files"])
