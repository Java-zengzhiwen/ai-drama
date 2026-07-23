import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";
import type { ChapterRead } from "../projects/api";
import { ChapterNavigator } from "./ChapterNavigator";

const { listChapters } = vi.hoisted(() => ({ listChapters: vi.fn() }));

vi.mock("../projects/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../projects/api")>();
  return { ...actual, listChapters };
});

const currentChapter: ChapterRead = {
  chapter_id: "chapter-1",
  created_at: "2026-07-20T00:00:00Z",
  current_source_revision_id: "source-1",
  position: 1,
  project_id: "project-1",
  title: "第一章",
  updated_at: "2026-07-20T00:00:00Z",
};

function renderNavigator() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChapterNavigator chapter={currentChapter} currentStateLabel="正在生成" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderEmptyNavigator() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const emptyChapter = { ...currentChapter, current_source_revision_id: "" };
  listChapters.mockResolvedValue([emptyChapter]);
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChapterNavigator chapter={emptyChapter} currentStateLabel="原文已确认" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChapterNavigator", () => {
  beforeEach(() => {
    listChapters.mockResolvedValue([
      currentChapter,
      {
        ...currentChapter,
        chapter_id: "chapter-2",
        current_source_revision_id: "source-2",
        position: 2,
        title: "第二章",
      },
    ]);
  });

  test("filters chapters and preserves project routes", async () => {
    renderNavigator();

    expect(screen.getByRole("navigation", { name: "章节导航" })).toBeVisible();
    expect(await screen.findByRole("link", { name: /第二章/ })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-2",
    );

    fireEvent.change(screen.getByRole("textbox", { name: "搜索章节标题" }), { target: { value: "第二" } });
    expect(screen.queryByRole("link", { name: /第一章/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /第二章/ })).toBeVisible();
  });

  test("uses the supplied current-state label", async () => {
    renderNavigator();

    expect(await screen.findByText("正在生成")).toBeVisible();
    expect(screen.getByRole("link", { name: /第一章/ })).toHaveAttribute("aria-current", "page");
  });

  test("does not label an empty current chapter as source confirmed", async () => {
    renderEmptyNavigator();

    expect(await screen.findByText("未开始")).toBeVisible();
    expect(screen.queryByText("原文已确认")).not.toBeInTheDocument();
  });
});
