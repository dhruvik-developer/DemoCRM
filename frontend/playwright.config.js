import { defineConfig } from "@playwright/test";

// E2E tests live in ./e2e and run against the Vite dev server.
// Browser binaries are NOT downloaded yet — run `npx playwright install`
// before the first `npm run e2e`.

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});
