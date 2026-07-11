# Agnes Video Input Contract Design

## Goal

Make the AI Drama Agnes video path match the live Agnes Video V2.0 contract
without treating general reference assets as ordered video keyframes.

## Input Semantics

- Standard video (`mode` absent, `std`, or `pro`) sends zero or one image.
- When a standard shot references several assets, only its single
  `shot_keyframe` is a provider video input. Scene, character, outfit, and prop
  references remain audit inputs and are not sent to Agnes as video frames.
- A standard shot with more than one `shot_keyframe` is rejected locally.
- Keyframe video accepts two or three ordered images and sends
  `extra_body.image` with `extra_body.mode = "keyframes"`.
- The current product workflow does not infer start/end order from general
  asset references. Product-level keyframes remain unavailable until ordered
  keyframe roles are represented explicitly.
- The provider adapter independently rejects invalid image-count/mode
  combinations before making an HTTP request.

## Status And Evidence

- Agnes `pending` and `queued` statuses normalize to internal `submitted`.
- Provider failures keep the stable browser-facing error message while
  persisting sanitized diagnostic metadata.
- Persisted metadata must redact API keys, bearer tokens, secret-like fields,
  and signed asset URL `signature` values.

## Runtime Validation

1. Run focused mocked provider and execution tests.
2. Run M3 and M4 verifiers and the full default test suite without real Agnes
   traffic.
3. Start the Web service from the inner repository root with the existing
   runtime database and public asset base URL.
4. Require a freshly signed asset URL to return HTTP 200 with an image content
   type through `assets.deltadevalex.fun`.
5. Run one explicitly authorized product-level standard single-image smoke
   test, poll using the response `video_id`, download the MP4, and verify local
   result persistence.

## Non-Goals

- No database schema expansion.
- No automatic conversion of general references into keyframes.
- No retry loop that submits additional real Agnes jobs implicitly.
- No full chapter production or UI redesign.
