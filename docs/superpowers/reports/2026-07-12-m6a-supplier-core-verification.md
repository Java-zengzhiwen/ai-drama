# M6A Supplier Core Verification

## Result

- Stage: M6A Supplier Core
- Result: READY_FOR_REVIEW
- Branch: `feat/m6a-supplier-core`
- Approved base: `a6eb1ab04e450a308599a749e4fe5f95e745f560`
- Reviewed implementation head: `682851d176725455ac3a714ea79cc4fd4df2fbb2`
- Implementation started: true
- Real Provider requests: none

M6A adds the supplier/version/config/credential persistence foundation, recoverable
credential storage, immutable TypeScript compilation artifacts, an isolated Node
worker, and application-layer loopback enforcement. It does not add project model
bindings, adapter cutover, management UI, or real Provider verification.

## Verification

All commands ran from the repository worktree with no real Provider authorization.

| Check | Result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q` | PASS: 529 passed, 1 skipped |
| `npm --prefix web run test -- --run` | PASS: 60 passed, 2 skipped |
| `npm --prefix web run build` | PASS |
| `npm --prefix web run test:e2e` | PASS: 2 passed |
| `npm --prefix worker test` | PASS: 3 passed |
| `python3 tools/verify_m3_agnes_generation.py` | PASS |
| `python3 tools/verify_m4_chapter_rehearsal.py` | PASS |
| `python3 migration/tools/verify_migration.py` | PASS: 81 files checked |
| `git diff --check` | PASS |

The full Python suite was run without a concurrent verifier after an earlier
concurrent run showed a transient nested-verifier failure. The isolated verifier
and both subsequent full runs passed.

## Safety Evidence

- Python tests deny non-loopback DNS, reverse DNS, TCP, `connect_ex`, UDP
  `sendto`, and `sendmsg` by default.
- Node tests preload a guard for TCP, connected and unconnected UDP, top-level
  callback/Promise DNS APIs, and callback/Promise Resolver instances.
- Worker validation exposes no native network API and returns
  `NETWORK_DISABLED_DURING_VALIDATION` from its injected HTTP helper.
- The tracked diff contains no added `Authorization`, `Bearer`, `api_key`,
  `token`, signed-query, or expiry assignments.
- Endpoint review found only existing Agnes defaults, `.invalid` test fixtures,
  and package-lock registry URLs. No new production Provider endpoint was added.
- Runtime data, databases, credentials, generated reports, and private outputs
  are not tracked by this change.

These test-process guards enumerate runtime APIs and are not an operating-system
network sandbox. Production supplier code remains separately constrained by the
restricted VM, forbidden imports/globals, scrubbed environment, injected helpers,
deadlines, output limits, and Python process termination.

## Review Record

Two independent read-only reviewers examined commit `682851d` after all findings
were corrected.

### Specification Compliance

`SPEC_REVIEW=PASS`, `BLOCKERS=NONE`.

The reviewer verified capability-to-export validation, supplier runtime
fingerprints, loopback management behavior, complete Python/Node test-network
guards, focused Python tests, Worker tests, and `git diff --check`.

### Technical And Security

`TECHNICAL_SECURITY_REVIEW=PASS`, `BLOCKERS=NONE`.

The review found and then verified fixes for VM constructor escape, credential
mode/recovery durability, atomic creation idempotency, conditional mutation CAS,
runtime compatibility fail-closed behavior, compiler export validation, and DNS,
TCP, and UDP test-network bypasses.

## Rollback

1. Stop the application before changing schema or credential state.
2. Disable the new supplier routes and worker by deploying the approved pre-M6A
   base. No production adapter or poller uses M6A supplier records yet.
3. Restore the pre-M6 schema backup if supplier tables must be removed. M6A
   migrations are additive and do not rewrite M1-M5 runtime rows.
4. Preserve credential journal and secret files until recovery reaches a terminal
   state; never delete a `pending_finalize` or corrupt credential by hand.
5. Restart on the pre-M6A build. Existing global backend selection and legacy
   Agnes/OpenAI execution paths remain unchanged because adapter cutover is M6C.

The rollback point is before M6A supplier route/worker activation and before any
future M6B binding or M6C cutover data depends on these records.

## Known Warnings

- Existing Starlette/httpx and asyncio policy deprecation warnings remain.
- The Web build reports the existing large-chunk warning.
- Supplier config compilation can leave an unreferenced immutable object after a
  losing ETag race; it cannot change current configuration and can be reclaimed
  by later object-store garbage collection.
