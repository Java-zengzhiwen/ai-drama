import { expect, type APIRequestContext, type Page, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_M6D_BACKEND_PORT ?? "18766";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;
const runningInVitest = Boolean(process.env.VITEST);
const repoRoot = runningInVitest
  ? resolve(process.cwd(), "..")
  : fileURLToPath(new URL("../..", import.meta.url));

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
  }, testInfo) => {
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

    await page.getByRole("button", { name: "新增模型" }).click();
    await page.getByLabel("显示名称").fill("Queued Video");
    await page.getByLabel("供应商模型名").fill("queued-video-v1");
    await page.getByLabel("能力", { exact: true }).selectOption("video");
    await page.getByRole("button", { name: "保存新模型" }).click();
    await expect(page.getByRole("row", { name: /Queued Video/ })).toContainText("Overlay");

    const modelsResponse = await request.get(`${backendURL}/api/suppliers/${supplierId}/models`);
    const models = (await modelsResponse.json()) as Array<{ supplier_model_id: string; capability: string }>;
    const modelId = models.find((model) => model.capability === "text")!.supplier_model_id;
    const videoModelId = models.find((model) => model.capability === "video")!.supplier_model_id;
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
    await page.getByLabel("默认视频模型").selectOption(videoModelId);
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
    const dataRoot = String(testInfo.config.metadata.m6dDataRoot);
    const queued = createQueuedSnapshotJob(dataRoot, project.project_id, chapter.chapter_id, unique);
    const queuedRead = await browserGet<Array<{ job_id: string; internal_status: string }>>(
      page,
      `/api/chapters/${chapter.chapter_id}/generation/jobs`,
    );
    expect(queuedRead).toContainEqual(expect.objectContaining({
      job_id: queued.job_id,
      internal_status: "queued",
    }));

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
    const afterSave = readQueuedSnapshotJob(dataRoot, queued.job_id);
    expect(afterSave.snapshot_hash).toBe(queued.snapshot_hash);
    expect(afterSave.supplier_version_id).toBe(queued.supplier_version_id);
    expect(afterSave.internal_status).toBe("queued");

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

  test("M6D captures approved desktop 1180 and 768 visual QA", async ({ page, request }, testInfo) => {
    await proxyApi(page, request);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/suppliers");
    await page.getByRole("link", { name: /OpenAI/ }).click();
    await page.getByRole("tab", { name: "模型" }).click();
    await expect(page.getByRole("heading", { name: "模型目录" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("m6d-implementation-desktop-1440.png"), fullPage: true });

    await page.setViewportSize({ width: 1180, height: 1000 });
    await expect(page.getByRole("complementary", { name: "供应商检查器" })).toBeVisible();
    const command = await page.locator(".supplier-command").boundingBox();
    const inspector = await page.locator(".supplier-inspector").boundingBox();
    expect(inspector!.y).toBeGreaterThan(command!.y);
    await page.screenshot({ path: testInfo.outputPath("m6d-implementation-1180.png"), fullPage: true });

    await page.setViewportSize({ width: 768, height: 1000 });
    await expect(page.getByLabel("切换供应商")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("m6d-implementation-768.png"), fullPage: true });
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
    const remoteEdit = await request.patch(`${backendURL}/api/models/${model.supplier_model_id}`, {
      data: { display_name: "CAS Text Remote" },
      headers: { "If-Match": `"model-${model.supplier_model_id}-1", "model-catalog-1"` },
    });
    expect(remoteEdit.ok()).toBeTruthy();
    await page.getByRole("button", { name: "保存新版本" }).click();
    const reloadModel = page.getByRole("dialog", { name: /编辑模型/ }).getByRole("button", { name: "重新加载模型" });
    await expect(reloadModel).toBeVisible();
    await reloadModel.click();
    await expect(page.getByRole("dialog", { name: /编辑模型/ }).getByLabel("显示名称")).toHaveValue("CAS Text Remote");
    await page.getByRole("button", { name: "保存新版本" }).click();
    await expect(page.getByRole("dialog", { name: /编辑模型/ })).toHaveCount(0);
    const finalModel = await request.get(`${backendURL}/api/suppliers/${supplier.supplier_id}/models`);
    const finalModels = (await finalModel.json()) as Array<{ supplier_model_id: string; display_name: string }>;
    expect(finalModels.find((item) => item.supplier_model_id === model.supplier_model_id)?.display_name).toBe("CAS Text Remote");
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

async function browserGet<T>(page: Page, path: string): Promise<T> {
  return page.evaluate(async (target) => {
    const response = await fetch(target);
    const body = await response.json();
    if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(body)}`);
    return body;
  }, path) as Promise<T>;
}

type QueuedSnapshotEvidence = {
  job_id: string;
  snapshot_hash: string;
  supplier_version_id: string;
  internal_status: string;
};

function pythonEvidence(dataRoot: string, script: string, ...args: string[]): QueuedSnapshotEvidence {
  if (!dataRoot) throw new Error("M6D Playwright data root is not configured");
  const output = execFileSync("python3", ["-c", script, dataRoot, ...args], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
  });
  return JSON.parse(output.trim()) as QueuedSnapshotEvidence;
}

function createQueuedSnapshotJob(dataRoot: string, projectId: string, chapterId: string, unique: string) {
  return pythonEvidence(dataRoot, `
import json, sys
from pathlib import Path
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.resolution import ModelResolver
from ai_drama_web.suppliers.snapshots import SnapshotBuilder

root = Path(sys.argv[1])
project_id, chapter_id, unique = sys.argv[2:5]
runtime = RuntimeStore(root / "runtime.db", root / "objects")
store = ProductStore(runtime)
resolved = ModelResolver(store).resolve(project_id, "shot_video_generation")
credential_id = resolved.supplier.current_credential_version_id
snapshot = SnapshotBuilder(store).build(
    resolved,
    credential_resolution_mode="current",
    resolved_credential_version_id=credential_id,
    resolved_constraints={},
    worker_limits={"timeout_seconds": 30, "max_output_bytes": 4194304},
)
job, created = store.enqueue_generation_job_with_snapshot(
    supplier_id=snapshot.supplier_id,
    capability="video",
    provider=f"m6:{snapshot.supplier_id}:video",
    job_type="video",
    project_id=project_id,
    chapter_id=chapter_id,
    shot_id=f"shot-{unique}",
    prompt_revision_id=f"prompt-{unique}",
    idempotency_key=f"queued-{unique}",
    request={"prompt": "offline queued snapshot"},
    snapshot=snapshot,
)
print(json.dumps({
    "job_id": job.job_id,
    "snapshot_hash": job.snapshot_hash,
    "supplier_version_id": snapshot.supplier_version_id,
    "internal_status": job.internal_status,
}))
runtime.close()
`, projectId, chapterId, unique);
}

function readQueuedSnapshotJob(dataRoot: string, jobId: string) {
  return pythonEvidence(dataRoot, `
import json, sys
from pathlib import Path
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.snapshots import load_snapshot

root = Path(sys.argv[1])
job_id = sys.argv[2]
runtime = RuntimeStore(root / "runtime.db", root / "objects")
store = ProductStore(runtime)
job = store.get_generation_job(job_id)
snapshot = load_snapshot(store, job.snapshot_hash)
print(json.dumps({
    "job_id": job.job_id,
    "snapshot_hash": job.snapshot_hash,
    "supplier_version_id": snapshot.supplier_version_id,
    "internal_status": job.internal_status,
}))
runtime.close()
`, jobId);
}
