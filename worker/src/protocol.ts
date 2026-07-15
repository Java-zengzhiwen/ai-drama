export const WORKER_PROTOCOL_VERSION = "1" as const;
export const HELPER_API_VERSION = "ai-drama-helper-v2" as const;

export type SupplierOperation =
  | "validate"
  | "textRequest"
  | "imageRequest"
  | "videoSubmit"
  | "videoPoll"
  | "videoFetch";
