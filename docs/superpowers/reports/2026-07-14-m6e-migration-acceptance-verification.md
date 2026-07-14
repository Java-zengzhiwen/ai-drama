# M6E Migration And Acceptance Verification

Date: 2026-07-14  
Branch: `feat/m6e-migration-acceptance`  
Base: `feat/m6d-management-ui@e999eb5bfbfbce423ce1bcbd16efbdd595afdbb4`

## Result

`READY_FOR_REVIEW`

M6E closes the migration, recovery, temporary-store maintenance, backup/restore, fake-provider acceptance, browser acceptance, rollback, and release-verification scope. The production M6 supplier execution flag remains disabled.

```text
PRODUCTION_FLAG_ENABLED=false
REAL_PROVIDER_REQUESTS=false
REAL_TEXT_REQUEST_COUNT=0
REAL_IMAGE_REQUEST_COUNT=0
REAL_VIDEO_REQUEST_COUNT=0
```

## Acceptance Matrix

| Criterion | Result | Executable evidence |
| --- | --- | --- |
| M6E-001 fresh migration | PASS | Fresh store applies every migration and starts |
| M6E-002 legacy migration | PASS | M5 and M6A-D identities/history remain readable |
| M6E-003 migration replay | PASS | Ledger remains unique across repeated startup |
| M6E-004 credential crash recovery | PASS | Replace/delete crash checkpoints converge to ready, deleted, or corrupt |
| M6E-005 active legacy backfill | PASS | Recoverable non-terminal jobs preserve provider video IDs and never resubmit |
| M6E-006 object inventory | PASS | All structured object references are protected; corruption and unknown types fail closed |
| M6E-007 safe GC | PASS | Dry-run default; apply requires temporary marker, verified backup, stable inventory, and grace |
| M6E-008 backup/restore | PASS | SQLite, objects, secrets, journal paths, hashes, modes, and app startup verified |
| M6E-009 fake text/image/video | PASS | Durable runs, jobs, assets, results, local PNG/MP4, and sanitized evidence |
| M6E-010 submit exactly once | PASS | Restart recovery preserves the provider video ID and submit count |
| M6E-011 rerun semantics | PASS | Inherited and current-model reruns create distinct frozen snapshots |
| M6E-012 hot reload | PASS | Old queued work keeps V1 while future work resolves V2 |
| M6E-013 feature-flag rollback | PASS | Off/on/off restart preserves history and disables supplier invocation when off |
| M6E-014 complete Playwright | PASS | Management, fake execution, result page, refresh, keyboard, 1440/1180/768, console/network checks |
| M6E-015 secret hygiene | PASS | Write-only API, masked projection, sanitized URLs/evidence, no secret in DOM/storage/readback |
| M6E-016 zero real requests | PASS | Worker DNS/TCP/UDP denial plus loopback-only browser traffic |
| M6E-017 M1-M5 regression | PASS | M3/M4/M6B/M6C/M6D and clean-worktree storyboard verifiers pass |
| M6E-018 release readiness | PASS | Backup, rollback, verifier, migration, and repository hygiene gates pass |

Final semantic verifier token: `M6_SUPPLIER_MODEL_MANAGEMENT_PASS`.

## Migration And Recovery

- Fresh and replayed stores preserve one migration ledger entry per migration, stable supplier/model identities, current pointers, and monotonic revisions.
- Legacy statuses `queued`, `submitting`, `submitted`, `polling`, `completed`, and `failed` are covered. Submitted/polling rows with provider IDs are backfilled without submit; missing provider evidence fails closed as `LEGACY_PROVIDER_ID_MISSING`; terminal rows remain unchanged.
- Credential recovery covers journal creation, file fsync, pending finalize, rename, ready commit, pending delete, file removal, and delete finalize. Secrets remain mode `0600`; missing unrecoverable files become `credential_storage_corrupt` and block execution.

## Storage Operations

- Inventory discovers every schema column named `object_id` or ending in `_object_id`; referenced, unknown, corrupt, and grace-period objects are never GC candidates.
- Inventory identity is independent of GC grace policy, so a verified backup can authorize a later policy-specific plan without changing store identity.
- GC apply is restricted to roots carrying `.m6e-temporary-root`, requires a matching verified backup and unchanged inventory hash, and was exercised only against pytest temporary directories.
- Backup uses SQLite backup/checkpoint semantics and records relative member paths, modes, sizes, and SHA-256 without file contents. Restore requires an empty destination, verifies the exact member set and hashes, relocates credential/journal paths, and preserves semantic identities.

## Fake Provider And Browser

The Python E2E configures one local fake supplier with text/image/video models, current credential, defaults and overrides, then persists text output, image job/asset, video submission/poll/fetch/result, two reruns, and V1/V2 snapshots. It proves three video submits for three distinct jobs and no resubmit across restart.

Playwright saves and executes a local TypeScript adapter through the real isolated Worker, persists image/video evidence, displays local video results, verifies both rerun modes and queued V1 retention after V2 save, refreshes routes, uses keyboard tab navigation, and checks 1440, 1180, and 768 pixel viewports. Browser requests remain loopback-only; console errors and unexpected HTTP failures are empty.

## Verification Commands

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
630 passed, 1 skipped

npm --prefix web run test -- --run
93 passed, 4 skipped

npm --prefix web run build
PASS

npm --prefix web run test:e2e
10 passed

npm --prefix worker test
9 passed

python3 tools/verify_m3_agnes_generation.py
PASS

python3 tools/verify_m4_chapter_rehearsal.py
PASS

python3 tools/verify_m6b_model_catalog_binding.py
PASS

python3 tools/verify_m6c_adapter_cutover.py
M6C-001..M6C-015 PASS

python3 tools/verify_m6d_management_ui.py
M6D-001..M6D-015 PASS

python3 tools/verify_m6_supplier_model_management.py
M6E-001..M6E-018 PASS

python3 migration/tools/verify_migration.py
valid; checked_files=81

python3 tools/verify_storyboard_workflow.py --report-dir /tmp/ai-drama-m6e-storyboard-report
STORYBOARD_TECHNICAL_VERDICT=PASS

git diff --check
PASS
```

The first attempt to run Vitest and Playwright concurrently caused CPU starvation and timeout failures in unrelated existing tests. Serial reruns completed in 8.20 and 17.1 seconds respectively with all tests passing. No timeout was enlarged and no product behavior changed.

Known non-blocking warnings are the existing Starlette `httpx` deprecation, Python 3.14 asyncio-policy deprecations, React test `act(...)` warnings, and the existing Vite main-chunk size warning.

## Security And Repository Hygiene

- Verifier subprocesses remove known real Provider credential variables and force mock runtime/default flag-off behavior. The isolated Playwright M6 server enables the flag only for a temporary local data root and local fake adapter.
- No historical real smoke script was run. No API key, Bearer token, password, signed URL, credential file, runtime database, private image, or private video is added to Git.
- Credentials are excluded from ordinary object GC and remain write-only through the restored application.
- Management APIs retain application-layer loopback enforcement; forwarded headers remain untrusted unless an explicit trusted proxy is configured.

## Rollback

Set `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED=false` and restart. Legacy execution routing returns without deleting M6 supplier, model, binding, snapshot, job, result, or audit evidence. The full operator sequence, abort thresholds, backup gate, restore drill, and post-rollback checks are in `docs/operations/m6-rollout-rollback.md` and `docs/operations/m6-backup-restore.md`.

## Independent Read-Only Reviews

Mandatory roles are specification/acceptance and architecture/technical/security/release. Both initial reviews inspected `f0ebcb2386712b187f358e044907b563ae57f08f` and returned `REQUEST_CHANGES` without modifying files or contacting a real Provider.

| Severity | Initial finding | Correction in `e95d88936ce191edd10e5222562134fdc9759d06` |
| --- | --- | --- |
| BLOCKER | Legacy queued/submitting rows without provider IDs remained non-terminal and could be submitted by the poller | Backfill now terminalizes them before runtime/credential resolution; poller submit-count regression is zero |
| BLOCKER | Flag-off rollback allowed snapshot-bearing jobs to fall through legacy submit/poll | Execution and poller freeze all active snapshot jobs while disabled; off/on/off counting backend stays at zero |
| BLOCKER | GC accepted a self-declared three-field backup JSON | GC now uses shared manifest verification for exact payload member set, size, SHA-256, mode, inventory, and credential safety |
| HIGH | M6E-002 had no real M5 or M6A-D stage-shaped upgrade fixtures | Added pre-M6 product schema/history plus M6A, M6B, M6C, and M6D ledger/data boundary upgrades with replay and pointer checks |
| HIGH | Backup/restore fixture was not a complete M6 store | Fixture now includes supplier runtime, credential, model, binding, snapshot, active/completed jobs, result, asset, media, orphan, restored app, and resumed fake poll/fetch |
| HIGH | Backup/restore allowed overlapping paths, unsafe credential mode, mixed payload evidence, and incomplete durability checks | Added overlap/symlink rejection, ready regular-file `0600` and content-hash gates, copied-snapshot DB/object/credential validation, payload inventory, and file/directory fsync |
| HIGH | Playwright used reload/sidecar evidence without an actual app restart or public-client rejection | Added a real uvicorn stop/start on the same temporary data root, browser-visible resumed result, and a browser navigation through simulated public ingress returning `LOCAL_MANAGEMENT_ONLY` |
| HIGH | Rollback acceptance did not execute flag-on model resolution | Flag-on now resolves built-in text/video models, credentials, bindings, a local fake text invocation, and queued/polling snapshots before flag-off restart |
| BLOCKER | Backup manifest verification opened the copied database through writable stores, so verification could mutate backup evidence and break repeated verify/restore | `74b80f72f1bf9808bb7d460d3931135deb0ffbed` validates the copied database through SQLite read-only mode; regressions verify stable hashes, repeated verification, repeated restore, and restore after GC apply |

Post-correction verification on `74b80f72f1bf9808bb7d460d3931135deb0ffbed`:

- Full Python: `630 passed, 1 skipped`.
- Vitest: `93 passed, 4 skipped`.
- Playwright: `10 passed`, including two M6E tests.
- Worker: `9 passed`.
- M3, M4, M6B, M6C, M6D, migration, storyboard, and M6E semantic verifiers: PASS.
- `M6_SUPPLIER_MODEL_MANAGEMENT_PASS`; production flag false; real request counts zero.

Both reviewers must re-inspect the exact report-bearing descendant and return PASS with no blocker/high before handoff.
