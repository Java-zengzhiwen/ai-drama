export const WORKER_PROTOCOL_VERSION = "2" as const;
export const HELPER_API_VERSION = "ai-drama-helper-v3" as const;

export type SupplierOperation =
  | "validate"
  | "textRequest"
  | "textStream"
  | "imageRequest"
  | "videoSubmit"
  | "videoPoll"
  | "videoFetch";

export type SupplierStreamFrame =
  | { type: "started"; sequence: number }
  | { type: "text_delta"; sequence: number; text: string }
  | { type: "usage"; sequence: number; usage: Record<string, number> }
  | { type: "completed"; sequence: number; evidence: Record<string, unknown> }
  | { type: "failed"; sequence: number; errorCode: string; evidence: Record<string, unknown> };
