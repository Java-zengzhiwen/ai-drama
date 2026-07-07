# M3 Interaction Spec

## Navigation

M3 stays inside the existing chapter workspace.

- Top routes remain project and chapter based.
- Chapter Tabs carry the production stage.
- `Agnes 生成` owns submission and job monitoring.
- `结果与重跑` owns result review, selection, failure review, and rerun.
- No new global sidebar item is added.

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

- ready rows are selectable;
- blocked rows are visible but not selectable;
- batch submit submits only selected ready rows;
- single-shot submit is disabled when the selected shot is blocked or already has an active equivalent job;
- submitting state disables duplicate clicks;
- manual refresh is always secondary to automatic polling.

## Prompt, Assets, And Parameters Preview

The selected shot must show:

- positive prompt;
- negative prompt;
- asset reference thumbnails;
- generation mode;
- duration;
- provider-supported video parameters;
- source Shot Prompt revision.

The preview is read-only on `Agnes 生成`. Prompt edits stay in `Shot Prompt`; rerun overrides stay in the rerun drawer.

## Polling And Recovery Notices

Inline notices appear above the table:

```text
自动轮询中，每 5 秒刷新一次。
RPM 限制：队列会按速率提交。
应用重启后恢复 queued/submitted/polling 任务。
```

`submission_outcome_unknown` is shown as a warning state that requires user attention before rerun or manual resolution.

## Results Preview

Video preview behavior:

- never autoplay;
- show poster/first frame and native play control;
- show source job and attempt metadata near the preview;
- show result URL expiration separately from generation failure.

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
- no field outside the approved override set is editable.

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
