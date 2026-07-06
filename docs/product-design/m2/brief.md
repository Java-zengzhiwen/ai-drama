# M2 Product Design Brief

## Scope

Milestone 2 covers production profiles, image assets, asset requirement analysis, and Shot Prompt preparation inside the existing chapter workspace.

This sprint is design-only. It does not modify production React code, FastAPI code, database schema, Agnes API integration, or production dependencies.

## User Goal

A local single user can move an approved Canonical Storyboard into a visually grounded production state:

1. maintain minimal Character, Scene, Prop, and Style profiles;
2. upload or generate image assets;
3. review asset versions with large image previews;
4. bind usable assets to profiles and shots;
5. see missing requirements per shot;
6. generate and edit Shot Prompts only when required assets are usable.

## Product Shape

M2 extends the M1 **Storyboard Command Table** rather than replacing it.

Inherited structure:

- top app bar;
- left project and chapter rail;
- Workflow Rail;
- chapter Tabs;
- dense table language;
- compact status chips;
- inline Alerts for gates and errors;
- right inspector for the selected item;
- save, confirm, reject, retry, and revision actions.

Selected M2 direction:

**Asset Detail Review Page**

The asset experience is image-preview-first. The main asset judgment surface is a nested asset detail page with:

- large bitmap preview;
- version comparison strip;
- review state and adoption controls;
- profile and shot bindings;
- continuity checks;
- related missing requirements;
- jump back to asset list or forward to Shot Prompt.

## M2 Boundary

M2 must not unlock:

- Agnes video generation;
- result preview;
- rerun flows;
- LibTV;
- post-production;
- professional image editing;
- infinite canvas;
- complex DAM;
- multi-user approval;
- drag-and-drop workflow engine.

## Prototype

Open the static prototype:

```text
docs/product-design/m2/assets/prototype.html
```

Selected direction image:

```text
docs/product-design/m2/assets/selected-direction-asset-detail-review-page.png
```
