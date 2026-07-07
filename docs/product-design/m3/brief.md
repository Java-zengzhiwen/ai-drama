# M3 Product Design Brief

## Scope

Milestone 3 covers Agnes video generation, persistent job visibility, video result review, result version selection, and explicit rerun inside the existing chapter workspace.

This sprint is design-only. It must not modify production React code, FastAPI code, database schema, Provider, Poller, API routes, migrations, or tests.

## User Goal

A local single user can submit ready Shot Prompt shots to Agnes Video, monitor asynchronous jobs, recover context after restart, preview generated clips without autoplay, select the current adopted result, and create a rerun without overwriting prior jobs or results.

## Product Shape

M3 extends the M1/M2 **Storyboard Command Table** and M2 asset review language. It does not redesign the product shell.

Inherited structure:

- top app bar;
- left project and chapter rail;
- Workflow Rail;
- chapter Tabs;
- compact table rows;
- compact status chips;
- inline Alerts for gates, errors, and recovery;
- right inspector or drawer for selected-item decisions;
- primary, secondary, danger, retry, and refresh button hierarchy.

Selected M3 direction:

**Generation Command + Result Preview**

The main surface keeps a clear ready-shot generation table from direction 1, while the selected-shot side panel adopts direction 3's stronger result preview, version strip, source job metadata, and rerun drawer.

## M3 Boundary

M3 unlocks:

```text
Agnes 生成
结果与重跑
```

M3 must not design or imply:

```text
LibTV
配音
字幕
BGM
视频剪辑
时间线
成片导出
多人协作
M4 验收页面
```

## Prototype

Open the static prototype:

```text
docs/product-design/m3/assets/prototype.html
```

Selected direction image:

```text
docs/product-design/m3/assets/selected-direction-generation-command-result-preview.png
```
