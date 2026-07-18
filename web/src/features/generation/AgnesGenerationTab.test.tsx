import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { AgnesGenerationTab } from "./AgnesGenerationTab";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = apiClient.get as unknown as Mock;
const mockedPost = apiClient.post as unknown as Mock;

const chapter = {
  chapter_id: "chapter-1",
  project_id: "project-1",
  title: "第一章",
  position: 1,
  current_source_revision_id: "source-1",
  created_at: "2026-07-05T10:00:00Z",
  updated_at: "2026-07-05T10:00:00Z",
  source_text: "",
};

const revision = {
  revision_id: "prompt-rev-1",
  artifact_id: "chapter-1:shot-prompts",
  chapter_id: "chapter-1",
  number: 1,
  approval_status: "approved",
  current: true,
  content: "{}",
  validation_results: [],
  source_storyboard_revision_id: "storyboard-1",
  shots: [
    {
      shot_id: "SHOT_001",
      duration_seconds: 5,
      positive_prompt: "Ready prompt",
      negative_prompt: "bad anatomy",
      continuity_notes: [],
      asset_refs: ["asset-1"],
      agnes_video_params: {},
    },
    {
      shot_id: "SHOT_002",
      duration_seconds: 5,
      positive_prompt: "Blocked prompt",
      negative_prompt: "",
      continuity_notes: [],
      asset_refs: [],
      agnes_video_params: {},
    },
  ],
  readiness: {
    SHOT_001: { status: "ready" },
    SHOT_002: { status: "blocked" },
  },
};

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
}

describe("AgnesGenerationTab", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
  });

  test("supports ready selection, batch submit, row preview, and polling live notice", async () => {
    mockedGet.mockResolvedValue({
      data: [
        {
          job_id: "job-active",
          provider: "agnes",
          job_type: "video",
          project_id: "project-1",
          chapter_id: "chapter-1",
          shot_id: "SHOT_001",
          prompt_revision_id: "prompt-rev-1",
          provider_job_id: "abc123",
          provider_result_id: "",
          internal_status: "polling",
          ui_status: "generating",
          idempotency_key: "prompt-rev-1:SHOT_001:source",
          attempt_number: 1,
          error_code: "",
          error_message: "",
          created_at: "2026-07-05T10:00:00Z",
          updated_at: "2026-07-05T10:00:00Z",
        },
      ],
    });
    mockedPost.mockResolvedValue({ data: { job_id: "job-new", created_at: "1", updated_at: "1" } });

    renderWithQueryClient(<AgnesGenerationTab chapter={chapter} revision={revision} />);

    expect(await screen.findByLabelText("自动轮询状态")).toHaveTextContent("自动轮询已开启");
    const generationTable = screen.getByRole("table", { name: "Agnes generation table" });
    expect(within(generationTable).getByRole("row", { name: /SHOT_001/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("选择 SHOT_002")).toBeDisabled();
    fireEvent.click(screen.getByLabelText("选择 SHOT_001"));
    expect(screen.getByText(/已选择 ready 镜头 1 个/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "批量提交 ready" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/generation/video-jobs", {
        prompt_revision_id: "prompt-rev-1",
        shot_id: "SHOT_001",
        idempotency_key: "prompt-rev-1:SHOT_001:source",
      }),
    );
    expect(await screen.findByText(/提交完成：created 1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "SHOT_002" }));
    expect(within(generationTable).getByRole("row", { name: /SHOT_002/ })).toHaveAttribute("aria-selected", "true");
    const preview = screen.getByLabelText("Agnes request preview");
    expect(within(preview).getByText("Blocked prompt")).toBeInTheDocument();
  });
});
