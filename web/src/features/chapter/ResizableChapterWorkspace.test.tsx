import { fireEvent, render, screen } from "@testing-library/react";
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
  });

  afterEach(() => {
    vi.restoreAllMocks();
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
});
