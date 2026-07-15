# AIXORA Adapter And Model Archive Verification

Date: 2026-07-15

Branch: `feat/aixora-adapter-model-archive`

Status: `AWAITING_REVIEW_FIX_CONFIRMATION`

## Outcome

The approved archive-delete behavior and AIXORA adapter were implemented. The existing local AIXORA supplier now exposes exactly four text models and one image model, retains its existing credential version, uses `https://www.aixora.store/v1`, and defaults reasoning effort to `medium`.

The existing `GPT-5.6 Sol` overlay had one immutable failed-test snapshot. Deleting it through the management contract archived it, removed it from normal model lists, and preserved its historical direct read.

Real acceptance was intentionally single-attempt and produced a mixed provider result:

- `gpt-5.6-sol`, `gpt-5.6-luna`, and `gpt-5.5` completed successfully through `/responses`.
- `gpt-5.6-terra` returned JSON that did not contain either supported Responses text shape and failed closed as `PROVIDER_RESPONSE_MALFORMED`.
- `gpt-image-2` text-to-image and image-to-image were each submitted exactly once and both returned the then-current generic `PROVIDER_HTTP_ERROR` in about one second.
- Before implementation, AIXORA model discovery did not advertise `gpt-image-2`. That is relevant context, but the persisted evidence cannot distinguish an account/route rejection from a request-contract rejection because the previous Worker collapsed HTTP status categories. The failures therefore remain unclassified Provider HTTP rejections. No parameter guessing, retry, fallback, or alternate model was attempted.
- The earlier authorized AIXORA `grok-4.5` research probe returned `model_not_found`; no Grok model was added.

The adapter and archive implementation are ready for code review. Provider readiness is currently proven for three text models, not for Terra or GPT Image 2.

## Implemented Contract

- Stable AIXORA manifest models:
  - `gpt-5.6-terra` — text
  - `gpt-5.6-sol` — text
  - `gpt-5.6-luna` — text
  - `gpt-5.5` — text
  - `gpt-image-2` — image
- Responses API text normalization with reasoning effort allowlist:
  `none`, `low`, `medium`, `high`, `xhigh`, `max`.
- GPT Image 2 generation through `/images/generations`.
- GPT Image 2 editing through `/images/edits` with Worker-owned multipart assembly.
- Versioned helper v2 with bounded host-side image base64 decoding, image magic validation, declared input download, data-URI input decoding, aggregate multipart limits, public-address checks, pinned DNS, peer-IP verification, redirect denial, and one-shot exact provider-result URL download. Immutable helper v1 snapshots remain executable without v2 media privileges.
- Archive metadata and replay-safe migration for historically referenced overlay models.
- Active project bindings remain a delete blocker; no-reference overlays still physically delete.
- Archived identities remain readable historically but are hidden from normal catalogs and rejected by new binding/resolution.

## Automated Verification

All automated verification ran with real Provider requests disabled and network denial enabled.

| Verification | Result |
| --- | --- |
| Python pytest | 691 passed, 1 skipped |
| Web Vitest | 109 passed, 4 skipped |
| Web production build | PASS |
| Playwright E2E | 11 passed |
| Supplier Worker tests | 26 passed |
| AIXORA semantic verifier | 10/10 PASS — `AIXORA_MODEL_ARCHIVE_PASS` |
| Model-level provider-test verifier | 15/15 PASS — `MODEL_LEVEL_PROVIDER_TESTS_PASS` |
| Migration verifier | valid, 81 tracked files |
| `git diff --check` | PASS |

Automated counters:

```text
AUTOMATED_REAL_PROVIDER_REQUESTS=false
AUTOMATED_REAL_TEXT_REQUEST_COUNT=0
AUTOMATED_REAL_IMAGE_REQUEST_COUNT=0
AUTOMATED_REAL_VIDEO_REQUEST_COUNT=0
AUTOMATED_PRODUCTION_M6_EXECUTION_FLAG_ENABLED=false
```

The long-running loopback feature-test service already had model tests and M6 supplier execution enabled before this increment so the user can exercise business binding locally. This change did not enable or modify a production deployment flag.

The automated verifier uses only fake/local transports. It verifies the adapter normalization, pre-network multipart assembly path, media boundaries, archive behavior, and default network denial; it does not independently reproduce or certify the real acceptance ledger below.

## Authorized Real Acceptance Ledger

No item below was automatically retried.

| Capability | Model | Attempts | Result | Safe evidence |
| --- | --- | ---: | --- | --- |
| text | `gpt-5.6-terra` | 1 | FAIL | `PROVIDER_RESPONSE_MALFORMED`; 9.145 s; no normalized output |
| text | `gpt-5.6-sol` | 1 | PASS | 6.153 s; normalized output present; usage persisted |
| text | `gpt-5.6-luna` | 1 | PASS | 5.386 s; normalized output present; usage persisted |
| text | `gpt-5.5` | 1 | PASS | 8.123 s; normalized output present; usage persisted |
| text-to-image | `gpt-image-2` | 1 | FAIL | `PROVIDER_HTTP_ERROR`; 0.988 s; no media persisted |
| image-to-image | `gpt-image-2` | 1 | FAIL | `PROVIDER_HTTP_ERROR`; 1.132 s; non-sensitive 1x1 PNG input fixture; no result media persisted |
| video | none | 0 | NOT RUN | Out of scope |

```text
REAL_TEXT_REQUEST_COUNT=4
REAL_TEXT_SUCCESS_COUNT=3
REAL_TEXT_TO_IMAGE_REQUEST_COUNT=1
REAL_IMAGE_TO_IMAGE_REQUEST_COUNT=1
REAL_VIDEO_REQUEST_COUNT=0
PREIMPLEMENTATION_GROK_TEXT_PROBE_COUNT=1
PREIMPLEMENTATION_GROK_RESULT=model_not_found
```

The report contains no raw provider response, API key, bearer value, signed URL, runtime ID, database, generated image, or private asset.

## Runtime State Validation

```text
SOURCE_SAVED=true
CONFIG_SAVED=true
CREDENTIAL_PRESERVED=true
HISTORICAL_OVERLAY_ARCHIVED=true
ACTIVE_MODEL_COUNT=5
SERVICE_RESTART_VALIDATED=true
```

The configured supplier is immediately available to current project workflows after a project binds one of its text or image model identities to the corresponding capability/operation. Existing immutable jobs continue using their own snapshots.

## Security And Secret Scan

- Supplier code is explicitly trusted local user-edited code. Its VM context exposes no import, `require`, `process`, native fetch, filesystem, environment, socket, or subprocess API. This is an API-isolation boundary, not a security claim that `node:vm` safely executes hostile code.
- The Worker uses Node's permission model as defense in depth: read access is limited to Worker sources, write access to the process temporary root, and child processes and Worker threads are not granted.
- The immutable snapshot stores only the selected credential version ID. Plaintext is read from the credential store at execution time, injected into that Worker invocation, and used only to build the request Authorization header.
- The Worker process receives a cleaned environment and the supplier VM cannot read host media globals.
- Same-origin and cross-origin Provider result URLs are exact, one-shot, GET-only byte downloads without supplier-controlled request metadata. Every `imageRequest` byte response must declare PNG/JPEG/WebP and match its magic before Worker return and Python persistence; frozen `videoFetch` continues to accept its non-image media response.
- Validation, pytest, Vitest, Playwright, Worker tests, and both verifiers make zero real provider requests.
- Tracked bearer/API-key hits were classified as variable interpolation, redaction logic, documentation placeholders, or test fixtures; no live credential value was found.
- `runtime-data`, databases, real results, and credential files remain outside Git.

## Rollback

- Disable the AIXORA supplier or affected model to prevent new work.
- Switch the supplier current version/config revision back to the previous immutable revision; do not delete history.
- Leave archive metadata and historical snapshots intact.
- Existing submitted/polling work continues from its frozen snapshot and credential version.
- Do not bind `gpt-5.6-terra` or `gpt-image-2` for production-like local work until their provider response/route gaps are separately resolved and verified.

## Independent Review

The first two independent read-only reviews examined candidate `0acd00f8f25f779e41d787c0ab115c7705d5e53a` and requested changes. No real Provider request was made during review.

The correction set addresses every blocker/high finding:

- documents the trusted-local-code boundary and adds Node permission-model defense in depth instead of treating `node:vm` as a hostile-code sandbox;
- upgrades new artifacts to helper API v2 while retaining exact helper v1 snapshot compatibility;
- constrains dynamic result URLs to one-shot, GET-only bytes with no headers/query/body and validates public resolution, peer IP, redirect status, response limit, media type, and image magic;
- enforces per-file and aggregate input limits before multipart concatenation;
- moves model archive/delete reference checking and mutation into one immediate database transaction;
- validates image magic in both Worker and Python persistence paths;
- preserves frozen helper v1 video-result downloads while enforcing image media type and magic for every helper v2 `imageRequest`, including same-origin result URLs;
- narrows verifier and report claims to the offline paths actually exercised;
- updates the browser fixture to return a valid bounded PNG through helper v2.
- proves the shared 1x1 PNG fixture has valid chunk CRCs and a decodable zlib image stream.

Final specification/acceptance and architecture/technical/security re-review of the correction commit is pending.
