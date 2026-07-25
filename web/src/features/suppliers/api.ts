import type { AxiosResponse } from "axios";
import { apiClient } from "../../api/client";

export type SupplierCredentialStatus = {
  configured: boolean;
  masked_suffix: string;
};

export type SupplierInput = {
  id?: string;
  key?: string;
  name?: string;
  label?: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
  description?: string;
  options?: Array<{
    value: string;
    label: string;
    description?: string;
  }>;
  [key: string]: unknown;
};

export type SupplierRead = {
  supplier_id: string;
  slug: string;
  display_name: string;
  source: "built_in" | "custom";
  enabled: number;
  current_supplier_version_id: string;
  current_config_revision_id: string;
  current_credential_version_id: string;
  revision: number;
  config_revision: number;
  credential_revision: number;
  model_catalog_revision: number;
  created_at: string;
  updated_at: string;
  author: string;
  version: string;
  manifest: Record<string, unknown>;
  inputs: SupplierInput[];
  input_values: Record<string, string>;
  config_values: Record<string, string>;
  capabilities: string[];
  model_count: number;
  base_url_summary: string;
  credential: SupplierCredentialStatus;
  credential_active_job_count: number;
};

export type SupplierCreate = { slug: string; display_name: string };
export type SupplierPatch = { display_name?: string; enabled?: boolean };
export type WithEtag<T> = { data: T; etag: string };
export type SupplierCodeRead = { source: string; supplier_version_id: string };
export type SupplierCodeSaved = {
  supplier_version_id: string;
  source_hash: string;
  compiled_artifact_hash: string;
  manifest_hash: string;
  compiler_name: string;
  compiler_version: string;
};
export type SupplierModelCapability = "text" | "image" | "video";
export type SupplierModelRead = {
  supplier_model_id: string;
  supplier_id: string;
  current_model_revision_id: string;
  model_revision_id: string;
  provider_model_name: string;
  display_name: string;
  capability: SupplierModelCapability;
  source: "built_in" | "overlay";
  enabled: number;
  revision: number;
  entity_revision: number;
  archived_at: string;
  archive_reason: string;
  definition: Record<string, unknown>;
  binding_count: number;
  created_at: string;
  updated_at: string;
};
export type SupplierModelCreate = {
  provider_model_name: string;
  display_name: string;
  capability: SupplierModelCapability;
  definition: Record<string, unknown>;
};
export type SupplierModelPatch = Partial<SupplierModelCreate> & {
  enabled?: boolean;
  acknowledged_binding_count?: number;
};
export type WithModelEtags<T> = WithEtag<T> & { catalogEtag: string };
export type ModelTestStatus =
  | "queued"
  | "submitting"
  | "completed"
  | "failed"
  | "submission_outcome_unknown";
export type ModelTestRead = {
  test_run_id: string;
  supplier_model_id: string;
  capability: "text" | "image";
  status: ModelTestStatus;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  output?: string;
  usage?: Record<string, number>;
  media_type?: string;
  byte_size?: number;
  elapsed_ms?: number;
  error_code?: string;
  error_message?: string;
  reasoning_effort?: string;
  size?: string;
  quality?: string;
  ratio?: string;
};

export type ReasoningEffort = "none" | "low" | "medium" | "high" | "xhigh" | "max";
export type ImageSize = "auto" | "1K" | "2K" | "3K" | "4K" | "1024x768" | "1024x1024" | "768x1024" | "1024x1536" | "1536x1024";
export type ImageQuality = "auto" | "low" | "medium" | "high";
export type ImageRatio = "1:1" | "3:4" | "4:3" | "16:9" | "9:16" | "2:3" | "3:2" | "21:9";
export type ModelTestOptions = {
  reasoning_effort?: ReasoningEffort | null;
  size?: ImageSize | null;
  quality?: ImageQuality | null;
  ratio?: ImageRatio | null;
};

function withEtag<T>(response: AxiosResponse<T>): WithEtag<T> {
  return { data: response.data, etag: String(response.headers?.etag ?? "") };
}

function withModelEtags<T>(response: AxiosResponse<T>): WithModelEtags<T> {
  return {
    ...withEtag(response),
    catalogEtag: String(response.headers?.["x-model-catalog-etag"] ?? ""),
  };
}

export async function listSuppliers(): Promise<SupplierRead[]> {
  const response = await apiClient.get<SupplierRead[]>("/suppliers");
  return response.data;
}

export async function getSupplier(supplierId: string): Promise<WithEtag<SupplierRead>> {
  return withEtag(await apiClient.get<SupplierRead>(`/suppliers/${supplierId}`));
}

export async function createSupplier(
  payload: SupplierCreate,
  idempotencyKey: string,
): Promise<SupplierRead> {
  const response = await apiClient.post<SupplierRead>("/suppliers", payload, {
    headers: { "Idempotency-Key": idempotencyKey, "If-None-Match": "*" },
  });
  return response.data;
}

export async function updateSupplier(
  supplierId: string,
  payload: SupplierPatch,
  etag: string,
): Promise<WithEtag<SupplierRead>> {
  return withEtag(
    await apiClient.patch<SupplierRead>(`/suppliers/${supplierId}`, payload, {
      headers: { "If-Match": etag },
    }),
  );
}

export async function saveSupplierConfig(
  supplierId: string,
  values: Record<string, string>,
  etag: string,
): Promise<WithEtag<{ config_revision_id: string; revision: number }>> {
  return withEtag(
    await apiClient.put(`/suppliers/${supplierId}/config`, { values }, {
      headers: { "If-Match": etag },
    }),
  );
}

export async function saveSupplierSecret(
  supplierId: string,
  credential: string,
  etag: string,
): Promise<WithEtag<SupplierCredentialStatus>> {
  return withEtag(
    await apiClient.put(`/suppliers/${supplierId}/secret`, { credential }, {
      headers: { "If-Match": etag },
    }),
  );
}

export async function deleteSupplierSecret(
  supplierId: string,
  etag: string,
  force = false,
): Promise<WithEtag<SupplierCredentialStatus>> {
  return withEtag(
    await apiClient.delete(`/suppliers/${supplierId}/secret`, {
      headers: { "If-Match": etag },
      params: force ? { force: true } : undefined,
    }),
  );
}

export async function getSupplierCode(supplierId: string): Promise<SupplierCodeRead> {
  const response = await apiClient.get<SupplierCodeRead>(`/suppliers/${supplierId}/code`);
  return response.data;
}

export async function saveSupplierCode(
  supplierId: string,
  source: string,
  etag: string,
): Promise<WithEtag<SupplierCodeSaved>> {
  return withEtag(
    await apiClient.put(`/suppliers/${supplierId}/code`, { source }, {
      headers: { "If-Match": etag },
    }),
  );
}

export async function restoreBuiltinSupplier(
  supplierId: string,
  etag: string,
): Promise<WithEtag<SupplierRead>> {
  return withEtag(
    await apiClient.post(`/suppliers/${supplierId}/restore-built-in`, undefined, {
      headers: { "If-Match": etag },
    }),
  );
}

export async function listSupplierModels(
  supplierId: string,
): Promise<WithEtag<SupplierModelRead[]>> {
  return withEtag(
    await apiClient.get<SupplierModelRead[]>(`/suppliers/${supplierId}/models`),
  );
}

export async function createSupplierModel(
  supplierId: string,
  payload: SupplierModelCreate,
  catalogEtag: string,
  idempotencyKey: string,
): Promise<WithModelEtags<SupplierModelRead>> {
  return withModelEtags(
    await apiClient.post<SupplierModelRead>(`/suppliers/${supplierId}/models`, payload, {
      headers: {
        "Idempotency-Key": idempotencyKey,
        "If-Match": catalogEtag,
        "If-None-Match": "*",
      },
    }),
  );
}

function combinedModelEtag(modelEtag: string, catalogEtag: string): string {
  return `${modelEtag}, ${catalogEtag}`;
}

export async function patchSupplierModel(
  modelId: string,
  payload: SupplierModelPatch,
  modelEtag: string,
  catalogEtag: string,
): Promise<WithModelEtags<SupplierModelRead>> {
  return withModelEtags(
    await apiClient.patch<SupplierModelRead>(`/models/${modelId}`, payload, {
      headers: { "If-Match": combinedModelEtag(modelEtag, catalogEtag) },
    }),
  );
}

export async function deleteSupplierModel(
  modelId: string,
  modelEtag: string,
  catalogEtag: string,
): Promise<void> {
  await apiClient.delete(`/models/${modelId}`, {
    headers: { "If-Match": combinedModelEtag(modelEtag, catalogEtag) },
  });
}

export async function getModelTestFeatureStatus(): Promise<{ enabled: boolean }> {
  const response = await apiClient.get<{ enabled: boolean }>("/model-tests/status");
  return response.data;
}

export async function createModelTest(
  modelId: string,
  prompt: string,
  options: ModelTestOptions,
  modelEtag: string,
  idempotencyKey: string,
): Promise<ModelTestRead> {
  const body: {
    prompt: string;
    reasoning_effort?: ReasoningEffort;
    size?: ImageSize;
    quality?: ImageQuality;
    ratio?: ImageRatio;
  } = { prompt };
  if (options.reasoning_effort) body.reasoning_effort = options.reasoning_effort;
  if (options.size) body.size = options.size;
  if (options.quality) body.quality = options.quality;
  if (options.ratio) body.ratio = options.ratio;
  const response = await apiClient.post<ModelTestRead>(
    `/models/${modelId}/tests`,
    body,
    { headers: { "Idempotency-Key": idempotencyKey, "If-Match": modelEtag } },
  );
  return response.data;
}

export async function recoverModelTest(
  modelId: string,
  idempotencyKey: string,
): Promise<ModelTestRead> {
  const response = await apiClient.get<ModelTestRead>(
    `/models/${modelId}/tests/by-idempotency-key`,
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
  return response.data;
}

export async function getModelTest(testRunId: string): Promise<ModelTestRead> {
  const response = await apiClient.get<ModelTestRead>(`/model-tests/${testRunId}`);
  return response.data;
}

export async function getModelTestContent(testRunId: string): Promise<Blob> {
  const response = await apiClient.get<Blob>(`/model-tests/${testRunId}/content`, {
    responseType: "blob",
  });
  return response.data;
}

export function newIdempotencyKey(prefix: string): string {
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `${prefix}-${suffix}`;
}
