import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { ChapterWorkspace } from "../chapter/ChapterWorkspace";
import type { ChapterRead, ChapterStatus } from "../projects/api";

vi.mock("../../api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

const mockedGet = apiClient.get as unknown as Mock;
const mockedPost = apiClient.post as unknown as Mock;
const mockedPut = apiClient.put as unknown as Mock;

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

const scriptApprovedStatus: ChapterStatus = {
  status: "script_approved",
  blocking_reason: "",
  next_action: "generate_storyboard",
};

const storyboardApprovedStatus: ChapterStatus = {
  status: "storyboard_approved",
  blocking_reason: "",
  next_action: "milestone_1_complete",
};

const assetsReadyStatus: ChapterStatus = {
  status: "assets_ready",
  blocking_reason: "",
  next_action: "generate_shot_prompts",
};

const promptsDraftStatus: ChapterStatus = {
  status: "prompts_draft",
  blocking_reason: "",
  next_action: "mark_shot_prompts_ready",
};

const promptsReadyStatus: ChapterStatus = {
  status: "prompts_ready",
  blocking_reason: "",
  next_action: "m2_complete",
};

const missingRequirements = {
  requirement_set_id: "requirements-1",
  chapter_id: "chapter-1",
  storyboard_revision_id: "storyboard-1",
  storyboard_content_hash: "storyboard-hash-1",
  content_object_id: "object-1",
  content_hash: "requirements-hash-1",
  created_at: "2026-07-05T10:10:00Z",
  status: "missing_assets",
  shot_rows: [
    {
      shot_id: "SHOT_001",
      status: "missing_assets",
      ready: [],
      missing_assets: [
        {
          need_type: "character_asset",
          target_type: "character",
          target_id: "CHAR_SHEN_QINGHE",
          role: "primary_reference",
          asset_type: "character_reference",
          status: "missing_assets",
        },
        {
          need_type: "shot_keyframe",
          target_type: "shot",
          target_id: "SHOT_001",
          role: "keyframe",
          asset_type: "shot_keyframe",
          status: "missing_assets",
        },
      ],
      asset_generation_in_progress: [],
      asset_review_required: [],
    },
  ],
  missing_assets: [],
  asset_generation_in_progress: [],
  asset_review_required: [],
};

const readyRequirements = {
  ...missingRequirements,
  requirement_set_id: "requirements-2",
  content_hash: "requirements-hash-2",
  status: "ready",
  shot_rows: [
    {
      shot_id: "SHOT_001",
      status: "ready",
      ready: [
        {
          need_type: "character_asset",
          target_type: "character",
          target_id: "CHAR_SHEN_QINGHE",
          role: "primary_reference",
          asset_type: "character_reference",
          asset_id: "asset-character-1",
          status: "ready",
        },
        {
          need_type: "shot_keyframe",
          target_type: "shot",
          target_id: "SHOT_001",
          role: "keyframe",
          asset_type: "shot_keyframe",
          asset_id: "asset-keyframe-1",
          status: "ready",
        },
      ],
      missing_assets: [],
      asset_generation_in_progress: [],
      asset_review_required: [],
    },
  ],
  missing_assets: [],
  asset_generation_in_progress: [],
  asset_review_required: [],
};

const readyRequirementsWithoutShotRow = {
  ...readyRequirements,
  requirement_set_id: "requirements-without-shot-row",
  shot_rows: [],
};

const mixedRequirements = {
  ...missingRequirements,
  requirement_set_id: "requirements-3",
  status: "asset_generation_in_progress",
  shot_rows: [
    {
      shot_id: "SHOT_001",
      status: "asset_generation_in_progress",
      ready: [],
      missing_assets: [
        {
          need_type: "scene_asset",
          target_type: "scene",
          target_id: "SCENE_ACCOUNT_ROOM",
          role: "layout_reference",
          asset_type: "scene_reference",
          status: "missing_assets",
        },
      ],
      asset_generation_in_progress: [
        {
          need_type: "character_outfit",
          target_type: "character",
          target_id: "CHAR_SHEN_QINGHE",
          role: "outfit_reference",
          asset_type: "character_outfit",
          asset_id: "asset-outfit-generating",
          status: "asset_generation_in_progress",
        },
      ],
      asset_review_required: [
        {
          need_type: "prop_asset",
          target_type: "prop",
          target_id: "PROP_ACCOUNT_BOOK",
          role: "handling_reference",
          asset_type: "prop_reference",
          asset_id: "asset-prop-draft",
          status: "asset_review_required",
        },
      ],
    },
  ],
  missing_assets: [],
  asset_generation_in_progress: [],
  asset_review_required: [],
};

const shotPromptCanonical = {
  schema_version: "shot-prompt-canonical-v1",
  project_id: "project-1",
  chapter_id: "chapter-1",
  source_storyboard_revision_id: "storyboard-1",
  shots: [
    {
      shot_id: "SHOT_001",
      scene_id: "SCENE_001",
      shot_order: 1,
      duration_seconds: 8,
      positive_prompt: "Live action medium shot of Shen Qinghe checking the account book.",
      negative_prompt: "cartoon, text overlays, distorted hands",
      continuity_notes: ["Keep the account book in her left hand."],
      asset_refs: ["asset-character-1", "asset-keyframe-1"],
      agnes_video_params: {
        duration_seconds: 8,
        aspect_ratio: "9:16",
        camera_motion: "locked",
      },
      source_storyboard_shot: {
        shot_size: "medium",
        camera_angle: "eye_level",
        visual_composition: {
          framing: "centered medium composition",
          subject_focus: "CHAR_SHEN_QINGHE",
        },
      },
    },
  ],
};

const generatedRevision = {
  revision_id: "prompt-1",
  artifact_id: "chapter-1:shot-prompts",
  chapter_id: "chapter-1",
  number: 1,
  approval_status: "pending",
  current: false,
  content: JSON.stringify(shotPromptCanonical),
  validation_results: [
    {
      validation_id: "validation-1",
      validator_id: "shot_prompt_set_structure",
      status: "PASS",
      required: true,
      error_code: "",
    },
  ],
  source_storyboard_revision_id: "storyboard-1",
  shots: shotPromptCanonical.shots,
  readiness: {
    SHOT_001: {
      status: "draft",
    },
  },
};

const regeneratedRevision = {
  ...generatedRevision,
  revision_id: "prompt-2",
  number: 2,
  content: JSON.stringify({
    ...shotPromptCanonical,
    shots: [
      {
        ...shotPromptCanonical.shots[0],
        positive_prompt:
          "Live action medium shot of Shen Qinghe checking the account book, regenerated for SHOT_001.",
      },
    ],
  }),
  shots: [
    {
      ...shotPromptCanonical.shots[0],
      positive_prompt:
        "Live action medium shot of Shen Qinghe checking the account book, regenerated for SHOT_001.",
    },
  ],
};

const readyRevision = {
  ...generatedRevision,
  readiness: {
    SHOT_001: {
      status: "ready",
    },
  },
};

const validationFailedRevision = {
  ...generatedRevision,
  revision_id: "prompt-fail",
  validation_results: [
    {
      validation_id: "validation-fail",
      validator_id: "shot_prompt_set_structure",
      status: "FAIL",
      required: true,
      error_code: "INVALID_DURATION",
    },
  ],
};

const invalidDurationCanonical = {
  ...shotPromptCanonical,
  shots: [
    {
      ...shotPromptCanonical.shots[0],
      duration_seconds: 16,
      agnes_video_params: {
        ...shotPromptCanonical.shots[0].agnes_video_params,
        duration_seconds: 16,
      },
    },
  ],
};

const invalidDurationRevision = {
  ...generatedRevision,
  revision_id: "prompt-duration",
  content: JSON.stringify(invalidDurationCanonical),
  shots: invalidDurationCanonical.shots,
};

const assetRefMismatchCanonical = {
  ...shotPromptCanonical,
  shots: [
    {
      ...shotPromptCanonical.shots[0],
      asset_refs: ["asset-character-1"],
    },
  ],
};

const assetRefMismatchRevision = {
  ...generatedRevision,
  revision_id: "prompt-asset-ref-mismatch",
  content: JSON.stringify(assetRefMismatchCanonical),
  shots: assetRefMismatchCanonical.shots,
};

const agnesPreview = {
  shot_id: "SHOT_001",
  positive_prompt: shotPromptCanonical.shots[0].positive_prompt,
  negative_prompt: shotPromptCanonical.shots[0].negative_prompt,
  asset_refs: shotPromptCanonical.shots[0].asset_refs,
  continuity_notes: shotPromptCanonical.shots[0].continuity_notes,
  agnes_video_params: shotPromptCanonical.shots[0].agnes_video_params,
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
  latestRequirements = missingRequirements,
  revisionsError = false,
  revisions = [] as unknown[],
  status = storyboardApprovedStatus,
}: {
  latestRequirements?: unknown;
  revisionsError?: boolean;
  revisions?: unknown[];
  status?: ChapterStatus;
} = {}) {
  const listedRevisions = [...revisions];
  let latest = latestRequirements;

  mockedGet.mockImplementation(async (url: string) => {
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
    if (url === "/chapters/chapter-1/asset-requirements/latest") {
      return { data: latest };
    }
    if (url === "/chapters/chapter-1/shot-prompts/revisions") {
      if (revisionsError) {
        throw {
          response: {
            data: {
              error_code: "SHOT_PROMPT_REVISION_LOAD_FAILED",
              error_message: "Shot Prompt revision 加载失败。请重试。",
            },
          },
        };
      }
      return { data: listedRevisions };
    }
    if (url === "/shot-prompt-revisions/prompt-1/shots/SHOT_001/agnes-preview") {
      return { data: agnesPreview };
    }
    throw new Error(`unexpected GET ${url}`);
  });

  mockedPost.mockImplementation(async (url: string) => {
    if (url === "/chapters/chapter-1/asset-requirements/analyze") {
      latest = readyRequirements;
      return { data: readyRequirements };
    }
    if (url === "/chapters/chapter-1/shot-prompts/generate") {
      listedRevisions.splice(0, listedRevisions.length, generatedRevision);
      return { data: generatedRevision };
    }
    if (url === "/shot-prompt-revisions/prompt-1/shots/SHOT_001/regenerate") {
      listedRevisions.splice(0, listedRevisions.length, generatedRevision, regeneratedRevision);
      return { data: regeneratedRevision };
    }
    if (url === "/shot-prompt-revisions/prompt-1/shots/SHOT_001/mark-ready") {
      listedRevisions.splice(0, listedRevisions.length, readyRevision);
      return { data: readyRevision };
    }
    throw new Error(`unexpected POST ${url}`);
  });

  mockedPut.mockImplementation(async (url: string, payload?: unknown) => {
    if (url === "/shot-prompt-revisions/prompt-1") {
      const update = payload as { content: string };
      const canonical = JSON.parse(update.content);
      const editedRevision = {
        ...generatedRevision,
        revision_id: "prompt-3",
        number: 3,
        content: JSON.stringify(canonical),
        shots: canonical.shots,
      };
      listedRevisions.splice(0, listedRevisions.length, generatedRevision, editedRevision);
      return { data: editedRevision };
    }
    throw new Error(`unexpected PUT ${url}`);
  });
}

async function openShotPromptTab() {
  const tab = await screen.findByRole("tab", { name: "Shot Prompt" });
  expect(tab).not.toHaveAttribute("aria-disabled", "true");
  fireEvent.click(tab);
  return tab;
}

describe("shot prompt workspace", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
    mockedPut.mockReset();
  });

  test("keeps shot prompts locked until storyboard approval while Agnes and results remain locked", async () => {
    setupWorkspaceMocks({ status: scriptApprovedStatus });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    expect(await screen.findByRole("heading", { name: "第一章" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Shot Prompt/ })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("tab", { name: /Agnes 生成/ })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("tab", { name: /结果与重跑/ })).toHaveAttribute("aria-disabled", "true");
  });

  test("analyzes and displays shot-level asset requirements with missing asset guidance", async () => {
    setupWorkspaceMocks();

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    const rail = screen.getByLabelText("workflow rail");
    expect(within(rail).getByText("资料与资产")).toBeInTheDocument();
    expect(within(rail).getByText("Shot Prompt 待生成：等待资产需求 ready")).toBeInTheDocument();
    expect(within(rail).getByText("Agnes 生成已锁定：Agnes 生成和结果与重跑保持锁定。")).toBeInTheDocument();

    expect(await screen.findByText("资产需求")).toBeInTheDocument();
    const requirementsTable = screen.getByRole("table", { name: "Asset requirement rows" });
    expect(within(requirementsTable).getByText("SHOT_001")).toBeInTheDocument();
    expect(within(requirementsTable).getAllByText("missing_assets").length).toBeGreaterThan(0);
    expect(textContentMatches(requirementsTable, "CHAR_SHEN_QINGHE")).toBeGreaterThan(0);
    expect(textContentMatches(requirementsTable, "shot_keyframe")).toBeGreaterThan(0);
    expect(screen.getAllByText("缺失资产，请先去资料与资产创建或绑定。").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "生成全章 Shot Prompt" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "重新分析资产需求" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/asset-requirements/analyze"),
    );
    await waitFor(() =>
      expect(mockedGet.mock.calls.filter(([url]) => url === "/chapters/chapter-1/status").length).toBeGreaterThan(1),
    );
    await waitFor(() => expect(within(requirementsTable).getAllByText("ready").length).toBeGreaterThan(0));
    expect(screen.getByRole("button", { name: "生成全章 Shot Prompt" })).toBeEnabled();
  });

  test.each([
    [assetsReadyStatus, "Shot Prompt 可生成"],
    [promptsDraftStatus, "Shot Prompt 待确认：检查并标记镜头 Ready"],
    [promptsReadyStatus, "Shot Prompt 已就绪"],
  ])("keeps storyboard available and workflow rail accurate for %s", async (status, shotPromptRailText) => {
    setupWorkspaceMocks({
      latestRequirements: readyRequirements,
      revisions: status.status === "assets_ready" ? [] : [status.status === "prompts_ready" ? readyRevision : generatedRevision],
      status,
    });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    expect(await screen.findByRole("heading", { name: "第一章" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "分镜" })).not.toHaveAttribute("aria-disabled", "true");
    const rail = screen.getByLabelText("workflow rail");
    expect(within(rail).getByText(shotPromptRailText)).toBeInTheDocument();
    expect(within(rail).getByText("Agnes 生成已锁定：Agnes 生成和结果与重跑保持锁定。")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Agnes 生成/ })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("tab", { name: /结果与重跑/ })).toHaveAttribute("aria-disabled", "true");
  });

  test("uses state-specific asset requirement guidance and blocks ready actions for blocked shots", async () => {
    setupWorkspaceMocks({ latestRequirements: mixedRequirements, revisions: [generatedRevision] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    const requirementsTable = await screen.findByRole("table", { name: "Asset requirement rows" });
    expect(within(requirementsTable).getAllByText("asset_generation_in_progress").length).toBeGreaterThan(0);
    expect(screen.getByText("等待生成完成，或去资料与资产查看生成中的资产。")).toBeInTheDocument();
    expect(screen.getByText("去资料与资产审核、标记可用或重绑资产。")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "去资料与资产创建或绑定" }));
    expect(await screen.findByLabelText("资料与资产工作台")).toBeInTheDocument();
    await openShotPromptTab();

    const shotTable = screen.getByRole("table", { name: "Shot prompt rows" });
    expect(within(shotTable).getByText("blocked_by_assets")).toBeInTheDocument();
    expect(screen.getByText("当前镜头被资产需求阻塞，请去资料与资产创建或绑定缺失资产。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "标记当前镜头 Ready" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "标记当前镜头 Ready" }));
    expect(mockedPost).not.toHaveBeenCalledWith(
      "/shot-prompt-revisions/prompt-1/shots/SHOT_001/mark-ready",
    );
  });

  test("previews asset refs as thumbnails and opens assets from prompt references", async () => {
    setupWorkspaceMocks({ latestRequirements: readyRequirements, revisions: [generatedRevision] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    expect(await screen.findByRole("tab", { name: "视觉引用" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Prompt 编辑" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Revision 历史" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Agnes 参数预览" })).toBeInTheDocument();

    expect(await screen.findByRole("img", { name: "asset-character-1 引用预览" })).toHaveAttribute(
      "src",
      "/api/assets/asset-character-1/content",
    );
    expect(screen.getByRole("img", { name: "asset-keyframe-1 引用预览" })).toHaveAttribute(
      "src",
      "/api/assets/asset-keyframe-1/content",
    );

    fireEvent.click(screen.getByRole("button", { name: "查看资产 asset-character-1" }));
    expect(await screen.findByLabelText("资料与资产工作台")).toBeInTheDocument();
  });

  test("shows a revision loading error instead of treating failed revisions as empty", async () => {
    setupWorkspaceMocks({ latestRequirements: readyRequirements, revisionsError: true });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    expect(await screen.findByText("Shot Prompt revision 加载失败。请重试。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "生成全章 Shot Prompt" })).toBeDisabled();
    expect(screen.queryByText("暂无 Shot Prompt revision。资产需求 ready 后生成全章。")).not.toBeInTheDocument();
  });

  test("disables ready when prompt duration or required validation gate fails", async () => {
    setupWorkspaceMocks({ latestRequirements: readyRequirements, revisions: [validationFailedRevision] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    expect(await screen.findByText("required validators did not pass")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "标记当前镜头 Ready" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "标记当前镜头 Ready" }));
    expect(mockedPost).not.toHaveBeenCalledWith(
      "/shot-prompt-revisions/prompt-fail/shots/SHOT_001/mark-ready",
    );

    cleanup();
    setupWorkspaceMocks({ latestRequirements: readyRequirements, revisions: [invalidDurationRevision] });
    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    expect(await screen.findByText("shot duration must be between 5 and 15 seconds")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "标记当前镜头 Ready" })).toBeDisabled();
  });

  test("disables ready when prompt asset_refs do not match ready asset requirements", async () => {
    setupWorkspaceMocks({ latestRequirements: readyRequirements, revisions: [assetRefMismatchRevision] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    expect(await screen.findByText("asset_refs must match ready asset requirements")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "标记当前镜头 Ready" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "标记当前镜头 Ready" }));
    expect(mockedPost).not.toHaveBeenCalledWith(
      "/shot-prompt-revisions/prompt-asset-ref-mismatch/shots/SHOT_001/mark-ready",
    );
  });

  test("disables ready when the current shot has no ready asset requirement row", async () => {
    setupWorkspaceMocks({ latestRequirements: readyRequirementsWithoutShotRow, revisions: [generatedRevision] });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    expect(await screen.findByText("asset requirements must be ready for the current shot")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "标记当前镜头 Ready" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "标记当前镜头 Ready" }));
    expect(mockedPost).not.toHaveBeenCalledWith(
      "/shot-prompt-revisions/prompt-1/shots/SHOT_001/mark-ready",
    );
  });

  test("generates shot prompts when requirements are ready and supports edit, regenerate, ready, and Agnes preview", async () => {
    setupWorkspaceMocks({ latestRequirements: readyRequirements });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);
    await openShotPromptTab();

    fireEvent.click(await screen.findByRole("button", { name: "生成全章 Shot Prompt" }));
    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/shot-prompts/generate"),
    );
    await waitFor(() =>
      expect(mockedGet.mock.calls.filter(([url]) => url === "/chapters/chapter-1/status").length).toBeGreaterThan(1),
    );

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    const shotTable = screen.getByRole("table", { name: "Shot prompt rows" });
    expect(within(shotTable).getByText("SHOT_001")).toBeInTheDocument();
    expect(within(shotTable).getByText("draft")).toBeInTheDocument();
    expect(screen.getByLabelText("positive_prompt")).toHaveValue(
      "Live action medium shot of Shen Qinghe checking the account book.",
    );
    expect(screen.getByLabelText("negative_prompt")).toHaveValue("cartoon, text overlays, distorted hands");
    expect(screen.getAllByText("Agnes 参数预览").length).toBeGreaterThan(0);
    expect(screen.getByText("源 storyboard shot")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("positive_prompt"), {
      target: { value: "Edited cinematic account-book prompt." },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存为新 Shot Prompt 版本" }));

    await waitFor(() => expect(mockedPut).toHaveBeenCalledTimes(1));
    const [putUrl, putPayload] = mockedPut.mock.calls[0];
    expect(putUrl).toBe("/shot-prompt-revisions/prompt-1");
    const savedCanonical = JSON.parse(putPayload.content);
    expect(savedCanonical.shots[0].positive_prompt).toBe("Edited cinematic account-book prompt.");

    fireEvent.click(screen.getByRole("button", { name: "Revision 1" }));
    fireEvent.click(screen.getByRole("button", { name: "重新生成当前镜头" }));
    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/shot-prompt-revisions/prompt-1/shots/SHOT_001/regenerate"),
    );
    expect(await screen.findByText("Revision 2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Revision 1" }));
    fireEvent.click(screen.getByRole("button", { name: "标记当前镜头 Ready" }));
    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/shot-prompt-revisions/prompt-1/shots/SHOT_001/mark-ready"),
    );
    await waitFor(() =>
      expect(mockedGet.mock.calls.filter(([url]) => url === "/chapters/chapter-1/status").length).toBeGreaterThan(2),
    );
    expect(await within(shotTable).findByText("ready")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "预览 Agnes 请求" }));
    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith("/shot-prompt-revisions/prompt-1/shots/SHOT_001/agnes-preview"),
    );
    await waitFor(() => expect(textContentMatches(document.body, "asset-character-1")).toBeGreaterThan(0));
    expect(textContentMatches(document.body, "locked")).toBeGreaterThan(0);
  });
});

function textContentMatches(root: HTMLElement, text: string) {
  return Array.from(root.querySelectorAll("*")).filter((element) =>
    element.textContent?.includes(text),
  ).length;
}
