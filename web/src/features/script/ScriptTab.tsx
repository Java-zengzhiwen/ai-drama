import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Skeleton, Tag, Typography } from "antd";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ChapterRead } from "../projects/api";
import {
  approveScriptRevision,
  generateScript,
  listScriptRevisions,
  rejectScriptRevision,
  updateScriptRevision,
  type ScriptGenerationRunRead,
  type ScriptRevisionRead,
  type ValidationResultRead,
} from "./api";
import { useScriptGenerationStream } from "./useScriptGenerationStream";

type ScriptTabProps = {
  activeRun?: ScriptGenerationRunRead | null;
  chapter: ChapterRead;
  onGenerationCompleted?: () => void;
  onRegenerateRequested?: () => void;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

type ScriptEditInput = {
  content: string;
  revisionId: string;
};

export function ScriptTab({ activeRun = null, chapter, onGenerationCompleted, onRegenerateRequested }: ScriptTabProps) {
  const queryClient = useQueryClient();
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [draft, setDraft] = useState("");
  const [loadedRevisionId, setLoadedRevisionId] = useState("");
  const [isDraftDirty, setIsDraftDirty] = useState(false);
  const stream = useScriptGenerationStream(activeRun);

  const revisionsQuery = useQuery({
    enabled: Boolean(chapter.chapter_id),
    queryKey: ["script-revisions", chapter.chapter_id],
    queryFn: () => listScriptRevisions(chapter.chapter_id),
  });

  const revisions = revisionsQuery.data ?? [];
  const selectedRevision = useMemo(
    () => selectRevision(revisions, selectedRevisionId),
    [revisions, selectedRevisionId],
  );

  useEffect(() => {
    if (selectedRevision && !selectedRevisionId) {
      setSelectedRevisionId(selectedRevision.revision_id);
      setDraft(selectedRevision.content);
      setLoadedRevisionId(selectedRevision.revision_id);
      setIsDraftDirty(false);
      return;
    }
    if (!selectedRevision && revisions.length > 0) {
      const latestRevision = revisions[revisions.length - 1];
      setSelectedRevisionId(latestRevision.revision_id);
      setDraft(latestRevision.content);
      setLoadedRevisionId(latestRevision.revision_id);
      setIsDraftDirty(false);
      return;
    }
    if (selectedRevision && selectedRevision.revision_id !== loadedRevisionId && !isDraftDirty) {
      setDraft(selectedRevision.content);
      setLoadedRevisionId(selectedRevision.revision_id);
      setIsDraftDirty(false);
    }
  }, [isDraftDirty, loadedRevisionId, revisions, selectedRevision]);

  useEffect(() => {
    if (stream.revisionId) {
      void queryClient.invalidateQueries({ queryKey: ["script-revisions", chapter.chapter_id] });
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    }
  }, [chapter.chapter_id, queryClient, stream.revisionId]);

  useEffect(() => {
    if (!stream.revisionId) {
      return;
    }
    const completedRevision = revisions.find(
      (revision) => revision.revision_id === stream.revisionId,
    );
    if (!completedRevision) {
      return;
    }
    setSelectedRevisionId(completedRevision.revision_id);
    setDraft(completedRevision.content);
    setLoadedRevisionId(completedRevision.revision_id);
    setIsDraftDirty(false);
    stream.clear();
    onGenerationCompleted?.();
  }, [onGenerationCompleted, revisions, stream.clear, stream.revisionId]);

  const generateMutation = useMutation({
    mutationFn: () => generateScript(chapter.chapter_id),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const saveMutation = useMutation({
    mutationFn: ({ content, revisionId }: ScriptEditInput) => updateScriptRevision(revisionId, { content }),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (revisionId: string) =>
      approveScriptRevision(revisionId, {
        reviewer: "local-user",
        note: "",
      }),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (revisionId: string) =>
      rejectScriptRevision(revisionId, {
        reviewer: "local-user",
        note: "",
      }),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const isScriptMutating =
    (stream.active && !stream.terminal) ||
    generateMutation.isPending ||
    saveMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending;

  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedRevision || isScriptMutating) {
      return;
    }
    saveMutation.mutate({
      content: draft.trim(),
      revisionId: selectedRevision.revision_id,
    });
  }

  function loadRevisionForEditing(revision: ScriptRevisionRead) {
    setSelectedRevisionId(revision.revision_id);
    setDraft(revision.content);
    setLoadedRevisionId(revision.revision_id);
    setIsDraftDirty(false);
  }

  if (revisionsQuery.isLoading && !stream.active) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  if (revisionsQuery.isError && !stream.active) {
    return (
      <WorkflowErrorAlert
        error={revisionsQuery.error}
        fallbackMessage="剧本加载失败。请重试。"
        onRetry={() => void revisionsQuery.refetch()}
      />
    );
  }

  return (
    <section aria-label="剧本工作台" className="production-workbench script-workbench">
      {!chapter.current_source_revision_id ? (
        <Alert message="暂无剧本。保存原文后生成剧本。" showIcon type="info" />
      ) : null}

      <div className="production-command-bar">
        <Button
          disabled={!chapter.current_source_revision_id || isScriptMutating}
          loading={generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
          type="primary"
        >
          生成剧本
        </Button>
        {selectedRevision ? <StatusChip status={selectedRevision.approval_status} /> : null}
      </div>

      {stream.active ? (
        <LiveScriptDraft
          onRegenerateRequested={onRegenerateRequested}
          stream={stream}
        />
      ) : null}

      {generateMutation.isError ? (
        <WorkflowErrorAlert
          error={generateMutation.error}
          fallbackMessage="剧本生成失败。请重试。"
          onRetry={() => generateMutation.mutate()}
        />
      ) : null}
      {saveMutation.isError ? (
        <WorkflowErrorAlert
          error={saveMutation.error}
          fallbackMessage="剧本保存失败。请重试。"
          onRetry={() => {
            if (saveMutation.variables) {
              saveMutation.mutate(saveMutation.variables);
            }
          }}
        />
      ) : null}
      {approveMutation.isError ? (
        <WorkflowErrorAlert
          error={approveMutation.error}
          fallbackMessage="剧本确认失败。请重试。"
          onRetry={() => {
            if (approveMutation.variables) {
              approveMutation.mutate(approveMutation.variables);
            }
          }}
        />
      ) : null}
      {rejectMutation.isError ? (
        <WorkflowErrorAlert
          error={rejectMutation.error}
          fallbackMessage="剧本拒绝失败。请重试。"
          onRetry={() => {
            if (rejectMutation.variables) {
              rejectMutation.mutate(rejectMutation.variables);
            }
          }}
        />
      ) : null}

      {stream.active ? null : revisions.length === 0 ? (
        <Typography.Text type="secondary">暂无剧本。保存原文后生成剧本。</Typography.Text>
      ) : (
        <div className="revision-workspace">
          <div className="revision-strip">
            {revisions.map((revision) => (
              <Button
                disabled={isScriptMutating}
                key={revision.revision_id}
                onClick={() => loadRevisionForEditing(revision)}
                type={revision.revision_id === selectedRevision?.revision_id ? "primary" : "default"}
              >
                Revision {revision.number}
              </Button>
            ))}
          </div>

          {selectedRevision ? (
            <form aria-label="剧本编辑" className="script-editor-panel" onSubmit={submitEdit}>
              <label className="editor-field">
                <span>剧本内容</span>
                <Input.TextArea
                  aria-label="剧本内容"
                  autoSize={{ minRows: 12 }}
                  disabled={isScriptMutating}
                  onChange={(event) => {
                    setDraft(event.target.value);
                    setIsDraftDirty(true);
                  }}
                  value={draft}
                />
              </label>
              <div className="production-action-footer">
                <Button disabled={!draft.trim() || isScriptMutating} htmlType="submit" loading={saveMutation.isPending}>
                  保存为新剧本版本
                </Button>
                <Button
                  disabled={selectedRevision.approval_status === "approved" || isDraftDirty || isScriptMutating}
                  loading={approveMutation.isPending}
                  onClick={() => approveMutation.mutate(selectedRevision.revision_id)}
                  type="primary"
                >
                  确认剧本
                </Button>
                <Button
                  disabled={selectedRevision.approval_status === "approved" || isDraftDirty || isScriptMutating}
                  loading={rejectMutation.isPending}
                  onClick={() => rejectMutation.mutate(selectedRevision.revision_id)}
                >
                  拒绝剧本
                </Button>
              </div>
            </form>
          ) : null}

          <ValidationTable rows={selectedRevision?.validation_results ?? []} />
        </div>
      )}
    </section>
  );
}

function LiveScriptDraft({
  onRegenerateRequested,
  stream,
}: {
  onRegenerateRequested?: () => void;
  stream: ReturnType<typeof useScriptGenerationStream>;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [followOutput, setFollowOutput] = useState(true);
  const elapsedSeconds = useElapsedSeconds(stream.active && !stream.terminal, stream.startedAt);
  const statusLabel = stream.reconnecting
    ? "正在重新连接"
    : stream.stage === "validating"
      ? "正在校验并保存"
      : stream.stage === "finalizing" || stream.status === "finalizing"
        ? "正在整理完整剧本"
      : stream.status === "completed"
        ? "正在加载正式版本"
      : stream.status === "failed"
        ? "生成中断"
        : stream.status === "unknown_outcome"
          ? "生成状态待确认"
          : stream.text
            ? "正在生成"
            : "正在等待模型响应";

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea && followOutput) {
      textarea.scrollTop = textarea.scrollHeight;
    }
  }, [followOutput, stream.text]);

  return (
    <section
      aria-busy={!stream.terminal}
      aria-label="实时剧本草稿"
      className="script-live-panel"
      data-terminal={stream.terminal}
    >
      <header className="script-live-header">
        <div>
          <strong>实时草稿</strong>
          <span aria-hidden="true" className="script-live-pulse" data-active={!stream.terminal} />
          <span aria-live="polite">{statusLabel}</span>
        </div>
        <div className="script-live-metrics">
          <span>{stream.characterCount.toLocaleString("zh-CN")} 字</span>
          <span>{formatElapsed(elapsedSeconds)}</span>
        </div>
      </header>
      <div className="script-live-editor">
        <textarea
          aria-label="实时剧本内容"
          autoFocus
          onScroll={(event) => {
            const target = event.currentTarget;
            setFollowOutput(target.scrollHeight - target.scrollTop - target.clientHeight < 80);
          }}
          placeholder="模型返回的剧本内容会逐字显示在这里……"
          readOnly
          ref={textareaRef}
          value={stream.text}
        />
        {!followOutput ? (
          <Button
            className="script-follow-output"
            onClick={() => {
              setFollowOutput(true);
              textareaRef.current?.scrollTo({
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
                  ? "auto"
                  : "smooth",
                top: textareaRef.current.scrollHeight,
              });
            }}
            size="small"
          >
            回到生成末尾
          </Button>
        ) : null}
      </div>
      {stream.status === "failed" || stream.status === "unknown_outcome" ? (
        <div className="script-live-failure">
          <Alert
            description={stream.errorCode || undefined}
            message="生成中断 · 该内容尚未保存为正式剧本版本"
            showIcon
            type="error"
          />
          <div className="script-live-failure-actions">
            <Button onClick={() => void navigator.clipboard?.writeText(stream.text)}>
              复制部分草稿
            </Button>
            <Button onClick={onRegenerateRequested} type="primary">
              返回原文重新生成
            </Button>
          </div>
        </div>
      ) : (
        <div className="script-live-notice">生成完成并通过校验后，将自动保存为正式剧本版本。</div>
      )}
    </section>
  );
}

function useElapsedSeconds(active: boolean, startedAt: number) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  useEffect(() => {
    if (!active) {
      return;
    }
    const update = () => setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [active, startedAt]);
  return elapsedSeconds;
}

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function selectRevision(revisions: ScriptRevisionRead[], selectedRevisionId: string) {
  if (selectedRevisionId) {
    const selected = revisions.find((revision) => revision.revision_id === selectedRevisionId);
    if (selected) {
      return selected;
    }
  }
  return revisions.find((revision) => revision.current) ?? revisions[revisions.length - 1];
}

function upsertRevision(queryClient: ReturnType<typeof useQueryClient>, chapterId: string, revision: ScriptRevisionRead) {
  queryClient.setQueryData<ScriptRevisionRead[]>(["script-revisions", chapterId], (current = []) => {
    const next = current.filter((item) => item.revision_id !== revision.revision_id);
    return [...next, revision].sort((left, right) => left.number - right.number);
  });
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
      description={details.code ? details.code : undefined}
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

function StatusChip({ status }: { status: string }) {
  const labelByStatus: Record<string, string> = {
    approved: "已确认",
    pending: "待确认",
    rejected: "已拒绝",
    superseded: "已替换",
  };
  const colorByStatus: Record<string, string> = {
    approved: "success",
    pending: "processing",
    rejected: "error",
    superseded: "default",
  };

  return <Tag color={colorByStatus[status] ?? "default"}>{labelByStatus[status] ?? status}</Tag>;
}

function ValidationTable({ rows }: { rows: ValidationResultRead[] }) {
  if (rows.length === 0) {
    return <Typography.Text type="secondary">暂无 QC 结果。</Typography.Text>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table
        aria-label="剧本 QC"
        style={{
          background: "#ffffff",
          border: "1px solid #d9dee8",
          borderCollapse: "collapse",
          minWidth: 560,
          width: "100%",
        }}
      >
        <thead style={{ background: "#f9fafc" }}>
          <tr>
            <th style={tableHeaderStyle}>QC</th>
            <th style={tableHeaderStyle}>状态</th>
            <th style={tableHeaderStyle}>级别</th>
            <th style={tableHeaderStyle}>错误码</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.validation_id}>
              <td style={tableCellStyle}>{row.validator_id}</td>
              <td style={tableCellStyle}>{row.status}</td>
              <td style={tableCellStyle}>{row.required ? "必需" : "可选"}</td>
              <td style={tableCellStyle}>{row.error_code || "无"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const tableHeaderStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#5f6b7a",
  fontSize: 12,
  fontWeight: 600,
  padding: "10px 12px",
  textAlign: "left" as const,
};

const tableCellStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#1f2937",
  padding: "10px 12px",
};
