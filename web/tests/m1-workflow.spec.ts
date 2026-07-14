import { expect, test } from "./network-test";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_BACKEND_PORT ?? "18765";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;

const runningInVitest = Boolean(process.env.VITEST);

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("M1 Playwright workflow runs through npm run test:e2e", () => undefined);
} else {
  test("M1 web workflow approves storyboard from a new chapter", async ({ page, request }) => {
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

    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: "项目列表" })).toBeVisible();
    await page.getByLabel("项目名称").fill(`M1 验证项目 ${unique}`);
    await page.getByLabel("项目描述").fill("古装重生短剧");
    await page.getByLabel("系列设定").fill("明代商贾世界");
    await page.getByLabel("人物上下文").fill("沈清荷、沈清莲、顾长渊");
    await page.getByLabel("制作简述").fill("真人写实，16:9，低饱和");
    await page.getByRole("button", { name: "创建项目" }).click();
    await page.getByRole("link", { name: `M1 验证项目 ${unique}` }).click();

    await expect(page.getByRole("heading", { name: `M1 验证项目 ${unique}` })).toBeVisible();
    await page.getByLabel("章节标题").fill("第一章");
    await page.getByLabel("章节序号").fill("1");
    await page.getByRole("button", { name: "添加章节" }).click();
    await expect(page.getByRole("link", { name: "第一章" })).toBeVisible();

    await page.goto("/projects");
    await page.getByRole("link", { name: `M1 验证项目 ${unique}` }).click();
    await expect(page.getByRole("heading", { name: `M1 验证项目 ${unique}` })).toBeVisible();
    await expect(page.getByRole("link", { name: "第一章" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("link", { name: "第一章" })).toBeVisible();
    await page.getByRole("link", { name: "第一章" }).click();

    await page.getByLabel("小说原文").fill("沈清荷醒来后发现自己回到成亲前，她决定重新查账。");
    await page.getByRole("button", { name: "保存原文" }).click();
    await expect(page.getByText("原文已保存为新版本。")).toBeVisible();

    await page.getByRole("tab", { name: "剧本" }).click();
    await page.getByRole("button", { name: "生成剧本" }).click();
    await expect(page.getByRole("button", { name: "确认剧本" })).toBeEnabled();
    await page.getByRole("button", { name: "确认剧本" }).click();
    await expect(page.getByText("剧本已确认")).toBeVisible();

    const storyboardTab = page.getByRole("tab", { name: "分镜" });
    await expect(storyboardTab).toBeEnabled();
    await storyboardTab.click();
    await page.getByRole("button", { name: "生成分镜" }).click();
    await expect(page.getByRole("table", { name: "Canonical shot table" })).toBeVisible();
    await expect(page.getByRole("button", { name: "确认分镜" })).toBeEnabled();
    await page.getByRole("button", { name: "确认分镜" }).click();

    await expect(page.getByLabel("workflow rail").getByText("分镜已确认", { exact: true })).toBeVisible();
    const chapterId = new URL(page.url()).pathname.split("/chapters/")[1];
    const statusResponse = await request.get(`${backendURL}/api/chapters/${chapterId}/status`);
    await expect(statusResponse).toBeOK();
    expect(await statusResponse.json()).toEqual({
      status: "assets_incomplete",
      blocking_reason: "asset requirements are not ready",
      next_action: "analyze_assets",
    });
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });
}
