# M6D Management UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver loopback-only supplier, code/config/secret, model catalog, and project binding interfaces backed exclusively by M6A-C APIs.

**Architecture:** Focused React Query feature modules consume typed API clients and preserve server ETags. Supplier code editing uses a lightweight text editor with compiler diagnostics; no browser code or credential reaches providers directly.

**Tech Stack:** React, TypeScript, Vite, TanStack Query, Ant Design, Vitest/Testing Library, Playwright.

## Global Constraints

- Backend capabilities are fixed by M6A-C; M6D adds no schema or provider capability.
- No marketplace, duplication, multi-account, remote management, or real model-test button.
- Default tests and browser flows deny real network; no real Provider request is authorized.
- All management errors render `LOCAL_MANAGEMENT_ONLY`; secrets are write-only and masked.
- Production UI implementation is blocked until Product Design presents exactly three visual directions and the user explicitly approves one recorded visual target.
- The approved visual target is `docs/superpowers/specs/2026-07-12-m6d-management-ui-visual-design.md`, backed by `docs/product-design/m6d/assets/selected-direction-supplier-operations-workbench.png`; implementation must preserve its locked hierarchy and tokens.
- Before stage handoff, at least two read-only review agents must independently return PASS: specification compliance, and technical/security/UX with emphasis on visual-target fidelity, secret masking, ETags, local-only behavior, accessibility, and browser network isolation. The main agent resolves and re-verifies all blockers.

---

### Task 0: Product Design Approval Checkpoint

**Files:**
- Create: `docs/superpowers/specs/2026-07-12-m6d-management-ui-visual-design.md`
- Create: disposable prototype or visual artifacts only under the Product Design workflow's approved non-production location

**Interfaces:**
- Consumes stable M6A-C API contracts and existing AI Drama screens.
- Produces a user-approved visual target covering supplier list, supplier config/secret/code, stable model management, project defaults/overrides, responsive behavior, error/conflict/loading/empty states, and accessibility expectations.

- [ ] Use Product Design context and ideation workflows to inspect the existing product and produce exactly three visual directions without modifying production UI files.
- [ ] Present all three directions to the user and wait for an explicit selection or revision request.
- [ ] Record the selected direction, rejected alternatives, interaction/state requirements, visual references, and approval evidence in the design artifact.
- [ ] Run document placeholder/secret/network scans, commit the approved visual design, and stop if explicit approval is absent.
- [ ] Reconcile Tasks 1-6 against the approved target; if component or test contracts change, revise this plan and obtain plan approval before implementation.

### Task 1: Typed Supplier API And Navigation

**Files:**
- Create: `web/src/features/suppliers/api.ts`
- Create: `web/src/features/suppliers/SupplierListPage.tsx`
- Modify: `web/src/app/App.tsx`
- Test: `web/src/features/suppliers/SupplierListPage.test.tsx`

**Interfaces:**
- Produces typed supplier reads/mutations carrying ETags and list/detail navigation.

- [ ] Write red render/API tests for built-in/custom suppliers, enabled state, empty/error/local-only states, and no secret fields.
- [ ] Run focused Vitest; expect missing route/components.
- [ ] Implement typed client, query keys, page, and loopback-error handling.
- [ ] Re-run focused tests and existing app navigation tests.
- [ ] Commit `feat: add supplier management navigation`.

### Task 2: Config, Secret, And TypeScript Editor

**Files:**
- Create: `web/src/features/suppliers/SupplierDetailPage.tsx`
- Create: `web/src/features/suppliers/SupplierCodeEditor.tsx`
- Create: `web/src/features/suppliers/SupplierConfigForm.tsx`
- Test: `web/src/features/suppliers/SupplierDetailPage.test.tsx`

**Interfaces:**
- Consumes M6A APIs; produces conditional saves with current ETag and line/column diagnostics.

- [ ] Write red tests for masked credential, replace/delete confirmation, config fields, code diagnostics, ETag conflict reload, restore built-in, and never rendering plaintext.
- [ ] Run focused tests; expect missing components.
- [ ] Implement minimal textarea-based TypeScript editor, diagnostics panel, schema-driven form, secret write-only field, and mutation conflict UX.
- [ ] Re-run tests and scan DOM snapshots for secret values.
- [ ] Commit `feat: add supplier configuration editor`.

### Task 3: Stable Model Catalog UI

**Files:**
- Create: `web/src/features/suppliers/SupplierModelsPanel.tsx`
- Test: `web/src/features/suppliers/SupplierModelsPanel.test.tsx`

**Interfaces:**
- Consumes model UUID/revision APIs; produces add/edit/disable flows and affected-binding acknowledgement.

- [ ] Write red tests for display/provider names, capability, source, revision, disable, referenced-delete rejection, ETag conflict, and identity preserved across rename.
- [ ] Run focused tests; expect missing panel.
- [ ] Implement table/forms using `supplier_model_id` in keys/routes; never use names as identity.
- [ ] Re-run focused tests.
- [ ] Commit `feat: manage stable supplier models`.

### Task 4: Project Defaults And Operation Overrides

**Files:**
- Create: `web/src/features/projects/ProjectModelBindings.tsx`
- Modify: `web/src/features/projects/ProjectDashboardPage.tsx`
- Modify: `web/src/features/projects/api.ts`
- Test: `web/src/features/projects/ProjectModelBindings.test.tsx`

**Interfaces:**
- Consumes binding-set ETag and resolver evidence; produces text/image/video defaults and optional operation overrides.

- [ ] Write red tests for inherited labels, explicit override, missing binding, disabled model, save conflict, and resolver preview.
- [ ] Run focused tests; expect missing UI/API.
- [ ] Implement binding editor with a single conditional PUT of the complete set.
- [ ] Re-run focused and existing project page tests.
- [ ] Commit `feat: configure project model bindings`.

### Task 5: Browser Acceptance And Accessibility

**Files:**
- Create: `web/e2e/m6-supplier-management.spec.ts`
- Modify: `web/playwright.config.ts` only if existing server wiring requires it
- Test: `web/e2e/m6-supplier-management.spec.ts`

- [ ] Add Playwright scenarios for custom supplier save, fake task hot reload, model binding, ETag conflict, restore, secret masking, keyboard labels, and non-loopback rejection fixture.
- [ ] Run the new spec against fake/loopback backend; assert network recorder has no external provider request.
- [ ] Fix only M6D UI/accessibility defects found by the spec.
- [ ] Run all Vitest, build, and E2E suites.
- [ ] Commit `test: cover m6 supplier management ui`.

### Task 6: M6D Verification

**Files:**
- Create: `docs/superpowers/reports/2026-07-12-m6d-management-ui-verification.md`

- [ ] Record UI/API surface coverage, accessibility results, zero-network evidence, and rollback by disabling M6 UI routes.
- [ ] Run M6A-C focused regression plus full baseline.
- [ ] Scan built assets, logs, fixtures, and git diff for secrets/provider endpoints.
- [ ] Confirm no schema/backend capability changed in this branch.
- [ ] Dispatch the two mandatory read-only reviewers; record findings and resolve/retest/re-review every blocker until both return PASS.
- [ ] Commit `test: verify m6d management ui` and push `feat/m6d-management-ui`.
