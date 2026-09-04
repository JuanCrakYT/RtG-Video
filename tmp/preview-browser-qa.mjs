import path from "node:path";

export default async function run(page) {
    const videoPath = path.resolve("tmp/synthetic_test.mp4");
    const input = page.locator("#video-file");
    await input.setInputFiles(videoPath);
    await page.waitForFunction(() => !document.querySelector("#preview").disabled);

    const popupPromise = page.waitForEvent("popup");
    await page.locator("#preview").click();
    const popup = await popupPromise;
    await popup.waitForFunction(() => Boolean(window.previewController?.metrics?.processedFrames));
    const beforePause = await popup.evaluate(() => window.previewController.getMetrics());
    await popup.getByRole("button", { name: "Pause" }).click();
    const pausedAt = await popup.evaluate(() => window.previewController.getMetrics());
    await popup.waitForTimeout(200);
    const pausedAfterWait = await popup.evaluate(() => window.previewController.getMetrics());
    await popup.getByRole("button", { name: "Play" }).click();
    await popup.waitForTimeout(200);
    const afterResume = await popup.evaluate(() => window.previewController.getMetrics());
    await popup.getByRole("button", { name: "Close" }).click();
    return {
        beforePause,
        pausedAt,
        pausedAfterWait,
        afterResume,
        popupClosed: await popup.evaluate(() => window.closed),
    };
}