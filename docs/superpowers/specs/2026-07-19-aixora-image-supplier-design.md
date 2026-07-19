# Aixora Image 独立供应商设计

日期：2026-07-19  
状态：已获用户口头确认，等待书面设计复核

## 目标

在现有本地供应商管理中新增一个自定义供应商 `aixora-image`。它完整复制当前 `aixora` 的适配能力和模型目录，但使用完全独立的凭据，使同一个 Aixora 服务可以按账号或 Key 分组管理。

## 冻结决策

- 新供应商 slug 和显示名称均为 `aixora-image`。
- 复制当前 `aixora` 的不可变适配源码，编译后生成 `aixora-image` 自己的 supplier version。
- 复制当前有效配置值，包括 Base URL 和默认思考深度；后续两个供应商可独立修改配置。
- 复制当前全部六个模型定义：五个文本模型和一个 `GPT Image 2` 图片模型。
- 每个复制模型都生成新的稳定 `supplier_model_id` 和不可变 `model_revision_id`，不得复用原供应商的身份。
- 原 `aixora` 保持不变，模型不删除、不停用。
- 不复制原供应商的 credential、credential version、测试记录、测试媒体、生成任务、执行快照、项目绑定或幂等记录。
- 新供应商初始 credential 状态为未配置；用户在本地网页中填写另一把 Key。
- 本次创建不自动修改任何项目模型绑定。

## 数据流

1. 读取现有 `aixora` 的当前 supplier version、配置 revision 和六个当前模型 revision。
2. 通过受 loopback-only 保护的管理 API 创建 `aixora-image`。
3. 将复制后的适配源码中的供应商 manifest 身份、名称和限流桶改为 `aixora-image`，避免两个账号共享运行时身份或限流桶。
4. 保存并本地编译适配代码；校验阶段禁止网络。
5. 保存复制后的非敏感配置。
6. 按原模型定义创建六个新的 overlay 模型。
7. 保持 credential 未配置，等待用户在网页填写新的 Key。

## 安全与隔离

- 不读取或复制原 credential 明文。
- 不在终端、日志、设计稿、Git 或响应中输出任何 Key。
- 供应商创建和配置只允许 loopback 请求。
- 两个供应商使用不同 credential version、supplier version、model identity 和 rate-limit bucket。
- 创建和离线验收不发起真实 Provider 请求。
- 真实测试仍需用户在模型行点击“确认并测试”，每次确认只授权一次对应模型调用。

## 验收标准

- 供应商列表同时显示 `aixora` 和 `aixora-image`，两者均可独立进入管理页面。
- `aixora-image` 的凭据状态为未配置，原 `aixora` 的凭据状态不变。
- `aixora-image` 显示与原供应商等价的六个模型，但所有模型 ID 均不同。
- 新供应商 Base URL 与默认思考深度初始值和原供应商一致。
- 新适配代码通过本地编译和网络禁用校验。
- 原供应商、项目绑定、历史任务、测试记录和运行时数据不发生变化。
- 完成定向测试、供应商管理 verifier、模型测试 verifier、迁移 verifier 和 `git diff --check`。

## 回滚

若创建或验证失败，在没有项目绑定、测试运行或生成任务引用时删除新建的 overlay 模型并停用 `aixora-image`。原 `aixora` 及其凭据、模型、绑定和历史不受影响。

## 不在范围内

- 不复制旧 Key。
- 不自动执行文本或图片真实测试。
- 不修改现有项目默认模型或步骤覆盖。
- 不新增供应商复制按钮或其他 UI 功能。
- 不改变 Aixora API contract、模型名或响应解析逻辑。
