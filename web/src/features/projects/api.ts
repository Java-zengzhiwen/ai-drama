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

export type ModelCapability = "text" | "image" | "video";
export type ProjectModelBindings = {
  project_id: string;
  defaults: Record<ModelCapability, string>;
  operation_overrides: Record<string, string>;
  binding_set_revision: number;
};
export type ModelResolution = {
  project_id?: string;
  operation_key: string;
  capability: ModelCapability;
  binding_source: "capability_default" | "operation_override";
  supplier_id?: string;
  supplier_model_id: string;
  model_revision_id?: string;
  provider_model_name: string;
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

export async function listChapters(projectId: string): Promise<ChapterRead[]> {
  const response = await apiClient.get<ChapterRead[]>(`/projects/${projectId}/chapters`);
  return response.data;
}

export async function getChapterStatus(chapterId: string): Promise<ChapterStatus> {
  const response = await apiClient.get<ChapterStatus>(`/chapters/${chapterId}/status`);
  return response.data;
}

export async function getProjectModelBindings(
  projectId: string,
): Promise<{ data: ProjectModelBindings; etag: string }> {
  const response = await apiClient.get<ProjectModelBindings>(`/projects/${projectId}/model-bindings`);
  return { data: response.data, etag: String(response.headers?.etag ?? "") };
}

export async function saveProjectModelBindings(
  projectId: string,
  payload: Pick<ProjectModelBindings, "defaults" | "operation_overrides">,
  etag: string,
): Promise<{ data: ProjectModelBindings; etag: string }> {
  const response = await apiClient.put<ProjectModelBindings>(
    `/projects/${projectId}/model-bindings`,
    payload,
    { headers: { "If-Match": etag } },
  );
  return { data: response.data, etag: String(response.headers?.etag ?? "") };
}

export async function getModelResolution(
  projectId: string,
  operationKey: string,
): Promise<ModelResolution> {
  const response = await apiClient.get<ModelResolution>(
    `/projects/${projectId}/model-resolution/${operationKey}`,
  );
  return response.data;
}
