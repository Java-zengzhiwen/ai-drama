# Agnes 图片与视频业务链路修订设计

日期：2026-07-25  
状态：交互设计已确认，等待书面设计复核  
实施状态：未开始

## 1. 目标

修订现有 Agnes 内置供应商，使当前项目业务能够可靠使用：

- `agnes-image-2.1-flash` 生成并持久化分镜关键帧图片；
- `agnes-video-v2.0` 按 Shot 提交视频、使用 `video_id` 轮询并持久化最终 MP4。

本次不接入 Agnes 文本模型，不新增 Agnes 供应商，不重写已经完成的 M6
Supplier、Model、ExecutionSnapshot、Job、Poller 或管理 UI 架构。

## 2. 契约来源与优先级

接口契约按以下优先级冻结：

1. Agnes 官方 Agnes Image 2.1 Flash 文档；
2. Agnes 官方 Agnes Video V2.0 文档；
3. 当前仓库已批准的 M6 供应商与模型管理设计；
4. 当前仓库已批准的 Agnes 视频输入契约；
5. 社区 Agnes-help-skill，只作为接入提示和故障排查的二级参考。

Agnes-help-skill 对以下内容有辅助价值：

- Base URL、Bearer 鉴权和常见错误排查；
- 图生图的 `extra_body.image` 位置；
- 视频必须优先使用 `video_id` 查询；
- 图片和视频的常见参数约束。

社区 Skill 不覆盖本次模型的全部最新官方契约，且可能晚于官方接口变更，因此不得覆盖
官方字段、响应路径或状态定义。

## 3. 冻结产品决策

- 继续使用现有 `Agnes` 供应商。
- 保持图片与视频的稳定 `supplier_model_id` 不变。
- 继续使用现有 Agnes credential，不复制或迁移密钥。
- 保存新版内置适配代码时创建新的不可变 Supplier Version。
- 图片尺寸与比例约束发生变化时，在同一稳定 `supplier_model_id` 下创建新的不可变
  Model Revision；历史 snapshot 继续引用旧 revision。
- 历史 Job 继续按创建时 ExecutionSnapshot 使用原 Supplier Version。
- 新 Job 使用保存后成为 current 的新版 Supplier Version。
- Agnes Image 保留模型行单次真实测试。
- Agnes Video 不新增模型行测试；通过项目 Shot 的正式生成流程验证。
- 不接入 Agnes 2.5 Pro Alpha 或其他文本模型。
- 不重新设计供应商页面、项目页面或生成结果页面。
- 内置安装器不得覆盖用户已经保存的自定义 Agnes Supplier Version；遇到自定义 current
  version 时保留原状，并要求用户明确执行内置恢复或适配代码更新。

## 4. 目标架构

### 4.1 图片链路

```text
项目 storyboard_keyframe_image 绑定
→ 解析 Agnes Image 模型、配置和当前 credential
→ 持久化 Generation Job 与 ExecutionSnapshot
→ imageRequest
→ 解析 data[0].url
→ Worker 下载并校验图片
→ 写入本地 Object Store
→ 创建关联 Job/Result 的 generated asset
```

图片请求进入网络前必须已经持久化 Job、请求对象和不可变快照。失败调用必须保留脱敏审计
记录，不得因为同步失败而丢失请求历史。

### 4.2 视频链路

```text
项目 shot_video_generation 绑定
→ 解析 Agnes Video 模型、配置和当前 credential
→ 持久化 Generation Job 与 ExecutionSnapshot
→ videoSubmit exactly once
→ 持久化 provider video_id
→ 后台按 video_id 执行 videoPoll
→ completed 后执行 videoFetch
→ 从 metadata.url 或兼容路径取得结果 URL
→ Worker 下载并校验 MP4
→ 写入本地 Object Store 与 Generation Result
```

Poller 必须按每个 Job 的 snapshot 路由，不得读取当前项目绑定、当前 Supplier Version、
当前模型 revision 或当前 config revision 来猜测历史任务。

## 5. Agnes Image 2.1 请求契约

### 5.1 文生图

推荐请求形态：

```json
{
  "model": "agnes-image-2.1-flash",
  "prompt": "...",
  "size": "1K",
  "ratio": "16:9",
  "extra_body": {
    "response_format": "url"
  }
}
```

规则：

- `model` 必须来自冻结的 model revision；
- `prompt` 必填；
- 新请求支持 `size` 等级 `1K`、`2K`、`3K`、`4K`；
- `ratio` 支持 `1:1`、`3:4`、`4:3`、`16:9`、`9:16`、`2:3`、`3:2`、`21:9`；
- 为保持历史请求可读和可重放，继续接受当前系统已有的受支持精确尺寸；
- `extra_body.response_format` 固定为 `url`；
- 不在顶层发送 `response_format`；
- 不猜测或发送官方文档未确认的质量参数。

### 5.2 图生图

- 参考图必须通过 `extra_body.image` 传递；
- 参考图可来自当前业务声明的公网 HTTPS URL 或 Data URI；
- 不发送 `tags: ["img2img"]`；
- 普通模式和参考图模式使用同一个 `/v1/images/generations` endpoint；
- 适配代码不得自行访问文件系统或宿主环境，所有输入读取和网络请求必须通过 Worker
  helper。

### 5.3 图片响应

- URL 输出读取 `data[0].url`；
- `data[0].url` 缺失时返回稳定错误 `PROVIDER_RESPONSE_MALFORMED`；
- Worker 只允许下载供应商响应声明的结果 URL；
- 下载后校验媒体类型与图片内容，再交由 Python 写入 Object Store；
- 供应商临时 URL 不作为产品结果的唯一存储。

## 6. Agnes Video V2.0 请求契约

### 6.1 输入语义

继续沿用已批准的严格输入规则：

- 普通模式允许零或一张 `shot_keyframe`；
- 普通模式有一张关键帧时使用顶层 `image`；
- 普通模式不得把人物、场景、服装或道具参考图误当作视频帧；
- `keyframes` 模式严格接受两至三张有序 `shot_keyframe`；
- `keyframes` 模式使用 `extra_body.image` 与
  `extra_body.mode: "keyframes"`；
- 不从普通资产引用中推断关键帧顺序。

### 6.2 参数白名单

只允许发送当前业务和官方文档共同确认的字段：

- `model`
- `prompt`
- `negative_prompt`
- `image`
- `mode`
- `num_frames`
- `frame_rate`
- `seed`
- `extra_body.image`
- `extra_body.mode`

`num_frames` 必须不超过 `441` 且满足 `8n + 1`，`frame_rate` 必须在 `1-60`
范围。当前业务继续只提供已经冻结的时长映射，不因官方文档支持更多时长而自动扩大 UI
或业务范围。

### 6.3 提交与轮询

- 创建 endpoint 为 `POST /v1/videos`；
- `videoSubmit` 只能执行一次；
- 成功响应必须包含可持久化的 `video_id`；
- 后续状态查询使用 `GET /agnesapi?video_id=<VIDEO_ID>`；
- 不使用 `task_id` 作为新 Job 的轮询标识；
- Poller 重启后继续使用已经保存的 `video_id`；
- 提交响应已经到达但本地结果不确定时进入未知结果状态，不得自动二次提交。

状态规范化：

| Provider 状态 | 内部状态 |
|---|---|
| `pending`, `queued` | `queued` |
| `processing`, `running` | `polling` |
| `succeeded`, `completed` | `completed` |
| `failed`, `error` | `failed` |

未知状态必须失败关闭为 `PROVIDER_STATUS_INVALID`。

### 6.4 视频结果

完成结果 URL 按以下顺序解析：

1. `metadata.url`，最新官方响应的主路径；
2. `url`；
3. `video_url`；
4. `data.url`；
5. `data.video_url`。

所有路径均缺失时返回 `RESULT_MISSING`。Worker 下载结果后必须验证为允许的视频媒体，
再由 Python 写入 Object Store 和 Generation Result。页面使用本地结果接口展示，不依赖
供应商临时 URL。

## 7. UI 与业务行为

供应商页面保持：

```text
Agnes
├── Agnes Image
└── Agnes Video
```

### 7.1 图片模型测试

- Agnes Image 模型行保留“测试”按钮；
- 弹窗包含提示词、尺寸等级和画幅比例；
- 提交前显示一次真实请求和可能费用警告；
- 每次用户确认只授权一次真实图片提交和必要的单次结果下载；
- 不允许自动重试、fallback 或批量请求；
- 成功后展示本地持久化的缩略图、媒体类型和耗时；
- 失败时展示稳定错误码。

### 7.2 视频正式生成

- Agnes Video 模型行不增加真实测试按钮；
- 模型详情提示用户到项目 Shot 生成流程验证；
- Shot 页面显示排队、生成中、完成或失败；
- 刷新页面或重启服务后继续同一个 Job；
- 完成后展示本地持久化视频。

### 7.3 提交前阻断

以下情况必须在网络提交前明确阻断：

- 项目没有绑定所需能力；
- 模型或供应商已停用；
- credential 缺失、损坏或不可用；
- 对应 Supplier Runtime 不可用；
- M6 Supplier execution feature flag 未开启；
- 图片尺寸或比例不受支持；
- 视频输入图数量或模式不符合规则；
- 视频参数不符合白名单或约束。

## 8. 安全与审计

- API Key 只从所选 credential version 注入；
- 适配源码、配置、日志和错误不得包含 credential；
- 网络只允许经过 Worker 注入 helper；
- 校验阶段所有网络 helper 返回 `NETWORK_DISABLED_DURING_VALIDATION`；
- Worker 继续执行公网地址、DNS 固定、peer IP、端口和重定向策略；
- 证据可以保存 HTTP 状态、响应结构、状态名称、opaque `video_id` 和字节统计；
- 证据不得保存 Authorization、Bearer、API Key、签名 query、完整签名资产 URL 或
  私密生成内容；
- 真实生成结果、数据库、credential 文件、`runtime-data` 和私密媒体不得进入 Git。

## 9. 错误语义

保留并补齐以下稳定错误：

- `CREDENTIAL_MISSING`
- `CREDENTIAL_STORAGE_CORRUPT`
- `SUPPLIER_RUNTIME_UNAVAILABLE`
- `INVALID_INPUT_IMAGES`
- `INVALID_IMAGE_SIZE`
- `INVALID_IMAGE_RATIO`
- `PROVIDER_RESPONSE_MALFORMED`
- `PROVIDER_VIDEO_ID_MISSING`
- `PROVIDER_STATUS_INVALID`
- `RESULT_MISSING`
- `HTTP_DESTINATION_NOT_ALLOWED`
- `SUPPLIER_WORKER_TIMEOUT`
- `SUBMISSION_OUTCOME_UNKNOWN`

浏览器只显示稳定错误码和用户可执行的下一步，不显示原始密钥、响应正文或临时签名 URL。

## 10. TDD 与自动验收

默认测试必须拒绝所有未声明真实网络。实施先写失败测试，再修改适配器。

必须覆盖：

### 图片

- 文生图的模型、提示词、尺寸、比例和 `extra_body.response_format`；
- 图生图参考图只位于 `extra_body.image`；
- 不发送 `tags` 或顶层 `response_format`；
- 尺寸等级、比例白名单和旧尺寸兼容；
- `data[0].url` 缺失时失败关闭；
- URL 下载、媒体验证、Object Store 和 generated asset 关联；
- 请求前持久化、失败审计、幂等复用和重启恢复；
- 模型行每次确认只提交一次。

### 视频

- 普通模式零至一张关键帧；
- `keyframes` 模式两至三张有序关键帧；
- `videoSubmit` exactly once；
- 创建响应保存 `video_id`；
- `videoPoll` 和 `videoFetch` 只使用 `video_id`；
- `metadata.url` 主路径及兼容结果路径；
- 未知状态、缺失结果和下载失败；
- 服务重启后续接原 Job，且不重新提交；
- MP4 校验、Object Store 与 Generation Result 关联；
- snapshot 路由和 feature flag 回滚。

### 横切

- credential、Bearer、签名 URL 和临时结果 URL 脱敏；
- legacy active/terminal Agnes Job 兼容；
- M1-M6 回归；
- 自动测试、CI、verifier 与只读审阅的真实请求计数均为零。

## 11. 真实验收授权边界

真实验收不是默认实施或自动测试的一部分。

1. 用户在 Agnes Image 模型行点击“确认并测试”，只授权一次真实图片请求和该结果的
   必要下载。
2. 图片通过后，用户在指定测试项目的安全 Shot 中主动点击生成视频，只授权一次
   `videoSubmit`。
3. 已授权的视频 Job 可以轮询同一个 `video_id` 并下载该 Job 的结果。
4. 授权不允许创建第二个视频 Job、自动重试、fallback、批量生成或完整章节生产。

## 12. 发布、回滚与历史兼容

- 默认保持 `M6_SUPPLIER_EXECUTION_ENABLED=false`；
- 假 Provider、完整回归和验收 verifier 全部通过后，才允许在本地运行配置中开启；
- 新适配器保存为新的不可变 Supplier Version；
- 新模型约束保存为新的不可变 Model Revision，项目 binding 继续引用稳定
  `supplier_model_id`；
- 已存在的 active Job 继续使用原 snapshot；
- 新 Job 使用 current Supplier Version；
- 异常时把 current version 切回上一版，不删除历史版本；
- 不删除 legacy backend、legacy fields、历史 Job、结果或 snapshot。

## 13. 验收基准

```text
AGNES_IMAGE_TEXT_TO_IMAGE=PASS
AGNES_IMAGE_IMAGE_TO_IMAGE=PASS
IMAGE_MODEL_TEST_SUBMIT_COUNT=1
PROJECT_IMAGE_GENERATION=PASS
VIDEO_SUBMIT_COUNT=1
VIDEO_POLL_IDENTIFIER=video_id
VIDEO_RESULT_PATH=metadata.url
VIDEO_RESULT_PERSISTED=true
RESTART_RESUME=PASS
SNAPSHOT_ROUTING=PASS
FEATURE_FLAG_ROLLBACK=PASS
SECRET_SCAN=PASS
REAL_REQUESTS_DURING_AUTOMATION=0
M1_M6_REGRESSION=PASS
```

## 14. 不在范围内

- Agnes 文本模型或图像理解入口；
- 新 Agnes 供应商或多账号连接；
- 视频模型行真实测试弹窗；
- 自动 retry、fallback 或批量生成；
- 完整章节或成片生产；
- 新视频时长、分辨率或高级参数 UI；
- 供应商管理、项目工作台或结果页面的视觉重设计；
- 删除 legacy provider 代码或历史数据；
- 未经用户操作授权的任何真实 Provider 请求。
