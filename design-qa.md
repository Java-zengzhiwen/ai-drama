# Source-to-Script Workbench — Design QA

## Evidence

- Source visual: `/Users/zengzhiwen/.codex/generated_images/019f4c96-0023-7ab1-81e2-d65db2d8e845/exec-ffef0a4a-950b-4f5e-a0d3-f40491bd9772.png`
- Implementation: `http://127.0.0.1:15174/projects/4fd5fd050e524f9e83184d4cc8df7bd2/chapters/02ef551cbd3048a1a28482005ff500f4`
- Implementation screenshot: `docs/product-design/ui-production-visualization/source-to-script-implementation-1440x1024.png`
- Combined comparison: `docs/product-design/ui-production-visualization/source-to-script-comparison-2880x1024.png`
- Viewport: `1440 × 1024`
- State: real local chapter data; the selected project has one chapter and no resolved `script_adaptation` model binding, while six enabled text models are available for direct selection.

## Visual comparison

The final comparison confirms the approved three-column structure: chapter navigation on the left, the existing manuscript content in the center, and the sole source-to-script action surface on the right. The right inspector uses the approved colored hierarchy rather than a flat white panel: pale-blue configuration and source-revision surfaces, a pale-green readiness surface, a blue-tinted preview header and notice, and a clearly separated action row.

Runtime data intentionally differs from the concept image. The implementation renders the actual single chapter instead of fabricated scene rows, reports the actual 2,468-character source, derives only explicitly labelled estimates, and presents the enabled project text models without inventing a default binding. The primary generation action fails closed until the user chooses a model.

## Fidelity surfaces

- Layout: 230px chapter navigation, flexible manuscript canvas, and 390px inspector at the desktop target.
- Typography: restrained product shell, serif manuscript reading surface, compact production metadata.
- Color: neutral canvas, selected chapter blue, blue source-revision hierarchy, green readiness hierarchy, and blue primary action.
- Controls: source editing, chapter search, navigation, save-only, model-binding navigation, and save-then-generate are real interactions.
- Responsive behavior: the inspector moves below the editor at medium widths and all three surfaces stack on narrow screens.
- Overflow: the workbench fills the remaining viewport height; chapter navigation, manuscript and inspector use contained scrolling, and the inspector action row remains at the bottom of the workbench. At `2048 × 1064`, the workbench content ends at `y=1035`, preserving only the intended 29px canvas inset.

## Interaction verification

- Chapter search has one unique control and returns the `没有匹配章节` state for an unmatched query.
- `仅保存原文` creates only a source revision.
- `保存并生成剧本` saves a changed model binding first, then saves a changed source, calls the existing script generation contract, and opens the Script tab.
- A missing project text-model resolution now exposes a direct model selector; generation remains disabled until a valid enabled text model is chosen.
- The selector persists `script_adaptation` through the existing revision/ETag contract and preserves every unrelated project default and operation override.
- A fully local fake-supplier acceptance run proved that the persisted project model is resolved into the immutable execution snapshot and receives exactly one `textRequest`; no credential or provider secret reaches the browser.
- Browser console errors and warnings: `0`.
- No real provider request was made during Design QA.

## Automated verification

- Focused source/script tests: `12 passed`.
- Local fake-provider source-to-script acceptance: `1 passed`.
- Targeted M6E fake-provider and script workflow regression: `8 passed`.
- Full web suite: `98 passed, 4 skipped`.
- Production web build: passed.
- `git diff --check`: passed.

## Final gate

No P0, P1, or P2 visual, interaction, safety, or responsive-layout findings remain.

final result: passed
