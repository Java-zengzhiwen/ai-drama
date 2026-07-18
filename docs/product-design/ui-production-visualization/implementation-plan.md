# UI Baseline Production Visualization — Implementation Plan

Date: 2026-07-18
Branch: `feat/ui-baseline-production-visualization`
Scope: production React frontend and verification evidence only

## Objective

Apply the frozen M1–M3 Product Design baseline to the existing production web application without changing backend contracts, generation semantics, supplier execution, persistence, or milestone scope. Preserve M6D as an adjacent global destination and visually align it with the same shell.

## Guardrails

- No backend, database, migration, provider adapter, poller, credential, or API contract changes.
- No real provider requests. Existing local/fake-provider tests remain the only executable provider evidence.
- No new continuity-review, post-production, timeline, publishing, or provider-comparison product surfaces.
- No commit or push in this sprint.
- Existing Product Design screenshots and locked decisions are visual truth. The current MVP UI is implementation evidence, not a design source.
- Test and QA fixtures are allowed only in explicit test/development execution and must not change production API behavior.

## Implementation sequence

### 1. Shared application shell

Files:

- `web/src/app/App.tsx`
- `web/src/app/app.css`
- `web/src/app/App.test.tsx`

Work:

- Establish a compact top application bar with active global navigation.
- Keep `/projects` and `/suppliers` as the only approved global destinations.
- Add a consistent full-width production canvas and responsive behavior.
- Preserve all routes and route semantics.

Tests first:

- active navigation exposes `aria-current=page`;
- chapter routes retain project/chapter workflow context;
- unknown routes still redirect to `/projects`.

### 2. Project and chapter entry

Files:

- `web/src/features/projects/ProjectListPage.tsx`
- `web/src/features/projects/ProjectDashboardPage.tsx`
- `web/src/features/chapter/ChapterWorkspace.tsx`
- `web/src/features/chapter/SourceTab.tsx`
- corresponding unit tests

Work:

- Convert project entry screens to the same workbench vocabulary.
- Build the chapter shell from a workflow step rail, compact chapter identity header, and dense tabs.
- Keep gate reasons visible beside blocked stages and preserve all current API calls.

Tests first:

- workflow stages have stable accessible names and gate state;
- locked tabs remain disabled and expose their reason;
- current stage can be selected without changing backend state.

### 3. M1 production surfaces

Files:

- `web/src/features/script/ScriptTab.tsx`
- `web/src/features/storyboard/StoryboardTab.tsx`
- `web/src/features/storyboard/ShotEditor.tsx`
- corresponding unit/E2E tests

Work:

- Use dense command bars and revision controls.
- Preserve the canonical storyboard table as the primary surface.
- Keep selected-shot editing and QC in a persistent right inspector.
- Retain approval, validation, dirty-state, and retry semantics.

Tests first:

- selected row and inspector relationship;
- explicit approval and gate transitions;
- invalid JSON/dirty state continue blocking unsafe actions.

### 4. M2 production surfaces

Files:

- `web/src/features/assets/ProfilesAssetsTab.tsx`
- `web/src/features/assets/AssetGrid.tsx`
- `web/src/features/prompts/AssetRequirementPanel.tsx`
- `web/src/features/prompts/ShotPromptTab.tsx`
- `web/src/features/prompts/ShotPromptEditor.tsx`
- corresponding unit/E2E tests

Work:

- Keep production profile and creation controls compact and secondary.
- Make the selected asset detail a visual-first 4:3 review surface with visible version history and decision inspector.
- Preserve asset grid, metadata, binding, usable/rejected states, and exact IDs.
- Keep Shot Prompt as dense rows plus inspector, with positive and negative prompts visually separated.
- Place blocked reasons and minimum correction actions adjacent to the affected requirement or prompt.

Tests first:

- asset detail opens from a real asset card and exposes large preview/version history;
- current adoption and rejected history remain visible;
- prompt readiness remains blocked by current API state.

### 5. M3 production surfaces

Files:

- `web/src/features/generation/AgnesGenerationTab.tsx`
- `web/src/features/generation/GenerationResultsTab.tsx`
- `web/src/features/generation/RehearsalVisibilityPanel.tsx`
- corresponding unit tests and manual browser visualization evidence

Work:

- Preserve a dense generation table and a 16:9 request/result inspector.
- Keep ready and blocked shots visible; only ready shots are selectable/submittable.
- Keep polling, rate-limit, recovery, and failure messages distinct.
- Keep result history and current adoption visible.
- Keep rerun explicit and source-context preserving. Desktop uses a 360px dialog-style drawer; narrower viewports use a full-width stacked region where supported by the existing component boundary.
- De-emphasize the adjacent M4 rehearsal evidence so it does not replace the M3 result task.

Tests first:

- table row selection, preview, and submit eligibility;
- no autoplay;
- rerun source context and allowed overrides;
- responsive drawer/table behavior.

### 6. M6D visual alignment

Files:

- `web/src/app/app.css`
- existing supplier pages only if markup hooks are required
- existing M6D tests

Work:

- Preserve the approved three-region supplier workbench.
- Align typography, borders, spacing, table density, focus states, and responsive breakpoints with the chapter shell.
- Do not change supplier/model/secret/code behavior.

### 7. Verification and visual evidence

Files:

- existing Playwright M1, M2, M6D and M6E workflows
- `docs/product-design/ui-production-visualization/*.md`
- `docs/product-design/ui-production-visualization/assets/*`

Run:

1. TypeScript build/typecheck.
2. Vitest unit/integration suite.
3. Playwright M1, M2, M6D, M6E regression suite plus visualization workflow.
4. Production build.
5. Local application launch with production APIs and fake/local-only evidence.
6. Browser console/network inspection.
7. 1440×1024, 1180×800, and 768×1024 screenshots.
8. Keyboard/focus/ARIA/contrast/overflow review.
9. Combined reference-versus-production comparison for M1, M2, M3, and M6D.
10. Fix every P0/P1/P2 finding, rerun affected verification, and update the final fidelity report.

## Rollback

All changes are frontend-only and additive to documentation/tests. Rollback is the deletion/reversion of the files changed on this uncommitted branch. Existing backend state and API contracts are unaffected.

## Completion gate

- All existing functional tests and production build pass.
- No real provider request is made.
- No backend or contract file changes exist.
- The three required viewports have usable, non-overlapping production layouts.
- M1/M2/M3 source comparisons have no open P0/P1/P2 findings.
- The final handoff lists every changed production file and every generated evidence artifact.
