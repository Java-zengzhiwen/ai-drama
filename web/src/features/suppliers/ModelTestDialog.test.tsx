import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { SupplierModelRead, SupplierRead } from "./api";
import { ModelTestDialog } from "./ModelTestDialog";

const api = vi.hoisted(() => ({
  createModelTest: vi.fn(),
  getModelTest: vi.fn(),
  getModelTestContent: vi.fn(),
  recoverModelTest: vi.fn(),
  newIdempotencyKey: vi.fn(() => "model-test-key-1"),
}));

vi.mock("./api", async (loadOriginal) => ({
  ...(await loadOriginal<typeof import("./api")>()),
  ...api,
}));

const supplier = { supplier_id: "supplier-1", display_name: "Agnes" } as SupplierRead;
const model = {
  supplier_model_id: "image-model-1",
  display_name: "Agnes Image",
  provider_model_name: "agnes-image-2.1-flash",
  capability: "image",
  entity_revision: 2,
  enabled: 1,
} as SupplierModelRead;

function renderDialog(
  open = true,
  currentSupplier: SupplierRead = supplier,
  currentModel: SupplierModelRead = model,
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ModelTestDialog supplier={currentSupplier} model={currentModel} open={open} onClose={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("model test dialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  test("warns before a real request and cancel performs no call", () => {
    renderDialog();

    expect(screen.getByRole("dialog", { name: "测试模型连接" })).toBeInTheDocument();
    expect(screen.getByText("将向真实供应商提交 1 次生成请求，可能产生费用。")).toBeInTheDocument();
    expect(screen.getByText("Agnes Image")).toBeInTheDocument();
    expect(screen.getByText("agnes-image-2.1-flash")).toBeInTheDocument();
    expect(screen.getByLabelText("测试提示词")).toHaveValue("一只白色陶瓷杯放在木桌上，柔和自然光，简洁写实，无文字");
    fireEvent.click(screen.getByRole("button", { name: /取\s*消/ }));

    expect(api.createModelTest).not.toHaveBeenCalled();
  });

  test("double confirmation creates one run and renders image metadata", async () => {
    api.createModelTest.mockResolvedValue({
      test_run_id: "run-1",
      supplier_model_id: model.supplier_model_id,
      capability: "image",
      status: "completed",
      media_type: "image/png",
      byte_size: 1024,
      elapsed_ms: 800,
      created_at: "2026-07-14T00:00:00Z",
    });
    api.getModelTestContent.mockResolvedValue(new Blob(["png"], { type: "image/png" }));
    renderDialog();
    const confirm = screen.getByRole("button", { name: "确认并测试" });

    fireEvent.click(confirm);
    fireEvent.click(confirm);

    await waitFor(() => expect(api.createModelTest).toHaveBeenCalledTimes(1));
    expect(api.createModelTest).toHaveBeenCalledWith(
      model.supplier_model_id,
      "一只白色陶瓷杯放在木桌上，柔和自然光，简洁写实，无文字",
      {},
      '"model-image-model-1-2"',
      "model-test-key-1",
    );
    expect(await screen.findByText("image/png")).toBeInTheDocument();
    expect(screen.getByText("1 KB")).toBeInTheDocument();
    expect(screen.getByText("800 ms")).toBeInTheDocument();
  });

  test("submits and displays a text reasoning override", async () => {
    const textSupplier = { ...supplier, slug: "aixora", display_name: "AIXORA" } as SupplierRead;
    const textModel = {
      ...model,
      supplier_model_id: "text-model-1",
      display_name: "GPT-5.6",
      provider_model_name: "gpt-5.6",
      capability: "text",
      definition: {
        constraints: {
          reasoning_effort: "medium",
          supported_reasoning_efforts: ["none", "low", "medium", "high", "xhigh", "max"],
        },
      },
    } as SupplierModelRead;
    api.createModelTest.mockResolvedValue({
      test_run_id: "run-text-1",
      supplier_model_id: textModel.supplier_model_id,
      capability: "text",
      status: "completed",
      output: "连接测试成功",
      reasoning_effort: "max",
      elapsed_ms: 420,
      created_at: "2026-07-17T00:00:00Z",
    });

    renderDialog(true, textSupplier, textModel);
    expect(screen.getByLabelText("本次思考深度")).toHaveValue("");
    expect(screen.getByRole("option", { name: "最大" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("本次思考深度"), { target: { value: "max" } });
    fireEvent.click(screen.getByRole("button", { name: "确认并测试" }));

    await waitFor(() => expect(api.createModelTest).toHaveBeenCalledWith(
      textModel.supplier_model_id,
      "请只回复：连接测试成功",
      { reasoning_effort: "max" },
      '"model-text-model-1-2"',
      "model-test-key-1",
    ));
    expect(await screen.findByText("实际思考深度：最大")).toBeInTheDocument();
  });

  test("limits GPT-5.5 reasoning options to its declared model capability", () => {
    const textModel = {
      ...model,
      supplier_model_id: "text-model-55",
      display_name: "GPT-5.5",
      provider_model_name: "gpt-5.5",
      capability: "text",
      definition: {
        constraints: {
          reasoning_effort: "medium",
          supported_reasoning_efforts: ["none", "low", "medium", "high", "xhigh"],
        },
      },
    } as SupplierModelRead;

    renderDialog(true, supplier, textModel);

    expect(screen.getByRole("option", { name: "超高" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "最大" })).not.toBeInTheDocument();
  });

  test("submits and restores declared GPT Image 2 size and quality overrides", async () => {
    const imageSupplier = {
      ...supplier,
      config_values: { image_size: "1024x1024", image_quality: "auto" },
    } as SupplierRead;
    const imageModel = {
      ...model,
      supplier_model_id: "gpt-image-model-2",
      display_name: "GPT Image 2",
      provider_model_name: "gpt-image-2",
      definition: {
        default_size: "1024x1024",
        constraints: {
          supported_sizes: ["auto", "1024x1024", "1024x1536", "1536x1024"],
          default_quality: "auto",
          supported_qualities: ["auto", "low", "medium", "high"],
        },
      },
    } as SupplierModelRead;
    api.createModelTest.mockResolvedValue({
      test_run_id: "run-image-2",
      supplier_model_id: imageModel.supplier_model_id,
      capability: "image",
      status: "completed",
      size: "1024x1536",
      quality: "high",
      media_type: "image/png",
      byte_size: 2048,
      elapsed_ms: 900,
      created_at: "2026-07-19T00:00:00Z",
    });
    api.getModelTestContent.mockResolvedValue(new Blob(["png"], { type: "image/png" }));

    renderDialog(true, imageSupplier, imageModel);
    expect(screen.getByLabelText("本次图片尺寸")).toHaveValue("");
    expect(screen.getByLabelText("本次图片质量")).toHaveValue("");
    expect(screen.queryByRole("option", { name: /2K/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /4K/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("本次图片尺寸"), { target: { value: "1024x1536" } });
    fireEvent.change(screen.getByLabelText("本次图片质量"), { target: { value: "high" } });
    fireEvent.click(screen.getByRole("button", { name: "确认并测试" }));

    await waitFor(() => expect(api.createModelTest).toHaveBeenCalledWith(
      imageModel.supplier_model_id,
      "一只白色陶瓷杯放在木桌上，柔和自然光，简洁写实，无文字",
      { size: "1024x1536", quality: "high" },
      '"model-gpt-image-model-2-2"',
      "model-test-key-1",
    ));
    expect(await screen.findByText("实际尺寸：1024 × 1536")).toBeInTheDocument();
    expect(screen.getByText("实际质量：高")).toBeInTheDocument();
  });

  test("restores and locks the reasoning override with the idempotent request", async () => {
    const textModel = {
      ...model,
      supplier_model_id: "text-model-recovery",
      capability: "text",
      definition: { constraints: { reasoning_effort: "medium" } },
    } as SupplierModelRead;
    sessionStorage.setItem(
      `ai-drama:model-test:${textModel.supplier_model_id}`,
      JSON.stringify({
        idempotencyKey: "stored-text-key",
        testRunId: "run-text-stored",
        reasoningEffort: "high",
      }),
    );
    api.getModelTest.mockResolvedValue({
      test_run_id: "run-text-stored",
      supplier_model_id: textModel.supplier_model_id,
      capability: "text",
      status: "queued",
      reasoning_effort: "high",
      created_at: "2026-07-17T00:00:00Z",
    });

    renderDialog(true, supplier, textModel);

    const select = await screen.findByLabelText("本次思考深度");
    expect(select).toHaveValue("high");
    expect(select).toBeDisabled();
    expect(api.createModelTest).not.toHaveBeenCalled();
  });

  test("resumes a queued run from session storage and polls to completion", async () => {
    sessionStorage.setItem(
      `ai-drama:model-test:${model.supplier_model_id}`,
      JSON.stringify({ idempotencyKey: "stored-key", testRunId: "run-stored" }),
    );
    api.getModelTest
      .mockResolvedValueOnce({
        test_run_id: "run-stored",
        supplier_model_id: model.supplier_model_id,
        capability: "image",
        status: "queued",
        created_at: "2026-07-14T00:00:00Z",
      })
      .mockResolvedValueOnce({
        test_run_id: "run-stored",
        supplier_model_id: model.supplier_model_id,
        capability: "image",
        status: "completed",
        media_type: "image/png",
        byte_size: 512,
        elapsed_ms: 750,
        created_at: "2026-07-14T00:00:00Z",
      });
    api.getModelTestContent.mockResolvedValue(new Blob(["png"], { type: "image/png" }));

    renderDialog();

    expect(await screen.findByText(/测试编号 run-stored/)).toBeInTheDocument();
    expect(await screen.findByText("image/png", {}, { timeout: 2_000 })).toBeInTheDocument();
    expect(api.createModelTest).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(`ai-drama:model-test:${model.supplier_model_id}`)).toBeNull();
  });

  test("continues polling after one transient local status failure", async () => {
    sessionStorage.setItem(
      `ai-drama:model-test:${model.supplier_model_id}`,
      JSON.stringify({ idempotencyKey: "stored-key", testRunId: "run-transient" }),
    );
    api.getModelTest
      .mockResolvedValueOnce({
        test_run_id: "run-transient",
        supplier_model_id: model.supplier_model_id,
        capability: "image",
        status: "queued",
        created_at: "2026-07-14T00:00:00Z",
      })
      .mockRejectedValueOnce(new Error("local connection reset"))
      .mockResolvedValueOnce({
        test_run_id: "run-transient",
        supplier_model_id: model.supplier_model_id,
        capability: "image",
        status: "completed",
        media_type: "image/png",
        byte_size: 128,
        elapsed_ms: 900,
        created_at: "2026-07-14T00:00:00Z",
      });
    api.getModelTestContent.mockResolvedValue(new Blob(["png"], { type: "image/png" }));

    renderDialog();

    expect(await screen.findByText("image/png", {}, { timeout: 3_000 })).toBeInTheDocument();
    expect(api.getModelTest).toHaveBeenCalledTimes(3);
  });

  test("locks confirmation before a persisted run recovery resolves", async () => {
    sessionStorage.setItem(
      `ai-drama:model-test:${model.supplier_model_id}`,
      JSON.stringify({ idempotencyKey: "stored-key", testRunId: "run-pending" }),
    );
    let resolveRecovery!: (value: unknown) => void;
    api.getModelTest.mockReturnValue(new Promise((resolve) => { resolveRecovery = resolve; }));

    renderDialog();

    const confirm = screen.getByRole("button", { name: "确认并测试" });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(api.createModelTest).not.toHaveBeenCalled();
    resolveRecovery({
      test_run_id: "run-pending",
      supplier_model_id: model.supplier_model_id,
      capability: "image",
      status: "queued",
      created_at: "2026-07-14T00:00:00Z",
    });
    expect(await screen.findByText(/测试编号 run-pending/)).toBeInTheDocument();
  });

  test("keeps the stored key and retries after a transient recovery failure", async () => {
    sessionStorage.setItem(
      `ai-drama:model-test:${model.supplier_model_id}`,
      JSON.stringify({ idempotencyKey: "stored-key", testRunId: "run-retry" }),
    );
    api.getModelTest
      .mockRejectedValueOnce(new Error("temporary local failure"))
      .mockResolvedValueOnce({
        test_run_id: "run-retry",
        supplier_model_id: model.supplier_model_id,
        capability: "image",
        status: "completed",
        media_type: "image/png",
        byte_size: 64,
        elapsed_ms: 400,
        created_at: "2026-07-14T00:00:00Z",
      });
    api.getModelTestContent.mockResolvedValue(new Blob(["png"], { type: "image/png" }));

    renderDialog();

    expect(await screen.findByText("image/png", {}, { timeout: 2_000 })).toBeInTheDocument();
    expect(api.getModelTest).toHaveBeenCalledTimes(2);
    expect(api.createModelTest).not.toHaveBeenCalled();
  });

  test("renders a stable failed state without retrying", async () => {
    api.createModelTest.mockResolvedValue({
      test_run_id: "run-failed",
      supplier_model_id: model.supplier_model_id,
      capability: "image",
      status: "failed",
      error_code: "PROVIDER_HTTP_ERROR",
      error_message: "供应商请求失败。",
      created_at: "2026-07-14T00:00:00Z",
    });
    renderDialog();

    fireEvent.click(screen.getByRole("button", { name: "确认并测试" }));

    expect(await screen.findByText("供应商请求失败。")).toBeInTheDocument();
    expect(screen.getByText("PROVIDER_HTTP_ERROR")).toBeInTheDocument();
    expect(api.createModelTest).toHaveBeenCalledTimes(1);
    expect(api.getModelTest).not.toHaveBeenCalled();
  });

  test("recovers a lost create response with the original idempotency key", async () => {
    api.createModelTest.mockRejectedValue(new Error("response lost"));
    api.recoverModelTest.mockResolvedValue({
      test_run_id: "run-recovered",
      supplier_model_id: model.supplier_model_id,
      capability: "image",
      status: "completed",
      media_type: "image/png",
      byte_size: 256,
      elapsed_ms: 500,
      created_at: "2026-07-14T00:00:00Z",
    });
    api.getModelTestContent.mockResolvedValue(new Blob(["png"], { type: "image/png" }));
    renderDialog();

    fireEvent.click(screen.getByRole("button", { name: "确认并测试" }));

    expect(await screen.findByText("image/png")).toBeInTheDocument();
    expect(api.createModelTest).toHaveBeenCalledTimes(1);
    expect(api.recoverModelTest).toHaveBeenCalledWith(model.supplier_model_id, "model-test-key-1");
    expect(sessionStorage.getItem(`ai-drama:model-test:${model.supplier_model_id}`)).toBeNull();
  });

  test("keeps submission locked when create and recovery outcomes are both unknown", async () => {
    api.createModelTest.mockRejectedValue(new Error("response lost"));
    api.recoverModelTest.mockRejectedValue(new Error("connection unavailable"));
    renderDialog();

    const confirm = screen.getByRole("button", { name: "确认并测试" });
    fireEvent.click(confirm);

    expect(await screen.findByText(/提交结果尚未确认/)).toBeInTheDocument();
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(api.createModelTest).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem(`ai-drama:model-test:${model.supplier_model_id}`)).toContain("model-test-key-1");
  });

  test("treats an immediate recovery 404 as uncertain and preserves the original key", async () => {
    api.createModelTest.mockRejectedValue(new Error("response lost"));
    api.recoverModelTest.mockRejectedValue({
      isAxiosError: true,
      response: { status: 404, data: { detail: { error_code: "MODEL_TEST_NOT_FOUND" } } },
    });
    renderDialog();

    const confirm = screen.getByRole("button", { name: "确认并测试" });
    fireEvent.click(confirm);

    expect(await screen.findByText(/提交结果尚未确认/)).toBeInTheDocument();
    expect(confirm).toBeDisabled();
    expect(sessionStorage.getItem(`ai-drama:model-test:${model.supplier_model_id}`)).toContain("model-test-key-1");
    expect(api.createModelTest).toHaveBeenCalledTimes(1);
  });

  test("shows a deterministic preflight error and unlocks without recovery", async () => {
    api.createModelTest.mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 409,
        data: {
          detail: {
            error_code: "CREDENTIAL_MISSING",
            error_message: "请先配置供应商密钥。",
          },
        },
      },
    });
    renderDialog();

    const confirm = screen.getByRole("button", { name: "确认并测试" });
    fireEvent.click(confirm);

    expect(await screen.findByText("请先配置供应商密钥。")).toBeInTheDocument();
    expect(confirm).toBeEnabled();
    expect(api.recoverModelTest).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(`ai-drama:model-test:${model.supplier_model_id}`)).toBeNull();
  });
});
