import { apiClient } from "../../api/client";
import type { ChapterRead } from "../projects/api";

export type SourceRevisionRead = {
  source_revision_id: string;
  chapter_id: string;
  number: number;
  object_id: string;
  content_hash: string;
  created_at: string;
};

export type SourceRevisionCreate = {
  content: string;
};

export type ValidationResultRead = {
  validation_id: string;
  validator_id: string;
  status: string;
  required: boolean;
  error_code: string;
};

export type ScriptRevisionRead = {
  revision_id: string;
  artifact_id: string;
  chapter_id: string;
  number: number;
  approval_status: string;
  current: boolean;
  content: string;
  validation_results: ValidationResultRead[];
};

export type ScriptRevisionUpdate = {
  content: string;
};

export type RevisionDecision = {
  reviewer: string;
  note: string;
};

export async function getChapter(chapterId: string): Promise<ChapterRead> {
  const response = await apiClient.get<ChapterRead>(`/chapters/${chapterId}`);
  return response.data;
}

export async function createSourceRevision(
  chapterId: string,
  payload: SourceRevisionCreate,
): Promise<SourceRevisionRead> {
  const response = await apiClient.post<SourceRevisionRead>(
    `/chapters/${chapterId}/source-revisions`,
    payload,
  );
  return response.data;
}

export async function generateScript(
  chapterId: string,
  payload?: { target_duration_minutes: number },
): Promise<ScriptRevisionRead> {
  const response = await apiClient.post<ScriptRevisionRead>(
    `/chapters/${chapterId}/script/generate`,
    payload,
  );
  return response.data;
}

export async function listScriptRevisions(chapterId: string): Promise<ScriptRevisionRead[]> {
  const response = await apiClient.get<ScriptRevisionRead[]>(`/chapters/${chapterId}/script/revisions`);
  return response.data;
}

export async function updateScriptRevision(
  revisionId: string,
  payload: ScriptRevisionUpdate,
): Promise<ScriptRevisionRead> {
  const response = await apiClient.put<ScriptRevisionRead>(`/script-revisions/${revisionId}`, payload);
  return response.data;
}

export async function approveScriptRevision(
  revisionId: string,
  payload: RevisionDecision,
): Promise<ScriptRevisionRead> {
  const response = await apiClient.post<ScriptRevisionRead>(
    `/script-revisions/${revisionId}/approve`,
    payload,
  );
  return response.data;
}

export async function rejectScriptRevision(
  revisionId: string,
  payload: RevisionDecision,
): Promise<ScriptRevisionRead> {
  const response = await apiClient.post<ScriptRevisionRead>(
    `/script-revisions/${revisionId}/reject`,
    payload,
  );
  return response.data;
}
