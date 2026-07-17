# AIXORA Model Reasoning Controls Verification

Date: 2026-07-17

Branch: `feat/aixora-adapter-model-archive`

Status: `READY_FOR_REVIEW`

## Outcome

The approved reasoning-control increment is implemented without a database migration:

- AIXORA now declares five enabled text models: `gpt-5.5`, `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-luna`, and `gpt-5.6-terra`.
- Plain `gpt-5.6` uses stable ID `07c95486e414569bb18f694431f3ad4f`.
- Every current AIXORA text model stores `constraints.reasoning_effort=medium` in its immutable model definition.
- The unavailable `gpt-image-2` declaration was removed. Local manifest reconciliation preserved its stable identity and immutable revision while setting `enabled=0`.
- New text execution resolves `request override -> model revision -> supplier config -> medium`, freezes the effective value in `ExecutionSnapshot.resolved_constraints`, and gives the Worker only that frozen constraint.
- Model tests accept one optional `low`, `medium`, or `high` override, include it in the durable request and idempotency identity, restore it after refresh, and return the effective value in the safe read.
- Model catalog create/edit mutations reject invalid reasoning definitions with `INVALID_REASONING_EFFORT` before persistence. The AIXORA editor preserves advanced JSON and no longer silently converts an invalid value to `medium`.

## Provider Evidence And Request Ledger

Before implementation, one authenticated non-generating metadata request confirmed the current AIXORA account catalog:

```text
GET /v1/models
HTTP_STATUS=200
MODEL_COUNT=7
TEXT_MODELS=gpt-5.4,gpt-5.4-mini,gpt-5.5,gpt-5.6,gpt-5.6-luna,gpt-5.6-sol,gpt-5.6-terra
IMAGE_MODELS=none
HAS_GPT_IMAGE_2=false
```

No real generation request was made during implementation, automated verification, local runtime reconciliation, or review:

```text
REAL_TEXT_GENERATION_REQUEST_COUNT=0
REAL_IMAGE_GENERATION_REQUEST_COUNT=0
REAL_VIDEO_GENERATION_REQUEST_COUNT=0
AUTOMATED_REAL_PROVIDER_REQUESTS=false
```

Historical authorized Provider attempts remain recorded in `docs/superpowers/reports/2026-07-15-aixora-adapter-model-archive-verification.md`; this incremental report does not rewrite that ledger.

## Automated Verification

All automated commands used fake/local transports with default external-network denial.

| Verification | Result |
| --- | --- |
| Python pytest | 717 passed, 1 skipped after both review corrections |
| Web Vitest | 113 passed, 4 skipped after the review correction |
| Web production build | PASS |
| Playwright E2E | 11 passed |
| Supplier Worker | 26 passed |
| AIXORA semantic verifier v2 | 12/12 PASS |
| M6C verifier | 15/15 PASS |
| M6D verifier | 15/15 PASS when run serially |
| M3 Agnes verifier | PASS |
| M4 chapter rehearsal verifier | PASS |
| Migration verifier | valid, 81 tracked files |
| `git diff --check` | PASS |
| tracked Bearer-like secret scan | 0 matches |
| tracked OpenAI-key-like secret scan | 0 matches |

The first parallel M6D verifier attempt overlapped a separately launched Playwright run and failed only checks that depended on that shared browser run. A serial rerun passed all 15 checks; the report uses the serial result.

The default application setting remains:

```text
DEFAULT_M6_PRODUCTION_FLAG=false
```

The long-running loopback feature-test service intentionally has M6 execution and model tests enabled for user testing. That local test-service setting is not a production deployment flag.

## Local Runtime Reconciliation

The loopback management API saved the reviewed adapter source and the LaunchAgent was restarted. No model-test confirmation endpoint was called.

```text
SUPPLIER_SLUG=aixora
SUPPLIER_VERSION=ai-drama-2
CREDENTIAL_CONFIGURED=true
ENABLED_TEXT_MODELS=5
GPT_5_6_PRESENT=true
GPT_IMAGE_2_PRESENT_HISTORICALLY=true
GPT_IMAGE_2_ENABLED=false
TEXT_MODEL_DEFAULT_REASONING=medium
```

The feature remains reachable at `http://127.0.0.1:8000/suppliers`. A project can use these defaults after binding an enabled AIXORA text model to the relevant text capability or operation. Existing jobs remain bound to their original immutable snapshots.

## Security And Rollback

- No credential value, Authorization header, raw Provider response, signed URL, database, runtime object, or private generated result is included in Git.
- Invalid model defaults and unsupported image-test reasoning are rejected before a durable run or Provider request is created.
- Disable the AIXORA supplier or affected model to stop new work.
- Roll back by switching the supplier current version to its previous immutable version; do not delete model revisions or snapshots.
- Re-enable an AIXORA image model only after new Provider catalog/route evidence and a separately reviewed adapter revision.

## Review State

Two independent reviewers inspected candidate `0c41ac696cf9a2ff9240bedaad4d0e59a5b105f1` and found the same High issue: model catalog mutations accepted invalid reasoning definitions and the UI could silently normalize them. The first correction added service-boundary validation, stable HTTP 422 mapping, fail-closed UI behavior, and focused red/green tests. Technical/security review then found that structured values could still reach a Python membership check and return HTTP 500. Candidate `5f20532b26d591e79ef974bb95c9c3a613203d18` resolves values by field presence, validates the type before membership, and rejects strings, numbers, arrays, objects, booleans, null, and empty strings outside the supported enum without persistence or Provider traffic.

Final read-only reviews of exact implementation candidate `5f20532b26d591e79ef974bb95c9c3a613203d18`:

- Specification/acceptance: `PASS`; blockers `NONE`; high findings `NONE`.
- Architecture/technical/security: `PASS`; blockers `NONE`; high findings `NONE`.
- Both reviewers confirmed the verification ledger, zero real generation requests, default production flag false, stable invalid-input behavior, and absence of tracked sensitive evidence.
