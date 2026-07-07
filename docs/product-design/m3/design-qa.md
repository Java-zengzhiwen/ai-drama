# M3 Design QA

## Evidence

source visual truth path:

```text
docs/product-design/m3/assets/selected-direction-generation-command-result-preview.png
```

implementation screenshot paths:

```text
docs/product-design/m3/assets/prototype-screenshot-1440x1024.png
docs/product-design/m3/assets/prototype-screenshot-1180x800.png
docs/product-design/m3/assets/prototype-screenshot-1180x800-drawer.png
docs/product-design/m3/assets/prototype-screenshot-768x1024.png
docs/product-design/m3/assets/prototype-screenshot-768x1024-drawer.png
```

full-view comparison evidence:

```text
docs/product-design/m3/assets/design-qa-comparison-1440x1024.png
docs/product-design/m3/assets/design-qa-responsive-1180x800.png
docs/product-design/m3/assets/design-qa-responsive-768x1024.png
```

focused region comparison evidence:

```text
docs/product-design/m3/assets/design-qa-focused-preview-rerun.png
docs/product-design/m3/assets/design-qa-recovery-lifecycle.png
```

viewports:

```text
1440 x 1024
1180 x 800
768 x 1024
```

state:

```text
Agnes 生成 / selected ready shot 1-01 / completed result v3 / recovery lifecycle exercised / recovered notice dismissed / rerun drawer opened from real trigger
Responsive evidence includes table-first viewport and drawer opened/scrolled into view.
```

## Findings

No actionable P0, P1, or P2 findings remain.

Expected source-to-prototype differences:

- The source visual still includes earlier unconfirmed Agnes parameter examples. The revised prototype intentionally removes or marks those provider parameters and only shows fields supported by backend provider capability/API schema.
- The source image uses a richer generated street-video frame than the prototype. The prototype uses existing M2 bitmap assets to avoid inventing production assets outside the design package.

## Required Fidelity Surfaces

Fonts and typography:

- Pass. Prototype uses the M1/M2 font stack and compact product UI scale.
- Verified at 1440 x 1024, 1180 x 800, and 768 x 1024: table headers, row text, drawer labels, notice text, and footer actions stay readable without overlapping.

Spacing and layout rhythm:

- Pass. Shell, Workflow Rail, Tabs, toolbar, notices, dense table, preview panel, version strip, and rerun drawer follow inherited M1/M2 rhythm and 6px radius.
- Desktop verification: drawer width is 360px and the settled state reserves space so it does not cover result preview.
- 1180 x 800 verification: table remains first, drawer opens as a stacked region below preview, and it does not cover table or preview.
- 768 x 1024 verification: layout is single column, dense table and version strip remain horizontally scrollable, drawer is full-width, and footer actions do not overflow.
- Version thumbnail token verification: prototype uses `min-width: 96px`.

Colors and visual tokens:

- Pass. Prototype uses inherited neutral surfaces, blue focus/accent, and success/warning/error/info chips.
- `restart_recovery_in_progress`, `recovered_after_restart`, and `submission_outcome_unknown` are visually separate notices.

Image quality and asset fidelity:

- Pass. Prototype uses real bitmap assets in `docs/product-design/m3/assets/`.
- Video preview remains a paused 16:9 decision surface and does not autoplay.

Copy and content:

- Pass. Copy covers ready/blocked visibility, ready-only submit, duplicate prevention, auto polling, manual refresh, RPM limit, restart recovery lifecycle, result versioning, current adopted result, two result URL expiration cases, and immutable rerun.
- `recovered_after_restart` distinguishes discovered, recovered, and exception counts.
- `submission_outcome_unknown` is shown separately and is not counted as recovered success.
- Forbidden scope remains absent: no LibTV, dubbing, subtitles, BGM, timeline, export, collaboration, or M4 acceptance UI.

## Interaction QA

Browser verification was executed against `docs/product-design/m3/assets/prototype.html`.

1440 x 1024:

- Pass. Drawer opens from a real `data-rerun-trigger`.
- Pass. Drawer role is `dialog`.
- Pass. Drawer has `aria-modal="true"`.
- Pass. Drawer width is 360px.
- Pass. Drawer does not cover result preview in settled state.
- Pass. Focus enters the first editable drawer field.
- Pass. `Tab` and `Shift+Tab` remain inside drawer.
- Pass. `Esc` closes drawer.
- Pass. Focus returns to the actual triggering rerun button.
- Pass. `recovered_after_restart` notice is visible.
- Pass. `submission_outcome_unknown` remains separately visible.

1180 x 800:

- Pass. Drawer stacks below preview.
- Pass. Drawer role is `region`.
- Pass. Drawer has no `aria-modal`.
- Pass. Focus enters drawer after open.
- Pass. No desktop focus trap is applied.
- Pass. `Esc` closes drawer and returns focus to the actual trigger.
- Pass. Table remains first and drawer does not cover table or preview.

768 x 1024:

- Pass. Layout is single column.
- Pass. Dense table remains horizontally scrollable.
- Pass. Version strip remains horizontally scrollable.
- Pass. Drawer is full-width.
- Pass. Footer actions do not overflow.
- Pass. `recovered_after_restart` notice is readable.
- Pass. Blocked checkboxes are disabled.
- Pass. Keyboard focus style is visible on drawer fields.

Recovery lifecycle:

- Pass. `restart_recovery_in_progress` and `recovered_after_restart` are mutually exclusive.
- Pass. Completion replaces the in-progress notice.
- Pass. Recovered copy distinguishes discovered, recovered, and exception counts.
- Pass. `submission_outcome_unknown` remains separately visible.
- Pass. Recovered notice can be dismissed by keyboard and pointer.
- Pass. Dismissal does not hide polling, RPM, or `submission_outcome_unknown` notices.
- Pass. Dismissal does not alter Drawer behavior or task state.

Accessibility:

- Pass. Polling, recovery in-progress, recovered, and unknown notices use separate polite live-region behavior so state changes do not re-announce the whole notice bar.
- Pass. Recovered dismiss button is reachable by `Tab`, has accessible name `关闭恢复完成提示`, and triggers with pointer, `Enter`, and `Space`.
- Pass. After dismissal, focus moves to the GenerationNoticeBar container and is not forced into the Drawer or page top.
- Pass. Table selection checkboxes and rerun action buttons have shot-specific accessible names.
- Pass. Row `Enter` selects the row without submitting a job.
- Pass. Row keyboard/click handling ignores events from buttons, inputs, selects, textareas, and links.

## Patches Made During QA

- Added `recovered_after_restart` and distinguished it from `restart_recovery_in_progress` and `submission_outcome_unknown`.
- Added recovery lifecycle prototype controls for scan in-progress and scan completed states.
- Added `recovered_after_restart` dismiss action with keyboard-accessible button and notice-level visibility state only.
- Updated recovery copy to distinguish 3 discovered unfinished tasks, 2 recovered tasks, and 1 manual-check exception.
- Implemented real drawer open/close behavior from `data-rerun-trigger` buttons for failed, cancelled, expired, and unsatisfactory examples.
- Added responsive drawer semantics: desktop `role="dialog"` with `aria-modal="true"`; narrow viewport `role="region"` with no `aria-modal`.
- Added desktop focus trap, `Esc` close, actual trigger focus return, and narrow viewport scroll/focus behavior.
- Replaced fixed `batchBtn` focus return with `lastRerunTrigger?.focus()`.
- Prevented row keyboard/click handlers from reacting to nested interactive controls.
- Updated version thumbnail min width to 96px.
- Regenerated 1440 x 1024, 1180 x 800, and 768 x 1024 screenshots plus full-view and focused comparison evidence.

## Final Result

final result: passed
