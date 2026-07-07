# M3 Implementation Handoff

## Page Routes

Keep existing routes:

```text
/projects
/projects/:projectId
/projects/:projectId/chapters/:chapterId
/settings/agnes
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
Agnes 生成
结果与重跑
```

M3 unlocks `Agnes 生成` and `结果与重跑` after Shot Prompt readiness permits video generation.

## Main Components By Page

### Agnes 生成

- `GenerationTab`
- `GenerationNoticeBar`
- `ShotGenerationTable`
- `ShotGenerationInspector`
- `PollingStatusIndicator`
- `FailureCategoryChip`
- `ResultPreviewPanel`
- `ResultVersionStrip`
- `RerunDrawer`

### 结果与重跑

- `ResultsTab`
- `ShotResultList`
- `VideoResultCard`
- `ResultVersionStrip`
- `ResultSelectionAction`
- `SourceInputsPanel`
- `FailureReviewPanel`
- `RerunDrawer`

## API Data Dependencies

Generation:

```text
POST /api/chapters/{chapter_id}/generation/video-jobs
GET  /api/chapters/{chapter_id}/generation/jobs
GET  /api/generation/jobs/{job_id}
POST /api/generation/jobs/{job_id}/refresh
```

Results:

```text
GET  /api/chapters/{chapter_id}/results
POST /api/shots/{shot_id}/results/{result_id}/select
POST /api/results/{result_id}/review
POST /api/generation/jobs/{job_id}/rerun
```

Existing supporting APIs:

```text
GET /api/chapters/{chapter_id}/status
GET /api/chapters/{chapter_id}/shot-prompts/revisions
GET /api/shot-prompt-revisions/{revision_id}/shots/{shot_id}/agnes-preview
GET /api/chapters/{chapter_id}/assets
GET /api/assets/{asset_id}/content
GET /api/settings/agnes
```

## State Mapping

Backend job states to UI states:

```text
draft      -> waiting
queued     -> queued
submitting -> submitting
submitted  -> generating
polling    -> generating
completed  -> completed
failed     -> failed
cancelled  -> cancelled
```

Display categories:

```text
authentication
rate_limited
invalid_request
input_unreachable
provider_busy
generation_failed
timeout
result_expired
unknown_provider_error
submission_outcome_unknown
```

## Loading, Empty, Error States

Loading:

- keep left rail, Workflow Rail, chapter Tabs, and active toolbar visible;
- use table skeletons and inspector skeletons.

Empty:

- Agnes generation: `暂无 ready 镜头。请先在 Shot Prompt 标记镜头 Ready。`
- Results: `暂无视频结果。提交 Agnes 生成后会显示结果版本。`

Error:

- show inline Alert with stable category;
- provide refresh or rerun only when API state allows it;
- do not offer destructive reset as first recovery action.

## Submit And Duplicate Behavior

- Batch submit applies only to selected ready rows.
- Single-shot submit applies only to the selected ready row.
- Submit buttons disable while the mutation is pending.
- If an equivalent job already exists, the row should show the existing job rather than creating another.
- Active queued/submitting/generating jobs cannot be submitted again.
- Explicit rerun is the only UI path that creates a new attempt for a prior source job.

## Polling And Refresh

- Use React Query polling only while nonterminal jobs exist.
- Show polling interval text near the table.
- Manual refresh is available for chapter-level job refresh and selected job refresh.
- RPM limit hint remains visible while queued jobs exist.
- Restart recovery notice remains visible when queued, submitted, polling, or `submission_outcome_unknown` jobs exist.

## Video Preview

- Use native video preview or a poster frame.
- Do not autoplay.
- Keep play controls visible.
- Show result URL expiration separately from local persisted result availability.

## Result Version History

- Keep every result version visible.
- Mark exactly one current adopted result per shot.
- Selecting a result must not delete or overwrite prior versions.
- Failed and expired versions remain visible for traceability.

## Rerun Drawer

Allowed override fields:

```text
positive prompt
negative prompt
selected assets
generation mode
duration
```

Required source context:

- source job id;
- provider job id;
- attempt number;
- source result id when available;
- source Prompt;
- source assets;
- source video parameters.

Rerun creation must preserve the source job and source result.

## Responsive Behavior

Desktop:

- keep generation table and right preview/inspector side by side;
- drawer opens from the right and may overlay the inspector.

Tablet / narrow desktop:

- keep table first;
- stack result preview below the table;
- drawer remains full-height.

Mobile:

- preserve order: Workflow Rail, Tabs, notices, table, selected preview, drawer;
- keep gate alerts visible;
- allow horizontal scroll for dense tables and version strips.

## Reusable M1/M2 Components

Reuse or closely match:

- `ChapterWorkspace`;
- Workflow Rail Tag pattern;
- locked/unlocked Tab label pattern;
- `WorkflowErrorAlert`;
- table styles from Script, Storyboard, Asset Requirement, and Shot Prompt tabs;
- right inspector layout from Storyboard and Shot Prompt;
- asset thumbnail and version strip language from M2;
- Drawer pattern from Asset Grid;
- Prompt Gate summary style;
- Agnes parameter preview block.

## Design Decisions Implementation Must Not Change

- M3 is still a chapter workspace, not a new dashboard.
- `Agnes 生成` uses a table-first command surface.
- Result preview is visible from the selected generation row.
- Video preview never autoplays.
- Rerun is explicit and immutable.
- Only approved override fields appear in the rerun drawer.
- Prior jobs and prior results remain visible after rerun.
- Blocked shots stay visible with direct correction routes.
- Polling, RPM, and restart recovery states are first-class UI states.
- Do not add LibTV, dubbing, subtitles, BGM, timeline, video editing, export, collaboration, or M4 acceptance UI.

## Prototype Reference

```text
docs/product-design/m3/assets/prototype.html
```
