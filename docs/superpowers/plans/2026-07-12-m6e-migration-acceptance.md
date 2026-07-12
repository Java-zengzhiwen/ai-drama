# M6E Migration And Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove fresh/legacy migration recovery, complete SUP-001..SUP-028 acceptance, deterministic reporting, and reversible final cutover readiness.

**Architecture:** A portable verifier constructs fresh and representative legacy stores, exercises fake text/image/video supplier flows and crash recovery, then emits deterministic JSON/Markdown evidence. Final cutover stays feature-flagged and does not remove legacy fields.

**Tech Stack:** Python, SQLite, pytest, Vitest, Playwright, existing M1-M5 verifiers.

## Global Constraints

- M6A-D are approved dependencies; M6E adds no new supplier capability.
- No real provider request, production rollout, or irreversible legacy deletion.
- All SUP-001..SUP-028 criteria require explicit PASS/FAIL/SKIPPED evidence; required criteria may not be skipped.
- Before M6 completion handoff, at least two read-only review agents must independently return PASS: specification/acceptance coverage, and technical/security with emphasis on migration recovery, verifier determinism, full regression, rollback, and evidence redaction. The main agent resolves and re-verifies all blockers.

---

### Task 1: Fresh And Legacy Migration Matrix

**Files:**
- Create: `tests/migration/test_m6_supplier_migration.py`
- Create: `tests/fixtures/m6_legacy_store.py`
- Modify: `migration/migration-manifest.json`
- Modify: `migration/tools/verify_migration.py`

**Interfaces:**
- Produces repeatable fixtures for fresh, M5 terminal-history, active Agnes, pending credential finalize/delete, and corrupt credential stores.

- [ ] Write red tests for each fixture, two migration passes, row/content hashes, active legacy snapshots, terminal readability, and no irreversible deletion.
- [ ] Run focused tests; expect missing M6 migration manifest/support.
- [ ] Extend migration verifier/manifest and recovery hooks without changing product features.
- [ ] Re-run focused tests and migration verifier twice.
- [ ] Commit `test: add m6 migration recovery matrix`.

### Task 2: Portable M6 Acceptance Verifier

**Files:**
- Create: `tools/verify_supplier_model_configuration.py`
- Create: `tests/tools/test_verify_supplier_model_configuration.py`

**Interfaces:**
- Produces `supplier-model-configuration-report.json` and `.md` with criterion ID, status, evidence, command, and redacted diagnostics; success token `M6_SUPPLIER_MODEL_CONFIGURATION_PASS`.

- [ ] Write red subprocess tests for exit codes, deterministic ordering, required fields, secret redaction, zero-network guard, and a forced failing criterion.
- [ ] Run focused tests; expect missing verifier.
- [ ] Implement portable temporary-root setup and criterion runners for SUP-001..SUP-028 using fake suppliers only.
- [ ] Run focused tests and inspect both reports for stable output and no sensitive fields.
- [ ] Commit `feat: add m6 supplier acceptance verifier`.

### Task 3: Full Fake Supplier E2E

**Files:**
- Create: `tests/acceptance/test_m6_supplier_workflow.py`
- Modify: `web/e2e/m6-supplier-management.spec.ts`

- [ ] Write end-to-end acceptance covering custom adapter save, next-task hot reload, text/image/video jobs, restart poll, result persistence, current selection, rerun current credential, and project override.
- [ ] Run focused Python/browser tests; fix only integration defects within approved M6 interfaces.
- [ ] Repeat with fresh and legacy stores and assert no external sockets.
- [ ] Run M3/M4 verifiers to prove generation/rehearsal compatibility.
- [ ] Commit `test: add m6 fake supplier end to end acceptance`.

### Task 4: Cutover And Rollback Drill

**Files:**
- Create: `tests/acceptance/test_m6_cutover_rollback.py`
- Create: `docs/operations/m6-supplier-cutover-runbook.md`

- [ ] Write red drill tests that enable M6 routing, create snapshot-bound work, disable routing, and verify legacy paths/history remain usable without discarding M6 evidence.
- [ ] Run the drill and confirm expected missing runbook/flag assertions.
- [ ] Document exact preflight, backup, enable, observe, rollback, and post-rollback commands; implement only missing flag plumbing already approved by M6C.
- [ ] Re-run drill twice for idempotency.
- [ ] Commit `docs: add m6 cutover rollback runbook`.

### Task 5: Final Regression And Security Audit

**Files:**
- Create: `docs/superpowers/reports/2026-07-12-m6-final-acceptance.md`

- [ ] Run full pytest, Vitest, build, Playwright, M1-M4 verifiers, migration verifier, and M6 verifier.
- [ ] Run static scans for secrets, signed URLs, direct provider calls, browser provider endpoints, forbidden worker APIs, placeholders, and untracked runtime data.
- [ ] Map every SUP criterion to exact automated evidence and classify any non-required operational item separately.
- [ ] Verify clean rollback state, working tree, diff check, and no real provider request counter/evidence.
- [ ] Commit `test: close m6 supplier acceptance` and push `feat/m6e-migration-acceptance`.

### Task 6: M6 Completion Review Gate

- [ ] Confirm M6A-E branches/commits are reviewed and merged in order.
- [ ] Confirm verifier token is `M6_SUPPLIER_MODEL_CONFIGURATION_PASS` and all required criteria PASS.
- [ ] Confirm no legacy field cleanup or real-provider execution is bundled.
- [ ] Dispatch the two mandatory read-only reviewers; record findings and resolve/retest/re-review every blocker until both return PASS.
- [ ] Produce Review Handoff with repository, branch, commit, report path, compare/PR URL, and exact verification summary.
- [ ] Stop for user approval; only after merge may governance record `M6_COMPLETE`.
