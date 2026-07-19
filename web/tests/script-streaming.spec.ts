import { expect, test } from "./network-test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const runningInVitest = Boolean(process.env.VITEST);
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("streaming script Playwright acceptance runs through npm run test:e2e", () => undefined);
} else {
  test("shows streamed script text in the central editor", async ({ page }) => {
    const qaDirectory = process.env.AI_DRAMA_QA_SCREENSHOT_DIR ?? "";
    let delayFirstStream = Boolean(qaDirectory);
    let revisionAvailable = false;
    let generationStartCount = 0;
    let streamMode: "streaming" | "failed" | "completed" = "streaming";
    const chapter = {
      chapter_id: "chapter-stream-1",
      project_id: "project-stream-1",
      title: "第一章",
      position: 1,
      current_source_revision_id: "source-stream-1",
      created_at: "2026-07-19T00:00:00Z",
      updated_at: "2026-07-19T00:00:00Z",
      source_text: "沈清荷重新翻开账册，决定追查旧案。".repeat(40),
    };

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
      if (path === "/api/chapters/chapter-stream-1/status") {
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
          content: "# 第一场\n\n沈清荷推门入内。",
          validation_results: [{
            validation_id: "validation-stream-1",
            validator_id: "script_markdown_contract",
            status: "PASS",
            required: true,
            error_code: "",
          }],
        }] : []);
      }
      if (path === "/api/chapters/chapter-stream-1/generation/jobs") return json([]);
      if (path === "/api/projects/project-stream-1/chapters") return json([chapter]);
      if (path === "/api/projects/project-stream-1/model-resolution/script_adaptation") {
        return json({
          project_id: "project-stream-1",
          operation_key: "script_adaptation",
          capability: "text",
          binding_source: "operation_override",
          supplier_id: "supplier-stream-1",
          supplier_model_id: "model-stream-1",
          model_revision_id: "model-stream-r1",
          provider_model_name: "fake-stream-text",
        });
      }
      if (path === "/api/projects/project-stream-1/model-bindings") {
        return json({
          project_id: "project-stream-1",
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
              'id: 1\nevent: text_delta\ndata: {"sequence":1,"text":"# 第一场\\n\\n未完成内容"}\n\n',
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
              'id: 1\nevent: text_delta\ndata: {"sequence":1,"text":"# 第一场\\n\\n沈清荷推门入内。"}\n\n',
              'id: 2\nevent: revision_completed\ndata: {"sequence":2,"revision_id":"script-stream-final-1"}\n\n',
            ].join(""),
            contentType: "text/event-stream",
            status: 200,
          });
        }
        return route.fulfill({
          body: [
            'id: 1\nevent: text_delta\ndata: {"sequence":1,"text":"# 第一场\\n\\n"}\n\n',
            'id: 2\nevent: text_delta\ndata: {"sequence":2,"text":"沈清荷推门入内。"}\n\n',
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
    await page.getByRole("button", { name: "保存并生成剧本" }).click();

    await expect(page.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
    if (qaDirectory) await captureQaState(page, qaDirectory, "starting");
    await expect(page.getByLabel("实时剧本内容")).toHaveValue("# 第一场\n\n沈清荷推门入内。");
    await expect(page.getByText("实时草稿")).toBeVisible();
    await expect(page.getByText(/正在生成|正在重新连接/)).toBeVisible();
    await page.reload();
    await expect(page.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByLabel("实时剧本内容")).toHaveValue("# 第一场\n\n沈清荷推门入内。");
    expect(generationStartCount).toBe(1);
    if (qaDirectory) {
      await captureQaState(page, qaDirectory, "streaming");
      await expect(page.getByText("正在重新连接")).toBeVisible();
      await captureQaState(page, qaDirectory, "reconnecting");

      streamMode = "failed";
      revisionAvailable = false;
      await page.reload();
      await expect(page.getByText("生成中断 · 该内容尚未保存为正式剧本版本")).toBeVisible();
      await captureQaState(page, qaDirectory, "failed");

      streamMode = "completed";
      revisionAvailable = false;
      await page.reload();
      await expect(page.getByLabel("剧本内容")).toHaveValue("# 第一场\n\n沈清荷推门入内。");
      await captureQaState(page, qaDirectory, "completed");
      expect(generationStartCount).toBe(1);
    }
  });
}

async function captureQaState(
  page: import("@playwright/test").Page,
  directory: string,
  state: string,
) {
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
}
