# M3 Screen States

## Agnes 生成

### empty

```text
暂无 ready 镜头。请先在 Shot Prompt 标记镜头 Ready。
```

### loading

Keep Workflow Rail, chapter Tabs, notices, and table header visible. Use table skeleton rows and inspector skeletons.

### ready

Ready rows are selectable and can be submitted. Show the prompt revision, asset readiness, mode, duration, and preview summary.

### blocked

Blocked rows remain visible in the table with the blocker reason.

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

### completed

Row shows `completed`, current result version if selected, and `打开结果`.

### failed

Row shows failure category and a rerun action. Prior attempts remain visible.

### cancelled

Row shows terminal cancelled status. It can be rerun only through explicit rerun if API permits.

## 结果与重跑

### no_results

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

### result_expired

Show warning:

```text
结果 URL 已过期。保留原 Job 和历史结果，可基于源输入重跑。
```

### rerun_drawer_open

Drawer shows source job, source assets, source prompt, approved override fields, and create/cancel actions.

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
