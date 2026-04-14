const path = require("path");
const { test, expect } = require("@playwright/test");

const BOOM_ZOOM_VIDEO = path.resolve(__dirname, "../../test-videos/daytime-color-shahed-boom-zoom.MP4");
const DAYLIGHT_SHAHED_VIDEO = path.resolve(__dirname, "../../test-videos/daytime-color-shahed.MP4");

async function uploadVideoAndWaitForPreprocessing(page, videoPath) {
  await page.goto("/");

  const uploadInput = page.locator('input[type="file"]');
  await expect(uploadInput).toHaveCount(1);
  await uploadInput.setInputFiles(videoPath);

  const startTrackingButton = page.getByRole("button", { name: "Start Tracking" });
  await expect(startTrackingButton).toBeEnabled({ timeout: 60_000 });
  return startTrackingButton;
}

async function findVideoFrame(page) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    for (const frame of page.frames()) {
      const videoCount = await frame.locator("video").count();
      if (videoCount > 0) {
        return frame;
      }
    }
    await page.waitForTimeout(200);
  }
  throw new Error("Could not find the runtime video iframe");
}

async function readVideoCurrentTime(page) {
  const frame = await findVideoFrame(page);
  return frame.locator("video").evaluate((video) => video.currentTime);
}

test("preprocessing summary shows non-zero tracking for boom-zoom", async ({ page }) => {
  await uploadVideoAndWaitForPreprocessing(page, BOOM_ZOOM_VIDEO);

  const pageText = page.locator("body");
  await expect(pageText).toContainText("Tracking Frames", { timeout: 15_000 });

  const text = await pageText.textContent();
  expect(text).toMatch(/Detection Frames:\s*[1-9]\d*/);
  expect(text).toMatch(/Tracking Frames:\s*[1-9]\d*/);
});

test("arm guidance does not restart playback from the beginning", async ({ page }) => {
  const startTrackingButton = await uploadVideoAndWaitForPreprocessing(page, DAYLIGHT_SHAHED_VIDEO);

  await startTrackingButton.click();
  await expect
    .poll(async () => readVideoCurrentTime(page), {
      timeout: 15_000,
      message: "Expected video playback to move forward before arming guidance",
    })
    .toBeGreaterThan(1.0);

  const beforeArmTime = await readVideoCurrentTime(page);
  await page.getByRole("button", { name: "Arm Guidance" }).click();

  await expect(page.locator("body")).toContainText("Guidance: Armed", { timeout: 10_000 });
  await page.waitForTimeout(600);

  const afterArmTime = await readVideoCurrentTime(page);
  expect(afterArmTime).toBeGreaterThan(beforeArmTime - 0.5);
});
