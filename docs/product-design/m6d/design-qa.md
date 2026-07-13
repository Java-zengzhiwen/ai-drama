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

- 1440x1000: [`assets/m6d-implementation-desktop-1440.png`](assets/m6d-implementation-desktop-1440.png) preserves the reference's left supplier rail, central tabbed model table, and right inspector. Compared with the approved reference, the implementation intentionally has fewer toolbar actions because duplication, marketplace, batch operations, and multi-account management are outside M6D scope.
- 1180x1000: [`assets/m6d-implementation-1180.png`](assets/m6d-implementation-1180.png) shows the inspector stacked below the command surface with no overlap or clipped table actions, matching the frozen responsive rule.
- 768x1000: [`assets/m6d-implementation-768.png`](assets/m6d-implementation-768.png) shows the compact supplier selector, horizontally scrollable model table, wrapped command header, and stacked inspector.
- Desktop Chrome automation also validates dialogs, keyboard tab navigation, route refresh, and the actual model-management workflow.
- The committed QA screenshots use the built-in OpenAI supplier and contain no credential input or secret value. Playwright separately retains a screenshot on failure and a trace on first retry.
- The approved reference image remains the visual comparison baseline and its frozen hash is recorded in the visual-design specification.

## Security-sensitive visual QA

- API keys are always masked after save; the eye control only reveals unsaved local input.
- Base URL summaries remove userinfo, query, and fragment data before display.
- `LOCAL_MANAGEMENT_ONLY` explicitly directs the user to a local address and never recommends disabling the guard.
- Browser E2E records every non-loopback request as a failure. The final run recorded none.

## Result

The coded M6D interface conforms to the user-approved Supplier Operations Workbench direction at desktop and compact viewports. No material visual departure requiring renewed Product Design approval was found.
