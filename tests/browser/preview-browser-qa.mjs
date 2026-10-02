export default async function run(page) {
    await page.waitForFunction(() => document.body.textContent.includes("Preview ready") || document.body.textContent.includes("Preview error"));
    await page.waitForSelector(".plyr__control--pressed", { state: "attached" });

    const pauseButton = page.locator('[data-plyr="pause"]');
    await pauseButton.click();

    const frameAtPause = await page.locator("#frame-counter").textContent();
    await page.waitForTimeout(150);
    const frameAfterPause = await page.locator("#frame-counter").textContent();

    const playButton = page.locator('[data-plyr="play"]');
    await playButton.click();

    await page.waitForTimeout(150);
    const frameAfterResume = await page.locator("#frame-counter").textContent();

    const closeButton = page.locator('[data-plyr="fullscreen"]'); // No close button in Plyr, use fullscreen as placeholder
    // Note: The new preview doesn't have a close button in the UI, window.close() is handled by beforeunload

    return {
        title: await page.title(),
        status: await page.locator("#status").textContent(),
        sourceReady: await page.locator("#source").evaluate((video) => video.readyState >= 1),
        controllerStarted: await page.evaluate(() => document.body.dataset.previewStarted === "true"),
        pauseHeldFrame: frameAtPause === frameAfterPause,
        resumed: frameAfterResume !== frameAfterPause,
    };
}