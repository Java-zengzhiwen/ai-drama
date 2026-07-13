import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_BACKEND_PORT ?? "18765";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;

const runningInVitest = Boolean(process.env.VITEST);

const VALID_SOURCE = `export const vendor = {
  id: "m6d-local",
  version: "1.0.0",
  name: "M6D Local",
  author: "Playwright",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "m6d-local",
  inputs: [{ key: "base_url", label: "Base URL", type: "url", required: true }],
  inputValues: { base_url: "https://fake.invalid/v1" },
  models: []
};
export async function textRequest(request: { prompt: string }) {
  return { text: request.prompt, usage: { total_tokens: 0 } };
}`;

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("M6D Playwright management UI runs through npm run test:e2e", () => undefined);
} else {
  test("M6D manages supplier code, config, write-only secret, models, and project bindings", async ({
    page,
    request,
  }) => {
    const unexpectedNetwork: string[] = [];
    await proxyApi(page, request);
    page.on("request", (browserRequest) => {
      const url = new URL(browserRequest.url());
      if (!isLocalHost(url.hostname)) unexpectedNetwork.push(browserRequest.url());
    });

    const unique = Date.now().toString(36);
    const supplierName = `M6D Local ${unique}`;
    await page.goto("/suppliers");
    await expect(page.getByRole("heading", { name: "模型供应商" })).toBeVisible();
    await expect(page.getByText("仅本地管理")).toBeVisible();
    await expect(page.getByRole("link", { name: /OpenAI/ })).toBeVisible();

    await page.getByRole("button", { name: "新增供应商" }).click();
    await page.getByLabel("供应商名称").fill(supplierName);
    await page.getByLabel("供应商标识").fill(`m6d-${unique}`);
    await page.getByRole("button", { name: "创建空模板" }).click();
    await page.getByRole("link", { name: new RegExp(supplierName) }).click();
    await expect(page.getByRole("heading", { name: supplierName })).toBeVisible();
    const supplierId = new URL(page.url()).pathname.split("/suppliers/")[1];

    await page.getByRole("tab", { name: "适配代码" }).click();
    const editor = page.getByLabel("TypeScript 供应商适配代码");
    await expect(editor).toBeVisible();
    await editor.fill("import fs from 'node:fs';");
    await page.getByRole("button", { name: "校验并保存" }).click();
    await expect(page.getByRole("alert")).toContainText("第 1 行");

    await editor.fill(VALID_SOURCE);
    await page.getByRole("button", { name: "校验并保存" }).click();
    await expect(page.getByRole("status")).toContainText("已保存不可变版本");

    await page.reload();
    await expect(page.getByRole("heading", { name: supplierName })).toBeVisible();
    await page.getByRole("tab", { name: "配置" }).click();
    await page.getByLabel("Base URL").fill("http://private.invalid/v1");
    await page.getByRole("button", { name: "保存配置" }).click();
    await expect(page.getByRole("alert")).toContainText("Base URL 必须使用 HTTPS");
    await page.getByLabel("Base URL").fill("https://fake.invalid/v2");
    await page.getByRole("button", { name: "保存配置" }).click();
    await expect(page.getByRole("status")).toHaveText("配置已保存为新版本。");

    const secret = `m6d-secret-${unique}-7890`;
    await page.getByRole("tab", { name: "密钥" }).click();
    await page.getByLabel("新的 API Key").fill(secret);
    await page.getByRole("button", { name: "显示未保存的密钥" }).click();
    await expect(page.getByLabel("新的 API Key")).toHaveAttribute("type", "text");
    await page.getByRole("button", { name: "保存密钥" }).click();
    await expect(page.getByLabel("新的 API Key")).toHaveValue("");
    await expect(page.getByText("已配置 ····7890")).toBeVisible();
    const supplierReadback = await request.get(`${backendURL}/api/suppliers/${supplierId}`);
    expect(await supplierReadback.text()).not.toContain(secret);

    await page.getByRole("tab", { name: "模型" }).click();
    await page.getByRole("button", { name: "新增模型" }).click();
    await page.getByLabel("显示名称").fill("Local Text");
    await page.getByLabel("供应商模型名").fill("local-text-v1");
    await page.getByLabel("能力", { exact: true }).selectOption("text");
    await page.getByLabel("模式与约束 JSON").fill('{"max_tokens":4096}');
    await page.getByRole("button", { name: "保存新模型" }).click();
    const modelRow = page.getByRole("row", { name: /Local Text/ });
    await expect(modelRow).toContainText("Overlay");
    await modelRow.getByRole("button", { name: "停用 Local Text" }).click();
    await expect(page.getByRole("row", { name: /Local Text/ })).toContainText("已停用");
    await page.getByRole("row", { name: /Local Text/ }).getByRole("button", { name: "启用 Local Text" }).click();
    await expect(page.getByRole("row", { name: /Local Text/ })).toContainText("已启用");
    await page.getByRole("row", { name: /Local Text/ }).getByRole("button", { name: "查看 Local Text" }).click();
    await expect(page.getByRole("complementary", { name: "模型检查器" })).toContainText("supplier_model_id");

    const modelsResponse = await request.get(`${backendURL}/api/suppliers/${supplierId}/models`);
    const models = (await modelsResponse.json()) as Array<{ supplier_model_id: string }>;
    const modelId = models.find((model) => Boolean(model.supplier_model_id))!.supplier_model_id;
    const projectResponse = await request.post(`${backendURL}/api/projects`, {
      data: {
        name: `M6D Project ${unique}`,
        description: "local fake management acceptance",
        series_canon: "local",
        characters_context: "local",
        production_brief: "local",
      },
    });
    expect(projectResponse.ok()).toBeTruthy();
    const project = (await projectResponse.json()) as { project_id: string };

    await page.goto(`/projects/${project.project_id}/model-bindings`);
    await expect(page.getByRole("heading", { name: "项目模型配置" })).toBeVisible();
    await expect(page.getByRole("note")).toContainText("现有 queued/submitted/polling 任务继续使用创建时快照");
    await page.getByLabel("默认文本模型").selectOption(modelId);
    await page.getByLabel("剧本改编").selectOption(modelId);
    await expect(page.getByTestId("binding-source-script_adaptation")).toHaveText("显式覆盖");
    await page.getByRole("button", { name: "保存全部模型配置" }).click();
    await expect(page.getByRole("status")).toContainText("只影响未来创建的任务");
    await page.getByRole("button", { name: "刷新解析预览" }).click();
    await expect(page.getByText(/local-text-v1 · 显式覆盖/)).toBeVisible();

    await page.goto(`/suppliers/${supplierId}`);
    await page.getByRole("tab", { name: "模型" }).click();
    await page.getByRole("row", { name: /Local Text/ }).getByRole("button", { name: "编辑 Local Text" }).click();
    await expect(page.getByText("我已确认将影响 2 处项目绑定")).toBeVisible();
    await expect(page.getByRole("button", { name: "保存新版本" })).toBeDisabled();
    await page.getByText("我已确认将影响 2 处项目绑定").click();
    await page.getByLabel("显示名称").fill("Local Text Revised");
    await page.getByRole("button", { name: "保存新版本" }).click();
    await expect(page.getByRole("row", { name: /Local Text Revised/ })).toContainText(/r\d+/);
    await expect(page.getByRole("row", { name: /Local Text Revised/ }).getByRole("button", { name: "删除 Local Text Revised" })).toBeDisabled();

    expect(unexpectedNetwork).toEqual([]);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("M6D primary management routes refresh without console errors", async ({ page, request }) => {
    const consoleErrors: string[] = [];
    await proxyApi(page, request);
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    await page.goto("/suppliers");
    await expect(page.getByRole("heading", { name: "模型供应商" })).toBeVisible();
    await page.getByRole("link", { name: /OpenAI/ }).click();
    await expect(page.getByRole("heading", { name: "OpenAI" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "OpenAI" })).toBeVisible();
    expect(consoleErrors).toEqual([]);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("M6D presents stable conflict and local-only failures without leaking details", async ({ page, request }) => {
    await proxyApi(page, request);
    const unique = Date.now().toString(36);
    const created = await request.post(`${backendURL}/api/projects`, {
      data: {
        name: `Conflict ${unique}`,
        description: "local",
        series_canon: "local",
        characters_context: "local",
        production_brief: "local",
      },
    });
    const project = (await created.json()) as { project_id: string };
    await page.goto(`/projects/${project.project_id}/model-bindings`);
    await expect(page.getByRole("heading", { name: "项目模型配置" })).toBeVisible();
    await page.route(`${frontendURL}/api/projects/${project.project_id}/model-bindings`, async (route) => {
      if (route.request().method() === "PUT") {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ detail: { error_code: "REVISION_CONFLICT" } }),
        });
      } else {
        await route.fallback();
      }
    });
    await page.getByRole("button", { name: "保存全部模型配置" }).click();
    await expect(page.getByRole("alert")).toContainText("数据已在其他页面更新");
    await expect(page.getByRole("button", { name: "重新加载绑定" })).toBeVisible();

    await page.unrouteAll({ behavior: "wait" });
    await page.route(`${frontendURL}/api/suppliers`, async (route) => {
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          error_code: "LOCAL_MANAGEMENT_ONLY",
          error_message: "supplier management is local only",
        }),
      });
    });
    await page.goto("/suppliers");
    await expect(page.getByRole("alert")).toContainText("只能在运行 AI Drama 的本机访问");
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });
}

async function proxyApi(page: Page, request: APIRequestContext) {
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
}

function isLocalHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "::1";
}
