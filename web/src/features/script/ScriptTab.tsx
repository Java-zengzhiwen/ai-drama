import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Skeleton, Tag, Typography } from "antd";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import type { ChapterRead } from "../projects/api";
import {
  approveScriptRevision,
  generateScript,
  listScriptRevisions,
  rejectScriptRevision,
  updateScriptRevision,
  type ScriptRevisionRead,
  type ValidationResultRead,
} from "./api";

type ScriptTabProps = {
  chapter: ChapterRead;
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

export function ScriptTab({ chapter }: ScriptTabProps) {
  const queryClient = useQueryClient();
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [draft, setDraft] = useState("");
  const [loadedRevisionId, setLoadedRevisionId] = useState("");
  const [isDraftDirty, setIsDraftDirty] = useState(false);

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

  if (revisionsQuery.isLoading) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  if (revisionsQuery.isError) {
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

      {revisions.length === 0 ? (
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
