# M6C Adapter Cutover Verification

## Result

- Branch: `feat/m6c-adapter-cutover`
- Base: `feat/m6b-model-catalog-binding` at `77ff2dd`
- Implementation started: true
- Real Provider requests: false
- Real request counts: text=0, image=0, video=0

The initial `9c9e4cd` checkpoint received two `REQUEST_CHANGES` reviews. This
revision closes the specified blockers without deleting legacy fields or M1-M5
history. The M6 execution feature flag remains disabled by default.

## Cutover evidence

- OpenAI-compatible text and Agnes image/video TypeScript adapters compile to
  immutable artifacts. Execution networking is available only through the
  versioned helper; validation networking remains disabled.
- The Worker exposes no host function to the VM. HTTP calls cross a VM-local
  Promise queue, enforce selected-config HTTPS origins, reject redirects, apply
  timeout/output limits, and keep the Worker environment sanitized.
- Text runs persist request, immutable snapshot, scoped idempotency, normalized
  output/usage, and sanitized evidence before/after one adapter invocation.
- Image and video enqueue writes request reference, execution snapshot index,
  job, prepared submission attempt, and scoped idempotency in one SQLite
  transaction after content-addressed objects are written and validated.
- Image execution stores local bytes, generation result, and generated asset
  linked to the durable job. Accepted image recovery finishes local persistence
  without a second provider invocation.
- Video submission persists `prepared -> submitting -> accepted -> committed`.
  Accepted recovery commits locally; an unrecorded outcome fails closed as
  `SUBMISSION_OUTCOME_UNKNOWN` and is never resubmitted.
- Poll/fetch routes by each job's frozen supplier/version/artifact/model/config,
  original credential, helper/runtime fingerprint, and rate bucket. Agnes polls
  with `video_id` only.
- Active legacy Agnes jobs with a provider ID receive an idempotent
  `legacy_agnes_v1` snapshot before polling and are never resubmitted. Terminal
  legacy rows remain readable without a snapshot.
- Default rerun inherits source runtime/model/config/constraints and resolves the
  current credential. Current-model rerun resolves the current project binding.
  Missing current credential creates no job, attempt, idempotency row, or call.

## Verification

| Check | Result |
| --- | --- |
| M6C semantic verifier M6C-001 through M6C-015 | PASS |
| Full Python suite | PASS: 591 passed, 1 skipped |
| M3 Agnes verifier | PASS |
| M4 rehearsal verifier | PASS |
| M6B model catalog/binding verifier | PASS |
| Migration verifier | PASS: 81 files |
| Focused M6C/generation/snapshot regressions | PASS |
| Worker isolation pytest | PASS: 15 |
| Worker Node tests | PASS: 9 |
| Web Vitest | PASS: 60, skipped: 2 |
| Web build | PASS |
| Playwright | PASS: 2 |
| Phase 1 portable verifier | PASS |
| Clean-worktree storyboard verifier | PASS: technical verdict PASS |
| `git diff --check` | PASS |

The clean-worktree storyboard verdict is recorded after the implementation
checkpoint commit so its clean-tree gate measures the actual candidate commit
rather than an uncommitted workspace.

## Storyboard timeout root cause

The previous full-suite failure was not an M6C performance regression. The
storyboard entrypoint launched a verifier that ran the entire pytest suite twice;
the acceptance self-test recursively launched another full suite. One isolated
run exceeded 489 seconds. The verifier now executes a bounded storyboard and
shot-prompt contract set and excludes the entrypoint only from its non-selftest
inner run. Three isolated reproductions completed in 44.33, 36.31, and 34.33
seconds; each inner contract run passed 112 tests. No timeout was enlarged.

## Safety scan

- Default and verifier transports deny unexpected real network access.
- No real smoke test or historical real-provider script was executed.
- Persisted evidence removes authorization/secret fields and signed query data.
- No API key, bearer token, password, database, runtime-data, credential file,
  signed URL, private generated image, or private video is tracked.
- Content-addressed objects written before a losing SQL transaction are
  unreferenced and eligible for later M6E garbage collection; no database row
  references a missing request or snapshot object.

## Rollback

Set `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=false` and restart. Legacy text,
Agnes image/video, generation fields, poller behavior, and history remain intact;
additive M6C snapshots, attempts, runs, and backfill metadata remain audit-only.

## Review record

The initial two reviews returned `REQUEST_CHANGES`. Corrections covered complete
execution wiring, durable snapshots/idempotency, submit recovery, legacy routing,
verifier semantics, Worker isolation, SSRF protection, media transport, and
frozen resource limits.

- Final specification-compliance review: `PASS`, `BLOCKERS=NONE`.
- Final technical/security review: `PASS`, `BLOCKERS=NONE`.

The security review specifically verified public-only DNS resolution, fixed
lookup plus peer-IP checks, redirect/port restrictions, VM-local request queues,
bounded media references, legacy poll/fetch completion, and snapshot-frozen
Worker limits. The specification review verified the latest M6C-001 through
M6C-015 contract and M6 supplier submit-once recovery.

Final delivery verification ran from clean commit `1eb1dc2`: full Python passed
with 591 tests and one skip; storyboard technical verdict was `PASS`; Web,
Worker, Playwright, M3, M4, M6B, M6C, migration, and diff checks all passed.
