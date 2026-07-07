import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Skeleton, Tag, Typography } from "antd";
import { useMemo, useState } from "react";
import type { ChapterRead } from "../projects/api";
import type { ShotPromptRevisionRead, ShotPromptShot } from "../prompts/api";
import {
  listGenerationJobs,
  queueVideoJob,
  refreshGenerationJob,
  type GenerationJobRead,
} from "./api";

type AgnesGenerationTabProps = {
  chapter: ChapterRead;
  revision: ShotPromptRevisionRead;
};

const terminalStatuses = new Set(["completed", "failed", "cancelled"]);

export function AgnesGenerationTab({ chapter, revision }: AgnesGenerationTabProps) {
  const queryClient = useQueryClient();
  const jobsQueryKey = ["generation-jobs", chapter.chapter_id];
  const [selectedShotId, setSelectedShotId] = useState(revision.shots[0]?.shot_id ?? "");
  const jobsQuery = useQuery({
    queryKey: jobsQueryKey,
    queryFn: () => listGenerationJobs(chapter.chapter_id),
    refetchInterval: (query) =>
      (query.state.data ?? []).some((job) => !terminalStatuses.has(job.internal_status)) ? 5000 : false,
  });
  const jobs = jobsQuery.data ?? [];
  const selectedShot = revision.shots.find((shot) => shot.shot_id === selectedShotId) ?? revision.shots[0];
  const selectedJob = selectedShot ? latestJobForShot(jobs, selectedShot.shot_id) : undefined;

  const queueMutation = useMutation({
    mutationFn: (shot: ShotPromptShot) =>
      queueVideoJob(chapter.chapter_id, {
        prompt_revision_id: revision.revision_id,
        shot_id: shot.shot_id,
        idempotency_key: `${revision.revision_id}:${shot.shot_id}:source`,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: jobsQueryKey }),
  });
  const refreshMutation = useMutation({
    mutationFn: (jobId: string) => refreshGenerationJob(jobId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: jobsQueryKey }),
  });
  const rows = useMemo(
    () =>
      revision.shots.map((shot) => ({
        shot,
        readiness: revision.readiness?.[shot.shot_id]?.status ?? "blocked",
        job: latestJobForShot(jobs, shot.shot_id),
      })),
    [jobs, revision.readiness, revision.shots],
  );
  const hasActiveJobs = jobs.some((job) => !terminalStatuses.has(job.internal_status));

  if (jobsQuery.isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  return (
    <section aria-label="Agnes 生成工作台" style={{ display: "grid", gap: 16 }}>
      <div style={headerStyle}>
        <Typography.Title level={2} style={titleStyle}>
          Agnes 生成
        </Typography.Title>
        <Typography.Text type="secondary">Ready 与 blocked 镜头都可见；只有 ready 镜头可提交。</Typography.Text>
      </div>

      {hasActiveJobs ? (
        <Alert
          message="自动轮询已开启"
          description="存在 queued/submitting/generating 任务，列表会定时刷新。手动刷新不会停止自动轮询。"
          showIcon
          type="info"
        />
      ) : null}
      {queueMutation.isError || refreshMutation.isError ? (
        <Alert message="Agnes 生成操作失败" showIcon type="error" />
      ) : null}

      <div style={workspaceGridStyle}>
        <section aria-label="Agnes generation rows" style={panelStyle}>
          <div style={toolbarStyle}>
            <Button disabled={!hasReady(rows) || queueMutation.isPending}>
              批量提交 ready
            </Button>
            <Button onClick={() => void jobsQuery.refetch()}>手动刷新</Button>
            <Typography.Text type="secondary">RPM 限制：queued 任务会按后端节流提交。</Typography.Text>
          </div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Shot</th>
                <th style={thStyle}>Ready</th>
                <th style={thStyle}>Job</th>
                <th style={thStyle}>Attempt</th>
                <th style={thStyle}>状态</th>
                <th style={thStyle}>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ shot, readiness, job }) => {
                const ready = readiness === "ready";
                return (
                  <tr key={shot.shot_id}>
                    <td style={tdStyle}>
                      <Button type="link" onClick={() => setSelectedShotId(shot.shot_id)}>
                        {shot.shot_id}
                      </Button>
                    </td>
                    <td style={tdStyle}>
                      <Tag color={ready ? "success" : "default"}>{ready ? "ready" : "blocked"}</Tag>
                    </td>
                    <td style={tdStyle}>{job?.job_id.slice(0, 8) ?? "-"}</td>
                    <td style={tdStyle}>{job?.attempt_number ?? "-"}</td>
                    <td style={tdStyle}>{job ? <StatusTag job={job} /> : <Tag>waiting</Tag>}</td>
                    <td style={tdStyle}>
                      {job && !terminalStatuses.has(job.internal_status) ? (
                        <Button size="small" onClick={() => refreshMutation.mutate(job.job_id)}>
                          刷新
                        </Button>
                      ) : (
                        <Button
                          disabled={!ready || queueMutation.isPending}
                          size="small"
                          type="primary"
                          onClick={() => queueMutation.mutate(shot)}
                        >
                          提交
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        <section aria-label="Agnes request preview" style={panelStyle}>
          <Typography.Title level={3} style={sectionTitleStyle}>
            请求预览
          </Typography.Title>
          {selectedShot ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div style={videoFrameStyle}>16:9 video preview</div>
              <PreviewBlock label="Prompt" value={selectedShot.positive_prompt} />
              <PreviewBlock label="Negative Prompt" value={selectedShot.negative_prompt} />
              <PreviewBlock label="参考资产" value={selectedShot.asset_refs.join(", ") || "-"} />
              <PreviewBlock label="视频参数" value={JSON.stringify(selectedShot.agnes_video_params ?? {})} />
              <PreviewBlock label="当前 Job" value={selectedJob?.job_id ?? "尚未提交"} />
            </div>
          ) : (
            <Typography.Text type="secondary">暂无 Shot Prompt 镜头。</Typography.Text>
          )}
        </section>
      </div>
    </section>
  );
}

function StatusTag({ job }: { job: GenerationJobRead }) {
  const color = job.internal_status === "failed" ? "error" : job.internal_status === "completed" ? "success" : "processing";
  return <Tag color={color}>{job.ui_status}</Tag>;
}

function PreviewBlock({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "grid", gap: 4 }}>
      <Typography.Text strong>{label}</Typography.Text>
      <Typography.Paragraph style={{ margin: 0 }}>{value}</Typography.Paragraph>
    </div>
  );
}

function latestJobForShot(jobs: GenerationJobRead[], shotId: string) {
  return [...jobs].reverse().find((job) => job.shot_id === shotId);
}

function hasReady(rows: Array<{ readiness: string }>) {
  return rows.some((row) => row.readiness === "ready");
}

const headerStyle = { display: "grid", gap: 4 };
const titleStyle = { fontSize: 18, margin: 0 };
const sectionTitleStyle = { fontSize: 16, margin: 0 };
const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};
const workspaceGridStyle = { display: "grid", gap: 12, gridTemplateColumns: "minmax(0, 1.5fr) minmax(320px, 0.8fr)" };
const toolbarStyle = { alignItems: "center", display: "flex", flexWrap: "wrap" as const, gap: 8 };
const tableStyle = { borderCollapse: "collapse" as const, width: "100%" };
const thStyle = { borderBottom: "1px solid #d9dee8", padding: 8, textAlign: "left" as const };
const tdStyle = { borderBottom: "1px solid #eef1f6", padding: 8, verticalAlign: "top" as const };
const videoFrameStyle = {
  alignItems: "center",
  aspectRatio: "16 / 9",
  background: "#101828",
  borderRadius: 6,
  color: "#ffffff",
  display: "flex",
  justifyContent: "center",
};
