import { useQuery } from "@tanstack/react-query";
import { Button, Tag } from "antd";
import { Suspense, useState, type KeyboardEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getSupplier, listSuppliers } from "./api";
import { SupplierConfigForm } from "./SupplierConfigForm";
import { LazySupplierCodeEditor } from "./SupplierCodeEditor.lazy";
import { SupplierSecretForm } from "./SupplierSecretForm";
import { SupplierModelsPanel } from "./SupplierModelsPanel";
import { toManagementError } from "./managementErrors";

type Section = "overview" | "config" | "secret" | "code" | "models";
const SECTIONS: { key: Section; label: string }[] = [
  { key: "overview", label: "概览" },
  { key: "config", label: "配置" },
  { key: "secret", label: "密钥" },
  { key: "code", label: "适配代码" },
  { key: "models", label: "模型" },
];

function ErrorState({ error }: { error: unknown }) {
  const normalized = toManagementError(error);
  return <div className="management-error" role="alert"><strong>{normalized.message.split("\n")[0]}</strong>{normalized.message.split("\n").slice(1).map((line) => <p key={line}>{line}</p>)}</div>;
}

export function SupplierDetailPage() {
  const { supplierId = "" } = useParams();
  const navigate = useNavigate();
  const [section, setSection] = useState<Section>("models");
  const suppliers = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });
  const detail = useQuery({
    queryKey: ["supplier", supplierId],
    queryFn: () => getSupplier(supplierId),
    enabled: Boolean(supplierId),
  });

  if (detail.isPending) return <div className="management-loading">正在加载供应商…</div>;
  if (detail.isError) return <ErrorState error={detail.error} />;
  const supplier = detail.data.data;
  const etagLabel = detail.data.etag.replace(/"/g, "");

  function selectAdjacentTab(event: KeyboardEvent<HTMLButtonElement>, current: Section) {
    const index = SECTIONS.findIndex((item) => item.key === current);
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % SECTIONS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + SECTIONS.length) % SECTIONS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = SECTIONS.length - 1;
    else return;
    event.preventDefault();
    const key = SECTIONS[next].key;
    setSection(key);
    document.getElementById(`supplier-tab-${key}`)?.focus();
  }

  return (
    <section className="supplier-workbench" aria-labelledby="supplier-title">
      <aside className="supplier-rail" aria-label="供应商导航">
        <div className="supplier-rail-heading">
          <Link to="/suppliers">模型供应商</Link>
        </div>
        {suppliers.data?.map((item) => (
          <Link
            key={item.supplier_id}
            className={item.supplier_id === supplierId ? "active" : ""}
            to={`/suppliers/${item.supplier_id}`}
          >
            <span>{item.display_name}</span>
            <small>{item.enabled ? "已启用" : "已停用"}</small>
          </Link>
        ))}
        <label className="supplier-mobile-select">
          <span>当前供应商</span>
          <select
            aria-label="切换供应商"
            value={supplierId}
            onChange={(event) => navigate(`/suppliers/${event.target.value}`)}
          >
            {suppliers.data?.map((item) => (
              <option key={item.supplier_id} value={item.supplier_id}>
                {item.display_name}{item.enabled ? "" : "（已停用）"}
              </option>
            ))}
          </select>
        </label>
      </aside>
      <main className="supplier-command">
        <header className="supplier-command-header">
          <div>
            <div className="supplier-title-line">
              <span className="supplier-mark inline" aria-hidden="true">{supplier.display_name.slice(0, 1)}</span>
              <h1 id="supplier-title">{supplier.display_name}</h1>
              <Tag color={supplier.enabled ? "green" : "default"}>{supplier.enabled ? "已启用" : "已停用"}</Tag>
              <Tag>{supplier.source === "built_in" ? "仅本地 · 内置" : "仅本地 · 自定义"}</Tag>
            </div>
            <p>{supplier.author || "本地"}{supplier.version ? ` · ${supplier.version}` : ""}</p>
          </div>
          <div className="revision-state">
            <span className="status-dot enabled" />
            <span>无冲突</span>
            <code>ETag: {etagLabel}</code>
          </div>
        </header>
        <div className="supplier-tabs" role="tablist" aria-label="供应商管理分区">
          {SECTIONS.map((item) => (
            <button
              key={item.key}
              id={`supplier-tab-${item.key}`}
              role="tab"
              aria-selected={section === item.key}
              aria-controls={`supplier-panel-${item.key}`}
              tabIndex={section === item.key ? 0 : -1}
              onClick={() => setSection(item.key)}
              onKeyDown={(event) => selectAdjacentTab(event, item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div
          id={`supplier-panel-${section}`}
          className="supplier-section-host"
          role="tabpanel"
          aria-labelledby={`supplier-tab-${section}`}
          tabIndex={0}
        >
          {section === "overview" ? (
            <section className="supplier-section">
              <div className="section-heading"><div><h2>供应商概览</h2><p>当前配置、能力与不可变版本状态。</p></div></div>
              <dl className="overview-grid">
                <div><dt>能力</dt><dd>{supplier.capabilities.join(" · ") || "尚未声明"}</dd></div>
                <div><dt>模型数量</dt><dd>{supplier.model_count}</dd></div>
                <div><dt>Base URL</dt><dd>{supplier.base_url_summary || "尚未配置"}</dd></div>
                <div><dt>API Key</dt><dd>{supplier.credential.configured ? `已配置 ····${supplier.credential.masked_suffix}` : "未配置"}</dd></div>
              </dl>
            </section>
          ) : null}
          {section === "config" ? <SupplierConfigForm supplier={supplier} onReload={detail.refetch} /> : null}
          {section === "secret" ? <SupplierSecretForm supplier={supplier} onReload={detail.refetch} /> : null}
          {section === "code" ? (
            <Suspense fallback={<div className="management-loading">正在加载编辑器…</div>}>
              <LazySupplierCodeEditor supplier={supplier} supplierEtag={detail.data.etag} onReload={detail.refetch} />
            </Suspense>
          ) : null}
          {section === "models" ? <SupplierModelsPanel supplier={supplier} /> : null}
        </div>
      </main>
      <aside className="supplier-inspector" aria-label="供应商检查器">
        <h2>供应商详情</h2>
        <dl>
          <dt>supplier_id</dt><dd><code>{supplier.supplier_id}</code></dd>
          <dt>当前版本</dt><dd><code>{supplier.current_supplier_version_id || "未保存"}</code></dd>
          <dt>配置修订</dt><dd>config-{supplier.config_revision}</dd>
          <dt>模型目录</dt><dd>model-catalog-{supplier.model_catalog_revision}</dd>
        </dl>
        <Button onClick={() => void detail.refetch()}>刷新当前状态</Button>
      </aside>
    </section>
  );
}
