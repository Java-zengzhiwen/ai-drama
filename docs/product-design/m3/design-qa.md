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
```

viewports:

```text
1440 x 1024
1180 x 800
768 x 1024
```

state:

```text
Agnes 生成 / selected ready shot 1-01 / completed result v3 / rerun drawer open
Responsive evidence includes top table-first viewport and drawer scrolled into view.
```

## Findings

No actionable P0, P1, or P2 findings remain.

Expected source-to-prototype differences:

- The source visual still includes earlier unconfirmed Agnes parameter examples. The revised prototype intentionally removes or marks those provider parameters and only shows fields supported by backend provider capability/API schema.
- The source image uses a richer generated street-video frame than the prototype. The prototype uses existing M2 bitmap assets to avoid inventing production assets outside the design package.

## Required Fidelity Surfaces

Fonts and typography:

- Pass. Prototype uses the M1/M2 font stack and compact product UI scale.
- Verified at 1440 x 1024, 1180 x 800, and 768 x 1024: table headers, row text, drawer labels, and notice text stay readable without overlapping.

Spacing and layout rhythm:

- Pass. Shell, Workflow Rail, Tabs, toolbar, notices, dense table, preview panel, version strip, and rerun drawer follow the inherited M1/M2 rhythm and 6px radius.
- Desktop verification: 360px drawer width is reserved and does not cover the result preview in the settled state.
- 1180 x 800 verification: table remains first, preview/drawer stack below, and drawer fields use full available width.
- 768 x 1024 verification: sidebar and workflow content reflow, dense table remains horizontally scrollable, drawer footer actions wrap without overflow.

Colors and visual tokens:

- Pass. Prototype uses inherited neutral surfaces, blue focus/accent, and success/warning/error/info chips.
- Gate, RPM, polling, restart recovery, URL-expired, and blocked states remain visually distinct.

Image quality and asset fidelity:

- Pass. Prototype uses real bitmap assets in `docs/product-design/m3/assets/`.
- Video preview remains a paused 16:9 decision surface and does not autoplay.

Copy and content:

- Pass. Copy covers ready/blocked visibility, ready-only submit, batch submit, single state inspection, duplicate-submission prevention, auto polling, manual refresh, RPM limit, restart recovery, result versioning, current adopted result, two result URL expiration cases, and immutable rerun.
- Forbidden scope remains absent: no LibTV, dubbing, subtitles, BGM, timeline, export, collaboration, or M4 acceptance UI.

Accessibility:

- Pass for design handoff. Drawer has modal dialog semantics, title/description wiring, Escape close behavior, and keyboard-reachable controls.
- Polling notices use polite live-region semantics.
- Table selection checkboxes have shot-specific labels, and blocked rows expose disabled selection.

## Patches Made During QA

- Changed prototype video parameter preview from unsupported fixed provider examples to 16:9 and backend capability/API schema driven parameter display.
- Removed the unconfirmed hard-coded FPS, style strength, slow mode, and fixed resolution examples from the prototype.
- Updated Tab Gate rules: current Shot Prompt revision unlocks `Agnes 生成`; at least one `GenerationJob` unlocks `结果与重跑`.
- Added rerun asset override contract using M2 Asset Picker, usable-only filtering, category filtering, current/replacement comparison, exact asset IDs, and provider reachability validation.
- Split result expiration into `source_url_expired + local_result_available` and `source_url_expired + local_result_missing`.
- Standardized drawer width, overlay rules, responsive stacking, keyboard behavior, and accessibility rules.
- Captured 1440 x 1024, 1180 x 800, and 768 x 1024 screenshots and regenerated comparison evidence.

## Final Result

final result: passed
