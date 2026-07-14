import json


def custom_supplier_template(slug, display_name):
    """Return the editable starter source for a newly created custom supplier."""
    supplier_id = json.dumps(slug, ensure_ascii=False)
    supplier_name = json.dumps(display_name, ensure_ascii=False)
    return f'''/**
 * AI Drama 供应商适配模板
 *
 * AI 生成适配代码步骤：
 * 1. 准备供应商官方 API 文档或脱敏 curl 示例，以及需要接入的模型名称和能力。
 * 2. 把资料与本模板交给 AI；没有足够信息时让 AI 主动追问，不得猜测端点或响应字段。
 * 3. 只提供认证字段名、请求体、示例响应；不要提供真实 API Key、Bearer 或签名链接。
 * 4. 让 AI 分析认证方式、端点、请求参数、成功/失败响应和异步任务状态，再开始写代码。
 * 5. 保留 vendor 的契约版本、helper 版本和已存在的稳定模型 ID，只实现需要的能力函数。
 * 6. 配置项放在 vendor.inputs；密钥由网页“密钥”页保存，运行时从 payload.credential 注入。
 * 7. 所有网络请求必须经过 helpers.http.request；不要读取文件、环境变量或宿主全局对象。
 * 8. 先点“校验并保存”（校验阶段禁止网络），再到“模型”页为具体文本或图片模型执行测试。
 *
 * 可直接复制给 AI 的指令：
 * “请依据随附的官方文档，在本模板中接入【供应商名称】的【text/image/video】能力。
 * 不得编造接口；不得写入任何密钥；保留 AI Drama 契约、稳定模型 ID 和未使用能力的骨架；
 * 只能使用 helpers.http.request；把供应商响应转换为下述规范化返回，并给关键映射添加中文注释。”
 *
 * 模型清单写法：
 * {{ supplierModelId: "稳定 UUID", providerModelName: "供应商模型名", displayName: "页面名称", capability: "text" }}
 * capability 可选 text、image、video。文本需实现 textRequest；图片需实现 imageRequest；
 * 视频需同时实现 videoSubmit、videoPoll、videoFetch。
 * supplierModelId 一经项目绑定就保持不变；providerModelName 是实际发给供应商的模型名；
 * displayName 只用于网页显示。可调端点和非密钥参数放入 inputs，不要写成散落常量。
 *
 * 运行时参数：
 * - payload.model：当前模型的 providerModelName
 * - payload.request：平台中立的本次请求
 * - payload.config：网页“配置”页保存的当前不可变配置
 * - payload.credential：网页“密钥”页选中的凭据，只能用于认证头，不得返回或记录
 * - helpers.http.request：唯一网络出口，负责目的地址、重定向、大小和超时限制
 *
 * 返回值约定：
 * - textRequest: {{ output: "规范化文本", usage: {{ input_tokens, output_tokens, total_tokens }} }}
 * - imageRequest: 返回 helpers.http.request 下载得到的本地媒体引用和 media_type
 * - videoSubmit: {{ video_id, status: "queued" }}；videoPoll 必须用 video_id，不能用 task_id
 * 供应商失败应抛出带稳定大写 code 的错误；不得吞掉错误，也不得返回原始认证头或签名 URL。
 */

export const vendor = {{
  id: {supplier_id},
  version: "template-1",
  name: {supplier_name},
  author: "AI Drama",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: {supplier_id},
  inputs: [
    {{ key: "base_url", label: "Base URL", type: "url", required: true }}
  ],
  inputValues: {{ base_url: "" }},
  models: []
}};

function operationNotConfigured(operation: string): never {{
  const error = new Error(`SUPPLIER_OPERATION_NOT_CONFIGURED: ${{operation}}`);
  Object.assign(error, {{ code: "SUPPLIER_OPERATION_NOT_CONFIGURED" }});
  throw error;
}}

export async function textRequest(_payload: unknown, _helpers: unknown) {{
  return operationNotConfigured("textRequest");
}}

export async function imageRequest(_payload: unknown, _helpers: unknown) {{
  return operationNotConfigured("imageRequest");
}}

export async function videoSubmit(_payload: unknown, _helpers: unknown) {{
  return operationNotConfigured("videoSubmit");
}}

export async function videoPoll(_payload: unknown, _helpers: unknown) {{
  return operationNotConfigured("videoPoll");
}}

export async function videoFetch(_payload: unknown, _helpers: unknown) {{
  return operationNotConfigured("videoFetch");
}}
'''
