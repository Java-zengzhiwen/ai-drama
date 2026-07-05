# M1 Screen States

## Loading

Project list:

- show table skeleton rows;
- keep create project action visible but disabled if submission is active.

Chapter workspace:

- keep rail and tabs visible;
- use row skeletons inside the active tab;
- do not hide the current workflow rail.

## Empty

Project list:

```text
暂无项目。创建项目后开始章节制作。
```

Source tab:

```text
暂无小说原文。粘贴正文后才能生成剧本。
```

Script tab:

```text
暂无剧本。保存原文后生成剧本。
```

Storyboard tab:

```text
暂无分镜。确认剧本后生成分镜。
```

## Error

Error surfaces must include:

- short error title;
- stable error code when available;
- retry action;
- no destructive reset action.

Example:

```text
分镜加载失败。请重试。
```

## Blocked

Script gate:

```text
未确认剧本，不允许生成分镜。
```

Storyboard gate:

```text
未确认分镜，不允许进入后续生产步骤。
```

Blocked state should appear next to the blocked action and in the workflow rail.

## Success

Confirmation success should update:

- workflow rail;
- chapter status;
- active tab status chip;
- right inspector gate summary.

No modal is required for success; inline confirmation is enough.
