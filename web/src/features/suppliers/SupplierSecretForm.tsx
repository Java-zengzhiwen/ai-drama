import { Button, Checkbox, Input, Modal } from "antd";
import { FormEvent, useEffect, useState } from "react";
import {
  deleteSupplierSecret,
  saveSupplierSecret,
  type SupplierCredentialStatus,
  type SupplierRead,
} from "./api";
import { toManagementError, type ManagementError } from "./managementErrors";

export function SupplierSecretForm({ supplier }: { supplier: SupplierRead }) {
  const [credential, setCredential] = useState("");
  const [visible, setVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [forceAcknowledged, setForceAcknowledged] = useState(false);
  const [status, setStatus] = useState<SupplierCredentialStatus>(supplier.credential);
  const [credentialRevision, setCredentialRevision] = useState(supplier.credential_revision);
  const [error, setError] = useState<ManagementError | null>(null);

  useEffect(() => {
    setStatus(supplier.credential);
    setCredentialRevision(supplier.credential_revision);
  }, [supplier.current_credential_version_id, supplier.credential_revision]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!credential) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await saveSupplierSecret(
        supplier.supplier_id,
        credential,
        `"credential-${credentialRevision}"`,
      );
      setStatus(saved.data);
      setCredentialRevision((current) => current + 1);
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setCredential("");
      setVisible(false);
      setSaving(false);
    }
  }

  async function remove() {
    setSaving(true);
    setError(null);
    try {
      const deleted = await deleteSupplierSecret(
        supplier.supplier_id,
        `"credential-${credentialRevision}"`,
        supplier.credential_active_job_count > 0,
      );
      setStatus(deleted.data);
      setCredentialRevision((current) => current + 1);
      setDeleteOpen(false);
      setForceAcknowledged(false);
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setCredential("");
      setVisible(false);
      setSaving(false);
    }
  }

  return (
    <section className="supplier-section" aria-labelledby="secret-title">
      <div className="section-heading">
        <div>
          <h2 id="secret-title">密钥</h2>
          <p>密钥只写入本机安全存储，保存后不会被浏览器读回。</p>
        </div>
        <code>credential-{credentialRevision}</code>
      </div>
      <div className="credential-status">
        <span className={status.configured ? "status-dot enabled" : "status-dot"} />
        {status.configured
          ? `已配置 ····${status.masked_suffix}`
          : "尚未配置 API Key"}
      </div>
      <form className="management-form" onSubmit={submit}>
        <label>
          <span>新的 API Key</span>
          <Input
            aria-label="新的 API Key"
            autoComplete="new-password"
            type={visible ? "text" : "password"}
            value={credential}
            onChange={(event) => setCredential(event.target.value)}
          />
        </label>
        <div className="credential-actions">
          <Button
            aria-label={visible ? "隐藏未保存的密钥" : "显示未保存的密钥"}
            disabled={!credential}
            onClick={() => setVisible((current) => !current)}
          >
            {visible ? "隐藏" : "显示"}
          </Button>
          <Button htmlType="submit" type="primary" disabled={credential.length < 8} loading={saving}>
            保存密钥
          </Button>
          <Button danger disabled={!status.configured} onClick={() => { setForceAcknowledged(false); setDeleteOpen(true); }}>
            删除密钥
          </Button>
        </div>
      </form>
      {error ? <div className="management-error" role="alert"><strong>{error.message}</strong></div> : null}
      <Modal
        title="确认删除密钥"
        open={deleteOpen}
        onCancel={() => { setDeleteOpen(false); setForceAcknowledged(false); }}
        onOk={() => void remove()}
        okText="确认删除"
        cancelText="取消"
        okButtonProps={{
          danger: true,
          loading: saving,
          disabled: supplier.credential_active_job_count > 0 && !forceAcknowledged,
        }}
        destroyOnHidden
      >
        {supplier.credential_active_job_count > 0 ? (
          <>
            <p>
              当前密钥仍被 {supplier.credential_active_job_count} 个活动任务引用。强制删除会取消尚未提交的任务，
              并将已提交或轮询中的任务标记为 credential_revoked；供应商侧任务不会被重新提交。
            </p>
            <Checkbox checked={forceAcknowledged} onChange={(event) => setForceAcknowledged(event.target.checked)}>
              我已确认强制删除对这 {supplier.credential_active_job_count} 个活动任务的影响
            </Checkbox>
          </>
        ) : (
          <p>删除后无法恢复。后续任务和重新运行将无法解析此密钥。</p>
        )}
      </Modal>
    </section>
  );
}
