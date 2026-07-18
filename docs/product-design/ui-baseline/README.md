# UI 事实基线档案

本目录汇总仓库中已经存在的 M1、M2、M3 Product Design 资料，供后续设计、实现和审阅直接继承。它回答“已经确认了什么、哪些证据存在、哪些能力仍缺失”，不提出新的页面方向，也不替代原始设计文件。

## 审阅范围

- 完整审阅 `docs/product-design/m1/`、`m2/`、`m3/` 下的 Markdown、HTML 和 PNG。
- 核对静态原型是否联网、使用何种数据以及有哪些本地交互。
- 检索仓库中散落的 UI 资料；将 M4 rehearsal 可见性和 M6D 供应商管理资料作为相邻继承与扩展证据单独记录，不纳入 M1–M3 核心设计包。
- 只读查看当前生产路由、组件和测试名称，用于区分“设计事实”与“已有生产实现证据”；本次没有重新运行完整生产验收。

## 状态摘要

```text
M1：项目、项目看板、章节工作台、原文、剧本、分镜与确认 Gate 已设计；有静态原型和选定方向图，无独立 Design QA。
M2：继承 M1，扩展 Profiles、视觉资产、缺失需求与 Shot Prompt；有静态原型、选定方向图和通过的 Design QA。
M3：继承 M1/M2，解锁 Agnes 生成、任务状态、结果版本与显式重跑；有响应式静态原型和通过的交互/可访问性 Design QA。
核心 UI 基线：M1–M3，以单项目、单章节工作台为中心，从原文到视频结果与重跑。
相邻继承与扩展证据：M4 rehearsal 可见性、M6D 模型供应商与项目模型绑定；两者不属于 M1–M3 核心设计包。
主要未覆盖范围：连续性 Observed State 审核、多 Provider 生成对比、LibTV/Seedance 执行、后期制作与发布。
```

M4 rehearsal 可见性是在现有生成/结果区域增加的工程可见性扩展，不等同于 Planned/Observed 连续性审核。M6D 是独立的全局供应商、模型与项目绑定管理工作台；它继承 M1–M3 的视觉系统，但不是章节主流程，也不代表多 Provider 生成中心已经完成。

## 文件导航

1. [现有资产清单](01-existing-assets-inventory.md)
2. [当前信息架构](02-current-information-architecture.md)
3. [当前设计系统](03-current-design-system.md)
4. [页面与功能覆盖](04-screen-and-feature-coverage.md)
5. [交互与状态基线](05-interaction-and-state-baseline.md)
6. [已锁定决策](06-locked-decisions.md)
7. [缺口与下一里程碑](07-gaps-and-next-milestones.md)
8. [来源证据索引](08-source-evidence-index.md)
9. [最终汇总报告](ui-baseline-report.md)

## 后续使用规则

- 后续 Product Design 默认延续 M1 的章节工作台、M2 的图片审查语言和 M3 的异步任务/结果语言。
- 新设计先查 [已锁定决策](06-locked-decisions.md)，不得因临时 MVP 页面样式不同而重做已确认方向。
- 严格区分“已设计”“已有静态原型”“已有 Design QA”“存在生产实现证据”“当前生产实现已重新验证”。仓库中存在路由、组件或历史测试时，只能说明存在生产实现证据；本次未重跑生产验收，统一标为“本次未重新验证”。
- 生产实现证据：仓库中存在与相关阶段对应的生产路由、组件、测试和历史里程碑记录。本次仅进行只读证据检查，未重跑生产验收，因此不将其重新判定为当前已验证完成。

## 双轨证据优先级

### 视觉目标证据优先级

```text
最新通过的 Product Design QA
> 用户批准的视觉目标
> selected-direction
> information architecture / interaction specification
> 早期探索方向图
> 普通需求或设想
```

判断页面应该长什么样时，优先依据最新 Design QA 和用户批准方向。临时生产前端不自动覆盖已批准视觉目标；早期方向图与后续 QA 冲突时，以后续 QA 为准。

### 运行事实证据优先级

```text
当前重新执行的生产验证结果
> 当前代码、测试和 E2E 证据
> 当前路由和组件只读证据
> 历史里程碑或提交记录
> 静态原型
```

判断功能当前是否真实可运行时，不能只依据静态原型。历史完成记录不等于当前分支已重新验证；没有重跑测试时必须标为“本次未重新验证”。

> 本目录是现有设计事实基线，不是新的设计方案。
