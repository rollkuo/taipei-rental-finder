import { defineConfig, devices } from "@playwright/test";

const PROD_URL = "https://taipei-rental-finder.vercel.app";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: PROD_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: /mobile\.spec\.ts/,
    },
    {
      name: "mobile",
      use: {
        ...devices["Pixel 7"],
        // Pixel 7 device descriptor uses Chromium, not WebKit — avoids needing the
        // WebKit binary install just for a viewport check.
      },
      testMatch: /mobile\.spec\.ts/,
    },
  ],
});
