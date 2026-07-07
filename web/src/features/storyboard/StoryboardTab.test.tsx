import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { apiClient } from "../../api/client";
import { ChapterWorkspace } from "../chapter/ChapterWorkspace";
import type { ChapterRead, ChapterStatus } from "../projects/api";
import { StoryboardTab } from "./StoryboardTab";

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

const canonicalStoryboard = {
  schema_version: "storyboard-canonical-v1",
  project_id: "project-1",
  chapter_id: "chapter-1",
  source: {
    script_artifact_id: "chapter-1:script",
    script_revision_id: "script-1",
    script_content_hash: "hash-1",
  },
  scenes: [
    {
      scene_id: "SCENE_001",
      scene_order: 1,
      source_scene_reference: "1-1",
      location: null,
      time: null,
      interior_exterior: null,
      characters: ["CHAR_SHEN_QINGHE"],
      summary: "沈清荷醒来后查账。",
    },
  ],
  shots: [
    {
      scene_id: "SCENE_001",
      shot_id: "SHOT_001",
      shot_order: 1,
      source_scene_reference: "1-1",
      duration_seconds: 8,
      shot_size: "medium",
      camera_angle: "eye_level",
      camera_movement: null,
      visual_composition: {
        framing: "centered medium composition",
        subject_focus: "CHAR_SHEN_QINGHE",
        background_relation: "old room remains still",
        screen_direction: null,
      },
      character_positions: [
        {
          character_id: "CHAR_SHEN_QINGHE",
          screen_zone: "center",
          depth: "foreground",
          pose: "standing",
          facing: null,
        },
      ],
      character_actions: [
        {
          character_id: "CHAR_SHEN_QINGHE",
          action_order: 1,
          action: "checks the account book",
        },
      ],
      emotion_performance: [
        {
          character_id: "CHAR_SHEN_QINGHE",
          emotion: "focused",
          intensity: "medium",
          performance_note: null,
        },
      ],
      dialogue: [
        {
          speaker_character_id: "CHAR_SHEN_QINGHE",
          text: "账不会骗人。",
          lip_sync_required: true,
        },
      ],
      sound_notes: ["paper movement"],
      continuity_in: {
        must_preserve: ["wardrobe"],
        must_change: [],
        source_unit_or_shot_id: null,
      },
      continuity_out: {
        must_preserve: ["wardrobe"],
        must_change: ["attention shifts to evidence"],
        source_unit_or_shot_id: null,
      },
    },
  ],
};

const generatedRevision = {
  revision_id: "storyboard-1",
  artifact_id: "chapter-1:script:storyboard",
  chapter_id: "chapter-1",
  number: 1,
  approval_status: "pending",
  current: false,
  content: JSON.stringify(canonicalStoryboard),
  validation_results: [
    {
      validation_id: "validation-1",
      validator_id: "storyboard_canonical_schema",
      status: "PASS",
      required: true,
      error_code: "",
    },
    {
      validation_id: "validation-2",
      validator_id: "storyboard_bundle_integrity",
      status: "PASS",
      required: true,
      error_code: "",
    },
  ],
};

const multiShotStoryboard = {
  ...canonicalStoryboard,
  shots: [
    canonicalStoryboard.shots[0],
    {
      ...canonicalStoryboard.shots[0],
      shot_id: "SHOT_002",
      shot_order: 2,
      shot_size: "wide",
      visual_composition: {
        framing: "wide room composition",
        subject_focus: "CHAR_SHEN_QINGHE",
        background_relation: "account books fill the table",
        screen_direction: null,
      },
    },
  ],
};

const multiShotRevision = {
  ...generatedRevision,
  content: JSON.stringify(multiShotStoryboard),
};

const editedRevision = {
  ...generatedRevision,
  revision_id: "storyboard-2",
  number: 2,
  content: JSON.stringify({
    ...canonicalStoryboard,
    shots: [
      {
        ...canonicalStoryboard.shots[0],
        shot_size: "close_up",
        dialogue: [
          {
            speaker_character_id: "CHAR_SHEN_QINGHE",
            text: "这本账必须重查。",
            lip_sync_required: true,
          },
        ],
      },
    ],
  }),
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

function setupStoryboardMocks(initialRevisions = [generatedRevision]) {
  let revisions = [...initialRevisions];

  mockedGet.mockImplementation(async (url: string) => {
    if (url === "/chapters/chapter-1/storyboard/revisions") {
      return { data: revisions };
    }
    throw new Error(`unexpected GET ${url}`);
  });

  mockedPost.mockImplementation(async (url: string, payload?: unknown) => {
    if (url === "/chapters/chapter-1/storyboard/generate") {
      revisions = [generatedRevision];
      return { data: generatedRevision };
    }
    if (url === "/storyboard-revisions/storyboard-1/validate") {
      const validated = {
        ...generatedRevision,
        validation_results: [
          ...generatedRevision.validation_results,
          {
            validation_id: "validation-3",
            validator_id: "storyboard_canonical_schema",
            status: "PASS",
            required: true,
            error_code: "",
          },
        ],
      };
      revisions = revisions.map((revision) =>
        revision.revision_id === "storyboard-1" ? validated : revision,
      );
      return { data: validated };
    }
    if (url === "/storyboard-revisions/storyboard-2/approve") {
      expect(payload).toEqual({ reviewer: "local-user", note: "" });
      revisions = revisions.map((revision) =>
        revision.revision_id === "storyboard-2"
          ? { ...revision, approval_status: "approved", current: true }
          : revision,
      );
      return { data: revisions.find((revision) => revision.revision_id === "storyboard-2") };
    }
    if (url === "/storyboard-revisions/storyboard-2/reject") {
      expect(payload).toEqual({ reviewer: "local-user", note: "" });
      revisions = revisions.map((revision) =>
        revision.revision_id === "storyboard-2"
          ? { ...revision, approval_status: "rejected", current: false }
          : revision,
      );
      return { data: revisions.find((revision) => revision.revision_id === "storyboard-2") };
    }
    throw new Error(`unexpected POST ${url}`);
  });

  mockedPut.mockImplementation(async (url: string, payload?: unknown) => {
    if (url === "/storyboard-revisions/storyboard-1") {
      const update = payload as { content: string };
      const savedCanonical = JSON.parse(update.content);
      revisions = [
        generatedRevision,
        {
          ...editedRevision,
          content: JSON.stringify(savedCanonical),
        },
      ];
      return { data: revisions[1] };
    }
    throw new Error(`unexpected PUT ${url}`);
  });
}

describe("storyboard web editor", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
    mockedPut.mockReset();
  });

  test("keeps the storyboard tab blocked until the script is approved", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1") {
        return { data: chapter };
      }
      if (url === "/chapters/chapter-1/status") {
        return {
          data: {
            status: "script_draft",
            blocking_reason: "",
            next_action: "approve_script",
          },
        };
      }
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: [] };
      }
      throw new Error(`unexpected GET ${url}`);
    });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    expect(await screen.findByRole("heading", { name: "第一章" })).toBeInTheDocument();
    expect(await screen.findByText("未确认剧本，不允许生成分镜。")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /分镜/ })).toHaveAttribute("aria-disabled", "true");
  });

  test("enables the storyboard tab after script approval and shows the empty state", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1") {
        return { data: chapter };
      }
      if (url === "/chapters/chapter-1/status") {
        return { data: scriptApprovedStatus };
      }
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: [] };
      }
      if (url === "/chapters/chapter-1/storyboard/revisions") {
        return { data: [] };
      }
      throw new Error(`unexpected GET ${url}`);
    });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    const storyboardTab = await screen.findByRole("tab", { name: "分镜" });
    expect(storyboardTab).not.toHaveAttribute("aria-disabled", "true");
    fireEvent.click(storyboardTab);

    expect(await screen.findByText("暂无分镜。确认剧本后生成分镜。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "生成分镜" })).toBeEnabled();
  });

  test("keeps post-storyboard tabs locked with milestone boundary copy after storyboard approval", async () => {
    mockedGet.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1") {
        return { data: chapter };
      }
      if (url === "/chapters/chapter-1/status") {
        return {
          data: {
            status: "storyboard_approved",
            blocking_reason: "",
            next_action: "milestone_1_complete",
          },
        };
      }
      if (url === "/chapters/chapter-1/script/revisions") {
        return { data: [] };
      }
      if (url === "/chapters/chapter-1/storyboard/revisions") {
        return { data: [generatedRevision] };
      }
      throw new Error(`unexpected GET ${url}`);
    });

    renderWithQueryClient(<ChapterWorkspace chapterId="chapter-1" projectId="project-1" />);

    expect(await screen.findByText("分镜已确认")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Shot Prompt" })).not.toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Agnes 生成和结果与重跑保持锁定。")).toBeInTheDocument();
    expect(screen.queryByText("未确认分镜，不允许进入后续生产步骤。")).not.toBeInTheDocument();
  });

  test("generates a storyboard, shows canonical shots, edits a shot, saves a new revision, and confirms it", async () => {
    setupStoryboardMocks([]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    fireEvent.click(await screen.findByRole("button", { name: "生成分镜" }));

    await waitFor(() => expect(mockedPost).toHaveBeenCalledWith("/chapters/chapter-1/storyboard/generate"));
    expect(await screen.findByText("storyboard_canonical_schema")).toBeInTheDocument();
    expect(screen.getAllByText("PASS").length).toBeGreaterThan(0);

    const shotTable = screen.getByRole("table", { name: "Canonical shot table" });
    expect(within(shotTable).getByText("shot_order")).toBeInTheDocument();
    expect(within(shotTable).getByText("duration_seconds")).toBeInTheDocument();
    expect(within(shotTable).getByText("shot_size")).toBeInTheDocument();
    expect(within(shotTable).getByText("camera_angle")).toBeInTheDocument();
    expect(within(shotTable).getByText("camera_movement")).toBeInTheDocument();
    expect(within(shotTable).getByText("visual_composition")).toBeInTheDocument();
    expect(within(shotTable).getByText("character_positions")).toBeInTheDocument();
    expect(within(shotTable).getByText("character_actions")).toBeInTheDocument();
    expect(within(shotTable).getByText("emotion_performance")).toBeInTheDocument();
    expect(within(shotTable).getByText("dialogue")).toBeInTheDocument();
    expect(within(shotTable).getByText("continuity_in")).toBeInTheDocument();
    expect(within(shotTable).getByText("continuity_out")).toBeInTheDocument();

    fireEvent.click(within(shotTable).getByRole("button", { name: "SHOT_001" }));
    expect(screen.getByLabelText("shot_order")).toHaveValue(1);
    expect(screen.getByLabelText("duration_seconds")).toHaveValue(8);

    fireEvent.change(screen.getByLabelText("shot_size"), { target: { value: "close_up" } });
    fireEvent.change(screen.getByLabelText("dialogue"), {
      target: {
        value: JSON.stringify([
          {
            speaker_character_id: "CHAR_SHEN_QINGHE",
            text: "这本账必须重查。",
            lip_sync_required: true,
          },
        ]),
      },
    });

    expect(screen.getByRole("button", { name: "确认分镜" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "拒绝分镜" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "保存为新分镜版本" }));

    await waitFor(() => expect(mockedPut).toHaveBeenCalledTimes(1));
    const [putUrl, putPayload] = mockedPut.mock.calls[0];
    expect(putUrl).toBe("/storyboard-revisions/storyboard-1");
    const savedCanonical = JSON.parse(putPayload.content);
    expect(savedCanonical.shots[0].shot_size).toBe("close_up");
    expect(savedCanonical.shots[0].dialogue[0].text).toBe("这本账必须重查。");

    expect(await screen.findByText("Revision 2")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("shot_size")).toHaveValue("close_up"));

    fireEvent.click(screen.getByRole("button", { name: "确认分镜" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/storyboard-revisions/storyboard-2/approve", {
        reviewer: "local-user",
        note: "",
      }),
    );
    expect(await screen.findByText("已确认")).toBeInTheDocument();
  });

  test("can reject a clean storyboard revision", async () => {
    setupStoryboardMocks([editedRevision]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "拒绝分镜" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/storyboard-revisions/storyboard-2/reject", {
        reviewer: "local-user",
        note: "",
      }),
    );
    expect(await screen.findByText("已拒绝")).toBeInTheDocument();
  });

  test("runs validation for a clean storyboard revision", async () => {
    setupStoryboardMocks([generatedRevision]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "运行分镜验证" }));

    await waitFor(() =>
      expect(mockedPost).toHaveBeenCalledWith("/storyboard-revisions/storyboard-1/validate"),
    );
    await waitFor(() => expect(screen.getAllByText("storyboard_canonical_schema").length).toBeGreaterThan(1));
  });

  test("shows backend error code and message with retry when storyboard generation fails", async () => {
    mockedGet.mockResolvedValue({ data: [] });
    mockedPost.mockRejectedValue({
      response: {
        data: {
          error_code: "SOURCE_REVISION_NOT_APPROVED",
          error_message: "source revision is not approved",
        },
      },
    });

    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    fireEvent.click(await screen.findByRole("button", { name: "生成分镜" }));

    expect(await screen.findByText("SOURCE_REVISION_NOT_APPROVED")).toBeInTheDocument();
    expect(screen.getByText("source revision is not approved")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /重\s*试/ }));

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(2));
  });

  test("does not retry storyboard generation after the draft becomes dirty", async () => {
    let generateAttempts = 0;
    setupStoryboardMocks([generatedRevision]);
    mockedPost.mockImplementation(async (url: string) => {
      if (url === "/chapters/chapter-1/storyboard/generate") {
        generateAttempts += 1;
        throw {
          response: {
            data: {
              error_code: "GENERATION_FAILED",
              error_message: "generation failed",
            },
          },
        };
      }
      throw new Error(`unexpected POST ${url}`);
    });
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "生成分镜" }));
    const retryButton = await screen.findByRole("button", { name: /重\s*试/ });

    fireEvent.change(screen.getByLabelText("shot_size"), {
      target: { value: "close_up" },
    });

    await waitFor(() => expect(screen.getByRole("button", { name: "生成分镜" })).toBeDisabled());
    expect(retryButton).toBeDisabled();
    fireEvent.click(retryButton);

    expect(generateAttempts).toBe(1);
    expect(screen.getByLabelText("shot_size")).toHaveValue("close_up");
  });

  test("blocks saving invalid JSON shot fields until they are valid again", async () => {
    setupStoryboardMocks([generatedRevision]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("visual_composition"), {
      target: { value: "{" },
    });

    expect(await screen.findByText("visual_composition 不是有效 JSON。")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "保存为新分镜版本" })).toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "保存为新分镜版本" }));
    expect(mockedPut).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("visual_composition"), {
      target: {
        value: JSON.stringify({
          framing: "tight close-up",
          subject_focus: "CHAR_SHEN_QINGHE",
          background_relation: "account book dominates foreground",
          screen_direction: null,
        }),
      },
    });
    expect(screen.queryByText("visual_composition 不是有效 JSON。")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "保存为新分镜版本" }));

    await waitFor(() => expect(mockedPut).toHaveBeenCalledTimes(1));
    const savedCanonical = JSON.parse(mockedPut.mock.calls[0][1].content);
    expect(savedCanonical.shots[0].visual_composition).toEqual({
      framing: "tight close-up",
      subject_focus: "CHAR_SHEN_QINGHE",
      background_relation: "account book dominates foreground",
      screen_direction: null,
    });
  });

  test("keeps invalid JSON blocking save after unrelated shot edits", async () => {
    setupStoryboardMocks([generatedRevision]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("visual_composition"), {
      target: { value: "{" },
    });
    expect(await screen.findByText("visual_composition 不是有效 JSON。")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("shot_size"), {
      target: { value: "close_up" },
    });

    expect(screen.getByText("visual_composition 不是有效 JSON。")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "保存为新分镜版本" })).toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "保存为新分镜版本" }));
    expect(mockedPut).not.toHaveBeenCalled();
  });

  test("keeps invalid JSON blocking shot switching", async () => {
    setupStoryboardMocks([multiShotRevision]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    const shotTable = screen.getByRole("table", { name: "Canonical shot table" });
    expect(within(shotTable).getByRole("button", { name: "SHOT_002" })).toBeEnabled();

    fireEvent.change(screen.getByLabelText("visual_composition"), {
      target: { value: "{" },
    });

    expect(await screen.findByText("visual_composition 不是有效 JSON。")).toBeInTheDocument();
    await waitFor(() =>
      expect(within(shotTable).getByRole("button", { name: "SHOT_002" })).toBeDisabled(),
    );
    fireEvent.click(within(shotTable).getByRole("button", { name: "SHOT_002" }));

    expect(within(screen.getByLabelText("分镜 inspector")).getByText("SHOT_001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存为新分镜版本" })).toBeDisabled();
    expect(mockedPut).not.toHaveBeenCalled();
  });

  test("does not discard a dirty draft by switching storyboard revisions", async () => {
    setupStoryboardMocks([
      { ...generatedRevision, current: true },
      { ...editedRevision, current: false },
    ]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    expect(screen.getByText("Revision 2")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("shot_size"), {
      target: { value: "close_up" },
    });

    await waitFor(() => expect(screen.getByRole("button", { name: "Revision 2" })).toBeDisabled());
    fireEvent.click(screen.getByRole("button", { name: "Revision 2" }));

    expect(screen.getByLabelText("shot_size")).toHaveValue("close_up");
    expect(screen.getByRole("button", { name: "保存为新分镜版本" })).toBeEnabled();
  });

  test("does not retry a stale storyboard save after the draft changes", async () => {
    let putAttempts = 0;
    setupStoryboardMocks([generatedRevision]);
    mockedPut.mockImplementation(async (url: string, payload?: unknown) => {
      if (url === "/storyboard-revisions/storyboard-1") {
        putAttempts += 1;
        if (putAttempts === 1) {
          throw {
            response: {
              data: {
                error_code: "SAVE_FAILED",
                error_message: "save failed",
              },
            },
          };
        }
        const update = payload as { content: string };
        return { data: { ...editedRevision, content: update.content } };
      }
      throw new Error(`unexpected PUT ${url}`);
    });
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("shot_size"), {
      target: { value: "close_up" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存为新分镜版本" }));
    const retryButton = await screen.findByRole("button", { name: /重\s*试/ });
    expect(retryButton).toBeEnabled();

    fireEvent.change(screen.getByLabelText("shot_size"), {
      target: { value: "wide" },
    });

    await waitFor(() => expect(retryButton).toBeDisabled());
    fireEvent.click(retryButton);

    expect(putAttempts).toBe(1);
    expect(screen.getByLabelText("shot_size")).toHaveValue("wide");
  });

  test("does not discard a dirty draft by generating a replacement storyboard", async () => {
    setupStoryboardMocks([generatedRevision]);
    renderWithQueryClient(<StoryboardTab chapter={chapter} status={scriptApprovedStatus} />);

    expect(await screen.findByText("Revision 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("shot_size"), {
      target: { value: "close_up" },
    });

    await waitFor(() => expect(screen.getByRole("button", { name: "生成分镜" })).toBeDisabled());
    fireEvent.click(screen.getByRole("button", { name: "生成分镜" }));

    expect(screen.getByLabelText("shot_size")).toHaveValue("close_up");
    expect(mockedPost).not.toHaveBeenCalledWith("/chapters/chapter-1/storyboard/generate");
  });
});
