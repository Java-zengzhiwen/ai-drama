# Current Frontend Audit

Date: 2026-07-18

## Starting point

- Branch: `feat/ui-baseline-production-visualization`
- Base commit: `3ae6e573824abec3921b7581cd1d7e2554547841`
- Baseline unit result: 93 passed, 4 Playwright wrappers skipped by Vitest.
- Baseline production build: passed.
- Existing production routes and APIs already covered M1–M3, adjacent M4 rehearsal visibility, and M6D supplier/model management.

## Audit findings and disposition

| Area | Existing production evidence | Baseline gap | Implemented disposition |
| --- | --- | --- | --- |
| Application shell | `/projects`, `/suppliers`, compact header | no active-location semantics; inconsistent canvas hierarchy | one compact shell, `aria-current`, shared tokens and focus treatment |
| Project/chapter entry | real project/chapter routes | MVP form/table presentation | workbench headings, denser tables/forms, stable chapter identity |
| Workflow rail | real status API and blocked tabs | status tags did not read as ordered production stages | seven-step rail with one active stage, completed/blocked state and machine-readable reason |
| Source/script | real revision, generation and approval APIs | weak command hierarchy | compact source/script workbenches and revision controls |
| Storyboard | canonical table, shot editor, QC, approval | table and editor lacked strong separation | dense command table, selected row, sticky inspector and revision strip |
| Profiles/assets | profile, upload, image generation, binding and review APIs | creation dominated; detail overlay was not visual-first | secondary creation area plus 4:3 preview drawer and version/adoption strip |
| Requirements/prompts | requirement analysis, prompt revisions, validation/readiness | inconsistent density and correction hierarchy | common table/inspector styling; positive/negative prompt separation |
| Generation | durable jobs, refresh, batch submit and request preview | semantics were correct but visually weak | dense job table, selected-row state and 16:9 request inspector |
| Results/rerun | result versions, adoption, review and rerun | M4 evidence preceded the M3 task; drawer was not responsive | M3 result task first, 16:9 preview, desktop drawer and compact inline rerun region |
| M6D | approved supplier workbench | token differences from chapter screens | typography, borders, spacing, focus and responsive alignment only |

## Issues found during implementation QA

1. Multiple workflow stages appeared active because processing state and active navigation were conflated. Fixed by separating `data-tone` from `data-active`.
2. A storyboard-approved chapter still displayed a generic downstream lock notice. Fixed by deriving the notice from the actual Agnes gate.
3. Asset drawers rendered inside a deeply scrolled asset container, so the title and main preview could open above the viewport. Fixed by restoring the Drawer portal boundary.
4. Rerun remained modal at 1180px even though the approved responsive direction calls for a stacked region. Fixed with a non-modal inline region at `max-width: 1180px`.
5. Full signed/provider source locations were visually overexposed in the results table. Fixed by showing a compact host/file provenance label without query data.

No open P0, P1, or P2 defect remains in the implemented screen scope.
