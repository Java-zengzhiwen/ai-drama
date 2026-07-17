import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import type { SupplierRead } from "./api";
import { SupplierModelsPanel } from "./SupplierModelsPanel";

vi.mock("../../api/client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const get = apiClient.get as unknown as Mock;
const post = apiClient.post as unknown as Mock;
const patch = apiClient.patch as unknown as Mock;
const remove = apiClient.delete as unknown as Mock;

const supplier = {
  supplier_id: "supplier-1",
  display_name: "Local Supplier",
  enabled: 1,
  model_catalog_revision: 4,
} as SupplierRead;

const models = [
  {
    supplier_model_id: "stable-base-text",
    supplier_id: "supplier-1",
    current_model_revision_id: "revision-base-2",
    model_revision_id: "revision-base-2",
    provider_model_name: "text-provider-v2",
    display_name: "Text Model",
    capability: "text",
    source: "built_in",
    enabled: 1,
    revision: 2,
    entity_revision: 2,
    definition: { modes: ["chat"], limits: { context: 128000 } },
    binding_count: 2,
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
  },
  {
    supplier_model_id: "stable-overlay-image",
    supplier_id: "supplier-1",
    current_model_revision_id: "revision-overlay-1",
    model_revision_id: "revision-overlay-1",
    provider_model_name: "image-provider-v1",
    display_name: "Image Model",
    capability: "image",
    source: "overlay",
    enabled: 1,
    revision: 1,
    entity_revision: 1,
    definition: { size: ["1024x1024"] },
    binding_count: 0,
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
  },
];

function renderPanel(currentSupplier = supplier) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <SupplierModelsPanel supplier={currentSupplier} />
    </QueryClientProvider>,
  );
}

describe("supplier models panel", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    patch.mockReset();
    remove.mockReset();
    sessionStorage.clear();
    get.mockResolvedValue({ data: models, headers: { etag: '"model-catalog-4"' } });
  });

  test("shows final model-level test actions only for enabled text and image models", async () => {
    const video = {
      ...models[1],
      supplier_model_id: "stable-video",
      current_model_revision_id: "revision-video-1",
      model_revision_id: "revision-video-1",
      display_name: "Video Model",
      provider_model_name: "video-provider-v1",
      capability: "video",
    };
    get.mockImplementation((url: string) => Promise.resolve(
      url === "/model-tests/status"
        ? { data: { enabled: true }, headers: {} }
        : { data: [...models, video], headers: { etag: '"model-catalog-4"' } },
    ));

    renderPanel();

    expect(await screen.findByRole("button", { name: "测试 Text Model" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试 Image Model" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "测试 Video Model" })).not.toBeInTheDocument();
    const imageRow = screen.getByRole("cell", { name: "Image Model" }).closest("tr");
    expect(imageRow?.querySelector(".row-actions")?.querySelector("button:last-child")).toHaveAccessibleName("测试 Image Model");
  });

  test("hides all model test actions while the feature flag is off", async () => {
    get.mockImplementation((url: string) => Promise.resolve(
      url === "/model-tests/status"
        ? { data: { enabled: false }, headers: {} }
        : { data: models, headers: { etag: '"model-catalog-4"' } },
    ));

    renderPanel();
    await screen.findByRole("cell", { name: "Text Model" });

    expect(screen.queryByRole("button", { name: /测试 Text Model/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /测试 Image Model/ })).not.toBeInTheDocument();
  });

  test("restores and disables a model row with a persisted active run", async () => {
    sessionStorage.setItem(
      "ai-drama:model-test:stable-base-text",
      JSON.stringify({ idempotencyKey: "stored-key", testRunId: "run-active" }),
    );
    get.mockImplementation((url: string) => {
      if (url === "/model-tests/status") return Promise.resolve({ data: { enabled: true }, headers: {} });
      if (url === "/model-tests/run-active") {
        return Promise.resolve({
          data: {
            test_run_id: "run-active",
            supplier_model_id: "stable-base-text",
            capability: "text",
            status: "queued",
            created_at: "2026-07-14T00:00:00Z",
          },
          headers: {},
        });
      }
      return Promise.resolve({ data: models, headers: { etag: '"model-catalog-4"' } });
    });

    renderPanel();

    expect(await screen.findByRole("dialog", { name: "测试模型连接" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试 Text Model" })).toBeDisabled();
    expect(await screen.findByText(/测试编号 run-active/)).toBeInTheDocument();
  });

  test("renders stable identity table and selected model inspector", async () => {
    renderPanel();

    expect(await screen.findByRole("cell", { name: "Text Model" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "显示名称" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "供应商模型名" })).toBeInTheDocument();
    expect(screen.getByText("内置")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看 Text Model" }));
    expect(screen.getByText("stable-base-text")).toBeInTheDocument();
    expect(screen.getByText("revision-base-2")).toBeInTheDocument();
    expect(screen.getByText("已绑定 2 处" )).toBeInTheDocument();
    expect(screen.getByText(/128000/)).toBeInTheDocument();
  });

  test("creates a new overlay with catalog preconditions", async () => {
    post.mockResolvedValue({
      data: { ...models[1], supplier_model_id: "new-overlay-video", capability: "video" },
      headers: { etag: '"model-new-overlay-video-1"', "x-model-catalog-etag": '"model-catalog-5"' },
    });
    renderPanel();
    await screen.findByRole("cell", { name: "Text Model" });
    fireEvent.click(screen.getByRole("button", { name: "新增模型" }));
    fireEvent.change(screen.getByLabelText("显示名称"), { target: { value: "Video Model" } });
    fireEvent.change(screen.getByLabelText("供应商模型名"), { target: { value: "video-v1" } });
    fireEvent.change(screen.getByLabelText("能力"), { target: { value: "video" } });
    fireEvent.click(screen.getByRole("button", { name: "保存新模型" }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0][0]).toBe("/suppliers/supplier-1/models");
    expect(post.mock.calls[0][2].headers["If-Match"]).toBe('"model-catalog-4"');
    expect(post.mock.calls[0][2].headers["If-None-Match"]).toBe("*");
  });

  test("requires affected-binding acknowledgement before semantic edit", async () => {
    patch.mockResolvedValue({
      data: { ...models[0], display_name: "Text Model Renamed", revision: 3 },
      headers: { etag: '"model-stable-base-text-3"', "x-model-catalog-etag": '"model-catalog-5"' },
    });
    renderPanel();
    await screen.findByRole("cell", { name: "Text Model" });
    fireEvent.click(screen.getByRole("button", { name: "编辑 Text Model" }));
    const save = screen.getByRole("button", { name: "保存新版本" });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("显示名称"), { target: { value: "Text Model Renamed" } });
    fireEvent.click(screen.getByLabelText("我已确认将影响 2 处项目绑定"));
    fireEvent.click(save);

    await waitFor(() => expect(patch).toHaveBeenCalledTimes(1));
    expect(patch).toHaveBeenCalledWith(
      "/models/stable-base-text",
      expect.objectContaining({ display_name: "Text Model Renamed", acknowledged_binding_count: 2 }),
      { headers: { "If-Match": '"model-stable-base-text-2", "model-catalog-4"' } },
    );
  });

  test("edits AIXORA text reasoning without clobbering advanced definition", async () => {
    const aixora = { ...supplier, slug: "aixora", display_name: "AIXORA" } as SupplierRead;
    const aixoraModels = [
      {
        ...models[0],
        binding_count: 0,
        definition: {
          modes: ["responses"],
          limits: { context: 128000 },
          constraints: { reasoning_effort: "low", temperature: 0.2 },
        },
      },
    ];
    get.mockImplementation((url: string) => Promise.resolve(
      url === "/model-tests/status"
        ? { data: { enabled: true }, headers: {} }
        : { data: aixoraModels, headers: { etag: '"model-catalog-4"' } },
    ));
    patch.mockResolvedValue({ data: aixoraModels[0], headers: {} });

    renderPanel(aixora);
    await screen.findByRole("cell", { name: "Text Model" });
    fireEvent.click(screen.getByRole("button", { name: "编辑 Text Model" }));

    expect(screen.getByLabelText("默认思考深度")).toHaveValue("low");
    fireEvent.change(screen.getByLabelText("默认思考深度"), { target: { value: "high" } });
    fireEvent.click(screen.getByRole("button", { name: "保存新版本" }));

    await waitFor(() => expect(patch).toHaveBeenCalledTimes(1));
    expect(patch.mock.calls[0][1].definition).toEqual({
      modes: ["responses"],
      limits: { context: 128000 },
      constraints: { reasoning_effort: "high", temperature: 0.2 },
    });
  });

  test("separates disable and physical-delete rules", async () => {
    patch.mockResolvedValue({ data: { ...models[0], enabled: 0, revision: 3 }, headers: {} });
    remove.mockResolvedValue({ data: undefined, headers: {} });
    renderPanel();
    await screen.findByRole("cell", { name: "Text Model" });

    expect(screen.getByRole("button", { name: "删除 Text Model" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "停用 Text Model" }));
    await waitFor(() =>
      expect(patch).toHaveBeenCalledWith(
        "/models/stable-base-text",
        { enabled: false },
        { headers: { "If-Match": '"model-stable-base-text-2", "model-catalog-4"' } },
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "删除 Image Model" }));
    expect(screen.getByText("没有历史引用的模型会永久删除；已有测试或任务历史的模型会归档并从可选列表隐藏。")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除模型" }));
    await waitFor(() => expect(remove).toHaveBeenCalledTimes(1));
  });

  test("renders stale combined-ETag conflict without retrying", async () => {
    patch.mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: { detail: { error_code: "REVISION_CONFLICT" } } },
    });
    renderPanel();
    await screen.findByRole("cell", { name: "Text Model" });
    fireEvent.click(screen.getByRole("button", { name: "停用 Text Model" }));

    expect(await screen.findByText("数据已在其他页面更新，请重新加载后再保存。" )).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新加载模型" })).toBeInTheDocument();
    expect(patch).toHaveBeenCalledTimes(1);
  });

  test("reloads the current model entity and succeeds after an edit conflict", async () => {
    const refreshed = {
      ...models[0],
      display_name: "Text Model Remote",
      entity_revision: 3,
      revision: 3,
      current_model_revision_id: "revision-base-3",
      model_revision_id: "revision-base-3",
      binding_count: 3,
    };
    get
      .mockResolvedValueOnce({ data: models, headers: { etag: '"model-catalog-4"' } })
      .mockResolvedValue({ data: [refreshed, models[1]], headers: { etag: '"model-catalog-5"' } });
    patch
      .mockRejectedValueOnce({
        isAxiosError: true,
        response: { status: 409, data: { detail: { error_code: "REVISION_CONFLICT" } } },
      })
      .mockResolvedValueOnce({ data: refreshed, headers: {} });
    renderPanel();
    await screen.findByRole("cell", { name: "Text Model" });
    fireEvent.click(screen.getByRole("button", { name: "编辑 Text Model" }));
    fireEvent.click(screen.getByLabelText("我已确认将影响 2 处项目绑定"));
    fireEvent.click(screen.getByRole("button", { name: "保存新版本" }));

    const reload = await screen.findByRole("button", { name: "重新加载模型" });
    fireEvent.click(reload);
    await waitFor(() => {
      const modelCatalogCalls = get.mock.calls.filter(([path]) => path === `/suppliers/${supplier.supplier_id}/models`);
      expect(modelCatalogCalls).toHaveLength(2);
    });
    expect(screen.getByLabelText("显示名称")).toHaveValue("Text Model Remote");
    expect(screen.getByRole("button", { name: "保存新版本" })).toBeDisabled();
    fireEvent.click(screen.getByLabelText("我已确认将影响 3 处项目绑定"));
    fireEvent.click(screen.getByRole("button", { name: "保存新版本" }));

    await waitFor(() => expect(patch).toHaveBeenCalledTimes(2));
    expect(patch.mock.calls[1][2]).toEqual({
      headers: { "If-Match": '"model-stable-base-text-3", "model-catalog-5"' },
    });
    expect(patch.mock.calls[1][1]).toEqual(expect.objectContaining({
      display_name: "Text Model Remote",
      acknowledged_binding_count: 3,
    }));
  });
});
