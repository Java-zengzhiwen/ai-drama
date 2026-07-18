import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Drawer, Input, Progress, Skeleton, Steps, Typography } from "antd";
import { type FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createProject,
  getChapterStatus,
  listChapters,
  listProjects,
  type ChapterRead,
  type ChapterStatus,
  type ProjectCreate,
  type ProjectRead,
} from "./api";

const emptyProject: ProjectCreate = {
  name: "",
  description: "",
  series_canon: "",
  characters_context: "",
  production_brief: "",
};

const workflowItems = ["原文", "剧本", "分镜", "资料资产", "Shot Prompt", "生成", "结果"].map(
  (title) => ({ title }),
);

type ProjectProductionSummary = {
  actionLabel: string;
  chapter: ChapterRead | null;
  chapterCount: number;
  href: string;
  project: ProjectRead;
  stageLabel: string;
  statusLabel: string;
  statusTone: "success" | "processing" | "default" | "error" | "warning";
  step: number;
  updatedAt: string;
};

type ProductionState = Pick<
  ProjectProductionSummary,
  "actionLabel" | "stageLabel" | "statusLabel" | "statusTone" | "step"
>;

const defaultProductionState: ProductionState = {
  actionLabel: "打开项目",
  stageLabel: "尚未开始",
  statusLabel: "尚未添加章节",
  statusTone: "default",
  step: 0,
};

const statusStateMap: Record<string, ProductionState> = {
  missing_source: {
    actionLabel: "添加原文",
    stageLabel: "原文",
    statusLabel: "待添加原文",
    statusTone: "default",
    step: 0,
  },
  source_empty: {
    actionLabel: "添加原文",
    stageLabel: "原文",
    statusLabel: "待添加原文",
    statusTone: "default",
    step: 0,
  },
  source_ready: {
    actionLabel: "生成剧本",
    stageLabel: "剧本",
    statusLabel: "剧本待生成",
    statusTone: "processing",
    step: 1,
  },
  script_draft: {
    actionLabel: "继续剧本",
    stageLabel: "剧本",
    statusLabel: "剧本待确认",
    statusTone: "warning",
    step: 1,
  },
  script_approved: {
    actionLabel: "生成分镜",
    stageLabel: "分镜",
    statusLabel: "分镜待生成",
    statusTone: "processing",
    step: 2,
  },
  storyboard_draft: {
    actionLabel: "继续分镜",
    stageLabel: "分镜",
    statusLabel: "分镜待确认",
    statusTone: "warning",
    step: 2,
  },
  storyboard_approved: {
    actionLabel: "进入资料与资产",
    stageLabel: "资料与资产",
    statusLabel: "资产待准备",
    statusTone: "processing",
    step: 3,
  },
  prompts_ready: {
    actionLabel: "继续制作",
    stageLabel: "Shot Prompt",
    statusLabel: "Prompt 已就绪",
    statusTone: "success",
    step: 4,
  },
  blocked: {
    actionLabel: "查看阻断原因",
    stageLabel: "需要处理",
    statusLabel: "存在阻断",
    statusTone: "error",
    step: 0,
  },
  error: {
    actionLabel: "检查项目",
    stageLabel: "需要检查",
    statusLabel: "状态异常",
    statusTone: "error",
    step: 0,
  },
};

export function ProjectListPage() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<ProjectCreate>(emptyProject);
  const [isCreateOpen, setCreateOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });
  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      queryClient.setQueryData<ProjectRead[]>(["projects"], (current = []) => [...current, project]);
      setDraft(emptyProject);
      setCreateOpen(false);
    },
  });

  const projects = useMemo(
    () =>
      [...(projectsQuery.data ?? [])].sort(
        (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
      ),
    [projectsQuery.data],
  );
  const projectSummaryQueries = useQueries({
    queries: projects.map((project) => ({
      queryKey: ["project-production-summary", project.project_id],
      queryFn: () => loadProjectProductionSummary(project),
    })),
  });
  const summaries = projects.map(
    (project, index) => projectSummaryQueries[index]?.data ?? createFallbackSummary(project),
  );
  const activeSummary = summaries[0] ?? null;
  const normalizedSearch = searchQuery.trim().toLocaleLowerCase("zh-CN");
  const otherSummaries = summaries.slice(1).filter((summary) => {
    if (!normalizedSearch) {
      return true;
    }
    return `${summary.project.name} ${summary.project.description}`
      .toLocaleLowerCase("zh-CN")
      .includes(normalizedSearch);
  });
  const isSubmitting = createProjectMutation.isPending;

  function updateDraft(field: keyof ProjectCreate, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createProjectMutation.mutate({
      name: draft.name.trim(),
      description: draft.description.trim(),
      series_canon: draft.series_canon.trim(),
      characters_context: draft.characters_context.trim(),
      production_brief: draft.production_brief.trim(),
    });
  }

  return (
    <section aria-labelledby="project-list-title" className="entry-workbench project-entry-workbench">
      <div className="project-entry-stack">
        <header className="project-entry-header">
          <div className="project-entry-heading-copy">
            <Typography.Title id="project-list-title" level={1}>
              项目
            </Typography.Title>
            <Typography.Text type="secondary">专注创作，持续推进每个故事。</Typography.Text>
          </div>
          <div className="project-entry-tools">
            <Input
              aria-label="搜索项目"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="搜索项目名称或描述"
              type="search"
              value={searchQuery}
            />
            <Button onClick={() => setCreateOpen(true)} type="primary">
              新建项目
            </Button>
          </div>
        </header>

        {projectsQuery.isLoading ? <Skeleton active paragraph={{ rows: 7 }} title={false} /> : null}
        {projectsQuery.isError ? (
          <Alert
            action={<Button onClick={() => void projectsQuery.refetch()}>重试</Button>}
            message="项目加载失败。请重试。"
            showIcon
            type="error"
          />
        ) : null}

        {!projectsQuery.isLoading && !projectsQuery.isError && summaries.length === 0 ? (
          <section className="project-empty-state" aria-label="项目空状态">
            <Typography.Title level={2}>从第一个故事开始</Typography.Title>
            <Typography.Text type="secondary">暂无项目。创建项目后开始章节制作。</Typography.Text>
          </section>
        ) : null}

        {activeSummary ? <FocusedProject summary={activeSummary} /> : null}

        {summaries.length > 1 ? (
          <section className="project-queue" aria-labelledby="other-projects-title">
            <div className="project-section-heading">
              <Typography.Title id="other-projects-title" level={2}>
                其他项目
              </Typography.Title>
              <Typography.Text type="secondary">共 {summaries.length - 1} 个项目</Typography.Text>
            </div>
            {otherSummaries.length === 0 ? (
              <div className="project-queue-empty">没有匹配的其他项目</div>
            ) : (
              <div className="dense-table-scroll">
                <table aria-label="其他项目" className="project-queue-table">
                  <thead>
                    <tr>
                      <th>项目名称</th>
                      <th>进度</th>
                      <th>当前阶段</th>
                      <th>当前状态</th>
                      <th>最近编辑</th>
                      <th>下一步</th>
                    </tr>
                  </thead>
                  <tbody>
                    {otherSummaries.map((summary) => (
                      <ProjectQueueRow key={summary.project.project_id} summary={summary} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ) : null}
      </div>

      <Drawer
        className="project-create-drawer"
        onClose={() => setCreateOpen(false)}
        open={isCreateOpen}
        title="新建项目"
        width={520}
      >
        <form aria-label="创建项目" className="project-create-form" id="project-create-form" onSubmit={submitProject}>
          <ProjectField
            disabled={isSubmitting}
            label="项目名称"
            onChange={(value) => updateDraft("name", value)}
            required
            value={draft.name}
          />
          <ProjectField
            disabled={isSubmitting}
            label="项目描述"
            onChange={(value) => updateDraft("description", value)}
            value={draft.description}
          />
          <ProjectField
            disabled={isSubmitting}
            label="系列设定"
            onChange={(value) => updateDraft("series_canon", value)}
            value={draft.series_canon}
          />
          <ProjectField
            disabled={isSubmitting}
            label="人物上下文"
            onChange={(value) => updateDraft("characters_context", value)}
            value={draft.characters_context}
          />
          <ProjectField
            disabled={isSubmitting}
            label="制作简述"
            onChange={(value) => updateDraft("production_brief", value)}
            value={draft.production_brief}
          />
          {createProjectMutation.isError ? (
            <Alert message="项目创建失败。请重试。" showIcon type="error" />
          ) : null}
          <div className="project-create-actions">
            <Button disabled={isSubmitting} onClick={() => setCreateOpen(false)}>
              取消
            </Button>
            <Button disabled={!draft.name.trim()} htmlType="submit" loading={isSubmitting} type="primary">
              创建项目
            </Button>
          </div>
        </form>
      </Drawer>
    </section>
  );
}

function FocusedProject({ summary }: { summary: ProjectProductionSummary }) {
  return (
    <section aria-label="继续制作" className="project-focus-section">
      <Typography.Title level={2}>继续制作</Typography.Title>
      <div className="project-focus">
        <div className="project-focus-summary">
          <div className="project-focus-identity">
            <Link className="project-focus-title" to={`/projects/${summary.project.project_id}`}>
              {summary.project.name}
            </Link>
            <Typography.Text type="secondary">
              {summary.project.description || "尚未填写项目描述"}
            </Typography.Text>
          </div>
          <dl className="project-focus-metadata">
            <div>
              <dt>当前章节</dt>
              <dd>{summary.chapter?.title ?? "尚未添加"}</dd>
            </div>
            <div>
              <dt>当前阶段</dt>
              <dd>
                <Badge status={summary.statusTone} text={summary.statusLabel} />
              </dd>
            </div>
            <div>
              <dt>进度</dt>
              <dd>{summary.chapterCount} 章</dd>
            </div>
            <div>
              <dt>最近编辑</dt>
              <dd>{formatUpdatedAt(summary.updatedAt)}</dd>
            </div>
          </dl>
        </div>
        <div className="project-focus-workflow">
          <Steps current={summary.step} items={workflowItems} responsive={false} size="small" />
        </div>
        <Link className="project-primary-link" to={summary.href}>
          {summary.actionLabel}
        </Link>
      </div>
    </section>
  );
}

function ProjectQueueRow({ summary }: { summary: ProjectProductionSummary }) {
  const progressPercent = Math.max(6, Math.round(((summary.step + 1) / workflowItems.length) * 100));
  return (
    <tr>
      <td>
        <div className="project-queue-name">
          <Link to={`/projects/${summary.project.project_id}`}>{summary.project.name}</Link>
          <span>{summary.project.description || "尚未填写项目描述"}</span>
        </div>
      </td>
      <td>
        <div className="project-queue-progress">
          <span>{summary.chapterCount} 章</span>
          <Progress percent={progressPercent} showInfo={false} size="small" />
        </div>
      </td>
      <td>{summary.stageLabel}</td>
      <td>
        <Badge status={summary.statusTone} text={summary.statusLabel} />
      </td>
      <td>{formatUpdatedAt(summary.updatedAt)}</td>
      <td>
        <Link className="project-secondary-link" to={summary.href}>
          {summary.actionLabel}
        </Link>
      </td>
    </tr>
  );
}

function ProjectField({
  disabled,
  label,
  onChange,
  required = false,
  value,
}: {
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="project-create-field">
      <span>
        {label}
        {required ? <Typography.Text type="danger"> *</Typography.Text> : null}
      </span>
      <Input
        aria-label={label}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}

async function loadProjectProductionSummary(project: ProjectRead): Promise<ProjectProductionSummary> {
  const chapters = await listChapters(project.project_id);
  const chapter = [...chapters].sort(
    (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
  )[0] ?? null;
  const status = chapter ? await getChapterStatus(chapter.chapter_id) : null;
  return createProjectSummary(project, chapters, chapter, status);
}

function createFallbackSummary(project: ProjectRead): ProjectProductionSummary {
  return createProjectSummary(project, [], null, null);
}

function createProjectSummary(
  project: ProjectRead,
  chapters: ChapterRead[],
  chapter: ChapterRead | null,
  status: ChapterStatus | null,
): ProjectProductionSummary {
  const productionState = status ? resolveProductionState(status) : defaultProductionState;
  return {
    ...productionState,
    chapter,
    chapterCount: chapters.length,
    href: chapter
      ? `/projects/${project.project_id}/chapters/${chapter.chapter_id}`
      : `/projects/${project.project_id}`,
    project,
    updatedAt: chapter?.updated_at ?? project.updated_at,
  };
}

function resolveProductionState(status: ChapterStatus): ProductionState {
  const baseState = statusStateMap[status.status] ?? {
    ...defaultProductionState,
    statusLabel: "状态待检查",
    statusTone: "warning" as const,
  };
  if (!status.blocking_reason) {
    return baseState;
  }
  return {
    ...baseState,
    statusLabel: localizeBlockingReason(status.blocking_reason, baseState.statusLabel),
    statusTone: "warning",
  };
}

function localizeBlockingReason(reason: string, fallback: string) {
  const normalizedReason = reason.trim();
  if (!normalizedReason) {
    return fallback;
  }
  const knownReasons: Record<string, string> = {
    "chapter source revision is required": "待添加原文",
  };
  if (knownReasons[normalizedReason]) {
    return knownReasons[normalizedReason];
  }
  return /[\u3400-\u9fff]/u.test(normalizedReason) ? normalizedReason : fallback;
}

function formatUpdatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "时间未知";
  }
  const today = new Date();
  if (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  ) {
    return `今天 ${new Intl.DateTimeFormat("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date)}`;
  }
  return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
}
