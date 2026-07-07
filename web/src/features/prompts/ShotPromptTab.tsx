import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Skeleton, Tabs, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import type { ChapterRead } from "../projects/api";
import {
  analyzeAssetRequirements,
  generateShotPrompts,
  getAgnesPreview,
  latestAssetRequirements,
  listShotPromptRevisions,
  markShotPromptReady,
  regenerateShotPrompt,
  updateShotPromptRevision,
  type AgnesPreviewRead,
  type ShotPromptCanonical,
  type ShotPromptRevisionRead,
  type ShotPromptShot,
  type ShotPromptStatus,
} from "./api";
import { AssetRequirementPanel } from "./AssetRequirementPanel";
import { AssetRefsPreview, ShotPromptEditor } from "./ShotPromptEditor";

type ShotPromptTabProps = {
  chapter: ChapterRead;
  onOpenAssets?: () => void;
};

type ApiError = {
  response?: {
    data?: {
      error_code?: string;
      error_message?: string;
    };
  };
};

export function ShotPromptTab({ chapter, onOpenAssets }: ShotPromptTabProps) {
  const queryClient = useQueryClient();
  const requirementsQueryKey = ["asset-requirements", chapter.chapter_id];
  const revisionsQueryKey = ["shot-prompt-revisions", chapter.chapter_id];
  const [selectedRevisionId, setSelectedRevisionId] = useState("");
  const [loadedRevisionId, setLoadedRevisionId] = useState("");
  const [selectedShotId, setSelectedShotId] = useState("");
  const [canonicalDraft, setCanonicalDraft] = useState<ShotPromptCanonical | null>(null);
  const [isDraftDirty, setIsDraftDirty] = useState(false);
  const [selectedReadiness, setSelectedReadiness] = useState<ShotPromptRevisionRead["readiness"]>({});
  const [preview, setPreview] = useState<AgnesPreviewRead | undefined>();

  const requirementsQuery = useQuery({
    queryKey: requirementsQueryKey,
    queryFn: () => latestAssetRequirements(chapter.chapter_id),
  });
  const revisionsQuery = useQuery({
    queryKey: revisionsQueryKey,
    queryFn: () => listShotPromptRevisions(chapter.chapter_id),
  });

  const requirements = requirementsQuery.data;
  const revisions = revisionsQuery.data ?? [];
  const selectedRevision = useMemo(
    () => selectRevision(revisions, selectedRevisionId),
    [revisions, selectedRevisionId],
  );
  const shots = canonicalDraft?.shots ?? selectedRevision?.shots ?? [];
  const selectedShot = shots.find((shot) => shot.shot_id === selectedShotId) ?? shots[0];
  const requirementRowsByShot = useMemo(() => {
    return Object.fromEntries((requirements?.shot_rows ?? []).map((row) => [row.shot_id, row]));
  }, [requirements?.shot_rows]);

  useEffect(() => {
    if (!selectedRevision) {
      if (revisions.length === 0 && !isDraftDirty) {
        setCanonicalDraft(null);
        setSelectedShotId("");
        setSelectedReadiness({});
        setPreview(undefined);
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

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeAssetRequirements(chapter.chapter_id),
    onSuccess: (nextRequirements) => {
      queryClient.setQueryData(requirementsQueryKey, nextRequirements);
      void queryClient.invalidateQueries({ queryKey: requirementsQueryKey });
    },
  });

  const generateMutation = useMutation({
    mutationFn: () => generateShotPrompts(chapter.chapter_id),
    onSuccess: (revision) => {
      upsertRevision(queryClient, revisionsQueryKey, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: revisionsQueryKey });
    },
  });

  const saveMutation = useMutation({
    mutationFn: ({ revisionId, content }: { revisionId: string; content: string }) =>
      updateShotPromptRevision(revisionId, { content }),
    onSuccess: (revision) => {
      upsertRevision(queryClient, revisionsQueryKey, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: revisionsQueryKey });
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: ({ revisionId, shotId }: { revisionId: string; shotId: string }) =>
      regenerateShotPrompt(revisionId, shotId),
    onSuccess: (revision) => {
      upsertRevision(queryClient, revisionsQueryKey, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: revisionsQueryKey });
    },
  });

  const markReadyMutation = useMutation({
    mutationFn: ({ revisionId, shotId }: { revisionId: string; shotId: string }) =>
      markShotPromptReady(revisionId, shotId),
    onSuccess: (revision) => {
      upsertRevision(queryClient, revisionsQueryKey, revision);
      loadRevisionForEditing(revision);
      void queryClient.invalidateQueries({ queryKey: revisionsQueryKey });
    },
  });

  const previewMutation = useMutation({
    mutationFn: ({ revisionId, shotId }: { revisionId: string; shotId: string }) =>
      getAgnesPreview(revisionId, shotId),
    onSuccess: (nextPreview) => setPreview(nextPreview),
  });

  const isMutating =
    analyzeMutation.isPending ||
    generateMutation.isPending ||
    saveMutation.isPending ||
    regenerateMutation.isPending ||
    markReadyMutation.isPending ||
    previewMutation.isPending;
  const requirementsReady = requirements?.status === "ready";
  const selectedStatus = selectedShot ? selectedShotStatus(selectedShot) : "";
  const selectedRequirementRow = selectedShot ? requirementRowsByShot[selectedShot.shot_id] : undefined;
  const readyBlockReason = selectedShot
    ? getReadyBlockReason(selectedShot, selectedRevision, selectedStatus, requirementsReady, selectedRequirementRow)
    : "select a shot before marking ready";
  const gateSummary = selectedShot ? getGateSummary(selectedStatus, readyBlockReason) : "";
  const canGenerate = Boolean(requirementsReady && !revisionsQuery.isError && !isDraftDirty && !isMutating);
  const canSave = Boolean(selectedRevision && canonicalDraft && selectedShot && isDraftDirty && !isMutating);
  const canUseShotActions = Boolean(selectedRevision && selectedShot && !isDraftDirty && !isMutating);
  const canMarkReady = Boolean(canUseShotActions && requirementsReady && selectedStatus !== "blocked_by_assets" && !readyBlockReason);

  function loadRevisionForEditing(revision: ShotPromptRevisionRead) {
    const canonical = parseCanonical(revision);
    setSelectedRevisionId(revision.revision_id);
    setLoadedRevisionId(revision.revision_id);
    setCanonicalDraft(canonical);
    setSelectedShotId(canonical.shots?.[0]?.shot_id ?? "");
    setSelectedReadiness(revision.readiness ?? {});
    setIsDraftDirty(false);
    setPreview(undefined);
  }

  function updateShot(field: "positive_prompt" | "negative_prompt", value: string) {
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
    setPreview(undefined);
  }

  function saveAsNewRevision() {
    if (!canSave || !selectedRevision || !canonicalDraft) {
      return;
    }
    saveMutation.mutate({
      revisionId: selectedRevision.revision_id,
      content: JSON.stringify(canonicalDraft, null, 2),
    });
  }

  function selectedShotStatus(shot: ShotPromptShot): ShotPromptStatus | string {
    const requirementRow = requirementRowsByShot[shot.shot_id];
    if (requirementRow && requirementRow.status !== "ready") {
      return "blocked_by_assets";
    }
    return selectedReadiness[shot.shot_id]?.status ?? selectedRevision?.readiness?.[shot.shot_id]?.status ?? "draft";
  }

  if (requirementsQuery.isLoading || revisionsQuery.isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  return (
    <section aria-label="Shot Prompt 工作台" style={{ display: "grid", gap: 16 }}>
      <div style={headerStyle}>
        <Typography.Title level={2} style={{ fontSize: 18, margin: 0 }}>
          Shot Prompt
        </Typography.Title>
        <Typography.Text type="secondary">基于已确认分镜和资产需求生成、编辑并检查 Agnes 请求。</Typography.Text>
      </div>

      <MutationErrors
        errors={[
          generateMutation.error,
          saveMutation.error,
          regenerateMutation.error,
          markReadyMutation.error,
          previewMutation.error,
        ]}
      />

      <AssetRequirementPanel
        disabled={isMutating}
        error={requirementsQuery.isError ? requirementsQuery.error : analyzeMutation.error}
        isAnalyzing={analyzeMutation.isPending}
        isLoading={false}
        onAnalyze={() => analyzeMutation.mutate()}
        onOpenAssets={onOpenAssets}
        requirements={requirements}
      />

      {!requirementsReady ? (
        <Alert
          message="Shot Prompt 生成被资产阻塞"
          description="缺失资产，请先去资料与资产创建或绑定。"
          showIcon
          type="warning"
        />
      ) : null}

      <section style={panelStyle}>
        <div style={toolbarStyle}>
          <div>
            <Typography.Title level={2} style={sectionTitleStyle}>
              Prompt revisions
            </Typography.Title>
            <Typography.Text type="secondary">全章生成后可选择 revision 和单镜头继续处理。</Typography.Text>
          </div>
          <Button
            disabled={!canGenerate}
            loading={generateMutation.isPending}
            onClick={() => {
              if (canGenerate) {
                generateMutation.mutate();
              }
            }}
            type="primary"
          >
            生成全章 Shot Prompt
          </Button>
        </div>

        {revisionsQuery.isError ? (
          <RevisionLoadError error={revisionsQuery.error} onRetry={() => void revisionsQuery.refetch()} />
        ) : revisions.length === 0 ? (
          <Typography.Text type="secondary">暂无 Shot Prompt revision。资产需求 ready 后生成全章。</Typography.Text>
        ) : (
          <Tabs
            defaultActiveKey="prompt-editor"
            items={[
              {
                children: (
                  <VisualReferenceView
                    onOpenAsset={onOpenAssets ? () => onOpenAssets() : undefined}
                    shot={selectedShot}
                  />
                ),
                key: "visual-refs",
                label: "视觉引用",
              },
              {
                children: (
                  <div
                    style={{
                      display: "grid",
                      gap: 16,
                      gridTemplateColumns: "minmax(0, 1.35fr) minmax(320px, 0.65fr)",
                    }}
                  >
                    <div style={{ display: "grid", gap: 12, minWidth: 0 }}>
                      <RevisionPicker
                        disabled={isDraftDirty || isMutating}
                        onSelect={loadRevisionForEditing}
                        revisions={revisions}
                        selectedRevisionId={selectedRevision?.revision_id ?? ""}
                      />

                      <ShotPromptTable
                        onSelect={(shotId) => {
                          if (!isMutating && !isDraftDirty) {
                            setSelectedShotId(shotId);
                            setPreview(undefined);
                          }
                        }}
                        selectedShotId={selectedShot?.shot_id ?? ""}
                        shotStatus={selectedShotStatus}
                        shots={shots}
                      />
                    </div>

                    <aside aria-label="Shot Prompt inspector" style={panelStyle}>
                      <PromptGateSummary reason={gateSummary} status={selectedStatus} />
                      <ShotPromptEditor
                        disabled={isMutating}
                        onChange={updateShot}
                        onOpenAsset={onOpenAssets ? () => onOpenAssets() : undefined}
                        preview={preview}
                        shot={selectedShot}
                      />
                      <ShotPromptActions
                        canMarkReady={canMarkReady}
                        canSave={canSave}
                        canUseShotActions={canUseShotActions}
                        isRegenerating={regenerateMutation.isPending}
                        isSaving={saveMutation.isPending}
                        isMarkingReady={markReadyMutation.isPending}
                        isPreviewing={previewMutation.isPending}
                        onMarkReady={() =>
                          selectedRevision &&
                          selectedShot &&
                          markReadyMutation.mutate({
                            revisionId: selectedRevision.revision_id,
                            shotId: selectedShot.shot_id,
                          })
                        }
                        onPreview={() =>
                          selectedRevision &&
                          selectedShot &&
                          previewMutation.mutate({
                            revisionId: selectedRevision.revision_id,
                            shotId: selectedShot.shot_id,
                          })
                        }
                        onRegenerate={() =>
                          selectedRevision &&
                          selectedShot &&
                          regenerateMutation.mutate({
                            revisionId: selectedRevision.revision_id,
                            shotId: selectedShot.shot_id,
                          })
                        }
                        onSave={saveAsNewRevision}
                      />
                    </aside>
                  </div>
                ),
                key: "prompt-editor",
                label: "Prompt 编辑",
              },
              {
                children: (
                  <RevisionHistoryView
                    disabled={isDraftDirty || isMutating}
                    onSelect={loadRevisionForEditing}
                    revisions={revisions}
                    selectedRevisionId={selectedRevision?.revision_id ?? ""}
                  />
                ),
                key: "revision-history",
                label: "Revision 历史",
              },
              {
                children: (
                  <AgnesPreviewView
                    canUseShotActions={canUseShotActions}
                    isPreviewing={previewMutation.isPending}
                    onPreview={() =>
                      selectedRevision &&
                      selectedShot &&
                      previewMutation.mutate({
                        revisionId: selectedRevision.revision_id,
                        shotId: selectedShot.shot_id,
                      })
                    }
                    preview={preview}
                    shot={selectedShot}
                  />
                ),
                key: "agnes-preview",
                label: "Agnes 参数预览",
              },
            ]}
          />
        )}
      </section>
    </section>
  );
}

function RevisionLoadError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const details = getApiErrorDetails(error, "Shot Prompt revision 加载失败。请重试。");
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

function RevisionPicker({
  disabled,
  onSelect,
  revisions,
  selectedRevisionId,
}: {
  disabled: boolean;
  onSelect: (revision: ShotPromptRevisionRead) => void;
  revisions: ShotPromptRevisionRead[];
  selectedRevisionId: string;
}) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {revisions.map((revision) => (
        <Button
          disabled={disabled}
          key={revision.revision_id}
          onClick={() => onSelect(revision)}
          type={revision.revision_id === selectedRevisionId ? "primary" : "default"}
        >
          Revision {revision.number}
        </Button>
      ))}
    </div>
  );
}

function PromptGateSummary({ reason, status }: { reason: string; status: string }) {
  return (
    <section aria-label="Prompt Gate" style={gateSummaryStyle}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <Typography.Text strong>Prompt Gate</Typography.Text>
        <Tag color={statusColor(status)}>{status || "draft"}</Tag>
      </div>
      <Typography.Text type={reason ? "warning" : "secondary"}>
        {reason || "当前镜头可在 Prompt、资产和 Agnes 参数检查后标记 Ready。"}
      </Typography.Text>
    </section>
  );
}

function ShotPromptActions({
  canMarkReady,
  canSave,
  canUseShotActions,
  isMarkingReady,
  isPreviewing,
  isRegenerating,
  isSaving,
  onMarkReady,
  onPreview,
  onRegenerate,
  onSave,
}: {
  canMarkReady: boolean;
  canSave: boolean;
  canUseShotActions: boolean;
  isMarkingReady: boolean;
  isPreviewing: boolean;
  isRegenerating: boolean;
  isSaving: boolean;
  onMarkReady: () => void;
  onPreview: () => void;
  onRegenerate: () => void;
  onSave: () => void;
}) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      <Button disabled={!canSave} loading={isSaving} onClick={onSave}>
        保存为新 Shot Prompt 版本
      </Button>
      <Button disabled={!canUseShotActions} loading={isRegenerating} onClick={onRegenerate}>
        重新生成当前镜头
      </Button>
      <Button disabled={!canMarkReady} loading={isMarkingReady} onClick={onMarkReady}>
        标记当前镜头 Ready
      </Button>
      <Button disabled={!canUseShotActions} loading={isPreviewing} onClick={onPreview}>
        预览 Agnes 请求
      </Button>
    </div>
  );
}

function VisualReferenceView({
  onOpenAsset,
  shot,
}: {
  onOpenAsset?: (assetId: string) => void;
  shot?: ShotPromptShot;
}) {
  if (!shot) {
    return <Typography.Text type="secondary">选择一个 shot 后查看视觉引用。</Typography.Text>;
  }
  return (
    <section style={panelStyle}>
      <Typography.Title level={3} style={sectionTitleStyle}>
        {shot.shot_id} 视觉引用
      </Typography.Title>
      <AssetRefsPreview assetRefs={shot.asset_refs} onOpenAsset={onOpenAsset} />
    </section>
  );
}

function RevisionHistoryView({
  disabled,
  onSelect,
  revisions,
  selectedRevisionId,
}: {
  disabled: boolean;
  onSelect: (revision: ShotPromptRevisionRead) => void;
  revisions: ShotPromptRevisionRead[];
  selectedRevisionId: string;
}) {
  return (
    <section style={panelStyle}>
      <div style={toolbarStyle}>
        <div>
          <Typography.Title level={3} style={sectionTitleStyle}>
            Revision 历史
          </Typography.Title>
          <Typography.Text type="secondary">切换版本前请先保存当前手工编辑。</Typography.Text>
        </div>
        <RevisionPicker
          disabled={disabled}
          onSelect={onSelect}
          revisions={revisions}
          selectedRevisionId={selectedRevisionId}
        />
      </div>
      <div style={{ overflowX: "auto" }}>
        <table aria-label="Shot prompt revision history" style={tableStyle}>
          <thead style={{ background: "#f9fafc" }}>
            <tr>
              <th style={tableHeaderStyle}>revision</th>
              <th style={tableHeaderStyle}>approval_status</th>
              <th style={tableHeaderStyle}>current</th>
              <th style={tableHeaderStyle}>validations</th>
            </tr>
          </thead>
          <tbody>
            {revisions.map((revision) => (
              <tr key={revision.revision_id}>
                <td style={tableCellStyle}>Revision {revision.number}</td>
                <td style={tableCellStyle}>{revision.approval_status}</td>
                <td style={tableCellStyle}>{revision.current ? "current" : "-"}</td>
                <td style={tableCellStyle}>
                  {revision.validation_results.map((result) => (
                    <Tag color={result.status === "PASS" ? "success" : "error"} key={result.validation_id}>
                      {result.validator_id}
                    </Tag>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AgnesPreviewView({
  canUseShotActions,
  isPreviewing,
  onPreview,
  preview,
  shot,
}: {
  canUseShotActions: boolean;
  isPreviewing: boolean;
  onPreview: () => void;
  preview?: AgnesPreviewRead;
  shot?: ShotPromptShot;
}) {
  if (!shot) {
    return <Typography.Text type="secondary">选择一个 shot 后查看 Agnes 参数。</Typography.Text>;
  }
  return (
    <section style={panelStyle}>
      <div style={toolbarStyle}>
        <div>
          <Typography.Title level={3} style={sectionTitleStyle}>
            Agnes 参数预览
          </Typography.Title>
          <Typography.Text type="secondary">本阶段只预览图片/视频请求参数，不解锁 Agnes 生成。</Typography.Text>
        </div>
        <Button disabled={!canUseShotActions} loading={isPreviewing} onClick={onPreview}>
          预览 Agnes 请求
        </Button>
      </div>
      <pre style={preStyle}>{JSON.stringify(preview?.agnes_video_params ?? shot.agnes_video_params, null, 2)}</pre>
    </section>
  );
}

function getReadyBlockReason(
  shot: ShotPromptShot,
  revision: ShotPromptRevisionRead | undefined,
  status: string,
  requirementsReady: boolean,
  requirementRow?: { status: string; ready: Array<{ asset_id?: string }> },
) {
  if (status === "blocked_by_assets") {
    return "当前镜头被资产需求阻塞，请去资料与资产创建或绑定缺失资产。";
  }
  if (!requirementsReady || requirementRow?.status !== "ready") {
    return "asset requirements must be ready for the current shot";
  }
  if (status === "needs_revision") {
    return "current shot needs revision before ready";
  }
  if (revision?.validation_results.some((result) => result.required && result.status !== "PASS")) {
    return "required validators did not pass";
  }
  const duration = getShotDuration(shot);
  if (duration !== undefined && (duration < 5 || duration > 15)) {
    return "shot duration must be between 5 and 15 seconds";
  }
  if (requirementRow?.status === "ready" && !assetRefsMatchReadyRequirements(shot, requirementRow)) {
    return "asset_refs must match ready asset requirements";
  }
  return "";
}

function assetRefsMatchReadyRequirements(
  shot: ShotPromptShot,
  requirementRow: { ready: Array<{ asset_id?: string }> },
) {
  const expectedAssetIds = uniqueSorted(requirementRow.ready.flatMap((need) => (need.asset_id ? [need.asset_id] : [])));
  const actualAssetIds = uniqueSorted(shot.asset_refs);
  return (
    expectedAssetIds.length === actualAssetIds.length &&
    expectedAssetIds.every((assetId, index) => assetId === actualAssetIds[index])
  );
}

function uniqueSorted(values: string[]) {
  return Array.from(new Set(values)).sort();
}

function getGateSummary(status: string, readyBlockReason: string) {
  if (readyBlockReason) {
    return readyBlockReason;
  }
  if (status === "ready") {
    return "当前镜头已 Ready。";
  }
  if (status === "draft") {
    return "当前镜头为 draft，可在检查完成后标记 Ready。";
  }
  return "";
}

function getShotDuration(shot: ShotPromptShot) {
  const directDuration = Number(shot.duration_seconds);
  if (Number.isFinite(directDuration)) {
    return directDuration;
  }
  const paramsDuration = Number(shot.agnes_video_params.duration_seconds);
  if (Number.isFinite(paramsDuration)) {
    return paramsDuration;
  }
  return undefined;
}

function parseCanonical(revision: ShotPromptRevisionRead): ShotPromptCanonical {
  const parsed = JSON.parse(revision.content) as ShotPromptCanonical;
  return {
    ...parsed,
    shots: parsed.shots ?? revision.shots ?? [],
  };
}

function selectRevision(revisions: ShotPromptRevisionRead[], selectedRevisionId: string) {
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
  queryKey: unknown[],
  revision: ShotPromptRevisionRead,
) {
  queryClient.setQueryData<ShotPromptRevisionRead[]>(queryKey, (current = []) => {
    const next = current.filter((item) => item.revision_id !== revision.revision_id);
    return [...next, revision].sort((left, right) => left.number - right.number);
  });
}

function ShotPromptTable({
  onSelect,
  selectedShotId,
  shotStatus,
  shots,
}: {
  onSelect: (shotId: string) => void;
  selectedShotId: string;
  shotStatus: (shot: ShotPromptShot) => string;
  shots: ShotPromptShot[];
}) {
  if (shots.length === 0) {
    return <Typography.Text type="secondary">当前 revision 没有 shot prompts。</Typography.Text>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table aria-label="Shot prompt rows" style={tableStyle}>
        <thead style={{ background: "#f9fafc" }}>
          <tr>
            <th style={tableHeaderStyle}>shot_id</th>
            <th style={tableHeaderStyle}>状态</th>
            <th style={tableHeaderStyle}>positive_prompt</th>
            <th style={tableHeaderStyle}>asset_refs</th>
          </tr>
        </thead>
        <tbody>
          {shots.map((shot) => (
            <tr key={shot.shot_id} style={shot.shot_id === selectedShotId ? selectedRowStyle : undefined}>
              <td style={tableCellStyle}>
                <Button onClick={() => onSelect(shot.shot_id)} size="small" type="link">
                  {shot.shot_id}
                </Button>
              </td>
              <td style={tableCellStyle}>
                <Tag color={statusColor(shotStatus(shot))}>{shotStatus(shot)}</Tag>
              </td>
              <td style={tableCellStyle}>{shot.positive_prompt}</td>
              <td style={tableCellStyle}>{shot.asset_refs.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MutationErrors({ errors }: { errors: Array<unknown> }) {
  const firstError = errors.find(Boolean);
  if (!firstError) {
    return null;
  }
  const details = getApiErrorDetails(firstError, "Shot Prompt 操作失败。请重试。");
  return <Alert description={details.code || undefined} message={details.message} showIcon type="error" />;
}

function getApiErrorDetails(error: unknown, fallbackMessage: string) {
  const data = (error as ApiError | undefined)?.response?.data;
  return {
    code: data?.error_code ?? "",
    message: data?.error_message ?? fallbackMessage,
  };
}

function statusColor(status: string) {
  if (status === "ready") {
    return "success";
  }
  if (status === "blocked_by_assets" || status === "needs_revision") {
    return "warning";
  }
  return "processing";
}

const headerStyle = {
  display: "grid",
  gap: 4,
};

const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};

const toolbarStyle = {
  alignItems: "start",
  display: "flex",
  flexWrap: "wrap" as const,
  gap: 12,
  justifyContent: "space-between",
};

const sectionTitleStyle = {
  fontSize: 16,
  margin: 0,
};

const gateSummaryStyle = {
  background: "#f9fafc",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 6,
  padding: 10,
};

const tableStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderCollapse: "collapse" as const,
  minWidth: 900,
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
  maxWidth: 260,
  padding: "10px 12px",
  verticalAlign: "top" as const,
};

const selectedRowStyle = {
  background: "#eef6ff",
};

const preStyle = {
  background: "#f9fafc",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  margin: 0,
  maxHeight: 240,
  overflow: "auto",
  padding: 10,
  whiteSpace: "pre-wrap" as const,
  wordBreak: "break-word" as const,
};
