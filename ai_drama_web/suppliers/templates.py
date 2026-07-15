import json


def custom_supplier_template(slug, display_name):
    """Return the editable starter source for a newly created custom supplier."""
    supplier_id = json.dumps(slug, ensure_ascii=False)
    supplier_name = json.dumps(display_name, ensure_ascii=False)
    return f'''/**
 * AI Drama 供应商适配模板
 *
 * AI 生成适配代码步骤：
 * 1. 收集供应商官方文本/图片/视频 API 文档、认证方式、端点、脱敏请求示例、响应示例、
 *    状态定义、限制和结果下载规则；没有足够信息时让 AI 主动追问，不得猜测。
 * 2. 不要提供真实 API Key。文档示例统一写 YOUR_API_KEY，真实值稍后在网页“密钥”页配置。
 * 3. 把完整模板交给 AI，要求保留 AI Drama manifest、helper、函数签名、隔离规则和规范返回。
 * 4. 只声明已由官方文档确认的 text、image 或 video 能力，不得让 AI 发明不支持的操作。
 * 5. 要求供应商错误映射为稳定且脱敏的 code，证据中移除密钥、认证头和签名查询参数。
 * 6. 视频必须拆成 submit/poll/fetch，并确认稳定查询 ID；Agnes 必须使用 video_id。
 * 7. 点“校验并保存”修复本地编译、manifest 和导出错误；校验禁止网络和顶层网络工作。
 * 8. 在“模型”页添加或核对模型，配置非密钥字段，再在遮罩密钥输入框保存真实凭据。
 * 9. 点击对应模型行“测试”，确认一次真实请求并检查规范化结果或脱敏错误。
 * 10. 仅实现已确认能力，并在模型级测试成功后再绑定项目。
 *
 * 信任边界与禁用清单：
 * - 网页中可编辑的适配代码属于本机用户明确保存的 trusted local code。VM 和 Node permission
 *   model 用于限制常规能力与宿主文件访问，但不是运行来源不明恶意代码的安全沙箱；不要粘贴
 *   未审查的第三方脚本。
 * - 禁止 import、require、process、原生 fetch、Node 内建模块、文件系统、环境变量、
 *   socket、子进程，以及 Toonflow 的 axios、logger、pollTask、createOpenAI 等全局对象。
 * - 禁止 exports.vendor、module.exports 或在 CommonJS 模板末尾追加 export {{}}；本文件只用 ESM 导出。
 * - 不得记录、返回或持久化 payload.credential、Authorization 认证头、Bearer 或签名查询值。
 * - 所有运行时网络只能通过 helpers.http.request；模块顶层不得发出任何 HTTP 请求。
 *
 * 可直接复制给 AI 的指令：
 * “请依据随附的官方文档，输出一个完整 TypeScript 文件，在本模板中接入【供应商名称】
 * 的【已确认能力】。不得编造接口或写入密钥；密钥示例只用 YOUR_API_KEY；保留 AI Drama
 * 契约、稳定模型 ID、隔离规则和未使用能力骨架；只能使用 helpers.http.request；把供应商
 * 响应转换为下述规范化返回，清理签名查询与认证信息，并给关键字段映射添加中文注释。”
 *
 * 模型清单写法：
 * {{ supplierModelId: "稳定 UUID", providerModelName: "供应商模型名", displayName: "页面名称", capability: "text" }}
 * 图片示例：{{ supplierModelId: "稳定 UUID", providerModelName: "image-model", displayName: "图片模型", capability: "image" }}
 * 视频示例：{{ supplierModelId: "稳定 UUID", providerModelName: "video-model", displayName: "视频模型", capability: "video" }}
 * 配置字段示例：{{ key: "base_url", label: "Base URL", type: "url", required: true }}
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
 * - helpers.http.request：唯一网络出口，负责目的地址、重定向、大小和超时限制；图生图可用
 *   multipart.fields 和 multipart.files，但 files.url 必须原样来自 payload.request.input_images
 * - helpers.media.decodeBase64：受限图片 base64 解码入口，返回本地媒体引用；不得自行使用 Buffer
 *
 * 返回值约定：
 * - textRequest: {{ output: "规范化文本", usage: {{ input_tokens, output_tokens, total_tokens }} }}
 * - imageRequest: 返回 helpers.http.request 下载或 helpers.media.decodeBase64 得到的本地媒体引用
 * - videoSubmit: {{ video_id, status: "queued" }}；videoPoll 必须用 video_id，不能用 task_id
 * 供应商失败应抛出带稳定大写 code 的错误；不得吞掉错误，也不得返回原始认证头或签名 URL。
 */

export const vendor = {{
  id: {supplier_id},
  version: "template-1",
  name: {supplier_name},
  author: "AI Drama",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v2",
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
