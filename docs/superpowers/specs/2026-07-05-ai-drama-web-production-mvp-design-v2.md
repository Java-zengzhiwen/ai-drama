# AI 漫剧 Web 生产平台 MVP Design Plan v2

**日期：** 2026-07-05  
**状态：** DRAFT_FOR_USER_REVIEW  
**建议入库路径：** `docs/superpowers/specs/2026-07-05-ai-drama-web-production-mvp-design-v2.md`  
**当前基础分支：** `main`  
**首要生成后端：** Agnes  
**后续生成后端：** LibTV  
**部署形态：** 本地、单用户、Web 优先

---

## 1. 设计结论

本 MVP 是一个本地单用户 AI 漫剧生产工作台。

用户应当能够在同一套 Web 工作区中完成：

```text
小说章节
→ 剧本
→ 分镜
→ 人物/场景/道具资料
→ 视觉资产
→ Shot Prompt
→ Agnes 图片/视频生成
→ 视频结果预览
→ 失败诊断与重跑
```

MVP 的终点是：

```text
一章小说对应的一组可预览、可追溯、可重跑的视频片段
```

MVP 不负责：

```text
配音
字幕
BGM
剪辑
镜头拼接
最终成片
LibTV 首版执行
多人协作
企业级审批与审计
通用 Agent 平台
```

---

## 2. 产品目标

### 2.1 主要目标

降低以下工作的人工成本：

- 小说改编为可拍摄剧本；
- 剧本拆成可执行分镜；
- 分析当前章节所需视觉资产；
- 生成和维护人物、场景、道具参考图；
- 自动生成逐镜视频提示词；
- 通过 Agnes 生成图像和视频；
- 保存生成过程、结果版本和失败原因；
- 支持用户调整 Prompt、资产或参数后重跑。

### 2.2 MVP 成功标准

真实小说章节可以完整跑通，并且每个镜头最终处于以下状态之一：

```text
video_ready
failed_with_reason
queued_for_rerun
```

系统必须能够从视频结果追溯到：

```text
小说章节
剧本版本
分镜版本
Shot Prompt 版本
输入资产
Agnes 请求参数
生成任务
视频结果
```

---

## 3. 当前仓库基线

当前 `main` 已经提供：

- Script Runtime；
- Script Adaptation Skill；
- 剧本 Revision、Validator、Approval；
- Storyboard Workflow；
- Storyboard Design Skill；
- Canonical Storyboard；
- Minimal Bundle Foundation；
- SQLite + 本地对象存储；
- Artifact / Revision / Approval 基础；
- Phase 3A Shot Prompt Store / Migration 基础。

### 3.1 保留并复用

```text
RuntimeStore
Artifact
Revision
ValidatorResult
ApprovalRecord
Object Storage
Script Workflow
Storyboard Workflow
Canonical Storyboard
Phase 3A Store 基础
```

### 3.2 包装为 Web 能力

```text
Runtime Services
Script 执行
Storyboard 执行
Revision 查询与编辑
Validator 执行
确认/拒绝操作
```

### 3.3 冻结

以下代码允许继续作为内部验证和回归工具，但不再扩大产品职责：

```text
migration/tools/*
tools/verify_*.py
现有 Bundle 验证工具
Phase 1 / Phase 2 / Phase 3A 历史验收工具
```

### 3.4 停止原计划

不再按原 Phase 3B–3E 继续开发：

```text
复杂 Review Event Lifecycle
Qualification Report
Approval Evidence Matrix
Portable Verifier
Final Verifier
多层 Verification Report
复杂 Revoke / Supersede 治理
```

---

## 4. MVP 范围

## 4.1 必须包含

### A. 项目与章节

- 创建项目；
- 编辑项目基础信息；
- 添加章节；
- 粘贴或导入小说原文；
- 保存章节顺序；
- 保存项目级制作规则；
- 展示各章节当前流程状态。

项目级制作规则包括：

```text
题材与时代
画面风格
画幅
镜头风格
光线与色彩
全局人物一致性规则
全局场景连续性规则
默认模型参数
```

### B. 剧本工作台

- 从章节原文生成剧本；
- 查看和编辑剧本；
- 保存不可变 Revision；
- 运行已有剧本 Validator；
- 展示 QC 结果；
- 确认或拒绝当前 Revision。

Gate：

```text
未确认剧本，不允许生成分镜。
```

MVP 用户态：

```text
pending
approved
rejected
```

### C. 分镜工作台

- 从已确认剧本生成分镜；
- 使用 Canonical Storyboard；
- 以镜头卡片或表格编辑；
- 编辑镜头顺序、时长、景别、运镜、人物、场景、动作、情绪、台词和连续性；
- 运行基础分镜验证；
- 确认或拒绝当前 Revision。

Gate：

```text
未确认分镜，不允许正式生成 Shot Prompt 或视频。
```

### D. 最小生产资料

支持当前项目/章节需要的：

```text
CharacterProfile
SceneProfile
PropProfile
StyleProfile
```

这些是生产资料，不是完整 Series Bible。

### E. 资产工作台

支持：

- 上传本地图片；
- 图片预览；
- 资产分类；
- 资产与人物、场景、道具、镜头绑定；
- 通过 Agnes 生成缺失资产；
- 保存生成参数和输入引用；
- 标记可用、拒绝或失败；
- 保留历史版本。

MVP 资产类型：

```text
character_reference
character_outfit
scene_reference
scene_angle
prop_reference
shot_keyframe
```

资产状态：

```text
draft
generating
usable
rejected
failed
```

### F. 资产需求分析

根据已确认分镜生成章节资产需求。

每个镜头识别：

- 角色；
- 服装版本；
- 场景；
- 场景机位；
- 道具；
- Shot Keyframe；
- 缺失资产；
- Prompt 是否可生成；
- 视频是否可生成。

### G. Shot Prompt Studio

每个 Canonical Storyboard Shot 对应一个可编辑 Prompt 单元。

必需字段：

```text
shot_id
shot_order
duration_seconds
scene_id
character_ids
prop_ids
asset_refs
camera
action
emotion
dialogue
positive_prompt
negative_prompt
continuity_notes
agnes_video_params
```

必须处理人物身份、人脸一致性、服装连续性、场景布局、人物站位、屏幕方向、动作连续性、台词与口型文本、镜头运动、前后衔接以及禁止变化。

Prompt 功能：

- 全章生成；
- 单镜重新生成；
- 人工编辑；
- 保存版本；
- 查看 Agnes 最终请求输入；
- 标记 ready 或 needs_revision。

### H. Agnes 图片生成

支持文生图、图生图、多参考输入、请求预览、提交、结果持久化、错误记录和重试。

图片输入优先策略：

```text
Data URI / Base64
```

### I. Agnes 视频生成

支持：

- 选择 ready 镜头；
- 创建异步视频任务；
- 保存 `video_id` 等 Provider 标识；
- 轮询任务；
- 应用重启后恢复轮询；
- 保存请求和响应；
- 获取并保存视频结果；
- 将结果绑定回 `shot_id`；
- 重跑生成新版本而不覆盖旧版本。

模式优先级：

```text
1. 图生视频
2. 多图 / 首尾帧 / 关键帧视频
3. 文生视频作为兼容模式
```

### J. 结果与重跑

每个镜头展示当前结果、旧版本、生成状态、输入资产、最终 Prompt、模型参数、视频预览、失败原因和重跑入口。

失败分类：

```text
face_drift
identity_mismatch
costume_error
scene_layout_error
character_position_error
action_error
camera_error
lip_sync_error
duration_error
visual_quality_error
storyboard_mismatch
provider_error
other
```

### K. 完整 Web 工作区

主要页面：

```text
/projects
/projects/:projectId
/projects/:projectId/chapters/:chapterId
/settings/agnes
```

章节页面为统一工作区，包含：

```text
原文
剧本
分镜
资料与资产
Shot Prompt
Agnes 生成
结果与重跑
```

---

## 4.2 明确延后

### LibTV

首版不实现 LibTV CLI 调用、项目绑定、画布节点编排、任务轮询和结果回填。

### 后期制作

不实现：

```text
配音
字幕
BGM
音效
剪辑时间线
镜头拼接
成片导出
剪映工程
Topaz 增强
自动发布
```

### 平台化功能

不实现：

```text
多人协作
登录与权限
评论与通知
多租户
计费
Skill 市场
通用 Workflow Engine
通用 Agent Runtime
多 Provider 动态插件体系
PostgreSQL
Redis
分布式队列
微服务
Kubernetes
```

---

## 5. 技术架构

推荐：

```text
前端：React + TypeScript
后端：FastAPI
运行时：现有 Python Runtime
数据库：SQLite
对象存储：本地文件系统
异步任务：SQLite 持久化 + 单进程后台 Poller
生成后端：AgnesBackend
```

系统结构：

```text
Browser
  ↓
React Web App
  ↓
FastAPI Application API
  ├── ProjectChapterService
  ├── ScriptWorkflowService
  ├── StoryboardWorkflowService
  ├── ProductionProfileService
  ├── AssetService
  ├── AssetRequirementService
  ├── ShotPromptService
  ├── GenerationJobService
  └── ResultService
      ├── Existing Runtime Core
      ├── Skill Runner
      ├── AgnesBackend
      ├── AssetDeliveryProvider
      ├── Persistent Poller
      ├── SQLite
      └── Local Object Storage
```

---

## 6. Skill 与 Service 边界

### Script Skill

负责小说章节到剧本内容；Service 负责输入、执行、Revision、Validator 和确认。

### Storyboard Skill

负责已确认剧本到 Canonical Storyboard；Service 负责 Gate、输入快照、Revision、Validator 和确认。

### Shot Prompt Skill

负责分镜、资料、资产和风格到正向 Prompt、负向 Prompt、连续性规则和模型输入建议。

ShotPromptService 负责：

```text
读取已确认分镜
分析资产是否齐全
调用 Skill
保存 ShotPromptSet Revision
结构验证
资产绑定
生成 Agnes 参数
管理 ready 状态
```

---

## 7. Agnes 集成

Agnes Help Skill 用于 API 文档参考、接入指导和错误排查，不是生产 Adapter。

平台需实现：

```text
Agnes API Client
请求参数映射
Secret 管理
图片生成
视频任务创建
video_id 持久化
任务轮询
RPM 限流
任务恢复
结果获取
错误归一化
重跑
```

薄 Backend 接口：

```python
class GenerationBackend:
    def create_image_job(self, request): ...
    def create_video_job(self, request): ...
    def get_job_status(self, provider_job_id): ...
    def fetch_result(self, provider_job_id): ...
    def rerun_job(self, source_job_id, overrides): ...
```

首版只实现 `AgnesBackend`。

视频参考图使用可公开访问的临时 HTTPS URL；本地 `localhost` URL 不可直接提供给远端 Agnes。

---

## 8. 数据对象

复用：

```text
Artifact
Revision
ValidatorResult
ApprovalRecord
RevisionOutput
InputSnapshot
```

新增：

```text
Project
Chapter
CharacterProfile
SceneProfile
PropProfile
StyleProfile
AssetRecord
AssetBinding
AssetRequirementSet
ShotPromptSet
GenerationJob
GenerationResult
ShotResultSelection
RerunRecord
```

GenerationJob 内部状态：

```text
draft
queued
submitting
submitted
polling
completed
failed
cancelled
```

UI 简化展示为：

```text
等待中
生成中
成功
失败
```

一个镜头允许多个结果，旧结果不可覆盖，最多一个结果标记为当前采用版本。

---

## 9. 后台任务机制

MVP 不使用 Redis。

单进程后台 Poller：

- 扫描 `queued/submitted/polling`；
- 提交 queued 任务；
- 查询 submitted/polling；
- 更新 `next_poll_at`；
- 保存完成结果；
- 保存标准化错误；
- 遵守 Agnes RPM 限制。

应用重启后恢复 queued、submitted 和 polling 状态；`submitting` 状态进入恢复检查，避免盲目重复提交。

幂等依赖客户端幂等键、请求哈希、Prompt Revision 和镜头标识。

---

## 10. Workflow Gate

```text
章节原文存在
→ 允许生成剧本

剧本 approved
→ 允许生成分镜

分镜 approved
→ 允许资产分析与 Prompt 生成

必要资产 usable
→ Prompt 可标记 ready

Prompt ready
→ 允许视频生成
```

章节状态由记录推导，不单独维护可任意编辑的状态字段。

---

## 11. 错误处理

用户可修正错误：

```text
missing_source
script_not_approved
storyboard_not_approved
missing_asset
asset_not_usable
prompt_not_ready
invalid_duration
unsupported_mode
```

Provider 错误统一为：

```text
authentication
rate_limited
invalid_request
input_unreachable
provider_busy
generation_failed
timeout
result_expired
unknown_provider_error
```

Agnes API Key 仅由后端读取，日志和导出内容必须脱敏。

---

## 12. 测试策略

保留四层：

```text
1. 现有 Runtime 回归测试
2. Fake Agnes 集成测试
3. 一条 Web 主流程测试
4. 真实 Agnes Smoke Test + 真实章节验收
```

真实章节建议包含：

```text
12–20 个镜头
至少 2 个角色
至少 2 个场景
至少 1 个关键道具
```

平台验收要求：

- 100% 镜头有 Canonical Storyboard；
- 100% 镜头有资产分析结果；
- 100% 镜头有 Shot Prompt 或明确阻塞原因；
- 100% 已提交任务最终进入 completed、failed 或 queued_for_rerun；
- 至少成功完成一次失败重跑；
- 至少成功验证一次重启恢复；
- 视频可采用率单独记录，不作为平台代码唯一通过线。

---

## 13. 开发里程碑

### Milestone 1：Web 剧本与分镜工作台

用户可以创建项目、添加章节、导入小说、生成/编辑/确认剧本和分镜。

不包含资产、Prompt、Agnes 和视频。

### Milestone 2：资料、资产与 Shot Prompt

用户可以建立人物/场景/道具资料、查看资产缺失、上传或生成参考图、生成和编辑逐镜 Prompt。

不包含视频生成、视频结果和重跑。

### Milestone 3：Agnes 视频生成与任务管理

用户可以选择 ready 镜头、提交视频任务、查看生成进度、预览视频、查看失败原因并重跑。

不包含 LibTV、配音、剪辑和成片。

### Milestone 4：真实章节验收与稳定化

使用 12–20 镜头真实章节完成端到端运行、重启恢复、失败重跑和阻断问题修复。

不新增任何产品模块。

---

## 14. Scope Control

任何新增功能都必须回答：

> 它是否直接帮助单用户从 Web 页面把一章小说转成可追溯的 Agnes 视频片段？

否则延期。

只允许为未来保留：

```text
薄 GenerationBackend 接口
清晰 Service 边界
稳定的数据追溯字段
```

---

## 15. MVP 完成条件

1. Web 页面完成主要流程；
2. 真实章节可生成和确认剧本；
3. 已确认剧本可生成和确认 Canonical Storyboard；
4. 可以维护最小人物、场景、道具和风格资料；
5. 可以分析资产缺失；
6. 可以上传或通过 Agnes 生成资产；
7. 每个镜头可以生成和编辑 Shot Prompt；
8. ready 镜头可提交 Agnes 视频任务；
9. 异步任务可持久化并在重启后恢复；
10. 视频结果可预览并绑定镜头；
11. 失败镜头有明确原因并可重跑；
12. 旧结果不会被重跑覆盖；
13. 现有 Runtime 回归测试通过；
14. 不依赖 LibTV、配音、剪辑、多人或复杂治理。

最终状态：

```text
AI_DRAMA_WEB_PRODUCTION_MVP_COMPLETE
AGNES_BACKEND_OPERATIONAL
LIBTV_DEFERRED
POST_PRODUCTION_DEFERRED
```

---

## 16. 后续但不属于 MVP

```text
LibTVBackend
配音
字幕
BGM
视频剪辑
成片合成
Topaz
项目导出
多章节批量运行
系列资产库
云端部署
多人协作
```
