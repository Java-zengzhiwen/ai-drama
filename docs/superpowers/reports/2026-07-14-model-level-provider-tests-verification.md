# Model-Level Provider Tests Verification

Date: 2026-07-15

Branch: `feat/model-level-provider-tests`

Reviewed implementation commit: `7d691cc9acf3e306f7ea29e7ef9011167e66ebf4`

## Result

`READY_FOR_REVIEW`

The supplier model catalog now exposes a model-row test action for enabled text
and image models. The action opens an explicit real-request confirmation dialog,
persists a frozen execution snapshot before execution, and displays normalized
text or locally persisted image results. Video models are intentionally outside
this phase.

The production model-test feature flag remains disabled by default. No real
provider request was made during implementation or verification.

## Implemented Contract

- Model-level test actions are available only for enabled text and image models.
- Each test requires explicit confirmation that one real request may incur cost.
- The server resolves the selected model directly and freezes supplier, code,
  config, model revision, credential version, runtime, helper, and rate bucket.
- Test runs are durable, auditable, snapshot-aware, and isolated from project
  generation history.
- Text responses normalize output and usage. Image bytes are downloaded to the
  local object store and previewed through the loopback-only content API.
- Submission is claimed exactly once. Ambiguous Worker outcomes fail closed and
  are never automatically resubmitted.
- Browser response-loss recovery retains the original idempotency key. A single
  recovery 404 or transient failure cannot unlock a duplicate paid request.
- Deterministic create-time 4xx errors display their safe configuration message,
  clear the unused key, and allow correction and retry.
- Normal M6 text/image idempotent replay occurs before shared bucket limiting.
  Image submission uses a single SQLite transaction to CAS the job and attempt
  from `queued/prepared` to `submitting/submitting` before gateway invocation.
- Management APIs remain loopback-only. Browser, Web Vitest, Worker, and Python
  test transports deny non-loopback traffic by default.
- The custom supplier adapter template and built-in examples include detailed
  Chinese comments and the approved AI-assisted supplier integration steps.

## Verification Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Python suite | PASS | `668 passed, 1 skipped` |
| Web Vitest | PASS | `109 passed, 4 skipped` |
| Web production build | PASS | TypeScript and Vite build completed |
| Worker tests | PASS | 9 tests through the default Node network-denial hook |
| Playwright | PASS | 11 browser tests, including the pre-transport external probe |
| Model-test verifier | PASS | `MTEST-001` through `MTEST-015` |
| M6 semantic verifier | PASS | `M6E-001` through `M6E-018` |
| Migration verifier | PASS | Included in M6E fresh, staged, and replay migration gates |
| Diff hygiene | PASS | `git diff --check` |
| Tracked secret scan | PASS | No real key, password, signed URL, or bearer token found |

The tracked scan found two known synthetic Bearer strings in provider unit test
fixtures. They are not credentials and are retained to verify sanitization.

## Network And Provider Evidence

- Python tests deny non-loopback socket and DNS traffic.
- Web Vitest loads the Node DNS/TCP/UDP denial bootstrap by default and includes
  an active external socket probe.
- Playwright installs a BrowserContext route before each test and aborts all
  non-loopback HTTP(S) requests before transport. An active external fetch probe
  proves the route is effective.
- Worker tests run with the Node network-denial bootstrap.
- Provider execution tests use deterministic fake gateways and assert exact call
  counts, including a two-connection concurrent image submission claim.

```text
PRODUCTION_MODEL_TEST_FLAG_ENABLED=false
PRODUCTION_M6_EXECUTION_FLAG_ENABLED=false
REAL_PROVIDER_REQUESTS=false
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

## Independent Reviews

Two independent read-only reviewers inspected exact implementation commit
`7d691cc9acf3e306f7ea29e7ef9011167e66ebf4` after all blocker/high fixes:

- Specification/acceptance: `PASS`; blockers `NONE`; high findings `NONE`.
- Architecture/technical/security: `PASS`; blockers `NONE`; high findings `NONE`.

Earlier review findings were closed with tests and implementation changes for
response-loss idempotency, persistent recovery locking, shared frozen-bucket
limiting, browser and Node transport denial, built-in code preservation, runner
CAS races, deterministic preflight errors, and concurrent image submit-once.

## Rollback

Keep `AI_DRAMA_MODEL_TESTS_ENABLED=false` to disable the model-test API and UI
without removing schema or history. Keep
`AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=false` to preserve the established M6
production rollback gate. Enabling either flag and making a real provider request
requires a separate explicit operational decision.
