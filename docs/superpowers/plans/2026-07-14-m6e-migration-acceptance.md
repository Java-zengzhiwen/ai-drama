# M6E Migration And Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close M6 with replayable migration and credential recovery, safe temporary-store object maintenance and backup/restore, complete fake-provider acceptance, deterministic release evidence, and a reversible rollout posture.

**Architecture:** M6E adds operational services and CLI entry points around the existing `RuntimeStore`, `ProductStore`, credential journal, legacy snapshot backfill, and feature flag. Every destructive operation is dry-run by default and is tested only against temporary data roots. A semantic verifier composes focused migration, recovery, fake-provider, browser, security, and M1-M5 regression evidence without calling a real Provider.

**Tech Stack:** Python 3, SQLite, pathlib/hashlib/json, FastAPI test client, pytest, React/Vite/Vitest, Playwright, existing Node supplier Worker.

## Global Constraints

- Base is `feat/m6d-management-ui@e999eb5bfbfbce423ce1bcbd16efbdd595afdbb4`.
- `REAL_TEXT_REQUEST_COUNT=0`, `REAL_IMAGE_REQUEST_COUNT=0`, and `REAL_VIDEO_REQUEST_COUNT=0` throughout implementation and verification.
- `AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED` remains false for the user environment; flag-on tests use isolated temporary roots and fake adapters only.
- Never clean the user runtime data root. GC apply and restore drills require explicit temporary roots created by tests.
- Preserve legacy provider fields, historical projects/chapters/assets/prompts/jobs/results, provider job/video IDs, and terminal status rows.
- No new Provider capability, marketplace, multi-account, remote management, or irreversible schema cleanup.
- Main agent is the sole writer and committer. Two independent read-only agents must return PASS before handoff.

---

### Task 1: Migration And Credential Recovery Matrix

**Files:**
- Create: `tests/migration/test_m6e_migration_matrix.py`
- Create: `tests/fixtures/m6e_store_factory.py`
- Modify: `tests/web/test_supplier_credentials.py`
- Modify: `migration/tools/verify_migration.py`
- Modify: `migration/migration-manifest.json` only if a new additive migration artifact is required

**Interfaces:**
- `M6EStoreFactory(root: Path)` creates fresh, M5 legacy, intermediate M6A-D, active legacy Agnes, and credential-journal states.
- `migration_matrix(root: Path) -> dict` reports deterministic row counts, protected hashes, ledger entries, and replay status without secret plaintext.

- [ ] **Step 1: Write failing migration matrix tests.** Cover fresh startup, M5 history preservation, M6A-D intermediate replay, stable UUID/current pointers, monotonic revisions, two-pass idempotency, and no duplicate rows.
- [ ] **Step 2: Run the focused tests and confirm expected RED.** Run `python3 -m pytest -q tests/migration/test_m6e_migration_matrix.py`; expected failures identify missing fixture/matrix helpers rather than existing migration regressions.
- [ ] **Step 3: Implement minimal fixture and matrix support.** Reuse `RuntimeStore`, `ProductStore`, `install_builtin_adapters`, and `LegacyAgnesBackfill`; do not create a parallel migration engine.
- [ ] **Step 4: Extend active legacy coverage.** Test queued/submitting/submitted/polling backfill, completed/failed unchanged, provider ID/video ID preservation, no submit, repeated startup idempotency, and missing evidence fail-closed.
- [ ] **Step 5: Expand credential crash tests.** Inject crashes at journal creation, temp write/fsync boundary, pending finalize, rename, ready commit, pending delete, file removal, and delete finalize; assert convergence to ready/deleted/corrupt, mode `0600`, no fallback, and no plaintext output.
- [ ] **Step 6: Run focused GREEN and migration verifier twice.** Run the matrix test, `tests/web/test_supplier_credentials.py`, and `python3 migration/tools/verify_migration.py` twice.
- [ ] **Step 7: Commit.** Commit `test: verify m6e migration recovery matrix`.

### Task 2: Object Store Inventory And Safe GC

**Files:**
- Create: `ai_drama_web/operations/object_store_maintenance.py`
- Create: `tools/inventory_object_store.py`
- Create: `tools/gc_object_store.py`
- Create: `tests/operations/test_m6_object_store_maintenance.py`

**Interfaces:**
- `ObjectInventory.build() -> ObjectInventoryReport` enumerates stored objects and all live/protected DB references.
- `ObjectGarbageCollector.plan(grace_seconds: int) -> GCPlan` is deterministic and dry-run only.
- `ObjectGarbageCollector.apply(plan_hash: str, backup_manifest: Path) -> GCApplyReport` requires a matching inventory hash and verified backup.

- [ ] **Step 1: Write failing inventory tests.** Seed every object-bearing table and assert request/result/media/snapshot/source/compiled/config/model/revision/journal references are protected.
- [ ] **Step 2: Write failing safety tests.** Cover unknown type retained, credential directory excluded, age grace, hash mismatch marked corrupt and retained, changed inventory rejected, missing backup rejected, non-temporary root rejected in automated apply, and dry-run default.
- [ ] **Step 3: Run focused RED.** Run `python3 -m pytest -q tests/operations/test_m6_object_store_maintenance.py`; expect missing module/CLI behavior.
- [ ] **Step 4: Implement structured DB reference discovery.** Inspect SQLite schema/table columns through explicit allowlisted object-reference columns; fail closed when an unknown `*_object_id` column appears.
- [ ] **Step 5: Implement content-address validation and deterministic reports.** Output count, bytes, classified type, age, corruption, inventory hash, and candidate IDs without file contents.
- [ ] **Step 6: Implement guarded apply.** Require `--apply`, `--data-root`, `--backup-manifest`, `--inventory-hash`, local temporary root marker, verified backup, unchanged inventory, and grace period.
- [ ] **Step 7: Run focused GREEN plus CLI subprocess tests.** Prove dry-run cannot delete and apply only deletes eligible candidates in a test temporary root.
- [ ] **Step 8: Commit.** Commit `feat: add safe m6 object inventory and gc`.

### Task 3: Backup And Restore Dry Run

**Files:**
- Create: `ai_drama_web/operations/backup_restore.py`
- Create: `tools/backup_m6_store.py`
- Create: `tools/restore_m6_store.py`
- Create: `tests/operations/test_m6_backup_restore.py`
- Create: `docs/operations/m6-backup-restore.md`

**Interfaces:**
- `M6BackupService.create(destination: Path) -> BackupManifest` checkpoints SQLite, copies DB/objects/credential files/journal metadata, and hashes every member.
- `M6RestoreService.restore(manifest: Path, destination: Path) -> RestoreReport` restores only into an empty destination and validates semantic equivalence.

- [ ] **Step 1: Write failing backup/restore tests.** Seed project, supplier/version/config/credential, models/bindings, snapshots, active/completed jobs, results, and orphan inventory.
- [ ] **Step 2: Run focused RED.** Run `python3 -m pytest -q tests/operations/test_m6_backup_restore.py`; expect missing service/CLI behavior.
- [ ] **Step 3: Implement a consistent checkpoint and manifest.** Use SQLite backup API under a read transaction/checkpoint, fsync copied files, record relative paths/modes/sizes/SHA-256, and never record secret contents.
- [ ] **Step 4: Implement guarded restore.** Reject non-empty targets, path traversal, manifest mismatch, unexpected files, incorrect credential mode, and corrupt DB/object hashes.
- [ ] **Step 5: Verify restored app semantics.** Start the app on the restored root and compare project/model/binding/snapshot/job/result identities; verify fake polling can resume and secret APIs remain write-only.
- [ ] **Step 6: Document exact backup, verify, restore, startup, and failure commands.** State that production backup/restore remains an operator action and the automated drill uses temporary roots only.
- [ ] **Step 7: Run GREEN and repeat restore for determinism.** Verify original and restored semantic summaries match without plaintext.
- [ ] **Step 8: Commit.** Commit `feat: add m6 backup restore drill`.

### Task 4: Full Fake Provider And Browser Acceptance

**Files:**
- Create: `tests/acceptance/test_m6e_fake_provider_workflow.py`
- Create: `web/tests/m6e-migration-acceptance.spec.ts`
- Modify: `web/playwright.config.ts` only for isolated M6E fake server metadata/ports

**Interfaces:**
- Python acceptance uses the existing supplier compiler/gateway/coordinator/poller and fake deterministic PNG/MP4 fixtures.
- Browser acceptance routes all API traffic to loopback and treats every non-loopback request or unexpected 4xx/5xx as failure.

- [ ] **Step 1: Write failing Python E2E.** Cover project, fake credential, V1 adapter, text/image/video models and bindings, text output, image job/asset, video submit/poll/fetch/result, submit-once counter, restart, default/current-model reruns, V2 save, old queued V1 snapshot, and new V2 work.
- [ ] **Step 2: Run focused RED.** Confirm failures expose missing acceptance fixture or real integration defect, not a mocked assertion.
- [ ] **Step 3: Implement only missing approved plumbing.** Reuse M6C/M6D contracts; do not add test-only production routes or new Provider parameters.
- [ ] **Step 4: Write browser acceptance.** Cover supplier management, bindings, fake text/image/video, queued retention, both reruns, result page, restart-visible state, route refresh, keyboard/dialog focus, 1440/1180/768, DOM/storage/network secret scan, public management rejection, clean console, and no unexpected HTTP failures.
- [ ] **Step 5: Run Python and Playwright GREEN.** Use temporary M6 flag-on fake server only; keep the user environment flag off.
- [ ] **Step 6: Run M3, M4, M6C, and M6D regressions.** Confirm no real smoke script is invoked.
- [ ] **Step 7: Commit.** Commit `test: add m6e fake provider acceptance`.

### Task 5: Feature Flag Rollback And Release Operations

**Files:**
- Create: `tests/acceptance/test_m6e_rollout_rollback.py`
- Create: `docs/operations/m6-rollout-rollback.md`

**Interfaces:**
- `semantic_store_summary(data_root) -> dict` compares legacy and M6 evidence before/after off/on/off restarts.

- [ ] **Step 1: Write failing off/on/off drill tests.** Flag off uses legacy paths with M6 data readable and no supplier invocation; temporary fake flag on routes new work through snapshots and resumes legacy active jobs; flag off restores legacy routing without deleting M6 rows.
- [ ] **Step 2: Run RED and identify missing assertions/plumbing.** No user environment variable is modified.
- [ ] **Step 3: Implement minimal approved flag behavior if required.** Prefer test setup and existing settings; do not introduce a production cutover control in the UI.
- [ ] **Step 4: Write rollout/rollback runbook.** Include backup gate, dry-run inventory, migration preflight, enable, observation, abort thresholds, rollback, restore, and post-rollback validation.
- [ ] **Step 5: Run the drill twice.** Assert history hashes and row identities remain stable and the production flag evidence remains false.
- [ ] **Step 6: Commit.** Commit `docs: add m6 rollout rollback drill`.

### Task 6: Final M6 Semantic Verifier

**Files:**
- Create: `tools/verify_m6_supplier_model_management.py`
- Create: `tools/verify_supplier_model_configuration.py` as a compatibility entry point required by the earlier governance contract
- Create: `tests/tools/test_verify_m6_supplier_model_management.py`

**Interfaces:**
- Emits JSON or Markdown for `M6E-001` through `M6E-018` with `PASS`/`FAIL`, evidence summary, command category, and zero request counters.
- Success token: `M6_SUPPLIER_MODEL_MANAGEMENT_PASS`.

- [ ] **Step 1: Write failing subprocess tests.** Require all 18 IDs, deterministic ordering, JSON/Markdown schema, nonzero exit on forced failure, no fixed pytest-count coupling, secret redaction, real endpoint denial, production flag false, and compatibility entry point parity.
- [ ] **Step 2: Run focused RED.** Expect missing verifier.
- [ ] **Step 3: Implement semantic criterion runners.** Compose focused temporary-root tests/verifiers; do not infer PASS from source strings alone.
- [ ] **Step 4: Map M6E criteria.** Fresh/legacy/replay, crash recovery, legacy backfill, inventory/GC, backup/restore, fake E2E, submit-once, reruns, hot reload, rollback, Playwright, secret hygiene, zero real requests, M1-M5 regression, and release readiness must have executable evidence.
- [ ] **Step 5: Run verifier twice and compare normalized reports.** Volatile durations/paths stay outside deterministic report fields.
- [ ] **Step 6: Commit.** Commit `feat: add final m6 acceptance verifier`.

### Task 7: Final Regression, Evidence, Reviews, And Handoff

**Files:**
- Create: `docs/superpowers/reports/2026-07-14-m6e-migration-acceptance-verification.md`
- Modify: `docs/operations/m6-backup-restore.md`
- Modify: `docs/operations/m6-rollout-rollback.md`

- [ ] **Step 1: Run the complete verification contract.** Run full pytest, Vitest, build, full Playwright, Worker tests, M3/M4/M6B/M6C/M6D/M6E verifiers, migration verifier, storyboard verifier, migration/crash/GC/backup/rollback matrices, and `git diff --check`.
- [ ] **Step 2: Run security/release scans.** Classify provider endpoint, Authorization/Bearer/api_key/token/signature/expires hits; verify no secret, signed URL, runtime DB/data, private generated media, or default real network path is tracked.
- [ ] **Step 3: Confirm deterministic release state.** Working tree is clean after default verification; default M6 flag false; zero real request counters; known warnings recorded.
- [ ] **Step 4: Write the release report.** Record base/head, matrices, inventory/GC, backup/restore, fake E2E IDs, browser evidence, M1-M5 regression, rollback point, flag state, request counters, commands/results, warnings, and sanitized evidence.
- [ ] **Step 5: Dispatch two independent read-only reviews.** One specification/acceptance reviewer and one architecture/technical/security/release reviewer inspect the exact candidate commit.
- [ ] **Step 6: Resolve every blocker/high TDD-first and rerun affected plus complete verification.** Repeat reviews until both PASS.
- [ ] **Step 7: Record reviewer roles, reviewed SHA, findings, corrections, and re-review status in the report.** Commit the reviewed report-only descendant.
- [ ] **Step 8: Push and hand off.** Push `feat/m6e-migration-acceptance`; create/update PR when authenticated or provide compare URL; emit the exact user-specified M6E handoff only.
