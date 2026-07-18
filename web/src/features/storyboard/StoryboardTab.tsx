import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Skeleton, Tag, Typography } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChapterStatus } from "../projects/api";
import type { ChapterRead } from "../projects/api";
import type { ValidationResultRead } from "../script/api";
import {
  approveStoryboardRevision,
  generateStoryboard,
  listStoryboardRevisions,
  rejectStoryboardRevision,
  updateStoryboardRevision,
  validateStoryboardRevision,
  type StoryboardRevisionRead,
} from "./api";
import { ShotEditor, type CanonicalShot } from "./ShotEditor";

type StoryboardTabProps = {
  chapter: ChapterRead;
  status?: ChapterStatus;
};

type CanonicalStoryboard = {
  schema_version?: string;
  shots?: CanonicalShot[];
  [key: string]: unknown;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

type SaveInput = {
  content: string;
  revisionId: string;
};

const storyboardBlockedReason = "未确认剧本，不允许生成分镜。";
const enabledStatuses = new Set([
  "script_approved",
  "storyboard_draft",
  "storyboard_approved",
  "assets_incomplete",
  "assets_ready",
  "prompts_draft",
  "prompts_ready",
]);
const tableFields: Array<keyof CanonicalShot> = [
  "shot_order",
  "duration_seconds",
  "shot_size",
  "camera_angle",
  "camera_movement",
  "visual_composition",
  "character_positions",
  "character_actions",
  "emotion_performance",
  "dialogue",
  "continuity_in",
  "continuity_out",
];

export function StoryboardTab({ chapter, status }: StoryboardTabProps) {
  const queryClient = useQueryClient();
  const enabled = enabledStatuses.has(status?.status ?? "");
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [loadedRevisionId, setLoadedRevisionId] = useState("");
  const [selectedShotId, setSelectedShotId] = useState("");
  const [canonicalDraft, setCanonicalDraft] = useState<CanonicalStoryboard | null>(null);
  const [invalidJsonFields, setInvalidJsonFields] = useState<Set<string>>(new Set());
  const [isDraftDirty, setIsDraftDirty] = useState(false);

  const revisionsQuery = useQuery({
    enabled: Boolean(chapter.chapter_id) && enabled,
    queryKey: ["storyboard-revisions", chapter.chapter_id],
    queryFn: () => listStoryboardRevisions(chapter.chapter_id),
  });

  const revisions = revisionsQuery.data ?? [];
  const selectedRevision = useMemo(
    () => selectRevision(revisions, selectedRevisionId),
    [revisions, selectedRevisionId],
  );
  const shots = canonicalDraft?.shots ?? [];
  const selectedShot = shots.find((shot) => shot.shot_id === selectedShotId) ?? shots[0];

  useEffect(() => {
    if (!selectedRevision) {
      if (revisions.length === 0 && !isDraftDirty) {
        setCanonicalDraft(null);
        setSelectedShotId("");
      }
      return;
    }
    if (!selectedRevisionId) {
      loadRevisionForEditing(selectedRevision);
      return;
    }
    if (selectedRevision.revision_id !== loadedRevisionId && !isDraftDirty) {
      loadRevisionForEditing(selectedRevision);
    }
  }, [isDraftDirty, loadedRevisionId, revisions.length, selectedRevision, selectedRevisionId]);

  const generateMutation = useMutation({
    mutationFn: () => generateStoryboard(chapter.chapter_id),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const saveMutation = useMutation({
    mutationFn: ({ content, revisionId }: SaveInput) => updateStoryboardRevision(revisionId, { content }),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const validateMutation = useMutation({
    mutationFn: (revisionId: string) => validateStoryboardRevision(revisionId),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
    },
  });

  const approveMutation = useMutation({
    mutationFn: (revisionId: string) =>
      approveStoryboardRevision(revisionId, {
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
      rejectStoryboardRevision(revisionId, {
        reviewer: "local-user",
        note: "",
      }),
    onSuccess: (revision) => {
      upsertRevision(queryClient, chapter.chapter_id, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: ["chapter-status", chapter.chapter_id] });
    },
  });

  const isStoryboardMutating =
    generateMutation.isPending ||
    saveMutation.isPending ||
    validateMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending;
  const hasInvalidJson = invalidJsonFields.size > 0;
  const canGenerateStoryboard = !isDraftDirty && !hasInvalidJson && !isStoryboardMutating;
  const currentSaveInput =
    selectedRevision && canonicalDraft
      ? {
          revisionId: selectedRevision.revision_id,
          content: JSON.stringify(canonicalDraft, null, 2),
        }
      : null;
  const canSaveDraft = Boolean(currentSaveInput && isDraftDirty && !hasInvalidJson && !isStoryboardMutating);
  const canRetrySave = Boolean(
    currentSaveInput &&
      saveMutation.variables &&
      !hasInvalidJson &&
      !isStoryboardMutating &&
      saveMutation.variables.revisionId === currentSaveInput.revisionId &&
      saveMutation.variables.content === currentSaveInput.content,
  );
  const canApproveStoryboard = Boolean(
    selectedRevision &&
      selectedRevision.approval_status !== "approved" &&
      !isDraftDirty &&
      !hasInvalidJson &&
      !isStoryboardMutating,
  );
  const canRejectStoryboard = canApproveStoryboard;
  const canValidateStoryboard = Boolean(selectedRevision && !isDraftDirty && !hasInvalidJson && !isStoryboardMutating);
  const canRetryValidate = Boolean(canValidateStoryboard && validateMutation.variables === selectedRevision?.revision_id);
  const canRetryApprove = Boolean(canApproveStoryboard && approveMutation.variables === selectedRevision?.revision_id);
  const canRetryReject = Boolean(canRejectStoryboard && rejectMutation.variables === selectedRevision?.revision_id);

  function loadRevisionForEditing(revision: StoryboardRevisionRead) {
    const canonical = parseCanonical(revision.content);
    setSelectedRevisionId(revision.revision_id);
    setLoadedRevisionId(revision.revision_id);
    setCanonicalDraft(canonical);
    setInvalidJsonFields(new Set());
    setSelectedShotId(canonical.shots?.[0]?.shot_id ?? "");
    setIsDraftDirty(false);
  }

  function updateShot(field: keyof CanonicalShot, value: unknown) {
    if (!selectedShot) {
      return;
    }
    setCanonicalDraft((current) => {
      if (!current?.shots) {
        return current;
      }
      return {
        ...current,
        shots: current.shots.map((shot) =>
          shot.shot_id === selectedShot.shot_id ? { ...shot, [field]: value } : shot,
        ),
      };
    });
    setIsDraftDirty(true);
  }

  const updateJsonValidity = useCallback((field: keyof CanonicalShot, isValid: boolean) => {
    setInvalidJsonFields((current) => {
      const next = new Set(current);
      if (isValid) {
        next.delete(String(field));
      } else {
        next.add(String(field));
      }
      return next;
    });
    if (!isValid) {
      setIsDraftDirty(true);
    }
  }, []);

  function saveAsNewRevision() {
    if (!canSaveDraft || !currentSaveInput) {
      return;
    }
    saveMutation.mutate(currentSaveInput);
  }

  if (!enabled) {
    return (
      <section aria-label="分镜工作台" style={{ display: "grid", gap: 12 }}>
        <Alert message={storyboardBlockedReason} showIcon type="info" />
        <Button disabled type="primary">
          生成分镜
        </Button>
      </section>
    );
  }

  if (revisionsQuery.isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  if (revisionsQuery.isError) {
    return (
      <WorkflowErrorAlert
        error={revisionsQuery.error}
        fallbackMessage="分镜加载失败。请重试。"
        onRetry={() => void revisionsQuery.refetch()}
      />
    );
  }

  return (
    <section aria-label="分镜工作台" className="production-workbench storyboard-workbench">
      <div className="production-command-bar">
        <Button
          disabled={!canGenerateStoryboard}
          loading={generateMutation.isPending}
          onClick={() => {
            if (canGenerateStoryboard) {
              generateMutation.mutate();
            }
          }}
          type="primary"
        >
          生成分镜
        </Button>
        {selectedRevision ? <StatusChip status={selectedRevision.approval_status} /> : null}
      </div>

      {generateMutation.isError ? (
        <WorkflowErrorAlert
          disabled={!canGenerateStoryboard}
          error={generateMutation.error}
          fallbackMessage="分镜生成失败。请重试。"
          onRetry={() => {
            if (canGenerateStoryboard) {
              generateMutation.mutate();
            }
          }}
        />
      ) : null}
      {saveMutation.isError ? (
        <WorkflowErrorAlert
          disabled={!canRetrySave}
          error={saveMutation.error}
          fallbackMessage="分镜保存失败。请重试。"
          onRetry={() => {
            if (canRetrySave && saveMutation.variables) {
              saveMutation.mutate(saveMutation.variables);
            }
          }}
        />
      ) : null}
      {validateMutation.isError ? (
        <WorkflowErrorAlert
          disabled={!canRetryValidate}
          error={validateMutation.error}
          fallbackMessage="分镜验证失败。请重试。"
          onRetry={() => {
            if (canRetryValidate && validateMutation.variables) {
              validateMutation.mutate(validateMutation.variables);
            }
          }}
        />
      ) : null}
      {approveMutation.isError ? (
        <WorkflowErrorAlert
          disabled={!canRetryApprove}
          error={approveMutation.error}
          fallbackMessage="分镜确认失败。请重试。"
          onRetry={() => {
            if (canRetryApprove && approveMutation.variables) {
              approveMutation.mutate(approveMutation.variables);
            }
          }}
        />
      ) : null}
      {rejectMutation.isError ? (
        <WorkflowErrorAlert
          disabled={!canRetryReject}
          error={rejectMutation.error}
          fallbackMessage="分镜拒绝失败。请重试。"
          onRetry={() => {
            if (canRetryReject && rejectMutation.variables) {
              rejectMutation.mutate(rejectMutation.variables);
            }
          }}
        />
      ) : null}

      {revisions.length === 0 ? (
        <Typography.Text type="secondary">暂无分镜。确认剧本后生成分镜。</Typography.Text>
      ) : (
        <div className="storyboard-layout">
          <div className="storyboard-table-column">
            <div className="revision-strip">
              {revisions.map((revision) => (
                <Button
                  disabled={isDraftDirty || isStoryboardMutating}
                  key={revision.revision_id}
                  onClick={() => loadRevisionForEditing(revision)}
                  type={revision.revision_id === selectedRevision?.revision_id ? "primary" : "default"}
                >
                  Revision {revision.number}
                </Button>
              ))}
            </div>
            <ShotTable
              disabled={hasInvalidJson || isStoryboardMutating}
              onSelect={setSelectedShotId}
              selectedShotId={selectedShot?.shot_id ?? ""}
              shots={shots}
            />
            <ValidationTable rows={selectedRevision?.validation_results ?? []} />
          </div>

          <aside
            aria-label="分镜 inspector"
            className="production-inspector storyboard-inspector"
            style={{
              border: "1px solid #d9dee8",
              borderRadius: 6,
              display: "grid",
              gap: 12,
              padding: 12,
            }}
          >
            <ShotEditor
              disabled={isStoryboardMutating}
              onChange={updateShot}
              onJsonValidityChange={updateJsonValidity}
              resetKey={`${loadedRevisionId}:${selectedShot?.shot_id ?? ""}`}
              shot={selectedShot}
            />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <Button
                disabled={!canSaveDraft}
                loading={saveMutation.isPending}
                onClick={saveAsNewRevision}
              >
                保存为新分镜版本
              </Button>
              <Button
                disabled={!canValidateStoryboard}
                loading={validateMutation.isPending}
                onClick={() => selectedRevision && validateMutation.mutate(selectedRevision.revision_id)}
              >
                运行分镜验证
              </Button>
              <Button
                disabled={!canApproveStoryboard}
                loading={approveMutation.isPending}
                onClick={() => selectedRevision && approveMutation.mutate(selectedRevision.revision_id)}
                type="primary"
              >
                确认分镜
              </Button>
              <Button
                disabled={!canRejectStoryboard}
                loading={rejectMutation.isPending}
                onClick={() => selectedRevision && rejectMutation.mutate(selectedRevision.revision_id)}
              >
                拒绝分镜
              </Button>
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}

function parseCanonical(content: string): CanonicalStoryboard {
  const parsed = JSON.parse(content) as CanonicalStoryboard;
  return {
    ...parsed,
    shots: parsed.shots ?? [],
  };
}

function selectRevision(revisions: StoryboardRevisionRead[], selectedRevisionId: string) {
  if (selectedRevisionId) {
    const selected = revisions.find((revision) => revision.revision_id === selectedRevisionId);
    if (selected) {
      return selected;
    }
  }
  return revisions.find((revision) => revision.current) ?? revisions[revisions.length - 1];
}

function upsertRevision(
  queryClient: ReturnType<typeof useQueryClient>,
  chapterId: string,
  revision: StoryboardRevisionRead,
) {
  queryClient.setQueryData<StoryboardRevisionRead[]>(["storyboard-revisions", chapterId], (current = []) => {
    const next = current.filter((item) => item.revision_id !== revision.revision_id);
    return [...next, revision].sort((left, right) => left.number - right.number);
  });
}

function ShotTable({
  disabled,
  onSelect,
  selectedShotId,
  shots,
}: {
  disabled: boolean;
  onSelect: (shotId: string) => void;
  selectedShotId: string;
  shots: CanonicalShot[];
}) {
  if (shots.length === 0) {
    return <Typography.Text type="secondary">当前 revision 没有 canonical shots。</Typography.Text>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table aria-label="Canonical shot table" style={tableStyle}>
        <thead style={{ background: "#f9fafc" }}>
          <tr>
            <th style={tableHeaderStyle}>shot_id</th>
            {tableFields.map((field) => (
              <th key={String(field)} style={tableHeaderStyle}>
                {field}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shots.map((shot) => (
            <tr
              aria-selected={shot.shot_id === selectedShotId}
              key={shot.shot_id}
              style={shot.shot_id === selectedShotId ? selectedRowStyle : undefined}
            >
              <td style={tableCellStyle}>
                <Button disabled={disabled} onClick={() => onSelect(shot.shot_id)} size="small" type="link">
                  {shot.shot_id}
                </Button>
              </td>
              {tableFields.map((field) => (
                <td key={String(field)} style={tableCellStyle}>
                  {formatTableValue(shot[field])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ValidationTable({ rows }: { rows: ValidationResultRead[] }) {
  if (rows.length === 0) {
    return <Typography.Text type="secondary">暂无 QC 结果。</Typography.Text>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table aria-label="分镜 QC" style={tableStyle}>
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

function WorkflowErrorAlert({
  disabled = false,
  error,
  fallbackMessage,
  onRetry,
}: {
  disabled?: boolean;
  error: unknown;
  fallbackMessage: string;
  onRetry: () => void;
}) {
  const details = getApiErrorDetails(error, fallbackMessage);

  return (
    <Alert
      action={
        <Button disabled={disabled} onClick={onRetry}>
          重试
        </Button>
      }
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

function formatTableValue(value: unknown) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

const tableStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderCollapse: "collapse" as const,
  minWidth: 980,
  width: "100%",
};

const tableHeaderStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#5f6b7a",
  fontSize: 12,
  fontWeight: 600,
  padding: "10px 12px",
  textAlign: "left" as const,
  verticalAlign: "top" as const,
};

const tableCellStyle = {
  borderBottom: "1px solid #d9dee8",
  color: "#1f2937",
  maxWidth: 220,
  padding: "10px 12px",
  verticalAlign: "top" as const,
};

const selectedRowStyle = {
  background: "#eef6ff",
};
