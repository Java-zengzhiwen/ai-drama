import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import {
  createSupplier,
  deleteSupplierSecret,
  getSupplierCode,
  getSupplier,
  listSuppliers,
  restoreBuiltinSupplier,
  saveSupplierCode,
  saveSupplierConfig,
  saveSupplierSecret,
  updateSupplier,
} from "./api";
import { LOCAL_MANAGEMENT_MESSAGE, toManagementError } from "./managementErrors";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const get = apiClient.get as unknown as Mock;
const post = apiClient.post as unknown as Mock;
const patch = apiClient.patch as unknown as Mock;
const put = apiClient.put as unknown as Mock;
const remove = apiClient.delete as unknown as Mock;

describe("supplier management API", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    patch.mockReset();
    put.mockReset();
    remove.mockReset();
  });

  test("uses independent config credential and supplier ETags", async () => {
    put.mockResolvedValue({ data: { configured: true, masked_suffix: "ABCD" }, headers: {} });
    remove.mockResolvedValue({ data: { configured: false, masked_suffix: "" }, headers: {} });
    post.mockResolvedValue({ data: { supplier_id: "supplier-1" }, headers: { etag: '"supplier-3"' } });

    await saveSupplierConfig("supplier-1", { base_url: "https://api.example.invalid" }, '"config-2"');
    await saveSupplierSecret("supplier-1", "write-only-value", '"credential-1"');
    await deleteSupplierSecret("supplier-1", '"credential-2"');
    await restoreBuiltinSupplier("supplier-1", '"supplier-2"');

    expect(put).toHaveBeenNthCalledWith(
      1,
      "/suppliers/supplier-1/config",
      { values: { base_url: "https://api.example.invalid" } },
      { headers: { "If-Match": '"config-2"' } },
    );
    expect(put).toHaveBeenNthCalledWith(
      2,
      "/suppliers/supplier-1/secret",
      { credential: "write-only-value" },
      { headers: { "If-Match": '"credential-1"' } },
    );
    expect(remove).toHaveBeenCalledWith("/suppliers/supplier-1/secret", {
      headers: { "If-Match": '"credential-2"' },
    });
    expect(post).toHaveBeenCalledWith(
      "/suppliers/supplier-1/restore-built-in",
      undefined,
      { headers: { "If-Match": '"supplier-2"' } },
    );
  });

  test("loads and saves source only through the local code endpoint", async () => {
    get.mockResolvedValue({ data: { source: "export const vendor = {};", supplier_version_id: "v1" } });
    put.mockResolvedValue({
      data: { supplier_version_id: "v2", compiler_name: "esbuild", compiler_version: "1" },
      headers: { etag: '"supplier-2"' },
    });

    await expect(getSupplierCode("supplier-1")).resolves.toEqual({
      source: "export const vendor = {};",
      supplier_version_id: "v1",
    });
    await saveSupplierCode("supplier-1", "export const vendor = {};", '"supplier-1"');

    expect(get).toHaveBeenCalledWith("/suppliers/supplier-1/code");
    expect(put).toHaveBeenCalledWith(
      "/suppliers/supplier-1/code",
      { source: "export const vendor = {};" },
      { headers: { "If-Match": '"supplier-1"' } },
    );
  });

  test("uses relative API paths and captures supplier ETag", async () => {
    get.mockResolvedValueOnce({ data: [], headers: {} });
    get.mockResolvedValueOnce({
      data: { supplier_id: "supplier-1" },
      headers: { etag: '"supplier-4"' },
    });

    await expect(listSuppliers()).resolves.toEqual([]);
    await expect(getSupplier("supplier-1")).resolves.toEqual({
      data: { supplier_id: "supplier-1" },
      etag: '"supplier-4"',
    });
    expect(get).toHaveBeenNthCalledWith(1, "/suppliers");
    expect(get).toHaveBeenNthCalledWith(2, "/suppliers/supplier-1");
  });

  test("sends creation and mutation preconditions", async () => {
    post.mockResolvedValue({ data: { supplier_id: "supplier-1" }, headers: {} });
    patch.mockResolvedValue({
      data: { supplier_id: "supplier-1", revision: 2 },
      headers: { etag: '"supplier-2"' },
    });

    await createSupplier(
      { slug: "local-studio", display_name: "Local Studio" },
      "create-local-studio",
    );
    await updateSupplier(
      "supplier-1",
      { display_name: "Renamed", enabled: false },
      '"supplier-1"',
    );

    expect(post).toHaveBeenCalledWith(
      "/suppliers",
      { slug: "local-studio", display_name: "Local Studio" },
      { headers: { "Idempotency-Key": "create-local-studio", "If-None-Match": "*" } },
    );
    expect(patch).toHaveBeenCalledWith(
      "/suppliers/supplier-1",
      { display_name: "Renamed", enabled: false },
      { headers: { "If-Match": '"supplier-1"' } },
    );
  });

  test("normalizes nested and top-level management errors", () => {
    const localOnly = toManagementError({
      isAxiosError: true,
      response: {
        status: 403,
        data: { error_code: "LOCAL_MANAGEMENT_ONLY", error_message: "denied" },
      },
    });
    const conflict = toManagementError({
      isAxiosError: true,
      response: {
        status: 409,
        data: { detail: { error_code: "REVISION_CONFLICT" } },
      },
    });

    expect(localOnly).toEqual({
      code: "LOCAL_MANAGEMENT_ONLY",
      message: LOCAL_MANAGEMENT_MESSAGE,
      status: 403,
    });
    expect(conflict).toEqual({
      code: "REVISION_CONFLICT",
      message: "数据已在其他页面更新，请重新加载后再保存。",
      status: 409,
    });
  });
});
