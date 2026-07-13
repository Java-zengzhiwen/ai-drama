import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { App } from "../../app/App";

vi.mock("../../api/client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const get = apiClient.get as unknown as Mock;
const put = apiClient.put as unknown as Mock;

const project = {
  project_id: "project-1",
  name: "模型路由项目",
  description: "",
  series_canon: "",
  characters_context: "",
  production_brief: "",
  created_at: "2026-07-13T00:00:00Z",
  updated_at: "2026-07-13T00:00:00Z",
};

const suppliers = [
  { supplier_id: "enabled-supplier", display_name: "Enabled", enabled: 1 },
  { supplier_id: "disabled-supplier", display_name: "Disabled", enabled: 0 },
];

const models = {
  "enabled-supplier": [
    { supplier_model_id: "text-default", supplier_id: "enabled-supplier", display_name: "Text Default", provider_model_name: "text-default-v1", capability: "text", enabled: 1, source: "overlay", revision: 1, model_revision_id: "tr1", current_model_revision_id: "tr1", definition: {}, binding_count: 0 },
    { supplier_model_id: "text-override", supplier_id: "enabled-supplier", display_name: "Text Override", provider_model_name: "text-override-v1", capability: "text", enabled: 1, source: "overlay", revision: 1, model_revision_id: "tr2", current_model_revision_id: "tr2", definition: {}, binding_count: 0 },
    { supplier_model_id: "image-default", supplier_id: "enabled-supplier", display_name: "Image Default", provider_model_name: "image-default-v1", capability: "image", enabled: 1, source: "overlay", revision: 1, model_revision_id: "ir1", current_model_revision_id: "ir1", definition: {}, binding_count: 0 },
    { supplier_model_id: "video-disabled", supplier_id: "enabled-supplier", display_name: "Video Disabled", provider_model_name: "video-disabled-v1", capability: "video", enabled: 0, source: "overlay", revision: 1, model_revision_id: "vr1", current_model_revision_id: "vr1", definition: {}, binding_count: 0 },
  ],
  "disabled-supplier": [
    { supplier_model_id: "video-hidden", supplier_id: "disabled-supplier", display_name: "Video Hidden", provider_model_name: "video-hidden-v1", capability: "video", enabled: 1, source: "overlay", revision: 1, model_revision_id: "vr2", current_model_revision_id: "vr2", definition: {}, binding_count: 0 },
  ],
};

const binding = {
  project_id: "project-1",
  defaults: { text: "text-default", image: "image-default", video: "" },
  operation_overrides: { storyboard_design: "text-override" },
  binding_set_revision: 3,
};

function mockReads() {
  get.mockImplementation(async (url: string) => {
    if (url === "/projects/project-1") return { data: project, headers: {} };
    if (url === "/suppliers") return { data: suppliers, headers: {} };
    if (url === "/suppliers/enabled-supplier/models") return { data: models["enabled-supplier"], headers: { etag: '"model-catalog-4"' } };
    if (url === "/suppliers/disabled-supplier/models") return { data: models["disabled-supplier"], headers: { etag: '"model-catalog-1"' } };
    if (url === "/projects/project-1/model-bindings") return { data: binding, headers: { etag: '"binding-set-3"' } };
    if (url === "/projects/project-1/model-resolution/script_adaptation") return { data: { operation_key: "script_adaptation", capability: "text", binding_source: "capability_default", supplier_model_id: "text-default", provider_model_name: "text-default-v1" }, headers: {} };
    if (url.startsWith("/projects/project-1/model-resolution/")) {
      throw { isAxiosError: true, response: { status: 409, data: { detail: { error_code: "MODEL_BINDING_MISSING" } } } };
    }
    throw new Error(`unexpected GET ${url}`);
  });
}

describe("project model bindings", () => {
  beforeEach(() => {
    get.mockReset();
    put.mockReset();
    window.history.replaceState({}, "", "/projects/project-1/model-bindings");
    mockReads();
  });

  afterEach(() => window.history.replaceState({}, "", "/"));

  test("filters default and operation options by enabled capability", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "项目模型配置" })).toBeInTheDocument();
    expect(screen.getByText("模型路由项目")).toBeInTheDocument();
    const textSelect = screen.getByLabelText("默认文本模型");
    expect(within(textSelect).getByRole("option", { name: "Enabled / Text Default" })).toBeInTheDocument();
    expect(within(textSelect).queryByRole("option", { name: /Image Default/ })).not.toBeInTheDocument();
    const videoSelect = screen.getByLabelText("默认视频模型");
    expect(within(videoSelect).queryByRole("option", { name: /Video Disabled|Video Hidden/ })).not.toBeInTheDocument();
    expect(screen.getByText("不自动回退：未配置时任务将明确阻塞。" )).toBeInTheDocument();
  });

  test("shows inherited and explicit operations and saves one complete binding set", async () => {
    put.mockResolvedValue({
      data: { ...binding, defaults: { ...binding.defaults, text: "text-override" }, binding_set_revision: 4 },
      headers: { etag: '"binding-set-4"' },
    });
    render(<App />);
    await screen.findByRole("heading", { name: "项目模型配置" });

    expect(screen.getByTestId("binding-source-storyboard_design")).toHaveTextContent("显式覆盖");
    expect(screen.getByTestId("binding-source-script_adaptation")).toHaveTextContent("继承默认");
    fireEvent.change(screen.getByLabelText("默认文本模型"), { target: { value: "text-override" } });
    fireEvent.change(screen.getByLabelText("剧本改编"), { target: { value: "text-default" } });
    fireEvent.click(screen.getByRole("button", { name: "保存全部模型配置" }));

    await waitFor(() => expect(put).toHaveBeenCalledTimes(1));
    expect(put).toHaveBeenCalledWith(
      "/projects/project-1/model-bindings",
      {
        defaults: { text: "text-override", image: "image-default", video: "" },
        operation_overrides: expect.objectContaining({
          storyboard_design: "text-override",
          script_adaptation: "text-default",
        }),
      },
      { headers: { "If-Match": '"binding-set-3"' } },
    );
  });

  test("renders backend resolution preview and stable missing-binding errors", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "项目模型配置" });
    fireEvent.click(screen.getByRole("button", { name: "刷新解析预览" }));

    expect(await screen.findByText("text-default-v1 · 继承默认" )).toBeInTheDocument();
    expect(await screen.findAllByText("尚未配置此步骤所需的模型。")).not.toHaveLength(0);
    expect(get).toHaveBeenCalledWith("/projects/project-1/model-resolution/script_adaptation");
  });

  test("stale binding set refuses overwrite and offers explicit reload", async () => {
    put.mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: { detail: { error_code: "REVISION_CONFLICT" } } },
    });
    render(<App />);
    await screen.findByRole("heading", { name: "项目模型配置" });
    fireEvent.click(screen.getByRole("button", { name: "保存全部模型配置" }));

    expect(await screen.findByText("数据已在其他页面更新，请重新加载后再保存。" )).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新加载绑定" })).toBeInTheDocument();
    expect(put).toHaveBeenCalledTimes(1);
  });
});
