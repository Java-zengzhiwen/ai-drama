import { Alert, Input, Typography } from "antd";
import { useEffect, useState } from "react";

export type CanonicalShot = {
  scene_id: string;
  shot_id: string;
  shot_order: number;
  source_scene_reference: string;
  duration_seconds: number;
  shot_size: string;
  camera_angle: string;
  camera_movement: unknown;
  visual_composition: unknown;
  character_positions: unknown;
  character_actions: unknown;
  emotion_performance: unknown;
  dialogue: unknown;
  continuity_in: unknown;
  continuity_out: unknown;
  [key: string]: unknown;
};

type ShotEditorProps = {
  disabled: boolean;
  onChange: (field: keyof CanonicalShot, value: unknown) => void;
  onJsonValidityChange: (field: keyof CanonicalShot, isValid: boolean) => void;
  resetKey: string;
  shot?: CanonicalShot;
};

const scalarFields: Array<keyof CanonicalShot> = [
  "shot_order",
  "duration_seconds",
  "shot_size",
  "camera_angle",
];

const jsonFields: Array<keyof CanonicalShot> = [
  "camera_movement",
  "visual_composition",
  "character_positions",
  "character_actions",
  "emotion_performance",
  "dialogue",
  "continuity_in",
  "continuity_out",
];

export function ShotEditor({ disabled, onChange, onJsonValidityChange, resetKey, shot }: ShotEditorProps) {
  const [jsonDrafts, setJsonDrafts] = useState<Record<string, string>>({});
  const [invalidFields, setInvalidFields] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!shot) {
      setJsonDrafts({});
      setInvalidFields(new Set());
      return;
    }
    setJsonDrafts(
      Object.fromEntries(jsonFields.map((field) => [String(field), formatJsonValue(shot[field])])),
    );
    setInvalidFields(new Set());
    jsonFields.forEach((field) => onJsonValidityChange(field, true));
  }, [onJsonValidityChange, resetKey]);

  if (!shot) {
    return <Typography.Text type="secondary">选择一个 shot 后编辑 canonical fields。</Typography.Text>;
  }

  function updateJsonField(field: keyof CanonicalShot, value: string) {
    setJsonDrafts((current) => ({ ...current, [String(field)]: value }));
    try {
      const parsed = JSON.parse(value);
      setInvalidFields((current) => {
        const next = new Set(current);
        next.delete(String(field));
        return next;
      });
      onJsonValidityChange(field, true);
      onChange(field, parsed);
    } catch {
      setInvalidFields((current) => {
        const next = new Set(current);
        next.add(String(field));
        return next;
      });
      onJsonValidityChange(field, false);
    }
  }

  return (
    <section aria-label="shot inspector" style={{ display: "grid", gap: 12 }}>
      <div>
        <Typography.Text strong>{shot.shot_id}</Typography.Text>
        <br />
        <Typography.Text type="secondary">保留 canonical field names 保存为新 revision。</Typography.Text>
      </div>

      {scalarFields.map((field) => (
        <label key={String(field)} style={fieldLayoutStyle}>
          <span>{field}</span>
          <Input
            aria-label={String(field)}
            disabled={disabled}
            onChange={(event) => {
              const value = event.target.value;
              onChange(
                field,
                field === "shot_order" || field === "duration_seconds" ? Number(value) : value,
              );
            }}
            type={field === "shot_order" || field === "duration_seconds" ? "number" : "text"}
            value={shot[field] as string | number}
          />
        </label>
      ))}

      {jsonFields.map((field) => {
        const value = shot[field];
        const isInvalidJsonScalar = invalidFields.has(String(field));
        return (
          <label key={String(field)} style={fieldLayoutStyle}>
            <span>{field}</span>
            <Input.TextArea
              aria-label={String(field)}
              autoSize={{ minRows: 3 }}
              disabled={disabled}
              onChange={(event) => updateJsonField(field, event.target.value)}
              value={jsonDrafts[String(field)] ?? formatJsonValue(value)}
            />
            {isInvalidJsonScalar ? (
              <Alert message={`${String(field)} 不是有效 JSON。`} showIcon type="warning" />
            ) : null}
          </label>
        );
      })}
    </section>
  );
}

function formatJsonValue(value: unknown) {
  if (typeof value === "string" && !isProbablyJson(value)) {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function isProbablyJson(value: string) {
  const trimmed = value.trim();
  return trimmed === "null" || trimmed.startsWith("{") || trimmed.startsWith("[") || trimmed.startsWith('"');
}

const fieldLayoutStyle = {
  display: "grid",
  gap: 6,
};
