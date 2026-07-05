import { apiClient } from "../../api/client";

export type ProjectCreate = {
  name: string;
  description: string;
  series_canon: string;
  characters_context: string;
  production_brief: string;
};

export type ProjectRead = ProjectCreate & {
  project_id: string;
  created_at: string;
  updated_at: string;
};

export type ChapterCreate = {
  title: string;
  position: number;
};

export type ChapterRead = ChapterCreate & {
  chapter_id: string;
  project_id: string;
  current_source_revision_id: string;
  created_at: string;
  updated_at: string;
  source_text?: string;
};

export type ChapterStatus = {
  status: string;
  blocking_reason: string;
  next_action: string;
};

export async function listProjects(): Promise<ProjectRead[]> {
  const response = await apiClient.get<ProjectRead[]>("/projects");
  return response.data;
}

export async function createProject(payload: ProjectCreate): Promise<ProjectRead> {
  const response = await apiClient.post<ProjectRead>("/projects", payload);
  return response.data;
}

export async function getProject(projectId: string): Promise<ProjectRead> {
  const response = await apiClient.get<ProjectRead>(`/projects/${projectId}`);
  return response.data;
}

export async function createChapter(projectId: string, payload: ChapterCreate): Promise<ChapterRead> {
  const response = await apiClient.post<ChapterRead>(`/projects/${projectId}/chapters`, payload);
  return response.data;
}

export async function getChapterStatus(chapterId: string): Promise<ChapterStatus> {
  const response = await apiClient.get<ChapterStatus>(`/chapters/${chapterId}/status`);
  return response.data;
}
