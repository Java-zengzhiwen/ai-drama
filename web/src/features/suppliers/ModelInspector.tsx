import type { SupplierModelRead } from "./api";

const CAPABILITY_LABEL = { text: "文本", image: "图片", video: "视频" } as const;

export function ModelInspector({ model }: { model: SupplierModelRead | null }) {
  if (!model) {
    return (
      <aside className="model-inspector" aria-label="模型检查器">
        <h3>模型详情</h3>
        <p>选择一个模型查看稳定身份、不可变修订和约束。</p>
      </aside>
    );
  }
  return (
    <aside className="model-inspector" aria-label="模型检查器">
      <h3>模型详情</h3>
      <dl>
        <dt>显示名称</dt><dd>{model.display_name}</dd>
        <dt>supplier_model_id</dt><dd><code>{model.supplier_model_id}</code></dd>
        <dt>供应商模型名</dt><dd>{model.provider_model_name}</dd>
        <dt>当前修订</dt><dd><code>{model.model_revision_id}</code></dd>
        <dt>能力</dt><dd>{CAPABILITY_LABEL[model.capability]}</dd>
        <dt>来源</dt><dd>{model.source === "built_in" ? "内置" : "Overlay"}</dd>
        <dt>影响范围</dt><dd>{model.binding_count ? `已绑定 ${model.binding_count} 处` : "尚未绑定"}</dd>
        <dt>模式与约束</dt><dd><pre>{JSON.stringify(model.definition, null, 2)}</pre></dd>
      </dl>
    </aside>
  );
}
