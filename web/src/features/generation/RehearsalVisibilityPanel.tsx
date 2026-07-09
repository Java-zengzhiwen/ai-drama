import { Alert, Tag, Typography } from "antd";
import type { ReactNode } from "react";
import type { GenerationJobRead, ShotResultsRead } from "./api";

type Scenario = "source_success" | "source_failed_then_rerun_success" | "unknown";

type ShotVisibility = {
  shotId: string;
  scenario: Scenario;
  jobs: GenerationJobRead[];
  results: ShotResultsRead["results"];
  currentResultId: string;
};

export function deriveRehearsalVisibility(jobs: GenerationJobRead[], resultGroups: ShotResultsRead[]) {
  const shotIds = [...new Set([...jobs.map((job) => job.shot_id), ...resultGroups.map((group) => group.shot_id)])].sort();
  const resultByShot = new Map(resultGroups.map((group) => [group.shot_id, group]));
  const shots: ShotVisibility[] = shotIds.map((shotId) => {
    const shotJobs = jobs
      .filter((job) => job.shot_id === shotId)
      .sort((left, right) => left.attempt_number - right.attempt_number);
    const group = resultByShot.get(shotId);
    return {
      shotId,
      scenario: deriveScenario(shotJobs, group),
      jobs: shotJobs,
      results: group?.results ?? [],
      currentResultId: group?.current_result_id ?? "",
    };
  });
  return {
    shots,
    summary: {
      totalShots: shots.length,
      completedShots: shots.filter((shot) => shot.jobs.some((job) => job.internal_status === "completed")).length,
      failedShots: shots.filter((shot) => shot.jobs.some((job) => job.internal_status === "failed")).length,
      rerunShots: shots.filter((shot) => Math.max(0, ...shot.jobs.map((job) => job.attempt_number)) > 1).length,
      selectedResultCoverage: shots.filter((shot) => shot.currentResultId).length,
    },
  };
}

function deriveScenario(jobs: GenerationJobRead[], group?: ShotResultsRead): Scenario {
  const first = jobs.find((job) => job.attempt_number === 1);
  if (!first || !group?.current_result_id || group.results.length === 0) {
    return "unknown";
  }
  if (first.internal_status === "completed") {
    return "source_success";
  }
  const selected = group.results.find((result) => result.result_id === group.current_result_id);
  const selectedJob = selected ? jobs.find((job) => job.job_id === selected.job_id) : undefined;
  if (
    first.internal_status === "failed" &&
    selectedJob &&
    selectedJob.attempt_number > 1 &&
    selectedJob.internal_status === "completed"
  ) {
    return "source_failed_then_rerun_success";
  }
  return "unknown";
}

export function RehearsalVisibilityPanel({
  jobs,
  resultGroups,
}: {
  jobs: GenerationJobRead[];
  resultGroups: ShotResultsRead[];
}) {
  const visibility = deriveRehearsalVisibility(jobs, resultGroups);
  if (visibility.summary.totalShots === 0) {
    return (
      <section aria-label="M4 rehearsal visibility" style={panelStyle}>
        <Typography.Title level={3} style={sectionTitleStyle}>
          M4 Rehearsal Visibility
        </Typography.Title>
        <Alert message="No generation jobs or results yet." showIcon type="info" />
        <DeferredBanner />
      </section>
    );
  }
  return (
    <section aria-label="M4 rehearsal visibility" style={panelStyle}>
      <Typography.Title level={3} style={sectionTitleStyle}>
        M4 Rehearsal Visibility
      </Typography.Title>
      <DeferredBanner />
      <section aria-label="Chapter Rehearsal Summary Card" style={summaryGridStyle}>
        <Metric label="Total shots" value={visibility.summary.totalShots} />
        <Metric label="Completed shots" value={visibility.summary.completedShots} />
        <Metric label="Failed shots" value={visibility.summary.failedShots} />
        <Metric label="Rerun shots" value={visibility.summary.rerunShots} />
        <Metric label="Selected results" value={visibility.summary.selectedResultCoverage} />
      </section>
      <Typography.Text type="secondary">Review status unavailable in Phase 1</Typography.Text>
      <Table
        ariaLabel="Shot Scenario Matrix"
        headers={["Shot", "Scenario", "Current result"]}
        rows={visibility.shots.map((shot) => [
          shot.shotId,
          <Tag key="scenario" color={shot.scenario === "unknown" ? "default" : "success"}>
            {shot.scenario}
          </Tag>,
          shot.currentResultId || "No result selected",
        ])}
      />
      <Table
        ariaLabel="Shot Timeline / Attempt History"
        headers={["Shot", "Attempt", "Job ID", "Status", "Error code"]}
        rows={visibility.shots.flatMap((shot) =>
          shot.jobs.map((job) => [
            shot.shotId,
            String(job.attempt_number),
            job.job_id,
            job.internal_status,
            job.error_code || "-",
          ]),
        )}
      />
      <Table
        ariaLabel="Result Version History"
        headers={["Shot", "Result", "Source job", "Attempt", "Local artifact"]}
        rows={visibility.shots.flatMap((shot) =>
          shot.results.map((result) => [
            shot.shotId,
            result.result_id,
            result.job_id,
            String(result.attempt_number),
            localArtifactCell(result),
          ]),
        )}
      />
      <Table
        ariaLabel="Current Selection Indicator"
        headers={["Shot", "Selected result"]}
        rows={visibility.shots.map((shot) => [shot.shotId, shot.currentResultId || "No result selected"])}
      />
    </section>
  );
}

function DeferredBanner() {
  return (
    <Alert
      message="Mock rehearsal visibility only"
      description={
        <span style={{ display: "grid", gap: 2 }}>
          <span>No real Agnes request was made by this panel</span>
          <span>Real provider smoke test remains deferred</span>
          <code>AUTHORIZE_REAL_AGNES_VIDEO_SMOKE_TEST</code>
          <span>Provider smoke status unavailable from Phase 1 data</span>
        </span>
      }
      showIcon
      type="warning"
    />
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div style={metricStyle}>
      <Typography.Text type="secondary">{label}</Typography.Text>
      <Typography.Text strong>{value}</Typography.Text>
    </div>
  );
}

function Table({
  ariaLabel,
  headers,
  rows,
}: {
  ariaLabel: string;
  headers: string[];
  rows: Array<Array<ReactNode>>;
}) {
  return (
    <section aria-label={ariaLabel} style={{ overflowX: "auto" }}>
      <Typography.Title level={4} style={subTitleStyle}>
        {ariaLabel}
      </Typography.Title>
      <table style={tableStyle}>
        <thead>
          <tr>{headers.map((header) => <th key={header} style={thStyle}>{header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${ariaLabel}-${index}`}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} style={tdStyle}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function localArtifactCell(result: ShotResultsRead["results"][number]) {
  if (result.local_result_available && result.local_content_url) {
    return (
      <span>
        <a href={result.local_content_url}>{result.local_content_url}</a>
        <video aria-label="Local artifact preview" controls preload="metadata" src={result.local_content_url} style={videoStyle} />
      </span>
    );
  }
  if (result.source_url_state === "source_url_expired") {
    return "Local artifact missing; source URL expired. Rerun required.";
  }
  return "Local artifact unavailable.";
}

const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};
const sectionTitleStyle = { fontSize: 16, margin: 0 };
const subTitleStyle = { fontSize: 14, margin: 0 };
const summaryGridStyle = { display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" };
const metricStyle = { border: "1px solid #eef1f6", borderRadius: 6, display: "grid", gap: 4, padding: 8 };
const tableStyle = { borderCollapse: "collapse" as const, width: "100%" };
const thStyle = { borderBottom: "1px solid #d9dee8", padding: 8, textAlign: "left" as const };
const tdStyle = { borderBottom: "1px solid #eef1f6", padding: 8, verticalAlign: "top" as const };
const videoStyle = { display: "block", marginTop: 6, maxWidth: 180, width: "100%" };
