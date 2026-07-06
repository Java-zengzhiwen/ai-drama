# M2 Interaction Spec

## Navigation

M2 stays inside the existing chapter workspace.

- Top route stays project and chapter based.
- Chapter Tabs carry the stage.
- M2 subviews carry the local task.
- Asset detail is a nested page, not a new global navigation item.

## Asset Preview List

Purpose: scan visual assets quickly.

Interactions:

- filter by asset type, binding target, and status;
- search by asset name, profile, shot, or source;
- upload image;
- open Agnes image generation entry;
- open asset detail;
- mark current adopted asset from the inspector only after review.

Visual rule: thumbnails are primary. Metadata is secondary.

## Asset Detail Review

Purpose: decide whether one image is usable for production.

Main regions:

- large image preview;
- simple fit / 100% / previous / next controls;
- version comparison strip;
- right inspector with metadata and decisions;
- related requirements table.

The preview is not an image editor. No crop, paint, layer, mask, infinite canvas, or professional retouch controls.

Review actions:

- `标记可用`;
- `拒绝`;
- `设为当前采用`;
- `返回资产列表`.

Rejecting an asset requires a reason when the asset was previously usable or current adopted.

## Profiles

Profiles use list plus inspector editing.

Supported profile types:

- Character;
- Scene;
- Prop;
- Style.

Profile actions:

- create;
- edit;
- save;
- bind reference asset;
- delete with confirmation.

Profile fields must stay minimal:

- name;
- identity or layout notes;
- continuity_notes;
- costume notes for Character;
- scene layout notes for Scene;
- prop handling notes for Prop;
- style rules for Style.

## Asset Requirements

Requirements are shown per shot in a dense table.

Each missing cell links to the smallest corrective action:

- create profile;
- upload image;
- generate image;
- open asset detail;
- choose current adopted asset.

Requirement rows must not hide blockers behind a modal.

## Shot Prompt Studio

Prompt editing uses the M1 table plus inspector pattern:

- left shot list;
- main positive and negative prompt editor;
- continuity notes;
- asset_refs thumbnail strip;
- right gate and Agnes parameter preview.

Prompt actions:

- 全章生成;
- 单镜重新生成;
- 手工编辑;
- 保存新 Revision;
- 标记 ready;
- view Revision history.

`标记 ready` is disabled when:

- requirements are not ready;
- an asset is missing;
- an asset is not usable;
- selected asset is rejected;
- duration is invalid;
- canonical prompt validation fails.

## Alerts And Gates

Inline Alerts stay near the blocked action. No success modal is needed.

Examples:

```text
未完成必要资产，Shot Prompt 暂不可标记 ready。
该资产不会用于 Shot Prompt，相关需求保持缺失。
M2 不开放 Agnes 视频生成。
```
