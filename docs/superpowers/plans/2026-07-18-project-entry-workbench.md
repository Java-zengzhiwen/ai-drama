# Project Entry Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `/projects` from the selected Product Design option 2 so a local producer can resume the most relevant project immediately while project creation remains a secondary drawer action.

**Architecture:** Keep the existing project and chapter APIs unchanged. The React page loads project metadata, then derives a lightweight production summary from each project's chapters and latest chapter status; the newest project becomes the focused “继续制作” surface and the remaining projects stay in one compact table.

**Tech Stack:** React 18, TypeScript, TanStack Query, Ant Design, React Router, Vitest, Testing Library, Vite.

## Global Constraints

- Preserve all existing backend contracts and M1–M6 behavior.
- Do not make any real provider request.
- Reuse the existing AI Drama shell, tokens, Ant Design components, and routes.
- The selected source visual is `/Users/zengzhiwen/.codex/generated_images/019f4c96-0023-7ab1-81e2-d65db2d8e845/exec-b49cebc3-5294-4e6d-9e04-4ca3bdf8090f.png` at `1440 x 1024`.
- Do not commit or push during this interactive local build.

---

### Task 1: Project entry behavior contract

**Files:**
- Modify: `web/src/features/projects/ProjectPages.test.tsx`

**Interfaces:**
- Consumes: existing `GET /projects`, `GET /projects/{project_id}/chapters`, and `GET /chapters/{chapter_id}/status` mocks.
- Produces: behavior expectations for the focused project, localized next action, search, and the create-project drawer.

- [x] **Step 1: Write the failing tests**

Add assertions that the newest project is shown in a `继续制作` region, its chapter status becomes a Chinese stage/action, search filters the remaining project rows, and the five project fields appear only after clicking `新建项目`.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `npm --prefix web run test -- --run src/features/projects/ProjectPages.test.tsx`

Expected: FAIL because the current page has an always-open form and no focused production summary.

### Task 2: Focused project summary and secondary creation flow

**Files:**
- Modify: `web/src/features/projects/ProjectListPage.tsx`
- Modify: `web/src/app/app.css`

**Interfaces:**
- Consumes: `ProjectRead`, `ChapterRead`, `ChapterStatus`, `listChapters(projectId)`, and `getChapterStatus(chapterId)`.
- Produces: a responsive page with `project-entry-header`, `project-focus`, `project-workflow`, `project-queue`, and an Ant Design `Drawer` for creation.

- [x] **Step 1: Implement the minimal summary resolver**

Sort projects by `updated_at`, load chapter/status summaries through TanStack Query, map provider-neutral status codes to Chinese stage/status/action copy, and keep navigation on existing project/chapter routes.

- [x] **Step 2: Implement the selected visual hierarchy**

Render the title/search/new-project controls, one focused `继续制作` section with a seven-stage Ant Design `Steps` rail, and one compact table for other projects. Move the existing five-field form unchanged into a right-side drawer.

- [x] **Step 3: Add responsive styles**

Match the source at 1440px, stack the focused metadata/workflow/action at 1180px, and preserve usable horizontal table scrolling at 768px.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `npm --prefix web run test -- --run src/features/projects/ProjectPages.test.tsx`

Expected: PASS.

### Task 3: Verification and design QA

**Files:**
- Create: `design-qa.md`
- Create: `docs/product-design/ui-production-visualization/assets/project-list-production-1440x1024.png`

**Interfaces:**
- Consumes: the selected source visual and the running `/projects` page.
- Produces: browser-verified evidence and a blocking Product Design QA result.

- [x] **Step 1: Run regression verification**

Run:

```bash
npm --prefix web run test -- --run
npm --prefix web run build
git diff --check
```

Expected: all tests and build pass; no whitespace errors.

- [x] **Step 2: Verify primary interactions**

At `/projects`, verify search, focused-project navigation target, drawer open/close, required-name submit gating, and console errors.

- [x] **Step 3: Capture and compare at 1440 x 1024**

Capture the production page at the source viewport, inspect the saved image, create one combined source-versus-production comparison, and fix every P0/P1/P2 difference.

- [x] **Step 4: Record the final gate**

Write `design-qa.md` with source path, implementation screenshot path, viewport, state, comparison history, required fidelity surfaces, tested interactions, console result, and exactly `final result: passed` or `final result: blocked`.
