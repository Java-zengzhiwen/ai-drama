# Model Parameter Selects Design

Date: 2026-07-19

Status: `APPROVED`

Branch: `feat/model-parameter-selects`

## 1. Purpose

Replace free-form Provider parameter entry with manifest-driven selects and expose the supported text reasoning and GPT Image 2 generation controls at the points where they affect real work.

The approved product option is C:

```text
supplier defaults
plus
one-request overrides in the model test dialog
```

Supplier defaults apply to future project and model-test requests. A model-test override applies only to the confirmed test and is frozen with that test's immutable snapshot.

## 2. Confirmed Provider Contract

The OpenAI model catalog currently declares:

- GPT-5.6 Sol, Terra, and Luna: `none`, `low`, `medium`, `high`, `xhigh`, `max`;
- GPT-5.5: `none`, `low`, `medium`, `high`, `xhigh`;
- GPT Image 2 size: `auto`, `1024x1024`, `1024x1536`, `1536x1024`;
- GPT Image 2 quality: `auto`, `low`, `medium`, `high`.

Sources:

- <https://developers.openai.com/api/docs/models>
- <https://developers.openai.com/api/docs/models/gpt-image-2>
- <https://platform.openai.com/docs/api-reference/images-streaming/image_generation/partial_image>

`2K` and `4K` are not accepted GPT Image 2 request values. The UI must not translate those marketing labels into guessed dimensions. It may show Chinese orientation labels, but it sends only the exact values above.

Aixora is an OpenAI-compatible relay, not the OpenAI service itself. The UI is based on the official model contract already accepted by the local adapter. A Provider rejection is reported without retry, fallback, or silent parameter substitution.

## 3. Scope

### In scope

- manifest input type `select` with an explicit option list;
- supplier default reasoning, image-size, and image-quality selects;
- model-specific reasoning options in the text model-test dialog;
- image size and quality overrides in the image model-test dialog;
- backend validation, immutable snapshot persistence, idempotency, recovery, and safe result metadata;
- Aixora adapter and model definitions for the approved values;
- synchronization of the existing local `aixora` and `aixora-image` runtime supplier code without reading or replacing their credentials;
- fake/local automated tests and zero real Provider requests.

### Out of scope

- `2K`, `4K`, arbitrary width/height, image upscaling, or post-processing;
- image format, compression, background, count, or streaming controls;
- video parameters;
- automatic Provider capability discovery;
- automatic fallback when Aixora rejects a model or parameter;
- real Provider requests during implementation or verification;
- database schema changes.

## 4. Manifest-Driven Select Contract

A supplier input may declare:

```json
{
  "key": "reasoning_effort",
  "label": "默认思考深度",
  "type": "select",
  "required": true,
  "options": [
    { "value": "none", "label": "无额外推理" },
    { "value": "low", "label": "低" },
    { "value": "medium", "label": "中" },
    { "value": "high", "label": "高" },
    { "value": "xhigh", "label": "超高" },
    { "value": "max", "label": "最大" }
  ]
}
```

Rules:

- `options` is an ordered array of non-empty, unique string values;
- each option has a non-empty display label;
- the current value must match one option before save;
- unknown input types continue to render as text for backward compatibility;
- malformed select declarations fail local supplier validation and never reach the Provider;
- supplier configuration values remain strings and continue using the independent config revision and ETag.

## 5. Supplier Defaults

The Aixora manifest exposes:

```text
reasoning_effort = medium
image_size = 1024x1024
image_quality = auto
```

The configuration page renders:

```text
默认思考深度
- 无额外推理
- 低
- 中
- 高
- 超高
- 最大

默认图片尺寸
- 自动
- 方形 1024 x 1024
- 竖版 1024 x 1536
- 横版 1536 x 1024

默认图片质量
- 自动
- 低（更快、费用较低）
- 中（质量与费用平衡）
- 高（耗时和费用可能增加）
```

Existing `medium` reasoning values remain valid. Existing image behavior remains square `1024x1024`; missing quality resolves to `auto`.

## 6. Model Capability Declarations

Model definitions carry UI-safe, immutable capability metadata:

```json
{
  "constraints": {
    "reasoning_effort": "medium",
    "supported_reasoning_efforts": ["none", "low", "medium", "high", "xhigh", "max"]
  }
}
```

GPT-5.5 omits `max`. GPT-5.6, GPT-5.6 Sol, GPT-5.6 Terra, and GPT-5.6 Luna include all six values. The image definition carries:

```json
{
  "default_size": "1024x1024",
  "constraints": {
    "supported_sizes": ["auto", "1024x1024", "1024x1536", "1536x1024"],
    "default_quality": "auto",
    "supported_qualities": ["auto", "low", "medium", "high"]
  }
}
```

The UI reads these declarations instead of maintaining an unrelated global list. Missing legacy declarations use the conservative existing controls and defaults.

## 7. Resolution And Snapshot Semantics

Text reasoning resolves:

```text
explicit request override
-> supplier configured default
-> model revision default
-> medium
```

Image controls resolve independently:

```text
explicit request override
-> supplier configured default
-> model revision default
-> system default
```

System image defaults are `1024x1024` and `auto`. The service validates the resolved value against the selected immutable model revision before creating a run.

The resolved fields are frozen before Provider submission:

```json
{
  "reasoning_effort": "high"
}
```

or:

```json
{
  "size": "1024x1536",
  "quality": "high"
}
```

Active jobs never re-read current supplier configuration. Invalid values return a stable local error and create neither a run nor a Provider request.

## 8. Model Test Contract

The loopback-only model-test create body becomes:

```json
{
  "prompt": "...",
  "reasoning_effort": "high"
}
```

for text, or:

```json
{
  "prompt": "...",
  "size": "1024x1536",
  "quality": "high"
}
```

for image. Capability-incompatible fields fail locally.

The dialog shows `跟随供应商配置` plus the selected model's declared values. After confirmation, prompt and overrides lock. Session recovery stores only the idempotency key, test-run ID, and selected non-secret overrides. The canonical request hash includes size, quality, and reasoning so changing a value under the same key returns `IDEMPOTENCY_CONFLICT`.

Safe completed reads expose effective `reasoning_effort` for text and effective `size` and `quality` for image. They do not expose credentials, Authorization data, raw Provider bodies, or Provider URLs.

## 9. Adapter Behavior

The adapter consumes only validated values supplied through the immutable request and snapshot:

```text
request override
-> frozen snapshot constraint
-> selected config value
-> adapter safety default
```

`imageRequest` sends the exact `size` and `quality` to `/v1/images/generations` or `/v1/images/edits`. It does not synthesize 2K/4K dimensions. Existing media decoding, URL sanitization, result download, and credential isolation remain unchanged.

The current local `aixora-image` supplier is a database-backed copy of Aixora. Repository changes alone do not update that immutable runtime version. After automated verification, a local loopback management update will save the reviewed source for `aixora` and the identity-adjusted equivalent for `aixora-image`, preserving both current credential references and making no Provider request.

## 10. Error Contract

```text
INVALID_REASONING_EFFORT
INVALID_IMAGE_SIZE
INVALID_IMAGE_QUALITY
MODEL_TEST_REASONING_UNSUPPORTED
MODEL_TEST_IMAGE_OPTIONS_UNSUPPORTED
IDEMPOTENCY_CONFLICT
REVISION_CONFLICT
```

All validation errors are local. Provider rejections remain sanitized and are never retried automatically.

## 11. Test And Acceptance Criteria

Automated tests use fake/local transports and keep real request counts at zero.

- supplier config renders select inputs from the manifest and rejects unknown values;
- text inputs and legacy unknown input types remain backward compatible;
- GPT-5.5 omits `max`; GPT-5.6-family models include it;
- text model tests submit, persist, recover, and display the selected reasoning effort;
- image model tests submit, persist, recover, and display the selected size and quality;
- request hash changes when any override changes;
- capability-incompatible and unsupported values create no run;
- image request payload contains exact official size and quality values;
- existing missing image quality resolves to `auto`;
- existing square default remains `1024x1024`;
- immutable snapshots are used after configuration changes;
- supplier/config/model management remains loopback-only and ETag conditional;
- credentials and runtime data remain untracked;
- no automated test or implementation action makes a real Provider request.

Acceptance requires focused Python and Web tests, full Python regression, Web tests/build/e2e, Worker tests, migration verification, `git diff --check`, tracked-secret scan, and confirmation that both local supplier credentials were preserved during runtime synchronization.

