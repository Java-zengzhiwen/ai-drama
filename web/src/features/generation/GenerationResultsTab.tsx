import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Skeleton, Tag, Typography } from "antd";
import type { ChapterRead } from "../projects/api";
import {
  listGenerationResults,
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
  const resultsQuery = useQuery({
    queryKey: resultsQueryKey,
    queryFn: () => listGenerationResults(chapter.chapter_id),
  });
  const selectMutation = useMutation({
    mutationFn: ({ shotId, resultId }: { shotId: string; resultId: string }) =>
      selectGenerationResult(shotId, resultId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: resultsQueryKey }),
  });
  const groups = resultsQuery.data ?? [];
  const selectedGroup = groups[0];
  const selectedResult = selectedGroup?.results[0];

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

      {resultsQuery.isError || selectMutation.isError ? (
        <Alert message="结果加载或选择失败。请重试。" showIcon type="error" />
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
                onSelect={(resultId) => selectMutation.mutate({ shotId: group.shot_id, resultId })}
              />
            ))}
          </section>
          <section aria-label="video result preview" style={panelStyle}>
            <Typography.Title level={3} style={sectionTitleStyle}>
              视频预览
            </Typography.Title>
            {selectedResult ? (
              <ResultPreview result={selectedResult} />
            ) : (
              <Typography.Text type="secondary">选择一个结果后预览。</Typography.Text>
            )}
          </section>
        </div>
      )}
    </section>
  );
}

function ResultGroup({
  group,
  selecting,
  onSelect,
}: {
  group: ShotResultsRead;
  selecting: boolean;
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
            <tr key={result.result_id}>
              <td style={tdStyle}>v{result.attempt_number}</td>
              <td style={tdStyle}>
                {group.current_result_id === result.result_id ? <Tag color="success">当前采用</Tag> : <Tag>候选</Tag>}
                {result.local_result_available ? <Tag color="processing">local_result_available</Tag> : <Tag color="warning">local_result_missing</Tag>}
              </td>
              <td style={tdStyle}>{result.source_url}</td>
              <td style={tdStyle}>
                <Button
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

function ResultPreview({ result }: { result: GenerationResultRead }) {
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <video controls preload="metadata" src={result.source_url} style={videoStyle} />
      <Typography.Text>Job {result.job_id}</Typography.Text>
      <Typography.Text type="secondary">Attempt {result.attempt_number}</Typography.Text>
      <Button>创建重跑</Button>
    </div>
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
const videoStyle = {
  aspectRatio: "16 / 9",
  background: "#101828",
  borderRadius: 6,
  width: "100%",
};
