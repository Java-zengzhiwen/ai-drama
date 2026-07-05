import { apiClient } from "../../api/client";
import type { RevisionDecision, ScriptRevisionRead, ScriptRevisionUpdate } from "../script/api";

export type StoryboardRevisionRead = ScriptRevisionRead;
export type StoryboardRevisionUpdate = ScriptRevisionUpdate;

export async function generateStoryboard(chapterId: string): Promise<StoryboardRevisionRead> {
  const response = await apiClient.post<StoryboardRevisionRead>(`/chapters/${chapterId}/storyboard/generate`);
  return response.data;
}

export async function listStoryboardRevisions(chapterId: string): Promise<StoryboardRevisionRead[]> {
  const response = await apiClient.get<StoryboardRevisionRead[]>(
    `/chapters/${chapterId}/storyboard/revisions`,
  );
  return response.data;
}

export async function updateStoryboardRevision(
  revisionId: string,
  payload: StoryboardRevisionUpdate,
): Promise<StoryboardRevisionRead> {
  const response = await apiClient.put<StoryboardRevisionRead>(`/storyboard-revisions/${revisionId}`, payload);
  return response.data;
}

export async function validateStoryboardRevision(revisionId: string): Promise<StoryboardRevisionRead> {
  const response = await apiClient.post<StoryboardRevisionRead>(
    `/storyboard-revisions/${revisionId}/validate`,
  );
  return response.data;
}

export async function approveStoryboardRevision(
  revisionId: string,
  payload: RevisionDecision,
): Promise<StoryboardRevisionRead> {
  const response = await apiClient.post<StoryboardRevisionRead>(
    `/storyboard-revisions/${revisionId}/approve`,
    payload,
  );
  return response.data;
}

export async function rejectStoryboardRevision(
  revisionId: string,
  payload: RevisionDecision,
): Promise<StoryboardRevisionRead> {
  const response = await apiClient.post<StoryboardRevisionRead>(
    `/storyboard-revisions/${revisionId}/reject`,
    payload,
  );
  return response.data;
}
