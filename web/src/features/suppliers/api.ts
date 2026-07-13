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

function withEtag<T>(response: AxiosResponse<T>): WithEtag<T> {
  return { data: response.data, etag: String(response.headers?.etag ?? "") };
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
): Promise<WithEtag<SupplierCredentialStatus>> {
  return withEtag(
    await apiClient.delete(`/suppliers/${supplierId}/secret`, {
      headers: { "If-Match": etag },
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

export function newIdempotencyKey(prefix: string): string {
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `${prefix}-${suffix}`;
}
