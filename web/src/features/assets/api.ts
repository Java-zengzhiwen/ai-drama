import { apiClient } from "../../api/client";

export type ProfileType = "character" | "scene" | "prop" | "style";
export type AssetType =
  | "character_reference"
  | "character_outfit"
  | "scene_reference"
  | "scene_angle"
  | "prop_reference"
  | "shot_keyframe";
export type AssetStatus = "draft" | "generating" | "usable" | "rejected" | "failed";
export type AssetSourceType = "upload" | "agnes" | "derived";
export type BindingTargetType = "character" | "scene" | "prop" | "shot";

export type ProductionProfileRead = {
  profile_id: string;
  project_id: string;
  chapter_id: string;
  profile_type: ProfileType;
  name: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ProductionProfileCreate = {
  chapter_id: string;
  profile_type: ProfileType;
  payload: Record<string, unknown>;
};

export type AssetRead = {
  asset_id: string;
  project_id: string;
  chapter_id: string;
  asset_type: AssetType;
  name: string;
  object_id: string;
  media_type: string;
  width: number;
  height: number;
  status: AssetStatus;
  source_type: AssetSourceType;
  source_job_id: string;
  metadata: Record<string, unknown>;
  bindings: AssetBindingRead[];
  created_at: string;
  updated_at: string;
};

export type AssetGenerateImageRequest = {
  asset_type: AssetType;
  name: string;
  prompt: string;
  size: string;
  input_asset_ids: string[];
  input_images: string[];
  metadata: Record<string, unknown>;
};

export type AssetBindingCreate = {
  target_type: BindingTargetType;
  target_id: string;
  role: string;
  is_current: boolean;
};

export type AssetBindingRead = AssetBindingCreate & {
  binding_id: string;
  asset_id: string;
  created_at: string;
};

export async function listProfiles(projectId: string, chapterId: string): Promise<ProductionProfileRead[]> {
  const response = await apiClient.get<ProductionProfileRead[]>(`/projects/${projectId}/profiles`, {
    params: { chapter_id: chapterId },
  });
  return response.data;
}

export async function createProfile(
  projectId: string,
  payload: ProductionProfileCreate,
): Promise<ProductionProfileRead> {
  const response = await apiClient.post<ProductionProfileRead>(`/projects/${projectId}/profiles`, payload);
  return response.data;
}

export async function listAssets(chapterId: string): Promise<AssetRead[]> {
  const response = await apiClient.get<AssetRead[]>(`/chapters/${chapterId}/assets`);
  return response.data;
}

export async function uploadAsset(chapterId: string, payload: FormData): Promise<AssetRead> {
  const response = await apiClient.post<AssetRead>(`/chapters/${chapterId}/assets`, payload, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function generateImageAsset(
  chapterId: string,
  payload: AssetGenerateImageRequest,
): Promise<AssetRead> {
  const response = await apiClient.post<AssetRead>(`/chapters/${chapterId}/assets/generate-image`, payload);
  return response.data;
}

export async function markAssetUsable(assetId: string): Promise<AssetRead> {
  const response = await apiClient.post<AssetRead>(`/assets/${assetId}/mark-usable`);
  return response.data;
}

export async function rejectAsset(assetId: string, reason: string): Promise<AssetRead> {
  const response = await apiClient.post<AssetRead>(`/assets/${assetId}/reject`, { reason });
  return response.data;
}

export async function bindAsset(assetId: string, payload: AssetBindingCreate): Promise<AssetBindingRead> {
  const response = await apiClient.post<AssetBindingRead>(`/assets/${assetId}/bindings`, payload);
  return response.data;
}
