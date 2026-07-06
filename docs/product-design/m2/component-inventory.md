# M2 Component Inventory

## Reuse From M1

- App shell;
- project/chapter rail;
- Workflow Rail;
- chapter Tabs;
- compact Tag status chips;
- inline Alert gates;
- table styles;
- revision button group;
- right inspector panel;
- validation/QC table;
- primary, secondary, danger, and retry button hierarchy.

## New M2 Components

### M2Subnav

Second-level navigation inside `资料与资产` and `Shot Prompt`.

### AssetGallery

Image-first grid for assets. Tiles include:

- thumbnail;
- asset name;
- asset_type;
- status;
- binding summary;
- current adopted marker.

### AssetDetailReview

Dedicated nested detail page with:

- large preview;
- preview controls;
- version strip;
- metadata inspector;
- decision actions;
- related requirements table.

### AssetVersionStrip

Horizontal version comparison. Shows usable, rejected, generating, and current adopted states.

### ProfileList

Dense table of Character, Scene, Prop, and Style profiles.

### ProfileEditor

Minimal form with continuity notes and type-specific notes.

### AssetBindingPanel

Shows profile, shot, role, current adopted asset, and alternate versions.

### AssetRequirementTable

Per-shot requirement table with direct missing-item actions.

### ShotPromptEditor

Prompt workbench with:

- shot list;
- positive_prompt area;
- negative_prompt area;
- continuity_notes;
- asset_refs thumbnails;
- Agnes parameter preview;
- Revision actions.

### PromptGateSummary

Right inspector block that explains why a prompt is draft, blocked, ready, or needs revision.

## Explicitly Not Components

Do not create:

- image editor toolbar;
- cropper;
- layer panel;
- infinite canvas;
- generic DAM taxonomy builder;
- workflow engine builder;
- video job table;
- result rerun console.
