import { useQuery } from "@tanstack/react-query";
import { Button, Tag } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getModelResolution,
  getProject,
  getProjectModelBindings,
  saveProjectModelBindings,
  type ModelCapability,
  type ModelResolution,
} from "./api";
import { listSupplierModels, listSuppliers, type SupplierModelRead, type SupplierRead } from "../suppliers/api";
import { toManagementError, type ManagementError } from "../suppliers/managementErrors";

const CAPABILITY_LABEL: Record<ModelCapability, string> = { text: "文本", image: "图片", video: "视频" };
const OPERATIONS: { key: string; label: string; capability: ModelCapability }[] = [
  { key: "source_segmentation", label: "原文拆分", capability: "text" },
  { key: "script_adaptation", label: "剧本改编", capability: "text" },
  { key: "material_extraction", label: "资料拆分", capability: "text" },
  { key: "character_bible", label: "人物设定", capability: "text" },
  { key: "scene_bible", label: "场景设定", capability: "text" },
  { key: "prop_bible", label: "道具设定", capability: "text" },
  { key: "storyboard_design", label: "分镜设计", capability: "text" },
  { key: "visual_anchor_planning", label: "视觉锚点规划", capability: "text" },
  { key: "image_prompt_generation", label: "图片提示词", capability: "text" },
  { key: "shot_prompt_generation", label: "镜头提示词", capability: "text" },
  { key: "character_reference_image", label: "人物参考图", capability: "image" },
  { key: "scene_reference_image", label: "场景参考图", capability: "image" },
  { key: "prop_reference_image", label: "道具参考图", capability: "image" },
  { key: "storyboard_keyframe_image", label: "分镜关键帧", capability: "image" },
  { key: "shot_video_generation", label: "镜头视频生成", capability: "video" },
];

type ModelOption = { supplier: SupplierRead; model: SupplierModelRead };
type Preview = { value?: ModelResolution; error?: ManagementError };

export function ProjectModelBindingsPage() {
  const { projectId = "" } = useParams();
  const [defaults, setDefaults] = useState<Record<ModelCapability, string>>({ text: "", image: "", video: "" });
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [bindingEtag, setBindingEtag] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ManagementError | null>(null);
  const [success, setSuccess] = useState("");
  const [preview, setPreview] = useState<Record<string, Preview>>({});
  const [previewing, setPreviewing] = useState(false);

  const project = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId), enabled: Boolean(projectId) });
  const bindings = useQuery({ queryKey: ["project-model-bindings", projectId], queryFn: () => getProjectModelBindings(projectId), enabled: Boolean(projectId) });
  const catalog = useQuery({
    queryKey: ["project-model-options"],
    queryFn: async () => {
      const supplierRows = await listSuppliers();
      const modelRows = await Promise.all(
        supplierRows.map(async (supplier) => ({ supplier, models: (await listSupplierModels(supplier.supplier_id)).data })),
      );
      return modelRows.flatMap(({ supplier, models }) => models.map((model) => ({ supplier, model })));
    },
  });

  useEffect(() => {
    if (!bindings.data) return;
    setDefaults(bindings.data.data.defaults);
    setOverrides(bindings.data.data.operation_overrides);
    setBindingEtag(bindings.data.etag);
  }, [bindings.data]);

  const selectable = useMemo(
    () => (catalog.data ?? []).filter(({ supplier, model }) => Boolean(supplier.enabled) && Boolean(model.enabled)),
    [catalog.data],
  );

  function options(capability: ModelCapability) {
    return selectable.filter(({ model }) => model.capability === capability);
  }

  function optionLabel(option: ModelOption) {
    return `${option.supplier.display_name} / ${option.model.display_name}`;
  }

  async function save() {
    setSaving(true);
    setError(null);
    setSuccess("");
    try {
      const saved = await saveProjectModelBindings(
        projectId,
        { defaults, operation_overrides: Object.fromEntries(Object.entries(overrides).filter(([, value]) => value)) },
        bindingEtag,
      );
      setBindingEtag(saved.etag);
      setSuccess("项目模型配置已保存；只影响未来创建的任务。" );
    } catch (caught) {
      setError(toManagementError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function refreshPreview() {
    setPreviewing(true);
    const entries = await Promise.all(
      OPERATIONS.map(async (operation) => {
        try {
          return [operation.key, { value: await getModelResolution(projectId, operation.key) }] as const;
        } catch (caught) {
          return [operation.key, { error: toManagementError(caught) }] as const;
        }
      }),
    );
    setPreview(Object.fromEntries(entries));
    setPreviewing(false);
  }

  if (project.isPending || bindings.isPending || catalog.isPending) return <div className="management-loading">正在加载项目模型配置…</div>;
  if (project.isError || bindings.isError || catalog.isError || !project.data || !bindings.data) {
    const caught = project.error ?? bindings.error ?? catalog.error;
    return <div className="management-error" role="alert"><strong>{toManagementError(caught).message}</strong></div>;
  }

  return (
    <section className="binding-workbench" aria-labelledby="binding-title">
      <header className="binding-header">
        <div>
          <Tag color="blue">项目模型路由</Tag>
          <h1 id="binding-title">项目模型配置</h1>
          <p><Link to={`/projects/${projectId}`}>{project.data.name}</Link> · 配置默认模型和步骤覆盖。</p>
        </div>
        <code>{bindingEtag.replace(/"/g, "")}</code>
      </header>
      <div className="binding-warning" role="note">
        <strong>配置变更只影响未来任务。</strong>
        <span>现有 queued/submitted/polling 任务继续使用创建时快照。</span>
      </div>
      <section className="binding-section" aria-labelledby="defaults-title">
        <div className="section-heading"><div><h2 id="defaults-title">默认模型</h2><p>每种能力最多选择一个项目默认模型。</p></div></div>
        <div className="binding-defaults">
          {(["text", "image", "video"] as ModelCapability[]).map((capability) => (
            <label key={capability}>
              <span>默认{CAPABILITY_LABEL[capability]}模型</span>
              <select aria-label={`默认${CAPABILITY_LABEL[capability]}模型`} value={defaults[capability]} onChange={(event) => setDefaults((current) => ({ ...current, [capability]: event.target.value }))}>
                <option value="">未配置</option>
                {options(capability).map((option) => <option key={option.model.supplier_model_id} value={option.model.supplier_model_id}>{optionLabel(option)}</option>)}
              </select>
            </label>
          ))}
        </div>
        <p className="no-fallback">不自动回退：未配置时任务将明确阻塞。</p>
      </section>
      <section className="binding-section" aria-labelledby="overrides-title">
        <div className="section-heading"><div><h2 id="overrides-title">步骤覆盖</h2><p>留空表示继承同能力的项目默认模型。</p></div><Button loading={previewing} onClick={() => void refreshPreview()}>刷新解析预览</Button></div>
        <div className="binding-operations">
          {OPERATIONS.map((operation) => {
            const explicit = Boolean(overrides[operation.key]);
            const result = preview[operation.key];
            return <div className="binding-operation" key={operation.key}>
              <div><strong>{operation.label}</strong><small>{operation.key}</small></div>
              <label><span className="sr-only">{operation.label}</span><select aria-label={operation.label} value={overrides[operation.key] ?? ""} onChange={(event) => setOverrides((current) => ({ ...current, [operation.key]: event.target.value }))}><option value="">继承默认</option>{options(operation.capability).map((option) => <option key={option.model.supplier_model_id} value={option.model.supplier_model_id}>{optionLabel(option)}</option>)}</select></label>
              <span data-testid={`binding-source-${operation.key}`} className={explicit ? "binding-explicit" : "binding-inherited"}>{explicit ? "显式覆盖" : "继承默认"}</span>
              <span className="binding-preview">{result?.value ? `${result.value.provider_model_name} · ${result.value.binding_source === "operation_override" ? "显式覆盖" : "继承默认"}` : result?.error?.message ?? "尚未预览"}</span>
            </div>;
          })}
        </div>
      </section>
      {error ? <div className="management-error" role="alert"><strong>{error.message}</strong>{error.code === "REVISION_CONFLICT" ? <Button size="small" onClick={() => void bindings.refetch()}>重新加载绑定</Button> : null}</div> : null}
      {success ? <div className="management-success" role="status">{success}</div> : null}
      <div className="binding-actions"><Button type="primary" loading={saving} onClick={() => void save()}>保存全部模型配置</Button></div>
    </section>
  );
}
