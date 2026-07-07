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

Inline notices for auto polling, RPM limit, `restart_recovery_in_progress`, `recovered_after_restart`, and `submission_outcome_unknown`.

Rules:

- `restart_recovery_in_progress` appears while startup recovery scans persisted jobs;
- `restart_recovery_in_progress` and `recovered_after_restart` are mutually exclusive;
- `recovered_after_restart` appears after Poller reclaims recoverable jobs and shows discovered, recovered, and exception counts;
- `recovered_after_restart` includes an accessible dismiss action;
- `submission_outcome_unknown` remains a separate warning and is never merged into `recovered_after_restart`;
- dismissing `recovered_after_restart` changes only notice visibility and does not change task state;
- dismissing `recovered_after_restart` does not stop Poller or React Query polling;
- dismissing `recovered_after_restart` does not hide polling, RPM, or `submission_outcome_unknown` notices;
- notice updates use separate polite live-region behavior and do not steal focus.

### ShotGenerationInspector

Selected-shot read-only panel showing Prompt, negative Prompt, source assets, 16:9 video aspect, and only Agnes parameters returned by backend provider capability/API schema.

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

`asset override` reuses the M2 Asset Picker rather than introducing a new picker.

Required asset override behaviors:

- only usable assets are selectable;
- category filters match M2 asset categories;
- current and replacement assets are compared before submit;
- exact asset IDs are saved in the rerun request;
- provider reachability is validated before submit.

### FailureCategoryChip

Compact normalized error category display for provider and workflow failures.

### PollingStatusIndicator

Shows whether React Query polling is active for nonterminal jobs. It must be announced with polite live-region semantics and must not move focus.

### DrawerAccessibilityContract

Shared behavior for `RerunDrawer`:

- desktop modal dialog role and labels;
- narrow viewport nonmodal region role and labels;
- focus moves in on open and returns on close;
- `Esc` closes;
- `Tab` and `Shift+Tab` remain inside only while desktop modal semantics are active;
- desktop width and responsive stacking follow the shared drawer token.

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
