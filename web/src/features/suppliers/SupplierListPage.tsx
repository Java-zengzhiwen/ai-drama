import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Input, Modal, Tag } from "antd";
import { FormEvent, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { createSupplier, listSuppliers, newIdempotencyKey, updateSupplier, type SupplierRead } from "./api";
import { toManagementError } from "./managementErrors";

const CAPABILITY_LABEL: Record<string, string> = {
  text: "文本",
  image: "图片",
  video: "视频",
};

function LocalManagementError({ error, onReload }: { error: unknown; onReload?: () => void }) {
  const normalized = toManagementError(error);
  const lines = normalized.message.split("\n");
  return (
    <div className="management-error" role="alert">
      <strong>{lines[0]}</strong>
      {lines.slice(1).map((line) => (
        <p key={line}>{line}</p>
      ))}
      {normalized.code === "REVISION_CONFLICT" && onReload ? (
        <Button size="small" onClick={onReload}>重新加载供应商</Button>
      ) : null}
    </div>
  );
}

function SupplierRow({ supplier, onToggle, toggling }: { supplier: SupplierRead; onToggle: () => void; toggling: boolean }) {
  const capabilities = supplier.capabilities.map((item) => CAPABILITY_LABEL[item] ?? item);
  return (
    <div className="supplier-row">
      <span className="supplier-mark" aria-hidden="true">
        {supplier.display_name.slice(0, 1).toUpperCase()}
      </span>
      <Link className="supplier-row-main" to={`/suppliers/${supplier.supplier_id}`}>
        <strong>{supplier.display_name}</strong>
        <small>
          {supplier.source === "built_in" ? "内置" : "自定义"}
          {supplier.author ? ` · ${supplier.author}` : ""}
          {supplier.version ? ` · ${supplier.version}` : ""}
        </small>
      </Link>
      <span className="supplier-row-meta">
        <span>{capabilities.length ? capabilities.join(" · ") : "暂无能力"}</span>
        <span>{supplier.model_count} 个模型</span>
      </span>
      <span className="supplier-row-meta">
        <span>{supplier.base_url_summary || "未配置 Base URL"}</span>
        <span>supplier-{supplier.revision} · config-{supplier.config_revision} · catalog-{supplier.model_catalog_revision}</span>
      </span>
      <span className="supplier-row-actions">
        <span>{supplier.enabled ? "已启用" : "已停用"}</span>
        <span>
          {supplier.credential.configured
            ? `已配置 ····${supplier.credential.masked_suffix}`
            : "未配置密钥"}
        </span>
        <Button
          size="small"
          aria-label={`${supplier.enabled ? "停用" : "启用"} ${supplier.display_name}`}
          loading={toggling}
          onClick={onToggle}
        >
          {supplier.enabled ? "停用" : "启用"}
        </Button>
      </span>
    </div>
  );
}

export function SupplierListPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [slug, setSlug] = useState("");
  const nameInput = useRef<import("antd").InputRef>(null);
  const suppliers = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });
  const create = useMutation({
    mutationFn: () =>
      createSupplier(
        { slug: slug.trim(), display_name: displayName.trim() },
        newIdempotencyKey("create-supplier"),
      ),
    onSuccess: async () => {
      setDialogOpen(false);
      setDisplayName("");
      setSlug("");
      await queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });
  const toggle = useMutation({
    mutationFn: (supplier: SupplierRead) =>
      updateSupplier(
        supplier.supplier_id,
        { enabled: !supplier.enabled },
        `"supplier-${supplier.revision}"`,
      ),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (displayName.trim() && slug.trim()) create.mutate();
  }

  return (
    <section className="management-page" aria-labelledby="supplier-list-title">
      <div className="management-page-heading">
        <div>
          <Tag color="blue">仅本地管理</Tag>
          <h1 id="supplier-list-title">模型供应商</h1>
          <p>在一个地方管理供应商、适配代码、模型和项目路由。</p>
        </div>
        <Button type="primary" onClick={() => setDialogOpen(true)}>
          新增供应商
        </Button>
      </div>

      {suppliers.isPending ? <div className="management-loading">正在加载供应商…</div> : null}
      {suppliers.isError ? <LocalManagementError error={suppliers.error} /> : null}
      {suppliers.data?.length === 0 ? (
        <div className="management-empty">
          <strong>尚未配置供应商</strong>
          <p>新建一个空模板，然后添加配置、适配代码和模型。</p>
        </div>
      ) : null}
      {suppliers.data?.length ? (
        <div className="supplier-list" aria-label="供应商列表">
          <div className="supplier-list-header">
            <span>供应商</span>
            <span>能力与模型</span>
            <span>连接与修订</span>
            <span>状态</span>
          </div>
          {suppliers.data.map((supplier) => (
            <SupplierRow
              key={supplier.supplier_id}
              supplier={supplier}
              toggling={toggle.isPending && toggle.variables?.supplier_id === supplier.supplier_id}
              onToggle={() => toggle.mutate(supplier)}
            />
          ))}
          {toggle.isError ? <LocalManagementError error={toggle.error} onReload={() => void suppliers.refetch()} /> : null}
        </div>
      ) : null}

      <Modal
        title="新增自定义供应商"
        open={dialogOpen}
        footer={null}
        onCancel={() => setDialogOpen(false)}
        afterOpenChange={(open) => {
          if (open) nameInput.current?.focus();
        }}
        destroyOnHidden
      >
        <form className="management-form" onSubmit={submit}>
          <label>
            <span>供应商名称</span>
            <Input
              aria-label="供应商名称"
              ref={nameInput}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </label>
          <label>
            <span>供应商标识</span>
            <Input
              aria-label="供应商标识"
              pattern="[a-z0-9][a-z0-9\\-]{0,63}"
              value={slug}
              onChange={(event) => setSlug(event.target.value)}
            />
          </label>
          {create.isError ? <LocalManagementError error={create.error} /> : null}
          <div className="management-form-actions">
            <Button onClick={() => setDialogOpen(false)}>取消</Button>
            <Button htmlType="submit" type="primary" loading={create.isPending}>
              创建空模板
            </Button>
          </div>
        </form>
      </Modal>
    </section>
  );
}
