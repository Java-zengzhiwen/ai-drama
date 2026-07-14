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

function renderDialog(open = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ModelTestDialog supplier={supplier} model={model} open={open} onClose={vi.fn()} />
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
      '"model-image-model-1-2"',
      "model-test-key-1",
    );
    expect(await screen.findByText("image/png")).toBeInTheDocument();
    expect(screen.getByText("1 KB")).toBeInTheDocument();
    expect(screen.getByText("800 ms")).toBeInTheDocument();
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
});
