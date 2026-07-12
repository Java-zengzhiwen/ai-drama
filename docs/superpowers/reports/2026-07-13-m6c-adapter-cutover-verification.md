# M6C Adapter Cutover Verification

## Result

Implementation started on `feat/m6c-adapter-cutover` from the approved M6B head.
No real Provider request was made; all request counters remain zero.

## Implemented

- Added the M6C plan and additive schema migration.
- Added snapshot/attempt fields and durable submission-attempt records to preserve
  submit-once behavior across restarts and unknown outcomes.
- Added provider-neutral adapter gateway and deterministic local fake adapter.
- Added stable video normalization that carries and polls `video_id`.
- Added the default-off `m6_supplier_execution_enabled` feature flag.
- Preserved legacy M3-M5 generation fields and paths.
- Added offline `verify_m6c_adapter_cutover.py`.

## Verification

| Check | Result |
| --- | --- |
| M6C offline verifier | PASS |
| M6B verifier | PASS |
| M3 Agnes verifier | PASS |
| M4 rehearsal verifier | PASS |
| `git diff --check` | PASS |
| Full Python suite | 563 passed, 1 skipped, 1 failed |

The single full-suite failure is the pre-existing storyboard verification
entrypoint timing out after 180 seconds; its stack is in
`tests/acceptance/test_storyboard_workflow_acceptance.py` and does not touch M6C
files. It must be resolved or explicitly waived before claiming a fully green
M6C acceptance run.

## Safety

`REAL_PROVIDER_REQUESTS=false`, `REAL_TEXT_REQUEST_COUNT=0`,
`REAL_IMAGE_REQUEST_COUNT=0`, and `REAL_VIDEO_REQUEST_COUNT=0`. No API key,
Bearer value, signed URL, database, runtime-data, or private generation result
is included in the changes.

## Review status

Two independent read-only reviews are required before merge: specification
compliance and technical/security. Their findings must be addressed before a
final READY_FOR_REVIEW handoff.

### Read-only review findings

Both reviews returned `REQUEST_CHANGES`. The remaining blockers are material:
the production poller and text/image paths are still legacy-only, queued jobs do
not yet build and persist a snapshot in the same transaction, active legacy
Agnes backfill is not implemented, and the rerun path does not yet fully attach
the inherited/current-credential snapshot before queueing. The new gateway and
verifier are tested offline, but are not sufficient evidence of a complete
cutover. This branch must not be marked ready or used for a real Provider test
until those blockers are fixed and the full regression suite is green.
