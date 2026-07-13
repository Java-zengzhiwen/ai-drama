# M6D Management UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved local-only Supplier Operations Workbench for supplier, credential, adapter code, stable model catalog, and project model-binding management without changing M6C execution semantics or making real Provider requests.

**Architecture:** A small additive management projection exposes only non-secret manifest/config/catalog metadata already stored by M6A-C. Typed React Query feature modules preserve response ETags, keep credential writes outside query caches, and render the approved three-region workbench with a lazily loaded TypeScript editor. Project bindings use one complete binding-set PUT and backend resolution previews; all management mutations fail closed on stale revisions and non-loopback access.

**Tech Stack:** FastAPI/Pydantic, React 18, TypeScript, Vite, TanStack Query, Ant Design, Axios, Vitest/Testing Library, Playwright, Python semantic verifier.

## Global Constraints

- Base is `feat/m6c-adapter-cutover` at `ef474f6a11badbf88833564b4909a8c8cf1b2505`; preserve M1-M6C behavior and history.
- Visual target is `docs/product-design/m6d/assets/selected-direction-supplier-operations-workbench.png` with SHA-256 `364553c249be0b772a95cfaae2d6959a9ae3e086e08bd28609c657ef2ed1dabc`.
- Preserve the Toonflow-like two-level product model `supplier -> models`; do not add marketplace, duplication, multiple accounts, or remote multi-user management.
- Management APIs remain application-layer loopback-only; never recommend weakening `LOCAL_MANAGEMENT_ONLY`.
- Credential plaintext is write-only: no GET, query cache, browser storage, URL, log, exception, trace, screenshot, or report may contain it.
- Every supplier/config/code/model/binding mutation carries the exact current ETag/precondition; `409` never auto-overwrites.
- M6 execution remains disabled by default and the UI exposes no real cutover or online-test control.
- Default tests deny unexpected external network; `REAL_TEXT_REQUEST_COUNT=0`, `REAL_IMAGE_REQUEST_COUNT=0`, and `REAL_VIDEO_REQUEST_COUNT=0` throughout.
- No production data migration is added. Any backend change is an additive read projection or safe error/ETag metadata needed by M6D, never an execution/poller/rerun change.
- Apply TDD for every behavior: focused red, expected failure, minimum green, focused regression, then commit.
- Final acceptance requires independent read-only specification-compliance and frontend/technical/security agents to return PASS after all blocker/high findings are fixed.

---

### Task 1: Management Read Projection And Stable Error Contract

**Files:**
- Modify: `ai_drama_web/routers/suppliers.py`
- Modify: `ai_drama_web/routers/models.py`
- Test: `tests/web/test_supplier_api.py`
- Test: `tests/web/test_model_api.py`

**Interfaces:**
- Produces `SupplierManagementRead` fields from immutable supplier version/config data: `author`, `version`, `capabilities`, `inputs`, `input_values`, `config_values`, `model_count`, and revision metadata.
- Produces model `binding_count` while preserving `supplier_model_id`, `model_revision_id`, and existing ETag headers.
- Never returns credential plaintext, authorization headers, code source in supplier list/detail, signed queries, or external response bodies.

- [ ] **Step 1: Write focused failing API tests.** Assert built-in and custom detail/list responses expose only the non-secret management projection, config values can be round-tripped after conditional save, malformed/missing immutable objects fail safely, model rows expose binding count, and a known credential value is absent from every GET body.
- [ ] **Step 2: Run red tests.** Run `python3 -m pytest -q tests/web/test_supplier_api.py tests/web/test_model_api.py`; expect failures for missing projection fields and binding count.
- [ ] **Step 3: Implement the minimum read projection.** Read current manifest/config objects by their immutable IDs, parse bounded JSON objects, derive capabilities/model count, redact query strings from URL summaries, and fall back to empty metadata for a custom empty template. Do not change supplier version/config pointers or M6C adapters.
- [ ] **Step 4: Run focused green and loopback regressions.** Run `python3 -m pytest -q tests/web/test_supplier_api.py tests/web/test_model_api.py tests/web/test_local_management_guard.py`; expect PASS.
- [ ] **Step 5: Commit.** Commit only the read projection and tests as `feat: expose supplier management metadata`.

### Task 2: Typed API Client, ETags, And Management Shell

**Files:**
- Modify: `web/src/api/client.ts`
- Modify: `web/src/app/App.tsx`
- Create: `web/src/app/app.css`
- Create: `web/src/features/suppliers/api.ts`
- Create: `web/src/features/suppliers/managementErrors.ts`
- Create: `web/src/features/suppliers/SupplierListPage.tsx`
- Test: `web/src/features/suppliers/api.test.ts`
- Test: `web/src/features/suppliers/SupplierListPage.test.tsx`
- Modify: `web/src/app/App.test.tsx`

**Interfaces:**
- `readWithEtag<T>(request): Promise<{ data: T; etag: string }>` preserves response ETags.
- `toManagementError(error): { code: string; message: string; status?: number }` supports FastAPI `detail.error_code` and top-level `error_code`.
- Supplier reads use React Query; secret mutations accept plaintext only as a direct call argument and return masked status, never query data containing plaintext.

- [ ] **Step 1: Write red client/route/render tests.** Cover relative `/api`, ETag capture, `If-Match`/`If-None-Match`, nested/top-level error parsing, supplier list metadata, enabled/disabled states, empty/loading/error states, local-only copy, create custom empty supplier, and absence of duplicate/marketplace controls.
- [ ] **Step 2: Run red tests.** Run `npm --prefix web run test -- --run web/src/features/suppliers/api.test.ts web/src/features/suppliers/SupplierListPage.test.tsx web/src/app/App.test.tsx`; expect missing module/route failures.
- [ ] **Step 3: Implement typed contracts and approved shell.** Add `/suppliers` navigation and route, compact neutral tokens (`#f6f8fb`, `#d9dee8`, `#2563eb`), supplier navigation rail, central workspace, status chips, and no decorative dashboard/cards/gradients.
- [ ] **Step 4: Implement safe mutations.** Send exact conditional headers, use generated local idempotency keys for create, avoid request/response logging, and invalidate only safe supplier query keys.
- [ ] **Step 5: Run focused green and existing route regression.** Expect all listed tests to pass and existing `/projects`, chapter, and settings routes to remain unchanged.
- [ ] **Step 6: Commit.** Commit as `feat: add supplier management shell`.

### Task 3: Config, Credential, And Lazy TypeScript Editor

**Files:**
- Create: `web/src/features/suppliers/SupplierDetailPage.tsx`
- Create: `web/src/features/suppliers/SupplierConfigForm.tsx`
- Create: `web/src/features/suppliers/SupplierSecretForm.tsx`
- Create: `web/src/features/suppliers/SupplierCodeEditor.tsx`
- Create: `web/src/features/suppliers/SupplierCodeEditor.lazy.tsx`
- Test: `web/src/features/suppliers/SupplierDetailPage.test.tsx`
- Test: `web/src/features/suppliers/SupplierCodeEditor.test.tsx`

**Interfaces:**
- Config fields come from non-secret manifest `inputs`; compatibility fields already present in `config_values` remain editable without inventing Provider parameters.
- Credential form stores plaintext only in component state, the eye control reveals only the unsaved input, and every mutation path clears it in `finally`.
- Code saves use supplier ETag and return immutable `supplier_version_id`; diagnostics expose only stable code/message/line/column.

- [ ] **Step 1: Write red tests.** Cover schema-driven non-secret fields, HTTPS Base URL validation, config conditional save/reload, masked credential status, eye behavior, input clearing after success/error, replace/delete confirmation, code source fetch, line numbers, invalid TypeScript diagnostics, successful immutable version, restore built-in, stale conflict reload, and no online-test button.
- [ ] **Step 2: Run red tests.** Expect missing detail/forms/editor failures.
- [ ] **Step 3: Implement overview/config/credential sections.** Keep saved credential unreadable; show only `已配置 ....ABCD`; describe destructive impact in an accessible confirmation dialog; never persist form state outside the component.
- [ ] **Step 4: Implement lazy editor.** Load the code editor only when `适配代码` is selected, render a monospace TypeScript editing surface with line gutter and keyboard labels, call only local validation/save, and render safe diagnostics.
- [ ] **Step 5: Run focused green plus DOM/storage scan tests.** Assert the submitted sentinel is absent from rendered DOM, query cache serialization, `localStorage`, and `sessionStorage` after mutation.
- [ ] **Step 6: Commit.** Commit as `feat: manage supplier configuration and code`.

### Task 4: Stable Model Catalog Workbench

**Files:**
- Create: `web/src/features/suppliers/SupplierModelsPanel.tsx`
- Create: `web/src/features/suppliers/ModelInspector.tsx`
- Test: `web/src/features/suppliers/SupplierModelsPanel.test.tsx`

**Interfaces:**
- All row keys, routes, mutations, and selections use `supplier_model_id`; display/provider names are labels only.
- PATCH sends both model and catalog ETags; create sends `If-None-Match: *`, catalog ETag, and a fresh idempotency key.
- Semantic edit sends `acknowledged_binding_count`; enable/disable is a separate mutation.

- [ ] **Step 1: Write red tests.** Cover required columns, capability/source/status filters, inspector stable identity/revision/definition, add overlay, rename with stable ID/new revision, disable/enable, base delete disabled, unreferenced overlay delete, referenced delete rejection, affected-binding acknowledgement, and stale combined ETag conflict.
- [ ] **Step 2: Run red tests.** Expect missing panel/inspector.
- [ ] **Step 3: Implement table and inspector.** Match the approved dense workbench, put stable ID in the inspector rather than the main label, preserve source distinctions, and expose no duplicate/batch/marketplace actions.
- [ ] **Step 4: Implement accessible dialogs and conditional writes.** Keep focus contained/restored, summarize validation errors, and refresh model/catalog ETags only after success or explicit reload.
- [ ] **Step 5: Run focused green and supplier detail regression.** Expect PASS.
- [ ] **Step 6: Commit.** Commit as `feat: manage stable supplier models`.

### Task 5: Project Defaults, Overrides, And Resolution Preview

**Files:**
- Modify: `web/src/features/projects/api.ts`
- Modify: `web/src/features/projects/ProjectDashboardPage.tsx`
- Create: `web/src/features/projects/ProjectModelBindingsPage.tsx`
- Create: `web/src/features/projects/ProjectModelBindings.test.tsx`
- Modify: `web/src/app/App.tsx`

**Interfaces:**
- Fixed operation keys and capabilities mirror `ai_drama_web/suppliers/operations.py` exactly.
- The editor keeps one local complete `{ defaults, operation_overrides }` set and sends one conditional PUT with the binding-set ETag.
- Selectable options require enabled supplier, enabled model, and matching capability; no automatic fallback is introduced.

- [ ] **Step 1: Write red tests.** Cover text/image/video defaults, capability filtering, disabled supplier/model exclusion, inherit/explicit labels, fixed operation overrides, single complete PUT, resolution preview, `MODEL_BINDING_MISSING`, capability mismatch, disabled errors, and stale conflict refusing overwrite.
- [ ] **Step 2: Run red tests.** Expect missing route/page/API functions.
- [ ] **Step 3: Implement `/projects/:projectId/model-bindings`.** Reuse the approved workbench visual system inside the project workspace, show future-task warning, filter options deterministically, and keep inherited values explicit in the UI but omitted from `operation_overrides`.
- [ ] **Step 4: Implement preview/error states.** Query backend resolution for saved operation rows, render stable Chinese messages, and never auto-select a fallback.
- [ ] **Step 5: Run focused green plus existing project page tests.** Expect no route or workflow regressions.
- [ ] **Step 6: Commit.** Commit as `feat: configure project model bindings`.

### Task 6: Browser Acceptance, Accessibility, And Visual QA

**Files:**
- Create: `web/tests/m6d-management-ui.spec.ts`
- Modify: `web/playwright.config.ts` only if required for deterministic local fixtures
- Create: `docs/product-design/m6d/design-qa.md`

**Interfaces:**
- Browser requests are proxied only to the loopback FastAPI test server; request recording rejects every non-loopback HTTP(S) URL.
- Test data uses fake/custom suppliers and deterministic local fixtures; no real Provider endpoint or credential is contacted.

- [ ] **Step 1: Write Playwright acceptance before UI fixes.** Cover the 16 contract scenarios: list/detail, config, secret clearing/no readback, valid/invalid code, restore, overlay lifecycle, bound edit acknowledgement, defaults/overrides, stale ETag, local-only error, fake new-version execution evidence, frozen queued snapshot evidence, zero external network, clean console, and direct route refresh.
- [ ] **Step 2: Run the M6D spec red/green.** Run `npm --prefix web run test:e2e -- m6d-management-ui.spec.ts`; fix only tested M6D defects and preserve external-network denial.
- [ ] **Step 3: Verify accessibility.** Exercise labels, keyboard traversal, dialog focus/escape/return, error summaries, loading/empty/disabled states, and destructive confirmations at desktop and responsive widths.
- [ ] **Step 4: Run visual QA against the exact approved image.** Capture matching desktop state plus 1180px and 768px responsive states; compare hierarchy, spacing, tokens, table density, inspector, and overflow. Record P0-P3 findings and fix all P0/P1/P2 until `final result: passed`.
- [ ] **Step 5: Verify lazy loading and bundle delta.** Compare M6C and M6D build outputs, prove the editor is a separate lazy chunk, and record size/warning evidence without hiding the existing large-chunk warning.
- [ ] **Step 6: Commit.** Commit as `test: cover m6d management ui`.

### Task 7: Semantic Verifier, Full Regression, Dual Review, And Handoff

**Files:**
- Create: `tools/verify_m6d_management_ui.py`
- Create: `tests/test_verify_m6d_management_ui.py`
- Create: `docs/superpowers/reports/2026-07-13-m6d-management-ui-verification.md`

**Interfaces:**
- Verifier emits JSON and Markdown for `M6D-001` through `M6D-015` without fixed test-count coupling.
- Report records exact commands, current commit candidate, zero-request counters, bundle/visual/accessibility evidence, rollback, and both review verdicts.

- [ ] **Step 1: Write red verifier tests.** Require all 15 semantic IDs, sanitized outputs, no fixed pass count, and zero real text/image/video counters.
- [ ] **Step 2: Implement the verifier.** Use local temporary data and focused subprocess checks; prohibit real endpoints and historical smoke scripts.
- [ ] **Step 3: Run the complete verification contract.** Run full Python, Web Vitest/build/Playwright, Worker tests, M3/M4/M6B/M6C/M6D verifiers, migration verifier, feature-flag rollback regression, route refresh, loopback/non-loopback tests, secret/provider scan, bundle comparison, and `git diff --check`.
- [ ] **Step 4: Dispatch two independent read-only agents.** One checks specification compliance; one checks frontend/technical/security/UX. Neither may edit files or make real Provider requests.
- [ ] **Step 5: Resolve every blocker/high with fresh red tests.** Re-run focused tests, the complete verification contract, and both reviews until both return PASS.
- [ ] **Step 6: Finalize report and commit.** Record evidence in the report, confirm a clean worktree and no tracked secrets/runtime data, and commit as `test: verify m6d management ui`.
- [ ] **Step 7: Push and hand off.** Push `feat/m6d-management-ui`, create/update a PR against `feat/m6c-adapter-cutover` when authentication permits, and emit the exact M6D Review Handoff contract.
