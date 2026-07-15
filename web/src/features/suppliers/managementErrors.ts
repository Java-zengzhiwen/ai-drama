import axios from "axios";

export const LOCAL_MANAGEMENT_MESSAGE =
  "此管理功能只能在运行 AI Drama 的本机访问。\n请使用本地地址打开，不要通过公网资产域名、FRP 或反向代理访问。";

export type ManagementError = {
  code: string;
  message: string;
  status?: number;
  line?: number;
  column?: number;
};

const ERROR_MESSAGES: Record<string, string> = {
  REVISION_CONFLICT: "数据已在其他页面更新，请重新加载后再保存。",
  IDEMPOTENCY_CONFLICT: "相同操作标识对应了不同内容，请重新发起操作。",
  PRECONDITION_REQUIRED: "缺少版本条件，请重新加载后再保存。",
  SUPPLIER_NOT_FOUND: "供应商不存在或已被移除。",
  MODEL_NOT_FOUND: "模型不存在或已被移除。",
  MODEL_BINDING_MISSING: "尚未配置此步骤所需的模型。",
  MODEL_CAPABILITY_MISMATCH: "所选模型能力与此步骤不匹配，请重新选择。",
  MODEL_DISABLED: "所选模型已停用，请重新选择。",
  MODEL_ARCHIVED: "所选模型已归档，请重新选择其他模型。",
  SUPPLIER_DISABLED: "所选模型的供应商已停用，请重新选择。",
  PROJECT_NOT_FOUND: "项目不存在或已被移除。",
  OPERATION_NOT_FOUND: "当前步骤不支持模型覆盖。",
  CREDENTIAL_IN_USE: "当前密钥仍被活动任务使用，请确认影响后再强制删除。",
};

export function toManagementError(error: unknown): ManagementError {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as
      | { error_code?: string; error_message?: string; detail?: Record<string, unknown> }
      | undefined;
    const detail: Record<string, unknown> =
      payload?.detail && typeof payload.detail === "object"
        ? payload.detail
        : ((payload ?? {}) as Record<string, unknown>);
    const code = typeof detail?.error_code === "string" ? detail.error_code : "REQUEST_FAILED";
    const serverMessage =
      typeof detail?.error_message === "string" ? detail.error_message : undefined;
    return {
      code,
      message:
        code === "LOCAL_MANAGEMENT_ONLY"
          ? LOCAL_MANAGEMENT_MESSAGE
          : ERROR_MESSAGES[code] ?? serverMessage ?? "操作失败，请稍后重试。",
      status: error.response?.status,
      ...(typeof detail?.line === "number" ? { line: detail.line } : {}),
      ...(typeof detail?.column === "number" ? { column: detail.column } : {}),
    };
  }
  return { code: "REQUEST_FAILED", message: "操作失败，请稍后重试。" };
}
