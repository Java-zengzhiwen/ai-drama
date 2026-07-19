import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { App } from "../../app/App";

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
const put = apiClient.put as unknown as Mock;
const remove = apiClient.delete as unknown as Mock;

const source = `export const vendor = {
  id: "local", version: "1", name: "Local", author: "AI Drama",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "local", inputs: [], inputValues: {}, models: []
};`;

const supplier = {
  supplier_id: "supplier-1",
  slug: "local",
  display_name: "Local Supplier",
  source: "built_in",
  enabled: 1,
  revision: 2,
  config_revision: 3,
  credential_revision: 1,
  model_catalog_revision: 0,
  current_supplier_version_id: "version-2",
  current_config_revision_id: "config-3",
  current_credential_version_id: "credential-1",
  created_at: "2026-07-13T00:00:00Z",
  updated_at: "2026-07-13T00:00:00Z",
  author: "AI Drama",
  version: "1.0.0",
  manifest: {},
  inputs: [
    { key: "base_url", label: "Base URL", type: "url", required: true },
    { key: "region", label: "区域", type: "text" },
  ],
  input_values: {},
  config_values: { base_url: "https://api.example.invalid/v1", region: "local" },
  capabilities: ["text"],
  model_count: 0,
  base_url_summary: "https://api.example.invalid/v1",
  credential: { configured: true, masked_suffix: "ABCD" },
  credential_active_job_count: 0,
};

function mockReads() {
  get.mockImplementation(async (url: string) => {
    if (url === "/suppliers") return { data: [supplier], headers: {} };
    if (url === "/suppliers/supplier-1") {
      return { data: supplier, headers: { etag: '"supplier-2"' } };
    }
    if (url === "/suppliers/supplier-1/code") {
      return { data: { source, supplier_version_id: "version-2" }, headers: {} };
    }
    if (url === "/suppliers/supplier-1/models") {
      return { data: [], headers: { etag: '"model-catalog-0"' } };
    }
    throw new Error(`unexpected GET ${url}`);
  });
}

describe("supplier detail page", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    put.mockReset();
    remove.mockReset();
    window.history.replaceState({}, "", "/suppliers/supplier-1");
    mockReads();
  });

  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  test("renders the approved supplier workbench hierarchy", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Local Supplier" })).toBeInTheDocument();
    expect(screen.getByText("AI Drama · 1.0.0")).toBeInTheDocument();
    expect(screen.getByText("ETag: supplier-2")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "概览" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "配置" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "密钥" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "适配代码" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "模型" })).toBeInTheDocument();
  });

  test("saves manifest-driven config with its independent ETag", async () => {
    put.mockResolvedValue({ data: { config_revision_id: "config-4", revision: 4 }, headers: { etag: '"config-4"' } });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "配置" }));

    fireEvent.change(screen.getByLabelText("Base URL"), {
      target: { value: "https://next.example.invalid/v1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() =>
      expect(put).toHaveBeenCalledWith(
        "/suppliers/supplier-1/config",
        { values: { base_url: "https://next.example.invalid/v1", region: "local" } },
        { headers: { "If-Match": '"config-3"' } },
      ),
    );
    expect(await screen.findByText("配置已保存为新版本。" )).toBeInTheDocument();
    await waitFor(() =>
      expect(get.mock.calls.filter(([url]) => url === "/suppliers/supplier-1")).toHaveLength(2),
    );
  });

  test("renders and saves a manifest-driven select instead of free text", async () => {
    const selectSupplier = {
      ...supplier,
      inputs: [
        ...supplier.inputs,
        {
          key: "reasoning_effort",
          label: "默认思考深度",
          type: "select",
          required: true,
          options: [
            { value: "low", label: "低" },
            { value: "medium", label: "中" },
            { value: "high", label: "高" },
          ],
        },
      ],
      config_values: { ...supplier.config_values, reasoning_effort: "medium" },
    };
    get.mockImplementation(async (url: string) => {
      if (url === "/suppliers") return { data: [selectSupplier], headers: {} };
      if (url === "/suppliers/supplier-1") {
        return { data: selectSupplier, headers: { etag: '"supplier-2"' } };
      }
      if (url === "/suppliers/supplier-1/models") {
        return { data: [], headers: { etag: '"model-catalog-0"' } };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    put.mockResolvedValue({ data: { config_revision_id: "config-4", revision: 4 }, headers: {} });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "配置" }));

    const effort = screen.getByRole("combobox", { name: "默认思考深度" });
    expect(effort).toHaveValue("medium");
    expect(screen.queryByRole("textbox", { name: "默认思考深度" })).not.toBeInTheDocument();
    fireEvent.change(effort, { target: { value: "high" } });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() => expect(put).toHaveBeenCalledWith(
      "/suppliers/supplier-1/config",
      {
        values: {
          base_url: "https://api.example.invalid/v1",
          region: "local",
          reasoning_effort: "high",
        },
      },
      { headers: { "If-Match": '"config-3"' } },
    ));
  });

  test("uses the refreshed config ETag for a consecutive save", async () => {
    let detailReads = 0;
    get.mockImplementation(async (url: string) => {
      if (url === "/suppliers") return { data: [supplier], headers: {} };
      if (url === "/suppliers/supplier-1") {
        detailReads += 1;
        const next = detailReads > 1
          ? { ...supplier, config_revision: 4, current_config_revision_id: "config-4" }
          : supplier;
        return { data: next, headers: { etag: '"supplier-2"' } };
      }
      if (url === "/suppliers/supplier-1/models") return { data: [], headers: { etag: '"model-catalog-0"' } };
      throw new Error(`unexpected GET ${url}`);
    });
    put.mockResolvedValue({ data: { config_revision_id: "config-next", revision: 4 }, headers: {} });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "配置" }));

    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));
    await waitFor(() => expect(screen.getAllByText("config-4").length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() => expect(put).toHaveBeenNthCalledWith(
      2,
      "/suppliers/supplier-1/config",
      { values: supplier.config_values },
      { headers: { "If-Match": '"config-4"' } },
    ));
  });

  test("rejects a non-HTTPS Base URL before mutation", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "配置" }));
    fireEvent.change(screen.getByLabelText("Base URL"), {
      target: { value: "http://remote.example.invalid/v1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(await screen.findByText("Base URL 必须使用 HTTPS。" )).toBeInTheDocument();
    expect(put).not.toHaveBeenCalled();
  });

  test("rejects Base URL userinfo before mutation", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "配置" }));
    fireEvent.change(screen.getByLabelText("Base URL"), {
      target: { value: "https://user:password@api.example.invalid/v1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(await screen.findByText("Base URL 不能包含用户名或密码。")).toBeInTheDocument();
    expect(put).not.toHaveBeenCalled();
  });

  test("keeps secret write-only and clears every browser-held input after save", async () => {
    const secret = "never-persist-this-secret-9876";
    put.mockResolvedValue({
      data: { configured: true, masked_suffix: "9876" },
      headers: { etag: '"credential-2"' },
    });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "密钥" }));

    expect(screen.getByText("已配置 ····ABCD")).toBeInTheDocument();
    const input = screen.getByLabelText("新的 API Key");
    fireEvent.change(input, { target: { value: secret } });
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "显示未保存的密钥" }));
    expect(input).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: "保存密钥" }));

    await waitFor(() => expect(input).toHaveValue(""));
    await waitFor(() =>
      expect(get.mock.calls.filter(([url]) => url === "/suppliers/supplier-1")).toHaveLength(2),
    );
    expect(screen.getByText("已配置 ····9876")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(secret);
    expect(put).toHaveBeenCalledWith(
      "/suppliers/supplier-1/secret",
      { credential: secret },
      { headers: { "If-Match": '"credential-1"' } },
    );
  });

  test("requires destructive confirmation before deleting a stored credential", async () => {
    remove.mockResolvedValue({
      data: { configured: false, masked_suffix: "" },
      headers: { etag: '"credential-2"' },
    });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "密钥" }));
    fireEvent.click(screen.getByRole("button", { name: "删除密钥" }));

    expect(screen.getByRole("dialog", { name: "确认删除密钥" })).toBeInTheDocument();
    expect(screen.getByText(/后续任务和重新运行将无法解析此密钥/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));
    await waitFor(() =>
      expect(remove).toHaveBeenCalledWith("/suppliers/supplier-1/secret", {
        headers: { "If-Match": '"credential-1"' },
        params: undefined,
      }),
    );
  });

  test("requires a second acknowledgement before force-deleting an active credential", async () => {
    get.mockImplementation(async (url: string) => {
      if (url === "/suppliers") return { data: [{ ...supplier, credential_active_job_count: 2 }], headers: {} };
      if (url === "/suppliers/supplier-1") return { data: { ...supplier, credential_active_job_count: 2 }, headers: { etag: '"supplier-2"' } };
      if (url === "/suppliers/supplier-1/models") return { data: [], headers: { etag: '"model-catalog-0"' } };
      throw new Error(`unexpected GET ${url}`);
    });
    remove.mockResolvedValue({ data: { configured: false, masked_suffix: "" }, headers: {} });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "密钥" }));
    fireEvent.click(screen.getByRole("button", { name: "删除密钥" }));

    expect(screen.getByText(/当前密钥仍被 2 个活动任务引用/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认删除" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /我已确认强制删除/ }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => expect(remove).toHaveBeenCalledWith(
      "/suppliers/supplier-1/secret",
      { headers: { "If-Match": '"credential-1"' }, params: { force: true } },
    ));
  });

  test("supports arrow-key navigation between tabs with roving focus", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    const modelsTab = screen.getByRole("tab", { name: "模型" });
    modelsTab.focus();
    fireEvent.keyDown(modelsTab, { key: "ArrowLeft" });

    const codeTab = screen.getByRole("tab", { name: "适配代码" });
    expect(codeTab).toHaveFocus();
    expect(codeTab).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("tabpanel")).toHaveAttribute("aria-labelledby", "supplier-tab-code");
  });

  test("lazy-loads TypeScript source and renders safe line-column diagnostics", async () => {
    put.mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          detail: {
            error_code: "TYPESCRIPT_COMPILE_FAILED",
            error_message: "Unexpected token",
            line: 3,
            column: 8,
          },
        },
      },
    });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    expect(get).not.toHaveBeenCalledWith("/suppliers/supplier-1/code");
    fireEvent.click(screen.getByRole("tab", { name: "适配代码" }));

    const editor = await screen.findByLabelText("TypeScript 供应商适配代码");
    expect(editor).toHaveValue(source);
    expect(screen.getByLabelText("代码行号")).toHaveTextContent("1");
    fireEvent.click(screen.getByRole("button", { name: "校验并保存" }));
    expect(await screen.findByText("第 3 行，第 8 列：Unexpected token")).toBeInTheDocument();
  });

  test("restores a built-in version using the supplier ETag", async () => {
    post.mockResolvedValue({ data: supplier, headers: { etag: '"supplier-3"' } });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "适配代码" }));
    await screen.findByLabelText("TypeScript 供应商适配代码");
    fireEvent.click(screen.getByRole("button", { name: "恢复内置版本" }));
    fireEvent.click(screen.getByRole("button", { name: "确认恢复" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        "/suppliers/supplier-1/restore-built-in",
        undefined,
        { headers: { "If-Match": '"supplier-2"' } },
      ),
    );
  });

  test("stale config save refuses overwrite and offers reload", async () => {
    put.mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: { detail: { error_code: "REVISION_CONFLICT" } } },
    });
    render(<App />);
    await screen.findByRole("heading", { name: "Local Supplier" });
    fireEvent.click(screen.getByRole("tab", { name: "配置" }));
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    expect(
      await screen.findByText("数据已在其他页面更新，请重新加载后再保存。"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新加载" })).toBeInTheDocument();
    expect(put).toHaveBeenCalledTimes(1);
  });
});
