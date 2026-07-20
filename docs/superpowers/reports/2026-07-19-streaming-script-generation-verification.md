# Streaming Script Generation Verification

Date: 2026-07-20
Repository: `Java-zengzhiwen/ai-drama`
Branch: `fix/aixora-message-input-normalization`
Reviewed implementation commit: `0e7f2851992af183201fbb4fbdfc365f02644d51`

## Result

```text
RESULT=READY_FOR_REVIEW
SCRIPT_STREAMING_IMPLEMENTED=true
FORMAL_REVISION_AFTER_REQUIRED_VALIDATION_ONLY=true
SPEC_PRODUCT_REVIEW=PASS
TECHNICAL_SECURITY_REVIEW=PASS
PRODUCTION_FLAGS_DEFAULT_FALSE=true
```

The approved central-editor streaming design is implemented. A source-to-script request now creates one durable local session, invokes the exact frozen supplier snapshot once, replays locally persisted events after refresh, and publishes a formal script revision only after parsing and all required Skill validators pass.

## Implemented Contract

- Worker protocol supports bounded, versioned NDJSON `textStream` frames through the injected HTTP helper only.
- Provider frame order, sequence, size, identity and terminal state are validated by the Python host.
- Supplier evidence is host-owned and sanitized; adapter-returned evidence cannot become authoritative evidence.
- The Aixora Responses parser exposes only message `output_text`; reasoning and malformed response shapes cannot be promoted to script text.
- Streamed text remains a temporary draft until the first real Markdown heading and is displayed incrementally in the central script editor.
- The browser persists the active run identity, reconnects by replaying durable events, and deduplicates event sequences.
- A repeated start mutation reuses one idempotency key. Reconnect never submits a second Provider request.
- Failed and unknown-outcome sessions retain the partial draft and expose explicit recovery actions. The legacy synchronous generate button stays hidden while a streaming session is active.
- Parser and required Skill validators run against a non-formal candidate. Failed candidates do not enter `revisions`, do not consume a version number, and cannot enter editing or approval flows.
- On success, the formal revision, validator results and `SUCCEEDED` run state are committed atomically.
- Restart recovery completes an already committed successful revision without resubmission. A `VALIDATING` crash produces a durable `SUBMISSION_OUTCOME_UNKNOWN` terminal event and leaves the formal revision count unchanged.
- `AI_DRAMA_SCRIPT_STREAMING_ENABLED` remains fail-closed by default. The existing rollback path remains available when the flag is disabled.

## Verification Evidence

Final verification was run against implementation commit `0e7f2851992af183201fbb4fbdfc365f02644d51`.

| Verification | Result |
| --- | --- |
| Full Python suite | `774 passed, 1 skipped` |
| Full Web Vitest suite | `131 passed, 5 skipped` |
| Web production build | PASS |
| Supplier Worker suite | `37 passed` |
| Streaming focused runner/recovery tests | PASS |
| Streaming fake-provider acceptance | PASS; deterministic one-submit flow |
| Streaming semantic verifier | `STREAM-001` through `STREAM-012` PASS |
| M3 Agnes verifier | PASS |
| M4 chapter rehearsal verifier | PASS |
| M6B catalog/binding verifier | PASS |
| M6C adapter cutover verifier | `M6C-001` through `M6C-015` PASS |
| Migration verifier | PASS; 81 tracked migration files checked |
| Web streaming Playwright flow | PASS in final independent review |
| Responsive Product Design QA | PASS; five states at three viewports on the implementation line |
| `git diff --check` | PASS |
| Tracked secret scan | PASS through `STREAM-011` |

All automated tests, verifiers and reviewers ran with real network disabled and reported:

```text
AUTOMATED_REAL_TEXT_REQUEST_COUNT=0
AUTOMATED_REAL_IMAGE_REQUEST_COUNT=0
AUTOMATED_REAL_VIDEO_REQUEST_COUNT=0
```

## Authorized Real Request Ledger

The user separately authorized exactly one real request during diagnosis. That authorization was consumed by one controlled Aixora text request and the request succeeded. No retry, image request or video request was made. No API key, authorization header, raw Provider response, signed URL, private generated result, database or `runtime-data` file is included in Git.

```text
AUTHORIZED_REAL_TEXT_REQUEST_COUNT=1
AUTHORIZED_REAL_IMAGE_REQUEST_COUNT=0
AUTHORIZED_REAL_VIDEO_REQUEST_COUNT=0
AUTHORIZATION_REMAINING=false
```

The real request confirmed the reachable text route only. Deterministic completion, restart, reconnect, validation, exact-once and UI acceptance evidence comes from the local fake Provider and offline test suite.

## Independent Read-Only Reviews

### Specification And Product Review

```text
VERDICT=PASS
BLOCKERS=NONE
HIGH_FINDINGS=NONE
REVIEWED_COMMIT=0e7f2851992af183201fbb4fbdfc365f02644d51
REAL_PROVIDER_REQUESTS=false
```

The reviewer confirmed the approved streaming UX, target-duration propagation, refresh/reconnect behavior, explicit failure recovery, hidden legacy bypass, and formal-revision validation gate.

### Architecture, Technical And Security Review

```text
VERDICT=PASS
BLOCKERS=NONE
HIGH_FINDINGS=NONE
REVIEWED_COMMIT=0e7f2851992af183201fbb4fbdfc365f02644d51
REAL_PROVIDER_REQUESTS=false
```

The reviewer confirmed candidate-first validation, atomic formal publication, durable unknown-outcome recovery, snapshot routing, atomic preparation, feature-flag rollback, host-owned evidence and strict response parsing.

## Merge Boundary

This report is a review handoff, not authorization to merge. Production flags remain off by default. A merge to `main` requires the user's explicit approval after review.
