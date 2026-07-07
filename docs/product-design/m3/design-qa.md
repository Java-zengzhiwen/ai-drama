# M3 Design QA

## Evidence

source visual truth path:

```text
docs/product-design/m3/assets/selected-direction-generation-command-result-preview.png
```

implementation screenshot path:

```text
docs/product-design/m3/assets/prototype-screenshot.png
```

full-view comparison evidence:

```text
docs/product-design/m3/assets/design-qa-comparison.png
```

focused region comparison evidence:

```text
docs/product-design/m3/assets/design-qa-focused-preview-rerun.png
```

viewport:

```text
1440 x 1024
```

state:

```text
Agnes 生成 / selected ready shot 1-01 / completed result v3 / rerun drawer open
```

## Findings

No actionable P0, P1, or P2 findings remain.

P3 follow-up polish:

- The static prototype gives the main generation table less horizontal room than the source image when the rerun drawer is open. This is acceptable for the design handoff because the table remains readable and horizontally scrollable, and the selected direction's required preview/drawer relationship is visible.
- The source image uses a richer generated street-video frame than the prototype. The prototype uses existing M2 bitmap assets to avoid inventing production assets outside the design package.

## Required Fidelity Surfaces

Fonts and typography:

- Pass. Prototype uses the M1/M2 font stack and compact 14px product UI scale.
- Headers, labels, table cells, and drawer fields stay within their containers at 1440 x 1024.

Spacing and layout rhythm:

- Pass. Shell, Workflow Rail, Tabs, toolbar, notices, dense table, preview panel, version strip, and rerun drawer follow the M1/M2 spacing rhythm and 6px radius.
- P1 found during QA: the drawer originally covered the result preview. Fixed by reserving drawer width in the workspace and narrowing the drawer.

Colors and visual tokens:

- Pass. Prototype uses inherited tokens: `#f6f8fb`, `#ffffff`, `#d9dee8`, `#2563eb`, and success/warning/error/info state colors.

Image quality and asset fidelity:

- Pass. Prototype uses real bitmap assets copied into `docs/product-design/m3/assets/`; no placeholder boxes, CSS art, or fake media surfaces are used for asset previews.
- Video preview is represented as a paused result frame with explicit play affordance and `不自动播放` label.

Copy and content:

- Pass. Copy covers ready/blocked rows, batch submit, single state inspection, auto polling, manual refresh, RPM limit, restart recovery, duplicate-submission prevention, result versioning, current adopted result, result expiration, and immutable rerun.
- Forbidden scope is absent from the prototype: no LibTV, dubbing, subtitles, BGM, timeline, export, collaboration, or M4 acceptance UI.

## Patches Made During QA

- Fixed the initial drawer overlay that hid the result preview at 1440 x 1024.
- Shortened the version-strip expired state label from `result_expired` to `已过期`; the full normalized category remains in the rerun warning Alert.
- Recaptured prototype screenshot and regenerated full-view plus focused comparison evidence.

## Final Result

final result: passed
