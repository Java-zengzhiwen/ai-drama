# 独立架构评审报告：Shot Prompt Workflow MVP

**评审声明**
本报告基于用户提供的“系统现状”文本进行推理。因无法访问实际仓库源码，以下所有关于当前系统实现（SQLite 表结构、Revision 字段、审批记录格式、依赖关系模型等）的具体假设，均以提供文本为唯一事实源。若实际实现与文本存在偏差，相关结论需重新评估。

---

## 1. Final Verdict

**GO WITH PREREQUISITE**（有条件通过）

先决条件：**必须首先将 Storyboard 升级为 JSON Canonical**，否则后续 Shot Prompt 的所有“确定性生成”“版本可复现”“审批与执行分离”承诺都将建立在不可靠的 Markdown 解析层上。

---

## 2. Strongest Objections

1. **Storyboard 仍以 Markdown 为权威源，却要求 Shot Prompt 以 JSON 为唯一权威**
   两套权威模型并存必然引发转换漂移、Markdown 解析歧义和审批粒度错位。

2. **revision_outputs 是过早抽象**
   在当前仅有一种 Renderer 输出时引入通用输出容器，会制造无意义的多态，导致内容寻址和审批目标模糊。

3. **资产绑定 (asset binding) 在没有 Visual Asset Registry 时引入状态机**
   必然产生“虚假可信状态”：`bound` 无法被机器验证，只能依赖人工承诺。

4. **execution_targets 固定嵌入 Canonical JSON**
   即使 payload 为 null，也破坏了“平台中立 Canonical Core”的语义——中立核心不应携带目标平台结构。

5. **将 generation_strategy 和 frame_requirements 放入 Shot Prompt Canonical**
   是把执行策略与内容创作混为一谈，未来每个新平台都会污染核心数据模型。

6. **资产绑定变化触发完整新 Revision 会导致版本雪崩**
   资产池微小更新迫使所有关联 Shot Prompt 重签，审批队列被无内容变化的 Revision 淹没。

7. **negative_prompt 完全确定性生成不可信**
   若其依赖模型推理或启发式规则，任何模型更新或阈值变化都会破坏可复现性；即使规则确定，规则版本变化也会造成漂移。

---

## 3. Hidden Assumptions

以下假设在方案中未经验证，且因无源码访问仅能基于文本推断：

1. **Storyboard Markdown 结构稳定且可无损解析为结构化数据**
   实际 Markdown 是面向人阅读的，缺乏模式强制，易引入非结构化片段。假设当前 Markdown 形态适用于可靠的结构化提取。

2. **Prompt Renderer 是纯函数且版本受控**
   未说明 Renderer 版本如何与 Revision 关联、如何处理热修复和向前兼容。假设 Renderer 输出仅依赖于 Canonical 输入和固定算法。

3. **资产绑定可通过“确定性 bind-assets”完全解决**
   资产标识符体系、别名、变体选择可能依赖外部服务或启发式，在当前单用户本地环境中未经验证。假设本地文件路径或 ID 足以唯一确定资产。

4. **1:N 拆分但禁止 N:1 合并是合理约束**
   若未来出现多镜头合成需求，可能被迫引入例外或重构核心假设。此约束假设生产流程固定。

5. **±2 秒偏差在视觉制作中可接受**
   未与下游平台（动画帧精度、配音同步）对齐，纯属本地假设。

6. **LibTV 和 Agnes 的 payload 结构可在未来无痛填充**
   预留空结构极易变成技术债，因为初期设计缺乏真实需求反馈。假设这些平台的需求已预知且不变。

7. **SQLite + immutable object storage 的内容寻址可直接映射到 JSON Canonical 的 Hash**
   Bundle 的 Hash 策略未定义，可能导致相同逻辑内容因序列化顺序不同而 Hash 不同。假设哈希算法和序列化规范已统一。

8. **当前 Revision 模型可以无缝扩展到 JSON 内容类型**
   假设 Revision 的 content_object_id 和 content_hash 字段可以容纳 JSON 对象，且审批、依赖、Freshness 逻辑无需改动。

9. **单用户本地环境意味着并发冲突可忽略**
   但资产绑定状态更新、渲染器等仍可能因多次运行产生竞争，假设这些场景不存在。

10. **“immutable object storage” 实现已支持内容寻址存储**
    可能是指基于哈希的文件系统或对象存储，但未明确。假设其读写接口和一致性保证足以支撑跨 Revision 引用。

---

## 4. Architecture Options

### 方案 A：直接 Shot Prompt Bundle（当前计划）

**概要**
保持 Storyboard Markdown 不变，在其之上直接构建 Shot Prompt 的 JSON Canonical、Renderer、Bundle 和审批流程。

**优点**
- 实现成本低，可快速产出 MVP。
- 不触碰现有 Storyboard 层，风险可控。

**缺点**
- 一致性差：Storyboard 解析为 Prompt Unit 的步骤不可复现，任何 Markdown 改动可能静默改变下游 JSON。
- 审批复杂度高：需要同时审批 Markdown 源和生成的 JSON，或只批 JSON 导致溯源断裂。
- 技术债积累快：未来 Storyboard 转 JSON 时，所有 Shot Prompt 的溯源链必须重算。
- 失败恢复困难：Markdown 解析错误可能直到执行阶段才暴露，且难以定位是解析器问题还是源内容问题。

---

### 方案 B：先升级 Storyboard Canonical JSON（推荐先决方案）

**概要**
将 Storyboard 权威源从 Markdown 改为 JSON，Markdown 降级为 Renderer 输出。Storyboard JSON 包含明确的 Shot 结构、时长、依赖关系。Shot Prompt 直接引用 Storyboard JSON 中的结构化 Shot。

**优点**
- 一致性极高：从 Script → Storyboard → Shot Prompt 全链路结构化，可复现性从根本上得到保证。
- 数据库复杂度适中：Storyboard JSON 可沿用现有 Revision 模型，仅需替换 content 类型。
- 审批清晰：审批对象是结构化 JSON，且可精确到 Shot 级别。
- 为未来 LibTV/Agnes 适配奠定可靠基础，结构化 Shot 信息可直接映射到执行计划。
- 技术债最小，因为一次性解决了解析歧义问题。

**缺点**
- 实现成本较高：需要迁移现有 Markdown Storyboard 为 JSON，并提供过渡期兼容（从 Markdown 导入、导出 Markdown 视图）。
- 需要定义 Storyboard JSON Schema，并确保与现有 Script Revision 的引用一致性。
- 对 Visual Asset Registry 的依赖不变（仍无），但至少故事板层不再引入额外歧义。

---

### 方案 C：Prompt Content 与 Asset Binding 分离版本化

**概要**
将 Shot Prompt 拆分为两个独立的可版本化 Artifact：`PromptContent`（纯粹创作内容，prompt_components）和 `AssetBinding`（资产引用与绑定状态）。两者分别拥有独立 Revision，通过组合产生最终输出。

**优点**
- 版本雪崩问题被消除：资产池更新仅改变 AssetBinding Revision，不影响 PromptContent 审批。
- 可复现性更精细：相同 PromptContent + 不同 AssetBinding 的组合可被精确追踪。
- 资产绑定状态的验证边界清晰：AssetBinding 可引入自己的验证器和 Freshness 检查。
- 后续 Asset Registry 引入时，仅需修改 AssetBinding，PromptContent 保持稳定。

**缺点**
- 数据库复杂度增加：需要额外的 Artifact 类型和组合关系。
- 审批复杂度上升：需要审批 PromptContent 和 AssetBinding 两者，且需判断组合后的最终产物是否合规。
- 实现成本高：当前 MVP 阶段需要投入额外设计，延迟直接产出的可见性。
- 对 Visual Asset Registry 的依赖可以通过 AssetBinding 的抽象缓解，但如果 Registry 缺失，绑定验证仍然不可机器执行。

---

### 方案比较表

| 维度 | A. 直接 Shot Prompt Bundle | B. 先升级 Storyboard Canonical JSON | C. Content/Asset 分离版本化 |
|------|----------------------------|-------------------------------------|-----------------------------|
| **一致性** | 低（Markdown 解析漂移） | 高（全链路结构化） | 高（内容与资产解耦，但需组合契约） |
| **可复现性** | 中（依赖解析器版本） | 高（JSON 直接寻址） | 很高（内容与资产独立 Hash） |
| **数据库复杂度** | 低（沿用现有表结构） | 中（新增 JSON Storyboard Artifact） | 高（多种 Revision 和组合关系） |
| **审批复杂度** | 中（需定义 Bundle 审批单位） | 低（审批结构化 Shot） | 高（两个对象 + 组合审批） |
| **实现成本** | 低 | 中高（需迁移） | 高（新抽象 + 迁移） |
| **LibTV/Agnes 适配** | 差（解析层脆弱） | 好（结构化直接映射） | 很好（内容与执行目标分离） |
| **对 Visual Asset Registry 依赖** | 无（但绑定量不可验证） | 无（但绑定量不可验证） | 低（抽象层可后续对接 Registry） |
| **技术债** | 高（解析器耦合、不可复现） | 低（一次性解决根源） | 中（组合复杂性、过度分离） |
| **失败恢复能力** | 低（解析错误难溯源） | 高（结构化校验早期拦截） | 高（资产失败可独立替换） |

---

## 5. Recommended Data Model

基于方案 B 构建，并选择性吸收方案 C 的资产绑定隔离思想（内部字段隔离，暂不分离版本化）。

### 核心实体关系

- **Artifact（抽象）**
  定义内容类别，如 `script`、`storyboard`、`shot_prompt`、`asset_binding`（后期可引入）。

- **Revision**
  不可变快照，包含：
  - `content_object_id`：指向实际存储的 JSON 对象（或资产引用片段）
  - `content_hash`：对权威内容的哈希（对于 Shot Prompt，仅包含 `prompt_components` 和 `assets.references`，不包含渲染输出）
  - `artifact_type`
  - `parent_revision_id`（可选，用于链接到上一版本）
  - `renderer_version`（仅当此 Revision 由 Renderer 生成时，如 Storyboard Markdown 输出）
  - `created_at`
  - `dependencies`：引用的其他 Revision ID 列表（例如 Storyboard 引用 Script Revision）

- **Bundle Outputs（派生输出）**
  对给定 Shot Prompt Revision 产生的关联文件清单：
  - `canonical_json`：Shot Prompt 权威内容（可能嵌入或引用）
  - `rendered_markdown`
  - `rendered_prompt`（正面）
  - `negative_prompt`
  每个输出文件有独立 content-addressed ID，并记录生成它的 `renderer_version` 和引用源 `source_revision_id`。

- **Approval**
  对象是 `(artifact_id, revision_id)` 元组，表明某个 Revision 被批准。包含批准类型：
  - `content_approval`：创作内容审批
  - `execution_approval`：执行就绪审批（在资产绑定和环境检查通过后）

- **Freshness**
  基于依赖链的哈希树校验：
  - Storyboard Shot Freshness 依赖于上游 Script Revision
  - Shot Prompt Freshness 依赖于 Storyboard Shot Revision 和资产引用状态
  - 若任何上游 content_hash 变更，下游状态自动标记为 `stale`

- **Asset Binding（内嵌在 Shot Prompt Revision 中）**
  记录资产引用列表，每条包含：
  - `asset_identifier`（符合命名规范）
  - `binding_type`（角色、道具等）
  - `status`（`pending`/`partially_bound`/`bound`/`stale`）
  - `bound_version`（本地文件哈希或版本号）
  - `verified_at`（仅当 Registry 存在时可自动设置）

- **Execution Readiness（派生状态）**
  非独立 Artifact，而是从 Shot Prompt Revision 计算出的状态：
  - 检查内容已审批
  - 检查资产绑定状态为 `bound` 且 Freshness 通过
  - 检查 Renderer 输出与 Canonical 内容一致性
  - 存储为 Revision 的元数据或独立的 Readiness Check Record

---

## 6. Recommended Canonical JSON

以下为 Shot Prompt Canonical JSON 字段骨架，标注生成来源。**所有执行和平台字段已移除**。

```json
{
  "schema_version": "1.0",

  "content": {
    "prompt_components": {                         // 模型生成/人工创作
      "subject": "a warrior in a forest",
      "action": "drawing a sword",
      "lighting": "golden hour backlight",
      "camera": "low angle, 35mm lens",
      "style": "cinematic, photorealistic"
    },
    "storyboard_ref": {                            // 系统自动（来自上游）
      "storyboard_revision_id": "<hash>",
      "shot_id": "shot_03"
    },
    "duration": {                                  // 来自 Storyboard
      "source_shot_duration_sec": 5.0,
      "unit_duration_sec": 5.0,
      "deviation_reason": null
    },
    "split_info": {                                // 人工创作（仅当拆分时）
      "is_split": false,
      "parent_unit_id": null,
      "child_unit_ids": []
    }
  },

  "assets": {
    "status": "pending",                           // 系统管理
    "references": [                                // 人工/系统：资产标识符
      {
        "asset_identifier": "char_hero_v2",
        "role": "subject",
        "bound_version": null,
        "verified": false,
        "verified_at": null
      }
    ]
  },

  "meta": {
    "canonical_hash": "<sha256-of-content-and-assets>",  // 系统计算
    "created_at": "2026-06-28T12:00:00Z"
  }
}
```

**关键说明**：
- **不存储** `rendered_prompt`、`negative_prompt`、`markdown`：这些由 Renderer 生成，作为派生输出独立存储。
- **不存储** `generation_strategy`、`frame_requirements`：属于执行规划层，应移出。
- **不存储** `execution_targets`：平台信息在执行时由 Adapter 注入。
- **审批对象**：仅为 `content` 和 `assets` 的 Canonical JSON，派生输出不参与内容审批（仅参与执行就绪检查）。
- **资产引用**中的 `verified` 字段在当前无 Registry 时只能为 `false` 或由人工设置，需在 UI 明确警示。

---

## 7. State Machine

### 7.1 Shot Prompt Revision 生命周期

```
                  +--------+
                  | Draft  |
                  +--------+
                    |    |
          submit for review  |
                    |        |
                    v        v
          +----------------+   +-------------------+
          | Content Review |   | Asset Update Only | (轻量资产更新)
          +----------------+   +-------------------+
              |       |                |
    approve   |       | reject         | (生成新 Revision，自动进入资产状态检查)
              v       v                v
   +------------------+    +------------------+
   | Content Approved |    | Content Rejected |
   +------------------+    +------------------+
            |                      |
            |                      v
            |             (resubmit) --> Draft
            v
   +---------------------+
   | Execution Pending   | (自动进入，检查资产和环境)
   +---------------------+
        |            |
   all assets bound    assets missing/unverified
        v                v
 +-----------------+   +-------------------+
 | Execution Ready |   | Execution Blocked |
 +-----------------+   +-------------------+
        |
        v
  +----------+
  | Executed | (Adapter 成功运行后)
  +----------+
        |
        v (runtime errors)
  +-----------------+
  | Execution Failed|
  +-----------------+
```

**非法转换**：
- `Content Approved` 不能直接到 `Executed`（必须经过 `Execution Ready`）
- `Content Approved` 不能直接修改内容字段后仍保持同一 Revision
- `bound` 不能直接变为 `pending`，必须先变成 `stale`
- 不能从 `Executed` 或 `Execution Failed` 回到 `Draft`（必须创建新 Revision）

### 7.2 Asset Binding 子状态

```
pending --> partially_bound --> bound
bound --> stale (上游资产 Revision 或本地文件变更)
stale --> (重新 bind) --> partially_bound / bound
```

---

## 8. Validator Matrix

| 验证规则 | 类型 | 触发条件 |
|-----------|------|----------|
| `prompt_components` 必须包含 `subject` 和 `action` | required | 创建/更新 Draft |
| `storyboard_ref` 必须指向已批准 Storyboard 的 Revision | required | 提交内容审批 |
| `duration.unit_duration_sec` 与源镜头偏差 ≤ 允许范围（由平台 Adapter 配置决定，不在核心硬编码） | conditional | 当 `split_info.is_split=true` 时 |
| 1:N 拆分时，子 Unit 的 `parent_unit_id` 必须引用有效 Prompt Unit | required | 创建子 Unit |
| 禁止 N:1 合并（多个 `parent_unit_id` 指向同一子 Unit） | forbidden | 任何写入 |
| `assets.references` 中每个 `asset_identifier` 必须符合命名规范 `[a-z0-9_]+` | conditional | 提交执行就绪检查 |
| 若 `assets.status == "bound"`，所有 `references` 必须非空且 `bound_version` 不为 null | required | 状态转换至 `bound` |
| Renderer 派生输出必须与 Canonical Hash 匹配（重新生成时校验） | required | 执行准备检查 |
| 派生输出存在时，其 `renderer_version` 必须与系统注册 Renderer 版本兼容 | conditional | 执行准备检查 |
| 不能对已审批的 Revision 修改 `content` 字段；资产更新必须创建新 Revision | forbidden | 任何更新操作 |
| `split_info.is_split=false` 时，`child_unit_ids` 必须为空 | required | 验证 |
| `meta.canonical_hash` 必须等于对 `content` 和 `assets` 的确定性序列化哈希 | required | 任何 Revision 写入前 |

---

## 9. Failure Scenarios

1. **Storyboard Markdown 解析歧义**
   用户修改 Markdown 格式，解析器抽取 Shot 信息偏移，导致 Prompt Unit 静默变化，执行时生成错误画面。

2. **Renderer 版本升级导致输出漂移**
   已审批 Shot Prompt 的派生输出与新 Renderer 输出不一致，但 Canonical 未变，执行时使用新 Renderer 生成不同结果，破坏可复现性。

3. **资产标识符重名或版本混淆**
   `asset_identifier` 未遵循全局唯一规则，绑定操作指向错误资产，`bound` 状态实际上虚假。

4. **依赖链断裂**
   上游 Script Revision 被删除或替换，Storyboard 仍引用旧 Revision，Freshness 检查失败但未能阻止执行。

5. **并发资产更新（本地多进程或多线程）**
   资产文件在绑定验证和实际执行之间被修改，`bound` 状态过时，执行使用了错误版本。

6. **内容审批与执行就绪混淆**
   审批人批准了内容，但资产未绑定，若状态机实现不当直接跳至 `Execution Ready`，引发空绑定运行。

7. **±2 秒偏差累积**
   多个子 Unit 各自偏差导致总时长超出下游平台容忍值，Adapter 拒绝执行，但上游已审批通过。

8. **N:1 合并误操作（未来放松约束时）**
   现有模型无法表达溯源，导致资产绑定和责任链混乱。

9. **Renderer 确定性假设崩溃**
   Renderer 内部使用了非固定种子随机数或依赖外部模型快照，`negative_prompt` 非确定性生成，跨环境无法复现。

10. **Bundle Hash 未包含 Renderer 版本**
    两个环境 Renderer 版本不同，生成内容不同但 Bundle Hash 相同，缓存/分发错误。

11. **资产 Registry 未就绪时绑定验证缺失**
    `bound` 状态仅由人工标记，但人工标记丢失或错误，执行时引用不存在的资产。

12. **Migration 脚本错误**
    Storyboard Markdown 转 JSON 时丢失自定义字段，导致历史项目不可用。

13. **execution_targets 占用 Canonical 空间**
    未来引入新平台时，必须修改 Canonical Schema，导致所有存量 Revision 需要迁移（若未按建议移除）。

14. **Prompt Content 与资产绑定捆绑版本化**
    微小资产版本更新强制创建内容 Revision，审批流拥堵，用户绕过审批直接修改执行参数。

15. **Split 约束由 Canonical 硬编码**
    若将 ±2 秒或禁止 N:1 写死在核心校验，后续平台需要不同规则时，被迫分叉核心逻辑。

16. **未定义 negative_prompt 生成失败行为**
    Renderer 产生空或格式错误 negative prompt，执行器静默失败或崩溃。

17. **Storyboard JSON 与 Markdown 视图不同步**
    若 Markdown 导出器实现有误，用户查看的 Markdown 视图与结构化 JSON 不一致，审批基于错误视图。

18. **资产绑定轻量 Revision 未触发执行就绪重新检查**
    资产更新后生成新 Revision，但状态仍残留 `Execution Ready`，导致使用旧输出执行。

---

## 10. Delivery Sequence

### 阶段 0：基础设施准备（若尚未就绪）
- 确认 immutable object storage 和内容寻址可靠
- 统一哈希算法和序列化规范（JSON Canonicalization）
- 提供本地资产文件哈希工具
- **退出条件**：所有组件可计算并验证内容哈希

### 阶段 1：Storyboard Canonical JSON（先决条件）
- **交付物**：
  - Storyboard JSON Schema（包含 Shot 结构、时长、依赖）
  - Markdown → JSON 迁移工具（解析现有 Markdown 并生成 JSON，附带人工校验界面）
  - JSON → Markdown 视图生成器（保持现有 Markdown 外观，确保用户可读）
  - 更新 Storyboard Revision 类型，使用 JSON 作为 content_object
- **退出条件**：
  - 所有现有 Storyboard Revision 成功转换为 JSON 且 Freshness 检查通过
  - Storyboard 审批流程基于 JSON（Markdown 仅作为只读视图）
- **不交付**：任何 Shot Prompt 相关功能

### 阶段 2：Shot Prompt 极简核心（MVP 真实范围）
- **交付物**：
  - Shot Prompt Canonical JSON Schema（仅 content、assets、meta）
  - 确定性 Renderer（版本锁定，输入 Canonical JSON，输出 Markdown、prompt_positive、prompt_negative）
  - 派生输出存储和 Bundle 结构（Canonical Hash + 派生文件清单）
  - 内容审批流程（人工审批 Canonical JSON，不审批派生输出）
  - 执行就绪状态派生（检查资产绑定状态和 Renderer 输出一致性，但不要求 Registry 自动验证）
- **退出条件**：
  - 可从已批准 Storyboard Shot 创建 Shot Prompt Draft
  - 通过 Renderer 生成派生输出，Bundle 完整性校验通过
  - 审批流闭环：提交 → 内容审批 → 执行就绪（人工确认资产或本地校验通过）
- **不交付**：自动资产绑定验证、多平台 Adapter、执行字段

### 阶段 3：资产绑定基础（过渡方案，不依赖外部 Registry）
- **交付物**：
  - 本地资产引用表（SQLite）替代 Registry，存储资产标识符和文件哈希
  - 资产绑定状态机（pending/partially_bound/bound/stale）
  - `bind-assets` 确定性算法：基于资产标识符匹配本地文件，计算哈希，更新 `bound_version`
  - 资产更新触发轻量 Revision（仅资产片段变化，prompt_components 不变）
- **退出条件**：
  - 用户可为 Shot Prompt 声明资产引用，执行 `bind-assets` 检测本地文件并更新状态
  - 执行就绪检查因资产缺失或未绑定而阻塞
  - 资产更新可生成新 Revision，且不强制重新进行内容审批（可选）
- **不交付**：与外部 Visual Asset Registry 集成、远程资产解析

### 阶段 4：执行规划与多平台（后续迭代，非 MVP）
- **交付物**：
  - Execution Planning Artifact（包含 generation_strategy、frame_requirements 等）
  - 平台 Adapter 接口和 LibTV/Agnes 具体实现，使用 Storyboard JSON 和 Shot Prompt Canonical 生成平台特定 payload
- **退出条件**：端到端可执行；但此阶段明确不属于当前 MVP

---

## 11. What Not To Build Yet

1. **Visual Asset Registry 完整集成**：仅使用本地 SQLite 资产表作为过渡，不设计外部 Registry 协议和 API。
2. **多用户协作、审批工作流引擎**：保持单用户，审批为本地标志位，不引入角色、签名、通知。
3. **平台 Adapter 的完整实现**：仅定义接口和占位，不实现 LibTV/Agnes 的真实对接。
4. **自动资产验证和远程解析**：资产 `bound` 状态仅基于本地文件存在和哈希，不执行远程调用或外部服务。
5. **Prompt Content 与 Asset Binding 的完全分离版本化**：资产绑定作为 Shot Prompt Revision 的内部片段，暂不拆分为独立 Artifact。
6. **generation_strategy 和 frame_requirements 的复杂策略引擎**：这些字段不应出现在 Canonical 中；如需携带，暂存于独立 Execution Planning 表，但不构建策略解析器。
7. **execution_targets 的多平台结构**：Canonical 中不预留任何平台字段；未来扩展时，在 Execution Planning 中按平台添加。
8. **±2 秒偏差的自动校验与重分配逻辑**：仅进行人工录入校验，不构建自动时间补偿；偏差容限移至平台 Adapter 配置。
9. **Renderer 的热更新和兼容性矩阵**：初期只支持单一 Renderer 版本，硬编码；版本升级时要求用户手动重新生成所有派生输出。
10. **N:1 合并的任何支持**：明确禁止，不在模型中预留。
11. **revision_outputs 通用抽象**：不使用通用的输出容器；明确命名每种输出类型。

---

## 12. Decision Table

| 决策 | 推荐 | 理由 |
|------|------|------|
| 是否应先升级 Storyboard 为 JSON Canonical？ | **是，作为前提** | 消除解析歧义，保障全链路可复现和审批一致性，是所有后续工作的基础 |
| Markdown 解析 Storyboard 是否可接受？ | **仅过渡期，最终必须替换** | 短期可用以导入历史，但必须提供迁移到 JSON 的明确路径 |
| revision_outputs 是否必要？ | **否，使用明确命名的输出对象** | 避免过早抽象；当前明确输出类型比通用容器更清晰，利于 Hash 和审批 |
| Canonical JSON 是否存 rendered_prompt？ | **否，仅存派生输出引用** | 保证内容寻址不变性；渲染输出应独立存储，关联 Canonical Hash 和 Renderer 版本 |
| negative_prompt 能否完全确定性？ | **不能信任，须明确生成规则并版本化** | 将其视为 Renderer 输出，记录规则版本；确定性假设必须通过严格测试验证 |
| Bundle Hash 策略 | **仅 Hash Canonical 内容 (prompt_components + assets.references)** | 派生内容不应参与 Canonical 哈希；Hash 变更只反映内容或资产引用变化 |
| Renderer 版本变化处理 | **要求 Renderer 版本成为派生输出元数据，与 Canonical Hash 解耦** | 版本变化触发重新生成和重新执行准备检查，但 Canonical Hash 不变 |
| 资产绑定状态无 Registry | **有意义但需清晰标记为“未验证”** | 提供人工绑定追踪价值，但状态不可信；需在 UI/日志中明确警告 |
| bound 状态虚假可信 | **高概率，必须引入 binding verification record** | 每次绑定验证应保存快照（文件哈希、时间戳），否则 `bound` 仅为声明 |
| 资产绑定变化需新 Revision？ | **是，但应允许轻量 Revision（仅资产片段变化）** | 完全避免新 Revision 会失去审计追踪；但区分“内容修订”和“资产修订”可减轻审批负担 |
| Prompt Revision 与 Asset Binding Revision 分离？ | **MVP 不分离，但内部隔离字段；未来视 Asset Registry 进展分离** | 当前分离成本高于收益，但设计上预留迁移空间 |
| content approval 与 execution readiness 是否同一 Artifact？ | **分离关注点，但作用于同一 Revision** | Approval 类型区分；Readiness 是状态推导，不独立成 Artifact |
| execution_targets 应出现在 Canonical 中？ | **绝对不应** | 破坏中立性，引入平台耦合，必然后续重构；应在 Adapter 层注入 |
| 固定 LibTV/Agnes 是否破坏中立？ | **是，严重破坏** | Canonical Core 若预留特定平台字段，即非中立；应完全移除 |
| ±2 秒偏差硬编码？ | **移至平台 Adapter 配置** | 不同平台容忍度不同；Canonical 应只记录绝对时长和偏差值，校验逻辑由 Adapter 执行 |
| generation_strategy 归属 | **移出 Shot Prompt，归属 Execution Planning** | 属于“如何生成”，而非“生成什么”；防止核心模型膨胀 |
| frame_requirements 侵入 | **是，会侵入 Image Prompt Skill 边界** | 技术参数不应在内容创作层定义，应在执行规划时根据平台和 Skill 约束添加 |
| bind-assets 字段修改保护 | **通过内容寻址和部分 Hash（仅资产片段）实现** | 修改资产字段时，仅资产片段 Hash 变化，Canonical 整体 Hash 随之变化，但可通过 UI 区分变化范围 |
| MVP 承担过多未来责任 | **是，显著过度设计** | execution_targets、通用 revision_outputs、复杂执行字段均为超前设计 |
| 最小技术债方案 | **方案 B 作为基础，辅以严格的字段移除（执行字段、平台预留等）** | 先 JSON 化 Storyboard，然后实现极简 Shot Prompt Canonical，所有非内容字段全部推迟 |

---

**最终建议**
立即暂停 Shot Prompt 直接开发，优先在一个受保护分支完成 Storyboard JSON Canonical 升级，并基于该分支重新设计 Shot Prompt Canonical，严格剔除所有执行和平台相关字段。最小可交付 MVP 应为：
**Storyboard JSON + 极简 Shot Prompt Canonical（仅有 prompt_components 和资产引用声明）+ 单一确定性 Renderer + 单用户内容审批**。
所有资产验证自动化、多平台适配、执行策略，均属后续迭代，不得纳入当前范围。