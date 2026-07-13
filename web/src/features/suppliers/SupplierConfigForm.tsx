import { Button, Input } from "antd";
import { FormEvent, useEffect, useState } from "react";
import { saveSupplierConfig, type SupplierInput, type SupplierRead } from "./api";
import { toManagementError, type ManagementError } from "./managementErrors";

function fieldKey(field: SupplierInput): string {
  return String(field.key ?? field.name ?? field.id ?? "");
}

function fieldLabel(field: SupplierInput, key: string): string {
  return String(field.label ?? key.replace(/_/g, " "));
}

function configFields(supplier: SupplierRead): SupplierInput[] {
  const manifestFields = supplier.inputs.filter((field) => fieldKey(field));
  if (manifestFields.length) return manifestFields;
  return Object.keys(supplier.config_values).map((key) => ({
    key,
    label: key.replace(/_/g, " "),
    type: key.includes("url") || key.includes("endpoint") ? "url" : "text",
  }));
}

function validate(values: Record<string, string>): ManagementError | null {
  for (const [key, value] of Object.entries(values)) {
    if ((key === "base_url" || key.endsWith("_endpoint")) && value) {
      try {
        if (new URL(value).protocol !== "https:") throw new Error("not https");
      } catch {
        return {
          code: "INVALID_BASE_URL",
          message: key === "base_url" ? "Base URL 必须使用 HTTPS。" : `${key} 必须使用 HTTPS。`,
        };
      }
    }
  }
  return null;
}

export function SupplierConfigForm({
  supplier,
  onReload,
}: {
  supplier: SupplierRead;
  onReload: () => Promise<unknown>;
}) {
  const [values, setValues] = useState<Record<string, string>>(supplier.config_values);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ManagementError | null>(null);
  const [success, setSuccess] = useState("");
  const fields = configFields(supplier);

  useEffect(() => setValues(supplier.config_values), [supplier.current_config_revision_id]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const validation = validate(values);
    if (validation) {
      setError(validation);
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess("");
    try {
      await saveSupplierConfig(
        supplier.supplier_id,
        values,
        `"config-${supplier.config_revision}"`,
      );
      setSuccess("配置已保存为新版本。");
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="management-form supplier-section" onSubmit={submit}>
      <div className="section-heading">
        <div>
          <h2>配置</h2>
          <p>普通配置与密钥分开保存。字段来自当前供应商清单。</p>
        </div>
        <code>config-{supplier.config_revision}</code>
      </div>
      {fields.length ? (
        <div className="config-grid">
          {fields.map((field) => {
            const key = fieldKey(field);
            const label = fieldLabel(field, key);
            return (
              <label key={key}>
                <span>{label}</span>
                <Input
                  aria-label={label}
                  required={Boolean(field.required)}
                  placeholder={typeof field.placeholder === "string" ? field.placeholder : undefined}
                  value={values[key] ?? supplier.input_values[key] ?? ""}
                  onChange={(event) =>
                    setValues((current) => ({ ...current, [key]: event.target.value }))
                  }
                />
                {field.description ? <small>{String(field.description)}</small> : null}
              </label>
            );
          })}
        </div>
      ) : (
        <div className="management-empty">当前清单没有可编辑的普通配置字段。</div>
      )}
      {error ? (
        <div className="management-error" role="alert">
          <strong>{error.message}</strong>
          {error.code === "REVISION_CONFLICT" ? (
            <Button size="small" onClick={() => void onReload()}>
              重新加载
            </Button>
          ) : null}
        </div>
      ) : null}
      {success ? <div className="management-success" role="status">{success}</div> : null}
      <div className="management-form-actions">
        <Button htmlType="submit" type="primary" loading={saving} disabled={!fields.length}>
          保存配置
        </Button>
      </div>
    </form>
  );
}
