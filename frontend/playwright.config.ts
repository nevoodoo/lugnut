import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, devices } from "@playwright/test";

// Runs against the built app (npm run build first), served by the real backend on a throwaway data dir.
export default defineConfig({
  testDir: "e2e",
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:8765", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } } }],
  webServer: {
    command: "uv run lugnut serve --port 8765",
    cwd: "..",
    url: "http://127.0.0.1:8765/api/health",
    reuseExistingServer: false,
    env: {
      LUGNUT_DATA_DIR: mkdtempSync(join(tmpdir(), "lugnut-e2e-")),
      LUGNUT_SECURE_COOKIES: "false",
      LUGNUT_REMINDER_INTERVAL_SECONDS: "0",
    },
  },
});
