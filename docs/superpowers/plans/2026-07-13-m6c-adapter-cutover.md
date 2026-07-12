# M6C Adapter Cutover Implementation Plan

## Guardrails

- Branch: `feat/m6c-adapter-cutover`, based on the approved M6B head.
- `M6_SUPPLIER_EXECUTION_ENABLED` defaults to `false`; disabled mode preserves the M3-M5 adapters and poller.
- Tests use only local fake suppliers and deny unexpected network access. No real Provider request is permitted.
- Only additive schema changes are allowed. Existing generation columns, provider IDs, results, and history remain readable.

## Task 1: Durable M6C persistence contract

Add an additive migration for nullable `generation_jobs` snapshot identity and a durable `generation_submission_attempts` table. The attempt row records prepared/submitted/committed/unknown state, sanitized evidence, provider ID, and attempt number. Add store methods with transactional transitions and snapshot-aware idempotency conflict checks. Extend rerun records with resolution mode and source/new snapshot hashes without changing legacy reads.

Acceptance: fresh and M6B databases migrate; draft creation persists request and snapshot before any adapter call; a crash/unknown submit is terminally non-resubmittable; same key with a different snapshot returns `IDEMPOTENCY_CONFLICT`; legacy rows remain readable.

## Task 2: Provider-neutral adapter gateway

Add a gateway that resolves an operation through `ModelResolver`, builds/persists an immutable `ExecutionSnapshot`, loads the exact supplier version/config/credential, and invokes the compiled artifact through `SupplierWorker`. The gateway exposes provider-neutral `textRequest`, `imageRequest`, `videoSubmit`, `videoPoll`, and `videoFetch` operations. It passes only the selected credential/config to the worker and sanitizes persisted evidence. Missing or incompatible runtime/credential returns stable fail-closed codes.

Acceptance: fake text, image, and video adapters execute without network; exact snapshot fields route each call; worker protocol/runtime/helper mismatch fails closed; evidence contains no authorization, bearer, token, secret, or signed query.

## Task 3: Built-in adapter contracts

Add versioned built-in OpenAI-compatible text and Agnes image/video adapter artifacts/manifests. Agnes normal mode accepts one ordered `shot_keyframe`; keyframes mode accepts two or three; video polling uses `video_id`; statuses normalize to queued/polling/completed/failed; submit is a single operation and fetch is separate. Real HTTP is available only through injected execution helpers and is never enabled by tests.

Acceptance: contract tests cover payload normalization, usage normalization, `video_id` polling, 2-3 keyframe validation, stable error mapping, and secret/URL sanitization. No unconfirmed Agnes parameter is introduced.

## Task 4: Text and image execution cutover

When the feature flag is enabled, text requests use the resolved snapshot gateway. Image generation creates a durable job/request and snapshot in one database transaction before invoking `imageRequest`, stores failure evidence, downloads result bytes through the provider-neutral result path, and links the generated asset to the job/result. Flag-off behavior is unchanged.

Acceptance: fake text snapshot/evidence, image pre-persist/failure audit/asset linkage, restart no-duplicate behavior, and zero real network tests pass.

## Task 5: Video execution and poller routing

Route M6C jobs by their persisted snapshot to the exact supplier version, compiled artifact, model/config revision, credential version, helper/runtime fingerprint, and frozen rate bucket. Persist provider `video_id`, poll only that ID, fetch once on completion, and never resubmit on restart or malformed evidence. Unknown submit outcomes fail closed. Keep the legacy backend path behind the disabled flag.

Acceptance: fake submit counter is exactly one; polling resumes after restart; fetch is exactly once; per-job snapshots ignore current project bindings; runtime/credential failures are stable; rate limiting uses snapshot data.

## Task 6: Legacy backfill and rerun semantics

Before polling, idempotently backfill active non-terminal Agnes jobs with a `legacy_agnes_v1` supplier/version/model/config/runtime fingerprint and preserve the existing provider ID. Terminal legacy rows remain readable without a snapshot. Default rerun inherits supplier/config/model/provider/constraints/runtime fingerprint but resolves the current credential; an explicit current-model rerun resolves current binding. Missing current credentials fail before job creation.

Acceptance: active legacy jobs poll/fetch without resubmit; startup backfill is idempotent; both rerun modes record source/new hashes and distinct idempotency scopes; current credential removal returns `CREDENTIAL_MISSING`.

## Task 7: Fake provider, verifier, and regression evidence

Add deterministic local fake text/PNG/video responses, status scripts, failure/timeout/malformed/restart injection, and call counters. Add `tools/verify_m6c_adapter_cutover.py` with checks M6C-001 through M6C-013, JSON and Markdown output, and explicit zero real-request counters. Add focused pytest tests before implementation and preserve M1-M5 verifier coverage.

Acceptance: focused red/green tests, full Python/Web/Worker/build/E2E/migration/M3/M4/M6B/M6C verification, `git diff --check`, and no generated runtime data tracked.

## Task 8: Read-only review and delivery

Run two independent read-only reviews: specification compliance and technical/security. Fix all blocker/high findings, rerun the complete matrix, write `docs/superpowers/reports/2026-07-13-m6c-adapter-cutover-verification.md`, commit, and push `origin/feat/m6c-adapter-cutover`. Never run historical real smoke tests.

Rollback: set the feature flag false and restart; legacy adapters and poller continue using existing fields while additive M6C evidence remains available for audit.
