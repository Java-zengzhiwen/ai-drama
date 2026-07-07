import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Skeleton, Tag, Typography } from "antd";
import type { ChapterRead } from "../projects/api";
import { AssetGenerator } from "./AssetGenerator";
import { AssetGrid } from "./AssetGrid";
import { AssetUpload } from "./AssetUpload";
import { ProfileEditor } from "./ProfileEditor";
import {
  bindAsset,
  createProfile,
  generateImageAsset,
  listAssets,
  listProfiles,
  markAssetUsable,
  rejectAsset,
  uploadAsset,
  type AssetBindingCreate,
  type AssetBindingRead,
  type AssetGenerateImageRequest,
  type AssetRead,
  type ProductionProfileCreate,
  type ProductionProfileRead,
} from "./api";

type ProfilesAssetsTabProps = {
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

export function ProfilesAssetsTab({ chapter }: ProfilesAssetsTabProps) {
  const queryClient = useQueryClient();
  const profilesQueryKey = ["production-profiles", chapter.project_id, chapter.chapter_id];
  const assetsQueryKey = ["chapter-assets", chapter.chapter_id];

  const profilesQuery = useQuery({
    queryKey: profilesQueryKey,
    queryFn: () => listProfiles(chapter.project_id, chapter.chapter_id),
  });
  const assetsQuery = useQuery({
    queryKey: assetsQueryKey,
    queryFn: () => listAssets(chapter.chapter_id),
  });

  const profileMutation = useMutation({
    mutationFn: (payload: ProductionProfileCreate) => createProfile(chapter.project_id, payload),
    onSuccess: (profile) => {
      queryClient.setQueryData<ProductionProfileRead[]>(profilesQueryKey, (current = []) =>
        upsertById(current, profile, "profile_id"),
      );
      void queryClient.invalidateQueries({ queryKey: profilesQueryKey });
    },
  });
  const uploadMutation = useMutation({
    mutationFn: (payload: FormData) => uploadAsset(chapter.chapter_id, payload),
    onSuccess: (asset) => {
      updateAssetCache(queryClient, assetsQueryKey, asset);
      void queryClient.invalidateQueries({ queryKey: assetsQueryKey });
    },
  });
  const generateMutation = useMutation({
    mutationFn: (payload: AssetGenerateImageRequest) => generateImageAsset(chapter.chapter_id, payload),
    onSuccess: (asset) => {
      updateAssetCache(queryClient, assetsQueryKey, asset);
      void queryClient.invalidateQueries({ queryKey: assetsQueryKey });
    },
  });
  const markUsableMutation = useMutation({
    mutationFn: markAssetUsable,
    onSuccess: (asset) => {
      updateAssetCache(queryClient, assetsQueryKey, asset);
      void queryClient.invalidateQueries({ queryKey: assetsQueryKey });
    },
  });
  const rejectMutation = useMutation({
    mutationFn: ({ assetId, reason }: { assetId: string; reason: string }) => rejectAsset(assetId, reason),
    onSuccess: (asset) => {
      updateAssetCache(queryClient, assetsQueryKey, asset);
      void queryClient.invalidateQueries({ queryKey: assetsQueryKey });
    },
  });
  const bindingMutation = useMutation({
    mutationFn: ({ assetId, payload }: { assetId: string; payload: AssetBindingCreate }) =>
      bindAsset(assetId, payload),
    onSuccess: (binding) => {
      updateAssetBindingCache(queryClient, assetsQueryKey, binding);
    },
  });

  const profiles = profilesQuery.data ?? [];
  const assets = assetsQuery.data ?? [];
  const isLoading = profilesQuery.isLoading || assetsQuery.isLoading;
  const isMutating =
    profileMutation.isPending ||
    uploadMutation.isPending ||
    generateMutation.isPending ||
    markUsableMutation.isPending ||
    rejectMutation.isPending ||
    bindingMutation.isPending;

  if (isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  return (
    <section aria-label="资料与资产工作台" style={{ display: "grid", gap: 16 }}>
      <div style={headerStyle}>
        <Typography.Title level={2} style={{ fontSize: 18, margin: 0 }}>
          资料与资产
        </Typography.Title>
        <Typography.Text type="secondary">围绕已确认分镜沉淀角色、场景、道具和参考图。</Typography.Text>
      </div>

      <MutationErrors
        errors={[
          profileMutation.error,
          uploadMutation.error,
          generateMutation.error,
          markUsableMutation.error,
          rejectMutation.error,
          bindingMutation.error,
        ]}
      />

      <div style={formsGridStyle}>
        <ProfileEditor
          chapterId={chapter.chapter_id}
          disabled={isMutating}
          onSubmit={(payload) => profileMutation.mutate(payload)}
        />
        <AssetUpload disabled={isMutating} onSubmit={(payload) => uploadMutation.mutate(payload)} />
        <AssetGenerator disabled={isMutating} onSubmit={(payload) => generateMutation.mutate(payload)} />
      </div>

      <section aria-label="生产资料列表" style={panelStyle}>
        <Typography.Title level={2} style={sectionTitleStyle}>
          生产资料
        </Typography.Title>
        {profiles.length === 0 ? (
          <Typography.Text type="secondary">暂无生产资料。创建角色、场景、道具或风格资料后会显示在这里。</Typography.Text>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {profiles.map((profile) => (
              <Tag key={profile.profile_id} style={{ display: "inline-flex", gap: 6 }}>
                <span>{profile.name}</span>
                <span>{profile.profile_type}</span>
              </Tag>
            ))}
          </div>
        )}
      </section>

      <section aria-label="资产列表" style={panelStyle}>
        <Typography.Title level={2} style={sectionTitleStyle}>
          资产
        </Typography.Title>
        <AssetGrid
          assets={assets}
          disabled={isMutating}
          onBind={(assetId, payload) => bindingMutation.mutate({ assetId, payload })}
          onMarkUsable={(assetId) => markUsableMutation.mutate(assetId)}
          onReject={(assetId, reason) => rejectMutation.mutate({ assetId, reason })}
          profiles={profiles}
        />
      </section>
    </section>
  );
}

function MutationErrors({ errors }: { errors: Array<unknown> }) {
  const firstError = errors.find(Boolean);
  if (!firstError) {
    return null;
  }
  const details = getApiErrorDetails(firstError, "资料与资产操作失败。请重试。");
  return <Alert description={details.code || undefined} message={details.message} showIcon type="error" />;
}

function getApiErrorDetails(error: unknown, fallbackMessage: string) {
  const data = (error as ApiError | undefined)?.response?.data;
  return {
    code: data?.error_code ?? "",
    message: data?.error_message ?? fallbackMessage,
  };
}

function updateAssetCache(
  queryClient: ReturnType<typeof useQueryClient>,
  queryKey: unknown[],
  asset: AssetRead,
) {
  queryClient.setQueryData<AssetRead[]>(queryKey, (current = []) => upsertById(current, asset, "asset_id"));
}

function updateAssetBindingCache(
  queryClient: ReturnType<typeof useQueryClient>,
  queryKey: unknown[],
  binding: AssetBindingRead,
) {
  queryClient.setQueryData<AssetRead[]>(queryKey, (current = []) =>
    current.map((asset) => {
      const existingBindings = asset.bindings ?? [];
      const normalizedBindings = existingBindings
        .map((currentBinding) =>
          binding.is_current && sameAdoptionScope(currentBinding, binding) && currentBinding.binding_id !== binding.binding_id
            ? { ...currentBinding, is_current: false }
            : currentBinding,
        )
        .filter((currentBinding) => currentBinding.binding_id !== binding.binding_id);
      return asset.asset_id === binding.asset_id
        ? { ...asset, bindings: [...normalizedBindings, binding] }
        : { ...asset, bindings: normalizedBindings };
    }),
  );
}

function sameAdoptionScope(left: AssetBindingRead, right: AssetBindingRead) {
  return left.target_type === right.target_type && left.target_id === right.target_id && left.role === right.role;
}

function upsertById<T extends Record<string, unknown>>(items: T[], item: T, idKey: keyof T) {
  const next = items.filter((current) => current[idKey] !== item[idKey]);
  return [...next, item];
}

const headerStyle = {
  display: "grid",
  gap: 4,
};

const formsGridStyle = {
  display: "grid",
  gap: 12,
  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
};

const panelStyle = {
  background: "#ffffff",
  border: "1px solid #d9dee8",
  borderRadius: 6,
  display: "grid",
  gap: 12,
  padding: 12,
};

const sectionTitleStyle = {
  fontSize: 16,
  margin: 0,
};
