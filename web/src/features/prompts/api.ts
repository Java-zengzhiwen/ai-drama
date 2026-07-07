import { apiClient } from "../../api/client";
import type { ValidationResultRead } from "../script/api";

export type AssetRequirementStatus =
  | "ready"
  | "missing_assets"
  | "asset_generation_in_progress"
  | "asset_review_required";

export type AssetRequirementNeed = {
  need_type: string;
  target_type: string;
  target_id: string;
  role: string;
  asset_type: string;
  asset_id?: string;
  status: AssetRequirementStatus;
};

export type AssetRequirementShotRow = {
  shot_id: string;
  status: AssetRequirementStatus;
  ready: AssetRequirementNeed[];
  missing_assets: AssetRequirementNeed[];
  asset_generation_in_progress: AssetRequirementNeed[];
  asset_review_required: AssetRequirementNeed[];
};

export type AssetRequirementSetRead = {
  requirement_set_id: string;
  chapter_id: string;
  storyboard_revision_id: string;
  storyboard_content_hash: string;
  content_object_id: string;
  content_hash: string;
  created_at: string;
  status: AssetRequirementStatus;
  shot_rows: AssetRequirementShotRow[];
  missing_assets: AssetRequirementNeed[];
  asset_generation_in_progress: AssetRequirementNeed[];
  asset_review_required: AssetRequirementNeed[];
};

export type ShotPromptStatus = "blocked_by_assets" | "draft" | "ready" | "needs_revision";

export type ShotPromptShot = {
  shot_id: string;
  scene_id?: string;
  shot_order?: number;
  duration_seconds?: number;
  positive_prompt: string;
  negative_prompt: string;
  continuity_notes: unknown;
  asset_refs: string[];
  agnes_video_params: Record<string, unknown>;
  source_storyboard_shot?: unknown;
  [key: string]: unknown;
};

export type ShotPromptCanonical = {
  schema_version?: string;
  project_id?: string;
  chapter_id?: string;
  source_storyboard_revision_id?: string;
  shots?: ShotPromptShot[];
  [key: string]: unknown;
};

export type ShotPromptRevisionRead = {
  revision_id: string;
  artifact_id: string;
  chapter_id: string;
  number: number;
  approval_status: string;
  current: boolean;
  content: string;
  validation_results: ValidationResultRead[];
  source_storyboard_revision_id: string;
  shots: ShotPromptShot[];
  readiness: Record<string, { status: ShotPromptStatus | string }>;
};

export type ShotPromptRevisionUpdate = {
  content: string;
};

export type AgnesPreviewRead = {
  shot_id: string;
  positive_prompt: string;
  negative_prompt: string;
  asset_refs: string[];
  continuity_notes: unknown;
  agnes_video_params: Record<string, unknown>;
};

export async function analyzeAssetRequirements(chapterId: string): Promise<AssetRequirementSetRead> {
  const response = await apiClient.post<AssetRequirementSetRead>(
    `/chapters/${chapterId}/asset-requirements/analyze`,
  );
  return response.data;
}

export async function latestAssetRequirements(chapterId: string): Promise<AssetRequirementSetRead> {
  const response = await apiClient.get<AssetRequirementSetRead>(
    `/chapters/${chapterId}/asset-requirements/latest`,
  );
  return response.data;
}

export async function generateShotPrompts(chapterId: string): Promise<ShotPromptRevisionRead> {
  const response = await apiClient.post<ShotPromptRevisionRead>(
    `/chapters/${chapterId}/shot-prompts/generate`,
  );
  return response.data;
}

export async function listShotPromptRevisions(chapterId: string): Promise<ShotPromptRevisionRead[]> {
  const response = await apiClient.get<ShotPromptRevisionRead[]>(
    `/chapters/${chapterId}/shot-prompts/revisions`,
  );
  return response.data;
}

export async function updateShotPromptRevision(
  revisionId: string,
  payload: ShotPromptRevisionUpdate,
): Promise<ShotPromptRevisionRead> {
  const response = await apiClient.put<ShotPromptRevisionRead>(
    `/shot-prompt-revisions/${revisionId}`,
    payload,
  );
  return response.data;
}

export async function regenerateShotPrompt(
  revisionId: string,
  shotId: string,
): Promise<ShotPromptRevisionRead> {
  const response = await apiClient.post<ShotPromptRevisionRead>(
    `/shot-prompt-revisions/${revisionId}/shots/${shotId}/regenerate`,
  );
  return response.data;
}

export async function markShotPromptReady(
  revisionId: string,
  shotId: string,
): Promise<ShotPromptRevisionRead> {
  const response = await apiClient.post<ShotPromptRevisionRead>(
    `/shot-prompt-revisions/${revisionId}/shots/${shotId}/mark-ready`,
  );
  return response.data;
}

export async function getAgnesPreview(
  revisionId: string,
  shotId: string,
): Promise<AgnesPreviewRead> {
  const response = await apiClient.get<AgnesPreviewRead>(
    `/shot-prompt-revisions/${revisionId}/shots/${shotId}/agnes-preview`,
  );
  return response.data;
}
