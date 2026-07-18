# 当前设计系统

## 1. 总体视觉语言

M1 锁定了浅色、专业、信息密集的制作工作台；M2 和 M3 明确“继承且不引入新视觉系统”。M1–M3 构成核心 UI 基线。相邻扩展 M6D 的视觉规范继续使用同一语言，但 M6D 不属于章节主流程。

M4 rehearsal 可见性和 M6D 均只作为相邻继承与扩展证据：前者证明现有生成/结果区域可增加工程可见性，后者证明视觉系统可延展到全局管理工作台；两者都不进入 M1–M3 核心设计包。

- 浅色页面背景 `#f6f8fb`，主要工作面 `#ffffff`，次级表面 `#f9fafc`。
- 细边框和轻微背景层次优先，避免卡片套卡片和重阴影。
- 主操作/焦点蓝 `#2563eb`；成功 `#16a34a`；警告 `#d97706`；错误 `#dc2626`。
- 设计语气是生产工具，不是营销 Dashboard、无限画布或视频编辑器。

## 2. 已明确的 Token

### 颜色

| Token | 值 |
| --- | --- |
| `page.background` | `#f6f8fb` |
| `surface.default` | `#ffffff` |
| `surface.subtle` | `#f9fafc` |
| `border.default` | `#d9dee8` |
| `border.strong` | `#b8c0cc` |
| `text.primary` | `#1f2937` |
| `text.secondary` | `#5f6b7a` |
| `text.muted` | `#8a94a3` |
| `accent.focus` | `#2563eb` |
| `status.success` | `#16a34a` |
| `status.warning` | `#d97706` |
| `status.error` | `#dc2626` |
| `status.info.bg` | `#dbeafe`（M2 起） |
| `status.blocked.bg` | `#fff1f2` |
| `status.blocked.border` | `#fca5a5` |

### 字体

```text
font.family   Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
body.size     14px
body.line     1.45
label.size    12px
title.size    18px
heading.size  22px
```

### 间距与圆角

```text
space.1  4px
space.2  8px
space.3  12px
space.4  16px
space.5  20px
space.6  24px

radius.sm  4px
radius.md  6px
radius.lg  8px
```

不存在已锁定的阴影 Token。原始文档只规定优先使用边框和轻微表面色；不得自行补造 Shadow 系统。

## 3. 页面布局基线

| 布局元素 | 基线规则 |
| --- | --- |
| 应用 Shell | 顶部应用栏 + 左侧项目/章节 Rail + 中央工作区；后续阶段不得重做 Shell |
| Workflow Rail | 在章节工作区顶部持续显示生产 Gate、当前步骤与阻断原因 |
| Chapter Tabs | 以固定顺序承载阶段；锁定项显示标签和原因，不创建隐藏的新路由体系 |
| 主编辑区 | 根据任务切换为文本编辑、密集表格、大图预览或结果预览 |
| Inspector | 选择对象的详情、QC、版本和决策动作；承担“判断”而非装饰信息 |
| Drawer | M3 重跑使用；桌面 360px，1180px 及以下堆叠，768px 全宽 |
| Notice | 与受影响操作/表格相邻；状态变化不依赖成功弹窗 |
| 表格 | 高密度、稳定行高、行分隔、必要时 sticky header/横向滚动 |
| 预览区 | M2 图片审查大图主导；M3 视频是 16:9 决策面，不是编辑面 |

## 4. 媒体比例基线

```text
asset.tile.thumbnail     4:3，最小 176px 宽
asset.detail.preview     4:3，填充主内容列
asset.version.thumbnail  4:3，最小 120px 宽
asset.ref.thumb          54px × 54px
shot.keyframe.thumb      16:9
outfit.reference         3:4
result.preview.video     16:9
result.version.thumbnail 16:9，最小 96px 宽
drawer.width.desktop     360px
```

实际 Provider 像素尺寸不是视觉 Token；只有后端 capability/API schema 明确支持时才展示参数。

## 5. 组件基线

| 组件 | 使用位置/用途 | 继承阶段 | QA 状态 | 后续复用 |
| --- | --- | --- | --- | --- |
| Workflow Rail | 章节生产进度和 Gate | M1 | M1 无独立 QA；M2/M3 QA 中延续 | 必须复用 |
| Chapter Tabs | 阶段导航与锁定态 | M1 | M2/M3 QA | 必须复用 |
| Dense Table | 分镜、需求、Prompt、生成任务 | M1 | M2/M3 QA | 必须复用，连续性审核也应表格优先 |
| Status Chip | 紧凑显示流程、资产、Job、结果状态 | M1 | M2/M3 QA | 必须复用 |
| Inspector | 当前对象详情、QC、决策 | M1 | M2/M3 QA | 必须复用 |
| Asset Preview | 资产列表缩略图和详情大图 | M2 | M2 QA 通过 | 连续性参考和 Provider 输入继续复用 |
| Version Strip | 资产版本或结果版本 | M2 | M2/M3 QA | 继续复用，保持历史可见 |
| Notice Bar | Gate、错误、轮询、RPM、恢复 | M1/M3 | M3 QA 通过 | 异步流程必须复用 |
| Rerun Drawer | 保留源任务的新任务覆盖项 | M3 | 三视口与键盘 QA 通过 | 仅重跑/修复型任务复用 |
| Action Footer | Drawer 底部重置/取消/创建 | M3 | M3 QA 通过 | 表单型 Drawer 复用 |
| Empty State | 无项目、无原文、无资产、无结果 | M1 | 文档覆盖；M2/M3 原型部分覆盖 | 复用文案结构 |
| Loading State | 保留 Shell/Rail/Tab，内容用 Skeleton | M1 | 文档覆盖；非完整视觉 QA | 复用行为 |
| Error State | 短标题、稳定错误码/分类、恢复动作 | M1 | M2/M3 QA | 复用，默认不提供破坏性重置 |
| Blocked State | 阻断项仍可见，原因贴近禁用动作 | M1 | M2/M3 QA | 生产 Gate 核心模式 |
| Prompt Gate Summary | Prompt 是否 ready 及原因 | M2 | M2 QA | Provider 提交前继续复用 |
| Result Preview | 暂停视频、源 Job、版本和采用动作 | M3 | M3 QA | 连续性审核的当前片段区可复用 |

## 6. Shared UI Contract

以下公共结构和组件构成后续 Product Design 的默认继承合同：

```text
Application Shell
Project / Chapter Rail
Workflow Rail
Chapter Tabs
Dense Table
Status Chip
Inspector
Asset Preview
Media / Result Preview
Version Strip
Notice Bar
Drawer
Action Footer
Loading State
Empty State
Error State
Blocked State
```

1. 后续 Product Design 必须优先复用这些组件和交互语言。
2. 新模块不得无理由创建第二套 Application Shell。
3. 表格型任务不得默认改成卡片墙。
4. 审核决定优先进入 Inspector。
5. 显式修改、重跑和修复优先使用 Drawer。
6. 资产和媒体版本必须保留历史，并明确当前采用版本。
7. Blocked 对象继续可见，但操作被禁用并显示行内原因。
8. 窄屏优先堆叠和横向滚动，不把密集生产数据强制变成嵌套卡片。
9. 新增组件时，设计文档必须解释现有 Shared UI Contract 为什么不足。
10. 未来 PD-C1、PD-P1、PD-D1 均应继承该 Contract。

## 7. 交互密度与层级

- 主操作按钮只用于创建、确认、提交或明确采用；刷新、筛选、返回和查看属于次级动作。
- 成功默认使用页面内反馈，不要求模态框。
- 阻断原因要在行内或受影响操作旁出现，不能藏在 Modal。
- 版本和历史不被新操作覆盖；当前采用通过标记表达。
- 右侧 Inspector/Drawer 承担复杂决策，主表保持扫描效率。

## 8. 响应式基线

| 视口 | 已有证据 | 表格 | Inspector/预览 | Drawer | 焦点/阅读顺序 |
| --- | --- | --- | --- | --- | --- |
| 1440×1024 | M3 原型与 QA；M2 1440 全页原型 | 桌面密集表格 | 与主区并列 | 右侧 360px 模态，工作区预留宽度 | 打开后进入首个字段，桌面 Focus Trap，关闭回触发器 |
| 1180×800 | M3 原型与 QA | 表格优先、横向内容保持 | 预览在表格后 | 堆叠在预览下，不覆盖表格 | `role=region`，无 Focus Trap，打开后滚入视图 |
| 768×1024 | M3 原型与 QA | 水平滚动，不改成卡片堆叠 | 单栏，版本条横向滚动 | 全宽，Footer 动作换行 | 保持 Workflow Rail → Tabs → Notice → Table → Preview → Drawer 顺序 |

补充边界：

- M1 原型仅在 CSS 中写有 `max-width: 1100px` 时隐藏 Inspector，没有独立响应式截图或 QA；不能把它当成最终窄屏规则。
- M2 文档规定窄屏 Inspector 下移、Subnav/版本条横向滚动，但只留有 1440 视觉 QA；其窄屏规则属于设计规范，未留独立截图证据。
- M3 是 M1–M3 中唯一有三档视口、Drawer 语义和焦点行为完整 QA 的阶段，后续应以 M3 响应式规则为准。

## 9. 可访问性基线

- 动态轮询、恢复和未知提交状态使用分离的 polite live region，不抢焦点。
- 表格选择框和重跑按钮提供镜头级可访问名称；Blocked checkbox 禁用且说明不可提交。
- 行级 `Enter` 只选择行，不提交；行事件忽略嵌套按钮、输入、选择器、文本域和链接。
- 桌面 Drawer 是有标题/描述的模态 Dialog，窄屏改为非模态 Region。
- `Esc` 关闭；焦点进入和回归触发器；仅桌面模态时循环 Tab。
- 现有证据支持这些具体交互通过，不等同于整个生产产品已达到完整 WCAG 合规。

## 10. 主要证据

- [M1 Visual Tokens](../m1/visual-tokens.md)
- [M2 Visual Tokens](../m2/visual-tokens.md)
- [M3 Visual Tokens](../m3/visual-tokens.md)
- [M2 Design QA](../m2/design-qa.md)
- [M3 Design QA](../m3/design-qa.md)
- [M6D 视觉设计补充](../../superpowers/specs/2026-07-12-m6d-management-ui-visual-design.md)
