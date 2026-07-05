import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Skeleton, Tabs, Tag, Typography } from "antd";
import { useMemo } from "react";
import { getChapterStatus, type ChapterStatus } from "../projects/api";
import { ScriptTab } from "../script/ScriptTab";
import { getChapter } from "../script/api";
import { SourceTab } from "./SourceTab";

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

export function ChapterWorkspace({ chapterId, projectId }: ChapterWorkspaceProps) {
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

  const status = statusQuery.data;
  const rail = useWorkflowRail(status, statusQuery.isError, statusQuery.isLoading);

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
    <section aria-labelledby="chapter-workspace-title" style={{ display: "grid", gap: 18 }}>
      <div>
        <Typography.Title id="chapter-workspace-title" level={1} style={{ fontSize: 22, margin: 0 }}>
          {chapter?.title ?? "章节工作区"}
        </Typography.Title>
        <Typography.Text type="secondary">
          Project {projectId} / Chapter {chapterId}
        </Typography.Text>
      </div>

      <div
        aria-label="workflow rail"
        style={{
          background: "#ffffff",
          border: "1px solid #d9dee8",
          borderRadius: 6,
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          padding: 12,
        }}
      >
        {rail.map((item) => (
          <Tag color={item.color} key={item.label}>
            {item.label}
            {item.reason ? `：${item.reason}` : ""}
          </Tag>
        ))}
      </div>

      {statusQuery.isError ? (
        <WorkflowErrorAlert
          error={statusQuery.error}
          fallbackMessage="流程状态加载失败。请重试。"
          onRetry={() => void statusQuery.refetch()}
        />
      ) : null}

      <LockedReasons status={status} />

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
          items={[
            {
              children: <SourceTab chapter={chapter} />,
              key: "source",
              label: "原文",
            },
            {
              children: <ScriptTab chapter={chapter} />,
              key: "script",
              label: "剧本",
            },
            {
              children: <LockedPanel reason={storyboardBlockedReason} title="分镜" />,
              disabled: true,
              key: "storyboard",
              label: lockedLabel("分镜", storyboardLockReason(status)),
            },
            {
              children: <LockedPanel reason={productionBlockedReason} title="资料与资产" />,
              disabled: true,
              key: "assets",
              label: lockedLabel("资料与资产", productionBlockedReason),
            },
            {
              children: <LockedPanel reason={productionBlockedReason} title="Shot Prompt" />,
              disabled: true,
              key: "shot-prompt",
              label: lockedLabel("Shot Prompt", productionBlockedReason),
            },
            {
              children: <LockedPanel reason={productionBlockedReason} title="Agnes 生成" />,
              disabled: true,
              key: "agnes",
              label: lockedLabel("Agnes 生成", productionBlockedReason),
            },
            {
              children: <LockedPanel reason={productionBlockedReason} title="结果与重跑" />,
              disabled: true,
              key: "results",
              label: lockedLabel("结果与重跑", productionBlockedReason),
            },
          ]}
        />
      )}
    </section>
  );
}

function useWorkflowRail(status?: ChapterStatus, statusUnavailable = false, statusLoading = false) {
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
    const scriptDone = current === "script_approved" || current === "storyboard_draft" || current === "storyboard_approved";
    const storyboardDone = current === "storyboard_approved";

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
    ];
  }, [status?.status, statusLoading, statusUnavailable]);
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

function LockedReasons({ status }: { status?: ChapterStatus }) {
  const storyboardReason = storyboardLockReason(status);

  return (
    <div aria-label="locked tab reasons" style={{ display: "grid", gap: 8 }}>
      {status?.status !== "storyboard_approved" ? (
        <Alert message="分镜已锁定" description={storyboardReason} showIcon type="info" />
      ) : null}
      <Alert message="后续生产步骤已锁定" description={productionBlockedReason} showIcon type="info" />
    </div>
  );
}

function storyboardLockReason(status?: ChapterStatus) {
  return status?.status === "script_approved" ? "分镜编辑将在下一任务实现。" : storyboardBlockedReason;
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
