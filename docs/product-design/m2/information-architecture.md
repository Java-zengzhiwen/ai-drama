# M2 Information Architecture

## Existing Routes

M2 keeps M1's main routes:

```text
/projects
/projects/:projectId
/projects/:projectId/chapters/:chapterId
```

No new top-level main navigation is introduced.

## M2 Nested Chapter Surfaces

The chapter workspace adds M2 surfaces inside the existing chapter route:

```text
/projects/:projectId/chapters/:chapterId?tab=assets&view=asset-list
/projects/:projectId/chapters/:chapterId/assets/:assetId
/projects/:projectId/chapters/:chapterId?tab=assets&view=profiles
/projects/:projectId/chapters/:chapterId?tab=assets&view=requirements
/projects/:projectId/chapters/:chapterId?tab=shot-prompt
```

`/assets/:assetId` is a nested detail surface under the chapter shell. It keeps the left rail, Workflow Rail, and chapter Tabs visible.

## Chapter Tabs

```text
原文
剧本
分镜
资料与资产
Shot Prompt
Agnes 生成（锁定）
结果与重跑（锁定）
```

## 资料与资产 Subviews

```text
资产预览
资产详情
Profiles
缺失需求
生成记录
```

`资产详情` is the selected direction's primary review surface.

## Shot Prompt Subviews

```text
视觉引用
Prompt 编辑
Revision 历史
Agnes 参数预览
```

The visual reference subview can link back to asset detail when an asset blocks prompt readiness.

## Primary Objects

Profiles:

- CharacterProfile;
- SceneProfile;
- PropProfile;
- StyleProfile.

Assets:

- character_reference;
- character_outfit;
- scene_reference;
- scene_angle;
- prop_reference;
- shot_keyframe.

Requirement states:

- ready;
- missing_assets;
- asset_generation_in_progress;
- asset_review_required.

Prompt states:

- draft;
- blocked_by_assets;
- ready;
- needs_revision.
