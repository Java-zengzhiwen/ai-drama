# Shot Prompt Workflow MVP 架构评审

评审时间：2026-06-28
仓库当前 HEAD：`5fdc7917cac78a96ff4ae222df562d39f453f662`
工作区状态：clean
当前测试数量：`92`（`python3 -m pytest --collect-only -q`）

## 1. Executive Verdict

**GO WITH PREREQUISITE**

结论：当前仓库可以作为 Shot Prompt Workflow MVP 的实现底座，但**不能直接在现有 Storyboard Markdown 路径上继续堆 Shot Prompt**。必须先补齐 Canonical JSON、`revision_outputs`、Renderer 边界、approval/readiness 分离和 asset binding 语义，否则后续会把 markdown 逻辑债、审批语义债和执行目标债一起带入。

### 当前仓库事实

- 运行时目前只声明两条执行 профиля：`markdown-script-mvp-v1` 和 `storyboard-markdown-mvp-v1`，且明确不包含 Shot Prompt / LibTV / Agnes / downstream execution。证据见 `README.md:3-23`、`skills/ai-drama-storyboard-design-skill/v0.1.0/skill.json:179-194`。
- Storyboard 目前是 Markdown-first，解析器只接受 Markdown 结构，不存在 Canonical JSON 输入模型。证据见 `ai_drama_runtime/parser.py:35-56`、`ai_drama_runtime/request.py:133-167`。
- 运行时已有“approved source script -> storyboard revision -> validators -> approval -> export”闭环。证据见 `ai_drama_runtime/services.py:216-371`、`ai_drama_runtime/services.py:373-535`。

## 2. Repository Evidence

### 2.1 当前运行时支持的 artifact types

- `README.md:5-18` 明确当前 profile 仅有 `markdown-script-mvp-v1` 和 `storyboard-markdown-mvp-v1`，并写明不支持 Shot Prompt、LibTV、Agnes。
- `skills/ai-drama-storyboard-design-skill/v0.1.0/skill.json:179-194` 只声明 `storyboard_markdown`，并把 `shot_prompt_package`、`libtv_execution_package`、`agnes_execution_package` 列为 `unsupported_bundle_artifacts`。
- `ai_drama_runtime/request.py:92-98`、`ai_drama_runtime/request.py:154-160` 里输出契约仍是 `markdown` + parser_version，而不是 canonical bundle。

### 2.2 当前 Storyboard 执行和审批模型

- `ai_drama_runtime/services.py:216-239`：Storyboard 运行必须给 `--source-revision`，源 revision 必须存在、是 drama script、已批准、且仍是当前批准版本。
- `ai_drama_runtime/services.py:240-371`：Storyboard run 会构建请求、写入 run/revision、插入 `revision_dependencies`，再执行 validators。
- `ai_drama_runtime/services.py:373-390`：审批要求 run status 只能是 `SUCCEEDED` 或 `VALIDATION_FAILED`，并且 required validators 必须全部 `PASS`，否则审批阻断。
- `ai_drama_runtime/services.py:417-428`：freshness 是动态计算的，只看当前批准的上游 script revision 是否仍是 source。
- `ai_drama_runtime/services.py:483-535`：export 会再次检查 freshness，过期 storyboard 不允许导出。

### 2.3 当前 validator 和包模型

- `ai_drama_runtime/validators.py:69-191`：validator 执行结果会被持久化，`NOT_APPLICABLE`、`SKIPPED_DEPENDENCY_MISSING`、`FAIL`、`PASS` 都是显式状态。
- `skills/ai-drama-storyboard-design-skill/v0.1.0/skill.json:43-170`：Storyboard 包只有结构、时长、源覆盖、连续性、genericity 五个 validators。
- `tests/test_storyboard_workflow.py:45-66`、`tests/test_validators_approval_export.py:65-93`：现有测试已经把 `NOT_APPLICABLE`、required validator 阻断审批、导出冲突等语义固化下来。

### 2.4 当前测试基线

- `python3 -m pytest --collect-only -q` 收集到 `92` 个测试。
- `tests/acceptance/test_storyboard_workflow_acceptance.py:21-83` 还在检查 report 本地化、`tested_commit_sha`、`tested_worktree_clean`、direct/verifier pytest 分拆和 skipped 原因。

## 3. Critical Findings

### BLOCKER

1. **当前 Storyboard 不是 Canonical JSON，不能直接作为 Shot Prompt 的权威源。**
   现在的请求和输出仍是 Markdown-first：`ai_drama_runtime/request.py:133-167` 只构造 Markdown 输出契约，`ai_drama_runtime/parser.py:35-56` 只做 Markdown 结构校验。Shot Prompt 需要 JSON 唯一权威源，这里必须先补。

2. **缺少 `revision_outputs` 这一层，无法表达 bundle 成员和派生输出。**
   当前 `revisions` 表只保存一个 `content_object_id`（`ai_drama_runtime/store.py:220-239`、`ai_drama_runtime/store.py:495-516`），无法稳定表达 canonical JSON、rendered Markdown、negative prompt、execution target artifacts 这些 bundle 成员。

3. **approval 和 readiness 目前耦合过紧。**
   `ai_drama_runtime/services.py:373-390` 把 required validators 结果直接当作审批前置条件；`ai_drama_runtime/services.py:483-535` 又把 freshness 直接绑定到 export。Shot Prompt 需要把“内容批准”和“执行就绪”分开，否则 asset binding、target readiness、renderer parity 都会挤进同一个审批阀门。

### HIGH

1. **`run create` 分发机制过于粗糙。**
   `ai_drama_runtime/cli.py:66-109` 只靠 `--input` vs `--source-revision` 分支，适合当前两条链路，不适合 Shot Prompt 这种 canonical package + binding revision + target export 的多阶段工作流。

2. **没有 Renderer 边界。**
   现在“生成什么”和“怎么渲染成 Markdown”都混在 runtime/service/request 里，无法保证字节级确定性，也不利于跨 target 复用。

3. **`bound` 语义当前无法可信验证。**
   仓库里没有 Visual Asset Registry，只有 Storyboard 上游 script 绑定和 provenance。没有 registry 时，`bound` 只能做局部一致性检查，不能做外部可信验证。

### MEDIUM

1. **`execution_targets` 目前应做成可扩展注册表，不应在 schema 里硬编码为 libtv/agness。**
2. **`bind-assets` 派生 revision 需要路径白名单与 hash 链限制，否则容易演化成“半重跑模型”。**
3. **旧 Storyboard Markdown 需要兼容层，否则历史 revisions 无法平滑迁移到 canonical bundle。**

### LOW

1. **当前 genericity validator 只覆盖 skill package，不覆盖 future Shot Prompt bundle。**
2. **现在的 export 仍是单文件 markdown + provenance sidecar，bundle 原子性不足。**

## 4. Three Architecture Options

### A. 直接从 Storyboard Markdown 开发 Shot Prompt

- 修改范围：最小。
- 技术债：最高。会把 markdown 语义、渲染规则、绑定状态、审批状态全黏在一起。
- 测试成本：短期最低，长期最高。
- 数据可靠性：弱。Markdown 不是唯一权威源。
- 后续流水线适配：差。后面再补 JSON、bundle、renderer 会二次重构。
- 回滚难度：中等，逻辑上很难干净回滚，因为数据模型会已经污染。

### B. 先升级 Storyboard JSON Canonical

- 修改范围：中等，先把 Storyboard 变成 canonical JSON + deterministic renderer，再做 Shot Prompt。
- 技术债：最低。把权威源、渲染器、导出物分开，后面 Shot Prompt 可以复用同一套 bundle 机制。
- 测试成本：中等，但一次性把关键语义钉死。
- 数据可靠性：高。JSON 作为唯一事实源。
- 后续流水线适配：最好。Shot Prompt、Visual Anchor、Image Prompt、LibTV/Agnes 都能共用 bundle/revision 模型。
- 回滚难度：低到中。只要兼容 legacy markdown revision 即可。

### C. Shot Prompt 内部临时 Normalization

- 修改范围：看起来最小，实际上会把规范化逻辑藏进 Shot Prompt 内部。
- 技术债：很高。canonical 逻辑隐蔽，后面会反复重复。
- 测试成本：前期低，后期高。
- 数据可靠性：中等偏低。双写/双解释风险大。
- 后续流水线适配：一般。
- 回滚难度：高。很容易依赖内部 normalization 行为，难拆。

**推荐：B**

原因：当前仓库已经证明 Storyboard 这条链路可以跑通，但 Shot Prompt 需要更严格的权威源、bundle 和 readiness 语义。先把 Storyboard 升级为 JSON Canonical + Markdown Renderer，是最少返工的路径。

## 5. Recommended Architecture

### 5.1 Artifact model

- `Storyboard Shot Prompt Revision` 应该成为一类 bundle artifact。
- canonical JSON 是唯一权威源。
- Markdown、negative prompt、rendered prompt 都是确定性派生物。
- 一个 revision 可以包含多个 bundle member，成员通过 `revision_outputs` 管。

### 5.2 Revision model

- revision 记录“谁生成的、基于谁、当前状态是什么”。
- canonical content 变了就是新 revision。
- asset binding 变了也必须新 revision。
- readiness 失败不应修改 canonical content 本身。

### 5.3 `revision_outputs` 表建议

建议把 bundle 成员从 `revisions.content_object_id` 迁移到独立表：

| column | purpose |
|---|---|
| `output_id` | 主键 |
| `revision_id` | 外键 |
| `output_kind` | `canonical_json` / `rendered_markdown` / `negative_prompt` / `binding_manifest` / `approval_manifest` 等 |
| `member_key` | bundle 内成员名 |
| `content_object_id` | 对象存储引用 |
| `content_hash` | SHA-256 |
| `mime_type` | `application/json` / `text/markdown` 等 |
| `renderer_name` | 生成者 |
| `renderer_version` | 版本钉死 |
| `is_canonical_source` | 是否权威源 |
| `created_at` | 审计时间 |

兼容策略：
- 旧 `revisions.content_object_id` 先保留为 legacy rendered markdown。
- 老版本 backfill 时只补 `rendered_markdown`，`canonical_json` 可先为空或由迁移脚本生成。
- 新 revision 必须写入 `canonical_json`，再由 renderer 生成 markdown。

### 5.4 Canonical JSON boundary

- canonical JSON 只能包含业务状态和生成策略，不包含时间戳、随机 ID、运行耗时等可变字段。
- 只允许 schema 定义的字段进入 canonical。
- 所有 derived text 只能从 canonical JSON 生成，不允许反向回写 canonical。

### 5.5 Renderer boundary

- Renderer 应放在 **Runtime**，不是 Skill Package。
- Skill Package 只声明 schema、字段顺序、约束和版本。
- Runtime 持有唯一 renderer 实现，保证字节级一致。

### 5.6 Freshness model

- freshness 不看“revision 创建时间”，只看 upstream approved source revision 是否仍是 current approved。
- derived revision 链要可追踪，任何上游 approved 变化都可让下游变 stale。

### 5.7 Approval / readiness model

- `content_approved`: 内容通过，说明 canonical JSON / prompt components 通过审查。
- `execution_ready`: 目标绑定、资产状态、renderer parity、required validators、target prerequisites 都满足。
- 内容批准和执行就绪必须是两条独立状态线。

### 5.8 Asset binding model

- binding 状态允许：`pending` / `partially_bound` / `bound`。
- 没有 Visual Asset Registry 时，不应把 `bound` 当成可外部可信验证状态。
- `bound` 必须依赖已批准的资产记录或 registry-backed proof。

### 5.9 Execution target model

- 核心层只定义 target contract，不硬编码 libtv/agness。
- `libtv`、`agnes` 可以是首批 target adapter，但不能锁死在 schema 里。

## 6. Proposed Schema Skeleton

```json
{
  "schema_version": "shot-prompt-package-v1",
  "artifact_type": "shot_prompt_revision",
  "revision": {
    "revision_id": "",
    "parent_revision_id": "",
    "revision_kind": "initial|derived_bind_assets|derived_render_only",
    "created_at": ""
  },
  "source": {
    "storyboard_revision_id": "",
    "storyboard_revision_hash": "",
    "storyboard_approval_record_id": "",
    "source_freshness_status": "FRESH|STALE"
  },
  "prompt_components": {
    "shots": [],
    "units": [],
    "scene_map": [],
    "shot_unit_map": []
  },
  "generation_strategy": {
    "policy_version": "",
    "split_policy": "1:1|1:N",
    "merge_policy": "forbidden",
    "duration_tolerance_seconds": 2
  },
  "frame_requirements": {
    "per_unit": [],
    "per_shot": [],
    "camera_lock": true
  },
  "asset_bindings": [
    {
      "asset_id": "",
      "asset_revision_id": "",
      "binding_state": "pending|partially_bound|bound",
      "binding_proof_hash": ""
    }
  ],
  "execution_targets": [
    {
      "target_id": "libtv",
      "readiness_status": "not_ready|ready|blocked",
      "adapter_version": "",
      "export_artifact_ref": ""
    }
  ],
  "rendering": {
    "renderer_name": "",
    "renderer_version": "",
    "rendered_prompt_hash": "",
    "negative_prompt_hash": "",
    "markdown_hash": ""
  },
  "provenance": {
    "content_approval_record_id": "",
    "execution_readiness_record_id": "",
    "validator_result_hash": "",
    "bundle_hash": ""
  }
}
```

## 7. Proposed CLI

建议把 Shot Prompt 做成独立命名空间，而不是继续扩张 `run create`：

```bash
ai-drama shot-prompt create --source-storyboard REVISION_ID
ai-drama shot-prompt bind-assets SHOT_PROMPT_REVISION_ID --asset-map path/to/map.json
ai-drama shot-prompt approve-content SHOT_PROMPT_REVISION_ID
ai-drama shot-prompt mark-ready SHOT_PROMPT_REVISION_ID --target libtv
ai-drama shot-prompt export SHOT_PROMPT_REVISION_ID --target libtv --output out/
```

稳定错误码建议：

- `2`：输入参数错误 / gate failure
- `3`：not found
- `4`：runtime / parse / renderer execution error
- `5`：validation failed
- `6`：approval blocked
- `7`：export conflict / atomicity failure
- `8`：readiness blocked

## 8. Validator Matrix

| validator | required | input | responsibility | failure condition |
|---|---:|---|---|---|
| `shot_prompt_schema` | yes | canonical JSON | JSON schema / required fields | schema mismatch / missing required keys |
| `shot_prompt_renderer_parity` | yes | canonical JSON + renderer | rendered bytes must match deterministic renderer | markdown/hash mismatch |
| `shot_prompt_unit_mapping` | yes | shots + units | verify 1:1 default, allow 1:N, forbid many shots -> one unit | merge detected / orphan unit / duplicate parentage |
| `shot_prompt_duration` | yes | shot/unit durations | enforce total duration and ±2s tolerance | missing duration / out of bounds / drift too large |
| `shot_prompt_source_freshness` | yes | source revision chain | reject stale sources | upstream approved source changed |
| `shot_prompt_asset_binding` | yes | asset bindings | enforce pending/partial/bound semantics | illegal state or unverified bound |
| `shot_prompt_execution_targets` | yes | target registry + bundle | target readiness for libtv/agness/others | missing adapter / unsupported target |
| `shot_prompt_genericity` | no | package text | block downstream leakage terms | forbidden term found |
| `shot_prompt_approval_gate` | yes | content+readiness records | ensure approval only when content and readiness both pass | any required record missing/failing |

## 9. Database Migration

### New tables

1. `revision_outputs`
2. `revision_asset_bindings`
3. `revision_readiness_records` 或 `revision_decisions`
4. `execution_target_records`

### Recommended indexes

- `revision_outputs(revision_id, output_kind)`
- `revision_outputs(content_hash)`
- `revision_asset_bindings(revision_id, binding_state)`
- `revision_readiness_records(revision_id, target_id)`

### Compatibility strategy

- 保留 `revisions` 表和旧 `content_object_id`。
- 新 revision 以 `revision_outputs` 为主。
- 旧 storyboard revision backfill 时，`content_object_id` 映射成 `rendered_markdown`；canonical JSON 如无可靠来源，不强行伪造。
- 增加 feature flag，旧 CLI 仍可读 legacy markdown，直到迁移完成。

### 回滚风险

- 低：如果只做 additive migration。
- 中：如果强制把旧 markdown retrofit 成 canonical JSON。
- 高：如果在同一迁移里同时更改 approval/readiness 语义。

## 10. Acceptance Test Matrix

| case | expected |
|---|---|
| 正常生成 | canonical JSON + markdown + bundle member hashes 全通过 |
| 未批准 Storyboard | gate fail / approval blocked |
| stale Storyboard | approval/export blocked |
| 漏镜 | coverage validator fail |
| 非法合并 | unit mapping validator fail |
| 拆分顺序错误 | unit order validator fail |
| 时长偏差 | duration validator fail when drift > ±2s |
| Renderer 不一致 | renderer parity fail |
| pending/partial/bound | 状态机校验通过或阻断非法跳转 |
| bind-assets no-op | no-op should be idempotent and produce same hash or explicit conflict policy |
| bind-assets 非法路径变化 | path whitelist fail |
| Bundle 导出失败回滚 | staging cleanup + no partial final bundle |
| 上游重新批准导致下游 stale | freshness turns stale, approval/export blocked |

## 11. Recommended Delivery Phases

### Phase 0: 规范冻结

- 目标：冻结 canonical JSON、bundle member、rendering、binding、readiness 语义。
- 文件范围：`docs/reviews/`、`docs/superpowers/specs/`、相关设计文档。
- 退出条件：字段名、状态机、错误码、validator matrix 固化。

### Phase 1: Storyboard Canonicalization

- 目标：把 Storyboard 从 markdown-first 提升为 canonical JSON + deterministic markdown renderer。
- 文件范围：runtime request/parser/services/store/tests。
- 退出条件：现有 storyboard 用 canonical JSON 驱动，markdown 只是派生物。

### Phase 2: `revision_outputs` + export bundle

- 目标：把 bundle 成员拆出，支持 atomic export。
- 文件范围：store、export、migration、tests。
- 退出条件：多成员输出可持久化、可比较、可原子导出。

### Phase 3: Approval / readiness split

- 目标：内容批准和执行就绪分离。
- 文件范围：services、validators、CLI、tests。
- 退出条件：content-approved 但 not-ready 的 revision 可以被识别，但不能导出/执行。

### Phase 4: Asset binding

- 目标：引入 pending / partially_bound / bound，并支持 `bind-assets` 派生 revision。
- 文件范围：asset binding 模型、CLI、migration、tests。
- 退出条件：绑定变更只改允许路径，且生成新 revision。

### Phase 5: Shot Prompt target adapters

- 目标：接入 libtv / agnes 等 execution targets。
- 文件范围：adapter zone、target registry、tests。
- 退出条件：target readiness 和 export contract 稳定。

## 12. Open Questions

只保留仓库里无法严格定死的问题：

1. Shot Prompt canonical JSON 的最终字段命名是否要与 Storyboard Canonical 完全共用一套 `revision_outputs` schema。
2. `approval` 是否要拆成两个持久化记录：`content_approval` 和 `execution_readiness_approval`，还是只拆状态不拆表。
3. `bind-assets` 产生的派生 revision 是否允许继承 content approval，只重算 readiness。
4. 旧 Storyboard markdown 是否需要在迁移中“结构化回填”成 canonical JSON，还是只作为 legacy 输出保存。
5. 首批 execution targets 是否只落 `libtv` 和 `agnes` 两个适配器，还是保留更宽的 target registry 接口但不实现。

## 13. Final Notes

- 当前仓库对 Storyboard 的支持已经足够证明“approved script -> storyboard revision -> validators -> approval/export”的生命周期是可行的，见 `ai_drama_runtime/services.py:216-535`。
- 但 Shot Prompt 需要的是“JSON authority + bundle + renderer + binding + readiness”这一层次，不是继续在 markdown 上堆新规则。
- 因此最佳开发顺序不是直接实现 Shot Prompt，而是先完成 Storyboard Canonical 化，再把这套 bundle/revision 机制抽成 Shot Prompt 复用底座。
