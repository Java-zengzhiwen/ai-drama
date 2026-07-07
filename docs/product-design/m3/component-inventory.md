# M3 Component Inventory

## Reuse From M1/M2

- App shell;
- project/chapter rail;
- Workflow Rail;
- chapter Tabs;
- compact Tag status chips;
- inline Alert gates;
- dense table styles;
- right inspector panel;
- drawer pattern from asset detail;
- revision button group;
- retry and refresh button behavior;
- asset thumbnails and asset reference strip;
- prompt editor read-only preview style.

## New M3 Components

### GenerationTab

Owns `Agnes 生成` layout, polling notices, shot table, selected-shot preview, and submit actions.

### ShotGenerationTable

Dense table for ready and blocked shots. It must keep blocked rows visible and nonselectable.

### GenerationNoticeBar

Inline notices for auto polling, RPM limit, and restart recovery.

### ShotGenerationInspector

Selected-shot read-only panel showing Prompt, negative Prompt, source assets, and Agnes parameters.

### ResultPreviewPanel

Paused video preview with source job metadata, attempt number, provider id, and result URL state.

### ResultVersionStrip

Horizontal version selector for completed, failed, expired, and current adopted versions.

### ResultSelectionAction

Explicit current-result selection action. It must not hide prior versions.

### RerunDrawer

Drawer with source job context and approved override fields only:

```text
Prompt override
negative prompt override
asset override
mode override
duration override
```

### FailureCategoryChip

Compact normalized error category display for provider and workflow failures.

### PollingStatusIndicator

Shows whether React Query polling is active for nonterminal jobs.

## Explicitly Not Components

Do not create:

- LibTV canvas;
- voice, subtitle, or BGM controls;
- trimming timeline;
- clip stitching timeline;
- export panel;
- collaborative review panel;
- generic workflow engine;
- provider marketplace;
- M4 acceptance dashboard.
