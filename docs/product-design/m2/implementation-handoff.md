# M2 Implementation Handoff

## Page Routes

Keep existing M1 routes:

```text
/projects
/projects/:projectId
/projects/:projectId/chapters/:chapterId
```

Add nested M2 chapter surfaces:

```text
/projects/:projectId/chapters/:chapterId?tab=assets&view=asset-list
/projects/:projectId/chapters/:chapterId/assets/:assetId
/projects/:projectId/chapters/:chapterId?tab=assets&view=profiles
/projects/:projectId/chapters/:chapterId?tab=assets&view=requirements
/projects/:projectId/chapters/:chapterId?tab=shot-prompt
```

Do not add a new main navigation item outside the existing project/chapter shell.

## Tab Structure

Chapter Tabs:

```text
原文
剧本
分镜
资料与资产
Shot Prompt
Agnes 生成（锁定）
结果与重跑（锁定）
```

`资料与资产` subviews:

```text
资产预览
资产详情
Profiles
缺失需求
生成记录
```

`Shot Prompt` subviews:

```text
视觉引用
Prompt 编辑
Revision 历史
Agnes 参数预览
```

## Main Components By Page

### 资料与资产: 资产预览

- `AssetGallery`
- `AssetFilterToolbar`
- `AssetStatusChip`
- `AssetQuickInspector`
- upload image action
- Agnes image generation entry

### 资料与资产: 资产详情

- `AssetDetailReview`
- `LargeAssetPreview`
- `AssetPreviewControls`
- `AssetVersionStrip`
- `AssetDecisionInspector`
- `ContinuityCheckList`
- `RelatedRequirementTable`

### 资料与资产: Profiles

- `ProfileList`
- `ProfileEditor`
- `AssetBindingPanel`
- `DeleteConfirmationPanel`
- `ProfileValidationAlert`

### 资料与资产: 缺失需求

- `AssetRequirementTable`
- `MissingAssetAction`
- `RequirementStatusChip`
- `AnalyzeRequirementsAction`

### Shot Prompt

- `ShotPromptShotList`
- `ShotPromptEditor`
- `PositivePromptSection`
- `NegativePromptSection`
- `ContinuityNotesSection`
- `AssetRefsPreview`
- `AgnesParamsPreview`
- `PromptRevisionHistory`
- `PromptGateSummary`

## API Data Dependencies

Profiles:

```text
POST /api/projects/{project_id}/profiles
GET  /api/projects/{project_id}/profiles
PUT  /api/profiles/{profile_id}
```

Assets:

```text
POST /api/chapters/{chapter_id}/assets
GET  /api/chapters/{chapter_id}/assets
POST /api/assets/{asset_id}/bindings
POST /api/assets/{asset_id}/mark-usable
POST /api/assets/{asset_id}/reject
GET  /api/assets/{asset_id}/content
POST /api/chapters/{chapter_id}/assets/generate-image
```

Asset requirements:

```text
POST /api/chapters/{chapter_id}/asset-requirements/analyze
GET  /api/chapters/{chapter_id}/asset-requirements/latest
```

Shot Prompts:

```text
POST /api/chapters/{chapter_id}/shot-prompts/generate
GET  /api/chapters/{chapter_id}/shot-prompts/revisions
PUT  /api/shot-prompt-revisions/{revision_id}
POST /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/regenerate
POST /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/mark-ready
GET  /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/agnes-preview
```

Agnes settings may be linked from image generation setup, but M2 UI must not expose video generation.

## Loading, Empty, Error States

Loading:

- keep left rail, Workflow Rail, chapter Tabs, and M2 subnav visible;
- use table skeletons for lists;
- use thumbnail skeletons for asset gallery;
- use inspector skeletons for selected detail.

Empty:

- Profiles: `暂无 Profile。创建人物、场景、道具或风格资料后开始绑定资产。`
- Assets: `暂无资产。上传图片或通过 Agnes 生成参考图。`
- Requirements: `暂无资产需求分析。确认分镜后运行分析。`
- Shot Prompt: `暂无 Prompt。资产 ready 后生成 Shot Prompt。`

Error:

- show inline Alert with retry;
- include stable error code when available;
- never offer destructive reset as the first recovery action.

## Disabled And Gate Logic

Storyboard not approved:

- disable `资料与资产`;
- disable `Shot Prompt`;
- show `未确认分镜，不允许进入后续生产步骤。`

Required assets not usable:

- allow profile and asset work;
- disable `标记 ready`;
- show `未完成必要资产，Shot Prompt 暂不可标记 ready。`

Asset rejected:

- keep asset visible in versions;
- exclude from requirement readiness;
- show `该资产不会用于 Shot Prompt，相关需求保持缺失。`

Asset generating:

- disable usable/reject/current-adopted actions until a result exists;
- keep generation parameters visible.

Prompt blocked:

- status is `blocked_by_assets`;
- `标记 ready` disabled;
- provide jump to the blocking asset requirement or asset detail.

M3 pages:

- `Agnes 生成` disabled;
- `结果与重跑` disabled;
- no video job, result, rerun, or polling UI in M2.

## Responsive Behavior

Desktop:

- use left rail, main content, and right inspector;
- asset detail uses large preview plus inspector.

Tablet / narrow desktop:

- collapse the right inspector below the main preview;
- keep subnav horizontally scrollable;
- keep asset version strip scrollable.

Mobile:

- stack left rail content above workspace if required by implementation;
- preserve task order: Workflow Rail, Tabs, subnav, active content, inspector;
- do not hide gate alerts.

## M1 Reusable Components

Reuse or closely match:

- `ChapterWorkspace` shell;
- Workflow Rail Tag pattern;
- locked Tab label pattern;
- `StatusChip`;
- `WorkflowErrorAlert`;
- table styles from Script and Storyboard tabs;
- right inspector layout from `StoryboardTab`;
- Revision button group;
- inline validation table language.

## Design Decisions Codex Must Not Change

- M2 is image-preview-first for assets.
- Asset detail is a nested chapter workspace page, not a global DAM.
- Large image preview is the primary asset review surface.
- Version comparison remains visible on asset detail.
- Asset adoption is explicit: one current adopted asset per binding role.
- Rejected assets remain visible but cannot satisfy requirements.
- Prompt readiness is blocked by missing, rejected, or non-usable assets.
- Positive and negative prompts must be visually separated.
- Agnes video and result/rerun pages remain locked.
- No professional image editor, infinite canvas, workflow engine, multi-user approval, LibTV, video generation, or post-production UI may be added during M2 implementation.

## Prototype Reference

```text
docs/product-design/m2/assets/prototype.html
```
