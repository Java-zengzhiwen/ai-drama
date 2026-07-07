import { Button, Input, Typography } from "antd";
import type { FormEvent } from "react";
import { useState } from "react";
import type { AssetGenerateImageRequest, AssetType, BindingTargetType } from "./api";

type AssetGeneratorProps = {
  disabled?: boolean;
  onSubmit: (payload: AssetGenerateImageRequest) => void;
};

const assetTypes: AssetType[] = [
  "character_reference",
  "character_outfit",
  "scene_reference",
  "scene_angle",
  "prop_reference",
  "shot_keyframe",
];
const refTypes: BindingTargetType[] = ["character", "scene", "prop", "shot"];

export function AssetGenerator({ disabled = false, onSubmit }: AssetGeneratorProps) {
  const [assetType, setAssetType] = useState<AssetType>("character_reference");
  const [name, setName] = useState("");
  const [refType, setRefType] = useState<BindingTargetType>("character");
  const [prompt, setPrompt] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !prompt.trim()) {
      return;
    }
    onSubmit({
      asset_type: assetType,
      name,
      prompt,
      size: "1024x1024",
      input_asset_ids: [],
      input_images: [],
      metadata: {
        ref_type: refType,
      },
    });
  }

  return (
    <form aria-label="Agnes 图片请求" onSubmit={submit} style={panelStyle}>
      <Typography.Title level={2} style={sectionTitleStyle}>
        Agnes 图片请求
      </Typography.Title>
      <label style={fieldStyle}>
        <span>Agnes 资产类型</span>
        <select
          aria-label="Agnes 资产类型"
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
        <span>Agnes 资产名称</span>
        <Input
          aria-label="Agnes 资产名称"
          disabled={disabled}
          onChange={(event) => setName(event.target.value)}
          value={name}
        />
      </label>
      <label style={fieldStyle}>
        <span>参考类型</span>
        <select
          aria-label="参考类型"
          disabled={disabled}
          onChange={(event) => setRefType(event.target.value as BindingTargetType)}
          value={refType}
        >
          {refTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <label style={fieldStyle}>
        <span>Agnes 提示词</span>
        <Input.TextArea
          aria-label="Agnes 提示词"
          autoSize={{ minRows: 3 }}
          disabled={disabled}
          onChange={(event) => setPrompt(event.target.value)}
          value={prompt}
        />
      </label>
      <div>
        <Button disabled={disabled} htmlType="submit" type="primary">
          请求 Agnes 图片
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
