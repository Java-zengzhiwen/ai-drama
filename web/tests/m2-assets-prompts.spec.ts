import { expect, type Locator, type Page, test } from "@playwright/test";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_BACKEND_PORT ?? "18765";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;

const pngBytes = Buffer.from(
  "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63f80f000101010018dd8db00000000049454e44ae426082",
  "hex",
);

const runningInVitest = Boolean(process.env.VITEST);

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("M2 Playwright workflow runs through npm run test:e2e", () => undefined);
} else {
  test("M2 workflow creates visual assets, analyzes requirements, and generates shot prompts", async ({
    page,
    request,
  }) => {
    const unique = Date.now().toString(36);

    await page.route(`${frontendURL}/api/**`, async (route) => {
      const browserRequest = route.request();
      const browserURL = new URL(browserRequest.url());
      const apiResponse = await request.fetch(`${backendURL}${browserURL.pathname}${browserURL.search}`, {
        data: browserRequest.postDataBuffer() ?? undefined,
        headers: browserRequest.headers(),
        method: browserRequest.method(),
      });
      await route.fulfill({ response: apiResponse });
    });

    await createApprovedStoryboard(page, unique);

    await page.getByRole("tab", { name: "资料与资产" }).click();
    await expect(page.getByLabel("资料与资产工作台")).toBeVisible();

    await createProfile(page, "character", "CHAR_SHEN_QINGHE", {
      continuity: "Same face, same blue robe, same restrained posture.",
      identity: "Young merchant-house daughter with guarded confidence.",
      appearance: "Natural face, practical hair, realistic period styling.",
      costume: "Blue robe and pale inner collar remain consistent.",
    });
    await createProfile(page, "scene", "SCENE_001", {
      continuity: "Morning bedroom layout stays consistent.",
      layout: "Bed at rear, table at right, still wardrobe in background.",
      lighting: "Soft daylight through paper windows.",
    });
    await createProfile(page, "scene", "SCENE_002", {
      continuity: "Account room layout stays consistent.",
      layout: "Desk centered with account book and ink stone.",
      lighting: "Low daylight, restrained contrast.",
    });

    await uploadAsset(page, "character_reference", "CHAR_SHEN_QINGHE reference");
    await generateAsset(page, "scene_reference", "SCENE_001 generated", "realistic morning bedroom reference");
    await uploadAsset(page, "scene_reference", "SCENE_002 reference");
    await uploadAsset(page, "shot_keyframe", "SHOT_001 keyframe");
    await uploadAsset(page, "shot_keyframe", "SHOT_002 keyframe");

    await markUsableAndBind(page, "CHAR_SHEN_QINGHE reference", {
      role: "primary_reference",
      targetName: "CHAR_SHEN_QINGHE",
      targetType: "character",
    });
    await markUsableAndBind(page, "SCENE_001 generated", {
      role: "layout_reference",
      targetName: "SCENE_001",
      targetType: "scene",
    });
    await markUsableAndBind(page, "SCENE_002 reference", {
      role: "layout_reference",
      targetName: "SCENE_002",
      targetType: "scene",
    });
    await markUsableAndBind(page, "SHOT_001 keyframe", {
      role: "keyframe",
      targetName: "SHOT_001",
      targetType: "shot",
    });
    await markUsableAndBind(page, "SHOT_002 keyframe", {
      role: "keyframe",
      targetName: "SHOT_002",
      targetType: "shot",
    });

    await page.getByRole("tab", { name: "Shot Prompt" }).click();
    await expect(page.getByLabel("Shot Prompt 工作台")).toBeVisible();
    await page.getByRole("button", { name: "重新分析资产需求" }).click();
    await expect(page.getByRole("button", { name: "生成全章 Shot Prompt" })).toBeEnabled();
    await page.getByRole("button", { name: "生成全章 Shot Prompt" }).click();

    const shotRows = page.getByRole("table", { name: "Shot prompt rows" });
    await expect(shotRows).toBeVisible();
    await expect(shotRows.getByRole("button", { name: "SHOT_001" })).toBeVisible();
    await expect(page.getByLabel("positive_prompt")).toHaveValue(/Live action SHOT_001/);
    await expect(page.getByRole("region", { name: "shot prompt inspector" })).toContainText("Agnes 参数预览");
    await page.getByRole("button", { name: "标记当前镜头 Ready" }).click();
    await expect(page.getByLabel("Prompt Gate").getByText("ready", { exact: true })).toBeVisible();
    const chapterId = new URL(page.url()).pathname.split("/chapters/")[1];
    const statusResponse = await request.get(`${backendURL}/api/chapters/${chapterId}/status`);
    await expect(statusResponse).toBeOK();
    expect(await statusResponse.json()).toEqual({
      status: "prompts_draft",
      blocking_reason: "",
      next_action: "mark_shot_prompts_ready",
    });

    await expect(page.getByRole("tab", { name: /Agnes 生成/ })).toHaveAttribute("aria-disabled", "true");
    await expect(page.getByRole("tab", { name: /结果与重跑/ })).toHaveAttribute("aria-disabled", "true");
  });
}

async function createApprovedStoryboard(page: Page, unique: string) {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "项目列表" })).toBeVisible();
  await page.getByLabel("项目名称").fill(`M2 验证项目 ${unique}`);
  await page.getByLabel("项目描述").fill("古装重生短剧");
  await page.getByLabel("系列设定").fill("明代商贾世界");
  await page.getByLabel("人物上下文").fill("沈清荷、沈清莲、顾长渊");
  await page.getByLabel("制作简述").fill("真人写实，16:9，低饱和");
  await page.getByRole("button", { name: "创建项目" }).click();
  await page.getByRole("link", { name: `M2 验证项目 ${unique}` }).click();

  await page.getByLabel("章节标题").fill("第一章");
  await page.getByLabel("章节序号").fill("1");
  await page.getByRole("button", { name: "添加章节" }).click();
  await page.getByRole("link", { name: "第一章" }).click();

  await page.getByLabel("小说原文").fill("沈清荷醒来后发现自己回到成亲前，她决定重新查账。");
  await page.getByRole("button", { name: "保存原文" }).click();
  await expect(page.getByText("原文已保存为新版本。")).toBeVisible();

  await page.getByRole("tab", { name: "剧本" }).click();
  await page.getByRole("button", { name: "生成剧本" }).click();
  await expect(page.getByRole("button", { name: "确认剧本" })).toBeEnabled();
  await page.getByRole("button", { name: "确认剧本" }).click();
  await expect(page.getByText("剧本已确认")).toBeVisible();

  await page.getByRole("tab", { name: "分镜" }).click();
  await page.getByRole("button", { name: "生成分镜" }).click();
  await expect(page.getByRole("table", { name: "Canonical shot table" })).toBeVisible();
  await expect(page.getByRole("button", { name: "确认分镜" })).toBeEnabled();
  await page.getByRole("button", { name: "确认分镜" }).click();
  await expect(page.getByLabel("workflow rail").getByText("分镜已确认", { exact: true })).toBeVisible();
}

async function createProfile(
  page: Page,
  type: "character" | "scene",
  name: string,
  notes: {
    appearance?: string;
    continuity: string;
    costume?: string;
    identity?: string;
    layout?: string;
    lighting?: string;
  },
) {
  const form = page.getByRole("form", { name: "生产资料编辑" });
  await form.getByLabel("资料类型").selectOption(type);
  await form.getByLabel("资料名称").fill(name);
  await form.getByLabel("连续性说明").fill(notes.continuity);
  if (type === "character") {
    await form.getByLabel("身份说明").fill(notes.identity ?? "");
    await form.getByLabel("外貌说明").fill(notes.appearance ?? "");
    await form.getByLabel("服装说明").fill(notes.costume ?? "");
  } else {
    await form.getByLabel("布局说明").fill(notes.layout ?? "");
    await form.getByLabel("光线说明").fill(notes.lighting ?? "");
  }
  await form.getByRole("button", { name: "创建资料" }).click();
  await expect(page.getByLabel("生产资料列表").getByText(name)).toBeVisible();
}

async function uploadAsset(page: Page, type: string, name: string) {
  const form = page.getByRole("form", { name: "资产上传" });
  await form.getByLabel("上传资产类型").selectOption(type);
  await form.getByLabel("上传资产名称").fill(name);
  await form.getByLabel("资产文件").setInputFiles({
    buffer: pngBytes,
    mimeType: "image/png",
    name: `${name}.png`,
  });
  await form.getByRole("button", { name: "上传资产" }).click();
  await expect(page.getByLabel(`资产 ${name}`)).toBeVisible();
  await expect(page.getByAltText(`${name} 缩略图`)).toBeVisible();
}

async function generateAsset(page: Page, type: string, name: string, prompt: string) {
  const form = page.getByRole("form", { name: "Agnes 图片请求" });
  await form.getByLabel("Agnes 资产类型").selectOption(type);
  await form.getByLabel("Agnes 资产名称").fill(name);
  await form.getByLabel("参考类型").selectOption("scene");
  await form.getByLabel("Agnes 提示词").fill(prompt);
  await form.getByRole("button", { name: "请求 Agnes 图片" }).click();
  await expect(page.getByLabel(`资产 ${name}`)).toBeVisible();
  await expect(page.getByAltText(`${name} 缩略图`)).toBeVisible();
}

async function markUsableAndBind(
  page: Page,
  assetName: string,
  binding: {
    role: string;
    targetName: string;
    targetType: "character" | "scene" | "shot";
  },
) {
  const card = page.getByLabel(`资产 ${assetName}`);
  await card.getByRole("button", { name: "标记可用" }).click();
  await expect(card.getByText("usable", { exact: true })).toBeVisible();

  const form = card.getByRole("form", { name: `${assetName} 绑定` });
  await form.getByLabel("绑定目标类型").selectOption(binding.targetType);
  if (binding.targetType === "shot") {
    await form.getByLabel("绑定目标", { exact: true }).fill(binding.targetName);
  } else {
    await form.getByLabel("绑定目标", { exact: true }).selectOption({ label: binding.targetName });
  }
  await form.getByLabel("绑定角色").fill(binding.role);
  await setCheckbox(form.getByLabel("设为当前绑定"));
  await form.getByRole("button", { name: "绑定资产" }).click();
  await expect(card.getByText("当前采用", { exact: true })).toBeVisible();
}

async function setCheckbox(locator: Locator) {
  if (!(await locator.isChecked())) {
    await locator.check();
  }
}
