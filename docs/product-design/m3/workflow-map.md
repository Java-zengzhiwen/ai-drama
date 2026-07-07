# M3 Workflow Map

## Gate Sequence

```text
章节原文存在
-> 剧本 approved
-> 分镜 approved
-> current Shot Prompt revision exists
-> Agnes 生成 unlocked
-> at least one GenerationJob exists
-> 结果与重跑 unlocked
```

## Generation Flow

1. User enters the chapter workspace.
2. Workflow Rail marks `Agnes 生成` as available when a current Shot Prompt revision exists.
3. User opens `Agnes 生成`.
4. Ready and blocked shots appear in one generation table; asset usability is row-level readiness, not a tab unlock requirement.
5. User selects ready shots or uses a single-shot submit action; blocked shots remain visible but not selectable.
6. UI prevents duplicate submission while a request is in flight or an equivalent job already exists.
7. Submitted rows move through `waiting`, `queued`, `submitting`, and `generating`.
8. Polling indicator explains that nonterminal jobs refresh automatically.
9. Manual refresh remains available for one job or the whole chapter.
10. Completed rows expose result preview and current-result selection.
11. Failed rows expose failure category, source inputs, and rerun entry.

## Result And Rerun Flow

1. User opens `结果与重跑` or selects a completed/failed row from `Agnes 生成`.
2. The selected shot shows a paused video preview.
3. User reviews version history and source job details.
4. User marks one result as current adopted.
5. If a result failed or is unsuitable, user opens the rerun drawer.
6. Rerun drawer is prefilled from the source job.
7. User may override only approved fields that the backend provider capability/API schema supports:

```text
Prompt override
negative prompt override
asset override
mode override
duration override
```

8. Asset override reuses the M2 Asset Picker, filters to usable assets by category, stores exact replacement asset IDs, and validates provider reachability before submit.
9. Creating a rerun creates a new job and preserves the source job and prior result versions.

## Required Branches

### Blocked Shot

```text
shot row blocked
-> inline reason names prompt or asset blocker
-> action links back to Shot Prompt or 资料与资产
-> submit controls stay disabled
```

### Duplicate Submit

```text
ready shot submitted
-> row enters queued or returns existing job
-> submit button disables during mutation
-> duplicate click shows existing job context
```

### Polling And Recovery

```text
nonterminal job exists
-> polling notice visible
-> manual refresh available
-> restart recovery notice visible for queued/submitted/polling
-> submitting without provider id shows submission_outcome_unknown
```

### Result Expired

```text
provider result URL expired
-> result stays in version history
-> if local_result_available, preview uses local persisted video and labels provider source URL expired
-> if local_result_missing, preview is unavailable and rerun uses only saved source Prompt/assets/job metadata
-> rerun remains available when API state permits
```

## Locked Boundary

M3 screens must never offer editing controls for timeline, trimming, captions, audio, stitching, export, LibTV execution, or M4 acceptance.
