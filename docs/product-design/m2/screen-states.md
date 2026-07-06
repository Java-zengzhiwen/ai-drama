# M2 Screen States

## Production Profiles

### empty

```text
暂无 Profile。创建人物、场景、道具或风格资料后开始绑定资产。
```

### loading

Keep the Workflow Rail, chapter Tabs, and subview Tabs visible. Show row skeletons in the list and inspector skeletons on the right.

### normal

Profile list on the left, editor or summary inspector on the right.

### editing

Unsaved changes disable switching selected Profile unless the user confirms discard or saves.

### validation_error

Inline field errors plus a top Alert. Example:

```text
Character Profile 必须至少绑定一个 usable 的 character_reference。
```

### saved

Inline success Alert. No modal.

### delete_confirmation

Show destructive confirmation in the inspector:

```text
删除 Profile 后，已上传资产保留，但相关需求会重新标记 missing_assets。
```

## Asset Studio

### empty

```text
暂无资产。上传图片或通过 Agnes 生成参考图。
```

### loading

Show thumbnail skeletons and keep filters visible.

### normal

Image gallery first. Metadata appears as compact chips and inspector details.

### generating

Tile and detail page show `generating`; usable, reject, and set-current actions are disabled until result exists.

### generation_failed

Show error Alert with retry action. Preserve generation parameters.

### usable

Asset can be selected in asset_refs and can satisfy requirements.

### rejected

Asset remains visible in version history but cannot satisfy requirements.

### current adopted asset

Only one asset per binding role can show `当前采用`.

## Asset Requirement Analysis

Statuses:

- `ready`;
- `missing_assets`;
- `asset_generation_in_progress`;
- `asset_review_required`.

Each non-ready state exposes a direct action in the row.

## Shot Prompt Studio

### draft

Prompt exists but is not ready for downstream video generation.

### blocked_by_assets

Show missing or rejected asset refs and disable `标记 ready`.

### ready

Show success chip and allow future M3 video generation, but M3 tabs remain locked in M2.

### needs_revision

Show warning chip and keep edit/regenerate actions enabled.

## Locked M3 Screens

Agnes video and result/rerun screens show locked labels only:

```text
M2 仅支持图片资产和 Shot Prompt。视频生成、结果和重跑在 M3 解锁。
```
