import { apiClient } from "../../api/client";

export type GenerationJobRead = {
  job_id: string;
  provider: string;
  job_type: string;
  project_id: string;
  chapter_id: string;
  shot_id: string;
  prompt_revision_id: string;
  provider_job_id: string;
  provider_result_id: string;
  internal_status: string;
  ui_status: string;
  idempotency_key: string;
  attempt_number: number;
  error_code: string;
  error_message: string;
  created_at: string;
  updated_at: string;
};

export type GenerationJobDetailRead = GenerationJobRead & {
  request: {
    shot_id: string;
    prompt: string;
    negative_prompt: string;
    duration_seconds: number;
    asset_ids: string[];
    parameters: Record<string, unknown>;
  };
};

export type VideoJobCreate = {
  prompt_revision_id: string;
  shot_id: string;
  idempotency_key: string;
};

export type GenerationResultRead = {
  result_id: string;
  job_id: string;
  attempt_number: number;
  media_type: string;
  source_url: string;
  source_url_state: "source_url_active" | "source_url_expired";
  local_result_available: boolean;
  local_content_url: string;
  created_at: string;
};

export type ShotResultsRead = {
  shot_id: string;
  current_result_id: string;
  results: GenerationResultRead[];
};

export async function listGenerationJobs(chapterId: string): Promise<GenerationJobRead[]> {
  const response = await apiClient.get<GenerationJobRead[]>(`/chapters/${chapterId}/generation/jobs`);
  return response.data;
}

export async function queueVideoJob(chapterId: string, payload: VideoJobCreate): Promise<GenerationJobRead> {
  const response = await apiClient.post<GenerationJobRead>(
    `/chapters/${chapterId}/generation/video-jobs`,
    payload,
  );
  return response.data;
}

export async function refreshGenerationJob(jobId: string): Promise<GenerationJobRead> {
  const response = await apiClient.post<GenerationJobRead>(`/generation/jobs/${jobId}/refresh`);
  return response.data;
}

export async function getGenerationJob(jobId: string): Promise<GenerationJobDetailRead> {
  const response = await apiClient.get<GenerationJobDetailRead>(`/generation/jobs/${jobId}`);
  return response.data;
}

export async function listGenerationResults(chapterId: string): Promise<ShotResultsRead[]> {
  const response = await apiClient.get<ShotResultsRead[]>(`/chapters/${chapterId}/results`);
  return response.data;
}

export async function selectGenerationResult(shotId: string, resultId: string) {
  const response = await apiClient.post(`/shots/${shotId}/results/${resultId}/select`);
  return response.data;
}

export type ResultReviewCreate = {
  decision: "passed" | "failed";
  failure_category: string;
  note: string;
};

export async function reviewGenerationResult(resultId: string, payload: ResultReviewCreate) {
  const response = await apiClient.post(`/results/${resultId}/review`, payload);
  return response.data;
}

export type GenerationRerunCreate = {
  idempotency_key: string;
  prompt?: string;
  negative_prompt?: string;
  asset_ids?: string[];
  duration_seconds?: number;
  mode?: "std" | "pro";
  seed?: number;
};

export async function rerunGenerationJob(jobId: string, payload: GenerationRerunCreate) {
  const response = await apiClient.post(`/generation/jobs/${jobId}/rerun`, payload);
  return response.data;
}
