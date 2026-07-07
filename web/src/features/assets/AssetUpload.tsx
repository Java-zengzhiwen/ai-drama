import { Button, Input, Typography } from "antd";
import type { FormEvent } from "react";
import { useState } from "react";
import type { AssetType } from "./api";

type AssetUploadProps = {
  disabled?: boolean;
  onSubmit: (payload: FormData) => void;
};

const assetTypes: AssetType[] = [
  "character_reference",
  "character_outfit",
  "scene_reference",
  "scene_angle",
  "prop_reference",
  "shot_keyframe",
];

export function AssetUpload({ disabled = false, onSubmit }: AssetUploadProps) {
  const [assetType, setAssetType] = useState<AssetType>("character_reference");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !file) {
      return;
    }
    const formData = new FormData();
    formData.append("asset_type", assetType);
    formData.append("name", name);
    formData.append("metadata", "{}");
    formData.append("file", file);
    onSubmit(formData);
  }

  return (
    <form aria-label="资产上传" onSubmit={submit} style={panelStyle}>
      <Typography.Title level={2} style={sectionTitleStyle}>
        上传资产
      </Typography.Title>
      <label style={fieldStyle}>
        <span>上传资产类型</span>
        <select
          aria-label="上传资产类型"
          disabled={disabled}
          onChange={(event) => setAssetType(event.target.value as AssetType)}
          value={assetType}
        >
          {assetTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <label style={fieldStyle}>
        <span>上传资产名称</span>
        <Input
          aria-label="上传资产名称"
          disabled={disabled}
          onChange={(event) => setName(event.target.value)}
          value={name}
        />
      </label>
      <label style={fieldStyle}>
        <span>资产文件</span>
        <input
          aria-label="资产文件"
          disabled={disabled}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          type="file"
        />
      </label>
      <div>
        <Button disabled={disabled} htmlType="submit" type="primary">
          上传资产
        </Button>
      </div>
    </form>
  );
}

const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};

const fieldStyle = {
  display: "grid",
  gap: 6,
};

const sectionTitleStyle = {
  fontSize: 16,
  margin: 0,
};
