import { useQuery } from "@tanstack/react-query";
import { Button, Checkbox, Input, Modal, Select, Tooltip } from "antd";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createSupplierModel,
  deleteSupplierModel,
  getModelTestFeatureStatus,
  listSupplierModels,
  newIdempotencyKey,
  patchSupplierModel,
  type SupplierModelCapability,
  type SupplierModelRead,
  type SupplierRead,
} from "./api";
import { ModelInspector } from "./ModelInspector";
import { hasStoredModelTest, ModelTestDialog } from "./ModelTestDialog";
import { toManagementError, type ManagementError } from "./managementErrors";

const CAPABILITY_LABEL = { text: "文本", image: "图片", video: "视频" } as const;
const REASONING_LABELS = { low: "低", medium: "中", high: "高" } as const;
type ReasoningEffort = keyof typeof REASONING_LABELS;

function modelTestDisabledReason(
  supplier: SupplierRead,
  model: SupplierModelRead,
  restoring: boolean,
): string {
  if (!supplier.enabled) return "请先启用供应商";
  if (!model.enabled) return "请先启用模型";
  if (restoring) return "该模型有正在进行或等待恢复的测试";
  return "";
}

type ModelDraft = {
  displayName: string;
  providerName: string;
  capability: SupplierModelCapability;
  definition: string;
};

const EMPTY_DRAFT: ModelDraft = {
  displayName: "",
  providerName: "",
  capability: "text",
  definition: "{}",
};

function modelEtag(model: SupplierModelRead): string {
  return `"model-${model.supplier_model_id}-${model.entity_revision}"`;
}

export function SupplierModelsPanel({ supplier }: { supplier: SupplierRead }) {
  const [selectedId, setSelectedId] = useState("");
  const [capability, setCapability] = useState<"all" | SupplierModelCapability>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<SupplierModelRead | null>(null);
  const [deleting, setDeleting] = useState<SupplierModelRead | null>(null);
  const [testing, setTesting] = useState<SupplierModelRead | null>(null);
  const [draft, setDraft] = useState<ModelDraft>(EMPTY_DRAFT);
  const [acknowledged, setAcknowledged] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ManagementError | null>(null);
  const models = useQuery({
    queryKey: ["supplier-models", supplier.supplier_id],
    queryFn: () => listSupplierModels(supplier.supplier_id),
  });
  const modelTests = useQuery({
    queryKey: ["model-test-feature-status"],
    queryFn: getModelTestFeatureStatus,
    staleTime: 30_000,
  });
  const catalogEtag = models.data?.etag || `"model-catalog-${supplier.model_catalog_revision}"`;
  const rows = useMemo(
    () =>
      (models.data?.data ?? []).filter(
        (model) => capability === "all" || model.capability === capability,
      ),
    [models.data, capability],
  );
  const selected = (models.data?.data ?? []).find((model) => model.supplier_model_id === selectedId) ?? null;

  useEffect(() => {
    if (testing || !models.data) return;
    const persisted = models.data.data.find(
      (model) => model.capability !== "video" && hasStoredModelTest(model.supplier_model_id),
    );
    if (persisted) setTesting(persisted);
  }, [models.data, testing]);

  function openCreate() {
    setDraft(EMPTY_DRAFT);
    setError(null);
    setCreateOpen(true);
  }

  function openEdit(model: SupplierModelRead) {
    setDraft({
      displayName: model.display_name,
      providerName: model.provider_model_name,
      capability: model.capability,
      definition: JSON.stringify(model.definition, null, 2),
    });
    setAcknowledged(model.binding_count === 0);
    setError(null);
    setEditing(model);
  }

  function definition(): Record<string, unknown> {
    const value = JSON.parse(draft.definition || "{}");
    if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("definition");
    if (supplier.slug === "aixora" && draft.capability === "text") {
      const reasoningEffort = draftReasoningEffort();
      if (!reasoningEffort) throw new Error("INVALID_REASONING_EFFORT");
      const constraints = value.constraints;
      value.constraints = {
        ...(constraints && !Array.isArray(constraints) && typeof constraints === "object"
          ? constraints as Record<string, unknown>
          : {}),
        reasoning_effort: reasoningEffort,
      };
    }
    return value;
  }

  function draftReasoningEffort(): ReasoningEffort | "" {
    try {
      const value = JSON.parse(draft.definition || "{}") as Record<string, unknown>;
      const constraints = value.constraints;
      if (constraints === undefined) return "medium";
      if (!constraints || Array.isArray(constraints) || typeof constraints !== "object") return "";
      const effort = constraints
        ? (constraints as Record<string, unknown>).reasoning_effort
        : undefined;
      if (effort === undefined) return "medium";
      return effort === "low" || effort === "medium" || effort === "high" ? effort : "";
    } catch {
      return "";
    }
  }

  function setDraftReasoningEffort(reasoningEffort: ReasoningEffort) {
    try {
      const value = JSON.parse(draft.definition || "{}") as Record<string, unknown>;
      if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("definition");
      const constraints = value.constraints;
      value.constraints = {
        ...(constraints && !Array.isArray(constraints) && typeof constraints === "object"
          ? constraints as Record<string, unknown>
          : {}),
        reasoning_effort: reasoningEffort,
      };
      setDraft((current) => ({ ...current, definition: JSON.stringify(value, null, 2) }));
      setError(null);
    } catch {
      setError({ code: "INVALID_DEFINITION", message: "请先修复模式与约束 JSON，再调整默认思考深度。" });
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createSupplierModel(
        supplier.supplier_id,
        {
          display_name: draft.displayName,
          provider_model_name: draft.providerName,
          capability: draft.capability,
          definition: definition(),
        },
        catalogEtag,
        newIdempotencyKey("create-model"),
      );
      setCreateOpen(false);
      await models.refetch();
    } catch (caught) {
      setError(caught instanceof Error && caught.message === "INVALID_REASONING_EFFORT"
        ? { code: "INVALID_REASONING_EFFORT", message: "思考深度只支持低、中、高，请修复模式与约束 JSON。" }
        : caught instanceof SyntaxError
          ? { code: "INVALID_DEFINITION", message: "模型约束必须是有效 JSON 对象。" }
          : toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing || (editing.binding_count > 0 && !acknowledged)) return;
    setSaving(true);
    setError(null);
    try {
      await patchSupplierModel(
        editing.supplier_model_id,
        {
          display_name: draft.displayName,
          provider_model_name: draft.providerName,
          capability: draft.capability,
          definition: definition(),
          acknowledged_binding_count: editing.binding_count,
        },
        modelEtag(editing),
        catalogEtag,
      );
      setEditing(null);
      await models.refetch();
    } catch (caught) {
      setError(caught instanceof Error && caught.message === "INVALID_REASONING_EFFORT"
        ? { code: "INVALID_REASONING_EFFORT", message: "思考深度只支持低、中、高，请修复模式与约束 JSON。" }
        : caught instanceof SyntaxError
          ? { code: "INVALID_DEFINITION", message: "模型约束必须是有效 JSON 对象。" }
          : toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function toggle(model: SupplierModelRead) {
    setSaving(true);
    setError(null);
    try {
      await patchSupplierModel(
        model.supplier_model_id,
        { enabled: !model.enabled },
        modelEtag(model),
        catalogEtag,
      );
      await models.refetch();
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!deleting) return;
    setSaving(true);
    setError(null);
    try {
      await deleteSupplierModel(
        deleting.supplier_model_id,
        modelEtag(deleting),
        catalogEtag,
      );
      setDeleting(null);
      await models.refetch();
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function reloadAfterConflict() {
    const refreshed = await models.refetch();
    if (!editing || !refreshed.data) return;
    const current = refreshed.data.data.find(
      (model) => model.supplier_model_id === editing.supplier_model_id,
    );
    if (current) {
      setEditing(current);
      setDraft({
        displayName: current.display_name,
        providerName: current.provider_model_name,
        capability: current.capability,
        definition: JSON.stringify(current.definition, null, 2),
      });
      setAcknowledged(current.binding_count === 0);
    }
  }

  const form = (mode: "create" | "edit") => (
    <form className="management-form" onSubmit={mode === "create" ? create : saveEdit}>
      <label><span>显示名称</span><Input aria-label="显示名称" value={draft.displayName} onChange={(event) => setDraft((current) => ({ ...current, displayName: event.target.value }))} /></label>
      <label><span>供应商模型名</span><Input aria-label="供应商模型名" value={draft.providerName} onChange={(event) => setDraft((current) => ({ ...current, providerName: event.target.value }))} /></label>
      <label><span>能力</span><select aria-label="能力" value={draft.capability} onChange={(event) => setDraft((current) => ({ ...current, capability: event.target.value as SupplierModelCapability }))}><option value="text">文本</option><option value="image">图片</option><option value="video">视频</option></select></label>
      {supplier.slug === "aixora" && draft.capability === "text" ? (
        <label><span>默认思考深度</span><select aria-label="默认思考深度" value={draftReasoningEffort()} onChange={(event) => setDraftReasoningEffort(event.target.value as ReasoningEffort)}>{!draftReasoningEffort() ? <option value="" disabled>无效值，请修复 JSON</option> : null}<option value="low">低</option><option value="medium">中</option><option value="high">高</option></select></label>
      ) : null}
      <label><span>模式与约束 JSON</span><textarea aria-label="模式与约束 JSON" value={draft.definition} onChange={(event) => setDraft((current) => ({ ...current, definition: event.target.value }))} /></label>
      {mode === "edit" && editing?.binding_count ? <Checkbox checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)}>我已确认将影响 {editing.binding_count} 处项目绑定</Checkbox> : null}
      {error ? (
        <div className="management-error" role="alert">
          <strong>{error.message}</strong>
          {error.code === "REVISION_CONFLICT" ? (
            <Button size="small" onClick={() => void reloadAfterConflict()}>重新加载模型</Button>
          ) : null}
        </div>
      ) : null}
      <div className="management-form-actions"><Button onClick={() => mode === "create" ? setCreateOpen(false) : setEditing(null)}>取消</Button><Button htmlType="submit" type="primary" loading={saving} disabled={!draft.displayName || !draft.providerName || (mode === "edit" && Boolean(editing?.binding_count) && !acknowledged)}>{mode === "create" ? "保存新模型" : "保存新版本"}</Button></div>
    </form>
  );

  return (
    <section className="models-workbench" aria-labelledby="models-title">
      <div className="models-main">
        <div className="section-heading">
          <div><h2 id="models-title">模型目录</h2><p>编辑会创建不可变新修订；稳定模型 ID 不变。</p></div>
          <code>{catalogEtag.replace(/"/g, "")}</code>
        </div>
        <div className="models-toolbar">
          <Button type="primary" onClick={openCreate}>新增模型</Button>
          <Select aria-label="能力筛选" value={capability} onChange={setCapability} options={[{ value: "all", label: "能力：全部" }, { value: "text", label: "文本" }, { value: "image", label: "图片" }, { value: "video", label: "视频" }]} />
        </div>
        {models.isPending ? <div className="management-loading">正在加载模型…</div> : null}
        {models.isError ? <div className="management-error" role="alert"><strong>{toManagementError(models.error).message}</strong></div> : null}
        {error && !createOpen && !editing ? <div className="management-error" role="alert"><strong>{error.message}</strong>{error.code === "REVISION_CONFLICT" ? <Button size="small" onClick={() => void reloadAfterConflict()}>重新加载模型</Button> : null}</div> : null}
        {models.data && !rows.length ? <div className="management-empty">当前筛选下没有模型。</div> : null}
        {rows.length ? (
          <div className="model-table-scroll">
            <table className="model-table">
              <thead><tr><th>显示名称</th><th>供应商模型名</th><th>能力</th><th>来源</th><th>版本 / 修订</th><th>启用状态</th><th>操作</th></tr></thead>
              <tbody>{rows.map((model) => {
                const restoring =
                  testing?.supplier_model_id === model.supplier_model_id
                  || hasStoredModelTest(model.supplier_model_id);
                const testDisabledReason = modelTestDisabledReason(supplier, model, restoring);
                return <tr key={model.supplier_model_id} className={selectedId === model.supplier_model_id ? "selected" : ""}><td>{model.display_name}</td><td><code>{model.provider_model_name}</code></td><td>{CAPABILITY_LABEL[model.capability]}</td><td>{model.source === "built_in" ? "内置" : "Overlay"}</td><td>r{model.revision}</td><td>{model.enabled ? "已启用" : "已停用"}</td><td><div className="row-actions"><Button size="small" aria-label={`查看 ${model.display_name}`} onClick={() => setSelectedId(model.supplier_model_id)}>查看</Button><Button size="small" aria-label={`编辑 ${model.display_name}`} onClick={() => openEdit(model)}>编辑</Button><Button size="small" aria-label={`${model.enabled ? "停用" : "启用"} ${model.display_name}`} disabled={saving} onClick={() => void toggle(model)}>{model.enabled ? "停用" : "启用"}</Button><Button size="small" danger aria-label={`删除 ${model.display_name}`} disabled={model.source === "built_in" || model.binding_count > 0} onClick={() => setDeleting(model)}>删除</Button>{modelTests.data?.enabled && model.capability !== "video" ? <Tooltip title={testDisabledReason}><span><Button size="small" aria-label={`测试 ${model.display_name}`} disabled={Boolean(testDisabledReason)} onClick={() => setTesting(model)}>测试</Button></span></Tooltip> : null}</div></td></tr>;
              })}</tbody>
            </table>
          </div>
        ) : null}
      </div>
      <ModelInspector model={selected} />
      <Modal title="新增模型" open={createOpen} footer={null} onCancel={() => setCreateOpen(false)} destroyOnHidden>{form("create")}</Modal>
      <Modal title="编辑模型并保存新版本" open={Boolean(editing)} footer={null} onCancel={() => setEditing(null)} destroyOnHidden>{editing ? form("edit") : null}</Modal>
      <Modal title="确认删除模型" open={Boolean(deleting)} onCancel={() => setDeleting(null)} onOk={() => void remove()} okText="确认删除模型" cancelText="取消" okButtonProps={{ danger: true }} confirmLoading={saving} destroyOnHidden><p>没有历史引用的模型会永久删除；已有测试或任务历史的模型会归档并从可选列表隐藏。</p></Modal>
      {testing ? <ModelTestDialog supplier={supplier} model={testing} open onClose={() => setTesting(null)} /> : null}
    </section>
  );
}
