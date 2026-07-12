# M6 Supplier And Model Configuration Governance Contract

**Status:** Proposed for review

**Active milestone:** M6 — Supplier And Project Model Configuration

**Authority:** This contract governs M6 after approval, beneath `AGENTS.md` and the approved design at `docs/superpowers/specs/2026-07-12-provider-model-management-design.md`.

## Objective

Deliver the approved `Supplier -> Models` product through five independently reviewable stages without regressing the M1-M5 runtime or making real provider requests during default implementation and verification.

## Authority Order

1. Root `AGENTS.md` M6 rules.
2. This M6 governance contract.
3. Approved provider/model management design.
4. The active stage plan (M6A, M6B, M6C, M6D, or M6E).
5. Existing M1-M5 contracts, tests, verifiers, and migration rules.
6. Current implementation.
7. Official provider documentation, after explicit conflict review.

## Stage Boundaries

| Stage | Deliverable | Must not do | Merge gate |
|---|---|---|---|
| M6A | Supplier/version/config/credential schema, crash recovery, isolated Node worker, loopback guard | Bind projects, cut over adapters, build UI | Supplier-core tests, migration replay, worker zero-network tests |
| M6B | Stable model identities/revisions, project defaults/overrides, resolver, snapshot value object | Route production adapters or poller | Catalog/binding/idempotency tests and M6A regression |
| M6C | OpenAI-compatible and Agnes adapter cutover by immutable snapshot; durable image/video routing | Add management UI or real provider tests | Fake text/image/video E2E, restart recovery, M1-M5 regression |
| M6D | Loopback-only supplier/model/binding UI | Add new backend capabilities or remote management | Vitest, Playwright, accessibility, M6A-C regression |
| M6E | Migration recovery, verifier, acceptance evidence, final cutover readiness | Add new product capability or production rollout | SUP-001..SUP-028, full suites, deterministic reports |

## Default Denials

- No real HTTP request to Agnes, OpenAI, DeepSeek, Anthropic, xAI, or any custom supplier.
- No browser-direct provider call.
- No secret plaintext in API responses, logs, snapshots, fixtures, reports, exceptions, or Git.
- No supplier-management request from a non-loopback direct peer.
- No dynamic Node import, `require`, `process`, native `fetch`, filesystem, socket, child process, or worker-thread access from supplier code.
- No fallback to a current runtime when an immutable historical artifact/runtime/helper is unavailable.
- No automatic model fallback when a project binding is missing.
- No physical deletion of referenced model/supplier/credential history.

## Collaboration

- The main agent is the sole writer and committer.
- Read-only subagents may audit schema/migration, worker isolation, runtime routing, UI/API fit, and test coverage.
- Each subagent returns findings only; it may not edit files, expose secrets, or run a real provider request.
- The main agent reconciles findings against the active plan before commit.

## TDD And Commit Contract

Every implementation task follows:

```text
focused red test
-> confirm expected failure
-> minimal implementation
-> focused green
-> affected regression
-> spec review
-> code-quality review
-> focused commit
```

Do not weaken tests, rewrite expected outputs without a contract reason, or combine unrelated stage work.

## Migration Contract

- Schema changes use the repository migration mechanism and a monotonic `schema_migrations` ledger.
- Migrations are idempotent and replayable on fresh and legacy stores.
- Legacy fields remain readable until M6E explicitly approves cutover cleanup; M6 does not irreversibly delete them.
- Credential files use the approved journal protocol and fail closed on unrecoverable corruption.
- Active legacy Agnes jobs receive explicit `legacy_agnes_v1` snapshots before poller startup.
- Every stage documents and verifies its rollback point.

## Network And Secret Verification

Default test transports reject external hosts. Allowed network targets are loopback test servers created by the test itself. Safety scans must detect:

```text
Authorization
Bearer
api_key
token
signature=
expires=
provider endpoints
```

Hits must be classified as implementation constants, redacted fixtures, or violations. A violation blocks the stage.

## Stage Preflight

Before each implementation stage:

1. Confirm the expected branch, clean tree, and approved base SHA.
2. Read `AGENTS.md`, this contract, the approved design, and the active stage plan completely.
3. Confirm all earlier-stage interfaces named under `Interfaces` exist with matching signatures.
4. Run the earlier stage's focused verifier/tests.
5. Confirm no real-provider authorization has been inferred from M5 history.

If an authoritative artifact or required interface is missing, stop with the active stage's blocked token.

## Verification Baseline

Each stage runs its focused suites plus, before review:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python3 -m pytest -q
npm --prefix web run test -- --run
npm --prefix web run build
npm --prefix web run test:e2e
python3 tools/verify_m3_agnes_generation.py
python3 tools/verify_m4_chapter_rehearsal.py
python3 migration/tools/verify_migration.py
git diff --check
```

M6E additionally runs `python3 tools/verify_supplier_model_configuration.py`.

## Review And Merge

- Each stage is pushed under the Review Handoff Policy.
- No stage merges to `main` without user approval after review.
- Prefer fast-forward merge; no force push or squash unless explicitly requested.
- A later stage does not erase evidence or rewrite history from an earlier stage.

## Stop Conditions

Stop instead of improvising if:

- a task requires a real provider request;
- a secret would be printed or committed;
- a management API cannot be enforced loopback-only;
- the worker cannot fail closed under the required isolation model;
- migration replay loses M1-M5 data or active-job recoverability;
- the stage requires a schema/interface not approved by the design;
- a later-stage feature is needed to make the current stage testable;
- the working tree contains unrelated user changes that overlap the stage.

## Planning Completion

M6 governance planning is complete only when this contract and five stage plans exist, contain no placeholders, map SUP-001..SUP-028, pass docs-only validation, and are committed and pushed without production-code changes.

Final planning token:

```text
M6_GOVERNANCE_AND_PLANS_READY_FOR_REVIEW
```
