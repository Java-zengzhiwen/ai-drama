import json
import os
import subprocess

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.suppliers.builtin_adapters import AGNES_SOURCE, _model_id
from ai_drama_web.suppliers.compiler import compile_supplier


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
      if (!globalThis.__responses.length) {
        throw Object.assign(new Error("FAKE_RESPONSE_MISSING"), {code:"FAKE_RESPONSE_MISSING"});
      }
      return globalThis.__responses.shift();
    }}),
    log: Object.freeze({info:()=>undefined, warning:()=>undefined})
  });
`).runInContext(context);
try {
  context.__result = await context.module.exports[input.operation](context.__payload, context.__helpers);
  process.stdout.write(JSON.stringify({ok:true, result:context.__result, calls:context.__calls}));
} catch (error) {
  process.stdout.write(JSON.stringify({
    ok:false,
    error_code:error?.code || "SUPPLIER_EXECUTION_FAILED",
    calls:context.__calls,
  }));
}
"""


OUTPUT_PNG = "https://platform-outputs.agnes-ai.space/images/result.png"
OUTPUT_MP4 = "https://platform-outputs.agnes-ai.space/videos/result.mp4"
MEDIA_RESULT = {
    "local_file": "/tmp/fake-media",
    "sha256": "fake-sha256",
    "size": 128,
    "media_type": "application/octet-stream",
}


@pytest.fixture
def artifact(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    try:
        yield compile_supplier(AGNES_SOURCE, runtime_store=runtime)
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
        env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "TZ": "UTC"},
    )
    return json.loads(completed.stdout)


def payload(model, *, request=None, constraints=None):
    return {
        "model": model,
        "credential": "fixture-credential-not-real",
        "config": {
            "image_endpoint": "https://apihub.agnes-ai.com/v1/images/generations",
            "video_endpoint": "https://apihub.agnes-ai.com/v1/videos",
            "video_status_endpoint": "https://apihub.agnes-ai.com/agnesapi",
            "result_origins": ["https://platform-outputs.agnes-ai.space"],
        },
        "request": request or {"prompt": "hello"},
        "constraints": constraints or {},
    }


def test_manifest_preserves_model_identity_and_declares_image_options(artifact):
    assert artifact.vendor["models"] == [
        {
            "supplierModelId": _model_id("agnes", "image"),
            "providerModelName": "agnes-image-2.1-flash",
            "displayName": "Agnes Image",
            "capability": "image",
            "default_size": "1K",
            "default_ratio": "1:1",
            "constraints": {
                "supported_sizes": [
                    "1K", "2K", "3K", "4K", "1024x768", "1024x1024", "768x1024",
                    "1024x1536", "1536x1024",
                ],
                "supported_ratios": [
                    "1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9",
                ],
            },
        },
        {
            "supplierModelId": _model_id("agnes", "video"),
            "providerModelName": "agnes-video-v2.0",
            "displayName": "Agnes Video",
            "capability": "video",
        },
    ]


def test_image_request_uses_tier_ratio_and_extra_body_image(artifact):
    reference = "https://assets.example.test/reference.png"
    result = invoke(
        artifact,
        "imageRequest",
        payload(
            "agnes-image-2.1-flash",
            request={
                "prompt": "cinematic frame",
                "size": "2K",
                "ratio": "16:9",
                "input_images": [reference],
            },
        ),
        [{"created": 1, "data": [{"url": OUTPUT_PNG}]}, MEDIA_RESULT],
    )

    assert result["ok"] is True
    assert result["calls"][0]["body"] == {
        "model": "agnes-image-2.1-flash",
        "prompt": "cinematic frame",
        "size": "2K",
        "ratio": "16:9",
        "extra_body": {"response_format": "url", "image": [reference]},
    }
    assert result["calls"][1] == {
        "method": "GET",
        "url": OUTPUT_PNG,
        "responseType": "bytes",
    }


@pytest.mark.parametrize(
    ("image_request", "error_code"),
    [
        ({"prompt": "frame", "size": "8K", "ratio": "1:1"}, "INVALID_IMAGE_SIZE"),
        ({"prompt": "frame", "size": "1K", "ratio": "5:4"}, "INVALID_IMAGE_RATIO"),
    ],
)
def test_image_request_rejects_unknown_options_before_network(
    artifact, image_request, error_code
):
    result = invoke(
        artifact,
        "imageRequest",
        payload("agnes-image-2.1-flash", request=image_request),
        [],
    )

    assert result == {"ok": False, "error_code": error_code, "calls": []}


def test_video_submit_and_poll_use_only_video_id(artifact):
    submitted = invoke(
        artifact,
        "videoSubmit",
        payload(
            "agnes-video-v2.0",
            request={
                "prompt": "move slowly",
                "input_images": [],
                "parameters": {"frame_rate": 24, "num_frames": 121},
            },
        ),
        [{"task_id": "task-ignored", "video_id": "video-official-1", "status": "queued"}],
    )
    polled = invoke(
        artifact,
        "videoPoll",
        payload("agnes-video-v2.0", request={"video_id": "video-official-1"}),
        [{"video_id": "video-official-1", "status": "processing"}],
    )

    assert submitted["result"] == {"video_id": "video-official-1", "status": "queued"}
    assert polled["result"] == {"video_id": "video-official-1", "status": "polling"}
    assert polled["calls"][0]["query"] == {"video_id": "video-official-1"}


@pytest.mark.parametrize(
    "provider_response",
    [
        {"id": "generic-id"},
        {"task_id": "task-id"},
    ],
)
def test_video_submit_rejects_responses_without_video_id(
    artifact, provider_response
):
    result = invoke(
        artifact,
        "videoSubmit",
        payload(
            "agnes-video-v2.0",
            request={"prompt": "move slowly", "input_images": []},
        ),
        [provider_response],
    )

    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_VIDEO_ID_MISSING"


@pytest.mark.parametrize(
    ("parameters", "error_code"),
    [
        ({"mode": "invalid-mode"}, "INVALID_VIDEO_MODE"),
        ({"num_frames": 0}, "INVALID_VIDEO_NUM_FRAMES"),
        ({"num_frames": 2}, "INVALID_VIDEO_NUM_FRAMES"),
        ({"num_frames": 442}, "INVALID_VIDEO_NUM_FRAMES"),
        ({"num_frames": 121.5}, "INVALID_VIDEO_NUM_FRAMES"),
        ({"frame_rate": 0}, "INVALID_VIDEO_FRAME_RATE"),
        ({"frame_rate": 61}, "INVALID_VIDEO_FRAME_RATE"),
        ({"frame_rate": 24.5}, "INVALID_VIDEO_FRAME_RATE"),
    ],
)
def test_video_submit_rejects_invalid_parameters_before_network(
    artifact, parameters, error_code
):
    result = invoke(
        artifact,
        "videoSubmit",
        payload(
            "agnes-video-v2.0",
            request={
                "prompt": "move slowly",
                "input_images": [],
                "parameters": parameters,
            },
        ),
        [],
    )

    assert result == {"ok": False, "error_code": error_code, "calls": []}


def test_video_poll_rejects_unknown_status(artifact):
    result = invoke(
        artifact,
        "videoPoll",
        payload("agnes-video-v2.0", request={"video_id": "video-official-1"}),
        [{"status": "mystery"}],
    )

    assert result["ok"] is False
    assert result["error_code"] == "PROVIDER_STATUS_INVALID"


def test_video_fetch_reads_official_metadata_url(artifact):
    result = invoke(
        artifact,
        "videoFetch",
        payload("agnes-video-v2.0", request={"video_id": "video-official-1"}),
        [
            {
                "video_id": "video-official-1",
                "status": "completed",
                "metadata": {"url": OUTPUT_MP4},
            },
            MEDIA_RESULT,
        ],
    )

    assert result["ok"] is True
    assert result["calls"][0]["query"] == {"video_id": "video-official-1"}
    assert result["calls"][1] == {
        "method": "GET",
        "url": OUTPUT_MP4,
        "responseType": "bytes",
    }
