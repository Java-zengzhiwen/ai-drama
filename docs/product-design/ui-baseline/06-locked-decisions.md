# 已锁定设计决策

以下只收录原文明确标为 Selected Direction、Locked Decision、Must Not Change、Required Fidelity/Final Result 或经过 QA 明确确认的规则。普通设想和未来计划不列为锁定。

范围上，M1–M3 是核心 UI 基线；M4 rehearsal 可见性和 M6D 是相邻继承与扩展证据。相邻证据可以支持视觉语言延展性，但不能扩大核心设计包的完成范围。

## 1. 全局产品结构

1. M1 的选定方向是 **Storyboard Command Table**，产品是生产工作台而不是文档查看器或营销 Dashboard。
   来源：`docs/product-design/m1/selected-direction.md`
2. M2、M3 都扩展现有 M1 章节工作台，不替换产品 Shell 或视觉系统。
   来源：`docs/product-design/m2/brief.md`、`docs/product-design/m3/brief.md`
3. M2、M3 不增加章节生产之外的新全局导航；相关能力留在项目/章节 Shell 中。
   来源：`docs/product-design/m2/implementation-handoff.md`、`docs/product-design/m3/implementation-handoff.md`
4. 相邻扩展 M6D 模型供应商是明确批准的独立全局目的地，但其视觉继续继承 M1–M3，不能用临时 MVP 风格反向替代章节工作台。M6D 不属于章节主流程，也不代表多 Provider 生成中心完成。
   来源：`docs/superpowers/specs/2026-07-12-m6d-management-ui-visual-design.md`

## 2. 章节工作台

1. 继续使用项目/章节 Rail、Workflow Rail、Chapter Tabs、主工作区和右侧 Inspector。
   来源：`docs/product-design/m1/brief.md`、`docs/product-design/m2/brief.md`、`docs/product-design/m3/brief.md`
2. 表格是结构化生产对象的主操作面，不能改成卡片化 Dashboard 或把关键字段藏入 Modal。
   来源：`docs/product-design/m1/selected-direction.md`、`docs/product-design/m3/selected-direction.md`
3. Inspector 继续承担当前选择的详情、QC、版本和决策动作。
   来源：`docs/product-design/m1/selected-direction.md`、`docs/product-design/m2/selected-direction.md`
4. Gate 原因必须与被阻断操作相邻，并同步出现在 Workflow Rail；成功使用行内反馈，不要求 Modal。
   来源：`docs/product-design/m1/screen-states.md`、`docs/product-design/m2/interaction-spec.md`

## 3. 分镜

1. Canonical Storyboard 使用密集表格和选中行 Inspector 编辑。
   来源：`docs/product-design/m1/selected-direction.md`
2. 剧本未 approved 时，分镜生成和确认都被阻断。
   来源：`docs/product-design/m1/brief.md`、`docs/product-design/m1/interaction-spec.md`
3. 分镜确认必须通过明确动作；确认后更新 Rail、章节状态、Tab 状态和 Inspector Gate 摘要。
   来源：`docs/product-design/m1/screen-states.md`

## 4. 资产

1. M2 选定方向是 **Asset Detail Review Page**，资产体验必须图片预览优先。
   来源：`docs/product-design/m2/selected-direction.md`
2. 资产详情嵌套在章节工作台内，不是全局 DAM。
   来源：`docs/product-design/m2/selected-direction.md`、`docs/product-design/m2/implementation-handoff.md`
3. 大图是主要资产审查面，版本历史保持可见，资产决策放在右侧 Inspector。
   来源：`docs/product-design/m2/selected-direction.md`
4. 每个 binding role 只有一个当前采用资产，采用动作必须显式。
   来源：`docs/product-design/m2/implementation-handoff.md`
5. 被拒绝资产保留在版本历史中，但不能满足资产需求。
   来源：`docs/product-design/m2/implementation-handoff.md`
6. 资产预览不是图片编辑器；禁止裁剪、图层、蒙版、画笔、无限画布和专业修图工具。
   来源：`docs/product-design/m2/interaction-spec.md`、`docs/product-design/m2/implementation-handoff.md`

## 5. Shot Prompt

1. Prompt readiness 被缺失、拒绝或不可用资产阻断，并提供返回最小纠正动作的入口。
   来源：`docs/product-design/m2/implementation-handoff.md`
2. Positive Prompt 与 Negative Prompt 必须视觉分离。
   来源：`docs/product-design/m2/implementation-handoff.md`
3. Prompt 编辑沿用表格 + Inspector/工作台模式，包含 continuity notes、asset refs、Revision 和参数预览。
   来源：`docs/product-design/m2/component-inventory.md`、`docs/product-design/m2/interaction-spec.md`

## 6. Agnes 生成

1. M3 选定方向是 **Generation Command + Result Preview**，继续位于章节工作台。
   来源：`docs/product-design/m3/selected-direction.md`
2. `Agnes 生成` 以密集生成表为主要提交和监控面。
   来源：`docs/product-design/m3/selected-direction.md`
3. `Agnes 生成` 的 Tab 解锁条件是 current Shot Prompt revision 存在，不要求每个镜头 ready。
   来源：`docs/product-design/m3/selected-direction.md`、`docs/product-design/m3/implementation-handoff.md`
4. Ready 和 Blocked 镜头都保持可见，只有 ready 镜头可选择和提交。
   来源：`docs/product-design/m3/selected-direction.md`
5. UI 必须阻止重复提交；active 等价 Job 显示既有上下文。
   来源：`docs/product-design/m3/selected-direction.md`、`docs/product-design/m3/implementation-handoff.md`
6. Polling、RPM、`restart_recovery_in_progress`、`recovered_after_restart` 和 `submission_outcome_unknown` 是一等且相互区分的状态。
   来源：`docs/product-design/m3/component-inventory.md`、`docs/product-design/m3/design-qa.md`
7. Provider 参数只能由后端 capability/API schema 决定；未确认字段必须隐藏，而不是在前端硬编码。
   来源：`docs/product-design/m3/implementation-handoff.md`、`docs/product-design/m3/design-qa.md`

## 7. 结果与重跑

1. `结果与重跑` 在至少存在一个 GenerationJob 后解锁。
   来源：`docs/product-design/m3/selected-direction.md`
2. 视频结果不自动播放，预览保持 16:9 并显示显式控件。
   来源：`docs/product-design/m3/selected-direction.md`、`docs/product-design/m3/implementation-handoff.md`
3. 所有结果版本保留，失败和过期版本也可追溯；每个镜头只标记一个当前采用结果。
   来源：`docs/product-design/m3/selected-direction.md`、`docs/product-design/m3/implementation-handoff.md`
4. 重跑必须是显式 Drawer，创建新 Job/attempt，不覆盖源 Job 或源结果。
   来源：`docs/product-design/m3/selected-direction.md`、`docs/product-design/m3/interaction-spec.md`
5. 重跑始终显示源 Prompt、源资产、Job、attempt 和参数上下文。
   来源：`docs/product-design/m3/selected-direction.md`
6. 覆盖字段仅限后端支持的 positive Prompt、negative Prompt、资产、mode 和 duration。
   来源：`docs/product-design/m3/implementation-handoff.md`
7. 资产覆盖复用 M2 Asset Picker，只列 usable 资产，并保存精确 asset ID。
   来源：`docs/product-design/m3/selected-direction.md`、`docs/product-design/m3/implementation-handoff.md`
8. Provider URL 过期与本地文件可用性必须分开呈现；本地缺失时不显示破损播放器。
   来源：`docs/product-design/m3/implementation-handoff.md`

## 8. 响应式

1. 桌面保留生成表与右侧预览/Inspector 并列；Drawer 宽度 360px，settled 状态不能遮住预览。
   来源：`docs/product-design/m3/visual-tokens.md`、`docs/product-design/m3/design-qa.md`
2. 1180px 及以下保持表格优先，预览和 Drawer 依次堆叠，不覆盖表格。
   来源：`docs/product-design/m3/implementation-handoff.md`、`docs/product-design/m3/design-qa.md`
3. 768px 及以下切换单栏，表格/版本条可横向滚动，Drawer 全宽，Footer 操作换行。
   来源：`docs/product-design/m3/design-qa.md`
4. 密集数据仍使用表格，不能为了窄屏改成嵌套卡片。
   来源：`docs/product-design/m3/visual-tokens.md`；M6D 进一步重申同一规则。

## 9. 可访问性

1. 桌面重跑 Drawer 使用有标题和描述的模态 Dialog；1180px 及以下改为非模态 Region。
   来源：`docs/product-design/m3/component-inventory.md`、`docs/product-design/m3/design-qa.md`
2. 打开后焦点进入 Drawer；Esc 关闭；关闭后回到实际触发按钮；仅桌面模态时 Focus Trap。
   来源：`docs/product-design/m3/design-qa.md`
3. 轮询/恢复 Notice 使用分离 polite live region，不抢焦点或重读整个 Notice Bar。
   来源：`docs/product-design/m3/design-qa.md`
4. 表格选择和重跑按钮有镜头级可访问名称；Blocked 选择框禁用；行 Enter 只选择不提交。
   来源：`docs/product-design/m3/design-qa.md`

## 10. Shared UI Contract

后续 Product Design 必须优先继承以下公共组件和结构：Application Shell、Project / Chapter Rail、Workflow Rail、Chapter Tabs、Dense Table、Status Chip、Inspector、Asset Preview、Media / Result Preview、Version Strip、Notice Bar、Drawer、Action Footer、Loading State、Empty State、Error State、Blocked State。

1. 新模块不得无理由创建第二套 App Shell，新增组件必须解释现有 Contract 为什么不足。
2. 表格型任务保持 Dense Table；窄屏使用堆叠与横向滚动，不强制改为嵌套卡片。
3. 审核决定优先进入 Inspector；显式修改、重跑和修复优先进入 Drawer。
4. 资产和媒体版本保留历史，并明确当前采用版本。
5. Blocked 对象继续可见，禁用操作并行内显示原因。
6. PD-C1、PD-P1、PD-D1 均继承本 Contract。

## 11. 明确不做的内容

在 M1–M3 范围内明确禁止加入：

- LibTV 画布/执行；
- 配音、字幕、BGM；
- 时间线、裁剪、拼接、视频编辑；
- 成片导出和发布；
- 多人协作/审批；
- Provider Marketplace 或通用工作流引擎；
- M1–M3 内新增 M4 验收 Dashboard。

来源：`docs/product-design/m2/implementation-handoff.md`、`docs/product-design/m3/component-inventory.md`、`docs/product-design/m3/implementation-handoff.md`。

这些是当时里程碑边界，不代表永远不能设计；未来阶段必须在现有 Shell 中明确扩展，并获得新的 Product Design 决策。

## 12. 已解决的文档差异

| 差异 | 处理 |
| --- | --- |
| M2 把 Agnes 生成/结果锁定，M3 解锁 | 正常阶段演进；采用 M3 Gate 条件，不视为冲突 |
| M3 选定方向图含早期未确认 Provider 参数 | M3 Design QA 较新且已通过：只显示后端 capability/API schema 支持字段 |
| M1 窄屏 CSS 直接隐藏 Inspector，M3 改为堆叠/全宽 | 采用较新且有三视口 QA 的 M3 响应式规则 |
| M3 文本先称 Drawer 为 Dialog，后又规定窄屏 Region | M3 Design QA 实测并锁定：桌面 Dialog，≤1180px Region |
| M3 明确不做 M4 验收页，M4 后续增加只读可见性面板 | 相邻工程可见性扩展；不反向改变 M3 核心设计范围，也不等同连续性审核 |

## 13. 待确认而非锁定

- 新建项目的完整交互和项目创建向导。
- `/settings/agnes` 的页面布局与其和 M6D Supplier 配置的最终关系。
- 项目级跨章节资产复用、Canon 总控和服装状态时间线。
- Seedance、LibTV、多 Provider 生成和连续性审核的最终页面结构。
