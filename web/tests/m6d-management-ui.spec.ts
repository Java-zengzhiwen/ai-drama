import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_M6D_BACKEND_PORT ?? "18766";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;

const runningInVitest = Boolean(process.env.VITEST);

function sourceFor(version: string, marker: string) {
  return `export const vendor = {
  id: "m6d-local",
  version: "${version}",
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
  return { output: "# ${marker}\\n\\nruntime_model: local-fake\\nsource_basis: browser-e2e\\n\\n## Scene: 1-1\\n\\n【画面】本地假供应商完成确定性剧本输出。\\n\\n【动作】角色检查模型版本。\\n\\n【台词】角色：${marker}。", usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 } };
}`;
}

const VALID_SOURCE = sourceFor("1.0.0", "M6D_BROWSER_VERSION_1");

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
    await expect(page.getByLabel("供应商名称")).toBeFocused();
    await page.getByLabel("供应商名称").fill(supplierName);
    await page.getByLabel("供应商标识").fill(`m6d-${unique}`);
    await page.getByRole("button", { name: "创建空模板" }).click();
    await page.getByRole("button", { name: `停用 ${supplierName}` }).click();
    await expect(page.getByRole("button", { name: `启用 ${supplierName}` })).toBeVisible();
    await page.getByRole("button", { name: `启用 ${supplierName}` }).click();
    await expect(page.getByRole("button", { name: `停用 ${supplierName}` })).toBeVisible();
    await page.getByRole("link", { name: new RegExp(supplierName) }).click();
    await expect(page.getByRole("heading", { name: supplierName })).toBeVisible();
    const supplierId = new URL(page.url()).pathname.split("/suppliers/")[1];

    await page.getByRole("tab", { name: "模型" }).focus();
    await page.getByRole("tab", { name: "模型" }).press("ArrowLeft");
    await expect(page.getByRole("tab", { name: "适配代码" })).toHaveAttribute("aria-selected", "true");
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

    await page.getByRole("button", { name: "新增模型" }).click();
    await page.getByLabel("显示名称").fill("Disposable Image");
    await page.getByLabel("供应商模型名").fill("disposable-image-v1");
    await page.getByLabel("能力", { exact: true }).selectOption("image");
    await page.getByRole("button", { name: "保存新模型" }).click();
    const disposableRow = page.getByRole("row", { name: /Disposable Image/ });
    await disposableRow.getByRole("button", { name: "删除 Disposable Image" }).click();
    await page.getByRole("button", { name: "确认删除模型" }).click();
    await expect(page.getByRole("row", { name: /Disposable Image/ })).toHaveCount(0);

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

    const chapterResponse = await request.post(
      `${backendURL}/api/projects/${project.project_id}/chapters`,
      { data: { title: "Browser fake execution", position: 1 } },
    );
    expect(chapterResponse.ok()).toBeTruthy();
    const chapter = (await chapterResponse.json()) as { chapter_id: string };
    const sourceResponse = await request.post(
      `${backendURL}/api/chapters/${chapter.chapter_id}/source-revisions`,
      { data: { content: "只在本地 fake supplier 中执行，不访问真实供应商。" } },
    );
    expect(sourceResponse.ok()).toBeTruthy();
    const firstExecution = await browserPost<{ content: string }>(
      page,
      `/api/chapters/${chapter.chapter_id}/script/generate`,
    );
    expect(firstExecution.content).toContain("M6D_BROWSER_VERSION_1");

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

    await page.getByRole("tab", { name: "适配代码" }).click();
    await page.getByLabel("TypeScript 供应商适配代码").fill(
      sourceFor("2.0.0", "M6D_BROWSER_VERSION_2"),
    );
    await page.getByRole("button", { name: "校验并保存" }).click();
    await expect(page.getByRole("status")).toContainText("已保存不可变版本");
    const secondExecution = await browserPost<{ content: string }>(
      page,
      `/api/chapters/${chapter.chapter_id}/script/generate`,
    );
    expect(secondExecution.content).toContain("M6D_BROWSER_VERSION_2");

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
    await page.getByRole("tab", { name: "适配代码" }).click();
    await expect(page.getByRole("button", { name: "恢复内置版本" })).toBeVisible();
    await page.getByRole("button", { name: "恢复内置版本" }).click();
    await expect(page.getByRole("dialog", { name: "恢复内置版本" })).toContainText("历史版本和已创建任务不会被删除");
    await page.getByRole("button", { name: "确认恢复" }).click();
    await page.reload();
    await expect(page.getByRole("heading", { name: "OpenAI" })).toBeVisible();
    expect(consoleErrors).toEqual([]);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("M6D uses the approved compact supplier selector at 768px", async ({ page, request }) => {
    await proxyApi(page, request);
    await page.setViewportSize({ width: 768, height: 900 });
    await page.goto("/suppliers");
    await page.getByRole("link", { name: /OpenAI/ }).click();
    await expect(page.getByLabel("切换供应商")).toBeVisible();
    await expect(page.locator(".supplier-rail > a").first()).toBeHidden();
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

  test("M6D rejects stale config code and model writes with explicit reload actions", async ({ page, request }) => {
    await proxyApi(page, request);
    const unique = Date.now().toString(36);
    const created = await request.post(`${backendURL}/api/suppliers`, {
      data: { slug: `cas-${unique}`, display_name: `CAS ${unique}` },
      headers: { "If-None-Match": "*", "Idempotency-Key": `cas-${unique}` },
    });
    const supplier = (await created.json()) as { supplier_id: string };
    await request.put(`${backendURL}/api/suppliers/${supplier.supplier_id}/code`, {
      data: { source: VALID_SOURCE },
      headers: { "If-Match": '"supplier-1"' },
    });
    const modelCreated = await request.post(`${backendURL}/api/suppliers/${supplier.supplier_id}/models`, {
      data: { display_name: "CAS Text", provider_model_name: "cas-text", capability: "text", definition: {} },
      headers: {
        "If-Match": '"model-catalog-0"',
        "If-None-Match": "*",
        "Idempotency-Key": `cas-model-${unique}`,
      },
    });
    expect(modelCreated.ok()).toBeTruthy();
    const model = (await modelCreated.json()) as { supplier_model_id: string };

    await page.goto(`/suppliers/${supplier.supplier_id}`);
    await page.getByRole("tab", { name: "配置" }).click();
    await page.route(`${frontendURL}/api/suppliers/${supplier.supplier_id}/config`, staleMutation);
    await page.getByLabel("Base URL").fill("https://fake.invalid/v2");
    await page.getByRole("button", { name: "保存配置" }).click();
    await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
    await page.unroute(`${frontendURL}/api/suppliers/${supplier.supplier_id}/config`, staleMutation);

    await page.getByRole("tab", { name: "适配代码" }).click();
    await page.route(`${frontendURL}/api/suppliers/${supplier.supplier_id}/code`, staleMutation);
    await page.getByRole("button", { name: "校验并保存" }).click();
    await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
    await page.unroute(`${frontendURL}/api/suppliers/${supplier.supplier_id}/code`, staleMutation);

    await page.getByRole("tab", { name: "模型" }).click();
    await page.getByRole("row", { name: /CAS Text/ }).getByRole("button", { name: "编辑 CAS Text" }).click();
    await page.route(`${frontendURL}/api/models/${model.supplier_model_id}`, staleMutation);
    await page.getByRole("button", { name: "保存新版本" }).click();
    await expect(page.getByRole("dialog", { name: /编辑模型/ }).getByRole("button", { name: "重新加载模型" })).toBeVisible();
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });
}

async function staleMutation(route: import("@playwright/test").Route) {
  if (["PUT", "PATCH"].includes(route.request().method())) {
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ detail: { error_code: "REVISION_CONFLICT" } }),
    });
  } else {
    await route.fallback();
  }
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

async function browserPost<T>(page: Page, path: string): Promise<T> {
  return page.evaluate(async (target) => {
    const response = await fetch(target, { method: "POST" });
    const body = await response.json();
    if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(body)}`);
    return body;
  }, path) as Promise<T>;
}
