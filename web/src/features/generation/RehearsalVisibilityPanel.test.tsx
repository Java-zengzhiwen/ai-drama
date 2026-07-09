import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import {
  RehearsalVisibilityPanel,
  deriveRehearsalVisibility,
} from "./RehearsalVisibilityPanel";
import type { GenerationJobRead, ShotResultsRead } from "./api";

const jobs: GenerationJobRead[] = [
  job("job-1", "SHOT_001", 1, "completed"),
  job("job-2a", "SHOT_002", 1, "failed", "generation_failed"),
  job("job-2b", "SHOT_002", 2, "completed"),
  job("job-3", "SHOT_003", 1, "failed", "generation_failed"),
];

const results: ShotResultsRead[] = [
  {
    shot_id: "SHOT_001",
    current_result_id: "result-1",
    results: [result("result-1", "job-1", 1, true, "/api/results/result-1/content", "source_url_active")],
  },
  {
    shot_id: "SHOT_002",
    current_result_id: "result-2b",
    results: [
      result("result-2b", "job-2b", 2, true, "/api/results/result-2b/content", "source_url_expired"),
    ],
  },
  {
    shot_id: "SHOT_003",
    current_result_id: "",
    results: [result("result-3", "job-3", 1, false, "", "source_url_expired")],
  },
];

describe("deriveRehearsalVisibility", () => {
  test("derives source success, failed then rerun success, unknown, and summary counts", () => {
    const visibility = deriveRehearsalVisibility(jobs, results);

    expect(visibility.summary).toMatchObject({
      totalShots: 3,
      completedShots: 2,
      failedShots: 2,
      rerunShots: 1,
      selectedResultCoverage: 2,
    });
    expect(visibility.shots.find((shot) => shot.shotId === "SHOT_001")?.scenario).toBe("source_success");
    expect(visibility.shots.find((shot) => shot.shotId === "SHOT_002")?.scenario).toBe(
      "source_failed_then_rerun_success",
    );
    expect(visibility.shots.find((shot) => shot.shotId === "SHOT_003")?.scenario).toBe("unknown");
  });
});

describe("RehearsalVisibilityPanel", () => {
  test("renders read-only rehearsal evidence and neutral Phase 1 review status", () => {
    render(<RehearsalVisibilityPanel jobs={jobs} resultGroups={results} />);

    expect(screen.getByText("Mock rehearsal visibility only")).toBeInTheDocument();
    expect(screen.getByText("No real Agnes request was made by this panel")).toBeInTheDocument();
    expect(screen.getByText("Real provider smoke test remains deferred")).toBeInTheDocument();
    expect(screen.getByText("AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST")).toBeInTheDocument();
    expect(screen.getByText("Provider smoke status unavailable from Phase 1 data")).toBeInTheDocument();
    expect(screen.getByText("Review status unavailable in Phase 1")).toBeInTheDocument();

    const matrix = screen.getByLabelText("Shot Scenario Matrix");
    expect(within(matrix).getByText("SHOT_001")).toBeInTheDocument();
    expect(within(matrix).getByText("source_success")).toBeInTheDocument();
    expect(within(matrix).getByText("SHOT_002")).toBeInTheDocument();
    expect(within(matrix).getByText("source_failed_then_rerun_success")).toBeInTheDocument();

    const timeline = screen.getByLabelText("Shot Timeline / Attempt History");
    expect(within(timeline).getByText("job-2a")).toBeInTheDocument();
    expect(within(timeline).getAllByText("generation_failed").length).toBeGreaterThan(0);
    expect(within(timeline).getByText("job-2b")).toBeInTheDocument();

    const selection = screen.getByLabelText("Current Selection Indicator");
    expect(within(selection).getByText("SHOT_002")).toBeInTheDocument();
    expect(within(selection).getByText("result-2b")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "/api/results/result-2b/content" })).toHaveAttribute(
      "href",
      "/api/results/result-2b/content",
    );
    expect(screen.getByText("Local artifact missing; source URL expired. Rerun required.")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Local artifact preview")[0]).not.toHaveAttribute("autoplay");
  });

  test("renders a neutral empty state", () => {
    render(<RehearsalVisibilityPanel jobs={[]} resultGroups={[]} />);

    expect(screen.getByText("No generation jobs or results yet.")).toBeInTheDocument();
  });
});

function job(
  job_id: string,
  shot_id: string,
  attempt_number: number,
  internal_status: string,
  error_code = "",
): GenerationJobRead {
  return {
    job_id,
    provider: "agnes",
    job_type: "video",
    project_id: "project-1",
    chapter_id: "chapter-1",
    shot_id,
    prompt_revision_id: "prompt-rev-1",
    provider_job_id: "",
    provider_result_id: "",
    internal_status,
    ui_status: internal_status,
    idempotency_key: job_id,
    attempt_number,
    error_code,
    error_message: "",
    created_at: "2026-07-05T10:00:00Z",
    updated_at: "2026-07-05T10:00:00Z",
  };
}

function result(
  result_id: string,
  job_id: string,
  attempt_number: number,
  local_result_available: boolean,
  local_content_url: string,
  source_url_state: "source_url_active" | "source_url_expired",
) {
  return {
    result_id,
    job_id,
    attempt_number,
    media_type: "video/mp4",
    source_url: "https://cdn.example.test/result.mp4",
    source_url_state,
    local_result_available,
    local_content_url,
    created_at: "2026-07-05T10:00:00Z",
  };
}
