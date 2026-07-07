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

M3 Gate rules:

- `Agnes 生成` unlocks when the chapter has a current Shot Prompt revision.
- Ready and blocked shots are both visible inside `Agnes 生成`.
- Only ready shots can be selected or submitted.
- `结果与重跑` unlocks when at least one `GenerationJob` exists for the chapter.
- Blocked rows stay visible with correction routes, but their submit controls are disabled.

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

## Provider Capability And API Schema Boundary

The frontend must display only video parameters that the backend provider capability/API schema explicitly supports.

Implementation rules:

- do not hard-code Agnes provider-only parameters in React;
- do not show fixed frame rate, style strength, fixed pixel resolution, or provider mode labels unless returned by backend capability/API schema;
- render mode and duration override controls only when those fields are supported;
- keep unsupported fields absent rather than disabled, unless the API returns an explicit unsupported reason that should be explained;
- persist canonical values from the API schema, not localized display labels.

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

Recovery UI states:

```text
restart_recovery_in_progress
recovered_after_restart
submission_outcome_unknown
```

Recovery semantics:

- `restart_recovery_in_progress`: app startup found persisted `queued`, `submitted`, or `polling` jobs and is checking whether Poller can reclaim them.
- `recovered_after_restart`: recovery check completed; Poller reclaimed recoverable jobs; UI shows discovered count, recovered count, and exception count.
- `submission_outcome_unknown`: persisted `submitting` job has no provider job id and cannot be counted as recovered success.

## Loading, Empty, Error States

Loading:

- keep left rail, Workflow Rail, chapter Tabs, and active toolbar visible;
- use table skeletons and inspector skeletons.

Empty:

- Agnes locked: `请先生成或选择当前 Shot Prompt revision。`
- Agnes unlocked with no ready rows: `暂无 ready 镜头。blocked 镜头仍会显示原因，但不可提交。`
- Results locked: `已有 GenerationJob 后可查看结果与重跑。`
- Results empty after unlock: `暂无视频结果。提交 Agnes 生成后会显示结果版本。`

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
- Show `restart_recovery_in_progress` while startup recovery scans persisted jobs.
- Do not show `restart_recovery_in_progress` and `recovered_after_restart` at the same time.
- Show `recovered_after_restart` after Poller reclaims recoverable jobs.
- `recovered_after_restart` must include discovered count, recovered count, and exception count.
- User may dismiss `recovered_after_restart`; dismissal must change only local notice visibility.
- Dismissal must not stop Poller, pause React Query polling, modify Job state, or hide polling/RPM notices.
- Show `submission_outcome_unknown` separately when a persisted `submitting` job has no provider job id.
- `submission_outcome_unknown` must not be hidden by `recovered_after_restart`.
- `submission_outcome_unknown` must not be counted as recovered success.

## Video Preview

- Use native video preview or a poster frame.
- Do not autoplay.
- Keep play controls visible.
- Show result URL expiration separately from local persisted result availability.
- `source_url_expired + local_result_available`: show the local persisted result, label the provider source URL as expired, keep rerun available when API state permits.
- `source_url_expired + local_result_missing`: do not show a broken video preview; show source Prompt, source assets, Job, and attempt metadata as the recovery basis.

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

Render an override field only if the backend provider capability/API schema supports it.

Required source context:

- source job id;
- provider job id;
- attempt number;
- source result id when available;
- source Prompt;
- source assets;
- source video parameters.

Rerun creation must preserve the source job and source result.

Asset override contract:

- reuse the M2 Asset Picker component and visual language;
- show only assets with usable state;
- support category filtering for `character_reference`, `character_outfit`, `scene_reference`, `scene_angle`, `prop_reference`, and `shot_keyframe`;
- show current asset and replacement asset side by side before submit;
- save exact replacement asset IDs in the rerun request;
- never save thumbnail URL, local path, display name, or provider URL as the identity;
- validate provider reachability for every selected replacement before enabling `创建重跑任务`;
- if reachability fails, preserve the selection in the drawer and show the normalized error category.

Drawer keyboard and accessibility:

- desktop uses `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and `aria-describedby`;
- 1180px and below uses `role="region"` and removes `aria-modal`;
- open from a real `data-rerun-trigger` action and save the actual trigger;
- move focus into the drawer title or first editable field when opened;
- trap `Tab` and `Shift+Tab` focus within the drawer only in desktop modal mode;
- do not trap focus in narrow viewport region mode;
- close on `Esc`;
- return focus to the invoking rerun action after close;
- close and cancel buttons both close the drawer;
- keep reset, cancel, and create actions keyboard reachable in that order.

## Responsive Behavior

Desktop:

- keep generation table and right preview/inspector side by side;
- drawer opens from the right at the shared desktop width token;
- workspace reserves drawer width when the drawer is persistently open;
- drawer may overlay the inspector only for transient open/close animation, not for the settled state.

Tablet / narrow desktop:

- keep table first;
- stack result preview below the table;
- at 1180px and below, drawer stacks below the preview and no longer covers table or inspector;
- drawer remains full-width within the content column.

Mobile:

- preserve order: Workflow Rail, Tabs, notices, table, selected preview, drawer;
- keep gate alerts visible;
- allow horizontal scroll for dense tables and version strips.
- at 768px and below, drawer is full-width with footer actions wrapping instead of overflowing.

## Table And Notice Accessibility

- Table selection checkboxes must have shot-specific accessible names.
- Blocked shot checkboxes are disabled and named as not submittable.
- Row focus with `Enter` selects the row; it must not submit the job.
- Batch submit button references selected-ready count via `aria-describedby`.
- Polling, RPM, and restart recovery notices use `role="status"` with `aria-live="polite"`.
- Notice updates must not steal focus from the table or drawer.
- Row click and row keyboard handlers must ignore events from `button`, `input`, `select`, `textarea`, or `a`.

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
- Agnes parameter preview block driven by backend provider capability/API schema.

## Design Decisions Implementation Must Not Change

- M3 is still a chapter workspace, not a new dashboard.
- `Agnes 生成` uses a table-first command surface.
- `Agnes 生成` unlocks from current Shot Prompt revision existence, not from every shot being ready.
- Result preview is visible from the selected generation row.
- Video preview never autoplays.
- Rerun is explicit and immutable.
- Only approved override fields appear in the rerun drawer.
- Approved override fields still appear only when backend provider capability/API schema supports them.
- Prior jobs and prior results remain visible after rerun.
- Ready and blocked shots stay visible; only ready shots can be submitted.
- Polling, RPM, and restart recovery states are first-class UI states.
- `restart_recovery_in_progress`, `recovered_after_restart`, and `submission_outcome_unknown` are distinct UI states and must not be merged.
- Do not add LibTV, dubbing, subtitles, BGM, timeline, video editing, export, collaboration, or M4 acceptance UI.

## Prototype Reference

```text
docs/product-design/m3/assets/prototype.html
```
