const path = require("path");
const { test, expect } = require("@playwright/test");

const boomZoomVideoPath = path.resolve(
  __dirname,
  "../../test-videos/daytime-color-shahed-boom-zoom.MP4",
);
const shortDaylightVideoPath = path.resolve(
  __dirname,
  "../../test-videos/daytime-color-shahed.MP4",
);

async function openAndUploadVideo(page, videoPath = boomZoomVideoPath) {
  await page.goto("/");
  await expect(page.getByText("Operator Runtime Block")).toBeVisible();

  const uploadInput = page.locator('input[type="file"]').first();
  await uploadInput.setInputFiles(videoPath);

  await expect(page.getByText(/Video loaded and ready to process/i)).toBeVisible();
  await expect(page.getByRole("button", { name: "Start Processing" })).toBeEnabled();
}

async function findVideoFrame(page) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    for (const frame of page.frames()) {
      try {
        if ((await frame.locator("video").count()) > 0) {
          return frame;
        }
      } catch {
        // Frame can disappear during rerender; keep polling.
      }
    }
    await page.waitForTimeout(200);
  }

  throw new Error("Could not find the runtime video iframe");
}

async function readVideoState(page) {
  const frame = await findVideoFrame(page);
  return frame.locator("video").evaluate((video) => ({
    currentTime: video.currentTime,
    paused: video.paused,
    ended: video.ended,
    duration: video.duration,
  }));
}

test("processing starts and progress moves forward", async ({ page }) => {
  await openAndUploadVideo(page);

  await page.getByRole("button", { name: "Start Processing" }).click();
  await expect(page.getByText(/Processing uploaded video preview/i)).toBeVisible();

  await expect
    .poll(async () => {
      const bodyText = await page.locator("body").textContent();
      const match = bodyText?.match(/Progress:\s*(\d+)\/(\d+)\s*frames/i);
      return match ? Number.parseInt(match[1], 10) : 0;
    }, {
      message: "Expected processing progress to advance beyond frame 0",
    })
    .toBeGreaterThan(0);
});

test("reset returns the app to the initial upload state", async ({ page }) => {
  await openAndUploadVideo(page);

  await page.getByRole("button", { name: "Reset State" }).click();

  await expect(page.getByText(/Upload a prerecorded video to initialize the runtime player/i)).toBeVisible();
  await expect(page.getByText(/Awaiting uploaded video/i)).toBeVisible();
});

test("video advances during first-run processing without resetting backward", async ({ page }) => {
  await openAndUploadVideo(page);

  await page.getByRole("button", { name: "Start Processing" }).click();
  await expect(page.getByText(/Processing uploaded video preview/i)).toBeVisible();

  await expect
    .poll(async () => {
      const state = await readVideoState(page);
      return state.currentTime;
    }, {
      timeout: 8_000,
      message: "Expected runtime video to advance beyond the first second during processing",
    })
    .toBeGreaterThan(1);

  const samples = [];
  for (let index = 0; index < 8; index += 1) {
    const state = await readVideoState(page);
    samples.push(state.currentTime);
    await page.waitForTimeout(400);
  }

  const significantBackwardJump = samples.some((value, index) => {
    if (index === 0) {
      return false;
    }
    return value < samples[index - 1] - 0.75;
  });

  expect(significantBackwardJump, `Video timeline reset backward during processing: ${samples.join(", ")}`).toBeFalsy();
});

test("video does not implicitly replay after processing reaches 100 percent", async ({ page }) => {
  await openAndUploadVideo(page, shortDaylightVideoPath);

  await page.getByRole("button", { name: "Start Processing" }).click();
  await expect(page.getByText(/Processing uploaded video preview/i)).toBeVisible();

  await expect
    .poll(async () => {
      const bodyText = await page.locator("body").textContent();
      const match = bodyText?.match(/Progress:\s*(\d+)\/(\d+)\s*frames/i);
      if (!match) {
        return 0;
      }
      const processed = Number.parseInt(match[1], 10);
      const total = Number.parseInt(match[2], 10);
      return total > 0 ? processed / total : 0;
    }, {
      timeout: 60_000,
      message: "Expected processing to reach completion",
    })
    .toBeGreaterThanOrEqual(1);

  const completionSamples = [];
  for (let index = 0; index < 6; index += 1) {
    const state = await readVideoState(page);
    completionSamples.push(state.currentTime);
    await page.waitForTimeout(500);
  }

  const replayDetected = completionSamples.some((value, index) => {
    if (index === 0) {
      return false;
    }
    return value < completionSamples[index - 1] - 0.75;
  });

  expect(
    replayDetected,
    `Video timeline replayed unexpectedly after processing completed: ${completionSamples.join(", ")}`,
  ).toBeFalsy();
});
