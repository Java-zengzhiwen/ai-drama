# M3 Screen States

## Agnes 生成

### locked_no_current_shot_prompt_revision

`Agnes 生成` tab remains locked when no current Shot Prompt revision exists.

```text
请先生成或选择当前 Shot Prompt revision。
```

### empty_no_ready_rows

```text
暂无 ready 镜头。blocked 镜头仍会显示原因，但不可提交。
```

### loading

Keep Workflow Rail, chapter Tabs, notices, and table header visible. Use table skeleton rows and inspector skeletons.

### ready

Ready rows are selectable and can be submitted. Show the prompt revision, asset readiness, and only backend provider capability/API schema supported parameter fields.

### blocked

Blocked rows remain visible in the table with the blocker reason. Their selection checkbox is disabled and the row action routes back to Shot Prompt or 资料与资产.

Examples:

```text
缺少 Prompt
缺少资产（角色）
资产不可达
Shot Prompt 未 ready
```

### waiting

The shot is eligible but not submitted. Row action shows `提交`.

### queued

The job is persisted and waiting for Poller submission. Row action changes to `查看任务`; duplicate submit is disabled.

### submitting

Network submission is in progress. Row shows warning if provider job id is not yet known.

### generating

Provider job exists and polling is active. Row shows progress-style status and the polling notice stays visible.

### restart_recovery_in_progress

Startup recovery check is running for persisted `queued`, `submitted`, and `polling` jobs. The notice is polite, nonblocking, and does not move focus.

```text
restart_recovery_in_progress：启动后检查 queued/submitted/polling 任务。
```

### recovered_after_restart

Poller has reclaimed recoverable persisted jobs after app restart. UI shows recovered count and exception count.

```text
应用重启后已恢复 3 个未完成任务：2 个继续自动处理，1 个需要人工检查。
```

Rules:

- shown only after recovery check completes;
- can be dismissed by the user;
- dismissal does not stop Poller or React Query polling;
- does not hide row-level failures;
- does not hide `submission_outcome_unknown`.

### submission_outcome_unknown

A persisted `submitting` job has no provider job id after restart. It is not counted as `recovered_after_restart`.

```text
1 个任务状态无法确认，已标记为 submission_outcome_unknown。
```

### completed

Row shows `completed`, current result version if selected, and `打开结果`.

### failed

Row shows failure category and a rerun action. Prior attempts remain visible.

### cancelled

Row shows terminal cancelled status. It can be rerun only through explicit rerun if API permits.

## 结果与重跑

### no_results

`结果与重跑` remains locked until at least one `GenerationJob` exists.

```text
暂无视频结果。提交 Agnes 生成后会显示结果版本。
```

### preview_available

Show a paused video preview with visible controls and `不自动播放` helper text.

### multiple_versions

Show version strip with completed, failed, expired, and current adopted markers.

### result_selected

Inline success state:

```text
当前采用结果已更新。
```

### source_url_expired_local_result_available

Show warning:

```text
Provider source URL 已过期。本地保存结果仍可预览；保留原 Job 和历史结果，可基于源输入重跑。
```

### source_url_expired_local_result_missing

Show error:

```text
Provider source URL 已过期，且本地结果缺失。无法预览原视频；保留源 Prompt、资产 ID、Job 和 attempt，可创建重跑。
```

### rerun_drawer_open

Drawer shows source job, source assets, source prompt, approved override fields, and create/cancel actions.

Asset override state inside the drawer:

- reuses the M2 Asset Picker;
- lists only usable assets;
- filters by category;
- compares current and replacement assets;
- stores exact asset IDs;
- blocks submit until provider reachability validation passes.

Drawer accessibility state:

- drawer is a modal dialog on desktop with `role="dialog"` and `aria-modal="true"`;
- drawer is a nonmodal region at 1180px and below with `role="region"` and no `aria-modal`;
- `Esc` closes it;
- `Tab` and `Shift+Tab` remain inside it only in desktop modal mode;
- narrow viewport open scrolls the drawer region into view and does not trap focus;
- focus returns to the invoking action after close.

## Shared Errors

All errors include:

- short message;
- stable error category;
- retry or recovery action when available;
- no destructive reset as first action.

Categories:

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
