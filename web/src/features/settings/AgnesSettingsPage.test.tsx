import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { App } from "../../app/App";

vi.mock("../../api/client", () => ({
  apiClient: {
    delete: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

const mockedDelete = apiClient.delete as unknown as Mock;
const mockedGet = apiClient.get as unknown as Mock;
const mockedPut = apiClient.put as unknown as Mock;

describe("Agnes settings page", () => {
  beforeEach(() => {
    mockedDelete.mockReset();
    mockedGet.mockReset();
    mockedPut.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  test("shows configured status with only the masked suffix", async () => {
    mockedGet.mockResolvedValue({ data: { configured: true, masked_suffix: "1234" } });
    window.history.replaceState({}, "", "/settings/agnes");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Agnes 设置" })).toBeInTheDocument();
    expect(await screen.findByText("已配置")).toBeInTheDocument();
    expect(await screen.findByText("****1234")).toBeInTheDocument();
    expect(screen.queryByText("agnes-live-secret-1234")).not.toBeInTheDocument();
  });

  test("saves a password key without rendering or storing it", async () => {
    const rawKey = "agnes-live-secret-9876";
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
    mockedGet.mockResolvedValue({ data: { configured: false, masked_suffix: "" } });
    mockedPut.mockResolvedValue({ data: { configured: true, masked_suffix: "9876" } });
    window.history.replaceState({}, "", "/settings/agnes");

    render(<App />);

    fireEvent.change(await screen.findByLabelText("Agnes API Key"), {
      target: { value: rawKey },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/settings/agnes", { api_key: rawKey }),
    );
    expect(await screen.findByText("****9876")).toBeInTheDocument();
    expect(screen.queryByDisplayValue(rawKey)).not.toBeInTheDocument();
    expect(screen.queryByText(rawKey)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain(rawKey);
    expect(setItemSpy).not.toHaveBeenCalled();
  });

  test("deletes the configured key", async () => {
    mockedGet.mockResolvedValue({ data: { configured: true, masked_suffix: "2468" } });
    mockedDelete.mockResolvedValue({ data: { configured: false, masked_suffix: "" } });
    window.history.replaceState({}, "", "/settings/agnes");

    render(<App />);

    expect(await screen.findByText("****2468")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "移除" }));

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith("/settings/agnes"));
    expect(await screen.findByText("未配置")).toBeInTheDocument();
    expect(screen.queryByText("****2468")).not.toBeInTheDocument();
  });
});
