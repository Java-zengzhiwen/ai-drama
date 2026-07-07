# M3 Interaction Spec

## Navigation

M3 stays inside the existing chapter workspace.

- Top routes remain project and chapter based.
- Chapter Tabs carry the production stage.
- `Agnes 生成` owns submission and job monitoring.
- `结果与重跑` owns result review, selection, failure review, and rerun.
- No new global sidebar item is added.

Tab Gate:

- `Agnes 生成` unlocks when a current Shot Prompt revision exists.
- Ready and blocked shots are both listed after unlock.
- Only ready shots can be selected or submitted.
- `结果与重跑` unlocks when at least one `GenerationJob` exists.

## Agnes 生成

Purpose: make ready-shot submission and job status clear without hiding blocked reasons.

Primary actions:

- `批量提交`;
- `提交当前镜头`;
- `刷新状态`;
- `打开结果`;
- `创建重跑`.

Table columns:

```text
select
shot_id
就绪状态
Prompt 版本
资产状态
模式
时长
任务状态
当前结果
最后更新时间
操作
```

Rules:

- ready rows are selectable and submittable;
- blocked rows are visible with correction routes but not selectable;
- batch submit submits only selected ready rows;
- single-shot submit is disabled when the selected shot is blocked or already has an active equivalent job;
- submitting state disables duplicate clicks;
- manual refresh is always secondary to automatic polling.

## Prompt, Assets, And Parameters Preview

The selected shot must show:

- positive prompt;
- negative prompt;
- asset reference thumbnails;
- 16:9 video aspect;
- generation mode only when supported by backend provider capability/API schema;
- duration only when supported by backend provider capability/API schema;
- other provider-supported video parameters;
- source Shot Prompt revision.

The frontend must not hard-code unconfirmed Agnes provider parameters. Fields such as frame rate, style strength, fixed pixel resolution, and mode labels are hidden unless the backend capability/API schema explicitly returns them.

The preview is read-only on `Agnes 生成`. Prompt edits stay in `Shot Prompt`; rerun overrides stay in the rerun drawer.

## Polling And Recovery Notices

Inline notices appear above the table:

```text
自动轮询中；刷新间隔来自运行时策略。
RPM 限制：队列会按速率提交。
restart_recovery_in_progress：启动后检查 queued/submitted/polling 任务。
recovered_after_restart：应用重启后已恢复 3 个未完成任务：2 个继续自动处理，1 个需要人工检查。
submission_outcome_unknown：1 个任务状态无法确认，已标记为 submission_outcome_unknown。
```

`submission_outcome_unknown` is shown as a warning state that requires user attention before rerun or manual resolution.

Recovery lifecycle:

- recovery check start shows `restart_recovery_in_progress`;
- recovery check completion shows `recovered_after_restart`;
- `recovered_after_restart` is a nonblocking success/info notice;
- users may dismiss `recovered_after_restart`;
- dismissing `recovered_after_restart` must not stop Poller or React Query polling;
- stable failure categories remain visible on affected rows;
- `submission_outcome_unknown` must not be hidden by `recovered_after_restart`;
- persisted `submitting` jobs without provider job id are counted only under `submission_outcome_unknown`, not recovered success.

Accessibility:

- polling and restart notices use `role="status"` and `aria-live="polite"`;
- RPM limit changes do not steal focus;
- manual refresh buttons remain keyboard reachable next to the notices.

## Results Preview

Video preview behavior:

- never autoplay;
- show poster/first frame and native play control;
- show source job and attempt metadata near the preview;
- show result URL expiration separately from generation failure.
- distinguish `source_url_expired + local_result_available` from `source_url_expired + local_result_missing`.

Version strip:

- shows every attempt/result version;
- marks current adopted result;
- keeps failed and expired versions visible;
- selection changes only the current adopted marker.

## Rerun Drawer

The rerun drawer opens from a failed, expired, or unsatisfactory result.

Allowed override controls:

```text
Prompt override
negative prompt override
asset override
mode override
duration override
```

Rules:

- source job and source result are always visible;
- original job and original result are retained;
- empty override fields mean reuse source values;
- creating a rerun creates a new job attempt;
- no field outside the approved override set is editable;
- override controls are rendered only when supported by backend provider capability/API schema.

Asset override details:

- reuse the M2 Asset Picker surface and thumbnail language;
- show only usable assets;
- filter by asset category (`character_reference`, `character_outfit`, `scene_reference`, `scene_angle`, `prop_reference`, `shot_keyframe`);
- show current asset versus replacement candidate before submit;
- persist exact replacement asset IDs, not labels or URLs;
- run provider reachability validation before enabling `创建重跑任务`;
- if reachability fails, keep the selected replacement visible and show the normalized error category.

Drawer behavior:

- desktop drawer width is fixed to the shared drawer token and opens from the right;
- desktop drawer may cover part of the inspector only when the workspace reserves drawer width or the inspector remains reachable;
- at 1180px and below, the drawer stacks below the preview instead of covering the table;
- at 768px and below, the drawer is full-width, keeps actions at the bottom, and preserves table horizontal scroll above it.

Keyboard and accessibility:

- drawer uses `role="dialog"`, `aria-modal="true"`, a labelled title, and a description;
- desktop drawer uses `role="dialog"` and `aria-modal="true"`;
- at 1180px and below, drawer uses `role="region"` and removes `aria-modal`;
- opening the drawer moves focus to the drawer title or first editable field;
- `Esc` closes the drawer and returns focus to the invoking rerun action;
- `Tab` and `Shift+Tab` stay inside the drawer only while desktop modal semantics are active;
- narrow viewport drawer does not trap focus and scrolls into view when opened;
- table selection checkboxes have shot-specific accessible names;
- blocked rows expose disabled checkbox state and correction action text;
- row focus with `Enter` selects the row without toggling blocked checkboxes.
- row keyboard handling ignores events that originate from `button`, `input`, `select`, `textarea`, or `a`.

## Error And Recovery

Error display uses compact chips plus inline Alert details.

Retryable categories:

```text
rate_limited
provider_busy
timeout
result_expired
unknown_provider_error
```

Terminal or configuration categories:

```text
authentication
invalid_request
input_unreachable
generation_failed
submission_outcome_unknown
```

The UI does not decide backend retry semantics; it only labels recovery affordances based on API state.
