# AIXORA Adapter And Model Archive Design

Status: approved product direction, implementation not started

Date: 2026-07-15

Repository: `Java-zengzhiwen/ai-drama`

## 1. Purpose

Complete the user-created AIXORA supplier with an AI Drama-native adapter for the explicitly approved GPT text and image models, make GPT reasoning effort configurable, and replace the misleading model physical-delete experience with an audit-preserving archive delete.

This is an additive post-M6 change based on the model-level provider-test branch. It does not weaken immutable execution snapshots, credential isolation, Worker network controls, loopback-only management, or the default transport denial used by automated tests.

## 2. Confirmed Product Decisions

- AIXORA text models are limited to `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.6-luna`, and `gpt-5.5`.
- Do not add the generic `gpt-5.6` alias as a separate catalog row.
- AIXORA text uses the Responses API rather than Chat Completions.
- Reasoning effort is configurable as `none`, `low`, `medium`, `high`, `xhigh`, or `max`; the supplier default is `medium`.
- A request-level `parameters.reasoning_effort` may override the supplier default after allowlist validation.
- AIXORA image uses only `gpt-image-2` and supports text-to-image and image-to-image.
- Overlay models without any historical or active reference are physically deleted.
- Overlay models with immutable historical references but no active project binding are archived and disappear from normal model selection.
- Models with an active project binding must be unbound before delete/archive.
- Built-in/manifest models remain non-deletable; they may be disabled.
- Grok is not added to AIXORA in this increment because live capability discovery and a minimal real call show that the configured AIXORA account group does not expose it.
- Real AIXORA calls are explicitly authorized for this implementation's final provider acceptance. Automated tests and verifiers remain fake-only and network-denied.

## 3. Verified Provider Evidence

The configured AIXORA credential was used without exposing its value.

`GET https://www.aixora.store/v1/models` returned the relevant text identities:

```text
gpt-5.5
gpt-5.6
gpt-5.6-luna
gpt-5.6-sol
gpt-5.6-terra
```

It did not list `gpt-image-2` or any Grok model. AIXORA's published documentation nevertheless explicitly documents `gpt-image-2` through `/v1/images/generations`, so image capability remains in scope and must be proven by a real post-implementation test.

A minimal authorized `grok-4.5` Responses request returned:

```text
HTTP=404
TYPE=model_not_found
MESSAGE=Model "grok-4.5" is not supported by any configured account in this group
```

This research request is the only real billable text request made before implementation. It returned before generation and produced no usable content.

xAI's contract separates capabilities:

- `grok-4.5`: text output and image understanding input;
- `grok-imagine-image-quality`: image generation and editing;
- `grok-imagine-video` / `grok-imagine-video-1.5`: text-to-video and image-to-video.

The product must never represent `grok-4.5` as one text/image/video generation model. A future xAI supplier requires either a working AIXORA route for each exact model or a separately configured xAI credential and Base URL.

## 4. AIXORA Supplier Contract

### 4.1 Manifest

The saved custom supplier source declares exactly five stable model identities:

```text
gpt-5.6-terra  text
gpt-5.6-sol    text
gpt-5.6-luna   text
gpt-5.5        text
gpt-image-2    image
```

Each manifest entry receives a deterministic stable `supplierModelId`. Display names may change through new revisions, but IDs and capabilities remain stable. The current hand-created `GPT-5.6 Sol` overlay is not silently reused as a manifest identity; after the archive behavior exists, it is archived because its failed model test already owns an immutable snapshot.

Manifest inputs are:

```text
base_url         required URL, default https://www.aixora.store/v1
reasoning_effort required text, default medium
```

The adapter normalizes one trailing slash from `base_url`, rejects any value that does not end in `/v1`, and validates reasoning effort against the frozen allowlist before network submission.

### 4.2 Text Request

`textRequest(payload, helpers)` performs:

```text
POST {base_url}/responses
Authorization: Bearer selected credential
Content-Type: application/json

{
  "model": payload.model,
  "input": provider-neutral prompt/messages,
  "instructions": optional system instruction,
  "reasoning": {"effort": selected effort},
  "stream": false,
  "store": false
}
```

Effort resolution is deterministic:

```text
payload.request.parameters.reasoning_effort
-> payload.config.reasoning_effort
-> medium
```

The adapter accepts both a provider `output_text` convenience field and canonical Responses `output[].content[]` text. It returns:

```json
{
  "output": "normalized text",
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0
  }
}
```

Missing output fails with `PROVIDER_RESPONSE_MALFORMED`. Authentication, quota, model, rate-limit, timeout, and provider failures use stable sanitized codes. Credential text, authorization headers, raw response bodies, and provider request IDs are not returned.

### 4.3 Text-To-Image

When `payload.request.input_images` is empty, `imageRequest` calls:

```text
POST {base_url}/images/generations
```

The request contains only confirmed fields: exact `payload.model`, prompt, one image, supported size, optional quality, and URL response format when the provider accepts it. Unknown parameters are not forwarded.

The adapter accepts a provider URL or base64 image result. A URL is downloaded immediately through the bounded HTTP helper. A base64 result is decoded through a new bounded media helper rather than by exposing `Buffer`, filesystem, or Node globals to supplier code. Final bytes are persisted in the local object store and provider URLs are not retained in user-visible evidence.

### 4.4 Image-To-Image

When one or more `input_images` are present, `imageRequest` calls:

```text
POST {base_url}/images/edits
Content-Type: multipart/form-data
```

Supplier code cannot read local files or construct arbitrary multipart uploads. The versioned helper receives:

- the configured target endpoint;
- allowed scalar fields (`model`, `prompt`, optional `size`, optional `quality`);
- source references copied exactly from `payload.request.input_images`;
- maximum input count and per-file/aggregate byte limits.

The Worker validates every input reference, performs SSRF and peer-IP checks, downloads only the declared input media, constructs multipart in the host helper, and terminates on timeout or size overflow. Signed query values are never logged or returned. The first implementation supports the platform's existing ordered image inputs without adding a new browser upload flow.

The output normalization and persistence rules are identical to text-to-image.

## 5. Model Archive Delete

### 5.1 Root Cause

The UI currently disables delete only for built-in models or active project bindings. The backend also counts execution snapshots. A failed model-level test creates a valid immutable snapshot, so the UI offers delete but the backend returns `MODEL_REFERENCED`. The current AIXORA overlay has zero bindings, one failed test, and one snapshot, reproducing this mismatch.

### 5.2 Data Contract

Add nullable archive metadata to `supplier_models`:

```text
archived_at
archive_reason
```

Migration is additive, replay-safe, and defaults existing models to active. Historical model revisions, snapshots, test runs, jobs, and results remain unchanged.

### 5.3 Delete Behavior

`DELETE /api/models/{supplier_model_id}` retains conditional ETag mutation and resolves as follows:

```text
built_in model                         -> BUILT_IN_MODEL_DELETE_FORBIDDEN
active project default/override        -> MODEL_REFERENCED
overlay with no references             -> physical delete, 204
overlay with historical snapshot only  -> archive, 204
already archived                       -> idempotent 204 for matching revision
```

Archiving increments the model entity revision and supplier catalog revision atomically. A stale request returns `REVISION_CONFLICT` and is never retried automatically.

### 5.4 Read And Resolution Behavior

- Normal supplier model lists exclude archived models.
- Project binding choices exclude archived models.
- Resolver rejects an archived model as `MODEL_ARCHIVED`; an already-created execution continues from its immutable snapshot.
- Historical test/job/result reads can still resolve archived identity and revisions.
- Direct model reads include archive metadata for audit and conflict recovery.
- No Phase 1 restore UI or archived-model management page is added.

The UI confirmation copy changes from physical-delete-only language to state that models with history will be archived. On success the row disappears after catalog refetch. If an active binding exists, delete remains disabled and explains that the model must first be unbound.

## 6. Security And Failure Handling

- Supplier source remains isolated from `process`, `require`, import, native fetch, filesystem, environment variables, sockets, and subprocesses.
- Network execution remains available only through injected helpers and immutable snapshot configuration.
- New base64 and multipart media helpers enforce the existing timeout, output, media, redirect, DNS, and peer-address limits.
- The Worker environment contains no AIXORA, Agnes, OpenAI, xAI, or other credential variables.
- AIXORA credentials are read only from the selected credential version and injected only into the authorization header.
- Sanitized evidence removes bearer values, signed URL queries, provider result URLs, and raw multipart metadata.
- Validation and automated tests remain network-disabled.
- Real-provider acceptance has no automatic retry, fallback, batch generation, or Grok request.

## 7. TDD And Test Plan

Implementation uses red-green-refactor in these independent slices:

1. archive migration and store behavior;
2. archive-aware API, resolver, and model lists;
3. delete/archive UI behavior and error copy;
4. bounded base64 media result helper;
5. bounded multipart image-input helper;
6. AIXORA text adapter normalization and effort selection;
7. AIXORA text-to-image and image-to-image normalization;
8. safe runtime configuration of the existing AIXORA supplier.

Automated coverage includes:

- physical delete without references;
- archive with a failed model-test snapshot;
- rejection with active project binding;
- archived model hidden from catalogs and bindings;
- immutable historical test readability after archive;
- archived model resolver rejection;
- ETag conflict and idempotent archive behavior;
- exact five-model AIXORA manifest;
- all allowed and invalid reasoning efforts;
- Responses output and usage variants;
- text-to-image URL and base64 results;
- image-to-image multipart field and ordered-input behavior;
- private/metadata IP, redirect, oversized input, malformed media, timeout, and signed-query sanitization;
- zero credential leakage;
- default zero real network in Python, Worker, browser, and verifier tests;
- M1-M6 and model-level provider-test regression.

## 8. Authorized Real Acceptance

After automated tests, independent review, local supplier-code validation, and safe configuration persistence, the user authorizes these exact AIXORA calls without automatic retry:

- one minimal text request for each of the four approved text models;
- one `gpt-image-2` text-to-image request;
- one `gpt-image-2` image-to-image request using a non-sensitive generated fixture.

Each call is separately counted and reported. A provider rejection is reported as evidence and does not trigger speculative contract changes. The earlier failed `grok-4.5` research request is also included in the final real-request ledger. No AIXORA Grok image or video call is permitted because the configured account group does not expose the text model and no exact generation model contract has been confirmed.

## 9. Acceptance Criteria

The increment is ready for review only when:

- the exact four text models and one image model appear under AIXORA;
- text tests prove Responses normalization and configurable reasoning effort;
- text-to-image and image-to-image produce valid locally persisted image bytes, or an accurate provider capability rejection is documented without fallback;
- the existing failed-test AIXORA overlay can be deleted from the normal UI through archive semantics;
- no active project binding is silently broken;
- archived history remains readable and immutable;
- automated tests and verifiers make zero real provider requests;
- real acceptance counts, statuses, elapsed times, media metadata, and sanitized errors are reported accurately;
- no API key, bearer value, signed URL, runtime database, private image, or generated result is committed;
- the production M6 execution flag is not enabled by this change;
- rollback can disable the new UI behavior and supplier version without deleting archive/history data.

## 10. Out Of Scope

- AIXORA Grok models while the configured account group returns `model_not_found`;
- direct xAI supplier creation or xAI credential entry;
- Grok image/video generation;
- automatic provider model discovery or catalog synchronization;
- archived-model restore UI or history browser;
- bulk deletion, bulk archive, or retention policies;
- advanced image editor UI, masks, or multi-turn editing;
- video model testing;
- retries, fallbacks, account routing, or multiple AIXORA credentials.

## 11. Contract References

- AIXORA API documentation: `https://mail.aixora.store/docs-page`
- OpenAI GPT model catalog and reasoning levels: `https://developers.openai.com/api/docs/models`
- OpenAI GPT Image 2 model contract: `https://developers.openai.com/api/docs/models/gpt-image-2`
- xAI Grok image generation: `https://docs.x.ai/developers/model-capabilities/images/generation`
- xAI Grok image editing: `https://docs.x.ai/developers/model-capabilities/images/editing`
- xAI Grok video generation: `https://docs.x.ai/developers/model-capabilities/video/generation`
