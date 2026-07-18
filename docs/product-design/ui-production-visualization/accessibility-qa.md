# Accessibility QA

## Automated and component evidence

- Global navigation exposes `aria-current="page"`.
- The chapter workflow is a named list with seven named list items and stable blocked-reason metadata.
- Dense generation/result/storyboard rows expose selected state with `aria-selected`.
- Asset detail exposes a named dialog, named `资产主预览` region, and named `资产版本历史` list.
- The compact rerun form exposes a named non-modal region rather than a dialog.
- Status errors/notices use Ant Design alert semantics and live announcement behavior.
- Disabled controls retain native/Ant disabled semantics.
- Result video has controls and does not have autoplay.

## Manual keyboard verification

- Desktop rerun opens as a focus-contained Ant Drawer.
- Pressing Escape from the drawer close control closes the drawer.
- After Escape, focus returns to the `创建重跑` trigger.
- Compact rerun opens with focus on its explicit close action and remains in document flow.
- Asset detail and metadata use body-level Drawer portals, preventing the focus context from being trapped in an offscreen scrolled container.
- All primary actions and tabs are keyboard-reachable with visible focus outlines.

## Browser evidence

- Console errors: 0.
- Console warnings: 0.
- External provider resources: 0.
- Named landmark/region inspection completed for M1, M2, M3 and M6D.

Accessibility verdict: PASS for the implemented screen scope.
