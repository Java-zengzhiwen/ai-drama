# UI Baseline Report

## 1. 执行结论

M1–M3 已形成一套连续、可继承的 AI 漫剧章节生产 UI 基线，不需要推翻重做。

```text
设计已验证：M1 项目/章节/原文/剧本/分镜；M2 Profiles/资产/需求/Shot Prompt；M3 Agnes 生成/结果/重跑。
静态原型已验证：M1、M2、M3 各有 1 个纯静态 Mock HTML 原型；M1 无独立 Design QA。
已有 Design QA：M2、M3 静态原型；M6D 有独立 Product Design QA，但属于相邻扩展证据。
存在生产实现证据：仓库中存在与相关阶段对应的生产路由、组件、测试和历史里程碑记录。本次仅进行只读证据检查，未重跑生产验收，因此不将其重新判定为当前已验证完成。
本次未重新验证：M1–M4 和 M6D 当前生产实现。
未确认：新建项目向导、项目级跨章节 Canon/资产、Seedance/LibTV、多 Provider 生成中心、视频连续性审核、后期与发布。
```

当前 UI 的统一基线可概括为：**浅色、紧凑、表格优先的章节制作工作台，以 Workflow Rail 表达 Gate，以右侧 Inspector/Drawer 承担审查和决策。**

## 2. 审阅范围

- 完整读取 M1 的 8 个、M2 的 21 个、M3 的 33 个文件，共 62 个。
- 核验 26 份 Markdown、4 个 HTML 和 32 个 PNG。
- 阅读三个静态原型的脚本，确认均使用本地 Mock 数据且不调用后端。
- 逐项检查现有方向图、原型截图、响应式截图、QA 对比图和素材图；通过哈希识别 M2/M3 的复用/重复证据。
- 检索散落 UI 资料，将 M4 rehearsal 可见性与 M6D 模型供应商管理设计/QA 归为相邻继承与扩展证据。
- 只读检查当前生产路由、主要组件、E2E/单元测试文件和里程碑完成记录；没有修改或运行生产功能。

核心 UI 基线只包含 M1、M2、M3。M4 rehearsal 可见性与 M6D 不属于 M1–M3 核心设计包，不能和核心主链处于同一完成度层级。

### 双轨证据优先级

视觉目标按以下优先级判断：

```text
最新通过的 Product Design QA
> 用户批准的视觉目标
> selected-direction
> information architecture / interaction specification
> 早期探索方向图
> 普通需求或设想
```

判断页面应该长什么样时，临时生产前端不自动覆盖已批准视觉目标；早期方向图与后续 QA 冲突时，以后续 QA 为准。

运行事实按以下优先级判断：

```text
当前重新执行的生产验证结果
> 当前代码、测试和 E2E 证据
> 当前路由和组件只读证据
> 历史里程碑或提交记录
> 静态原型
```

静态原型不能证明功能真实可运行，历史记录也不等于当前分支已重新验证。没有重跑测试时必须标为“本次未重新验证”。

## 3. 现有 UI 总览

核心页面链：

```text
项目列表
→ 项目总览/章节列表
→ 章节工作台
→ 原文
→ 剧本
→ 分镜
→ 资料与资产
→ Shot Prompt
→ Agnes 生成
→ 结果与重跑
```

相邻继承与扩展证据：

- M4 rehearsal 可见性是在现有生成/结果区域增加的工程可见性扩展，不是 M1–M3 核心 Product Design 包，也不等同 Planned/Observed 连续性审核。
- M6D 是独立的全局供应商、模型与项目绑定管理工作台。它继承 M1–M3 的视觉系统，但不是章节主流程；它证明供应商管理 UI 有独立设计和后续实现证据，不代表多 Provider 生成中心完成。

尚未进入主链：连续性审核、Provider 对比、LibTV/Seedance、后期和发布。

## 4. M1 设计总结

M1 选定 **Storyboard Command Table**：

- 项目列表与项目看板用于找到下一章节动作。
- 章节工作台以项目/章节 Rail、Workflow Rail、原文/剧本/分镜 Tabs、密集分镜表和右 Inspector 组成。
- 剧本 approved 是分镜 Gate，分镜 approved 是后续生产 Gate。
- 定义 Loading、Empty、Error、Blocked 和 Success，并要求阻断原因贴近操作。
- 静态原型可切换页面/Tab、选择镜头、模拟状态和确认分镜。

证据限制：只有选定方向图和 HTML；没有独立 M1 Design QA、响应式截图或原型实现截图。

## 5. M2 设计总结

M2 不换 Shell，增加 **Asset Detail Review Page**：

- 最小 Character、Scene、Prop、Style Profiles。
- 图片资产列表、上传/生成入口、以大图为主的详情审查、版本条和当前采用。
- 镜头级缺失需求，直接指向最小纠正动作。
- Shot Prompt 正/负 Prompt、continuity notes、asset refs、Revision 和 Agnes 参数预览。
- Missing/rejected/non-usable 资产阻断 Prompt ready。
- 明确不是全局 DAM、专业图片编辑器、视频生成或后期工作台。

M2 有选定方向图、静态原型截图和全页 QA 对比，最终 QA 通过；但没有独立 1180/768 响应式截图。

## 6. M3 设计总结

M3 选定 **Generation Command + Result Preview**：

- `Agnes 生成` 使用 ready/blocked 同表的密集命令面；只允许 ready 镜头提交。
- UI 阻止重复提交，展示轮询、RPM、启动恢复和未知提交结果。
- 结果页使用暂停的 16:9 视频预览、版本条、源 Job/attempt 和当前采用。
- 所有结果版本保留；重跑通过显式 Drawer 创建新任务，不覆盖源记录。
- 参数只在后端 capability/API schema 支持时出现。
- Provider URL 过期与本地文件可用性分离显示。

M3 的 QA 最完整：1440×1024、1180×800、768×1024 三视口；Drawer 桌面/窄屏语义；Focus Trap、Esc、焦点回归、Live Region、恢复 Notice 生命周期均通过。

## 7. 当前统一设计系统

### 视觉

- 浅色工作台：`#f6f8fb` 页面、白色工作面、`#d9dee8` 细分隔。
- 主蓝 `#2563eb`，成功/警告/错误分别为 `#16a34a`、`#d97706`、`#dc2626`。
- Inter/system 14px 正文、12px Label、18/22px 标题层级。
- 4/8/12/16/20/24px 间距，4/6/8px 小圆角。
- 边框和浅表面优先，避免重阴影、渐变、装饰卡片和卡片套卡片。

### 结构

- 项目/章节 Rail + Workflow Rail + Chapter Tabs。
- 主工作区根据对象切换文本、表格、大图或视频预览。
- Inspector 负责决策，Drawer 负责显式重跑/修复。
- 表格保持高密度；窄屏水平滚动而不是转成卡片堆叠。

### 核心组件

可直接复用：Workflow Rail、Chapter Tabs、Dense Table、Status Chip、Inspector、Asset Preview、Version Strip、Notice Bar、Result Preview、Rerun Drawer、Action Footer、Empty/Loading/Error/Blocked State。

### Shared UI Contract

公共组件和结构包括 Application Shell、Project / Chapter Rail、Workflow Rail、Chapter Tabs、Dense Table、Status Chip、Inspector、Asset Preview、Media / Result Preview、Version Strip、Notice Bar、Drawer、Action Footer、Loading State、Empty State、Error State、Blocked State。

1. 后续 Product Design 必须优先复用这些组件和交互语言；新模块不得无理由创建第二套 App Shell。
2. 表格型任务不得默认改成卡片墙；窄屏优先堆叠和横向滚动，不把密集生产数据强制变成嵌套卡片。
3. 审核决定优先进入 Inspector；显式修改、重跑和修复优先使用 Drawer。
4. 资产和媒体版本保留历史，并明确当前采用版本。
5. Blocked 对象继续可见，操作被禁用并显示行内原因。
6. 新增组件时必须解释现有 Shared UI Contract 为什么不足。
7. PD-C1、PD-P1、PD-D1 均继承本 Contract。

## 8. 已锁定设计决策

1. 不重做章节工作台或引入新的章节级 Shell。
2. 表格是分镜、需求和生成任务的主要操作面。
3. Inspector 继续承担详情、QC、版本和决定。
4. 资产详情以大图为主，版本历史持续可见。
5. 视频不自动播放，保持 16:9 决策预览。
6. 资产和结果历史不被新版本覆盖；每个 binding/镜头只标一个当前采用。
7. Blocked 镜头继续可见但不可提交，原因和修复入口行内呈现。
8. 重跑必须显式创建新任务，并保存源 Prompt、资产、Job、attempt。
9. Provider 参数由后端 capability/API schema 决定，前端不能硬编码未确认字段。
10. M1–M3 不引入 LibTV、时间线、配音、字幕、BGM、剪辑、导出或协作 UI。

完整来源见 [已锁定决策](06-locked-decisions.md)。

## 9. 当前页面和功能覆盖

### 已完整设计

- 项目列表、项目总览/章节列表。
- 原文查看/编辑、剧本编辑/QC/确认、分镜表/确认。
- Profiles、人物/场景/道具资产、资产详情/审查、缺失需求。
- Shot Prompt 主工作流。
- Agnes 生成、批量提交、任务轮询/恢复。
- 结果预览、结果版本、当前采用、失败分类和显式重跑。

### 部分设计

- 新建项目、原著导入、视觉引用、Prompt Revision、Agnes 设置/参数。
- M4 rehearsal 可见性存在独立工程计划和实现证据，但没有纳入 M1–M3 Product Design 包，本次未重新验证。
- 模型供应商和项目模型绑定在 M6D 有独立设计、实现证据和 QA；M6D 不属于章节主流程，也不等于多 Provider 生成中心，本次未重新验证。

### 未覆盖或明确延后

- 登录/注册、全局 Dashboard、跨项目任务中心。
- 项目级跨章节资产/Canon/服装状态时间线。
- Seedance、LibTV、Provider 对比与 Provider-neutral Clip Contract UI。
- 视频连续性 Observed State 与修复动作。
- 后期、封面、版权和发布。

## 10. 尚未覆盖的关键能力

最关键缺口是“计划连续性 → 实际视频 → 决策/修复”的闭环：

```text
Planned Start/End
→ 视频结果首/尾帧
→ Observed Start/End
→ 人脸/服装/站位/道具/场景判断
→ accept / accept_with_deviation / repair / reject
→ repair_tail / reanchor_after_drift（后续高级动作）
```

第二缺口是多 Provider 生成：相邻 M6D 资料说明 Supplier/Model/Binding 管理已有独立设计和后续实现证据，但生成工作台还没有 Seedance/LibTV、实际解析模型可见性和同镜结果比较设计。

第三缺口是后期与发布：当前结果页明确是决策面，不是时间线或 NLE。

## 11. 与现有 AI 漫剧平台工作流的对应关系

| 工作流 | 现有 UI | 结论 |
| --- | --- | --- |
| 小说/原著 | 原文 Tab | 部分覆盖；无完整导入向导 |
| 剧本 | 剧本 Tab | 已覆盖 |
| 剧本审核 | 校验、确认、拒绝、Gate | 已覆盖 |
| 人物/场景/道具 Profile | Profiles | 已覆盖 |
| 视觉资产 | 资产预览/详情/需求 | 已覆盖 |
| 分镜 | Storyboard Command Table | 已覆盖；M1 无独立 QA |
| Shot Prompt | Prompt Studio | 已覆盖 |
| Provider 生成 | Agnes 生成 | 单 Provider 已覆盖，多 Provider 未覆盖 |
| 视频结果 | 结果预览/版本 | 已覆盖 |
| 重跑 | Rerun Drawer | 已覆盖 |
| 连续性审核 | 无 | 未覆盖 |
| 后期 | 无 | 明确延后 |
| 发布 | 无 | 未覆盖 |

## 12. 后续 Product Design 推荐顺序

1. **PD-C1 Continuity Review（视频连续性审核与 Canon 状态）**：补上结果与后期之间的事实审查闭环。
2. **PD-P1 Multi-Provider Generation（多 Provider 生成体验）**：在 M3 Generation Table 中接入 Seedance/LibTV 等 capability，而不是重做 Dashboard。
3. **PD-D1 Post-production and Delivery（后期与发布）**：以通过连续性审核的当前采用片段为稳定输入，逐步加入组装、音频、字幕、封面和发布。

Seedance 应插入 `Shot Prompt → Provider 生成`；连续性状态系统应插入 `视频结果/重跑 → 连续性审核 → 后期`。

PD-C1 首轮设计范围严格限定为：

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

首轮暂不包含自动人脸识别模型、自动视频理解模型、完整视频时间线、多 Provider 对比、后期剪辑、自动修复执行、Seedance 专用完整参数或复杂 Canon 图数据库。本次只修订未来范围描述，不启动 PD-C1 设计。

## 13. 风险与待确认项

### 已识别差异

- M3 早期方向图显示了未确认 Provider 参数；后续 QA 已锁定 capability 驱动规则。
- M1 窄屏原型隐藏 Inspector；M3 三视口 QA 已升级为堆叠/全宽规则。
- M2 的生成页锁定与 M3 的解锁是正常阶段演进。
- M3 排除 M4 验收页，而 M4 后续加入只读面板，是相邻工程可见性扩展，不是 M3 回归，也不等同连续性审核。

### 缺失证据

- M1 Design QA、M1 原型截图和响应式证据。
- M2 1180/768 独立响应式截图。
- M1–M3 静态原型与当前生产前端的统一视觉对比 QA。
- Seedance/LibTV/连续性审核的 Product Design 包。

### 待确认

- 新建项目向导与项目级 Canon 总控是否在 PD-C1 前补齐。
- `/settings/agnes` 是否最终并入 M6D Supplier 管理语义。
- PD-C1 启动前所需的最小 Planned/Observed 状态与 revision 契约。

## 14. 生成文件清单

```text
docs/product-design/ui-baseline/README.md
docs/product-design/ui-baseline/01-existing-assets-inventory.md
docs/product-design/ui-baseline/02-current-information-architecture.md
docs/product-design/ui-baseline/03-current-design-system.md
docs/product-design/ui-baseline/04-screen-and-feature-coverage.md
docs/product-design/ui-baseline/05-interaction-and-state-baseline.md
docs/product-design/ui-baseline/06-locked-decisions.md
docs/product-design/ui-baseline/07-gaps-and-next-milestones.md
docs/product-design/ui-baseline/08-source-evidence-index.md
docs/product-design/ui-baseline/ui-baseline-report.md
```

## 15. 问题直接回答

1. **是否需要推翻 M1–M3 重新设计？** 不需要；三阶段的继承关系清晰，M2/M3 QA 支持继续使用。
2. **当前能否以 M1–M3 作为统一 UI 基线？** 可以；响应式和可访问性优先采用 M3 较新的 QA 规则。
3. **下一轮最应优先设计哪个模块？** 视频连续性审核与 Canon 状态。
4. **哪些组件可以直接复用？** Workflow Rail、Tabs、Dense Table、Status Chip、Inspector、媒体预览、Version Strip、Notice Bar、Drawer 和各类状态面。
5. **哪些页面仅有静态原型，尚未由这些原型证明生产代码已实现？** M1–M3 原型中的所有页面都属于静态 Mock；生产实现必须依据另行存在的路由、组件、测试和里程碑证据判断。
6. **当前 UI 是否已覆盖完整 AI 漫剧平台？** 没有；它覆盖到视频结果与重跑，缺连续性审核、多 Provider 执行、后期和发布。
7. **Seedance 和连续性状态系统应插入哪里？** Seedance 进入现有 Provider 生成层；连续性状态系统位于结果/重跑之后、后期之前。
