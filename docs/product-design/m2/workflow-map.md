# M2 Workflow Map

## Gate Sequence

```text
章节原文存在
-> 剧本 approved
-> 分镜 approved
-> 资料与资产 unlocked
-> required assets usable
-> Shot Prompt can become ready
-> Agnes 生成 remains locked in M2
-> 结果与重跑 remains locked in M2
```

## User Flow

1. User enters the chapter workspace after storyboard approval.
2. Workflow Rail marks `资料与资产` as current.
3. User opens `资料与资产`.
4. User creates or edits Profiles.
5. User uploads or generates image assets.
6. User opens an asset detail page to review large preview and versions.
7. User marks an asset usable, rejects it, or sets it as current adopted asset.
8. User runs asset requirement analysis.
9. Missing requirements link to asset creation or asset detail review.
10. Once required assets are usable, user opens `Shot Prompt`.
11. User generates or edits Shot Prompts.
12. User reviews positive prompt, negative prompt, continuity notes, asset refs, and Agnes parameter preview.
13. User saves a new Revision or marks a shot ready.

## Required Branches

### Missing Asset

```text
缺失需求行
-> 创建资产 / 上传图片 / Agnes 生成图片
-> asset detail review
-> mark usable
-> set current adopted
-> requirement updates to ready
```

### Rejected Asset

```text
asset detail
-> reject
-> enter rejection reason
-> related requirement remains missing_assets
-> Shot Prompt stays blocked_by_assets
```

### Asset Generation In Progress

```text
Agnes image generation submitted
-> asset status generating
-> detail page shows read-only generation state
-> user cannot mark usable until result exists
```

### Prompt Blocked

```text
Shot Prompt row
-> blocked_by_assets
-> asset refs panel names missing asset
-> jump to asset requirement or asset detail
```

## Locked M2 Boundary

`Agnes 生成` and `结果与重跑` remain visible but disabled. Their lock reason:

```text
M2 仅支持图片资产与 Shot Prompt，视频生成与结果重跑在 M3 解锁。
```
