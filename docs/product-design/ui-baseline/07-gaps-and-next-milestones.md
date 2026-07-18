# 缺口与下一里程碑

## 1. 结论

不需要推翻 M1–M3。当前最明显的流程断点位于“视频结果/重跑”之后：系统能生成并采用片段，却没有把计划连续性与实际片段首尾状态进行审核和修复的 Product Design。

本文件仍以 M1–M3 为核心 UI 基线；M4 rehearsal 可见性和 M6D 仅是相邻继承与扩展证据。M4 不等同连续性审核，M6D 不等同多 Provider 生成体验。

推荐顺序：

```text
PD-C1：视频连续性审核与 Canon 状态
→ PD-P1：多 Provider 生成体验
→ PD-D1：后期与发布
```

英文名称分别为 `PD-C1 Continuity Review`、`PD-P1 Multi-Provider Generation`、`PD-D1 Post-production and Delivery`。推荐未来目录为 `docs/product-design/continuity-review/`、`docs/product-design/multi-provider-generation/`、`docs/product-design/post-production-delivery/`；本次不创建目录，也不启动下一阶段设计。

## 2. 平台级缺口

| 缺口 | 当前证据 | 影响 | 建议时机 |
| --- | --- | --- | --- |
| 登录和账户 | M1–M3 未覆盖，本地单用户被视为既定上下文 | 暂不影响本地单用户主流程 | 需要远程/多人时再设计 |
| 新建项目完整流程 | M1 只有 IA、空态和项目列表，没有表单/向导 | 首次使用入口不完整 | 可作为轻量补充，不应阻挡 PD-C1 |
| 项目创建向导 | 未覆盖 | Series Canon、制作简述、章节导入缺少统一入口 | 与项目级 Canon 总控一起设计 |
| 全局 Dashboard | 明确未建立 | 无跨项目健康概览 | 有多个活跃项目后再验证需求 |
| 跨项目任务中心 | 未覆盖 | 无全局 queued/failed/attention 聚合 | 多 Provider/批量生产后再设计 |

## 3. 项目级缺口

| 缺口 | 当前覆盖 | 需要补充 |
| --- | --- | --- |
| 项目级人物/场景/道具资产库 | M2 只在章节 Shell 内做 Profiles/资产 | 跨章节资产索引、引用来源、当前 Canon 版本 |
| 跨章节资产复用 | 只有章节内 binding | 复用、分叉、冲突和更新影响范围 |
| 世界观与风格总控 | M2 有最小 StyleProfile 概念 | Series Canon、视觉风格、时代/地域规则和下游继承 |
| 服装与状态时间线 | M2 只有 outfit asset 和 continuity notes | 按章/场/镜状态、换装节点、污损/道具持有状态 |

这些能力与连续性审核高度相关。PD-C1 首轮只定义完成连续性判断所需的最小 Canon/状态显示与记录边界，不在本阶段建设完整项目级资产库或复杂 Canon 图数据库。

## 4. 视频生成缺口

| 缺口 | 当前覆盖 | 需要补充 |
| --- | --- | --- |
| 多 Provider | 相邻 M6D 已设计供应商、模型和项目绑定配置，并存在后续实现证据 | 生成时的 Provider/模型解析可见性、能力差异、结果归一化 |
| LibTV | M1–M3 明确延后 | 提交、任务状态、结果/错误与 Canvas/CLI 边界 |
| Seedance | 未覆盖 | 模型能力、输入资产、参数、轮询和结果映射 |
| Provider 对比 | 未覆盖 | 同镜候选结果、成本/耗时/质量证据、采用决策 |
| Provider-neutral Clip Contract | M3 有 capability 边界和通用 Job/Result 语言 | 统一 Clip 输入、输出、状态、版本和审查契约的 UI 表达 |

M6D 是独立的全局供应商、模型与项目绑定管理工作台，继承 M1–M3 的视觉系统但不属于章节主流程。它已有独立设计与后续实现证据，却没有解决“在生成工作台如何查看实际解析到哪个 Provider/模型，如何比较结果”，因此不能用它证明多 Provider 生成体验已经完成。本次也未重新验证其生产实现。

## 5. 连续性审核缺口

当前只有：

- Storyboard 的 `continuity_in`/`continuity_out`；
- M2 的资产一致性检查和 `continuity_notes`；
- M3 的结果预览、版本、采用与重跑。

尚无以下视频事实层：

```text
Planned Start State
Planned End State
Observed Start State
Observed End State
前镜尾帧 vs 当前首帧
人脸 / 服装 / 站位 / 道具 / 场景审核
accept
accept_with_deviation
repair
reject
repair_tail
reanchor_after_drift
extension_depth
```

这也是推荐 PD-C1 优先的原因：它把已有 Storyboard/资产/Prompt 计划状态与 M3 实际视频结果闭环。M4 rehearsal 可见性只是生成/结果区域的工程可见性扩展，不等同于这个 Planned/Observed 连续性审核闭环。

## 6. 后期与发布缺口

以下均无 Product Design，M2/M3 对其中多数明确延后：

```text
视频拼接
旁白
BGM
字幕
调色
封面
平台导出/发布
抖音
红果
发布物料
版权资料
```

后期设计不应直接把 M3 结果页变成复杂时间线。应先明确“采用片段集合”的稳定输入，再决定最小后期工作台。

## 7. PD-C1：视频连续性审核与 Canon 状态

### 目标

让用户在采用片段进入后期前，对每镜 Planned/Observed 首尾状态作出可追溯判断，并明确下一步动作。

### 首轮设计范围

```text
打开已生成镜头
→ 查看前镜当前采用结果的尾帧
→ 查看当前镜首帧与尾帧
→ 查看 Planned Start / End
→ 记录 Observed Start / End
→ 展示连续性问题
→ 用户作出决定
   ├── accept
   ├── accept_with_deviation
   ├── repair
   └── reject
→ 给出下一步动作
```

首轮可继续使用章节 Tab、Dense Table、Media / Result Preview、Inspector 和 Drawer 表达上述流程，但这些只是既有 Shared UI Contract 的复用建议，不是本次启动的新页面设计。

### 与 M1–M3 连接点

- 读取 M1 Storyboard continuity 字段。
- 复用 M2 人物/服装/场景/道具资产与版本条。
- 读取 M3 当前采用结果、视频预览、源 Job/attempt 和重跑入口。

### 首轮暂不包含

```text
自动人脸识别模型实现
自动视频理解模型实现
完整视频时间线
多 Provider 对比
后期剪辑
自动修复执行
Seedance 专用完整参数
复杂 Canon 图数据库
```

### 设计启动前依赖

- Planned/Observed 状态模型与 revision 规则。
- 视频首尾帧提取或持久化契约。
- 连续性决策和偏差记录的数据契约。
- 采用结果必须稳定、可追溯。

### 风险

- 把连续性审核误做成通用视频 QC 或完整后期编辑器。
- Observed State 自动推断不可靠却被当成事实。
- repair/reanchor 语义未冻结就暴露过多高级动作。

### 可复用组件

Dense Table、Status Chip、Inspector、Asset Preview、Result Preview、Version Strip、Notice Bar、Rerun Drawer、Blocked/Error State。

## 8. PD-P1：多 Provider 生成体验

### 目标

在保留章节表格优先工作流的前提下，支持 Agnes、Seedance、LibTV 或其他 Provider 的能力解析、提交、状态归一化和结果比较。

### 建议页面

- 扩展现有 `Provider 生成` Tab（可重新命名 Agnes 生成，但需单独确认迁移文案）。
- 行级已解析 Supplier/Model/Capability 标签。
- Provider-neutral 参数预览和不可用原因。
- 同镜候选结果比较 Inspector/版本条。
- 章节级 Provider 过滤和异常任务视图，而非新建全局 Dashboard。

### 与现有连接点

- 复用 M3 Generation Table、Polling Notice、Failure Chip、Result Preview 和 Rerun Drawer。
- 读取 M6D 项目模型绑定，不在生成页重复配置 API Key/Base URL。
- 在 Shot Prompt 之后插入 Provider 执行，结果仍流向现有结果/重跑与 PD-C1 连续性审核。

### 依赖

- Provider-neutral Clip Contract。
- 各 Provider capability/schema 与状态/失败归一化。
- 项目绑定解析与 ExecutionSnapshot 可见性。
- Seedance/LibTV Adapter 及假 Provider 验证。

### 风险

- 把 Provider 差异泄漏成大量硬编码控件。
- 在生成页重复 M6D 配置职责。
- Provider 比较把“候选版本”与“当前采用”语义弄乱。

### 可复用组件

Generation Table、Notice Bar、Status Chip、Result Preview、Version Strip、Rerun Drawer、M6D 模型 Inspector 和 capability 标签。

## 9. PD-D1：后期与发布

### 目标

把已通过连续性审核的采用片段组合为可发布成片，并管理音频、字幕、封面和发布物料。

### 建议页面

- 章节/成片组装工作台。
- 采用片段清单与最小顺序/转场控制。
- 旁白、字幕、BGM、调色状态面板。
- 封面与发布物料清单。
- 平台导出/发布检查单和版权资料面板。

### 与现有连接点

- 输入来自 PD-C1 通过的当前采用结果集合。
- 复用 M3 结果预览、版本/采用语言和 Notice/Error。
- 不修改 M3 原始 Job/Result；后期产物应有自己的 revision。

### 依赖

- 成片/时间线最小数据契约。
- 媒体处理、字幕/音频、导出和发布目标契约。
- 版权和平台规格。

### 风险

- 一次性构建完整 NLE 导致范围失控。
- 发布平台规则快速变化。
- 后期 revision 与原视频结果追溯断裂。

### 可复用组件

Version Strip、Result Preview、Dense Table、Status Chip、Inspector、Notice Bar、Action Footer。

## 10. 推荐下一步

下一阶段优先级保持为 `PD-C1 Continuity Review`。正式启动时，先冻结最小状态词汇和一条“前镜尾帧 → 当前首帧 → Planned/Observed → 判断 → 下一步动作”的用户流程，再进入 Product Design 视觉探索。Seedance 应在未来 Provider 生成层接入；连续性系统应位于结果与重跑之后、后期之前。本次只记录范围，不启动 PD-C1。
