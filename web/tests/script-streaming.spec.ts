import { expect, test } from "./network-test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const runningInVitest = Boolean(process.env.VITEST);
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("streaming script Playwright acceptance runs through npm run test:e2e", () => undefined);
} else {
  test("shows streamed script text in the central editor", async ({ page }, testInfo) => {
    const qaDirectory = process.env.AI_DRAMA_QA_SCREENSHOT_DIR
      ?? testInfo.outputPath("workspace-qa");
    let delayFirstStream = true;
    let revisionAvailable = false;
    let generationStartCount = 0;
    let streamMode: "streaming" | "failed" | "completed" = "streaming";
    const longSource = "沈清荷重新翻开账册，决定追查旧案。夜雨敲窗，她逐页核对被涂改的数字。".repeat(140);
    const longScript = `# 第一场\n\n${"沈清荷推门入内，沿着灯影逐页核对账册。\n\n".repeat(180)}`;
    const partialScript = `# 第一场\n\n${"未完成内容仍然保留在实时草稿中。\n\n".repeat(120)}`;
    const chapter = {
      chapter_id: "chapter-stream-1",
      project_id: "project-stream-1",
      title: "第一章",
      position: 1,
      current_source_revision_id: "source-stream-1",
      created_at: "2026-07-19T00:00:00Z",
      updated_at: "2026-07-19T00:00:00Z",
      source_text: longSource,
    };
    const secondChapter = {
      ...chapter,
      chapter_id: "chapter-stream-2",
      project_id: "project-stream-2",
      title: "第二项目第一章",
      current_source_revision_id: "source-stream-2",
    };
    const projectOneChapters = [
      chapter,
      ...Array.from({ length: 18 }, (_, index) => ({
        ...chapter,
        chapter_id: `chapter-stream-nav-${index + 2}`,
        title: `章节导航长列表 ${index + 2}`,
        position: index + 2,
      })),
    ];

    await page.route(`http://127.0.0.1:${frontendPort}/api/**`, async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      const json = (body: unknown, headers: Record<string, string> = {}) =>
        route.fulfill({
          body: JSON.stringify(body),
          contentType: "application/json",
          headers,
          status: 200,
        });

      if (path === "/api/chapters/chapter-stream-1") return json(chapter);
      if (path === "/api/chapters/chapter-stream-2") return json(secondChapter);
      if (path === "/api/chapters/chapter-stream-1/status" || path === "/api/chapters/chapter-stream-2/status") {
        return json({ status: "source_ready", blocking_reason: "未确认剧本", next_action: "generate_script" });
      }
      if (path === "/api/chapters/chapter-stream-1/script/revisions") {
        return json(revisionAvailable ? [{
          revision_id: "script-stream-final-1",
          artifact_id: "chapter-stream-1:script",
          chapter_id: "chapter-stream-1",
          number: 1,
          approval_status: "pending",
          current: false,
          content: longScript,
          validation_results: Array.from({ length: 24 }, (_, index) => ({
            validation_id: `validation-stream-${index + 1}`,
            validator_id: `script_contract_${index + 1}`,
            status: "PASS",
            required: true,
            error_code: "",
          })),
        }] : []);
      }
      if (path === "/api/chapters/chapter-stream-2/script/revisions") return json([]);
      if (path === "/api/chapters/chapter-stream-1/generation/jobs" || path === "/api/chapters/chapter-stream-2/generation/jobs") return json([]);
      if (path === "/api/projects/project-stream-1/chapters") return json(projectOneChapters);
      if (path === "/api/projects/project-stream-2/chapters") return json([secondChapter]);
      if (path === "/api/projects/project-stream-1/model-resolution/script_adaptation" || path === "/api/projects/project-stream-2/model-resolution/script_adaptation") {
        return json({
          project_id: path.includes("project-stream-2") ? "project-stream-2" : "project-stream-1",
          operation_key: "script_adaptation",
          capability: "text",
          binding_source: "operation_override",
          supplier_id: "supplier-stream-1",
          supplier_model_id: "model-stream-1",
          model_revision_id: "model-stream-r1",
          provider_model_name: "fake-stream-text",
        });
      }
      if (path === "/api/projects/project-stream-1/model-bindings" || path === "/api/projects/project-stream-2/model-bindings") {
        return json({
          project_id: path.includes("project-stream-2") ? "project-stream-2" : "project-stream-1",
          defaults: { text: "model-stream-1", image: "", video: "" },
          operation_overrides: { script_adaptation: "model-stream-1" },
          binding_set_revision: 1,
        }, { etag: '"binding-set-1"' });
      }
      if (path === "/api/suppliers") {
        return json([{ supplier_id: "supplier-stream-1", display_name: "本地假供应商", enabled: 1 }]);
      }
      if (path === "/api/suppliers/supplier-stream-1/models") {
        return json([{
          supplier_model_id: "model-stream-1",
          supplier_id: "supplier-stream-1",
          display_name: "Fake Stream Text",
          provider_model_name: "fake-stream-text",
          capability: "text",
          enabled: 1,
        }], { etag: '"model-catalog-1"' });
      }
      if (path === "/api/chapters/chapter-stream-1/script/generations" && request.method() === "POST") {
        generationStartCount += 1;
        return route.fulfill({
          body: JSON.stringify({
            run_id: "stream-run-browser-1",
            status: "prepared",
            last_sequence: 0,
            character_count: 0,
            revision_id: "",
            error_code: "",
          }),
          contentType: "application/json",
          status: 202,
        });
      }
      if (path === "/api/script-generation-runs/stream-run-browser-1/events") {
        if (delayFirstStream) {
          delayFirstStream = false;
          await new Promise((resolve) => setTimeout(resolve, 1500));
        }
        if (streamMode === "failed") {
          return route.fulfill({
            body: [
              `id: 1\nevent: text_delta\ndata: ${JSON.stringify({ sequence: 1, text: partialScript })}\n\n`,
              'id: 2\nevent: failed\ndata: {"sequence":2,"error_code":"FAKE_STREAM_INTERRUPTED"}\n\n',
            ].join(""),
            contentType: "text/event-stream",
            status: 200,
          });
        }
        if (streamMode === "completed") {
          revisionAvailable = true;
          return route.fulfill({
            body: [
              `id: 1\nevent: text_delta\ndata: ${JSON.stringify({ sequence: 1, text: longScript })}\n\n`,
              'id: 2\nevent: revision_completed\ndata: {"sequence":2,"revision_id":"script-stream-final-1"}\n\n',
            ].join(""),
            contentType: "text/event-stream",
            status: 200,
          });
        }
        return route.fulfill({
          body: [
            `id: 1\nevent: text_delta\ndata: ${JSON.stringify({ sequence: 1, text: longScript.slice(0, Math.floor(longScript.length / 2)) })}\n\n`,
            `id: 2\nevent: text_delta\ndata: ${JSON.stringify({ sequence: 2, text: longScript.slice(Math.floor(longScript.length / 2)) })}\n\n`,
          ].join(""),
          contentType: "text/event-stream",
          headers: { "Cache-Control": "no-store" },
          status: 200,
        });
      }
      if (path === "/api/script-generation-runs/stream-run-browser-1") {
        return json({
          run_id: "stream-run-browser-1",
          status: streamMode === "failed" ? "failed" : "streaming",
          last_sequence: 2,
          character_count: 14,
          revision_id: "",
          error_code: streamMode === "failed" ? "FAKE_STREAM_INTERRUPTED" : "",
        });
      }
      throw new Error(`unexpected browser API request: ${request.method()} ${path}`);
    });

    await page.goto("/projects/project-stream-1/chapters/chapter-stream-1");
    await expect(page.getByLabel("文本模型")).toHaveValue("model-stream-1");
    await verifyDesktopViewports(page, "source");

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.getByRole("tab", { name: "剧本" }).click();
    await page.getByRole("tab", { name: "原文" }).click();
    await dragLeftDividerToRatio(page, 15);
    await expectActiveLeftRatio(page, 15);
    await page.getByRole("tab", { name: "剧本" }).click();
    await expectActiveLeftRatio(page, 15);
    await page.getByRole("tab", { name: "原文" }).click();
    await page.reload();
    await expectActiveLeftRatio(page, 15);

    await page.goto("/projects/project-stream-2/chapters/chapter-stream-2");
    await expect(page.getByLabel("文本模型")).toHaveValue("model-stream-1");
    await expectActiveLeftRatio(page, 15);
    await page.goto("/projects/project-stream-1/chapters/chapter-stream-1");
    await page.getByRole("separator", { name: "调整章节导航宽度" }).dblclick();
    await expectActiveLeftRatio(page, 11);

    await page.setViewportSize({ width: 1024, height: 800 });
    await page.getByRole("separator", { name: "调整章节导航宽度" }).press("Home");
    await page.getByRole("separator", { name: "调整详情栏宽度" }).press("Home");
    await expectSourceControlsContained(page);
    await page.getByLabel("目标时长").selectOption("4");
    await expect(page.getByLabel("目标时长")).toHaveValue("4");
    await page.getByRole("separator", { name: "调整章节导航宽度" }).press("End");
    await page.getByRole("separator", { name: "调整详情栏宽度" }).press("End");
    await expectWorkspaceInsideViewport(page, "source at constrained 1024x800");

    await page.setViewportSize({ width: 768, height: 1024 });
    await expectCompactWorkspace(page, "原文转剧本");

    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.getByRole("button", { name: "保存并生成剧本" }).click();

    await expect(page.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
    await captureQaState(page, qaDirectory, "starting");
    await expect(page.getByLabel("实时剧本内容")).toHaveValue(longScript);
    await expect(page.getByText("实时草稿")).toBeVisible();
    await expect(page.locator("span[aria-live='polite']")).toHaveText(/正在生成|正在重新连接/);
    await verifyDesktopViewports(page, "streaming");
    await page.setViewportSize({ width: 768, height: 1024 });
    await expectCompactWorkspace(page, "剧本详情");
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.reload();
    await expect(page.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByLabel("实时剧本内容")).toHaveValue(longScript);
    expect(generationStartCount).toBe(1);
    await captureQaState(page, qaDirectory, "streaming");

    streamMode = "failed";
    revisionAvailable = false;
    await page.reload();
    await expect(page.getByLabel("实时剧本内容")).toHaveValue(partialScript);
    await expect(page.getByText("生成中断 · 该内容尚未保存为正式剧本版本")).toBeVisible();
    await verifyDesktopViewports(page, "failed");
    await page.setViewportSize({ width: 768, height: 1024 });
    await expectCompactWorkspace(page, "剧本详情");
    await page.setViewportSize({ width: 1920, height: 1080 });
    await captureQaState(page, qaDirectory, "failed");

    streamMode = "completed";
    revisionAvailable = false;
    await page.reload();
    await expect(page.getByLabel("剧本内容")).toHaveValue(longScript);
    await verifyDesktopViewports(page, "completed");
    await page.setViewportSize({ width: 768, height: 1024 });
    await expectCompactWorkspace(page, "剧本详情");
    await captureQaState(page, qaDirectory, "completed");
    expect(generationStartCount).toBe(1);
  });
}

const desktopViewports = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1180, height: 800 },
];

async function activeWorkspace(page: import("@playwright/test").Page) {
  return page.locator(".ant-tabs-tabpane-active [data-testid='resizable-chapter-workspace']");
}

async function verifyDesktopViewports(page: import("@playwright/test").Page, state: string) {
  const requiredPanes = ["left", "center"];
  let rightPaneScrolled = false;
  for (const viewport of desktopViewports) {
    await page.setViewportSize(viewport);
    await expectWorkspaceInsideViewport(page, `${state} at ${viewport.width}x${viewport.height}`);
    await expectPaneScrollingDoesNotMoveDocument(
      page,
      `${state} at ${viewport.width}x${viewport.height}`,
      requiredPanes,
    );
    rightPaneScrolled = await expectRightPaneScrollContract(
      page,
      `${state} at ${viewport.width}x${viewport.height}`,
      state,
    ) || rightPaneScrolled;
  }
  if (state === "source" || state === "completed") {
    expect(rightPaneScrolled, `${state} right pane must be wheel-scrollable when its fixture overflows`).toBe(true);
  }
}

async function expectWorkspaceInsideViewport(page: import("@playwright/test").Page, context: string) {
  const metrics = await page.evaluate(() => {
    const workspace = document.querySelector<HTMLElement>(
      ".ant-tabs-tabpane-active [data-testid='resizable-chapter-workspace']",
    );
    const center = workspace?.querySelector<HTMLElement>("[data-workspace-pane='center']");
    if (!workspace || !center) throw new Error("active workspace is missing");
    const workspaceRect = workspace.getBoundingClientRect();
    const centerRect = center.getBoundingClientRect();
    return {
      bodyOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      bodyOverflowY: document.documentElement.scrollHeight - document.documentElement.clientHeight,
      bottom: workspaceRect.bottom,
      centerRatio: centerRect.width / workspaceRect.width,
      viewportHeight: window.innerHeight,
    };
  });
  expect(metrics.bodyOverflowX, `${context} horizontal document overflow`).toBeLessThanOrEqual(1);
  expect(metrics.bodyOverflowY, `${context} vertical document overflow`).toBeLessThanOrEqual(1);
  expect(metrics.bottom, `${context} workspace bottom`).toBeLessThanOrEqual(metrics.viewportHeight + 1);
  // Grid tracks round to device pixels; allow at most one tenth of one percentage point.
  expect(metrics.centerRatio, `${context} center ratio`).toBeGreaterThanOrEqual(0.549);
}

async function expectPaneScrollingDoesNotMoveDocument(
  page: import("@playwright/test").Page,
  context: string,
  requiredPanes: string[],
) {
  await page.evaluate(() => window.scrollTo(0, 0));
  const workspace = await activeWorkspace(page);
  const selectors: Record<string, string[]> = {
    left: [".source-chapter-list"],
    center: [".source-manuscript-textarea", ".script-live-editor textarea", ".script-editor-workspace textarea"],
    right: [".source-inspector-scroll", ".script-inspector-scroll"],
  };
  for (const paneName of requiredPanes) {
    let target: import("@playwright/test").Locator | undefined;
    const diagnostics: Array<Record<string, unknown>> = [];
    for (const selector of selectors[paneName]) {
      const candidate = workspace.locator(selector).first();
      if (await candidate.count() === 0) continue;
      const metrics = await candidate.evaluate((element) => {
        const node = element as HTMLElement;
        const overflowY = getComputedStyle(node).overflowY;
        return {
          clientHeight: node.clientHeight,
          overflowY,
          scrollHeight: node.scrollHeight,
        };
      });
      diagnostics.push({ selector, ...metrics });
      if (["auto", "scroll"].includes(metrics.overflowY)
        && metrics.scrollHeight > metrics.clientHeight + 1) {
        target = candidate;
        break;
      }
    }
    expect(target, `${context} ${paneName} real scroll target ${JSON.stringify(diagnostics)}`).toBeDefined();
    await target!.evaluate((element) => { (element as HTMLElement).scrollTop = 0; });
    await target!.hover();
    await page.mouse.wheel(0, 180);
    await expect.poll(
      () => target!.evaluate((element) => (element as HTMLElement).scrollTop),
      { message: `${context} ${paneName} wheel scrolling` },
    ).toBeGreaterThan(0);
  }
  expect(await page.evaluate(() => window.scrollY), `${context} document scroll`).toBe(0);
}

async function expectRightPaneScrollContract(
  page: import("@playwright/test").Page,
  context: string,
  state: string,
) {
  const workspace = await activeWorkspace(page);
  const target = workspace.locator(state === "source" ? ".source-inspector-scroll" : ".script-inspector-scroll");
  await expect(target, `${context} right scroll region`).toHaveCSS("overflow-y", "auto");
  const overflows = await target.evaluate((element) => {
    const node = element as HTMLElement;
    return node.scrollHeight > node.clientHeight + 1;
  });
  if (!overflows) return false;
  await target.evaluate((element) => { (element as HTMLElement).scrollTop = 0; });
  await target.hover();
  await page.mouse.wheel(0, 180);
  await expect.poll(
    () => target.evaluate((element) => (element as HTMLElement).scrollTop),
    { message: `${context} right pane wheel scrolling` },
  ).toBeGreaterThan(0);
  expect(await page.evaluate(() => window.scrollY), `${context} document scroll`).toBe(0);
  return true;
}

async function expectSourceControlsContained(page: import("@playwright/test").Page) {
  const result = await page.evaluate(() => {
    const workspace = document.querySelector<HTMLElement>(
      ".ant-tabs-tabpane-active [data-testid='resizable-chapter-workspace']",
    );
    const rightPane = workspace?.querySelector<HTMLElement>("[data-workspace-pane='right']");
    if (!rightPane) throw new Error("right workspace pane is missing");
    const paneRect = rightPane.getBoundingClientRect();
    const controls = Array.from(rightPane.querySelectorAll<HTMLElement>(
      ".source-model-select, .source-duration-control select, .source-inspector-actions button",
    ));
    return {
      controls: controls.map((control) => {
        const rect = control.getBoundingClientRect();
        return {
          label: control.getAttribute("aria-label") || control.textContent?.trim() || control.className,
          left: rect.left,
          right: rect.right,
          width: rect.width,
        };
      }),
      paneLeft: paneRect.left,
      paneRight: paneRect.right,
    };
  });
  expect(result.controls).toHaveLength(4);
  for (const control of result.controls) {
    expect(control.width, `${control.label} width`).toBeGreaterThan(0);
    expect(control.left, `${control.label} left edge`).toBeGreaterThanOrEqual(result.paneLeft - 1);
    expect(control.right, `${control.label} right edge`).toBeLessThanOrEqual(result.paneRight + 1);
  }
}

async function dragLeftDividerToRatio(page: import("@playwright/test").Page, targetRatio: number) {
  const workspace = await activeWorkspace(page);
  const divider = workspace.getByRole("separator", { name: "调整章节导航宽度" });
  const workspaceBox = await workspace.boundingBox();
  const dividerBox = await divider.boundingBox();
  if (!workspaceBox || !dividerBox) throw new Error("workspace geometry is unavailable");
  const currentRatio = await workspace.evaluate((element) =>
    Number.parseFloat((element as HTMLElement).style.getPropertyValue("--workspace-left")),
  );
  await page.mouse.move(dividerBox.x + dividerBox.width / 2, dividerBox.y + dividerBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    dividerBox.x + dividerBox.width / 2 + workspaceBox.width * ((targetRatio - currentRatio) / 100),
    dividerBox.y + dividerBox.height / 2,
  );
  await page.mouse.up();
}

async function expectActiveLeftRatio(page: import("@playwright/test").Page, expectedRatio: number) {
  const workspace = await activeWorkspace(page);
  await expect.poll(async () => workspace.evaluate((element) =>
    Number.parseFloat((element as HTMLElement).style.getPropertyValue("--workspace-left")),
  )).toBeCloseTo(expectedRatio, 1);
}

async function expectCompactWorkspace(page: import("@playwright/test").Page, rightDrawerTitle: string) {
  const workspace = await activeWorkspace(page);
  await expect(workspace.getByRole("separator")).toHaveCount(0);
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
  const leftTrigger = workspace.getByRole("button", { name: "打开章节导航" });
  const rightTrigger = workspace.getByRole("button", { name: `打开${rightDrawerTitle}` });
  await leftTrigger.click();
  await expect(page.getByRole("dialog", { name: "章节导航" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "章节导航" })).toBeHidden();
  await expect(leftTrigger).toBeFocused();
  await rightTrigger.click();
  await expect(page.getByRole("dialog", { name: rightDrawerTitle })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(rightTrigger).toBeFocused();
}

async function captureQaState(
  page: import("@playwright/test").Page,
  directory: string,
  state: string,
) {
  const originalViewport = page.viewportSize();
  mkdirSync(directory, { recursive: true });
  for (const viewport of [
    { width: 1440, height: 1024 },
    { width: 1180, height: 800 },
    { width: 768, height: 1024 },
  ]) {
    await page.setViewportSize(viewport);
    const horizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(horizontalOverflow, `${state} must not overflow at ${viewport.width}px`).toBe(false);
    await page.screenshot({
      fullPage: true,
      path: join(directory, `${state}-${viewport.width}x${viewport.height}.png`),
    });
  }
  if (originalViewport) await page.setViewportSize(originalViewport);
}
