import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { App } from "../../app/App";
import { ChapterWorkspace } from "../chapter/ChapterWorkspace";
import type { ChapterRead } from "../projects/api";
import { ScriptTab } from "./ScriptTab";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

const mockedGet = apiClient.get as unknown as Mock;
const mockedPost = apiClient.post as unknown as Mock;
const mockedPut = apiClient.put as unknown as Mock;

type SourceRevisionRead = {
  source_revision_id: string;
  chapter_id: string;
  number: number;
  object_id: string;
  content_hash: string;
  created_at: string;
};

type ScriptRevisionRead = {
  revision_id: string;
  artifact_id: string;
  chapter_id: string;
  number: number;
  approval_status: string;
  current: boolean;
  content: string;
  validation_results: Array<{
    validation_id: string;
    validator_id: string;
    status: string;
    required: boolean;
    error_code: string;
  }>;
};

const baseChapter: ChapterRead = {
  chapter_id: "chapter-1",
  project_id: "project-1",
  title: "第一章",
  position: 1,
  current_source_revision_id: "",
  created_at: "2026-07-05T10:00:00Z",
  updated_at: "2026-07-05T10:00:00Z",
  source_text: "",
};

const generatedScript: ScriptRevisionRead = {
  revision_id: "script-1",
  artifact_id: "chapter-1:script",
  chapter_id: "chapter-1",
  number: 1,
  approval_status: "pending",
  current: false,
  content: "# 第一场\n沈清荷推门入内。",
  validation_results: [
    {
      validation_id: "validation-1",
      validator_id: "script_markdown_contract",
      status: "PASS",
      required: true,
      error_code: "",
    },
  ],
};

const editedScript: ScriptRevisionRead = {
  ...generatedScript,
  revision_id: "script-2",
  number: 2,
  content: "# 第一场\n沈清荷推门入内，压低声音。",
};

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
  return queryClient;
}

function sourceReadyChapter(): ChapterRead {
  return {
    ...baseChapter,
    current_source_revision_id: "source-1",
    source_text: "第一章正文。沈清荷醒来。",
  };
}

function setupWorkspaceMocks() {
  let chapter: ChapterRead = { ...baseChapter };
  let revisions: ScriptRevisionRead[] = [];
  let bindingRevision = 1;
  let bindings = {
    defaults: { text: "model-sol", image: "", video: "" },
    operation_overrides: { script_adaptation: "model-sol" } as Record<string, string>,
  };

  mockedGet.mockImplementation(async (url: string) => {
    if (url === "/projects/project-1/chapters") {
      return {
        data: [
          chapter,
          {
            ...baseChapter,
            chapter_id: "chapter-2",
            title: "第二章",
            position: 2,
            current_source_revision_id: "source-2",
            source_text: "第二章正文。",
          },
        ],
      };
    }
    if (url === "/projects/project-1/model-resolution/script_adaptation") {
      return {
        data: {
          project_id: "project-1",
          operation_key: "script_adaptation",
          capability: "text",
          binding_source: "operation_override",
          supplier_id: "supplier-aixora",
          supplier_model_id: "model-sol",
          model_revision_id: "model-sol-r1",
          provider_model_name: "gpt-5.6-sol",
        },
      };
    }
    if (url === "/projects/project-1/model-bindings") {
      return {
        data: {
          project_id: "project-1",
          ...bindings,
          binding_set_revision: bindingRevision,
        },
        headers: { etag: `\"binding-set-${bindingRevision}\"` },
      };
    }
    if (url === "/suppliers") {
      return {
        data: [
          {
            supplier_id: "supplier-aixora",
            display_name: "aixora",
            enabled: 1,
          },
        ],
      };
    }
    if (url === "/suppliers/supplier-aixora/models") {
      return {
        data: [
          {
            supplier_model_id: "model-sol",
            supplier_id: "supplier-aixora",
            display_name: "GPT-5.6 Sol",
            provider_model_name: "gpt-5.6-sol",
            capability: "text",
            enabled: 1,
          },
          {
            supplier_model_id: "model-terra",
            supplier_id: "supplier-aixora",
            display_name: "GPT-5.6 Terra",
            provider_model_name: "gpt-5.6-terra",
            capability: "text",
            enabled: 1,
          },
        ],
        headers: { etag: "\"model-catalog-1\"" },
      };
    }
    if (url === "/chapters/chapter-1") {
      return { data: chapter };
    }
    if (url === "/chapters/chapter-1/status") {
      return {
        data: {
          status: revisions.some((revision) => revision.approval_status === "approved")
            ? "script_approved"
            : chapter.current_source_revision_id
              ? "source_ready"
              : "missing_source",
          blocking_reason: revisions.some((revision) => revision.approval_status === "approved")
            ? ""
            : "未确认剧本，不允许生成分镜。",
          next_action: chapter.current_source_revision_id ? "generate_script" : "add_source",
        },
      };
    }
    if (url === "/chapters/chapter-1/script/revisions") {
      return { data: revisions };
    }
    throw new Error(`unexpected GET ${url}`);
  });

  mockedPost.mockImplementation(async (url: string, payload?: unknown) => {
    if (url === "/chapters/chapter-1/source-revisions") {
      const source = payload as { content: string };
      const revision: SourceRevisionRead = {
        source_revision_id: "source-1",
        chapter_id: "chapter-1",
        number: 1,
        object_id: "object-1",
        content_hash: "hash-1",
        created_at: "2026-07-05T10:01:00Z",
      };
      chapter = {
        ...chapter,
        current_source_revision_id: revision.source_revision_id,
        source_text: source.content,
      };
      return { data: revision };
    }
    if (url === "/chapters/chapter-1/script/generate") {
      revisions = [generatedScript];
      return { data: generatedScript };
    }
    if (url === "/script-revisions/script-2/approve") {
      revisions = revisions.map((revision) =>
        revision.revision_id === "script-2"
          ? { ...revision, approval_status: "approved", current: true }
          : revision,
      );
      return { data: revisions.find((revision) => revision.revision_id === "script-2") };
    }
    throw new Error(`unexpected POST ${url}`);
  });

  mockedPut.mockImplementation(async (url: string, payload?: unknown) => {
    if (url === "/projects/project-1/model-bindings") {
      const next = payload as typeof bindings;
      bindings = next;
      bindingRevision += 1;
      return {
        data: {
          project_id: "project-1",
          ...bindings,
          binding_set_revision: bindingRevision,
        },
        headers: { etag: `\"binding-set-${bindingRevision}\"` },
      };
    }
    if (url === "/script-revisions/script-1") {
      const update = payload as { content: string };
      revisions = [{ ...generatedScript }, { ...editedScript, content: update.content }];
      return { data: revisions[1] };
    }
    throw new Error(`unexpected PUT ${url}`);
  });
}

describe("chapter source and script workspace tabs", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
    mockedPut.mockReset();
    setupWorkspaceMocks();
    window.history.replaceState({}, "", "/projects/project-1/chapters/chapter-1");
  });

  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  test("saves source as a new revision and shows the current source text", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { level: 1, name: "第一章" })).toBeInTheDocument();
    expect(within(screen.getByLabelText("workflow rail")).getByRole("listitem", { name: "原文完成" })).toHaveAttribute("data-reason", "暂无小说原文");
    expect(within(screen.getByLabelText("workflow rail")).getByRole("listitem", { name: "分镜待确认" })).toHaveAttribute("data-reason", "未确认剧本，不允许生成分镜。");
    expect(screen.getByText("分镜阶段将在生成并确认剧本后解锁")).toBeInTheDocument();
    expect(screen.getByText("暂无小说原文。粘贴正文后才能生成剧本。")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "仅保存原文" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/source-revisions", {
        content: "第一章正文。沈清荷醒来。",
      }),
    );
    expect(await screen.findByText("原文已保存为新版本。")).toBeInTheDocument();
    expect(screen.getByDisplayValue("第一章正文。沈清荷醒来。")).toBeInTheDocument();
  });

  test("generates, validates, edits, and approves a script revision", async () => {
    render(<App />);

    fireEvent.change(await screen.findByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "仅保存原文" }));
    await screen.findByText("原文已保存为新版本。");

    fireEvent.click(screen.getByRole("tab", { name: "剧本" }));
    fireEvent.click(await screen.findByRole("button", { name: "生成剧本" }));

    expect(await screen.findByText("script_markdown_contract")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
    expect(screen.getByText("待确认")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByLabelText("剧本内容")).toHaveValue("# 第一场\n沈清荷推门入内。"),
    );

    fireEvent.change(screen.getByLabelText("剧本内容"), {
      target: { value: "# 第一场\n沈清荷推门入内，压低声音。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存为新剧本版本" }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/script-revisions/script-1", {
        content: "# 第一场\n沈清荷推门入内，压低声音。",
      }),
    );
    expect(await screen.findByText("Revision 2")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByLabelText("剧本内容")).toHaveValue(
        "# 第一场\n沈清荷推门入内，压低声音。",
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "确认剧本" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/script-revisions/script-2/approve", {
        reviewer: "local-user",
        note: "",
      }),
    );
    expect(await screen.findByText("已确认")).toBeInTheDocument();
    expect(within(screen.getByLabelText("workflow rail")).getByText("剧本已确认")).toBeInTheDocument();
  });

  test("renders the approved source workbench and saves before generating a script", async () => {
    render(<App />);

    expect(await screen.findByRole("navigation", { name: "章节导航" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "原文转剧本" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /第二章/ })).toHaveAttribute(
      "href",
      "/projects/project-1/chapters/chapter-2",
    );
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "文本模型" })).toHaveValue("model-sol"),
    );
    const durationSelect = screen.getByRole("combobox", { name: "目标时长" });
    expect(durationSelect).toHaveValue("3");
    fireEvent.change(durationSelect, { target: { value: "5" } });

    fireEvent.change(screen.getByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存并生成剧本" }));

    await waitFor(() =>
      expect(mockedPost.mock.calls.slice(0, 2)).toEqual([
        ["/chapters/chapter-1/source-revisions", { content: "第一章正文。沈清荷醒来。" }],
        ["/chapters/chapter-1/script/generate", { target_duration_minutes: 5 }],
      ]),
    );
    expect(await screen.findByText("script_markdown_contract")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
  });

  test("saves a changed script model binding before source and script generation", async () => {
    const callOrder: string[] = [];
    const originalPut = mockedPut.getMockImplementation();
    const originalPost = mockedPost.getMockImplementation();
    mockedPut.mockImplementation(async (...args: unknown[]) => {
      callOrder.push("binding");
      return originalPut?.(...args);
    });
    mockedPost.mockImplementation(async (...args: unknown[]) => {
      callOrder.push(String(args[0]).endsWith("/source-revisions") ? "source" : "script");
      return originalPost?.(...args);
    });

    render(<App />);

    const modelSelect = await screen.findByRole("combobox", { name: "文本模型" });
    await waitFor(() => expect(modelSelect).toHaveValue("model-sol"));
    fireEvent.change(modelSelect, { target: { value: "model-terra" } });
    fireEvent.change(screen.getByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存并生成剧本" }));

    await waitFor(() => expect(callOrder.slice(0, 3)).toEqual(["binding", "source", "script"]));
    expect(mockedPut).toHaveBeenCalledWith(
      "/projects/project-1/model-bindings",
      {
        defaults: { text: "model-sol", image: "", video: "" },
        operation_overrides: { script_adaptation: "model-terra" },
      },
      { headers: { "If-Match": "\"binding-set-1\"" } },
    );
    expect(screen.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
  });

  test("save-only persists the source without generating a script", async () => {
    render(<App />);

    fireEvent.change(await screen.findByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "仅保存原文" }));

    await screen.findByText("原文已保存为新版本。");
    expect(mockedPost).not.toHaveBeenCalledWith("/chapters/chapter-1/script/generate");
  });

  test("shows backend error codes when script generation fails", async () => {
    mockedPost.mockImplementation(async (url: string, payload?: unknown) => {
      if (url === "/chapters/chapter-1/source-revisions") {
        const source = payload as { content: string };
        return {
          data: {
            source_revision_id: "source-1",
            chapter_id: "chapter-1",
            number: 1,
            object_id: "object-1",
            content_hash: "hash-1",
            created_at: "2026-07-05T10:01:00Z",
            content: source.content,
          },
        };
      }
      if (url === "/chapters/chapter-1/script/generate") {
        throw {
          response: {
            data: {
              error_code: "SOURCE_REVISION_REQUIRED",
              error_message: "chapter source revision is required",
            },
          },
        };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    render(<App />);

    fireEvent.change(await screen.findByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "仅保存原文" }));
    await screen.findByText("原文已保存为新版本。");
    fireEvent.click(screen.getByRole("tab", { name: "剧本" }));
    fireEvent.click(await screen.findByRole("button", { name: "生成剧本" }));

    expect(await screen.findByText("SOURCE_REVISION_REQUIRED")).toBeInTheDocument();
    expect(screen.getByText("chapter source revision is required")).toBeInTheDocument();
  });

  test("shows backend error codes when chapter status loading fails", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1") {
        return { data: baseChapter };
      }
      if (url === "/chapters/chapter-1/status") {
        throw {
          response: {
            data: {
              error_code: "CHAPTER_STATUS_FAILED",
              error_message: "chapter status unavailable",
            },
          },
        };
      }
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: [] };
      }
      throw new Error(`unexpected GET ${url}`);
    });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    expect(await screen.findByText("CHAPTER_STATUS_FAILED")).toBeInTheDocument();
    expect(screen.getByText("chapter status unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /重\s*试/ })).toBeInTheDocument();
  });

  test("shows backend error codes and can retry source save failures", async () => {
    let sourceAttempts = 0;
    mockedPost.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1/source-revisions") {
        sourceAttempts += 1;
        throw {
          response: {
            data: {
              error_code: "SOURCE_SAVE_FAILED",
              error_message: "source save rejected",
            },
          },
        };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    render(<App />);

    fireEvent.change(await screen.findByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "仅保存原文" }));

    expect(await screen.findByText("SOURCE_SAVE_FAILED")).toBeInTheDocument();
    expect(screen.getByText("source save rejected")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /重\s*试/ }));

    await waitFor(() => expect(sourceAttempts).toBe(2));
  });

  test("does not allow approving an old script while save is pending", async () => {
    let resolveSave: ((value: { data: ScriptRevisionRead }) => void) | undefined;
    mockedPut.mockImplementation((url: string, payload?: unknown) => {
      if (url === "/script-revisions/script-1") {
        const update = payload as { content: string };
        return new Promise((resolve) => {
          resolveSave = resolve;
          setTimeout(() => {
            resolve({
              data: {
                ...editedScript,
                content: update.content,
              },
            });
          }, 100);
        });
      }
      throw new Error(`unexpected PUT ${url}`);
    });
    render(<App />);

    fireEvent.change(await screen.findByLabelText("小说原文"), {
      target: { value: "第一章正文。沈清荷醒来。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "仅保存原文" }));
    await screen.findByText("原文已保存为新版本。");
    fireEvent.click(screen.getByRole("tab", { name: "剧本" }));
    fireEvent.click(await screen.findByRole("button", { name: "生成剧本" }));
    await screen.findByText("script_markdown_contract");

    fireEvent.change(screen.getByLabelText("剧本内容"), {
      target: { value: "# 第一场\n沈清荷推门入内，压低声音。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存为新剧本版本" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "确认剧本" })).toBeDisabled());
    fireEvent.click(screen.getByRole("button", { name: "确认剧本" }));
    expect(mockedPost).not.toHaveBeenCalledWith("/script-revisions/script-1/approve", {
      reviewer: "local-user",
      note: "",
    });
    expect(resolveSave).toBeDefined();
  });

  test("keeps a dirty draft bound to its initial revision across revision refetches", async () => {
    const initialRevision = { ...generatedScript, current: false };
    const newerRevision = { ...editedScript, current: true };
    let revisionsResponse = [initialRevision];
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: revisionsResponse };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    mockedPut.mockResolvedValue({ data: { ...initialRevision, content: "# 第一场\n未保存草稿。" } });
    const queryClient = renderWithQueryClient(<ScriptTab chapter={sourceReadyChapter()} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("剧本内容"), {
      target: { value: "# 第一场\n未保存草稿。" },
    });
    revisionsResponse = [initialRevision, newerRevision];

    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: ["script-revisions", "chapter-1"] });
    });

    expect(await screen.findByText("Revision 2")).toBeInTheDocument();
    expect(screen.getByLabelText("剧本内容")).toHaveValue("# 第一场\n未保存草稿。");
    fireEvent.click(screen.getByRole("button", { name: "保存为新剧本版本" }));

    await waitFor(() =>
      expect(mockedPut).toHaveBeenCalledWith("/script-revisions/script-1", {
        content: "# 第一场\n未保存草稿。",
      }),
    );
  });

  test("retries a failed approve against the original revision after selection changes", async () => {
    const firstRevision = { ...generatedScript, current: true };
    const secondRevision = { ...editedScript, approval_status: "pending", current: false };
    const approveUrls: string[] = [];
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: [firstRevision, secondRevision] };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    mockedPost.mockImplementation(async (url: string) => {
      if (url.endsWith("/approve")) {
        approveUrls.push(url);
        throw {
          response: {
            data: {
              error_code: "SCRIPT_APPROVAL_FAILED",
              error_message: "approval rejected",
            },
          },
        };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    renderWithQueryClient(<ScriptTab chapter={sourceReadyChapter()} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认剧本" }));
    expect(await screen.findByText("SCRIPT_APPROVAL_FAILED")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revision 2" }));
    fireEvent.click(screen.getByRole("button", { name: /重\s*试/ }));

    await waitFor(() =>
      expect(approveUrls).toEqual([
        "/script-revisions/script-1/approve",
        "/script-revisions/script-1/approve",
      ]),
    );
  });

  test("does not allow approving or rejecting a dirty draft before saving", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: [{ ...generatedScript, current: true }] };
      }
      throw new Error(`unexpected GET ${url}`);
    });
    renderWithQueryClient(<ScriptTab chapter={sourceReadyChapter()} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("剧本内容"), {
      target: { value: "# 第一场\n未保存草稿。" },
    });

    await waitFor(() => expect(screen.getByRole("button", { name: "确认剧本" })).toBeDisabled());
    expect(screen.getByRole("button", { name: "拒绝剧本" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "确认剧本" }));
    fireEvent.click(screen.getByRole("button", { name: "拒绝剧本" }));

    expect(mockedPost).not.toHaveBeenCalledWith("/script-revisions/script-1/approve", {
      reviewer: "local-user",
      note: "",
    });
    expect(mockedPost).not.toHaveBeenCalledWith("/script-revisions/script-1/reject", {
      reviewer: "local-user",
      note: "",
    });
  });
});
