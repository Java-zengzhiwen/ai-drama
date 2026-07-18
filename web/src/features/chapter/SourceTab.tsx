import {
  CheckOutlined,
  InfoCircleFilled,
  PlayCircleFilled,
  SaveOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Typography } from "antd";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useInRouterContext } from "react-router-dom";
import {
  getModelResolution,
  getProjectModelBindings,
  listChapters,
  saveProjectModelBindings,
  type ChapterRead,
} from "../projects/api";
import {
  listSupplierModels,
  listSuppliers,
  type SupplierModelRead,
  type SupplierRead,
} from "../suppliers/api";
import {
  createSourceRevision,
  generateScript,
  type SourceRevisionRead,
} from "../script/api";

type SourceTabProps = {
  chapter: ChapterRead;
  onOpenScript?: () => void;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

type TextModelOption = {
  model: SupplierModelRead;
  supplier: SupplierRead;
};

export function SourceTab({ chapter, onOpenScript }: SourceTabProps) {
  const queryClient = useQueryClient();
  const inRouterContext = useInRouterContext();
  const [draft, setDraft] = useState(chapter.source_text ?? "");
  const [saved, setSaved] = useState(false);
  const [chapterSearch, setChapterSearch] = useState("");
  const [lastRevision, setLastRevision] = useState<SourceRevisionRead | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");

  useEffect(() => {
    setDraft(chapter.source_text ?? "");
    setSaved(false);
    setLastRevision(null);
    setSelectedModelId("");
  }, [chapter.chapter_id, chapter.project_id]);

  const chaptersQuery = useQuery({
    queryKey: ["chapters", chapter.project_id],
    queryFn: () => listChapters(chapter.project_id),
  });
  const modelQuery = useQuery({
    queryKey: ["model-resolution", chapter.project_id, "script_adaptation"],
    queryFn: () => getModelResolution(chapter.project_id, "script_adaptation"),
  });
  const bindingsQuery = useQuery({
    queryKey: ["project-model-bindings", chapter.project_id],
    queryFn: () => getProjectModelBindings(chapter.project_id),
  });
  const modelCatalogQuery = useQuery({
    queryKey: ["project-model-options", chapter.project_id],
    queryFn: async () => {
      const suppliers = await listSuppliers();
      const rows = await Promise.all(
        suppliers.map(async (supplier) => ({
          supplier,
          models: (await listSupplierModels(supplier.supplier_id)).data,
        })),
      );
      return rows.flatMap(({ supplier, models }) =>
        models.map((model) => ({ model, supplier })),
      );
    },
  });

  const textModelOptions = useMemo(
    () => (modelCatalogQuery.data ?? []).filter(({ model, supplier }) =>
      Boolean(supplier.enabled) && Boolean(model.enabled) && model.capability === "text",
    ),
    [modelCatalogQuery.data],
  );
  const configuredModelId = bindingsQuery.data?.data.operation_overrides.script_adaptation
    || bindingsQuery.data?.data.defaults.text
    || "";

  useEffect(() => {
    if (bindingsQuery.data) {
      setSelectedModelId(configuredModelId);
    }
  }, [bindingsQuery.data, configuredModelId]);

  const normalizedDraft = draft.trim();
  const persistedSource = (chapter.source_text ?? "").trim();
  const sourceIsSaved = Boolean(normalizedDraft) && (
    saved
    || (Boolean(chapter.current_source_revision_id) && normalizedDraft === persistedSource)
  );
  const characterCount = countReadableCharacters(draft);
  const estimatedMinutes = Math.max(1, Math.round(characterCount / 900));
  const estimatedScenes = Math.max(1, Math.ceil(characterCount / 450));
  const previewRows = buildPreviewRows(estimatedScenes, characterCount);

  const filteredChapters = useMemo(() => {
    const chapters = chaptersQuery.data ?? [chapter];
    const query = chapterSearch.trim().toLowerCase();
    return chapters
      .filter((item) => !query || item.title.toLowerCase().includes(query))
      .sort((left, right) => left.position - right.position);
  }, [chapter, chapterSearch, chaptersQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (content: string) => createSourceRevision(chapter.chapter_id, { content }),
    onSuccess: (revision, content) => {
      queryClient.setQueryData<ChapterRead>(["chapter", chapter.chapter_id], (current) => ({
        ...(current ?? chapter),
        current_source_revision_id: revision.source_revision_id,
        source_text: content,
      }));
      void queryClient.invalidateQueries({ queryKey: ["chapters", chapter.project_id] });
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
      setLastRevision(revision);
      setSaved(true);
    },
  });

  const bindingMutation = useMutation({
    mutationFn: async (supplierModelId: string) => {
      const current = bindingsQuery.data;
      if (!current) {
        throw new Error("项目模型配置尚未加载完成。");
      }
      const savedBindings = await saveProjectModelBindings(
        chapter.project_id,
        {
          defaults: current.data.defaults,
          operation_overrides: {
            ...current.data.operation_overrides,
            script_adaptation: supplierModelId,
          },
        },
        current.etag,
      );
      queryClient.setQueryData(
        ["project-model-bindings", chapter.project_id],
        savedBindings,
      );
      await queryClient.invalidateQueries({
        queryKey: ["model-resolution", chapter.project_id, "script_adaptation"],
      });
      return savedBindings;
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedModelId) {
        throw new Error("请先选择文本模型。");
      }
      if (selectedModelId !== configuredModelId) {
        await bindingMutation.mutateAsync(selectedModelId);
      }
      if (!sourceIsSaved) {
        await saveMutation.mutateAsync(normalizedDraft);
      }
      return generateScript(chapter.chapter_id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["script-revisions", chapter.chapter_id] });
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
      onOpenScript?.();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (normalizedDraft) {
      saveMutation.mutate(normalizedDraft);
    }
  }

  const mutationPending = saveMutation.isPending
    || bindingMutation.isPending
    || generateMutation.isPending;
  const mutationError = generateMutation.isError
    ? generateMutation.error
    : bindingMutation.isError
      ? bindingMutation.error
      : saveMutation.error;
  const selectedModel = textModelOptions.find(
    ({ model }) => model.supplier_model_id === selectedModelId,
  );
  const modelSelectionReady = Boolean(selectedModel)
    && !bindingsQuery.isLoading
    && !modelCatalogQuery.isLoading;

  return (
    <form aria-label="原文编辑" className="source-conversion-layout" onSubmit={submit}>
      <nav aria-label="章节导航" className="source-chapter-nav">
        <div className="source-panel-heading">
          <strong>章节导航</strong>
          <span>{filteredChapters.length} 章</span>
        </div>
        <Input
          allowClear
          aria-label="搜索章节标题"
          onChange={(event) => setChapterSearch(event.target.value)}
          placeholder="搜索章节标题"
          prefix={<SearchOutlined />}
          value={chapterSearch}
        />
        <div className="source-chapter-list">
          {filteredChapters.map((item) => {
            const current = item.chapter_id === chapter.chapter_id;
            const complete = Boolean(item.current_source_revision_id);
            const chapterLinkContent = (
              <>
                <span className="source-chapter-position">
                  {String(item.position).padStart(2, "0")}
                </span>
                <span className="source-chapter-title">{item.title}</span>
                <span className="source-chapter-state" data-complete={complete}>
                  <i aria-hidden="true" />
                  {complete ? "原文已确认" : current ? "原文处理中" : "未开始"}
                </span>
              </>
            );
            const href = `/projects/${item.project_id}/chapters/${item.chapter_id}`;
            return inRouterContext ? (
              <Link
                aria-current={current ? "page" : undefined}
                className="source-chapter-link"
                data-current={current}
                key={item.chapter_id}
                to={href}
              >
                {chapterLinkContent}
              </Link>
            ) : (
              <a
                aria-current={current ? "page" : undefined}
                className="source-chapter-link"
                data-current={current}
                href={href}
                key={item.chapter_id}
              >
                {chapterLinkContent}
              </a>
            );
          })}
          {!filteredChapters.length ? (
            <Typography.Text className="source-chapter-empty" type="secondary">
              没有匹配章节
            </Typography.Text>
          ) : null}
        </div>
        {inRouterContext ? (
          <Link className="source-new-chapter" to={`/projects/${chapter.project_id}`}>
            ＋ 新建章节
          </Link>
        ) : (
          <a className="source-new-chapter" href={`/projects/${chapter.project_id}`}>
            ＋ 新建章节
          </a>
        )}
      </nav>

      <section aria-label="原文编辑区" className="source-manuscript">
        <div className="source-editor-toolbar" aria-label="原文编辑工具栏">
          <span className="source-editor-mode">正文</span>
          <span>宋体</span>
          <span>16px</span>
          <span className="source-toolbar-divider" />
          <Typography.Text type="secondary">纯文本编辑</Typography.Text>
          <span className="source-editor-save-state" data-saved={sourceIsSaved}>
            <CheckOutlined /> {sourceIsSaved ? "已保存" : "有未保存更改"}
          </span>
        </div>
        {!chapter.source_text && !draft ? (
          <div className="source-empty-copy">暂无小说原文。粘贴正文后才能生成剧本。</div>
        ) : null}
        <div className="source-manuscript-paper">
          <div className="source-manuscript-title">{chapter.title}</div>
          <Input.TextArea
            aria-label="小说原文"
            className="source-manuscript-textarea"
            disabled={mutationPending}
            onChange={(event) => {
              setDraft(event.target.value);
              setSaved(false);
            }}
            placeholder="在这里粘贴或编辑小说原文……"
            value={draft}
          />
        </div>
        <footer className="source-editor-footer">
          <span>共 {characterCount.toLocaleString("zh-CN")} 字</span>
          <span>版本：{lastRevision ? `v${lastRevision.number}` : "当前"}</span>
          <span data-saved={sourceIsSaved}>{sourceIsSaved ? "已保存" : "待保存"}</span>
        </footer>
      </section>

      <aside aria-label="原文转剧本" className="source-conversion-inspector" role="region">
        <header className="source-inspector-header">
          <strong>原文转剧本</strong>
          {inRouterContext ? (
            <Link to={`/projects/${chapter.project_id}/model-bindings`}>管理模型</Link>
          ) : (
            <a href={`/projects/${chapter.project_id}/model-bindings`}>管理模型</a>
          )}
        </header>

        <div className="source-inspector-scroll">
          <div className="source-inspector-config">
          <InspectorField label="文本模型">
            <select
              aria-label="文本模型"
              className="source-model-select"
              disabled={mutationPending || modelCatalogQuery.isLoading || bindingsQuery.isLoading}
              onChange={(event) => setSelectedModelId(event.target.value)}
              value={selectedModelId}
            >
              <option value="">请选择文本模型</option>
              {textModelOptions.map(({ model, supplier }) => (
                <option key={model.supplier_model_id} value={model.supplier_model_id}>
                  {supplier.display_name} / {model.display_name}
                </option>
              ))}
            </select>
            <small className="source-model-hint" data-pending={Boolean(selectedModelId && selectedModelId !== configuredModelId)}>
              {selectedModelId && selectedModelId !== configuredModelId
                ? "将在生成前保存为本项目的剧本改编模型"
                : modelQuery.data?.provider_model_name
                  ? `当前调用：${modelQuery.data.provider_model_name}`
                  : selectedModel
                    ? `当前调用：${selectedModel.model.provider_model_name}`
                    : modelCatalogQuery.isLoading
                      ? "正在加载可用模型…"
                      : "请选择一个已启用的文本模型"}
            </small>
          </InspectorField>
          <InspectorField label="改编目标">
            <div className="source-readonly-control">沿用项目制作简述</div>
          </InspectorField>
          <InspectorField label="目标时长">
            <div className="source-duration-control">
              <strong>{estimatedMinutes}</strong>
              <span>分钟</span>
              <small>按原文字数自动估算</small>
            </div>
          </InspectorField>
          </div>

          <section className="source-revision-card">
          <strong>原文版本（不可编辑）</strong>
          <dl>
            <div><dt>版本</dt><dd>{lastRevision ? `v${lastRevision.number}` : "当前"}</dd></div>
            <div><dt>创建</dt><dd>{formatRevisionTime(lastRevision?.created_at ?? chapter.updated_at)}</dd></div>
            <div><dt>字数</dt><dd>{characterCount.toLocaleString("zh-CN")} 字</dd></div>
          </dl>
          </section>

          <section className="source-readiness-card">
          <strong>就绪校验</strong>
          <ReadinessItem ready={sourceIsSaved} text="原文已保存" />
          <ReadinessItem ready={Boolean(chapter.title.trim())} text="章节标题已设置" />
          <ReadinessItem ready={characterCount >= 500} text="字数满足要求（≥ 500）" />
          <ReadinessItem
            ready={estimatedMinutes >= 3 && estimatedMinutes <= 8}
            text={`预计可生成时长在范围内（约 ${estimatedMinutes} 分钟）`}
          />
          </section>

          <section className="source-preview-card">
          <strong>预计生成结构（预览）</strong>
          <div className="source-preview-table" role="table" aria-label="预计生成结构">
            <div className="source-preview-row source-preview-head" role="row">
              <span role="columnheader">场次（预计）</span>
              <span role="columnheader">人物（预计）</span>
              <span role="columnheader">对白（预计）</span>
            </div>
            {previewRows.map((row) => (
              <div className="source-preview-row" key={row.scene} role="row">
                <span role="cell">{row.scene}</span>
                <span role="cell">待剧本生成</span>
                <span role="cell">{row.dialogue}</span>
              </div>
            ))}
            <footer>
              <span>预计场次：{estimatedScenes} 场</span>
              <span>对白数量仅供预览</span>
            </footer>
          </div>
          </section>

          <div className="source-inspector-notice">
          <InfoCircleFilled />
          <span>分镜阶段将在生成并确认剧本后解锁</span>
          </div>

          {saved && !generateMutation.isPending ? (
            <Alert message="原文已保存为新版本。" showIcon type="success" />
          ) : null}
          {mutationError ? (
            <WorkflowErrorAlert
              error={mutationError}
              fallbackMessage={generateMutation.isError
                ? "剧本生成失败。请重试。"
                : bindingMutation.isError
                  ? "模型配置保存失败。请重试。"
                  : "原文保存失败。请重试。"}
              onRetry={() => {
                if (generateMutation.isError || bindingMutation.isError) {
                  generateMutation.mutate();
                } else if (saveMutation.variables) {
                  saveMutation.mutate(saveMutation.variables);
                }
              }}
            />
          ) : null}
        </div>

        <div className="source-inspector-actions">
          <Button
            disabled={!normalizedDraft || mutationPending}
            htmlType="submit"
            icon={<SaveOutlined aria-hidden="true" />}
            loading={saveMutation.isPending && !generateMutation.isPending}
          >
            仅保存原文
          </Button>
          <Button
            disabled={!normalizedDraft || mutationPending || !modelSelectionReady}
            icon={<PlayCircleFilled aria-hidden="true" />}
            loading={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
            type="primary"
          >
            保存并生成剧本
          </Button>
        </div>
      </aside>
    </form>
  );
}

function InspectorField({ children, label }: { children: ReactNode; label: string }) {
  return (
    <label className="source-inspector-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function ReadinessItem({ ready, text }: { ready: boolean; text: string }) {
  return (
    <div className="source-readiness-item" data-ready={ready}>
      <span aria-hidden="true">{ready ? "✓" : "○"}</span>
      <span>{text}</span>
    </div>
  );
}

function WorkflowErrorAlert({
  error,
  fallbackMessage,
  onRetry,
}: {
  error: unknown;
  fallbackMessage: string;
  onRetry: () => void;
}) {
  const details = getApiErrorDetails(error, fallbackMessage);

  return (
    <Alert
      action={<Button onClick={onRetry}>重试</Button>}
      description={details.code || undefined}
      message={details.message}
      showIcon
      type="error"
    />
  );
}

function getApiErrorDetails(error: unknown, fallbackMessage: string) {
  const data = (error as ApiError | undefined)?.response?.data;
  return {
    code: data?.error_code ?? "",
    message: data?.error_message ?? fallbackMessage,
  };
}

function countReadableCharacters(content: string) {
  return content.replace(/\s/g, "").length;
}

function buildPreviewRows(sceneCount: number, characterCount: number) {
  const visibleRows = Math.min(3, sceneCount);
  const dialoguePerScene = Math.max(2, Math.round(characterCount / Math.max(sceneCount, 1) / 55));
  return Array.from({ length: visibleRows }, (_, index) => ({
    scene: `1-${String(index + 1).padStart(2, "0")}`,
    dialogue: `${Math.max(2, dialoguePerScene - 1)}–${dialoguePerScene + 2} 句`,
  }));
}

function formatRevisionTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
    hour12: false,
  }).format(date);
}
