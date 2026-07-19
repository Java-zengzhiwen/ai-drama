import { expect, test } from "./network-test";

const runningInVitest = Boolean(process.env.VITEST);
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";

if (runningInVitest) {
  const { test: vitestTest } = await import("vitest");
  vitestTest.skip("streaming script Playwright acceptance runs through npm run test:e2e", () => undefined);
} else {
  test("shows streamed script text in the central editor", async ({ page }) => {
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
      if (path === "/api/chapters/chapter-stream-1/script/revisions") return json([]);
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
          status: "streaming",
          last_sequence: 2,
          character_count: 14,
          revision_id: "",
          error_code: "",
        });
      }
      throw new Error(`unexpected browser API request: ${request.method()} ${path}`);
    });

    await page.goto("/projects/project-stream-1/chapters/chapter-stream-1");
    await expect(page.getByLabel("文本模型")).toHaveValue("model-stream-1");
    await page.getByRole("button", { name: "保存并生成剧本" }).click();

    await expect(page.getByRole("tab", { name: "剧本" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByLabel("实时剧本内容")).toHaveValue("# 第一场\n\n沈清荷推门入内。");
    await expect(page.getByText("实时草稿")).toBeVisible();
    await expect(page.getByText(/正在生成|正在重新连接/)).toBeVisible();
  });
}
