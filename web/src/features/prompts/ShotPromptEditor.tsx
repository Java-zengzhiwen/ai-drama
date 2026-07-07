import { Button, Input, Typography } from "antd";
import type { AgnesPreviewRead, ShotPromptShot } from "./api";

type ShotPromptEditorProps = {
  disabled?: boolean;
  onChange: (field: "positive_prompt" | "negative_prompt", value: string) => void;
  onOpenAsset?: (assetId: string) => void;
  preview?: AgnesPreviewRead;
  shot?: ShotPromptShot;
};

export function ShotPromptEditor({
  disabled = false,
  onChange,
  onOpenAsset,
  preview,
  shot,
}: ShotPromptEditorProps) {
  if (!shot) {
    return <Typography.Text type="secondary">选择一个 shot 后编辑 Shot Prompt。</Typography.Text>;
  }

  return (
    <section aria-label="shot prompt inspector" style={{ display: "grid", gap: 12 }}>
      <div>
        <Typography.Text strong>{shot.shot_id}</Typography.Text>
        <br />
        <Typography.Text type="secondary">编辑后保存会提交完整 canonical JSON。</Typography.Text>
      </div>

      <label style={fieldLayoutStyle}>
        <span>positive_prompt</span>
        <Input.TextArea
          aria-label="positive_prompt"
          autoSize={{ minRows: 5 }}
          disabled={disabled}
          onChange={(event) => onChange("positive_prompt", event.target.value)}
          value={shot.positive_prompt}
        />
      </label>

      <label style={fieldLayoutStyle}>
        <span>negative_prompt</span>
        <Input.TextArea
          aria-label="negative_prompt"
          autoSize={{ minRows: 3 }}
          disabled={disabled}
          onChange={(event) => onChange("negative_prompt", event.target.value)}
          value={shot.negative_prompt}
        />
      </label>

      <ReadonlyBlock title="continuity_notes" value={shot.continuity_notes} />
      <AssetRefsPreview assetRefs={shot.asset_refs} onOpenAsset={onOpenAsset} />
      <ReadonlyBlock title="Agnes 参数预览" value={preview?.agnes_video_params ?? shot.agnes_video_params} />
      <ReadonlyBlock title="源 storyboard shot" value={shot.source_storyboard_shot ?? { shot_id: shot.shot_id }} />

      {preview ? (
        <section aria-label="Agnes preview" style={subPanelStyle}>
          <Typography.Title level={3} style={smallTitleStyle}>
            Agnes 请求预览
          </Typography.Title>
          <ReadonlyBlock title="preview_asset_refs" value={preview.asset_refs} />
          <ReadonlyBlock title="preview_positive_prompt" value={preview.positive_prompt} />
          <ReadonlyBlock title="preview_negative_prompt" value={preview.negative_prompt} />
        </section>
      ) : null}
    </section>
  );
}

export function AssetRefsPreview({
  assetRefs,
  onOpenAsset,
}: {
  assetRefs: string[];
  onOpenAsset?: (assetId: string) => void;
}) {
  return (
    <section aria-label="asset_refs" style={subPanelStyle}>
      <Typography.Text strong>asset_refs</Typography.Text>
      {assetRefs.length === 0 ? (
        <Typography.Text type="secondary">暂无资产引用。</Typography.Text>
      ) : (
        <div style={assetRefGridStyle}>
          {assetRefs.map((assetId) => (
            <div key={assetId} style={assetRefCardStyle}>
              <img
                alt={`${assetId} 引用预览`}
                src={`/api/assets/${assetId}/content`}
                style={assetThumbStyle}
              />
              <Typography.Text style={{ fontSize: 12 }} title={assetId}>
                {assetId}
              </Typography.Text>
              <Button onClick={() => onOpenAsset?.(assetId)} size="small" type="link">
                查看资产 {assetId}
              </Button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ReadonlyBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <section style={subPanelStyle}>
      <Typography.Text strong>{title}</Typography.Text>
      <pre style={preStyle}>{formatValue(value)}</pre>
    </section>
  );
}

function formatValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value ?? null, null, 2);
}

const fieldLayoutStyle = {
  display: "grid",
  gap: 6,
};

const subPanelStyle = {
  background: "#f9fafc",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 6,
  padding: 10,
};

const smallTitleStyle = {
  fontSize: 14,
  margin: 0,
};

const assetRefGridStyle = {
  display: "grid",
  gap: 8,
  gridTemplateColumns: "repeat(auto-fit, minmax(132px, 1fr))",
};

const assetRefCardStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 6,
  minWidth: 0,
  padding: 8,
};

const assetThumbStyle = {
  aspectRatio: "16 / 10",
  background: "#edf1f7",
  border: "1px solid #d9dee8",
  borderRadius: 4,
  objectFit: "cover" as const,
  width: "100%",
};

const preStyle = {
  margin: 0,
  maxHeight: 180,
  overflow: "auto",
  whiteSpace: "pre-wrap" as const,
  wordBreak: "break-word" as const,
};
