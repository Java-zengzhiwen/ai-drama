import { defineConfig, devices } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_BACKEND_PORT ?? "18765";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;
const webDir = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = fileURLToPath(new URL("..", import.meta.url));
const playwrightOutputRoot = mkdtempSync(join(tmpdir(), "ai-drama-m1-playwright-"));
const playwrightDataRoot = join(playwrightOutputRoot, "runtime-data");

export default defineConfig({
  testDir: "./tests",
  outputDir: join(playwrightOutputRoot, "test-results"),
  reporter: [["list"], ["html", { open: "never", outputFolder: join(playwrightOutputRoot, "report") }]],
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: frontendURL,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command:
        `python3 -m uvicorn ai_drama_web.app:create_app --factory --host 127.0.0.1 --port ${backendPort}`,
      cwd: repoRoot,
      env: {
        ...process.env,
        AI_DRAMA_DATA_ROOT: playwrightDataRoot,
        PYTHONDONTWRITEBYTECODE: "1",
      },
      reuseExistingServer: false,
      url: `${backendURL}/api/health`,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: webDir,
      reuseExistingServer: false,
      url: frontendURL,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
