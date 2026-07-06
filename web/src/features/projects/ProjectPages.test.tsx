import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { App } from "../../app/App";
import type { ChapterCreate, ProjectCreate } from "./api";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = apiClient.get as unknown as Mock;
const mockedPost = apiClient.post as unknown as Mock;

describe("project pages", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
  });

  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  test("loads projects and creates a project", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/projects") {
        return { data: [] };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    mockedPost.mockImplementation(async (url: string, payload: ProjectCreate) => {
      if (url === "/projects") {
        return {
          data: {
            project_id: "project-1",
            name: payload.name,
            description: payload.description,
            series_canon: payload.series_canon,
            characters_context: payload.characters_context,
            production_brief: payload.production_brief,
            created_at: "2026-07-05T10:00:00Z",
            updated_at: "2026-07-05T10:00:00Z",
          },
        };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    window.history.replaceState({}, "", "/projects");

    render(<App />);

    await screen.findByText("暂无项目。创建项目后开始章节制作。");
    fireEvent.change(screen.getByLabelText("项目名称"), { target: { value: "生死" } });
    fireEvent.change(screen.getByLabelText("项目描述"), { target: { value: "古装重生短剧" } });
    fireEvent.change(screen.getByLabelText("系列设定"), { target: { value: "明代商贾世界" } });
    fireEvent.change(screen.getByLabelText("人物上下文"), { target: { value: "沈清荷、沈清莲" } });
    fireEvent.change(screen.getByLabelText("制作简述"), {
      target: { value: "真人写实，16:9，低饱和" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建项目" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/projects", {
        name: "生死",
        description: "古装重生短剧",
        series_canon: "明代商贾世界",
        characters_context: "沈清荷、沈清莲",
        production_brief: "真人写实，16:9，低饱和",
      }),
    );
    expect(await screen.findByRole("link", { name: "生死" })).toHaveAttribute(
      "href",
      "/projects/project-1",
    );
    expect(screen.getByText("未加载")).toBeInTheDocument();
    expect(screen.queryByText("待添加章节")).not.toBeInTheDocument();
  });

  test("loads a project dashboard with persisted chapters from the API", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/projects/project-1") {
        return {
          data: {
            project_id: "project-1",
            name: "生死",
            description: "古装重生短剧",
            series_canon: "明代商贾世界",
            characters_context: "沈清荷、沈清莲",
            production_brief: "真人写实，16:9",
            created_at: "2026-07-05T10:00:00Z",
            updated_at: "2026-07-05T10:00:00Z",
          },
        };
      }
      if (url === "/projects/project-1/chapters") {
        return {
          data: [
            {
              chapter_id: "chapter-1",
              project_id: "project-1",
              title: "第一章",
              position: 1,
              current_source_revision_id: "",
              created_at: "2026-07-05T10:05:00Z",
              updated_at: "2026-07-05T10:05:00Z",
              source_text: "",
            },
          ],
        };
      }
      if (url === "/chapters/chapter-1/status") {
        return {
          data: {
            status: "source_empty",
            blocking_reason: "暂无小说原文",
            next_action: "add_source",
          },
        };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    mockedPost.mockImplementation(async (url: string, payload: ChapterCreate) => {
      if (url === "/projects/project-1/chapters") {
        return {
          data: {
            chapter_id: "chapter-1",
            project_id: "project-1",
            title: payload.title,
            position: payload.position,
            current_source_revision_id: "",
            created_at: "2026-07-05T10:05:00Z",
            updated_at: "2026-07-05T10:05:00Z",
            source_text: "",
          },
        };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "生死" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "第一章" })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-1",
    );
    expect(screen.queryByText("当前后端暂无章节列表接口，本页仅显示本次会话新建的章节。")).not.toBeInTheDocument();
  });

  test("refetches persisted chapters after creating a chapter", async () => {
    let chapters = [
      {
        chapter_id: "chapter-1",
        project_id: "project-1",
        title: "第一章",
        position: 1,
        current_source_revision_id: "",
        created_at: "2026-07-05T10:05:00Z",
        updated_at: "2026-07-05T10:05:00Z",
        source_text: "",
      },
    ];
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/projects/project-1") {
        return {
          data: {
            project_id: "project-1",
            name: "生死",
            description: "古装重生短剧",
            series_canon: "明代商贾世界",
            characters_context: "沈清荷、沈清莲",
            production_brief: "真人写实，16:9",
            created_at: "2026-07-05T10:00:00Z",
            updated_at: "2026-07-05T10:00:00Z",
          },
        };
      }
      if (url === "/projects/project-1/chapters") {
        return { data: chapters };
      }
      if (url === "/chapters/chapter-1/status" || url === "/chapters/chapter-2/status") {
        return {
          data: {
            status: "source_empty",
            blocking_reason: "暂无小说原文",
            next_action: "add_source",
          },
        };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    mockedPost.mockImplementation(async (url: string, payload: ChapterCreate) => {
      if (url === "/projects/project-1/chapters") {
        const chapter = {
          chapter_id: "chapter-2",
          project_id: "project-1",
          title: payload.title,
          position: payload.position,
          current_source_revision_id: "",
          created_at: "2026-07-05T10:10:00Z",
          updated_at: "2026-07-05T10:10:00Z",
          source_text: "",
        };
        chapters = [...chapters, chapter];
        return { data: chapter };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    expect(await screen.findByRole("link", { name: "第一章" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("章节标题"), { target: { value: "第一章" } });
    fireEvent.change(screen.getByLabelText("章节标题"), { target: { value: "第二章" } });
    fireEvent.change(screen.getByLabelText("章节序号"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "添加章节" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/projects/project-1/chapters", {
        title: "第二章",
        position: 2,
      }),
    );
    expect(await screen.findByRole("link", { name: "第二章" })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-2",
    );
    expect(mockedGet).toHaveBeenCalledWith("/projects/project-1/chapters");
  });

  test("shows persisted chapters after remounting the project dashboard", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/projects/project-1") {
        return {
          data: {
            project_id: "project-1",
            name: "生死",
            description: "古装重生短剧",
            series_canon: "明代商贾世界",
            characters_context: "",
            production_brief: "",
            created_at: "2026-07-05T10:00:00Z",
            updated_at: "2026-07-05T10:00:00Z",
          },
        };
      }
      if (url === "/projects/project-1/chapters") {
        return {
          data: [
            {
              chapter_id: "chapter-1",
              project_id: "project-1",
              title: "第一章",
              position: 1,
              current_source_revision_id: "",
              created_at: "2026-07-05T10:05:00Z",
              updated_at: "2026-07-05T10:05:00Z",
              source_text: "",
            },
          ],
        };
      }
      if (url === "/chapters/chapter-1/status") {
        return {
          data: {
            status: "source_empty",
            blocking_reason: "暂无小说原文",
            next_action: "add_source",
          },
        };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    window.history.replaceState({}, "", "/projects/project-1");

    const { unmount } = render(<App />);

    expect(await screen.findByRole("heading", { name: "生死" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "第一章" })).toBeInTheDocument();
    unmount();
    mockedGet.mockClear();

    render(<App />);

    expect(await screen.findByRole("link", { name: "第一章" })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-1",
    );
    expect(mockedGet).toHaveBeenCalledWith("/projects/project-1/chapters");
  });

  test("shows chapter status and next action for created chapters", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/projects/project-1") {
        return {
          data: {
            project_id: "project-1",
            name: "生死",
            description: "",
            series_canon: "",
            characters_context: "",
            production_brief: "",
            created_at: "2026-07-05T10:00:00Z",
            updated_at: "2026-07-05T10:00:00Z",
          },
        };
      }
      if (url === "/projects/project-1/chapters") {
        return {
          data: [
            {
              chapter_id: "chapter-1",
              project_id: "project-1",
              title: "第一章",
              position: 1,
              current_source_revision_id: "source-1",
              created_at: "2026-07-05T10:05:00Z",
              updated_at: "2026-07-05T10:05:00Z",
              source_text: "正文",
            },
          ],
        };
      }
      if (url === "/chapters/chapter-1/status") {
        return {
          data: {
            status: "source_ready",
            blocking_reason: "",
            next_action: "generate_script",
          },
        };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    mockedPost.mockResolvedValue({
      data: {
        chapter_id: "chapter-1",
        project_id: "project-1",
        title: "第一章",
        position: 1,
        current_source_revision_id: "source-1",
        created_at: "2026-07-05T10:05:00Z",
        updated_at: "2026-07-05T10:05:00Z",
        source_text: "正文",
      },
    });
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    await screen.findByRole("heading", { name: "生死" });

    expect(await screen.findByText("source_ready")).toBeInTheDocument();
    expect(screen.getByText("generate_script")).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledWith("/chapters/chapter-1/status");
  });
});
