# M6D Product Design QA

Status: implementation QA complete

Approved reference: `assets/selected-direction-supplier-operations-workbench.png`

## Matching criteria

- The desktop supplier detail keeps the approved three-region workbench: supplier rail, central command surface, and inspector.
- The central model surface remains a dense table. Stable model identity is exposed in the inspector instead of replacing the human-readable name.
- Surfaces use the frozen white / `#f6f8fb` workspace, `#d9dee8` dividers, compact typography, small radii, and blue primary actions. No dashboard cards, gradients, illustrations, or new brand language were introduced.
- Code editing is a lazy-loaded secondary surface. The main application chunk does not contain the editor module.
- At 1180px the inspector stacks below the command surface. At 768px the supplier rail changes to the approved compact selector, while dense model and binding tables remain horizontally scrollable.

## Interaction QA

- Supplier tabs implement `tablist`, `tab`, `tabpanel`, `aria-controls`, roving `tabIndex`, Arrow Left/Right, Home, and End.
- The create-supplier dialog moves focus to the supplier-name input.
- Destructive credential and model actions require a modal confirmation; force credential deletion additionally requires an explicit impact acknowledgement when active jobs exist.
- Config, code, supplier, model, and binding conflicts fail closed and expose a reload action.
- Secret input is cleared after every mutation attempt and is never rendered from server state.

## Viewport and automation evidence

- Desktop Chrome: the M6D Playwright management flow validates the complete workbench, table, inspector, dialogs, keyboard tab navigation, and route refresh.
- 768x900 Chrome: `M6D uses the approved compact supplier selector at 768px` validates selector visibility and desktop rail suppression.
- Playwright is configured to retain a screenshot on failure and a trace on first retry. The final verification run completed without a retry; therefore no failure artifact containing form state or secrets was retained.
- The approved reference image remains the visual comparison baseline and its frozen hash is recorded in the visual-design specification.

## Security-sensitive visual QA

- API keys are always masked after save; the eye control only reveals unsaved local input.
- Base URL summaries remove userinfo, query, and fragment data before display.
- `LOCAL_MANAGEMENT_ONLY` explicitly directs the user to a local address and never recommends disabling the guard.
- Browser E2E records every non-loopback request as a failure. The final run recorded none.

## Result

The coded M6D interface conforms to the user-approved Supplier Operations Workbench direction at desktop and compact viewports. No material visual departure requiring renewed Product Design approval was found.
