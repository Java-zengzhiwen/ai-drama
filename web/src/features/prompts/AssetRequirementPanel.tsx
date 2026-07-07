import { Alert, Button, Skeleton, Tag, Typography } from "antd";
import type { AssetRequirementNeed, AssetRequirementSetRead, AssetRequirementShotRow } from "./api";

type AssetRequirementPanelProps = {
  disabled?: boolean;
  error?: unknown;
  isAnalyzing: boolean;
  isLoading: boolean;
  onAnalyze: () => void;
  onOpenAssets?: () => void;
  requirements?: AssetRequirementSetRead;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

export function AssetRequirementPanel({
  disabled = false,
  error,
  isAnalyzing,
  isLoading,
  onAnalyze,
  onOpenAssets,
  requirements,
}: AssetRequirementPanelProps) {
  if (isLoading) {
    return <Skeleton active paragraph={{ rows: 5 }} />;
  }

  const details = error ? getApiErrorDetails(error, "资产需求加载失败。请重新分析。") : null;

  return (
    <section aria-label="资产需求" style={panelStyle}>
      <div style={toolbarStyle}>
        <div>
          <Typography.Title level={2} style={sectionTitleStyle}>
            资产需求
          </Typography.Title>
          <Typography.Text type="secondary">
            按镜头检查人物、服装、场景、道具和 shot_keyframe 需求。
          </Typography.Text>
        </div>
        <Button disabled={disabled} loading={isAnalyzing} onClick={onAnalyze}>
          重新分析资产需求
        </Button>
      </div>

      {details ? (
        <Alert description={details.code || undefined} message={details.message} showIcon type="warning" />
      ) : null}

      {!requirements ? (
        <Typography.Text type="secondary">暂无资产需求。请先重新分析资产需求。</Typography.Text>
      ) : (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <Tag color={requirements.status === "ready" ? "success" : "warning"}>{requirements.status}</Tag>
            <Typography.Text type="secondary">Storyboard {requirements.storyboard_revision_id}</Typography.Text>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table aria-label="Asset requirement rows" style={tableStyle}>
              <thead style={{ background: "#f9fafc" }}>
                <tr>
                  <th style={tableHeaderStyle}>shot_id</th>
                  <th style={tableHeaderStyle}>状态</th>
                  <th style={tableHeaderStyle}>ready</th>
                  <th style={tableHeaderStyle}>missing_assets</th>
                  <th style={tableHeaderStyle}>asset_generation_in_progress</th>
                  <th style={tableHeaderStyle}>asset_review_required</th>
                  <th style={tableHeaderStyle}>操作</th>
                </tr>
              </thead>
              <tbody>
                {requirements.shot_rows.map((row) => (
                  <tr key={row.shot_id}>
                    <td style={tableCellStyle}>{row.shot_id}</td>
                    <td style={tableCellStyle}>
                      <Tag color={row.status === "ready" ? "success" : "warning"}>{row.status}</Tag>
                    </td>
                    <td style={tableCellStyle}>{formatNeeds(row.ready)}</td>
                    <td style={tableCellStyle}>{formatNeeds(row.missing_assets)}</td>
                    <td style={tableCellStyle}>{formatNeeds(row.asset_generation_in_progress)}</td>
                    <td style={tableCellStyle}>{formatNeeds(row.asset_review_required)}</td>
                    <td style={tableCellStyle}>
                      {row.status === "ready" ? (
                        <Typography.Text type="secondary">已满足</Typography.Text>
                      ) : (
                        <RequirementGuidance onOpenAssets={onOpenAssets} row={row} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function RequirementGuidance({
  onOpenAssets,
  row,
}: {
  onOpenAssets?: () => void;
  row: AssetRequirementShotRow;
}) {
  return (
    <div style={{ display: "grid", gap: 4 }}>
      {row.missing_assets.length > 0 ? (
        <Typography.Text>缺失资产，请先去资料与资产创建或绑定。</Typography.Text>
      ) : null}
      {row.asset_generation_in_progress.length > 0 ? (
        <Typography.Text>等待生成完成，或去资料与资产查看生成中的资产。</Typography.Text>
      ) : null}
      {row.asset_review_required.length > 0 ? (
        <Typography.Text>去资料与资产审核、标记可用或重绑资产。</Typography.Text>
      ) : null}
      <Button onClick={onOpenAssets} size="small" type="link">
        去资料与资产创建或绑定
      </Button>
    </div>
  );
}

function formatNeeds(needs: AssetRequirementNeed[]) {
  if (needs.length === 0) {
    return "-";
  }
  return (
    <div style={{ display: "grid", gap: 4 }}>
      {needs.map((need) => (
        <Typography.Text key={`${need.need_type}:${need.target_id}:${need.asset_id ?? ""}`}>
          {need.need_type} / {need.asset_type} / {need.target_id}
          {need.asset_id ? ` / ${need.asset_id}` : ""}
        </Typography.Text>
      ))}
    </div>
  );
}

function getApiErrorDetails(error: unknown, fallbackMessage: string) {
  const data = (error as ApiError | undefined)?.response?.data;
  return {
    code: data?.error_code ?? "",
    message: data?.error_message ?? fallbackMessage,
  };
}

const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};

const toolbarStyle = {
  alignItems: "start",
  display: "flex",
  flexWrap: "wrap" as const,
  gap: 12,
  justifyContent: "space-between",
};

const sectionTitleStyle = {
  fontSize: 16,
  margin: 0,
};

const tableStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderCollapse: "collapse" as const,
  minWidth: 980,
  width: "100%",
};

const tableHeaderStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#5f6b7a",
  fontSize: 12,
  fontWeight: 600,
  padding: "10px 12px",
  textAlign: "left" as const,
  verticalAlign: "top" as const,
};

const tableCellStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#1f2937",
  maxWidth: 260,
  padding: "10px 12px",
  verticalAlign: "top" as const,
};
