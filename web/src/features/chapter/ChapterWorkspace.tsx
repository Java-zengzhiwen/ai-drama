import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Skeleton, Tabs, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link, useInRouterContext } from "react-router-dom";
import { ProfilesAssetsTab } from "../assets/ProfilesAssetsTab";
import { AgnesGenerationTab } from "../generation/AgnesGenerationTab";
import { GenerationResultsTab } from "../generation/GenerationResultsTab";
import { listGenerationJobs } from "../generation/api";
import { getChapterStatus, type ChapterStatus } from "../projects/api";
import { listShotPromptRevisions } from "../prompts/api";
import { ShotPromptTab } from "../prompts/ShotPromptTab";
import { ScriptTab } from "../script/ScriptTab";
import { getChapter, type ScriptGenerationRunRead } from "../script/api";
import {
  clearActiveScriptRun,
  loadActiveScriptRun,
  persistActiveScriptRun,
} from "../script/streaming";
import { StoryboardTab } from "../storyboard/StoryboardTab";
import { SourceTab } from "./SourceTab";
import { WorkflowGateBar } from "./WorkflowGateBar";

type ChapterWorkspaceProps = {
  chapterId: string;
  projectId: string;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

const storyboardBlockedReason = "未确认剧本，不允许生成分镜。";
const productionBlockedReason = "未确认分镜，不允许进入后续生产步骤。";
const agnesBlockedReason = "请先生成或选择当前 Shot Prompt revision。";
const resultsBlockedReason = "已有 GenerationJob 后可查看结果与重跑。";
const workflowTabKeys = ["source", "script", "storyboard", "assets", "shot-prompt", "agnes", "results"];

export function ChapterWorkspace({ chapterId, projectId }: ChapterWorkspaceProps) {
  const inRouterContext = useInRouterContext();
  const [activeTab, setActiveTab] = useState("source");
  const [activeScriptRun, setActiveScriptRun] = useState<ScriptGenerationRunRead | null>(null);
  useEffect(() => {
    const restored = loadActiveScriptRun(chapterId);
    setActiveScriptRun(restored);
    setActiveTab(restored ? "script" : "source");
  }, [chapterId]);
  const chapterQuery = useQuery({
    enabled: Boolean(chapterId),
    queryKey: ["chapter", chapterId],
    queryFn: () => getChapter(chapterId),
  });
  const statusQuery = useQuery({
    enabled: Boolean(chapterId),
    queryKey: ["chapter-status", chapterId],
    queryFn: () => getChapterStatus(chapterId),
  });
  const shotPromptRevisionsQuery = useQuery({
    enabled: Boolean(chapterId) && shotPromptUnlocked(statusQuery.data),
    queryKey: ["shot-prompt-revisions", chapterId],
    queryFn: () => listShotPromptRevisions(chapterId),
  });
  const generationJobsQuery = useQuery({
    enabled: Boolean(chapterId),
    queryKey: ["generation-jobs", chapterId],
    queryFn: () => listGenerationJobs(chapterId),
  });

  const status = statusQuery.data;
  const currentPromptRevision = (shotPromptRevisionsQuery.data ?? []).find((revision) => revision.current);
  const agnesOpen = Boolean(currentPromptRevision);
  const resultsOpen = (generationJobsQuery.data ?? []).length > 0;
  const rail = useWorkflowRail(status, statusQuery.isError, statusQuery.isLoading, agnesOpen, resultsOpen);
  const workflowGate = useWorkflowGate(status, statusQuery.isError, statusQuery.isLoading, agnesOpen);

  if (chapterQuery.isError) {
    return (
      <Alert
        action={<Button onClick={() => void chapterQuery.refetch()}>重试</Button>}
        message="章节加载失败。请重试。"
        showIcon
        type="error"
      />
    );
  }

  const chapter = chapterQuery.data;

  return (
    <section
      aria-labelledby="chapter-workspace-title"
      className="chapter-workspace"
      data-editor-workspace={activeTab === "source" || activeTab === "script" ? "true" : undefined}
    >
      <header className="chapter-heading">
        <div className="chapter-breadcrumb">
          {inRouterContext ? (
            <Link to={`/projects/${projectId}`}>返回项目</Link>
          ) : (
            <a href={`/projects/${projectId}`}>返回项目</a>
          )}
          <span aria-hidden="true">/</span>
          <span>章节 {chapter?.position ?? "-"}</span>
        </div>
        <Typography.Title id="chapter-workspace-title" level={1} style={{ fontSize: 22, margin: 0 }}>
          {chapter?.title ?? "章节工作区"}
        </Typography.Title>
        <Typography.Text type="secondary">从原文到生成结果的单章制作工作台</Typography.Text>
      </header>

      <div
        aria-label="workflow rail"
        className="workflow-rail"
        role="list"
      >
        {rail.map((item, index) => (
          <div
            aria-label={item.label}
            className="workflow-step"
            data-active={workflowTabKeys[index] === activeTab}
            data-reason={item.reason || undefined}
            data-tone={item.color}
            key={item.label}
            role="listitem"
          >
            <span className="workflow-step-index">{String(index + 1).padStart(2, "0")}</span>
            <span className="workflow-step-copy">
              <strong aria-hidden="true">{item.label}</strong>
              <small aria-hidden="true">{item.reason ? "查看阻断原因" : "已完成"}</small>
            </span>
          </div>
        ))}
      </div>

      {statusQuery.isError ? (
        <WorkflowErrorAlert
          error={statusQuery.error}
          fallbackMessage="流程状态加载失败。请重试。"
          onRetry={() => void statusQuery.refetch()}
        />
      ) : null}

      {activeTab === "source" || activeTab === "script" ? (
        <WorkflowGateBar details={workflowGate.details} summary={workflowGate.summary} />
      ) : null}

      {chapterQuery.isLoading || !chapter ? (
        <Tabs
          items={[
            {
              children: <Skeleton active paragraph={{ rows: 8 }} />,
              key: "source",
              label: "原文",
            },
            {
              children: <Skeleton active paragraph={{ rows: 8 }} />,
              key: "script",
              label: "剧本",
            },
          ]}
        />
      ) : (
        <Tabs
          className="chapter-tabs"
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              children: (
                <SourceTab
                  chapter={chapter}
                  onScriptGenerationStarted={(run) => {
                    persistActiveScriptRun(chapter.chapter_id, run);
                    setActiveScriptRun(run);
                    setActiveTab("script");
                  }}
                  onLegacyScriptGenerated={() => {
                    clearActiveScriptRun(chapter.chapter_id);
                    setActiveScriptRun(null);
                    setActiveTab("script");
                  }}
                />
              ),
              key: "source",
              label: "原文",
            },
            {
              children: (
                <ScriptTab
                  activeRun={activeScriptRun}
                  chapter={chapter}
                  onGenerationCompleted={() => {
                    clearActiveScriptRun(chapter.chapter_id);
                    setActiveScriptRun(null);
                  }}
                  onRegenerateRequested={() => {
                    clearActiveScriptRun(chapter.chapter_id);
                    setActiveScriptRun(null);
                    setActiveTab("source");
                  }}
                />
              ),
              key: "script",
              label: "剧本",
            },
            {
              children: storyboardUnlocked(status) ? (
                <StoryboardTab chapter={chapter} status={status} />
              ) : (
                <LockedPanel reason={storyboardBlockedReason} title="分镜" />
              ),
              disabled: !storyboardUnlocked(status),
              key: "storyboard",
              label: storyboardUnlocked(status) ? "分镜" : lockedLabel("分镜", storyboardLockReason(status)),
            },
            {
              children: assetsUnlocked(status) ? (
                <ProfilesAssetsTab chapter={chapter} />
              ) : (
                <LockedPanel reason={productionBlockedReason} title="资料与资产" />
              ),
              disabled: !assetsUnlocked(status),
              key: "assets",
              label: assetsUnlocked(status) ? "资料与资产" : lockedLabel("资料与资产", productionBlockedReason),
            },
            {
              children: shotPromptUnlocked(status) ? (
                <ShotPromptTab chapter={chapter} onOpenAssets={() => setActiveTab("assets")} />
              ) : (
                <LockedPanel reason={productionLockReason(status)} title="Shot Prompt" />
              ),
              disabled: !shotPromptUnlocked(status),
              key: "shot-prompt",
              label: shotPromptUnlocked(status)
                ? "Shot Prompt"
                : lockedLabel("Shot Prompt", productionLockReason(status)),
            },
            {
              children: agnesOpen && currentPromptRevision && chapter ? (
                <AgnesGenerationTab chapter={chapter} revision={currentPromptRevision} />
              ) : (
                <LockedPanel reason={agnesLockReason(status)} title="Agnes 生成" />
              ),
              disabled: !agnesOpen,
              key: "agnes",
              label: agnesOpen ? "Agnes 生成" : lockedLabel("Agnes 生成", agnesLockReason(status)),
            },
            {
              children: resultsOpen && chapter ? (
                <GenerationResultsTab chapter={chapter} />
              ) : (
                <LockedPanel reason={resultsBlockedReason} title="结果与重跑" />
              ),
              disabled: !resultsOpen,
              key: "results",
              label: resultsOpen ? "结果与重跑" : lockedLabel("结果与重跑", resultsBlockedReason),
            },
          ]}
        />
      )}
    </section>
  );
}

function useWorkflowRail(
  status?: ChapterStatus,
  statusUnavailable = false,
  statusLoading = false,
  agnesOpen = false,
  resultsOpen = false,
) {
  return useMemo(() => {
    if (statusUnavailable || statusLoading) {
      const reason = statusLoading ? "状态加载中" : "状态不可用";
      return [
        {
          color: statusLoading ? "processing" : "default",
          label: "原文完成",
          reason,
        },
        {
          color: "default",
          label: "剧本已确认",
          reason,
        },
        {
          color: "default",
          label: "分镜待确认",
          reason,
        },
      ];
    }

    const current = status?.status ?? "missing_source";
    const sourceDone = current !== "missing_source";
    const scriptDone = current === "script_approved" || current === "storyboard_draft" || storyboardDoneStatus(current);
    const storyboardDone = storyboardDoneStatus(current);
    const productionOpen = storyboardDone;
    const shotPromptStep = shotPromptRailStep(current, productionOpen);

    return [
      {
        color: sourceDone ? "success" : "processing",
        label: "原文完成",
        reason: sourceDone ? "" : "暂无小说原文",
      },
      {
        color: scriptDone ? "success" : sourceDone ? "processing" : "default",
        label: "剧本已确认",
        reason: scriptDone ? "" : "未确认剧本",
      },
      {
        color: storyboardDone ? "success" : "default",
        label: storyboardDone ? "分镜已确认" : "分镜待确认",
        reason: storyboardDone ? "" : storyboardLockReason(status),
      },
      {
        color: productionOpen ? "processing" : "default",
        label: productionOpen ? "资料与资产" : "资料与资产待解锁",
        reason: productionOpen ? "" : productionBlockedReason,
      },
      {
        color: shotPromptStep.color,
        label: shotPromptStep.label,
        reason: shotPromptStep.reason,
      },
      {
        color: agnesOpen ? "processing" : "default",
        label: agnesOpen ? "Agnes 生成" : "Agnes 生成已锁定",
        reason: agnesOpen ? "" : agnesBlockedReason,
      },
      {
        color: resultsOpen ? "processing" : "default",
        label: resultsOpen ? "结果与重跑" : "结果与重跑已锁定",
        reason: resultsOpen ? "" : resultsBlockedReason,
      },
    ];
  }, [agnesOpen, resultsOpen, status?.status, statusLoading, statusUnavailable]);
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

function useWorkflowGate(
  status: ChapterStatus | undefined,
  statusUnavailable: boolean,
  statusLoading: boolean,
  agnesOpen: boolean,
) {
  return useMemo(() => {
    if (statusUnavailable) {
      return { details: ["流程状态加载失败。请重试。"], summary: "流程状态暂不可用" };
    }
    if (statusLoading) {
      return { details: [], summary: "正在确认流程状态" };
    }

  const storyboardReason = storyboardLockReason(status);
  const productionReason = productionLockReason(status);
    const details = [
      !storyboardUnlocked(status) ? storyboardReason : "",
      !assetsUnlocked(status) ? productionReason : "",
      assetsUnlocked(status) && !agnesOpen ? agnesBlockedReason : "",
    ].filter((reason, index, reasons) => Boolean(reason) && reasons.indexOf(reason) === index);

    return {
      details,
      summary: details.length ? "完成当前确认后可解锁后续步骤" : "当前阶段可继续进行",
    };
  }, [agnesOpen, status, statusLoading, statusUnavailable]);
}

function productionLockReason(status?: ChapterStatus) {
  return storyboardDoneStatus(status?.status ?? "") ? agnesBlockedReason : productionBlockedReason;
}

function agnesLockReason(status?: ChapterStatus) {
  return shotPromptUnlocked(status) ? agnesBlockedReason : productionBlockedReason;
}

function storyboardLockReason(status?: ChapterStatus) {
  return storyboardUnlocked(status) ? "" : storyboardBlockedReason;
}

function storyboardUnlocked(status?: ChapterStatus) {
  const current = status?.status ?? "";
  return ["script_approved", "storyboard_draft"].includes(current) || storyboardDoneStatus(current);
}

function assetsUnlocked(status?: ChapterStatus) {
  return storyboardDoneStatus(status?.status ?? "");
}

function shotPromptUnlocked(status?: ChapterStatus) {
  return storyboardDoneStatus(status?.status ?? "");
}

function storyboardDoneStatus(status: string) {
  return ["storyboard_approved", "assets_incomplete", "assets_ready", "prompts_draft", "prompts_ready"].includes(status);
}

function shotPromptRailStep(status: string, productionOpen: boolean) {
  if (!productionOpen) {
    return {
      color: "default",
      label: "Shot Prompt 待解锁",
      reason: productionBlockedReason,
    };
  }
  if (status === "assets_ready") {
    return {
      color: "processing",
      label: "Shot Prompt 可生成",
      reason: "",
    };
  }
  if (status === "prompts_draft") {
    return {
      color: "processing",
      label: "Shot Prompt 待确认",
      reason: "检查并标记镜头 Ready",
    };
  }
  if (status === "prompts_ready") {
    return {
      color: "success",
      label: "Shot Prompt 已就绪",
      reason: "",
    };
  }
  return {
    color: "default",
    label: "Shot Prompt 待生成",
    reason: "等待资产需求 ready",
  };
}

function lockedLabel(label: string, reason: string) {
  return (
    <span title={reason}>
      {label} <Typography.Text type="secondary">已锁定</Typography.Text>
    </span>
  );
}

function LockedPanel({ reason, title }: { reason: string; title: string }) {
  return <Alert message={`${title} 已锁定`} description={reason} showIcon type="info" />;
}
