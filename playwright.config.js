const { defineConfig } = require("@playwright/test");

const externalBaseUrl = process.env.PLAYWRIGHT_EXTERNAL_BASE_URL || null;

module.exports = defineConfig({
  testDir: "./tests/ui",
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: externalBaseUrl || "http://127.0.0.1:8501",
    headless: true,
    channel: "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  webServer: externalBaseUrl
    ? undefined
    : {
        command: ".venv/bin/streamlit run app/app.py --server.port 8501",
        url: "http://127.0.0.1:8501",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
