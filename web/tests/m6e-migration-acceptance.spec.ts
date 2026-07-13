import { expect, type APIRequestContext, type Page, test } from "@playwright/test";
import { execFileSync, spawn, type ChildProcess } from "node:child_process";
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

const TEXT_MODEL_ID = "88888888-8888-4888-8888-888888888888";
const IMAGE_MODEL_ID = "99999999-9999-4999-8999-999999999999";
const VIDEO_MODEL_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

function adapterSource(version: string) {
  return `export const vendor = {
  id: "m6e-browser", version: "${version}", name: "M6E Browser Fake", author: "Playwright",
  adapterContractVersion: "ai-drama-supplier-v1", helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "m6e-browser-local", inputs: [], inputValues: {},
  models: [
    { supplierModelId: "${TEXT_MODEL_ID}", providerModelName: "m6e-text", displayName: "M6E Text", capability: "text" },
    { supplierModelId: "${IMAGE_MODEL_ID}", providerModelName: "m6e-image", displayName: "M6E Image", capability: "image" },
    { supplierModelId: "${VIDEO_MODEL_ID}", providerModelName: "m6e-video", displayName: "M6E Video", capability: "video" }
  ]
};
export async function textRequest() {
  return { output: "# M6E_BROWSER_${version}\\n\\nruntime_model: local-fake\\nsource_basis: browser-e2e\\n\\n## Scene: 1-1\\n\\n【画面】离线验收。\\n\\n【动作】检查结果。\\n\\n【台词】角色：M6E_BROWSER_${version}。", usage: { input_tokens: 0, output_tokens: 0 } };
}
export async function imageRequest() { return { media_type: "image/png", content: "m6e-image-${version}" }; }
export async function videoSubmit() { return { video_id: "m6e-video-${version}" }; }
export async function videoPoll(payload) { return { video_id: payload.request.video_id, status: "completed" }; }
export async function videoFetch() { return { media_type: "video/mp4", content: "m6e-video-content-${version}" }; }`;
}

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("M6E Playwright acceptance runs through npm run test:e2e", () => undefined);
} else {
test("M6E completes offline text image video reruns and keeps restart-visible evidence", async ({
  page,
  request,
}, testInfo) => {
  const consoleErrors: string[] = [];
  const unexpectedNetwork: string[] = [];
  const unexpectedResponses: string[] = [];
  await proxyApi(page, request);
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("request", (browserRequest) => {
    if (!isLoopback(new URL(browserRequest.url()).hostname)) unexpectedNetwork.push(browserRequest.url());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) unexpectedResponses.push(`${response.status()} ${response.url()}`);
  });

  const unique = Date.now().toString(36);
  const supplier = await apiJson<{ supplier_id: string }>(request, "post", "/api/suppliers", {
    data: { slug: `m6e-browser-${unique}`, display_name: `M6E Browser ${unique}` },
    headers: { "If-None-Match": "*", "Idempotency-Key": `m6e-browser-${unique}` },
  });
  await apiJson(request, "put", `/api/suppliers/${supplier.supplier_id}/code`, {
    data: { source: adapterSource("V1") },
    headers: { "If-Match": '"supplier-1"' },
  });
  const secret = `m6e-local-${unique}-secret`;
  await apiJson(request, "put", `/api/suppliers/${supplier.supplier_id}/secret`, {
    data: { credential: secret },
    headers: { "If-Match": '"credential-0"' },
  });
  const modelsResponse = await request.get(`${backendURL}/api/suppliers/${supplier.supplier_id}/models`);
  expect(modelsResponse.ok()).toBeTruthy();
  const models = (await modelsResponse.json()) as Array<{ supplier_model_id: string; capability: string }>;
  const modelId = (capability: string) => models.find((item) => item.capability === capability)!.supplier_model_id;
  const project = await apiJson<{ project_id: string }>(request, "post", "/api/projects", {
    data: {
      name: `M6E Browser ${unique}`,
      description: "offline browser acceptance",
      series_canon: "",
      characters_context: "",
      production_brief: "",
    },
  });
  const chapter = await apiJson<{ chapter_id: string }>(
    request,
    "post",
    `/api/projects/${project.project_id}/chapters`,
    { data: { title: "M6E complete acceptance", position: 1 } },
  );
  await apiJson(request, "post", `/api/chapters/${chapter.chapter_id}/source-revisions`, {
    data: { content: "本地 fake provider 浏览器验收，不访问真实供应商。" },
  });
  await apiJson(request, "put", `/api/projects/${project.project_id}/model-bindings`, {
    data: {
      defaults: { text: modelId("text"), image: modelId("image"), video: modelId("video") },
      operation_overrides: { script_adaptation: modelId("text") },
    },
    headers: { "If-Match": '"binding-set-0"' },
  });

  await page.goto(`/projects/${project.project_id}/chapters/${chapter.chapter_id}`);
  const script = await browserPost<{ content: string }>(
    page,
    `/api/chapters/${chapter.chapter_id}/script/generate`,
    {},
  );
  expect(script.content).toContain("M6E_BROWSER_V1");
  const image = await browserPost<{ source_job_id: string; object_id: string }>(
    page,
    `/api/chapters/${chapter.chapter_id}/assets/generate-image`,
    {
      asset_type: "shot_keyframe",
      name: "M6E browser frame",
      prompt: "offline image",
      size: "1024x768",
      idempotency_key: `m6e-image-${unique}`,
    },
  );
  expect(image.source_job_id).not.toBe("");
  expect(image.object_id).not.toBe("");

  const dataRoot = String(testInfo.config.metadata.m6dDataRoot);
  const first = videoFixture(dataRoot, "create", project.project_id, chapter.chapter_id, unique);
  await apiJson(request, "put", `/api/suppliers/${supplier.supplier_id}/code`, {
    data: { source: adapterSource("V2") },
    headers: { "If-Match": '"supplier-2"' },
  });
  const reruns = videoFixture(dataRoot, "rerun", first.source_job_id, first.old_queued_job_id, unique);
  expect(reruns.inherited_supplier_version_id).toBe(first.v1_supplier_version_id);
  expect(reruns.current_supplier_version_id).not.toBe(first.v1_supplier_version_id);
  expect(reruns.old_queued_snapshot_hash).toBe(first.old_queued_snapshot_hash);
  expect(reruns.submit_count).toBe(2);

  await page.reload();
  await page.getByRole("tab", { name: /结果与重跑/ }).click();
  await expect(page.getByText("local_result_available").first()).toBeVisible();
  await expect(page.getByLabel("Local artifact preview").first()).toBeVisible();

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1180, height: 820 },
    { width: 768, height: 1024 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto(`/suppliers/${supplier.supplier_id}`);
    await expect(page.getByRole("heading", { name: `M6E Browser ${unique}` })).toBeVisible();
    await page.getByRole("tab", { name: "模型" }).focus();
    await page.getByRole("tab", { name: "模型" }).press("ArrowLeft");
    await expect(page.getByRole("tab", { name: "适配代码" })).toHaveAttribute("aria-selected", "true");
  }

  const browserState = await page.evaluate(() => ({
    body: document.body.innerText,
    local: JSON.stringify(localStorage),
    session: JSON.stringify(sessionStorage),
  }));
  expect(JSON.stringify(browserState)).not.toContain(secret);
  const supplierReadback = await request.get(`${backendURL}/api/suppliers/${supplier.supplier_id}`);
  expect(await supplierReadback.text()).not.toContain(secret);
  const publicPage = await page.context().newPage();
  const publicResponse = await publicPage.goto(
    `${String(testInfo.config.metadata.m6ePublicBackendURL)}/api/suppliers`,
  );
  expect(publicResponse?.status()).toBe(403);
  await expect(publicPage.locator("body")).toContainText("LOCAL_MANAGEMENT_ONLY");
  await publicPage.close();
  expect(consoleErrors).toEqual([]);
  expect(unexpectedNetwork).toEqual([]);
  expect(unexpectedResponses).toEqual([]);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("M6E restarts the local app and resumes frozen snapshot evidence", async ({ page, request }, testInfo) => {
  const port = 18768;
  const restartURL = `http://127.0.0.1:${port}`;
  const dataRoot = testInfo.outputPath("restart-runtime");
  let server = startRestartServer(dataRoot, port);
  try {
    await waitForHealth(request, restartURL);
    const unique = `restart-${Date.now().toString(36)}`;
    const supplier = await apiJson<{ supplier_id: string }>(request, "post", "/api/suppliers", {
      data: { slug: unique, display_name: "M6E Restart Fake" },
      headers: { "If-None-Match": "*", "Idempotency-Key": unique },
    }, restartURL);
    await apiJson(request, "put", `/api/suppliers/${supplier.supplier_id}/code`, {
      data: { source: adapterSource("RESTART") }, headers: { "If-Match": '"supplier-1"' },
    }, restartURL);
    await apiJson(request, "put", `/api/suppliers/${supplier.supplier_id}/secret`, {
      data: { credential: "restart-local-only" }, headers: { "If-Match": '"credential-0"' },
    }, restartURL);
    const modelsResponse = await request.get(`${restartURL}/api/suppliers/${supplier.supplier_id}/models`);
    const models = (await modelsResponse.json()) as Array<{ supplier_model_id: string; capability: string }>;
    const modelId = (capability: string) => models.find((item) => item.capability === capability)!.supplier_model_id;
    const project = await apiJson<{ project_id: string }>(request, "post", "/api/projects", {
      data: { name: "M6E Restart", description: "offline", series_canon: "", characters_context: "", production_brief: "" },
    }, restartURL);
    const chapter = await apiJson<{ chapter_id: string }>(request, "post", `/api/projects/${project.project_id}/chapters`, {
      data: { title: "Restart", position: 1 },
    }, restartURL);
    await apiJson(request, "post", `/api/chapters/${chapter.chapter_id}/source-revisions`, {
      data: { content: "本地重启恢复验收。" },
    }, restartURL);
    await apiJson(request, "put", `/api/projects/${project.project_id}/model-bindings`, {
      data: {
        defaults: { text: modelId("text"), image: modelId("image"), video: modelId("video") },
        operation_overrides: { script_adaptation: modelId("text") },
      },
      headers: { "If-Match": '"binding-set-0"' },
    }, restartURL);
    await proxyApi(page, request, restartURL);
    await page.goto(`/projects/${project.project_id}/chapters/${chapter.chapter_id}`);
    const script = await browserPost<{ content: string }>(page, `/api/chapters/${chapter.chapter_id}/script/generate`, {});
    expect(script.content).toContain("M6E_BROWSER_RESTART");
    const jobs = videoFixture(dataRoot, "create", project.project_id, chapter.chapter_id, unique);
    await page.unrouteAll({ behavior: "ignoreErrors" });

    await stopRestartServer(server);
    server = startRestartServer(dataRoot, port);
    await waitForHealth(request, restartURL);
    await proxyApi(page, request, restartURL);
    const resumed = await browserGet<{ internal_status: string; provider_job_id: string }>(
      page, `/api/generation/jobs/${jobs.old_queued_job_id}`,
    );
    expect(resumed.internal_status).toBe("submitted");
    expect(resumed.provider_job_id).toBe("m6e-video-RESTART");
    const completed = await browserPost<{ internal_status: string }>(
      page, `/api/generation/jobs/${jobs.old_queued_job_id}/refresh`, {},
    );
    expect(completed.internal_status).toBe("completed");
    await page.goto(`/projects/${project.project_id}/chapters/${chapter.chapter_id}`);
    await page.getByRole("tab", { name: /结果与重跑/ }).click();
    await expect(page.getByText("local_result_available").first()).toBeVisible();
    await page.reload();
    await expect(page.getByRole("tab", { name: /结果与重跑/ })).toBeVisible();
    await page.unrouteAll({ behavior: "ignoreErrors" });
  } finally {
    await stopRestartServer(server);
  }
});
}

type VideoEvidence = {
  source_job_id: string;
  old_queued_job_id: string;
  v1_supplier_version_id: string;
  old_queued_snapshot_hash: string;
  inherited_supplier_version_id: string;
  current_supplier_version_id: string;
  submit_count: number;
};

function videoFixture(dataRoot: string, action: "create" | "rerun", ...args: string[]): VideoEvidence {
  const script = String.raw`
import json, sys
from pathlib import Path
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import SupplierCredentialStore
from ai_drama_web.suppliers.execution import SnapshotExecutionGateway
from ai_drama_web.suppliers.snapshots import load_snapshot
from ai_drama_web.services.m6_generation import M6GenerationCoordinator
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.providers.fake import FakeGenerationBackend

root = Path(sys.argv[1]); action = sys.argv[2]
runtime = RuntimeStore(root / "runtime.db", root / "objects")
store = ProductStore(runtime)
credentials = SupplierCredentialStore(store, root)
gateway = SnapshotExecutionGateway(store, credentials)
coordinator = M6GenerationCoordinator(store, runtime, credentials, gateway)

def complete(job):
    service = GenerationExecutionService(store, runtime, FakeGenerationBackend(), supplier_gateway=gateway, supplier_execution_enabled=True)
    service.submit_queued_job(job.job_id)
    return service.refresh_job(job.job_id)

if action == "create":
    project_id, chapter_id, unique = sys.argv[3:6]
    source, _ = coordinator.enqueue_video(project_id=project_id, chapter_id=chapter_id, shot_id=f"shot-{unique}", prompt_revision_id=f"prompt-{unique}", idempotency_key=f"source-{unique}", request={"prompt":"offline","asset_ids":[],"parameters":{}})
    old, _ = coordinator.enqueue_video(project_id=project_id, chapter_id=chapter_id, shot_id=f"old-{unique}", prompt_revision_id=f"old-prompt-{unique}", idempotency_key=f"old-{unique}", request={"prompt":"old queued","asset_ids":[],"parameters":{}})
    complete(source)
    source_snapshot = load_snapshot(store, source.snapshot_hash)
    print(json.dumps({"source_job_id":source.job_id,"old_queued_job_id":old.job_id,"v1_supplier_version_id":source_snapshot.supplier_version_id,"old_queued_snapshot_hash":old.snapshot_hash,"inherited_supplier_version_id":"","current_supplier_version_id":"","submit_count":1}))
else:
    source_id, old_id, unique = sys.argv[3:6]
    source = store.get_generation_job(source_id); old = store.get_generation_job(old_id)
    inherited, _ = coordinator.rerun_video(source_job=source,idempotency_key=f"inherit-{unique}",request={"prompt":"inherit","asset_ids":[],"parameters":{}},use_current_project_model=False)
    current, _ = coordinator.rerun_video(source_job=source,idempotency_key=f"current-{unique}",request={"prompt":"current","asset_ids":[],"parameters":{}},use_current_project_model=True)
    complete(inherited); complete(current)
    print(json.dumps({"source_job_id":source.job_id,"old_queued_job_id":old.job_id,"v1_supplier_version_id":"","old_queued_snapshot_hash":old.snapshot_hash,"inherited_supplier_version_id":load_snapshot(store,inherited.snapshot_hash).supplier_version_id,"current_supplier_version_id":load_snapshot(store,current.snapshot_hash).supplier_version_id,"submit_count":2}))
runtime.close()
`;
  const output = execFileSync("python3", ["-c", script, dataRoot, action, ...args], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
  });
  return JSON.parse(output.trim()) as VideoEvidence;
}

async function proxyApi(page: Page, request: APIRequestContext, targetBackendURL = backendURL) {
  await page.route(`${frontendURL}/api/**`, async (route) => {
    const browserRequest = route.request();
    const url = new URL(browserRequest.url());
    const response = await request.fetch(`${targetBackendURL}${url.pathname}${url.search}`, {
      data: browserRequest.postDataBuffer() ?? undefined,
      headers: browserRequest.headers(),
      method: browserRequest.method(),
    });
    await route.fulfill({ response });
  });
}

async function apiJson<T>(
  request: APIRequestContext,
  method: "post" | "put",
  path: string,
  options: object,
  targetBackendURL = backendURL,
) {
  const response = await request[method](`${targetBackendURL}${path}`, options);
  expect(response.ok(), `${response.status()} ${await response.text()}`).toBeTruthy();
  return response.json() as Promise<T>;
}

async function browserGet<T>(page: Page, path: string): Promise<T> {
  return page.evaluate(async (target) => {
    const response = await fetch(target);
    const value = await response.json();
    if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(value)}`);
    return value;
  }, path) as Promise<T>;
}

function startRestartServer(dataRoot: string, port: number) {
  return spawn(
    "python3",
    ["-m", "uvicorn", "ai_drama_web.app:create_app", "--factory", "--host", "127.0.0.1", "--port", String(port)],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        AI_DRAMA_DATA_ROOT: dataRoot,
        AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED: "true",
        AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS: "3600",
        PYTHONDONTWRITEBYTECODE: "1",
      },
      stdio: "ignore",
    },
  );
}

async function waitForHealth(request: APIRequestContext, url: string) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      if ((await request.get(`${url}/api/health`)).ok()) return;
    } catch {
      // The child process may still be binding its loopback socket.
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 100));
  }
  throw new Error(`restart server did not become healthy: ${url}`);
}

async function stopRestartServer(child: ChildProcess) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  await Promise.race([
    new Promise<void>((resolvePromise) => child.once("exit", () => resolvePromise())),
    new Promise<void>((resolvePromise) => setTimeout(resolvePromise, 3000)),
  ]);
  if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
}

async function browserPost<T>(page: Page, path: string, body: object): Promise<T> {
  return page.evaluate(async ({ target, payload }) => {
    const response = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: Object.keys(payload).length ? JSON.stringify(payload) : undefined,
    });
    const value = await response.json();
    if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(value)}`);
    return value;
  }, { target: path, payload: body }) as Promise<T>;
}

function isLoopback(hostname: string) {
  return ["127.0.0.1", "localhost", "::1"].includes(hostname);
}
