# Responsive QA

Manual browser QA used the same real local project/chapter and supplier data at all three viewports.

| Viewport | Screens inspected | Result |
| --- | --- | --- |
| 1440×1024 | M1 storyboard; M2 asset drawer; M3 generation/results/rerun; M6D models | pass |
| 1180×800 | M3 generation/results; inline rerun region; M6D models | pass |
| 768×1024 | workflow/tabs; M2 full-width asset drawer; M3 results; M6D compact supplier selector | pass |

## Measurements

- 1440 chapter workbench: document width 1425px for a 1440px viewport; no body overflow.
- 1180 chapter workbench: document width 1165px for a 1180px viewport; no body overflow.
- 768 chapter workbench: document width 753px for a 768px viewport; no body overflow.
- M6D produced matching non-overflow measurements at 1440, 1180 and 768.

Dense tables and the seven-step rail retain intentional local horizontal scrolling. This prevents clipped actions and does not create page-level overflow. At 1180 and 768, M3's rerun form is a stacked non-modal region. At 768, asset detail uses a full-width portal drawer whose title, close action, 4:3 preview and version history begin at the viewport top.

## Evidence

- `assets/m1-storyboard-production-1440x1024.png`
- `assets/m2-asset-detail-production-1440x1024.png`
- `assets/m2-asset-detail-production-768x1024.png`
- `assets/m3-generation-production-1180x800.png`
- `assets/m3-results-production-768x1024.png`
- `assets/m3-rerun-production-1180x800.png`
- `assets/m6d-supplier-models-production-1440x1024.png`
- `assets/m6d-supplier-models-production-1180x800.png`
- `assets/m6d-supplier-models-production-768x1024.png`

Responsive verdict: PASS.
