import { Button, Modal } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  getSupplierCode,
  restoreBuiltinSupplier,
  saveSupplierCode,
  type SupplierRead,
} from "./api";
import { toManagementError, type ManagementError } from "./managementErrors";

export function SupplierCodeEditor({
  supplier,
  supplierEtag,
  onReload,
}: {
  supplier: SupplierRead;
  supplierEtag: string;
  onReload: () => Promise<unknown>;
}) {
  const [source, setSource] = useState("");
  const [versionId, setVersionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [error, setError] = useState<ManagementError | null>(null);
  const [success, setSuccess] = useState("");
  const lineNumbers = useMemo(
    () => Array.from({ length: Math.max(1, source.split("\n").length) }, (_, index) => index + 1),
    [source],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    void getSupplierCode(supplier.supplier_id)
      .then((value) => {
        if (!active) return;
        setSource(value.source);
        setVersionId(value.supplier_version_id);
      })
      .catch((caught) => active && setError(toManagementError(caught)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [supplier.supplier_id, supplier.current_supplier_version_id]);

  async function save() {
    setSaving(true);
    setError(null);
    setSuccess("");
    try {
      const saved = await saveSupplierCode(supplier.supplier_id, source, supplierEtag);
      setVersionId(saved.data.supplier_version_id);
      setSuccess(`已保存不可变版本 ${saved.data.supplier_version_id}`);
      await onReload();
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function restore() {
    setSaving(true);
    setError(null);
    try {
      await restoreBuiltinSupplier(supplier.supplier_id, supplierEtag);
      setRestoreOpen(false);
      await onReload();
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="supplier-section code-section" aria-labelledby="code-title">
      <div className="section-heading">
        <div>
          <h2 id="code-title">适配代码</h2>
          <p>本地校验并保存为不可变版本；此操作不会调用供应商。</p>
        </div>
        <code>{versionId || "未保存版本"}</code>
      </div>
      {loading ? <div className="management-loading">正在加载代码…</div> : (
        <div className="code-editor-shell">
          <pre className="code-line-numbers" aria-label="代码行号">
            {lineNumbers.join("\n")}
          </pre>
          <textarea
            aria-label="TypeScript 供应商适配代码"
            className="code-editor"
            spellCheck={false}
            value={source}
            onChange={(event) => setSource(event.target.value)}
          />
        </div>
      )}
      {error ? (
        <div className="management-error" role="alert">
          <strong>
            {error.line
              ? `第 ${error.line} 行，第 ${error.column ?? 0} 列：${error.message}`
              : error.message}
          </strong>
          {error.code === "REVISION_CONFLICT" ? (
            <Button size="small" onClick={() => void onReload()}>重新加载</Button>
          ) : null}
        </div>
      ) : null}
      {success ? <div className="management-success" role="status">{success}</div> : null}
      <div className="management-form-actions">
        {supplier.source === "built_in" ? (
          <Button onClick={() => setRestoreOpen(true)}>恢复内置版本</Button>
        ) : null}
        <Button type="primary" loading={saving} disabled={loading || !source.trim()} onClick={() => void save()}>
          校验并保存
        </Button>
      </div>
      <Modal
        title="恢复内置版本"
        open={restoreOpen}
        onCancel={() => setRestoreOpen(false)}
        onOk={() => void restore()}
        okText="确认恢复"
        cancelText="取消"
        confirmLoading={saving}
        destroyOnHidden
      >
        <p>恢复只切换当前内置版本指针，历史版本和已创建任务不会被删除。</p>
      </Modal>
    </section>
  );
}
