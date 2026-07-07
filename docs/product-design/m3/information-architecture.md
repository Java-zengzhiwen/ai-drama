# M3 Information Architecture

## Existing Routes

M3 keeps the existing route shell:

```text
/projects
/projects/:projectId
/projects/:projectId/chapters/:chapterId
/settings/agnes
```

No new global navigation is introduced.

## Chapter Workspace Tabs

```text
原文
剧本
分镜
资料与资产
Shot Prompt
Agnes 生成
结果与重跑
```

`Agnes 生成` and `结果与重跑` are unlocked only when Shot Prompt readiness allows video generation. Earlier tabs remain available and retain their M1/M2 behavior.

## Agnes 生成 Surface

Purpose: submit ready shots and monitor provider jobs.

Primary regions:

- generation toolbar;
- inline polling, RPM, and restart recovery notices;
- ready/blocked shot generation table;
- selected shot prompt and parameter preview;
- result preview inspector for the selected shot;
- rerun drawer entry when the selected job/result needs another attempt.

## 结果与重跑 Surface

Purpose: review completed or failed shot results and create explicit reruns.

Primary regions:

- shot result list;
- non-autoplay video preview;
- result version strip;
- current adopted result marker;
- source Prompt, source assets, Job, and attempt metadata;
- failure category review;
- rerun drawer with approved overrides only.

## Primary Objects

Generation:

- ready shot;
- blocked shot;
- prompt revision;
- generation job;
- job attempt;
- provider job identifier;
- provider result URL;
- idempotency key status.

Results:

- generation result;
- result version;
- current selected result;
- result review;
- failure category;
- rerun record.

## UI State Vocabulary

Generation display states:

```text
waiting
queued
submitting
generating
completed
failed
cancelled
```

Result display states:

```text
success
failed
result_expired
current_selected
not_selected
```

Provider and recovery failure categories:

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
