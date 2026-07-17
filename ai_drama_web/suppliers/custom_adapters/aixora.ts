/**
 * AIXORA GPT 文本与图片供应商适配器
 *
 * 使用 AI 接入其他供应商时，建议把本文件和供应商官方 API 文档一起交给 AI，并明确：
 * 1. 只替换已由官方文档确认的模型、端点、请求字段和响应字段，不猜测供应商能力；
 * 2. 不要把真实 API Key 写进代码，密钥只从 payload.credential 注入认证头；
 * 3. 保留稳定 supplierModelId、契约版本、helper 版本和规范化返回结构；
 * 4. 所有网络必须通过 helpers.http.request，禁止 fetch、axios、import、require 和 Node 全局；
 * 5. 图片 base64 必须通过 helpers.media.decodeBase64，不能在适配代码中接触 Buffer 或文件系统；
 * 6. 图生图 multipart 只传声明过的 input_images，由 Worker 下载、校验并组装文件；
 * 7. 先在网页执行“校验并保存”，再对具体模型执行一次明确授权的真实测试。
 *
 * 信任边界：网页保存的 adapter 属于 trusted local code。VM 与 Node permission model
 * 限制常规 API、宿主文件、子进程和线程访问，但不是恶意脚本沙箱；不要保存来源不明代码。
 *
 * AIXORA 当前冻结范围：五个 GPT 文本模型和 GPT Image 2 图片模型。/v1/models
 * 目录可能不列出图片模型，但 /v1/images/generations 已通过同账号真实调用验证可用。
 * 本文件不声明 Grok 或视频能力，也不会猜测或替换其它图片/视频模型。
 */

type SupplierPayload = {
  model: string;
  credential: string;
  config: { base_url?: string; reasoning_effort?: string };
  constraints?: { reasoning_effort?: string };
  request: {
    prompt?: string;
    messages?: unknown[];
    instructions?: string;
    system?: string;
    size?: string;
    quality?: string;
    input_images?: string[];
    parameters?: { reasoning_effort?: string };
  };
};

type SupplierHelpers = {
  http: { request(options: Record<string, unknown>): Promise<any> };
  media: { decodeBase64(value: string, mediaType: string): Promise<Record<string, unknown>> };
};

export const vendor = {
  id: "aixora",
  version: "ai-drama-2",
  name: "AIXORA",
  author: "AI Drama",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v2",
  rateLimitBucketKey: "aixora-generation",
  inputs: [
    { key: "base_url", label: "Base URL", type: "url", required: true },
    { key: "reasoning_effort", label: "默认思考深度", type: "text", required: true },
  ],
  inputValues: {
    base_url: "https://www.aixora.store/v1",
    reasoning_effort: "medium",
  },
  models: [
    {
      supplierModelId: "9ea394a5b44e555db3af4c95711c929b",
      providerModelName: "gpt-5.5",
      displayName: "GPT-5.5",
      capability: "text",
      constraints: { reasoning_effort: "medium" },
    },
    {
      supplierModelId: "07c95486e414569bb18f694431f3ad4f",
      providerModelName: "gpt-5.6",
      displayName: "GPT-5.6",
      capability: "text",
      constraints: { reasoning_effort: "medium" },
    },
    {
      supplierModelId: "a1a97eb5b16457c38a1e53ee7459c6de",
      providerModelName: "gpt-5.6-sol",
      displayName: "GPT-5.6 Sol",
      capability: "text",
      constraints: { reasoning_effort: "medium" },
    },
    {
      supplierModelId: "41f191fa614050daabefd1085cf730aa",
      providerModelName: "gpt-5.6-luna",
      displayName: "GPT-5.6 Luna",
      capability: "text",
      constraints: { reasoning_effort: "medium" },
    },
    {
      supplierModelId: "ad6e2e9101f35b62800dc8a6ff1cdaaa",
      providerModelName: "gpt-5.6-terra",
      displayName: "GPT-5.6 Terra",
      capability: "text",
      constraints: { reasoning_effort: "medium" },
    },
    {
      supplierModelId: "e7dc2c3c5a205726ad2b44b583e3aeb9",
      providerModelName: "gpt-image-2",
      displayName: "GPT Image 2",
      capability: "image",
      default_size: "1024x1024",
      constraints: {},
    },
  ],
};

const REASONING_EFFORTS = new Set(["none", "low", "medium", "high", "xhigh", "max"]);
const IMAGE_SIZES = new Set(["1024x1024", "1536x1024", "1024x1536", "auto"]);
const IMAGE_QUALITIES = new Set(["low", "medium", "high", "auto"]);

function fail(code: string): never {
  const error = new Error(code);
  Object.assign(error, { code });
  throw error;
}

/** Base URL 必须明确指向 OpenAI-compatible 的 /v1 根路径，避免请求落到网页路径。 */
function baseUrl(payload: SupplierPayload): string {
  const value = String(payload.config?.base_url || "").replace(/\/+$/, "");
  if (!/^https:\/\/[A-Za-z0-9.-]+(?::443)?\/v1$/.test(value)) fail("INVALID_BASE_URL");
  return value;
}

function authorization(payload: SupplierPayload): Record<string, string> {
  if (!payload.credential) fail("CREDENTIAL_MISSING");
  return {
    Authorization: `Bearer ${payload.credential}`,
    "Content-Type": "application/json",
  };
}

/** 请求级覆盖优先，其次使用快照冻结值，最后才读取供应商默认值。 */
function reasoningEffort(payload: SupplierPayload): string {
  const value = String(
    payload.request?.parameters?.reasoning_effort
      || payload.constraints?.reasoning_effort
      || payload.config?.reasoning_effort
      || "medium",
  );
  if (!REASONING_EFFORTS.has(value)) fail("INVALID_REASONING_EFFORT");
  return value;
}

/** Responses API 可能提供 output_text，也可能只提供标准 output/content 数组。 */
function responseText(raw: any): string {
  if (typeof raw?.output_text === "string" && raw.output_text) return raw.output_text;
  const parts: string[] = [];
  for (const item of Array.isArray(raw?.output) ? raw.output : []) {
    for (const content of Array.isArray(item?.content) ? item.content : []) {
      if (typeof content?.text === "string") parts.push(content.text);
    }
  }
  if (!parts.length) fail("PROVIDER_RESPONSE_MALFORMED");
  return parts.join("");
}

/**
 * AIXORA 的 Responses 入口对字符串 input 的兼容性并不稳定：部分推理模型会只返回
 * reasoning 项而不返回最终 message。普通提示词因此统一转换为 Responses API 的标准
 * message/input_text 结构；调用方已提供 messages 时保持原样。这里不做失败重试，避免
 * 一次用户测试被重复提交和重复计费。
 */
function responsesInput(payload: SupplierPayload): unknown[] {
  if (Array.isArray(payload.request?.messages) && payload.request.messages.length) {
    return payload.request.messages;
  }
  return [
    {
      type: "message",
      role: "user",
      content: [{ type: "input_text", text: String(payload.request?.prompt || "") }],
    },
  ];
}

export async function textRequest(payload: SupplierPayload, helpers: SupplierHelpers) {
  const body: Record<string, unknown> = {
    model: payload.model,
    input: responsesInput(payload),
    reasoning: { effort: reasoningEffort(payload) },
    stream: false,
    store: false,
  };
  const instructions = payload.request?.instructions || payload.request?.system;
  if (instructions) body.instructions = String(instructions);

  const raw = await helpers.http.request({
    method: "POST",
    url: `${baseUrl(payload)}/responses`,
    headers: authorization(payload),
    body,
  });
  const usage = raw?.usage || {};
  const inputTokens = Number(usage.input_tokens || 0);
  const outputTokens = Number(usage.output_tokens || 0);
  return {
    output: responseText(raw),
    usage: {
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      total_tokens: Number(usage.total_tokens || inputTokens + outputTokens),
    },
  };
}

function imageFields(payload: SupplierPayload): Record<string, string | number> {
  const size = String(payload.request?.size || "1024x1024");
  if (!IMAGE_SIZES.has(size)) fail("INVALID_IMAGE_SIZE");
  const fields: Record<string, string | number> = {
    model: payload.model,
    prompt: String(payload.request?.prompt || ""),
    size,
  };
  const quality = payload.request?.quality;
  if (quality !== undefined) {
    if (!IMAGE_QUALITIES.has(String(quality))) fail("INVALID_IMAGE_QUALITY");
    fields.quality = String(quality);
  }
  return fields;
}

/** 图片响应统一转成本地临时媒体引用，Python 网关随后校验 hash 并写入 object store。 */
async function normalizedImage(raw: any, helpers: SupplierHelpers) {
  const item = raw?.data?.[0];
  if (typeof item?.b64_json === "string" && item.b64_json) {
    return helpers.media.decodeBase64(item.b64_json, "image/png");
  }
  if (typeof item?.url === "string" && item.url.startsWith("https://")) {
    return helpers.http.request({ method: "GET", url: item.url, responseType: "bytes" });
  }
  return fail("PROVIDER_RESPONSE_MALFORMED");
}

export async function imageRequest(payload: SupplierPayload, helpers: SupplierHelpers) {
  if (payload.model !== "gpt-image-2") fail("MODEL_CAPABILITY_MISMATCH");
  const fields = imageFields(payload);
  const inputs = Array.isArray(payload.request?.input_images)
    ? payload.request.input_images.map(String)
    : [];

  if (inputs.length) {
    const auth = authorization(payload).Authorization;
    // 文件内容由 Worker 从 payload.request.input_images 的原始声明中取得；适配代码看不到字节。
    const raw = await helpers.http.request({
      method: "POST",
      url: `${baseUrl(payload)}/images/edits`,
      headers: { Authorization: auth },
      multipart: {
        fields,
        files: inputs.map(url => ({ fieldName: "image[]", url })),
      },
    });
    return normalizedImage(raw, helpers);
  }

  const raw = await helpers.http.request({
    method: "POST",
    url: `${baseUrl(payload)}/images/generations`,
    headers: authorization(payload),
    // AIXORA supports OpenAI-compatible URL results. Prefer URL over b64_json
    // so the Worker does not need to move multi-megabyte JSON through the VM.
    body: { ...fields, n: 1, response_format: "url" },
  });
  return normalizedImage(raw, helpers);
}
