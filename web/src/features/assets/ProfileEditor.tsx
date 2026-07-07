import { Button, Input, Typography } from "antd";
import type { FormEvent } from "react";
import { useState } from "react";
import type { ProductionProfileCreate, ProfileType } from "./api";

type ProfileEditorProps = {
  disabled?: boolean;
  onSubmit: (payload: ProductionProfileCreate) => void;
  chapterId: string;
};

const profileTypeOptions: ProfileType[] = ["character", "scene", "prop", "style"];

export function ProfileEditor({ chapterId, disabled = false, onSubmit }: ProfileEditorProps) {
  const [profileType, setProfileType] = useState<ProfileType>("character");
  const [name, setName] = useState("");
  const [continuityNotes, setContinuityNotes] = useState("");
  const [identityNotes, setIdentityNotes] = useState("");
  const [appearanceNotes, setAppearanceNotes] = useState("");
  const [costumeNotes, setCostumeNotes] = useState("");
  const [layoutNotes, setLayoutNotes] = useState("");
  const [lightingNotes, setLightingNotes] = useState("");
  const [propHandlingNotes, setPropHandlingNotes] = useState("");
  const [styleRules, setStyleRules] = useState("");
  const [cinematographyRules, setCinematographyRules] = useState("");
  const [colorRules, setColorRules] = useState("");
  const [negativeRules, setNegativeRules] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildPayload();
    if (!name.trim() || !continuityNotes.trim()) {
      return;
    }
    onSubmit({
      chapter_id: chapterId,
      profile_type: profileType,
      payload,
    });
  }

  function buildPayload() {
    const base = {
      name,
      continuity_notes: continuityNotes,
    };
    if (profileType === "character") {
      return {
        ...base,
        identity_notes: identityNotes,
        appearance_notes: appearanceNotes,
        costume_notes: costumeNotes,
      };
    }
    if (profileType === "scene") {
      return {
        ...base,
        scene_layout_notes: layoutNotes,
        lighting_notes: lightingNotes,
      };
    }
    if (profileType === "prop") {
      return {
        ...base,
        prop_handling_notes: propHandlingNotes,
      };
    }
    return {
      ...base,
      style_rules: styleRules,
      cinematography_rules: cinematographyRules,
      color_rules: colorRules,
      negative_rules: negativeRules,
    };
  }

  return (
    <form aria-label="生产资料编辑" onSubmit={submit} style={panelStyle}>
      <Typography.Title level={2} style={sectionTitleStyle}>
        生产资料
      </Typography.Title>
      <label style={fieldStyle}>
        <span>资料类型</span>
        <select
          aria-label="资料类型"
          disabled={disabled}
          onChange={(event) => setProfileType(event.target.value as ProfileType)}
          value={profileType}
        >
          {profileTypeOptions.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <label style={fieldStyle}>
        <span>资料名称</span>
        <Input
          aria-label="资料名称"
          disabled={disabled}
          onChange={(event) => setName(event.target.value)}
          value={name}
        />
      </label>
      <label style={fieldStyle}>
        <span>连续性说明</span>
        <Input.TextArea
          aria-label="连续性说明"
          autoSize={{ minRows: 2 }}
          disabled={disabled}
          onChange={(event) => setContinuityNotes(event.target.value)}
          value={continuityNotes}
        />
      </label>
      {profileType === "character" ? (
        <>
          <label style={fieldStyle}>
            <span>身份说明</span>
            <Input.TextArea
              aria-label="身份说明"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setIdentityNotes(event.target.value)}
              value={identityNotes}
            />
          </label>
          <label style={fieldStyle}>
            <span>外貌说明</span>
            <Input.TextArea
              aria-label="外貌说明"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setAppearanceNotes(event.target.value)}
              value={appearanceNotes}
            />
          </label>
          <label style={fieldStyle}>
            <span>服装说明</span>
            <Input.TextArea
              aria-label="服装说明"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setCostumeNotes(event.target.value)}
              value={costumeNotes}
            />
          </label>
        </>
      ) : null}
      {profileType === "scene" ? (
        <>
          <label style={fieldStyle}>
            <span>布局说明</span>
            <Input.TextArea
              aria-label="布局说明"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setLayoutNotes(event.target.value)}
              value={layoutNotes}
            />
          </label>
          <label style={fieldStyle}>
            <span>光线说明</span>
            <Input.TextArea
              aria-label="光线说明"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setLightingNotes(event.target.value)}
              value={lightingNotes}
            />
          </label>
        </>
      ) : null}
      {profileType === "prop" ? (
        <label style={fieldStyle}>
          <span>道具使用说明</span>
          <Input.TextArea
            aria-label="道具使用说明"
            autoSize={{ minRows: 2 }}
            disabled={disabled}
            onChange={(event) => setPropHandlingNotes(event.target.value)}
            value={propHandlingNotes}
          />
        </label>
      ) : null}
      {profileType === "style" ? (
        <>
          <label style={fieldStyle}>
            <span>风格规则</span>
            <Input.TextArea
              aria-label="风格规则"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setStyleRules(event.target.value)}
              value={styleRules}
            />
          </label>
          <label style={fieldStyle}>
            <span>摄影规则</span>
            <Input.TextArea
              aria-label="摄影规则"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setCinematographyRules(event.target.value)}
              value={cinematographyRules}
            />
          </label>
          <label style={fieldStyle}>
            <span>色彩规则</span>
            <Input.TextArea
              aria-label="色彩规则"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setColorRules(event.target.value)}
              value={colorRules}
            />
          </label>
          <label style={fieldStyle}>
            <span>反向规则</span>
            <Input.TextArea
              aria-label="反向规则"
              autoSize={{ minRows: 2 }}
              disabled={disabled}
              onChange={(event) => setNegativeRules(event.target.value)}
              value={negativeRules}
            />
          </label>
        </>
      ) : null}
      <div>
        <Button disabled={disabled} htmlType="submit" type="primary">
          创建资料
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
