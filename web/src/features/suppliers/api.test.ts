import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import {
  createSupplier,
  getSupplier,
  listSuppliers,
  updateSupplier,
} from "./api";
import { LOCAL_MANAGEMENT_MESSAGE, toManagementError } from "./managementErrors";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const get = apiClient.get as unknown as Mock;
const post = apiClient.post as unknown as Mock;
const patch = apiClient.patch as unknown as Mock;

describe("supplier management API", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    patch.mockReset();
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
