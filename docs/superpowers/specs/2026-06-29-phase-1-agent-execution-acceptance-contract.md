# Phase 1 Agent Execution & Acceptance Contract

## 1. Status

```text
Status: FROZEN FOR AGENT EXECUTION
Phase: Phase 1 — Storyboard Canonicalization
Implementation: ALLOWED
Execution Authorization: GRANTED
```

本文件冻结前，Codex 不得开始 Phase 1 实现。

---

## 2. Purpose

本契约用于约束一次完整的 Codex Agentic Run，使 Codex 能够在尽量少的人类往返下完成：

```text
Context Loading
→ Repository Analysis
→ Clarification Check
→ Implementation Plan
→ Test-First Execution
→ Self-Repair
→ Independent Agent Review
→ Deterministic Verification
→ Commit and Push
```

本契约的目标不是重新设计 Foundation，而是将已冻结的 Foundation Design 转换为可实施、可验证、可审计的 Phase 1 交付。

---

## 3. Authority Hierarchy

出现冲突时，优先级从高到低如下：

1. 本文件冻结后的明确条款；
2. `docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md`；
3. 仓库根目录及适用子目录中的 `AGENTS.md`；
4. 当前仓库真实代码与数据库结构；
5. 两份 Foundation Review 输入；
6. Codex 的默认工程判断。

规则：

- Codex 不得修改高优先级文档来迁就低优先级实现；
- 当前代码与冻结规范冲突时，应修改代码，除非触发本契约的 Stop Condition；
- 未被规范决定的普通内部实现细节，由 Codex 按最小改动原则决定；
- 不得重新审议已经冻结的 Foundation Decisions。

---

## 4. Frozen Baseline

### Repository

```text
Repository: Java-zengzhiwen/ai-drama
Branch: test/storyboard-complete-verification
Foundation Baseline Commit: 69f27e8168ade5e241e9c643746c62220e9e09de
Execution Start Commit: Provided by the Phase 1 launch prompt after the preparation documents have been committed and pushed
```

### Foundation Design

```text
docs/superpowers/specs/2026-06-28-storyboard-canonical-shot-prompt-foundation-design.md
```

### Existing Test Baseline

```text
python3 -m pytest -q
Expected baseline: 92 passed
```

Phase 1 开始前必须核对：

```bash
git rev-parse HEAD
git branch --show-current
git status --short
python3 -m pytest -q
```

冻结后的启动检查必须满足：

1. Current HEAD must exactly equal the Execution Start Commit supplied by the Phase 1 launch prompt.
2. Foundation Baseline Commit `69f27e8168ade5e241e9c643746c62220e9e09de` must be an ancestor of the Execution Start Commit.
3. The working tree must be clean.
4. Changes between Foundation Baseline Commit and Execution Start Commit must contain only authorized Phase 1 preparation documents.
5. Existing baseline tests must pass before implementation starts.

若上述任一条件不满足，必须停止并报告，不得自行继续。

---

## 5. Phase 1 Goal

Phase 1 的唯一业务目标是：

```text
将 Storyboard 从 Markdown-first Runtime
升级为 Canonical JSON-first Runtime
```

最终权威关系：

```text
Storyboard Canonical JSON
= authoritative revision content

Storyboard Markdown
= deterministic derived view
```

Phase 1 完成后，系统必须能够：

1. 创建 `storyboard-canonical-v1` Revision；
2. 将 Canonical JSON 作为 Revision 的权威内容对象；
3. 稳定计算 Canonical Hash；
4. 从 Canonical JSON 确定性渲染 Markdown；
5. 对 Canonical Storyboard 执行冻结的 Validators；
6. 显式迁移 Legacy Markdown Storyboard；
7. 保持 Legacy Revision 历史不可变；
8. 保持当前已支持流程的回归兼容。

---

## 6. Phase 1 In Scope

### 6.1 Canonical Model

- `storyboard-canonical-v1` 数据模型；
- Scene 与 Shot 的冻结字段；
- 最小元素 Schema；
- 字段类型与 nullable 规则；
- ID、顺序、时长、连续性和来源引用规则。

### 6.2 Canonical Serialization

- `canonical-json-v1`；
- UTF-8 without BOM；
- Unicode NFC；
- object keys 字典序排序；
- arrays 保持业务顺序；
- compact separators；
- `allow_nan = false`；
- canonical bytes 不含尾换行；
- 重复 JSON key 拒绝。

### 6.3 Hashing

- Storyboard Canonical Hash；
- 输入稳定时 Hash 可重复；
- Runtime metadata、approval state、absolute path 不进入 Canonical Hash。

### 6.4 Canonical Storyboard Revision

- 新 Canonical Storyboard Revision 创建；
- `content_profile = storyboard-canonical-v1`；
- Canonical JSON object 成为权威 `content_object_id`；
- 与已批准 Script Revision 建立 dependency；
- 不改写 Legacy Markdown Revision。

### 6.5 Deterministic Renderer

- Canonical JSON → Markdown；
- 相同 canonical bytes + renderer ID/version → byte-identical Markdown；
- 不调用模型；
- 不访问网络；
- 不读取当前时间；
- 不使用随机数；
- 不依赖 locale、terminal width、absolute path 或环境变量；
- text output 使用 LF；
- text output 只有一个尾换行。

### 6.6 Legacy Migration

显式迁移流程：

```text
Legacy Markdown Revision
→ Parser
→ Canonical Candidate
→ Schema Validation
→ Source Coverage Validation
→ Renderer Round-trip Review
→ Human Confirmation
→ New Canonical Revision
```

要求：

- 不原地修改 Legacy Revision；
- 不自动批准；
- 不自动成为 current approved；
- Fidelity 无法证明时 fail closed；
- 返回 `LEGACY_MIGRATION_REQUIRES_REVIEW`。

### 6.7 Validators

至少实现或接入：

- `storyboard_canonical_schema`
- `storyboard_shot_identity`
- `storyboard_shot_order`
- `storyboard_duration`
- `storyboard_source_coverage`
- `storyboard_continuity`
- `storyboard_renderer_parity`
- `storyboard_source_freshness`

`storyboard_bundle_integrity` 的正式持久化实现属于 Phase 2，但 Phase 1 可以建立接口、测试边界或临时校验，不得落地 Phase 2 的 Bundle Persistence。

### 6.8 CLI Integration

允许：

- 复用现有 `ai-drama run create`；
- 增加或接入 `ai-drama storyboard render`；
- 增加或接入 `ai-drama storyboard migrate-legacy`；
- 复用现有 inspect / compare 能力；
- 为测试增加必要的 CLI 输出。

最终命令名称必须在 Implementation Plan 中基于现有 CLI 结构确认，不得无理由创建平行命令体系。

---

## 7. Explicitly Out of Scope

Phase 1 禁止实现：

- `revision_outputs` 正式持久化；
- Bundle Manifest 正式持久化；
- Atomic bundle export；
- Shot Prompt Canonical；
- Shot-to-Unit 生成；
- Asset Binding；
- `bind-assets`；
- Asset Registry；
- Approval inheritance for asset-only revisions；
- Execution Planning Artifact；
- Target Adapter；
- LibTV Adapter；
- Agnes Adapter；
- Platform Payload；
- Execution Authorization；
- `execution_readiness = ready`；
- Web UI；
- Remote API；
- 无关业务重构。

若实现这些内容是继续 Phase 1 的必要条件，必须触发 Stop Condition。

---

## 8. Protected Decisions

Codex 不得修改或重新解释：

```text
Canonical JSON is the authority
Markdown is derived
Legacy revisions are immutable
Legacy and Canonical Storyboard revisions share one logical storyboard artifact
legacy_migration creates a new revision under the same logical artifact
Canonical serialization rules
Hash scope
Storyboard 5–15 second duration rule
Approval and freshness are separate
Execution readiness remains blocked
No automatic approval
No Phase 2 bundle persistence in Phase 1
No Shot Prompt implementation in Phase 1
```

不得修改 Foundation Design 状态或内容，除非用户另行授权。

---

## 9. Agent Operating Model

### 9.1 Main Agent

主 Agent 是唯一允许修改代码、测试和计划文档的 Agent。

主 Agent职责：

- 加载上下文；
- 汇总子 Agent分析；
- 创建 Implementation Plan；
- 先写失败测试；
- 实施代码；
- 运行修复循环；
- 汇总独立审查；
- 生成验证报告；
- commit 和 push。

### 9.2 Read-only Subagents

主 Agent必须显式启动以下只读子 Agent。

#### Agent A — Repository Mapper

输出：

- 当前 Storyboard 创建链路；
- Revision 存储链路；
- Parser、Renderer、Validator、CLI 位置；
- 当前数据库约束；
- 兼容性风险；
- 建议修改文件；
- 禁止修改文件。

不得写文件。

#### Agent B — Acceptance Designer

将本契约转为：

- Unit tests；
- Integration tests；
- CLI tests；
- Database assertions；
- Golden tests；
- Negative tests；
- Regression tests；
- Verification script checks。

不得写业务代码。

#### Agent C — Migration Reviewer

检查：

- Legacy Revision 不可变；
- Canonical Revision 创建新对象；
- Migration 不自动批准；
- Migration 不自动 current-approved；
- 同一逻辑 Artifact 关系；
- Fidelity fail-closed；
- Approval/current-approved 唯一性风险。

不得写文件。

#### Agent D — Scope Reviewer

检查是否越界进入：

- Phase 2 Bundle；
- Shot Prompt；
- Asset Binding；
- Execution Planning；
- LibTV；
- Agnes；
- 无关重构。

不得写文件。

#### Agent E — Final Contract Reviewer

在实现完成后执行，只读检查：

```text
Foundation clause
→ implementation location
→ test evidence
→ PASS / FAIL
```

不得修改代码。

#### Agent F — Adversarial Tester

在实现完成后尝试破坏：

- duplicate JSON keys；
- Unicode normalization；
- NaN / Infinity；
- object key order；
- array order；
- invalid duration；
- duplicate IDs；
- missing source scene；
- continuity mismatch；
- renderer nondeterminism；
- environment-dependent renderer output；
- Legacy Revision mutation；
- automatic approval；
- stale source；
- migration fidelity failure。

不得修改业务代码。可提出新增测试建议，由主 Agent实现。

---

## 10. Context Loading Requirements

主 Agent在修改代码前必须读取：

```text
AGENTS.md
Foundation Design
README.md
ai_drama_runtime/store.py
ai_drama_runtime/services.py
ai_drama_runtime/validators.py
ai_drama_runtime/request.py
ai_drama_runtime/parser.py
ai_drama_runtime/cli.py
tests/test_storyboard_workflow.py
tests/test_validators_approval_export.py
Storyboard Skill manifest and related package files
Relevant migrations/schema initialization code
```

主 Agent必须先输出一份 Context Summary：

```text
Current Runtime Behavior
Target Phase 1 Behavior
Protected Decisions
Expected Changed Files
Expected New Tests
Compatibility Risks
Potential Stop Conditions
```

Context Summary 阶段不得修改代码。

---

## 11. Stop and Ask Conditions

出现以下任一情况，Codex必须停止实施并向用户提问：

1. Foundation Design 内存在无法同时满足的冻结条款；
2. 当前数据库结构无法在不改变 Protected Decision 的前提下支持 Phase 1；
3. 必须提前实现 `revision_outputs` 才能继续；
4. 必须改变 Artifact Boundary；
5. 必须改变 Canonical Hash Scope；
6. 必须改变 current-approved 唯一性规则；
7. 必须自动批准 Migration 才能继续；
8. 必须修改 Foundation Design；
9. 必须引入新的生产依赖，但契约没有授权；
10. 现有业务行为与规范冲突，且规范未定义兼容策略；
11. 同一个阻断问题连续修复三次仍未通过；
12. 完整测试出现无法归类为实现错误的语义冲突；
13. 发现工作树包含未经授权的外部修改；
14. 发现基线 Commit、分支或测试数不匹配。

停止时只输出：

```text
# BLOCKED

- condition:
- evidence:
- why_contract_is_insufficient:
- options:
- recommended_option:
- affected_files:
- implementation_started:
- uncommitted_changes:
```

不得自行选择架构方案，不得提交半成品。

---

## 12. Non-Blocking Engineering Decisions

以下事项不需要询问用户，由 Codex按最小改动原则决定：

- 私有函数名称；
- 内部模块拆分；
- fixture 组织；
- 内部异常类组织；
- 不影响外部契约的局部重构；
- 测试辅助函数；
- 临时文件清理方式；
- 日志字段顺序；
- 内部类型注解；
- 不改变 CLI 合同的实现细节。

---

## 13. Planning Gate

实现前必须创建独立 Implementation Plan。

建议路径：

```text
docs/superpowers/plans/2026-06-29-phase-1-storyboard-canonicalization-implementation-plan.md
```

计划必须包含：

- Baseline；
- Scope / Non-scope；
- Current architecture map；
- Target architecture；
- 文件级变更计划；
- 数据流；
- Schema strategy；
- Serialization strategy；
- Hash strategy；
- Renderer interface；
- Migration path；
- Validator integration；
- CLI changes；
- Test-first task sequence；
- Rollback strategy；
- Risk register；
- Acceptance mapping；
- Commit sequence。

计划完成后，主 Agent必须自检：

```text
Does the plan modify Protected Decisions?
Does the plan include Phase 2+ scope?
Does every task have a test?
Does every acceptance criterion map to code and tests?
```

若无 blocker，可继续执行，不需要再次询问用户。

---

## 14. Test-First Execution Rule

Phase 1 必须采用：

```text
Failing Test
→ Minimal Implementation
→ Focused Test
→ Full Verification
```

禁止：

- 先实现所有代码再补测试；
- 删除失败测试；
- 降低断言强度；
- 把 FAIL 改成 SKIP；
- 修改 Golden Output 迎合错误实现；
- 将应失败的输入默认为容错成功；
- 通过放宽 Schema 绕过规范。

---

## 15. Required Verification Entry Point

必须创建统一验证入口，建议：

```bash
python3 tools/verify_phase1_storyboard_canonicalization.py
```

该脚本必须：

- 可重复运行；
- 不依赖网络；
- 不修改生产数据；
- 使用临时目录或测试数据库；
- 输出明确 PASS / FAIL；
- 失败时输出具体检查项；
- 返回非零退出码表示失败。

最终成功输出：

```text
PHASE1_STORYBOARD_CANONICALIZATION: PASS
```

失败输出：

```text
PHASE1_STORYBOARD_CANONICALIZATION: FAIL
- check:
- evidence:
- expected:
- actual:
```

---

## 16. Acceptance Matrix

### 16.1 Baseline and Scope

| ID | Check | Expected |
|---|---|---|
| P1-001 | Baseline relationship | Foundation Baseline Commit is an ancestor of Execution Start Commit, and current HEAD exactly matches the Execution Start Commit supplied by the launch prompt. |
| P1-002 | Branch | `test/storyboard-complete-verification` |
| P1-003 | Existing tests | baseline `92 passed` before implementation |
| P1-004 | Unauthorized files | none modified |
| P1-005 | Phase 2+ scope | not implemented |

### 16.2 Canonical JSON

| ID | Check | Expected |
|---|---|---|
| P1-010 | Valid Canonical Storyboard | accepted |
| P1-011 | Missing required field | rejected |
| P1-012 | Nullable rule violation | rejected |
| P1-013 | Duplicate JSON key | rejected |
| P1-014 | NaN / Infinity | rejected |
| P1-015 | Invalid UTF-8/BOM handling | rejected or normalized per contract |
| P1-016 | Unicode NFC equivalents | canonical bytes equal |
| P1-017 | Object key order variation | canonical bytes equal |
| P1-018 | Array order variation | canonical bytes differ when business order differs |

### 16.3 Identity and Order

| ID | Check | Expected |
|---|---|---|
| P1-020 | Valid scene_id | accepted |
| P1-021 | Invalid scene_id | `SHOT_ID_INVALID` or frozen schema error |
| P1-022 | Duplicate scene_id | rejected |
| P1-023 | Valid shot_id | accepted |
| P1-024 | Duplicate shot_id | rejected |
| P1-025 | Non-increasing scene_order | `SHOT_ORDER_INVALID` |
| P1-026 | Non-increasing shot_order | `SHOT_ORDER_INVALID` |
| P1-027 | Non-increasing action_order | rejected |

### 16.4 Duration

| ID | Check | Expected |
|---|---|---|
| P1-030 | Duration 5 | accepted |
| P1-031 | Duration 15 | accepted |
| P1-032 | Duration 4 | `STORYBOARD_DURATION_INVALID` |
| P1-033 | Duration 16 | `STORYBOARD_DURATION_INVALID` |
| P1-034 | Non-integer duration | rejected |

### 16.5 Source Coverage and Freshness

| ID | Check | Expected |
|---|---|---|
| P1-040 | Approved fresh Script source | accepted |
| P1-041 | Unapproved Script source | creation blocked |
| P1-042 | Missing source revision | `SOURCE_REVISION_NOT_FOUND` |
| P1-043 | Wrong source artifact type | `SOURCE_ARTIFACT_TYPE_INVALID` |
| P1-044 | Missing Script Scene coverage | `SHOT_COVERAGE_INCOMPLETE` |
| P1-045 | Invalid source_scene_reference | rejected |
| P1-046 | Stale source | `SOURCE_STALE` |
| P1-047 | Dependency cycle | `DEPENDENCY_CYCLE_DETECTED` |

### 16.6 Hashing

| ID | Check | Expected |
|---|---|---|
| P1-050 | Same canonical input repeated | same bytes and hash |
| P1-051 | Object key order differs | same hash |
| P1-052 | Unicode composed/decomposed | same hash after NFC |
| P1-053 | Business content differs | different hash |
| P1-054 | Approval metadata differs | canonical hash unchanged |
| P1-055 | Absolute path differs | canonical hash unchanged |

### 16.7 Renderer

| ID | Check | Expected |
|---|---|---|
| P1-060 | Same input + same renderer version | byte-identical Markdown |
| P1-061 | Repeated render | byte-identical |
| P1-062 | Different locale | byte-identical |
| P1-063 | Different terminal width | byte-identical |
| P1-064 | Different environment variables | byte-identical |
| P1-065 | Renderer output newline | exactly one trailing LF |
| P1-066 | Renderer parity | PASS |
| P1-067 | Renderer byte mismatch | `RENDERER_PARITY_FAILED` |

### 16.8 Canonical Revision

| ID | Check | Expected |
|---|---|---|
| P1-070 | Create Canonical Storyboard | new immutable Revision |
| P1-071 | content_profile | `storyboard-canonical-v1` |
| P1-072 | content_object_id | points to canonical JSON object |
| P1-073 | dependency | points to approved Script Revision |
| P1-074 | approval status | not auto-approved |
| P1-075 | freshness | FRESH when source is current-approved |
| P1-076 | rewrite existing Revision | forbidden |
| P1-077 | approval record in canonical JSON | absent |

### 16.9 Legacy Migration

| ID | Check | Expected |
|---|---|---|
| P1-080 | Valid Legacy migration candidate | new Canonical Revision candidate |
| P1-081 | Legacy Revision bytes before/after | unchanged |
| P1-082 | Same logical Artifact | preserved |
| P1-083 | Migration auto-approval | forbidden |
| P1-084 | Migration auto-current-approved | forbidden |
| P1-085 | Fidelity cannot be proven | `LEGACY_MIGRATION_REQUIRES_REVIEW` |
| P1-086 | Renderer round-trip mismatch | migration blocked |
| P1-087 | Human confirmation absent | final creation/promotion blocked |

### 16.10 CLI

| ID | Check | Expected |
|---|---|---|
| P1-090 | Canonical create command | creates Canonical Revision |
| P1-091 | Render command | emits deterministic Markdown |
| P1-092 | Legacy migration command | creates reviewable candidate/new Revision path |
| P1-093 | Invalid CLI input | non-zero exit |
| P1-094 | Domain error | symbolic error preserved |
| P1-095 | Existing CLI behavior | no regression |

### 16.11 Regression

| ID | Check | Expected |
|---|---|---|
| P1-100 | Existing 92 tests | all pass |
| P1-101 | New Phase 1 tests | all pass |
| P1-102 | Full pytest | all pass |
| P1-103 | git diff --check | pass |
| P1-104 | verification script | PASS |
| P1-105 | working tree after commit | clean |

---

## 17. Required Negative Tests

至少覆盖：

```text
duplicate JSON key
unknown field where additionalProperties=false
null for non-null array
empty string for required non-empty text
invalid scene_id
invalid shot_id
duplicate ID
invalid order
duration 4
duration 16
float duration
missing source
unapproved source
stale source
missing scene coverage
continuity mismatch
NaN
Infinity
renderer nondeterminism
renderer environment dependency
legacy mutation
migration auto-approval
migration without human confirmation
```

---

## 18. Required Golden Fixtures

至少提供：

```text
tests/fixtures/storyboard_canonical/valid_minimal.json
tests/fixtures/storyboard_canonical/valid_full.json
tests/fixtures/storyboard_canonical/invalid_duplicate_key.json
tests/fixtures/storyboard_canonical/invalid_duration.json
tests/fixtures/storyboard_canonical/invalid_order.json
tests/fixtures/storyboard_canonical/expected_rendered_minimal.md
tests/fixtures/storyboard_canonical/expected_rendered_full.md
```

文件名可按仓库惯例调整，但语义覆盖不得减少。

Golden Markdown 只能由冻结 Renderer Contract 决定，不得在实现错误时随意更新。

---

## 19. Self-Repair Loop

主 Agent必须循环：

```text
1. Run focused failing test
2. Fix minimal implementation
3. Re-run focused test
4. Run related test group
5. Run verification script
6. Run full pytest
7. Run Final Contract Reviewer
8. Run Adversarial Tester
9. Fix blockers and majors
10. Re-run all verification
```

退出循环的唯一条件：

```text
All required tests PASS
Verification script PASS
No blocker or major review finding
No scope violation
```

若同一 blocker 修复三次仍失败，触发 Stop Condition。

---

## 20. Review Severity

### Blocker

- 违反 Protected Decision；
- 数据不可逆损坏；
- Legacy Revision 被改写；
- 自动批准；
- Hash 不确定；
- Renderer 不确定；
- Phase 2+ 越界；
- 验收脚本错误地报告 PASS；
- Existing tests 回退。

### Major

- 缺少必要负向测试；
- CLI 行为与契约不一致；
- 错误码不稳定；
- Source coverage 或 freshness 漏检；
- Migration fail-open；
- 关键 Acceptance ID 没有证据。

### Minor

- 内部命名；
- 注释不足；
- 非关键代码组织；
- 不影响契约的文档措辞。

完成前必须：

```text
Blocker = 0
Major = 0
```

Minor 可记录在最终报告中。

---

## 21. Git and Change Control

### Allowed Changes

- Phase 1 Implementation Plan；
- Phase 1 业务实现；
- Phase 1 tests；
- Phase 1 fixtures；
- Phase 1 verification script；
- 必要的 README / CLI help 更新；
- 必要的 migration/schema compatibility code。

### Forbidden Changes

- Foundation Design；
- Review inputs；
- Shot Prompt Skill 业务逻辑；
- LibTV / Agnes；
- 无关 Skill；
- Phase 2+ implementation；
- 无关重构。

### Commit Strategy

建议分为：

```text
1. plan: phase 1 storyboard canonicalization
2. test: add phase 1 acceptance coverage
3. feat: implement storyboard canonicalization
4. docs: add phase 1 verification report
```

具体可按仓库惯例合并，但必须保持审计清晰。

禁止：

- force push；
- 重写已推送历史；
- 删除测试来获得 PASS；
- 将外部无关修改混入提交。

---

## 22. Required Final Deliverables

Phase 1 完成后必须交付：

1. Implementation Plan；
2. Canonical Schema implementation；
3. Canonical Serializer；
4. Canonical Hash implementation；
5. Canonical Storyboard Revision creation；
6. Deterministic Renderer；
7. Legacy Migration path；
8. Validators；
9. CLI integration；
10. Unit tests；
11. Integration tests；
12. Negative tests；
13. Golden fixtures；
14. Unified verification script；
15. Phase 1 Verification Report；
16. Canonical JSON sample；
17. Rendered Markdown sample；
18. Git commit SHA；
19. Changed-file list；
20. Known limitations。

---

## 23. Required Verification Report

建议路径：

```text
docs/superpowers/reports/2026-06-29-phase-1-storyboard-canonicalization-verification.md
```

报告必须包含：

```text
Baseline
Final Commit
Changed Files
Test Count
Existing Test Result
New Test Result
Acceptance Matrix P1-001 ... P1-105
Verification Script Output
Canonical Hash Evidence
Renderer Determinism Evidence
Legacy Immutability Evidence
Migration Evidence
CLI Evidence
Scope Review
Independent Review Findings
Known Limitations
Final Gate
```

每个 Acceptance ID 必须为：

```text
PASS
FAIL
NOT_APPLICABLE
```

本阶段冻结项不得使用 `NOT_APPLICABLE` 绕过。

---

## 24. Final Gate

只有全部满足时才允许声明 Phase 1 完成：

```text
Foundation Design unchanged
Protected Decisions unchanged
All baseline tests pass
All new Phase 1 tests pass
Verification script PASS
All required Acceptance IDs PASS
No Blocker
No Major
Legacy Revision immutable
Canonical Hash deterministic
Renderer deterministic
Migration fail-closed
No auto-approval
No Phase 2+ scope
Working tree clean
Commit pushed
```

最终状态：

```text
Phase 1 Status: COMPLETE
Phase 1 Acceptance: PASS
Phase 2 Authorization: NOT GRANTED
```

Phase 1 完成不得自动进入 Phase 2。

---

## 25. Final Codex Output Format

Codex完成后只输出：

```text
# Final Status

- phase:
- status:
- acceptance:
- baseline_commit:
- final_commit:
- branch:
- pushed:
- working_tree_clean:
- existing_tests:
- new_tests:
- total_tests:
- verification_script:
- protected_decisions_changed:
- foundation_design_changed:
- phase_2_scope_implemented:

# Deliverables

- implementation_plan:
- canonical_schema:
- serializer:
- hashing:
- canonical_revision:
- renderer:
- legacy_migration:
- validators:
- cli:
- fixtures:
- verification_report:

# Acceptance Summary

- passed:
- failed:
- not_applicable:
- blocker_count:
- major_count:
- minor_count:

# Key Evidence

- canonical_hash_repeatability:
- unicode_nfc:
- duplicate_key_rejection:
- renderer_determinism:
- legacy_revision_immutability:
- migration_requires_review:
- no_auto_approval:
- regression_suite:

# Changed Files

逐项列出。

# Known Limitations

只列 Phase 1 已知限制。

# Next Gate

- phase_2_allowed:
- remaining_blockers:
```

---

## 26. User Freeze Record

用户冻结本契约时，应记录：

```text
Frozen By: USER
Frozen Date: 2026-06-29
Frozen Foundation Baseline Commit: 69f27e8168ade5e241e9c643746c62220e9e09de
Execution Start Commit: Provided by the Phase 1 launch prompt
Frozen Baseline Commit: 69f27e8168ade5e241e9c643746c62220e9e09de
Execution Authorization: GRANTED
```

冻结后，除非触发 Stop Condition 或用户显式修改，本契约不得由 Codex自行更改。
