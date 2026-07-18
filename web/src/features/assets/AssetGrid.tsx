import { Button, Card, Drawer, Input, Tag, Typography } from "antd";
import type { FormEvent } from "react";
import { useState } from "react";
import type {
  AssetBindingCreate,
  AssetBindingRead,
  AssetRead,
  BindingTargetType,
  ProductionProfileRead,
} from "./api";

type AssetGridProps = {
  assets: AssetRead[];
  disabled?: boolean;
  onBind: (assetId: string, payload: AssetBindingCreate) => void;
  onMarkUsable: (assetId: string) => void;
  onReject: (assetId: string, reason: string) => void;
  profiles: ProductionProfileRead[];
};

export function AssetGrid({
  assets,
  disabled = false,
  onBind,
  onMarkUsable,
  onReject,
  profiles,
}: AssetGridProps) {
  const [metadataAsset, setMetadataAsset] = useState<AssetRead | null>(null);
  const [inspectedAsset, setInspectedAsset] = useState<AssetRead | null>(null);

  if (assets.length === 0) {
    return <Typography.Text type="secondary">暂无资产。上传图片或请求 Agnes 图片后会显示在这里。</Typography.Text>;
  }

  return (
    <>
      <div aria-label="资产网格" style={gridStyle}>
        {assets.map((asset) => (
          <AssetCard
            asset={asset}
            disabled={disabled}
            key={asset.asset_id}
            onBind={onBind}
            onInspect={setInspectedAsset}
            onMarkUsable={onMarkUsable}
            onOpenMetadata={setMetadataAsset}
            onReject={onReject}
            profiles={profiles}
          />
        ))}
      </div>
      <AssetInspector
        asset={inspectedAsset}
        assets={assets}
        onClose={() => setInspectedAsset(null)}
      />
      <Drawer
        className="asset-metadata-drawer"
        destroyOnClose
        onClose={() => setMetadataAsset(null)}
        open={Boolean(metadataAsset)}
        title={metadataAsset ? `${metadataAsset.name} metadata` : "metadata"}
        width={420}
      >
        {metadataAsset ? (
          <pre style={metadataStyle}>{JSON.stringify(metadataAsset.metadata ?? {}, null, 2)}</pre>
        ) : null}
      </Drawer>
    </>
  );
}

function AssetCard({
  asset,
  disabled,
  onBind,
  onInspect,
  onMarkUsable,
  onOpenMetadata,
  onReject,
  profiles,
}: {
  asset: AssetRead;
  disabled: boolean;
  onBind: (assetId: string, payload: AssetBindingCreate) => void;
  onInspect: (asset: AssetRead) => void;
  onMarkUsable: (assetId: string) => void;
  onOpenMetadata: (asset: AssetRead) => void;
  onReject: (assetId: string, reason: string) => void;
  profiles: ProductionProfileRead[];
}) {
  const [targetType, setTargetType] = useState<BindingTargetType>("character");
  const [targetId, setTargetId] = useState(profiles.find((profile) => profile.profile_type === "character")?.profile_id ?? "");
  const [role, setRole] = useState("primary_reference");
  const [isCurrent, setIsCurrent] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const targetProfiles = profiles.filter((profile) => profile.profile_type === targetType);
  const canUseProfileSelect = targetType !== "shot";
  const binding = primaryBinding(asset);
  const markUsableDisabled = disabled || asset.status === "generating" || asset.status === "usable";
  const rejectDisabled = disabled || asset.status === "generating";
  const currentDisabled = disabled || asset.status !== "usable";
  const bindDisabled = disabled || (isCurrent && asset.status !== "usable");

  function submitBinding(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!targetId.trim() || !role.trim() || (isCurrent && asset.status !== "usable")) {
      return;
    }
    onBind(asset.asset_id, {
      target_type: targetType,
      target_id: targetId,
      role,
      is_current: isCurrent,
    });
  }

  function submitRejection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (asset.status === "generating") {
      return;
    }
    onReject(asset.asset_id, rejectReason);
  }

  function updateTargetType(value: BindingTargetType) {
    setTargetType(value);
    const firstProfile = profiles.find((profile) => profile.profile_type === value);
    setTargetId(firstProfile?.profile_id ?? "");
  }

  return (
    <Card
      aria-label={`资产 ${asset.name}`}
      styles={{ body: { display: "grid", gap: 12, padding: 12 } }}
      style={{ borderRadius: 6 }}
    >
      <div style={thumbnailWrapStyle}>
        <img
          alt={`${asset.name} 缩略图`}
          src={`/api/assets/${asset.asset_id}/content`}
          style={thumbnailStyle}
        />
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        <Typography.Text strong>{asset.name}</Typography.Text>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          <Tag>{asset.asset_type}</Tag>
          <Tag color={statusColor(asset.status)}>{asset.status}</Tag>
          <Tag>{asset.source_type}</Tag>
          {binding ? (
            <>
              <Tag color="processing">{`${binding.target_type}:${binding.target_id}`}</Tag>
              {binding.is_current ? <Tag color="success">当前采用</Tag> : null}
            </>
          ) : (
            <Tag>未绑定</Tag>
          )}
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <Button disabled={markUsableDisabled} onClick={() => onMarkUsable(asset.asset_id)}>
          标记可用
        </Button>
        <Button disabled={disabled} onClick={() => onInspect(asset)}>
          查看大图
        </Button>
        <Button disabled={disabled} onClick={() => onOpenMetadata(asset)}>
          查看 metadata
        </Button>
      </div>
      <form aria-label={`${asset.name} 绑定`} onSubmit={submitBinding} style={inlineFormStyle}>
        <label style={fieldStyle}>
          <span>绑定目标类型</span>
          <select
            aria-label="绑定目标类型"
            disabled={disabled}
            onChange={(event) => updateTargetType(event.target.value as BindingTargetType)}
            value={targetType}
          >
            {(["character", "scene", "prop", "shot"] as BindingTargetType[]).map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <label style={fieldStyle}>
          <span>绑定目标</span>
          {canUseProfileSelect ? (
            <select
              aria-label="绑定目标"
              disabled={disabled}
              onChange={(event) => setTargetId(event.target.value)}
              value={targetId}
            >
              <option value="">选择资料</option>
              {targetProfiles.map((profile) => (
                <option key={profile.profile_id} value={profile.profile_id}>
                  {profile.name}
                </option>
              ))}
            </select>
          ) : (
            <Input
              aria-label="绑定目标"
              disabled={disabled}
              onChange={(event) => setTargetId(event.target.value)}
              value={targetId}
            />
          )}
        </label>
        <label style={fieldStyle}>
          <span>绑定角色</span>
          <Input
            aria-label="绑定角色"
            disabled={disabled}
            onChange={(event) => setRole(event.target.value)}
            value={role}
          />
        </label>
        <label style={{ alignItems: "center", display: "flex", gap: 8 }}>
          <input
            aria-label="设为当前绑定"
            checked={isCurrent}
            disabled={currentDisabled}
            onChange={(event) => setIsCurrent(event.target.checked)}
            type="checkbox"
          />
          <span>设为当前</span>
        </label>
        <div>
          <Button disabled={bindDisabled} htmlType="submit">
            绑定资产
          </Button>
        </div>
      </form>
      <form aria-label={`${asset.name} 拒绝`} onSubmit={submitRejection} style={inlineFormStyle}>
        <label style={fieldStyle}>
          <span>拒绝原因</span>
          <Input
            aria-label="拒绝原因"
            disabled={rejectDisabled}
            onChange={(event) => setRejectReason(event.target.value)}
            value={rejectReason}
          />
        </label>
        <div>
          <Button disabled={rejectDisabled} htmlType="submit">
            拒绝资产
          </Button>
        </div>
      </form>
    </Card>
  );
}

function AssetInspector({
  asset,
  assets,
  onClose,
}: {
  asset: AssetRead | null;
  assets: AssetRead[];
  onClose: () => void;
}) {
  const relatedAssets = asset ? assets.filter((candidate) => sameVersionFamily(candidate, asset)) : [];
  return (
    <Drawer
      className="asset-detail-drawer"
      destroyOnClose
      onClose={onClose}
      open={Boolean(asset)}
      title={asset ? `资产详情：${asset.name}` : "资产详情"}
      width={520}
    >
      {asset ? (
        <div className="asset-detail-layout">
          <section aria-label="资产主预览" className="asset-main-preview" style={largePreviewWrapStyle}>
            <img
              alt={`${asset.name} 大图预览`}
              src={`/api/assets/${asset.asset_id}/content`}
              style={largePreviewStyle}
            />
          </section>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            <Tag>{asset.asset_type}</Tag>
            <Tag color={statusColor(asset.status)}>{asset.status}</Tag>
            <Tag>{asset.source_type}</Tag>
            {primaryBinding(asset)?.is_current ? <Tag color="success">当前采用</Tag> : null}
          </div>
          <section aria-label="版本与采用列表" style={{ display: "grid", gap: 8 }}>
            <Typography.Title level={2} style={{ fontSize: 16, margin: 0 }}>
              版本与采用
            </Typography.Title>
            <div aria-label="资产版本历史" className="asset-version-strip" role="list" style={versionStripStyle}>
              {relatedAssets.map((candidate) => (
                <div aria-label={`版本 ${candidate.name}`} key={candidate.asset_id} role="listitem" style={versionItemStyle}>
                  <img
                    alt={`${candidate.name} 版本缩略图`}
                    src={`/api/assets/${candidate.asset_id}/content`}
                    style={versionThumbStyle}
                  />
                  <Typography.Text strong>{candidate.name}</Typography.Text>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    <Tag color={statusColor(candidate.status)}>{candidate.status}</Tag>
                    {primaryBinding(candidate)?.is_current ? <Tag color="success">当前采用</Tag> : null}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </Drawer>
  );
}

function primaryBinding(asset: AssetRead) {
  const bindings = asset.bindings ?? [];
  return bindings.find((binding) => binding.is_current) ?? bindings[0];
}

function sameVersionFamily(left: AssetRead, right: AssetRead) {
  const leftBinding = primaryBinding(left);
  const rightBinding = primaryBinding(right);
  if (leftBinding && rightBinding) {
    return (
      leftBinding.target_type === rightBinding.target_type &&
      leftBinding.target_id === rightBinding.target_id &&
      leftBinding.role === rightBinding.role
    );
  }
  return left.asset_type === right.asset_type;
}

function statusColor(status: AssetRead["status"]) {
  if (status === "usable") {
    return "success";
  }
  if (status === "rejected" || status === "failed") {
    return "error";
  }
  if (status === "generating") {
    return "processing";
  }
  return "default";
}

const gridStyle = {
  display: "grid",
  gap: 12,
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
};

const thumbnailWrapStyle = {
  aspectRatio: "4 / 3",
  background: "#f4f6fa",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  overflow: "hidden",
};

const thumbnailStyle = {
  display: "block",
  height: "100%",
  objectFit: "cover" as const,
  width: "100%",
};

const largePreviewWrapStyle = {
  aspectRatio: "16 / 10",
  background: "#f4f6fa",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  overflow: "hidden",
};

const largePreviewStyle = {
  display: "block",
  height: "100%",
  objectFit: "contain" as const,
  width: "100%",
};

const versionStripStyle = {
  display: "grid",
  gap: 8,
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
};

const versionItemStyle = {
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 6,
  padding: 8,
};

const versionThumbStyle = {
  aspectRatio: "4 / 3",
  background: "#f4f6fa",
  display: "block",
  objectFit: "cover" as const,
  width: "100%",
};

const inlineFormStyle = {
  borderTop: "1px solid #edf0f5",
  display: "grid",
  gap: 8,
  paddingTop: 10,
};

const fieldStyle = {
  display: "grid",
  gap: 6,
};

const metadataStyle = {
  background: "#f9fafc",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  margin: 0,
  overflow: "auto",
  padding: 12,
  whiteSpace: "pre-wrap" as const,
};
