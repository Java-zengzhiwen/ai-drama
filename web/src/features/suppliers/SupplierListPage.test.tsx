import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { App } from "../../app/App";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const get = apiClient.get as unknown as Mock;
const post = apiClient.post as unknown as Mock;

const suppliers = [
  {
    supplier_id: "agnes-1",
    slug: "agnes",
    display_name: "Agnes",
    source: "built_in",
    enabled: 1,
    revision: 2,
    config_revision: 3,
    credential_revision: 1,
    model_catalog_revision: 4,
    current_supplier_version_id: "version-2",
    current_config_revision_id: "config-3",
    current_credential_version_id: "credential-1",
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
    author: "AI Drama",
    version: "m6c-1",
    manifest: {},
    inputs: [],
    input_values: {},
    config_values: { base_url: "https://agnes.example.invalid" },
    capabilities: ["image", "video"],
    model_count: 2,
    base_url_summary: "https://agnes.example.invalid",
    credential: { configured: true, masked_suffix: "ABCD" },
  },
  {
    supplier_id: "custom-1",
    slug: "custom-local",
    display_name: "自有供应商",
    source: "custom",
    enabled: 0,
    revision: 1,
    config_revision: 1,
    credential_revision: 0,
    model_catalog_revision: 0,
    current_supplier_version_id: "",
    current_config_revision_id: "config-1",
    current_credential_version_id: "",
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
    author: "",
    version: "",
    manifest: {},
    inputs: [],
    input_values: {},
    config_values: {},
    capabilities: [],
    model_count: 0,
    base_url_summary: "",
    credential: { configured: false, masked_suffix: "" },
  },
];

describe("supplier list page", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    window.history.replaceState({}, "", "/suppliers");
  });

  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  test("renders supplier operations list with safe metadata", async () => {
    get.mockResolvedValue({ data: suppliers, headers: {} });

    render(<App />);

    expect(await screen.findByRole("heading", { name: "模型供应商" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Agnes/ })).toHaveAttribute(
      "href",
      "/suppliers/agnes-1",
    );
    expect(screen.getByText("图片 · 视频")).toBeInTheDocument();
    expect(screen.getByText("已配置 ····ABCD")).toBeInTheDocument();
    expect(screen.getByText("已停用")).toBeInTheDocument();
    expect(screen.getByText("2 个模型")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /复制供应商|供应商市场/ })).not.toBeInTheDocument();
  });

  test("creates a custom empty-template supplier", async () => {
    get.mockResolvedValue({ data: [], headers: {} });
    post.mockResolvedValue({ data: suppliers[1], headers: {} });
    render(<App />);

    await screen.findByText("尚未配置供应商");
    fireEvent.click(screen.getByRole("button", { name: "新增供应商" }));
    fireEvent.change(screen.getByLabelText("供应商名称"), {
      target: { value: "自有供应商" },
    });
    fireEvent.change(screen.getByLabelText("供应商标识"), {
      target: { value: "custom-local" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建空模板" }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0][0]).toBe("/suppliers");
    expect(post.mock.calls[0][1]).toEqual({
      slug: "custom-local",
      display_name: "自有供应商",
    });
  });

  test("renders the stable local-only guidance", async () => {
    get.mockRejectedValue({
      isAxiosError: true,
      response: { status: 403, data: { error_code: "LOCAL_MANAGEMENT_ONLY" } },
    });
    render(<App />);

    expect(
      await screen.findByText("此管理功能只能在运行 AI Drama 的本机访问。"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("请使用本地地址打开，不要通过公网资产域名、FRP 或反向代理访问。"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/关闭|绕过.*限制/)).not.toBeInTheDocument();
  });
});
