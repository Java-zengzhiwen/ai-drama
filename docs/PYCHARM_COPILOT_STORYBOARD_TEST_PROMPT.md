# 给 PyCharm Copilot 的 Storyboard Workflow MVP 测试 Prompt

你现在在 PyCharm 中对以下项目做**只读测试和验收**：

```text
/Users/zengzhiwen/AI-manju/ai-drama-skill-runtime
```

当前目标分支：

```text
feat/storyboard-workflow-mvp
```

当前预期最新提交：

```text
72a7a2a6c4f457bc0b353c571be6e6e68b1c662e
```

---

## 一、你的工作方式

请直接在 PyCharm Terminal 中执行测试，并把每一步的：

- 执行命令
- 退出码
- 关键输出
- 实际结果
- 是否通过
- 发现的问题

实时展示出来。

不要只告诉我“测试通过”，必须展示证据。

### 强制约束

本轮只测试，不修改实现。

禁止：

- 修改任何源码
- 修改 Skill
- 修改测试
- 修改数据库结构
- commit
- push
- merge
- reset
- checkout 其他分支
- 删除项目文件
- 安装新依赖
- 使用真实 API Key，除非我明确同意
- 把 API Key 打印到终端或报告中

所有运行数据放到：

```text
/tmp/ai-drama-storyboard-copilot-test
```

所有导出文件放到：

```text
/tmp/ai-drama-storyboard-copilot-export
```

可以删除并重建这两个 `/tmp` 测试目录，但不能删除项目目录中的任何内容。

---

## 二、何时必须停下来问我

遇到以下情况时，立即停止当前步骤并向我提问：

1. 当前分支不是 `feat/storyboard-workflow-mvp`
2. 当前 HEAD 不是预期提交，且无法确定原因
3. working tree 不干净
4. 缺少 Python 环境或项目依赖
5. `ai-drama` 命令不可用，且 `python3 -m ai_drama_runtime.cli` 也不可用
6. 需要安装依赖
7. 需要真实模型 API Key、Base URL 或 Model
8. 需要修改源码才能继续
9. 测试会影响正式数据
10. 发现数据库或项目文件可能被破坏

普通测试失败不需要立刻停止。请记录失败并继续执行其他相互独立的测试。

---

# 三、测试阶段

## Stage 0：环境确认

先执行：

```bash
cd /Users/zengzhiwen/AI-manju/ai-drama-skill-runtime

git branch --show-current
git rev-parse HEAD
git log -3 --oneline
git status --short
python3 --version
which ai-drama || true
```

预期：

```text
branch = feat/storyboard-workflow-mvp
HEAD = 72a7a2a6c4f457bc0b353c571be6e6e68b1c662e
git status --short 无输出
```

如果不符合，停下来问我。

然后设置测试变量：

```bash
export SKILLS_ROOT="skills"
export SCRIPT_SKILL="ai-drama-script-adaptation-skill@v0.6.1-rc2.4"
export STORYBOARD_SKILL="ai-drama-storyboard-design-skill@v0.1.0"
export ACCEPTANCE_ROOT="acceptance/shengsi-chapter-001"

export DATA_ROOT="/tmp/ai-drama-storyboard-copilot-test"
export EXPORT_ROOT="/tmp/ai-drama-storyboard-copilot-export"

rm -rf "$DATA_ROOT" "$EXPORT_ROOT"
mkdir -p "$DATA_ROOT" "$EXPORT_ROOT"
```

如果 `ai-drama` 不可用，后续统一使用：

```bash
python3 -m ai_drama_runtime.cli
```

请定义一个你自己的 CLI 前缀变量，避免后续命令不一致。

---

## Stage 1：基础自动化验证

依次执行：

```bash
python3 migration/tools/verify_migration.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_ADDOPTS='-p no:cacheprovider' \
python3 -m pytest -q
```

```bash
python3 -m py_compile \
  migration/tools/verify_migration.py \
  ai_drama_runtime/*.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/validators/*.py \
  skills/ai-drama-script-adaptation-skill/v0.6.1-rc2.4/runtime-validators/*.py \
  skills/ai-drama-storyboard-design-skill/v0.1.0/validators/*.py
```

记录：

- migration verify 结果
- pytest 数量
- 是否有 skip / xfail / fail
- py_compile 结果

当前声明的预期：

```text
migration status=valid
checked_files=81
pytest=61 passed
```

不要因为预期不同而伪造结果。

---

## Stage 2：Skill 可发现性与 Manifest

执行：

```bash
$CLI --skills-root "$SKILLS_ROOT" skills list
```

```bash
$CLI --skills-root "$SKILLS_ROOT" skills validate "$SCRIPT_SKILL"
```

```bash
$CLI --skills-root "$SKILLS_ROOT" skills validate "$STORYBOARD_SKILL"
```

检查：

- Script Skill 可发现
- Storyboard Skill 可发现
- Storyboard 版本为 `v0.1.0`
- execution profile 为 `storyboard-markdown-mvp-v1`
- input type 为 `approved_script_revision`
- output type 为 `storyboard_revision`
- 四个 required Storyboard Validator 已登记

---

## Stage 3：CLI 输入 Gate 测试

分别执行并记录退出码：

### 3.1 未提供输入

```bash
$CLI \
  --skills-root "$SKILLS_ROOT" \
  --data-root "$DATA_ROOT" \
  run create \
  --skill "$SCRIPT_SKILL" \
  --runtime mock
```

预期：退出码 2。

### 3.2 同时提供两个输入

```bash
$CLI \
  --skills-root "$SKILLS_ROOT" \
  --data-root "$DATA_ROOT" \
  run create \
  --skill "$SCRIPT_SKILL" \
  --input "$ACCEPTANCE_ROOT" \
  --source-revision fake \
  --runtime mock
```

预期：退出码 2。

### 3.3 Storyboard Skill 错用 `--input`

```bash
$CLI \
  --skills-root "$SKILLS_ROOT" \
  --data-root "$DATA_ROOT" \
  run create \
  --skill "$STORYBOARD_SKILL" \
  --input "$ACCEPTANCE_ROOT" \
  --runtime mock
```

预期：

```text
SKILL_INPUT_TYPE_MISMATCH
```

### 3.4 Script Skill 错用 `--source-revision`

```bash
$CLI \
  --skills-root "$SKILLS_ROOT" \
  --data-root "$DATA_ROOT" \
  run create \
  --skill "$SCRIPT_SKILL" \
  --source-revision fake \
  --runtime mock
```

预期：

```text
SKILL_INPUT_TYPE_MISMATCH
```

### 3.5 Storyboard 使用不存在的 Revision

```bash
$CLI \
  --skills-root "$SKILLS_ROOT" \
  --data-root "$DATA_ROOT" \
  run create \
  --skill "$STORYBOARD_SKILL" \
  --source-revision missing-revision \
  --runtime mock \
  --model mock-storyboard-v1
```

预期：

```text
SOURCE_REVISION_NOT_FOUND
```

---

## Stage 4：Mock Script → Storyboard 完整流程

### 4.1 生成 Script

执行 Script Mock Run，并把 JSON 保存到变量或临时文件。

必须提取：

```text
SCRIPT_RUN_ID
SCRIPT_REVISION_ID
SCRIPT_ARTIFACT_ID
```

检查：

```text
status=SUCCEEDED
artifact_id=shengsi-chapter-001
revision_id 非空
```

### 4.2 未审批时尝试 Storyboard

使用刚生成但尚未批准的 Script Revision 运行 Storyboard。

预期：

```text
SOURCE_REVISION_NOT_APPROVED
```

### 4.3 检查 Gate Failure 持久化

直接用只读 SQLite 查询：

```sql
SELECT
  gate_id,
  target_skill_id,
  source_revision_id,
  error_code,
  error_message,
  created_at
FROM workflow_gate_records
ORDER BY created_at;
```

预期至少存在：

```text
SOURCE_REVISION_NOT_FOUND
SOURCE_REVISION_NOT_APPROVED
```

### 4.4 批准 Script

调用：

```text
approvals approve
```

并检查：

```text
approval_status=approved
```

### 4.5 生成 Storyboard

使用当前批准的 Script Revision 运行 Storyboard Mock。

必须提取：

```text
STORYBOARD_RUN_ID
STORYBOARD_REVISION_ID
STORYBOARD_ARTIFACT_ID
```

检查：

```text
artifact_id=shengsi-chapter-001:storyboard
status=SUCCEEDED 或 VALIDATION_FAILED
```

不要预设一定成功，以实际结果为准。

---

## Stage 5：Validator 实际执行检查

从 CLI 结果和 SQLite 中检查 Storyboard Revision 的所有 Validation Record。

必须确认以下四个 required Validator 的真实状态：

```text
storyboard_structure
storyboard_duration
storyboard_source_coverage
storyboard_continuity
```

对每个 Validator 展示：

- status
- required
- exit_code
- error_code
- report 内容
- stdout
- stderr

检查它们是否真实执行，而不是错误地显示 `NOT_APPLICABLE`。

同时记录：

```text
genericity
```

是否实际执行，还是 `NOT_APPLICABLE`。

---

## Stage 6：真实 Source Coverage 缺陷检查

这是本轮最重要的手工验收。

分别读取数据库中的：

1. Source Script Revision 内容
2. Storyboard Revision 内容

从 Source Script 中提取所有：

```text
## 场次：...
```

从 Storyboard 中提取所有：

```text
source_scene_reference
```

输出：

```text
SOURCE_SCRIPT_SCENES
STORYBOARD_SOURCE_REFERENCES
MISSING_SOURCE_SCENES
EXTRA_SOURCE_REFERENCES
```

然后对比 Validator 的：

```text
storyboard_source_coverage
```

判断：

- 如果 Source Script 有 1-1～1-8；
- Storyboard 只覆盖 1-1～1-2；
- 但 Validator 仍为 PASS；

则记录为：

```text
BLOCKER: SOURCE_COVERAGE_FALSE_PASS
```

不得根据 Storyboard 自己的场次标题代替真实来源 Script 做判断。

---

## Stage 7：审批与导出

只有 Storyboard Revision 存在时继续。

### 7.1 审批 Storyboard

执行：

```text
approvals approve STORYBOARD_REVISION_ID
```

检查数据库 Approval Record 的 action 是否为：

```text
storyboard_approved
```

不能是：

```text
script_approved
```

### 7.2 导出 Storyboard

导出到：

```text
/tmp/ai-drama-storyboard-copilot-export/approved-storyboard.md
```

检查：

```text
approved-storyboard.md
approved-storyboard.md.provenance.json
```

Provenance 必须包含：

```text
source_script_artifact_id
source_script_revision_id
source_script_content_hash
source_script_approval_record_id
source_approval_record
freshness_status
```

---

## Stage 8：Staleness 测试

1. 再生成一个新的 Script Revision；
2. 批准新的 Script Revision；
3. 查询旧 Storyboard 的 freshness；
4. 尝试重新批准旧 Storyboard；
5. 尝试导出旧 Storyboard；
6. 使用旧 Script Revision 再生成 Storyboard；
7. 使用新 Script Revision 生成新 Storyboard。

预期：

```text
旧 Storyboard = STALE
旧 Storyboard 审批被阻止
旧 Storyboard 导出被阻止
旧 Script Revision 不能再启动 Storyboard
新 Script Revision 可以启动 Storyboard
```

然后对比旧、新两个 Storyboard Revision。

Compare 必须展示：

```text
source_revision_id
source_script_content_hash
source_script_approval_record_id
freshness_status
request_hash
validator_status
text_diff
```

---

## Stage 9：Required NOT_APPLICABLE 策略测试

这个测试使用单独的数据目录：

```text
/tmp/ai-drama-storyboard-copilot-na-test
```

流程：

1. 生成并批准 Script；
2. 生成 Storyboard；
3. 在测试数据库中，把一个 required Storyboard Validator 的状态临时改成：
   `NOT_APPLICABLE`
4. 尝试批准 Storyboard。

这是测试数据库中的故障注入，允许直接修改 `/tmp` 数据库，但不能修改源码。

正确行为：

```text
审批失败
退出码=6
```

如果审批成功，记录：

```text
BLOCKER: REQUIRED_NOT_APPLICABLE_CAN_BE_APPROVED
```

---

## Stage 10：Validator 边界故障注入

使用独立 `/tmp` 目录或复制出的 Storyboard 内容做以下检查，不修改源码。

至少验证：

1. `shot_order` 倒序是否会失败；
2. `source_scene_reference` 与 scene_id 不一致是否会失败；
3. 一个镜头缺少 duration、另一个镜头有两个 duration 是否会失败；
4. 一个镜头缺少 continuity 字段是否会失败；
5. 重复 shot_id 是否会失败。

每项都记录：

```text
EXPECTED
ACTUAL
PASS / FAIL
```

---

## Stage 11：真实模型测试

先检查环境变量是否存在，但不要打印具体值：

```text
AI_DRAMA_API_KEY
AI_DRAMA_BASE_URL
AI_DRAMA_MODEL
```

如果缺少任何必要配置，停下来问我：

```text
是否提供真实模型配置并继续 Real Model Smoke Test？
```

未经确认不要继续。

如果我同意，再执行：

```text
真实 Script Run
→ 人工确认是否批准 Script
→ 真实 Storyboard Run
→ 不自动批准 Storyboard
```

真实 Storyboard 输出需要人工检查：

- 是否覆盖全部 Script 场次
- 每镜是否 5–15 秒
- 是否保持剧情因果
- 是否没有新增核心剧情
- 是否包含明确站位、动作、情绪
- 是否包含 continuity_in / continuity_out
- 是否混入 LibTV、Agnes 或视频 Prompt
- Validator 与人工判断是否一致

---

# 四、最终输出格式

全部完成后，生成一份中文报告：

```text
STORYBOARD_WORKFLOW_MANUAL_TEST_REPORT
```

报告必须包含：

## 1. 环境

- Branch
- HEAD
- Python
- CLI 入口
- Working tree

## 2. 自动测试

- Migration Verification
- Pytest
- PyCompile
- GitHub CI 是否存在

## 3. 流程测试

- Script Run
- Script Approval
- Storyboard Gate
- Storyboard Run
- Validators
- Storyboard Approval
- Export
- Staleness
- Compare

## 4. 关键缺陷检查

- Source Coverage 是否真实比较来源 Script
- Required NOT_APPLICABLE 是否阻止审批
- Genericity 是否实际执行
- Shot Order 是否严格递增
- Duration 是否逐镜验证
- Scene Reference 是否分别校验
- Runtime Request 是否重复 Context / Schema / Contract

## 5. 发现的问题

按级别分类：

```text
BLOCKER
HIGH
MEDIUM
LOW
```

每个问题包含：

- 复现步骤
- 预期
- 实际
- 证据
- 是否阻止合并

## 6. 最终记录表

使用以下表格：

| 测试项 | 状态 | 证据 / 说明 |
|---|---|---|
| Migration Verify | PASS / FAIL | |
| Pytest | PASS / FAIL | |
| PyCompile | PASS / FAIL | |
| Skill 可发现 | PASS / FAIL | |
| CLI 输入互斥 | PASS / FAIL | |
| Skill 输入类型 Gate | PASS / FAIL | |
| Missing Revision Gate | PASS / FAIL | |
| Unapproved Script Gate | PASS / FAIL | |
| Gate Failure 持久化 | PASS / FAIL | |
| Storyboard Run | PASS / FAIL | |
| Required Validators 真实执行 | PASS / FAIL | |
| Source Coverage 真实校验 | PASS / FAIL | |
| Storyboard Approval Action | PASS / FAIL | |
| Export 与 Provenance | PASS / FAIL | |
| Staleness | PASS / FAIL | |
| Stale Approval Block | PASS / FAIL | |
| Stale Export Block | PASS / FAIL | |
| Compare | PASS / FAIL | |
| Required N/A Approval Policy | PASS / FAIL | |
| Validator 边界故障注入 | PASS / FAIL | |
| Real Model Smoke | PASS / FAIL / SKIPPED | |

最后输出：

```text
TECHNICAL_MVP_VERDICT=PASS 或 FAIL
QUALITY_ACCEPTANCE_STATUS=PENDING_USER_REVIEW 或 USER_APPROVED
MERGE_TO_MAIN=ALLOWED 或 BLOCKED
```

判定规则：

只有所有阻塞项通过，才允许：

```text
TECHNICAL_MVP_VERDICT=PASS
MERGE_TO_MAIN=ALLOWED
```

真实模型 Storyboard 未经我人工审阅，不得输出：

```text
QUALITY_ACCEPTANCE_STATUS=USER_APPROVED
```

现在从 Stage 0 开始执行。
