const { defineConfig } = require("@playwright/test");

const baseURL = process.env.PLAYWRIGHT_EXTERNAL_BASE_URL || "http://127.0.0.1:8501";

module.exports = defineConfig({
  testDir: "./tests/ui",
  timeout: 120_000,
  expect: {
    timeout: 15_000,
  },
  retries: 0,
  reporter: [["list"], ["html", { outputFolder: "output/playwright/report", open: "never" }]],
  use: {
    baseURL,
    browserName: "chromium",
    channel: "chrome",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
  },
});
