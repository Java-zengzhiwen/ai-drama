import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Checkbox, Drawer, Form, Input, Select, Skeleton, Tag, Typography } from "antd";
import { useMemo, useState } from "react";
import { listAssets } from "../assets/api";
import type { ChapterRead } from "../projects/api";
import {
  getGenerationJob,
  listGenerationResults,
  rerunGenerationJob,
  reviewGenerationResult,
  selectGenerationResult,
  type GenerationResultRead,
  type ShotResultsRead,
} from "./api";

type GenerationResultsTabProps = {
  chapter: ChapterRead;
};

export function GenerationResultsTab({ chapter }: GenerationResultsTabProps) {
  const queryClient = useQueryClient();
  const resultsQueryKey = ["generation-results", chapter.chapter_id];
  const jobsQueryKey = ["generation-jobs", chapter.chapter_id];
  const [previewResultId, setPreviewResultId] = useState("");
  const [rerunResult, setRerunResult] = useState<GenerationResultRead | undefined>();
  const resultsQuery = useQuery({
    queryKey: resultsQueryKey,
    queryFn: () => listGenerationResults(chapter.chapter_id),
  });
  const assetsQuery = useQuery({
    queryKey: ["assets", chapter.chapter_id],
    queryFn: () => listAssets(chapter.chapter_id),
  });
  const sourceJobQuery = useQuery({
    enabled: Boolean(rerunResult?.job_id),
    queryKey: ["generation-job", rerunResult?.job_id],
    queryFn: () => getGenerationJob(rerunResult?.job_id ?? ""),
  });
  const selectMutation = useMutation({
    mutationFn: ({ shotId, resultId }: { shotId: string; resultId: string }) =>
      selectGenerationResult(shotId, resultId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: resultsQueryKey }),
  });
  const reviewMutation = useMutation({
    mutationFn: ({ resultId, payload }: { resultId: string; payload: Parameters<typeof reviewGenerationResult>[1] }) =>
      reviewGenerationResult(resultId, payload),
  });
  const rerunMutation = useMutation({
    mutationFn: ({ jobId, payload }: { jobId: string; payload: Parameters<typeof rerunGenerationJob>[1] }) =>
      rerunGenerationJob(jobId, payload),
    onSuccess: () => {
      setRerunResult(undefined);
      void queryClient.invalidateQueries({ queryKey: resultsQueryKey });
      void queryClient.invalidateQueries({ queryKey: jobsQueryKey });
    },
  });
  const groups = resultsQuery.data ?? [];
  const selectedResult = useMemo(() => {
    const flat = groups.flatMap((group) => group.results);
    return flat.find((result) => result.result_id === previewResultId) ?? flat[0];
  }, [groups, previewResultId]);
  const usableImageAssets = (assetsQuery.data ?? []).filter(
    (asset) => asset.status === "usable" && asset.media_type.startsWith("image/"),
  );

  if (resultsQuery.isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  return (
    <section aria-label="结果与重跑工作台" style={{ display: "grid", gap: 16 }}>
      <div style={headerStyle}>
        <Typography.Title level={2} style={titleStyle}>
          结果与重跑
        </Typography.Title>
        <Typography.Text type="secondary">结果版本、当前采用结果和来源 Job 信息保持可追溯。</Typography.Text>
      </div>

      {resultsQuery.isError || selectMutation.isError || reviewMutation.isError || rerunMutation.isError ? (
        <Alert message="结果加载、选择、审核或重跑失败。请重试。" showIcon type="error" />
      ) : null}

      {groups.length === 0 ? (
        <Alert message="暂无视频结果。提交 Agnes 生成后会显示结果版本。" showIcon type="info" />
      ) : (
        <div style={workspaceGridStyle}>
          <section aria-label="shot result rows" style={panelStyle}>
            {groups.map((group) => (
              <ResultGroup
                group={group}
                key={group.shot_id}
                selecting={selectMutation.isPending}
                selectedResultId={selectedResult?.result_id ?? ""}
                onPreview={setPreviewResultId}
                onSelect={(resultId) => selectMutation.mutate({ shotId: group.shot_id, resultId })}
              />
            ))}
          </section>
          <section aria-label="video result preview" style={panelStyle}>
            <Typography.Title level={3} style={sectionTitleStyle}>
              视频预览
            </Typography.Title>
            {selectedResult ? (
              <ResultPreview
                result={selectedResult}
                reviewing={reviewMutation.isPending}
                onReview={(payload) => reviewMutation.mutate({ resultId: selectedResult.result_id, payload })}
                onRerun={() => setRerunResult(selectedResult)}
              />
            ) : (
              <Typography.Text type="secondary">选择一个结果后预览。</Typography.Text>
            )}
          </section>
          <RerunDrawer
            assets={usableImageAssets}
            job={sourceJobQuery.data}
            loading={sourceJobQuery.isLoading || rerunMutation.isPending}
            open={Boolean(rerunResult)}
            onClose={() => setRerunResult(undefined)}
            onSubmit={(values) => {
              if (!rerunResult) {
                return;
              }
              rerunMutation.mutate({
                jobId: rerunResult.job_id,
                payload: {
                  idempotency_key: `${rerunResult.job_id}:rerun:${Date.now()}`,
                  prompt: values.prompt || undefined,
                  negative_prompt: values.negative_prompt || undefined,
                  asset_ids: values.asset_ids,
                  duration_seconds: values.duration_seconds,
                  mode: values.mode,
                },
              });
            }}
          />
        </div>
      )}
    </section>
  );
}

function ResultGroup({
  group,
  selecting,
  selectedResultId,
  onPreview,
  onSelect,
}: {
  group: ShotResultsRead;
  selecting: boolean;
  selectedResultId: string;
  onPreview: (resultId: string) => void;
  onSelect: (resultId: string) => void;
}) {
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <Typography.Title level={3} style={sectionTitleStyle}>
        {group.shot_id}
      </Typography.Title>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>版本</th>
            <th style={thStyle}>状态</th>
            <th style={thStyle}>来源 URL</th>
            <th style={thStyle}>操作</th>
          </tr>
        </thead>
        <tbody>
          {group.results.map((result) => (
            <tr
              key={result.result_id}
              onClick={(event) => {
                if ((event.target as HTMLElement).closest("button")) {
                  return;
                }
                onPreview(result.result_id);
              }}
              style={result.result_id === selectedResultId ? selectedRowStyle : undefined}
            >
              <td style={tdStyle}>v{result.attempt_number}</td>
              <td style={tdStyle}>
                {group.current_result_id === result.result_id ? <Tag color="success">当前采用</Tag> : <Tag>候选</Tag>}
                {result.local_result_available ? <Tag color="processing">local_result_available</Tag> : <Tag color="warning">local_result_missing</Tag>}
                <Tag color={result.source_url_state === "source_url_expired" ? "warning" : "default"}>
                  {result.source_url_state}
                </Tag>
              </td>
              <td style={tdStyle}>{result.source_url}</td>
              <td style={tdStyle}>
                <Button
                  aria-label={`采用 ${result.result_id}`}
                  disabled={selecting || group.current_result_id === result.result_id}
                  size="small"
                  onClick={() => onSelect(result.result_id)}
                >
                  采用
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultPreview({
  result,
  reviewing,
  onReview,
  onRerun,
}: {
  result: GenerationResultRead;
  reviewing: boolean;
  onReview: (payload: { decision: "passed" | "failed"; failure_category: string; note: string }) => void;
  onRerun: () => void;
}) {
  const previewUrl = result.local_content_url || result.source_url;
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {previewUrl ? (
        <video controls preload="metadata" src={previewUrl} style={videoStyle} />
      ) : (
        <Alert message="本地结果缺失，来源 URL 已过期。可保留记录并创建重跑。" showIcon type="warning" />
      )}
      <Typography.Text>Job {result.job_id}</Typography.Text>
      <Typography.Text type="secondary">Attempt {result.attempt_number}</Typography.Text>
      <Typography.Text type="secondary">Source URL: {result.source_url_state}</Typography.Text>
      <div style={toolbarStyle}>
        <Button onClick={() => onReview({ decision: "passed", failure_category: "", note: "" })} loading={reviewing}>
          标记通过
        </Button>
        <Button
          onClick={() => onReview({ decision: "failed", failure_category: "generation_failed", note: "" })}
          loading={reviewing}
        >
          标记失败
        </Button>
        <Button type="primary" onClick={onRerun}>
          创建重跑
        </Button>
      </div>
    </div>
  );
}

function RerunDrawer({
  assets,
  job,
  loading,
  open,
  onClose,
  onSubmit,
}: {
  assets: Array<{ asset_id: string; name: string; asset_type: string }>;
  job?: { request: { prompt: string; negative_prompt: string; asset_ids: string[]; duration_seconds: number; parameters: Record<string, unknown> } };
  loading: boolean;
  open: boolean;
  onClose: () => void;
  onSubmit: (values: { prompt?: string; negative_prompt?: string; asset_ids?: string[]; duration_seconds?: number; mode?: "std" | "pro" }) => void;
}) {
  return (
    <Drawer
      aria-label="创建 Agnes 重跑"
      destroyOnClose
      onClose={onClose}
      open={open}
      title="创建重跑"
      width={360}
    >
      <section aria-label="创建 Agnes 重跑" aria-modal="true" role="dialog">
        <Form
          key={job?.request.prompt ?? "loading"}
          disabled={loading}
          layout="vertical"
          onFinish={onSubmit}
          initialValues={{
            prompt: job?.request.prompt,
            negative_prompt: job?.request.negative_prompt,
            asset_ids: job?.request.asset_ids,
            duration_seconds: job?.request.duration_seconds,
            mode: job?.request.parameters.mode,
          }}
        >
          <Typography.Paragraph type="secondary">
            当前资产：{job?.request.asset_ids.join(", ") || "-"}
          </Typography.Paragraph>
          <Form.Item label="Prompt override" name="prompt">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="Negative prompt override" name="negative_prompt">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="Asset override" name="asset_ids">
            <Checkbox.Group style={{ display: "grid", gap: 8 }}>
              {assets.map((asset) => (
                <Checkbox key={asset.asset_id} value={asset.asset_id}>
                  {asset.name} / {asset.asset_type} / {asset.asset_id}
                </Checkbox>
              ))}
            </Checkbox.Group>
          </Form.Item>
          <Form.Item label="Duration override" name="duration_seconds">
            <Select
              allowClear
              options={[
                { label: "5 seconds", value: 5 },
                { label: "10 seconds", value: 10 },
              ]}
            />
          </Form.Item>
          <Form.Item label="Mode override" name="mode">
            <Select
              allowClear
              options={[
                { label: "std", value: "std" },
                { label: "pro", value: "pro" },
              ]}
            />
          </Form.Item>
          <Button htmlType="submit" loading={loading} type="primary">
            创建重跑
          </Button>
        </Form>
      </section>
    </Drawer>
  );
}

const headerStyle = { display: "grid", gap: 4 };
const titleStyle = { fontSize: 18, margin: 0 };
const sectionTitleStyle = { fontSize: 16, margin: 0 };
const workspaceGridStyle = { display: "grid", gap: 12, gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 0.8fr)" };
const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};
const tableStyle = { borderCollapse: "collapse" as const, width: "100%" };
const thStyle = { borderBottom: "1px solid #d9dee8", padding: 8, textAlign: "left" as const };
const tdStyle = { borderBottom: "1px solid #eef1f6", padding: 8, verticalAlign: "top" as const };
const selectedRowStyle = { background: "#f5f8ff" };
const toolbarStyle = { display: "flex", flexWrap: "wrap" as const, gap: 8 };
const videoStyle = {
  aspectRatio: "16 / 9",
  background: "#101828",
  borderRadius: 6,
  width: "100%",
};
