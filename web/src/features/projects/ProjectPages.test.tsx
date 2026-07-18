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
      if (url === "/projects/project-1/chapters") {
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
    expect(screen.queryByLabelText("项目名称")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新建项目" }));
    expect(screen.getByRole("dialog", { name: "新建项目" })).toBeInTheDocument();
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
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "新建项目" })).not.toBeInTheDocument());
    expect(await screen.findByText("尚未添加章节")).toBeInTheDocument();
  });

  test("focuses the newest project and filters the remaining production queue", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/projects") {
        return {
          data: [
            {
              project_id: "project-older",
              name: "M2 Verification",
              description: "古装重生短剧",
              series_canon: "",
              characters_context: "",
              production_brief: "",
              created_at: "2026-07-17T10:00:00Z",
              updated_at: "2026-07-17T10:00:00Z",
            },
            {
              project_id: "project-active",
              name: "生死",
              description: "古装重生短剧",
              series_canon: "",
              characters_context: "",
              production_brief: "",
              created_at: "2026-07-18T06:00:00Z",
              updated_at: "2026-07-18T06:32:00Z",
            },
          ],
        };
      }
      if (url === "/projects/project-active/chapters") {
        return {
          data: [
            {
              chapter_id: "chapter-active",
              project_id: "project-active",
              title: "第一章",
              position: 1,
              current_source_revision_id: "source-1",
              created_at: "2026-07-18T06:10:00Z",
              updated_at: "2026-07-18T06:32:00Z",
              source_text: "正文",
            },
          ],
        };
      }
      if (url === "/chapters/chapter-active/status") {
        return {
          data: {
            status: "script_draft",
            blocking_reason: "",
            next_action: "approve_script",
          },
        };
      }
      if (url === "/projects/project-older/chapters") {
        return {
          data: [
            {
              chapter_id: "chapter-older",
              project_id: "project-older",
              title: "第一章",
              position: 1,
              current_source_revision_id: "source-2",
              created_at: "2026-07-17T10:00:00Z",
              updated_at: "2026-07-17T10:00:00Z",
              source_text: "正文",
            },
          ],
        };
      }
      if (url === "/chapters/chapter-older/status") {
        return {
          data: {
            status: "missing_source",
            blocking_reason: "chapter source revision is required",
            next_action: "add_source",
          },
        };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    window.history.replaceState({}, "", "/projects");

    render(<App />);

    const focusRegion = await screen.findByRole("region", { name: "继续制作" });
    expect(focusRegion).toHaveTextContent("生死");
    expect(focusRegion).toHaveTextContent("剧本待确认");
    expect(screen.getByRole("link", { name: "继续剧本" })).toHaveAttribute(
      "href",
      "/projects/project-active/chapters/chapter-active",
    );
    expect(await screen.findByRole("link", { name: "M2 Verification" })).toBeInTheDocument();
    expect(screen.getByText("待添加原文")).toBeInTheDocument();
    expect(screen.queryByText("chapter source revision is required")).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "搜索项目" }), {
      target: { value: "不存在" },
    });
    expect(screen.queryByRole("link", { name: "M2 Verification" })).not.toBeInTheDocument();
    expect(screen.getByText("没有匹配的其他项目")).toBeInTheDocument();
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
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "生死" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "第一章" })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-1",
    );
    expect(await screen.findByText("source_empty")).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledWith("/projects/project-1/chapters");
  });

  test("refetches project chapters after creating a chapter", async () => {
    const chapter = {
      chapter_id: "chapter-1",
      project_id: "project-1",
      title: "第一章",
      position: 1,
      current_source_revision_id: "",
      created_at: "2026-07-05T10:05:00Z",
      updated_at: "2026-07-05T10:05:00Z",
      source_text: "",
    };
    let chapterListCalls = 0;
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
        chapterListCalls += 1;
        return { data: chapterListCalls === 1 ? [] : [chapter] };
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
    expect(await screen.findByText("暂无章节。添加章节后开始制作。")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("章节标题"), { target: { value: "第一章" } });
    fireEvent.change(screen.getByLabelText("章节序号"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "添加章节" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/projects/project-1/chapters", {
        title: "第一章",
        position: 1,
      }),
    );
    expect(await screen.findByRole("link", { name: "第一章" })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-1",
    );
    expect(await screen.findByText("source_empty")).toBeInTheDocument();
    expect(screen.getByText("add_source")).toBeInTheDocument();
    await waitFor(() => expect(chapterListCalls).toBeGreaterThanOrEqual(2));
  });

  test("shows persisted chapters after the project dashboard remounts", async () => {
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

    const firstRender = render(<App />);
    expect(await screen.findByRole("link", { name: "第一章" })).toBeInTheDocument();
    firstRender.unmount();

    render(<App />);

    expect(await screen.findByRole("heading", { name: "生死" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "第一章" })).toBeInTheDocument();
  });

  test("shows an error when project chapters fail to load", async () => {
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
        throw new Error("chapters unavailable");
      }
      throw new Error(`unexpected GET ${url}`);
    });
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    expect(await screen.findByText("章节列表加载失败。请重试。")).toBeInTheDocument();
  });

  test("shows the empty state when the project has no chapters", async () => {
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
        return { data: [] };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    expect(await screen.findByText("暂无章节。添加章节后开始制作。")).toBeInTheDocument();
  });

  test("shows chapter status and next action for created chapters", async () => {
    const chapter = {
      chapter_id: "chapter-1",
      project_id: "project-1",
      title: "第一章",
      position: 1,
      current_source_revision_id: "source-1",
      created_at: "2026-07-05T10:05:00Z",
      updated_at: "2026-07-05T10:05:00Z",
      source_text: "正文",
    };
    let chapterListCalls = 0;
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
        chapterListCalls += 1;
        return { data: chapterListCalls === 1 ? [] : [chapter] };
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
      data: chapter,
    });
    window.history.replaceState({}, "", "/projects/project-1");

    render(<App />);

    await screen.findByRole("heading", { name: "生死" });
    fireEvent.change(screen.getByLabelText("章节标题"), { target: { value: "第一章" } });
    fireEvent.click(screen.getByRole("button", { name: "添加章节" }));

    expect(await screen.findByText("source_ready")).toBeInTheDocument();
    expect(screen.getByText("generate_script")).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledWith("/chapters/chapter-1/status");
  });
});
