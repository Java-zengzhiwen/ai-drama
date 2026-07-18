# 现有设计资产清单

## 统计口径

| 指标 | M1 | M2 | M3 | 合计 |
| --- | ---: | ---: | ---: | ---: |
| 文件数量 | 8 | 21 | 33 | 62 |
| Markdown | 6 | 10 | 10 | 26 |
| HTML | 1 | 2 | 1 | 4 |
| PNG | 1 | 9 | 22 | 32 |

- HTML 原型数量：3（M1、M2、M3 各 1）。M2 另有 1 个静态 QA 对比 HTML，不计为原型。
- 截图/方向图/素材图片数量：32 个 PNG 物理文件。
- QA 证据数量：10 个以 `design-qa` 命名的物理文件，其中 2 份 QA 说明文档、1 个对比 HTML、7 个对比/聚焦/响应式 PNG。
- 去重说明：M3 逐字节复用了 M2 的 6 张素材图片；M3 的 `prototype-screenshot.png` 与 `prototype-screenshot-1440x1024.png` 相同，`design-qa-comparison.png` 与 `design-qa-comparison-1440x1024.png` 相同。统计保留仓库物理文件数，证据索引会标注复用关系。

## M1

| 阶段 | 文件或资产路径 | 类型 | 内容用途 | 状态 | 最终选定方向 | 有 QA |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | `docs/product-design/m1/brief.md` | 设计说明 | 定义项目、章节、原文、剧本、分镜与 Gate 范围 | 已设计 | 否 | 否 |
| M1 | `docs/product-design/m1/information-architecture.md` | 信息架构 | 路由、项目列表、项目看板和章节工作台结构 | 已设计 | 否 | 否 |
| M1 | `docs/product-design/m1/interaction-spec.md` | 交互说明 | 导航、Tab、分镜选择、确认 Gate 和原型交互 | 已设计 | 否 | 否 |
| M1 | `docs/product-design/m1/screen-states.md` | 状态说明 | Loading、Empty、Error、Blocked、Success | 已设计 | 否 | 否 |
| M1 | `docs/product-design/m1/selected-direction.md` | 选定方向 | 锁定 Storyboard Command Table | 最终方向 | 是 | 否 |
| M1 | `docs/product-design/m1/visual-tokens.md` | 设计说明 | 颜色、字体、间距、圆角和组件语言 | 已设计 | 否 | 否 |
| M1 | `docs/product-design/m1/assets/prototype.html` | 静态原型 | 项目列表/看板/章节工作台与状态模拟 | 原型完成 | 是 | 否 |
| M1 | `docs/product-design/m1/assets/selected-direction-storyboard-command-table.png` | 方向图 | 选定的密集分镜工作台视觉方向 | 最终方向图 | 是 | 否 |

### M1 原型性质

- 纯静态、前端单文件，使用内嵌 Mock 数据、CSS 和 JavaScript。
- 无 `fetch`、XHR、后端 API 或生产前端写入。
- 可操作交互：项目列表/项目看板/章节工作台切换，原文/剧本/分镜 Tab 切换，分镜行选择，状态模拟，剧本未确认阻断模拟，确认分镜。
- 未提供独立原型截图、响应式截图或 Design QA；选定方向图不能替代原型实现 QA。

## M2

| 阶段 | 文件或资产路径 | 类型 | 内容用途 | 状态 | 最终选定方向 | 有 QA |
| --- | --- | --- | --- | --- | --- | --- |
| M2 | `docs/product-design/m2/brief.md` | 设计说明 | 定义 Profiles、资产、需求与 Shot Prompt 范围 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/component-inventory.md` | 设计说明 | M1 复用组件与 M2 新组件清单 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/design-qa.md` | QA 说明 | 静态原型与选定方向的 QA 结论 | QA 通过 | 否 | 是 |
| M2 | `docs/product-design/m2/implementation-handoff.md` | 实现交接 | 路由、组件、API 依赖、Gate 与响应式规则 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/information-architecture.md` | 信息架构 | 章节内资产、Profile、需求和 Prompt 子视图 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/interaction-spec.md` | 交互说明 | 资产列表/详情、Profile、需求和 Prompt 交互 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/screen-states.md` | 状态说明 | Profile、资产、需求和 Prompt 状态 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/selected-direction.md` | 选定方向 | 锁定 Asset Detail Review Page | 最终方向 | 是 | 是 |
| M2 | `docs/product-design/m2/visual-tokens.md` | 设计说明 | 继承 M1 并补充图片比例与布局 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/workflow-map.md` | 交互说明 | Storyboard → 资产 → Prompt Gate 流程 | 已设计 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/prototype.html` | 静态原型 | 资产预览/详情、Profiles、需求、Prompt、状态样例 | 原型完成 | 是 | 是 |
| M2 | `docs/product-design/m2/assets/design-qa-comparison.html` | QA 对比页 | 方向图与原型截图并列对比 | QA 证据 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/design-qa-comparison.png` | QA 对比图 | 全页视觉比较 | QA 证据 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/prototype-detail-screenshot.png` | 实现截图 | 1440 宽资产详情静态原型 | 原型截图 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/selected-direction-asset-detail-review-page.png` | 方向图 | 大图优先资产审查方向 | 最终方向图 | 是 | 是 |
| M2 | `docs/product-design/m2/assets/asset-character-reference.png` | 其他 | 人物正面参考 Mock 位图 | 原型素材 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/asset-character-outfit.png` | 其他 | 人物服装 Mock 位图 | 原型素材 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/asset-scene-reference.png` | 其他 | 场景参考 Mock 位图 | 原型素材 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/asset-scene-angle.png` | 其他 | 场景机位 Mock 位图 | 原型素材 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/asset-prop-reference.png` | 其他 | 道具参考 Mock 位图 | 原型素材 | 否 | 是 |
| M2 | `docs/product-design/m2/assets/asset-shot-keyframe.png` | 其他 | 镜头关键帧 Mock 位图 | 原型素材 | 否 | 是 |

### M2 原型性质

- 纯静态单文件，使用本地 Mock 文本和 6 张本地位图。
- 无 `fetch`、XHR、后端调用或生产前端写入。
- 可操作交互：在资产预览、资产详情、Profiles、缺失需求、Shot Prompt 和状态样例之间切换；页面内跳转按钮可切换对应视图。
- 上传、生成、保存、审查等业务按钮主要是展示态，不持久化数据。
- QA 只证明静态原型与选定方向一致，不证明生产 React 页面已经完成。

## M3

| 阶段 | 文件或资产路径 | 类型 | 内容用途 | 状态 | 最终选定方向 | 有 QA |
| --- | --- | --- | --- | --- | --- | --- |
| M3 | `docs/product-design/m3/brief.md` | 设计说明 | 定义生成、持久任务、结果与重跑范围 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/component-inventory.md` | 设计说明 | M1/M2 复用组件与 M3 新组件 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/design-qa.md` | QA 说明 | 三视口视觉、交互与可访问性 QA | QA 通过 | 否 | 是 |
| M3 | `docs/product-design/m3/implementation-handoff.md` | 实现交接 | API、状态映射、轮询、预览、重跑和响应式 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/information-architecture.md` | 信息架构 | 生成和结果页结构、对象和状态词汇 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/interaction-spec.md` | 交互说明 | 提交、轮询、恢复、预览与重跑交互 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/screen-states.md` | 状态说明 | Job、结果、恢复和 Drawer 状态 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/selected-direction.md` | 选定方向 | 锁定 Generation Command + Result Preview | 最终方向 | 是 | 是 |
| M3 | `docs/product-design/m3/visual-tokens.md` | 设计说明 | 继承 Token 并补充视频/Drawer 尺寸 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/workflow-map.md` | 交互说明 | 生成、结果、重跑、恢复与过期分支 | 已设计 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype.html` | 静态原型 | 生成表、预览、版本、恢复 Notice 和重跑 Drawer | 原型完成 | 是 | 是 |
| M3 | `docs/product-design/m3/assets/selected-direction-generation-command-result-preview.png` | 方向图 | 生成指令表 + 结果预览方向 | 最终方向图 | 是 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-screenshot.png` | 实现截图 | 1440×1024 原型截图，和同尺寸命名文件相同 | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-screenshot-1440x1024.png` | 实现截图 | 1440×1024 桌面 + Drawer | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-screenshot-1180x800.png` | 响应式截图 | 1180×800 表格优先布局 | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-screenshot-1180x800-drawer.png` | 响应式截图 | 1180×800 堆叠 Drawer | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-screenshot-768x1024.png` | 响应式截图 | 768×1024 单栏布局 | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-screenshot-768x1024-drawer.png` | 响应式截图 | 768×1024 全宽 Drawer | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-recovery-in-progress-1440x1024.png` | 实现截图 | 启动恢复检查中 | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-recovery-completed-1440x1024.png` | 实现截图 | 恢复完成与异常并列 | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/prototype-recovery-dismissed-1440x1024.png` | 实现截图 | 恢复 Notice 关闭后其他 Notice 保留 | 原型截图 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/design-qa-comparison.png` | QA 对比图 | 1440 全页比较，与同尺寸文件相同 | QA 证据 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/design-qa-comparison-1440x1024.png` | QA 对比图 | 选定方向与桌面原型比较 | QA 证据 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/design-qa-responsive-1180x800.png` | QA 对比图 | 1180 表格与堆叠 Drawer | QA 证据 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/design-qa-responsive-768x1024.png` | QA 对比图 | 768 单栏与全宽 Drawer | QA 证据 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/design-qa-focused-preview-rerun.png` | QA 对比图 | 预览、Drawer 与恢复关闭焦点区 | QA 证据 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/design-qa-recovery-lifecycle.png` | QA 对比图 | 恢复检查中/完成/关闭生命周期 | QA 证据 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/asset-character-reference.png` | 其他 | 复用 M2 人物参考 Mock 位图 | 复用素材 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/asset-character-outfit.png` | 其他 | 复用 M2 服装 Mock 位图 | 复用素材 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/asset-scene-reference.png` | 其他 | 复用 M2 场景参考 Mock 位图 | 复用素材 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/asset-scene-angle.png` | 其他 | 复用 M2 场景机位 Mock 位图 | 复用素材 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/asset-prop-reference.png` | 其他 | 复用 M2 道具 Mock 位图 | 复用素材 | 否 | 是 |
| M3 | `docs/product-design/m3/assets/asset-shot-keyframe.png` | 其他 | 复用 M2 关键帧 Mock 位图 | 复用素材 | 否 | 是 |

### M3 原型性质

- 纯静态、Mock 数据、无 Provider 或后端请求；没有 `fetch`、XHR、localStorage 或 sessionStorage。
- 可操作交互：镜头行选择，重跑 Drawer 从真实触发按钮打开/关闭，桌面焦点陷阱与窄屏非模态语义，Esc 关闭与焦点回归，恢复检查中/完成切换，恢复完成 Notice 关闭。
- 播放、提交、刷新、采用结果等多数业务动作仅展示，不产生持久任务。
- QA 对静态原型在 1440×1024、1180×800、768×1024 做了视觉、响应式、交互和可访问性检查。

## 相邻继承与扩展证据（不计入 M1–M3 核心基线数量）

- M6D — `docs/product-design/m6d/`：独立全局供应商、模型与项目绑定管理工作台的选定方向、三视口生产实现截图和 Product Design QA。它继承 M1–M3 的视觉系统，但不是章节主流程，也不证明多 Provider 生成中心完成。
- M6D — `docs/superpowers/specs/2026-07-12-m6d-management-ui-visual-design.md`：经用户批准的 Supplier Operations Workbench 视觉规范，属于相邻扩展设计。
- M4 — `docs/milestones/m4-ui-visibility-plan.md`：章节级 rehearsal 可见性计划。它是在生成/结果区域增加的工程可见性扩展，不等同于 Planned/Observed 连续性审核。
- `docs/milestones/m3-baseline-summary.md`、`docs/milestones/m4-final-closeout.md`：历史生产实现与验证记录，不是 Product Design 方向文件，也不代表本次已重新验证当前生产实现。

核心 UI 基线只包含 M1、M2、M3。以上资料只用于证明视觉语言和工作台结构可被后续阶段继承。
