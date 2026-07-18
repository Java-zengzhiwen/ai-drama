import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { ChapterWorkspace } from "../chapter/ChapterWorkspace";
import type { ChapterRead, ChapterStatus } from "../projects/api";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = apiClient.get as unknown as Mock;
const mockedPost = apiClient.post as unknown as Mock;

const chapter: ChapterRead = {
  chapter_id: "chapter-1",
  project_id: "project-1",
  title: "第一章",
  position: 1,
  current_source_revision_id: "source-1",
  created_at: "2026-07-05T10:00:00Z",
  updated_at: "2026-07-05T10:00:00Z",
  source_text: "沈清荷醒来后决定查账。",
};

const storyboardApprovedStatus: ChapterStatus = {
  status: "storyboard_approved",
  blocking_reason: "",
  next_action: "milestone_1_complete",
};

const scriptApprovedStatus: ChapterStatus = {
  status: "script_approved",
  blocking_reason: "",
  next_action: "generate_storyboard",
};

const characterProfile = {
  profile_id: "profile-1",
  project_id: "project-1",
  chapter_id: "chapter-1",
  profile_type: "character",
  name: "沈清荷",
  payload: {
    name: "沈清荷",
    continuity_notes: "账册始终随身",
    identity_notes: "沈家长女",
    appearance_notes: "",
    costume_notes: "素色长衫",
  },
  created_at: "2026-07-05T10:02:00Z",
  updated_at: "2026-07-05T10:02:00Z",
};

const uploadedAsset = {
  asset_id: "asset-1",
  project_id: "project-1",
  chapter_id: "chapter-1",
  asset_type: "character_reference",
  name: "沈清荷正面照",
  object_id: "object-1",
  media_type: "image/png",
  width: 768,
  height: 1024,
  status: "draft",
  source_type: "upload",
  source_job_id: "",
  metadata: {
    prompt: "front portrait",
    notes: "uploaded during Task 12",
  },
  bindings: [],
  created_at: "2026-07-05T10:03:00Z",
  updated_at: "2026-07-05T10:03:00Z",
};

const generatedAsset = {
  ...uploadedAsset,
  asset_id: "asset-2",
  asset_type: "scene_reference",
  name: "旧账房参考",
  object_id: "object-2",
  status: "draft",
  source_type: "agnes",
  source_job_id: "job-1",
  metadata: {
    prompt: "quiet account room",
  },
  bindings: [],
};

const generatingAsset = {
  ...generatedAsset,
  asset_id: "asset-3",
  name: "生成中的账房参考",
  object_id: "object-3",
  status: "generating",
  bindings: [],
};

const currentBinding = {
  binding_id: "binding-1",
  asset_id: "asset-2",
  target_type: "character",
  target_id: "profile-1",
  role: "primary_reference",
  is_current: true,
  created_at: "2026-07-05T10:04:00Z",
};

const adoptedAsset = {
  ...generatedAsset,
  status: "usable",
  bindings: [currentBinding],
};

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
  return queryClient;
}

function setupWorkspaceMocks({
  assets = [],
  profiles = [],
  status = storyboardApprovedStatus,
}: {
  assets?: unknown[];
  profiles?: unknown[];
  status?: ChapterStatus;
} = {}) {
  const listedAssets = [...assets];
  const listedProfiles = [...profiles];

  mockedGet.mockImplementation(async (url: string, config?: { params?: Record<string, string> }) => {
    if (url === "/chapters/chapter-1") {
      return { data: chapter };
    }
    if (url === "/chapters/chapter-1/status") {
      return { data: status };
    }
    if (url === "/chapters/chapter-1/script/revisions") {
      return { data: [] };
    }
    if (url === "/chapters/chapter-1/storyboard/revisions") {
      return { data: [] };
    }
    if (url === "/projects/project-1/profiles") {
      expect(config?.params).toEqual({ chapter_id: "chapter-1" });
      return { data: listedProfiles };
    }
    if (url === "/chapters/chapter-1/assets") {
      return { data: listedAssets };
    }
    throw new Error(`unexpected GET ${url}`);
  });

  mockedPost.mockImplementation(async (url: string, payload?: unknown, config?: unknown) => {
    if (url === "/projects/project-1/profiles") {
      expect(payload).toEqual({
        chapter_id: "chapter-1",
        profile_type: "character",
        payload: {
          name: "沈清荷",
          continuity_notes: "账册始终随身",
          identity_notes: "沈家长女",
          appearance_notes: "",
          costume_notes: "素色长衫",
        },
      });
      listedProfiles.push(characterProfile);
      return { data: characterProfile };
    }
    if (url === "/chapters/chapter-1/assets") {
      expect(payload).toBeInstanceOf(FormData);
      expect(config).toEqual({ headers: { "Content-Type": "multipart/form-data" } });
      const formData = payload as FormData;
      expect(formData.get("asset_type")).toBe("character_reference");
      expect(formData.get("name")).toBe("沈清荷正面照");
      expect(formData.get("file")).toBeInstanceOf(File);
      listedAssets.push(uploadedAsset);
      return { data: uploadedAsset };
    }
    if (url === "/chapters/chapter-1/assets/generate-image") {
      expect(payload).toEqual({
        asset_type: "scene_reference",
        name: "旧账房参考",
        prompt: "quiet account room",
        size: "1024x1024",
        input_asset_ids: [],
        input_images: [],
        metadata: {
          ref_type: "scene",
        },
      });
      listedAssets.push(generatedAsset);
      return { data: generatedAsset };
    }
    if (url === "/assets/asset-2/mark-usable") {
      const updated = { ...generatedAsset, status: "usable", bindings: [] };
      listedAssets.splice(0, listedAssets.length, updated);
      return { data: updated };
    }
    if (url === "/assets/asset-2/reject") {
      expect(payload).toEqual({ reason: "身份漂移" });
      const updated = { ...generatedAsset, status: "rejected" };
      listedAssets.splice(0, listedAssets.length, updated);
      return { data: updated };
    }
    if (url === "/assets/asset-2/bindings") {
      expect(payload).toEqual({
        target_type: "character",
        target_id: "profile-1",
        role: "primary_reference",
        is_current: true,
      });
      return {
        data: currentBinding,
      };
    }
    throw new Error(`unexpected POST ${url}`);
  });
}

async function openAssetsTab() {
  const assetsTab = await screen.findByRole("tab", { name: "资料与资产" });
  expect(assetsTab).not.toHaveAttribute("aria-disabled", "true");
  fireEvent.click(assetsTab);
  return assetsTab;
}

describe("profiles and assets workspace", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
  });

  test("keeps profiles and assets locked until storyboard approval", async () => {
    setupWorkspaceMocks({ status: scriptApprovedStatus });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    expect(await screen.findByRole("heading", { name: "第一章" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /资料与资产/ })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getAllByText("未确认分镜，不允许进入后续生产步骤。").length).toBeGreaterThan(0);
  });

  test("unlocks after storyboard approval and shows empty profile and asset states", async () => {
    setupWorkspaceMocks();

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    const workflow = await screen.findByRole("list", { name: "workflow rail" });
    await waitFor(() => expect(within(workflow).getAllByRole("listitem")).toHaveLength(7));
    expect(screen.queryByText("后续生产步骤已锁定")).not.toBeInTheDocument();
    await openAssetsTab();

    expect(await screen.findByText("暂无生产资料。创建角色、场景、道具或风格资料后会显示在这里。")).toBeInTheDocument();
    expect(screen.getByText("暂无资产。上传图片或请求 Agnes 图片后会显示在这里。")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Shot Prompt" })).not.toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("tab", { name: /Agnes 生成/ })).toHaveAttribute("aria-disabled", "true");
  });

  test("creates a character profile and refreshes the profile list", async () => {
    setupWorkspaceMocks();

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openAssetsTab();

    fireEvent.change(await screen.findByLabelText("资料类型"), { target: { value: "character" } });
    fireEvent.change(screen.getByLabelText("资料名称"), { target: { value: "沈清荷" } });
    fireEvent.change(screen.getByLabelText("连续性说明"), { target: { value: "账册始终随身" } });
    fireEvent.change(screen.getByLabelText("身份说明"), { target: { value: "沈家长女" } });
    fireEvent.change(screen.getByLabelText("服装说明"), { target: { value: "素色长衫" } });
    fireEvent.click(screen.getByRole("button", { name: "创建资料" }));

    await waitFor(() => expect(mockedPost).toHaveBeenCalledWith("/projects/project-1/profiles", expect.any(Object)));
    expect(await screen.findByText("沈清荷")).toBeInTheDocument();
    expect(within(screen.getByLabelText("生产资料列表")).getByText("character")).toBeInTheDocument();
  });

  test("uploads an image and shows it in the visual-first asset grid", async () => {
    setupWorkspaceMocks({ profiles: [characterProfile] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openAssetsTab();

    fireEvent.change(await screen.findByLabelText("上传资产类型"), {
      target: { value: "character_reference" },
    });
    fireEvent.change(screen.getByLabelText("上传资产名称"), { target: { value: "沈清荷正面照" } });
    fireEvent.change(screen.getByLabelText("资产文件"), {
      target: { files: [new File(["image"], "portrait.png", { type: "image/png" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "上传资产" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/assets", expect.any(FormData), {
        headers: { "Content-Type": "multipart/form-data" },
      }),
    );
    const card = await screen.findByLabelText("资产 沈清荷正面照");
    expect(within(card).getByRole("img", { name: "沈清荷正面照 缩略图" })).toHaveAttribute(
      "src",
      "/api/assets/asset-1/content",
    );
    expect(within(card).getByText("character_reference")).toBeInTheDocument();
    expect(within(card).getByText("draft")).toBeInTheDocument();
    expect(within(card).getByText("upload")).toBeInTheDocument();
  });

  test("requests an Agnes image and shows draft asset returned by the backend", async () => {
    setupWorkspaceMocks({ profiles: [characterProfile] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openAssetsTab();

    fireEvent.change(await screen.findByLabelText("Agnes 资产类型"), {
      target: { value: "scene_reference" },
    });
    fireEvent.change(screen.getByLabelText("Agnes 资产名称"), { target: { value: "旧账房参考" } });
    fireEvent.change(screen.getByLabelText("参考类型"), { target: { value: "scene" } });
    fireEvent.change(screen.getByLabelText("Agnes 提示词"), { target: { value: "quiet account room" } });
    fireEvent.click(screen.getByRole("button", { name: "请求 Agnes 图片" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/assets/generate-image", expect.any(Object)),
    );
    const card = await screen.findByLabelText("资产 旧账房参考");
    expect(within(card).getByText("draft")).toBeInTheDocument();
    expect(within(card).getByText("agnes")).toBeInTheDocument();
  });

  test("keeps generating assets in review-only mode until a result is available", async () => {
    setupWorkspaceMocks({ assets: [generatingAsset], profiles: [characterProfile] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openAssetsTab();

    const card = await screen.findByLabelText("资产 生成中的账房参考");
    expect(within(card).getByRole("button", { name: "标记可用" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "拒绝资产" })).toBeDisabled();
    expect(within(card).getByLabelText("设为当前绑定")).toBeDisabled();
  });

  test("shows persisted current bindings and opens a visual asset inspector", async () => {
    setupWorkspaceMocks({ assets: [uploadedAsset, adoptedAsset], profiles: [characterProfile] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openAssetsTab();

    const card = await screen.findByLabelText("资产 旧账房参考");
    expect(within(card).getByText("character:profile-1")).toBeInTheDocument();
    expect(within(card).getByText("当前采用")).toBeInTheDocument();

    fireEvent.click(within(card).getByRole("button", { name: "查看大图" }));

    const inspector = await screen.findByRole("dialog", { name: "资产详情：旧账房参考" });
    expect(within(inspector).getByRole("region", { name: "资产主预览" })).toBeInTheDocument();
    expect(within(inspector).getByRole("list", { name: "资产版本历史" })).toBeInTheDocument();
    expect(within(inspector).getByRole("img", { name: "旧账房参考 大图预览" })).toHaveAttribute(
      "src",
      "/api/assets/asset-2/content",
    );
    expect(within(inspector).getByText("版本与采用")).toBeInTheDocument();
    expect(within(inspector).getByText("旧账房参考")).toBeInTheDocument();
    expect(within(inspector).getAllByText("当前采用").length).toBeGreaterThan(0);
  });

  test("marks assets usable, rejects them, binds them, and opens metadata drawer", async () => {
    setupWorkspaceMocks({ assets: [generatedAsset], profiles: [characterProfile] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openAssetsTab();

    const card = await screen.findByLabelText("资产 旧账房参考");
    fireEvent.click(within(card).getByRole("button", { name: "标记可用" }));
    await waitFor(() => expect(mockedPost).toHaveBeenCalledWith("/assets/asset-2/mark-usable"));
    expect(await within(card).findByText("usable")).toBeInTheDocument();

    fireEvent.change(within(card).getByLabelText("绑定目标类型"), { target: { value: "character" } });
    fireEvent.change(within(card).getByLabelText("绑定目标"), { target: { value: "profile-1" } });
    fireEvent.change(within(card).getByLabelText("绑定角色"), { target: { value: "primary_reference" } });
    fireEvent.click(within(card).getByLabelText("设为当前绑定"));
    fireEvent.click(within(card).getByRole("button", { name: "绑定资产" }));

    await waitFor(() => expect(mockedPost).toHaveBeenCalledWith("/assets/asset-2/bindings", expect.any(Object)));
    expect(await within(card).findByText("character:profile-1")).toBeInTheDocument();
    expect(within(card).getByText("当前采用")).toBeInTheDocument();

    fireEvent.click(within(card).getByRole("button", { name: "查看 metadata" }));
    expect(await screen.findByRole("dialog", { name: "旧账房参考 metadata" })).toBeInTheDocument();
    expect(screen.getByText(/quiet account room/)).toBeInTheDocument();

    fireEvent.change(within(card).getByLabelText("拒绝原因"), { target: { value: "身份漂移" } });
    fireEvent.click(within(card).getByRole("button", { name: "拒绝资产" }));
    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/assets/asset-2/reject", {
        reason: "身份漂移",
      }),
    );
    expect(await within(card).findByText("rejected")).toBeInTheDocument();
  });
});
