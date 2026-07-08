import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { GenerationResultsTab } from "./GenerationResultsTab";

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

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
}

describe("GenerationResultsTab", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
    mockedGet.mockImplementation((url: string) => {
      if (url === "/chapters/chapter-1/results") {
        return Promise.resolve({
          data: [
            {
              shot_id: "SHOT_001",
              current_result_id: "result-1",
              results: [
                {
                  result_id: "result-1",
                  job_id: "job-1",
                  attempt_number: 1,
                  media_type: "video/mp4",
                  source_url: "https://cdn.example.test/source-1.mp4",
                  source_url_state: "source_url_active",
                  local_result_available: true,
                  local_content_url: "/api/results/result-1/content",
                  created_at: "2026-07-05T10:00:00Z",
                },
                {
                  result_id: "result-2",
                  job_id: "job-2",
                  attempt_number: 2,
                  media_type: "video/mp4",
                  source_url: "https://cdn.example.test/source-2.mp4",
                  source_url_state: "source_url_expired",
                  local_result_available: true,
                  local_content_url: "/api/results/result-2/content",
                  created_at: "2026-07-05T10:05:00Z",
                },
              ],
            },
          ],
        });
      }
      if (url === "/chapters/chapter-1/assets") {
        return Promise.resolve({
          data: [
            {
              asset_id: "asset-usable",
              project_id: "project-1",
              chapter_id: "chapter-1",
              asset_type: "shot_keyframe",
              name: "可用关键帧",
              object_id: "object-1",
              media_type: "image/png",
              width: 1,
              height: 1,
              status: "usable",
              source_type: "upload",
              source_job_id: "",
              metadata: {},
              bindings: [],
              created_at: "2026-07-05T10:00:00Z",
              updated_at: "2026-07-05T10:00:00Z",
            },
            {
              asset_id: "asset-draft",
              project_id: "project-1",
              chapter_id: "chapter-1",
              asset_type: "shot_keyframe",
              name: "草稿关键帧",
              object_id: "object-2",
              media_type: "image/png",
              width: 1,
              height: 1,
              status: "draft",
              source_type: "upload",
              source_job_id: "",
              metadata: {},
              bindings: [],
              created_at: "2026-07-05T10:00:00Z",
              updated_at: "2026-07-05T10:00:00Z",
            },
          ],
        });
      }
      if (url === "/generation/jobs/job-2") {
        return Promise.resolve({
          data: {
            job_id: "job-2",
            provider: "agnes",
            job_type: "video",
            project_id: "project-1",
            chapter_id: "chapter-1",
            shot_id: "SHOT_001",
            prompt_revision_id: "prompt-rev-1",
            provider_job_id: "x7k9q",
            provider_result_id: "result-2",
            internal_status: "completed",
            ui_status: "completed",
            idempotency_key: "idem-2",
            attempt_number: 2,
            error_code: "",
            error_message: "",
            created_at: "2026-07-05T10:05:00Z",
            updated_at: "2026-07-05T10:06:00Z",
            request: {
              shot_id: "SHOT_001",
              prompt: "Source prompt",
              negative_prompt: "Source negative",
              duration_seconds: 5,
              asset_ids: ["asset-old"],
              parameters: { mode: "std" },
            },
          },
        });
      }
      return Promise.resolve({ data: [] });
    });
    mockedPost.mockResolvedValue({ data: {} });
  });

  test("selects versions, adopts results, reviews, and submits rerun asset overrides", async () => {
    renderWithQueryClient(<GenerationResultsTab chapter={chapter} />);

    const preview = await screen.findByLabelText("video result preview");
    expect(within(preview).getByText("Job job-1")).toBeInTheDocument();
    expect(preview.querySelector("video")).toHaveAttribute("src", "/api/results/result-1/content");

    fireEvent.click(screen.getByText("v2"));
    expect(within(preview).getByText("Job job-2")).toBeInTheDocument();
    expect(preview.querySelector("video")).toHaveAttribute("src", "/api/results/result-2/content");
    expect(within(preview).getByText("Source URL: source_url_expired")).toBeInTheDocument();

    const rows = screen.getByLabelText("shot result rows");
    fireEvent.click(within(rows).getByRole("button", { name: "采用 result-2" }));
    await waitFor(() => expect(mockedPost).toHaveBeenCalledWith("/shots/SHOT_001/results/result-2/select"));

    fireEvent.click(within(preview).getByRole("button", { name: "标记通过" }));
    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/results/result-2/review", {
        decision: "passed",
        failure_category: "",
        note: "",
      }),
    );

    fireEvent.click(within(preview).getByRole("button", { name: "创建重跑" }));
    const dialog = await screen.findByRole("dialog", { name: "创建 Agnes 重跑" });
    expect(await within(dialog).findByText(/当前资产：asset-old/)).toBeInTheDocument();
    expect(await within(dialog).findByLabelText(/可用关键帧/)).toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/草稿关键帧/)).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByLabelText(/可用关键帧/));
    fireEvent.click(within(dialog).getByRole("button", { name: "创建重跑" }));

    await waitFor(() => {
      const rerunCall = mockedPost.mock.calls.find(([url]) => url === "/generation/jobs/job-2/rerun");
      expect(rerunCall?.[1]).toMatchObject({
        prompt: "Source prompt",
        negative_prompt: "Source negative",
        asset_ids: ["asset-usable"],
        duration_seconds: 5,
        mode: "std",
      });
    });
  });
});
