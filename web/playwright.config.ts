import { defineConfig, devices } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const backendPort = process.env.AI_DRAMA_PLAYWRIGHT_BACKEND_PORT ?? "18765";
const m6dBackendPort = process.env.AI_DRAMA_PLAYWRIGHT_M6D_BACKEND_PORT ?? "18766";
const m6ePublicBackendPort = process.env.AI_DRAMA_PLAYWRIGHT_M6E_PUBLIC_BACKEND_PORT ?? "18767";
const frontendPort = process.env.AI_DRAMA_PLAYWRIGHT_FRONTEND_PORT ?? "15173";
const backendURL = `http://127.0.0.1:${backendPort}`;
const frontendURL = `http://127.0.0.1:${frontendPort}`;
const webDir = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = fileURLToPath(new URL("..", import.meta.url));
const playwrightOutputRoot = mkdtempSync(join(tmpdir(), "ai-drama-m1-playwright-"));
const playwrightDataRoot = join(playwrightOutputRoot, "runtime-data");
const playwrightM6dDataRoot = join(playwrightOutputRoot, "runtime-data-m6d");
const playwrightM6ePublicDataRoot = join(playwrightOutputRoot, "runtime-data-m6e-public");

export default defineConfig({
  metadata: {
    m6dDataRoot: playwrightM6dDataRoot,
    m6ePublicBackendURL: `http://127.0.0.1:${m6ePublicBackendPort}`,
  },
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
      command:
        `python3 -m uvicorn ai_drama_web.app:create_app --factory --host 127.0.0.1 --port ${m6dBackendPort}`,
      cwd: repoRoot,
      env: {
        ...process.env,
        AI_DRAMA_DATA_ROOT: playwrightM6dDataRoot,
        AI_DRAMA_AGNES_POLL_INTERVAL_SECONDS: "3600",
        AI_DRAMA_M6_SUPPLIER_EXECUTION_ENABLED: "true",
        PYTHONDONTWRITEBYTECODE: "1",
      },
      reuseExistingServer: false,
      url: `http://127.0.0.1:${m6dBackendPort}/api/health`,
    },
    {
      command:
        `python3 -m uvicorn tests.support.m6e_public_ingress:create_public_ingress_app --factory --host 127.0.0.1 --port ${m6ePublicBackendPort}`,
      cwd: repoRoot,
      env: {
        ...process.env,
        AI_DRAMA_DATA_ROOT: playwrightM6ePublicDataRoot,
        PYTHONDONTWRITEBYTECODE: "1",
      },
      reuseExistingServer: false,
      url: `http://127.0.0.1:${m6ePublicBackendPort}/api/health`,
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
