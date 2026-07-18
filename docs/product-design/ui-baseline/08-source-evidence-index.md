# 来源证据索引

## 1. M1 证据

| 证据路径 | 阶段 | 支持的结论 | 最终方向 | 经过 QA |
| --- | --- | --- | --- | --- |
| `docs/product-design/m1/brief.md` | M1 | 单用户从原文到 approved Storyboard；范围和 Gate | 否 | 否 |
| `docs/product-design/m1/information-architecture.md` | M1 | 三条核心路由、项目列表/看板/章节工作台 | 否 | 否 |
| `docs/product-design/m1/interaction-spec.md` | M1 | 导航、Tab、确认和分镜表交互 | 否 | 否 |
| `docs/product-design/m1/screen-states.md` | M1 | Loading/Empty/Error/Blocked/Success 语言 | 否 | 否 |
| `docs/product-design/m1/selected-direction.md` | M1 | Storyboard Command Table 为选定方向 | 是 | 否 |
| `docs/product-design/m1/visual-tokens.md` | M1 | 浅色工作台 Token、密度、圆角和组件规则 | 否 | 否 |
| `docs/product-design/m1/assets/prototype.html` | M1 | 静态 Mock 项目/章节/原文/剧本/分镜交互 | 是 | 否 |
| `docs/product-design/m1/assets/selected-direction-storyboard-command-table.png` | M1 | 左 Rail、顶部流程、分镜表、右 Inspector 视觉方向 | 是 | 否 |

## 2. M2 证据

| 证据路径 | 阶段 | 支持的结论 | 最终方向 | 经过 QA |
| --- | --- | --- | --- | --- |
| `docs/product-design/m2/brief.md` | M2 | M2 扩展 M1，范围是 Profiles/资产/需求/Prompt | 否 | 是 |
| `docs/product-design/m2/information-architecture.md` | M2 | 章节内路由、Tabs、Subviews 和对象 | 否 | 是 |
| `docs/product-design/m2/selected-direction.md` | M2 | Asset Detail Review Page 锁定决策 | 是 | 是 |
| `docs/product-design/m2/design-qa.md` | M2 | 原型 QA 通过，P0–P2 无未结项 | 否 | 是 |
| `docs/product-design/m2/implementation-handoff.md` | M2 | 路由、组件、Gate、响应式和 Must Not Change | 否 | 是 |
| `docs/product-design/m2/interaction-spec.md` | M2 | 资产、Profile、需求、Prompt 交互 | 否 | 是 |
| `docs/product-design/m2/screen-states.md` | M2 | Profile、Asset、Requirement、Prompt 状态 | 否 | 是 |
| `docs/product-design/m2/visual-tokens.md` | M2 | 继承 M1 并锁定媒体比例/布局 | 否 | 是 |
| `docs/product-design/m2/component-inventory.md` | M2 | M1 复用与 M2 新组件 | 否 | 是 |
| `docs/product-design/m2/workflow-map.md` | M2 | 分镜到资产和 Prompt 的 Gate 分支 | 否 | 是 |
| `docs/product-design/m2/assets/prototype.html` | M2 | 六个静态子视图、Mock 数据和本地视图切换 | 是 | 是 |
| `docs/product-design/m2/assets/selected-direction-asset-detail-review-page.png` | M2 | 大图优先、版本条、Inspector 和需求表 | 是 | 是 |
| `docs/product-design/m2/assets/prototype-detail-screenshot.png` | M2 | 1440 宽资产详情原型实现 | 否 | 是 |
| `docs/product-design/m2/assets/design-qa-comparison.html` | M2 | 可打开的源图/原型并列比较 | 否 | 是 |
| `docs/product-design/m2/assets/design-qa-comparison.png` | M2 | 全页源图与静态原型比较 | 否 | 是 |
| `docs/product-design/m2/assets/asset-character-reference.png` | M2 | 人物参考预览使用真实位图而非占位框 | 否 | 是 |
| `docs/product-design/m2/assets/asset-character-outfit.png` | M2 | 3:4 服装参考素材 | 否 | 是 |
| `docs/product-design/m2/assets/asset-scene-reference.png` | M2 | 16:9 场景参考素材 | 否 | 是 |
| `docs/product-design/m2/assets/asset-scene-angle.png` | M2 | 16:9 场景机位素材 | 否 | 是 |
| `docs/product-design/m2/assets/asset-prop-reference.png` | M2 | 4:3 道具参考素材 | 否 | 是 |
| `docs/product-design/m2/assets/asset-shot-keyframe.png` | M2 | 16:9 镜头关键帧素材 | 否 | 是 |

## 3. M3 证据

| 证据路径 | 阶段 | 支持的结论 | 最终方向 | 经过 QA |
| --- | --- | --- | --- | --- |
| `docs/product-design/m3/brief.md` | M3 | 生成、持久任务、结果、采用和重跑范围 | 否 | 是 |
| `docs/product-design/m3/information-architecture.md` | M3 | 生成/结果页面、对象和恢复状态词汇 | 否 | 是 |
| `docs/product-design/m3/selected-direction.md` | M3 | Generation Command + Result Preview 锁定决策 | 是 | 是 |
| `docs/product-design/m3/design-qa.md` | M3 | 三视口视觉/交互/可访问性 QA 通过 | 否 | 是 |
| `docs/product-design/m3/implementation-handoff.md` | M3 | Job 映射、轮询、结果、重跑、响应式、可访问性 | 否 | 是 |
| `docs/product-design/m3/interaction-spec.md` | M3 | 提交、恢复 Notice、结果和 Drawer 行为 | 否 | 是 |
| `docs/product-design/m3/screen-states.md` | M3 | GenerationJob、结果、恢复和 Drawer 状态 | 否 | 是 |
| `docs/product-design/m3/visual-tokens.md` | M3 | 视频 16:9、版本缩略图和 Drawer 尺寸 | 否 | 是 |
| `docs/product-design/m3/component-inventory.md` | M3 | 生成/结果/Notice/Drawer 组件与禁区 | 否 | 是 |
| `docs/product-design/m3/workflow-map.md` | M3 | Gate、提交、恢复、过期和重跑流程 | 否 | 是 |
| `docs/product-design/m3/assets/prototype.html` | M3 | 静态生成表、结果预览、恢复模拟和 Drawer | 是 | 是 |
| `docs/product-design/m3/assets/selected-direction-generation-command-result-preview.png` | M3 | 选定的表格 + 预览 + 重跑方向 | 是 | 是 |
| `docs/product-design/m3/assets/prototype-screenshot.png` | M3 | 桌面原型截图；与 1440 命名文件逐字节相同 | 否 | 是 |
| `docs/product-design/m3/assets/prototype-screenshot-1440x1024.png` | M3 | 1440 桌面 + 360px Drawer | 否 | 是 |
| `docs/product-design/m3/assets/prototype-screenshot-1180x800.png` | M3 | 1180 表格优先状态 | 否 | 是 |
| `docs/product-design/m3/assets/prototype-screenshot-1180x800-drawer.png` | M3 | 1180 非模态堆叠 Drawer | 否 | 是 |
| `docs/product-design/m3/assets/prototype-screenshot-768x1024.png` | M3 | 768 单栏和表格横向滚动 | 否 | 是 |
| `docs/product-design/m3/assets/prototype-screenshot-768x1024-drawer.png` | M3 | 768 全宽 Drawer 与换行 Footer | 否 | 是 |
| `docs/product-design/m3/assets/prototype-recovery-in-progress-1440x1024.png` | M3 | 恢复检查中与 unknown 分离 | 否 | 是 |
| `docs/product-design/m3/assets/prototype-recovery-completed-1440x1024.png` | M3 | 恢复完成计数与 unknown 分离 | 否 | 是 |
| `docs/product-design/m3/assets/prototype-recovery-dismissed-1440x1024.png` | M3 | 关闭 recovered 后 polling/RPM/unknown 保留 | 否 | 是 |
| `docs/product-design/m3/assets/design-qa-comparison.png` | M3 | 桌面源图比较；与 1440 QA 文件逐字节相同 | 否 | 是 |
| `docs/product-design/m3/assets/design-qa-comparison-1440x1024.png` | M3 | 选定方向与 1440 原型比较 | 否 | 是 |
| `docs/product-design/m3/assets/design-qa-responsive-1180x800.png` | M3 | 1180 表格和 Drawer 比较 | 否 | 是 |
| `docs/product-design/m3/assets/design-qa-responsive-768x1024.png` | M3 | 768 单栏和 Drawer 比较 | 否 | 是 |
| `docs/product-design/m3/assets/design-qa-focused-preview-rerun.png` | M3 | 预览、重跑和关闭 Notice 聚焦 QA | 否 | 是 |
| `docs/product-design/m3/assets/design-qa-recovery-lifecycle.png` | M3 | 恢复 in-progress/completed/dismissed 生命周期 | 否 | 是 |
| `docs/product-design/m3/assets/asset-character-reference.png` | M3 | 复用 M2 位图；SHA-256 相同 | 否 | 是 |
| `docs/product-design/m3/assets/asset-character-outfit.png` | M3 | 复用 M2 位图；SHA-256 相同 | 否 | 是 |
| `docs/product-design/m3/assets/asset-scene-reference.png` | M3 | 复用 M2 位图；SHA-256 相同 | 否 | 是 |
| `docs/product-design/m3/assets/asset-scene-angle.png` | M3 | 复用 M2 位图；SHA-256 相同 | 否 | 是 |
| `docs/product-design/m3/assets/asset-prop-reference.png` | M3 | 复用 M2 位图；SHA-256 相同 | 否 | 是 |
| `docs/product-design/m3/assets/asset-shot-keyframe.png` | M3 | 复用 M2 位图；SHA-256 相同 | 否 | 是 |

## 4. 相邻继承与扩展证据

本节不属于 M1–M3 核心 UI 基线。M4 rehearsal 可见性用于说明工程可见性扩展；M6D 用于说明同一视觉系统能够延展到独立的全局供应商管理工作台。两者都不能改变 M1–M3 的核心范围。

| 证据路径 | 阶段 | 支持的结论 | 最终方向 | 经过 QA |
| --- | --- | --- | --- | --- |
| `docs/milestones/m3-baseline-summary.md` | 工程 M3 | 持久 Job/Result、选择、review、version、rerun UI 有实现和历史验证证据 | 否 | 工程验证 |
| `docs/milestones/m4-ui-visibility-plan.md` | 工程 M4 | 章节 rehearsal 可见性缺口和建议表面 | 否 | 否（计划） |
| `docs/milestones/m4-final-closeout.md` | 工程 M4 | 存在 Phase 1 只读可见性面板的历史实现/验证记录；本次未重新验证 | 否 | 历史工程验证 |
| `docs/superpowers/specs/2026-07-12-m6d-management-ui-visual-design.md` | M6D | 用户批准 Supplier Operations Workbench，继承 M1–M3 | 是 | 是 |
| `docs/product-design/m6d/design-qa.md` | M6D | 独立供应商管理工作台留有三视口和交互 QA；不代表多 Provider 生成中心完成 | 否 | 是 |
| `docs/product-design/m6d/assets/selected-direction-supplier-operations-workbench.png` | M6D | 供应商 Rail + 模型表 + Inspector 方向 | 是 | 是 |
| `docs/product-design/m6d/assets/m6d-implementation-desktop-1440.png` | M6D | 存在桌面生产实现截图证据；本次未重新验证 | 否 | 是 |
| `docs/product-design/m6d/assets/m6d-implementation-1180.png` | M6D | 存在 1180 Inspector 堆叠截图证据；本次未重新验证 | 否 | 是 |
| `docs/product-design/m6d/assets/m6d-implementation-768.png` | M6D | 存在 768 compact supplier selector 截图证据；本次未重新验证 | 否 | 是 |
| `web/src/app/App.tsx` | 当前生产只读证据 | 存在 `/projects`、章节、供应商、设置和绑定路由 | 否 | 非设计 QA；本次未重新验证 |
| `web/src/features/chapter/ChapterWorkspace.tsx` | 当前生产只读证据 | 存在 M1–M3 七个 Chapter Tabs 和 Gate 逻辑 | 否 | 非设计 QA；本次未重新验证 |
| `web/tests/m1-workflow.spec.ts` | 当前生产只读证据 | M1 主流程 E2E 文件存在 | 否 | 本次未重跑 |
| `web/tests/m2-assets-prompts.spec.ts` | 当前生产只读证据 | M2 资产/Prompt E2E 文件存在 | 否 | 本次未重跑 |

## 5. 缺失或无法读取的证据

所有实际发现文件均可读取；没有损坏 PNG 或无法打开的 HTML/Markdown。缺失项如下：

| 预期存在但实际未找到 | 路径 | 影响 | 处理方式 |
| --- | --- | --- | --- |
| M1 Design QA 文档 | `docs/product-design/m1/design-qa.md` | 无法证明 M1 静态原型与方向图做过正式视觉/交互 QA | M1 标记“有方向/原型、无 QA” |
| M1 原型截图 | `docs/product-design/m1/assets/prototype-*.png` | 无仓库内静态原型视觉实现证据 | 仅引用 HTML 和方向图，不声称 QA |
| M2 响应式截图 | `docs/product-design/m2/assets/*1180*`、`*768*` | M2 响应式仅有文档规范，没有独立视觉证据 | 采用 M3 后续三视口规则作为统一响应式基线 |
| M1–M3 生产前端对选定方向的统一对比 QA | 未形成同一套目录证据 | 静态原型 QA 不能证明生产实现视觉一致 | 生产实现状态单独标注；M6D 存在独立 Product Design QA 证据 |
| Seedance/LibTV/连续性审核 Product Design 包 | 未发现 | 无法继承现成页面方向 | 列入后续里程碑，不自行补全 |

## 6. 双轨证据优先级

### 视觉目标证据优先级

```text
最新通过的 Product Design QA
> 用户批准的视觉目标
> selected-direction
> information architecture / interaction specification
> 早期探索方向图
> 普通需求或设想
```

判断页面应该长什么样时，以最新 Design QA 和用户批准方向为先。临时生产前端不自动覆盖已批准视觉目标；早期方向图与后续 QA 冲突时，以后续 QA 为准。

### 运行事实证据优先级

```text
当前重新执行的生产验证结果
> 当前代码、测试和 E2E 证据
> 当前路由和组件只读证据
> 历史里程碑或提交记录
> 静态原型
```

判断当前功能是否真实可运行时，静态原型和历史完成记录都不够。本次没有重跑生产测试，因此相关结论统一为“存在生产实现证据，本次未重新验证”。

### 本次应用结果

1. M3 Design QA 覆盖并纠正 M3 早期方向图中的未确认 Provider 参数。
2. M3 三视口 QA 覆盖 M1 仅隐藏 Inspector 的早期窄屏原型行为。
3. M6D 是相邻的全局供应商管理范围，不改变 M1–M3 章节生产 Shell，也不等于多 Provider 生成体验。
4. M4 rehearsal 可见性是相邻工程扩展，不等于 Planned/Observed 连续性审核。
5. `docs/项目完整开发路径与当前状态.md` 中“Web UI 暂缓、Shot Prompt 未开始”等状态早于 M1–M6 工程 closeout，属于过时状态快照，不用于当前完成度结论。
