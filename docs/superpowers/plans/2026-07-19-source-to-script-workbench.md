# Source-to-Script Workbench Implementation Plan

> **Scope:** Implement the approved Product Design reference for the chapter source page without changing backend contracts or making real provider requests.

## Visual source of truth

- Reference: `/Users/zengzhiwen/.codex/generated_images/019f4c96-0023-7ab1-81e2-d65db2d8e845/exec-ffef0a4a-950b-4f5e-a0d3-f40491bd9772.png`
- Target viewport: `1440 × 1024`
- Product contract: left chapter navigation, central manuscript editor, colored right-side source-to-script inspector, and one primary save-and-generate action.

## Task 1: Lock interaction behavior with focused tests

**Files:**

- Modify: `web/src/features/script/ScriptTab.test.tsx`

1. Extend the local API harness for chapter navigation and project model resolution.
2. Add a failing test proving the source page exposes the three-column workbench and resolved text model.
3. Add a failing test proving `保存并生成剧本` saves a changed source revision before requesting script generation and then opens the script tab.
4. Keep a separate failing assertion proving `仅保存原文` never generates a script.
5. Run the focused Vitest file and confirm failures are caused by the missing UI and orchestration.

## Task 2: Implement the contract-shaped workbench

**Files:**

- Modify: `web/src/features/chapter/SourceTab.tsx`
- Modify: `web/src/features/chapter/ChapterWorkspace.tsx`

1. Load real project chapters for left navigation and the resolved `script_adaptation` model for the inspector.
2. Preserve plain-text source editing and source-revision persistence.
3. Add save-only and save-then-generate flows; generation reuses the existing backend resolver and never receives a browser-supplied secret or arbitrary provider configuration.
4. Open the existing Script tab after successful generation.
5. Replace source-page-wide lock alerts with the compact inspector notice while retaining lock reasons in the workflow rail and on locked tabs.
6. Keep non-contract controls read-only or derived rather than pretending unsupported adaptation parameters are sent to the backend.

## Task 3: Match the selected visual and verify

**Files:**

- Modify: `web/src/app/app.css`
- Modify: `design-qa.md`

1. Implement the approved hierarchy, spacing, colored inspector surfaces, manuscript typography, selected chapter state, and responsive layouts.
2. Run focused tests, affected frontend tests, and the production build.
3. Run the local app without enabling real-provider execution.
4. Compare the implementation against the reference at `1440 × 1024`, fix all P0/P1/P2 visual findings, and save the comparison evidence.
5. Record the result in project-root `design-qa.md` with exact final result `passed`.
