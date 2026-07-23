import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ResizableChapterWorkspace } from "./ResizableChapterWorkspace";
import { WORKSPACE_RATIO_STORAGE_KEY } from "./workspaceLayout";

function renderWorkspace() {
  return render(
    <ResizableChapterWorkspace
      center={<div>中央剧本</div>}
      left={<div>章节列表</div>}
      leftDrawerTitle="章节导航"
      right={<div>生成状态</div>}
      rightDrawerTitle="剧本详情"
    />,
  );
}

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width, writable: true });
}

describe("ResizableChapterWorkspace", () => {
  beforeEach(() => {
    window.localStorage.clear();
    setViewportWidth(1920);
    vi.stubGlobal("PointerEvent", MouseEvent);
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      bottom: 600,
      height: 600,
      left: 0,
      right: 1000,
      top: 0,
      width: 1000,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test("starts at the approved wide ratios", () => {
    renderWorkspace();

    const workspace = screen.getByTestId("resizable-chapter-workspace");
    expect(workspace.style.getPropertyValue("--workspace-left")).toBe("11fr");
    expect(workspace.style.getPropertyValue("--workspace-center")).toBe("73fr");
    expect(workspace.style.getPropertyValue("--workspace-right")).toBe("16fr");
  });

  test("persists keyboard changes and resets on double click", () => {
    renderWorkspace();

    const divider = screen.getByRole("separator", { name: "调整章节导航宽度" });
    fireEvent.keyDown(divider, { key: "ArrowRight" });
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("12fr");
    expect(JSON.parse(window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY) ?? "{}")).toMatchObject({ left: 12 });

    fireEvent.doubleClick(divider);
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("11fr");
  });

  test("exposes bounded separators and supports the complete keyboard contract", () => {
    renderWorkspace();

    const leftDivider = screen.getByRole("separator", { name: "调整章节导航宽度" });
    const rightDivider = screen.getByRole("separator", { name: "调整详情栏宽度" });
    expect(leftDivider).toHaveAttribute("aria-orientation", "vertical");
    expect(leftDivider).toHaveAttribute("aria-valuemin", "8");
    expect(leftDivider).toHaveAttribute("aria-valuemax", "20");
    expect(rightDivider).toHaveAttribute("aria-valuemin", "12");
    expect(rightDivider).toHaveAttribute("aria-valuemax", "28");

    fireEvent.keyDown(leftDivider, { key: "ArrowRight", shiftKey: true });
    expect(JSON.parse(window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY) ?? "{}")).toMatchObject({ left: 16 });
    fireEvent.keyDown(rightDivider, { key: "ArrowLeft" });
    expect(JSON.parse(window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY) ?? "{}")).toMatchObject({ right: 17 });
    fireEvent.keyDown(leftDivider, { key: "Home" });
    expect(leftDivider).toHaveAttribute("aria-valuenow", "8");
    fireEvent.keyDown(rightDivider, { key: "End" });
    expect(rightDivider).toHaveAttribute("aria-valuenow", "28");
  });

  test("previews pointer dragging and persists the final ratio once", () => {
    const setItem = vi.spyOn(window.localStorage, "setItem");
    renderWorkspace();

    const divider = screen.getByRole("separator", { name: "调整章节导航宽度" });
    fireEvent.pointerDown(divider, { clientX: 110, pointerId: 1 });
    fireEvent.pointerMove(divider, { clientX: 160, pointerId: 1 });
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("16fr");
    expect(setItem).not.toHaveBeenCalled();
    fireEvent.pointerUp(divider, { clientX: 160, pointerId: 1 });

    expect(setItem).toHaveBeenCalledTimes(1);
    expect(JSON.parse(window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY) ?? "{}")).toMatchObject({ left: 16 });
  });

  test("restores one global preference", () => {
    window.localStorage.setItem(WORKSPACE_RATIO_STORAGE_KEY, JSON.stringify({ version: 1, left: 13, right: 18 }));
    renderWorkspace();

    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("13fr");
  });

  test("uses center-first drawers below 1024px", () => {
    setViewportWidth(768);
    renderWorkspace();

    expect(screen.getByText("中央剧本")).toBeVisible();
    expect(screen.getByRole("button", { name: "打开章节导航" })).toBeVisible();
    expect(screen.getByRole("button", { name: "打开剧本详情" })).toBeVisible();
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  test("keeps one compact drawer open and restores trigger focus after Escape", async () => {
    setViewportWidth(768);
    renderWorkspace();

    const leftTrigger = screen.getByRole("button", { name: "打开章节导航" });
    const rightTrigger = screen.getByRole("button", { name: "打开剧本详情" });
    fireEvent.click(leftTrigger);
    expect(await screen.findByRole("dialog", { name: "章节导航" })).toBeInTheDocument();

    fireEvent.click(rightTrigger);
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "章节导航" })).not.toBeInTheDocument();
      expect(screen.getByRole("dialog", { name: "剧本详情" })).toBeInTheDocument();
    });

    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "剧本详情" })).not.toBeInTheDocument());
    await waitFor(() => expect(rightTrigger).toHaveFocus());
  });

  test("preserves the wide preference across the compact breakpoint", () => {
    window.localStorage.setItem(
      WORKSPACE_RATIO_STORAGE_KEY,
      JSON.stringify({ version: 1, left: 13, right: 18 }),
    );
    renderWorkspace();

    setViewportWidth(768);
    fireEvent(window, new Event("resize"));
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
    expect(window.localStorage.getItem(WORKSPACE_RATIO_STORAGE_KEY)).toContain('"left":13');

    setViewportWidth(1920);
    fireEvent(window, new Event("resize"));
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-left")).toBe("13fr");
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-right")).toBe("18fr");
  });

  test("falls back to defaults when local storage cannot be read", () => {
    vi.spyOn(window.localStorage, "getItem").mockImplementation(() => {
      throw new Error("storage unavailable");
    });

    expect(() => renderWorkspace()).not.toThrow();
    expect(screen.getByTestId("resizable-chapter-workspace").style.getPropertyValue("--workspace-center")).toBe("73fr");
  });
});
