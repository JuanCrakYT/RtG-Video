export default async function run(page) {
    await page.waitForFunction(() => document.body.textContent.includes("Preview playing") || document.body.textContent.includes("Preview error"));
    await page.getByRole("button", { name: "Pause" }).click();
    const frameAtPause = await page.locator("body").textContent();
    await page.waitForTimeout(150);
    const frameAfterPause = await page.locator("body").textContent();
    await page.getByRole("button", { name: "Play" }).click();
    await page.waitForTimeout(150);
    const frameAfterResume = await page.locator("body").textContent();
    await page.getByRole("button", { name: "Close" }).click();
    return {
        title: await page.title(),
        status: await page.locator("#status").textContent(),
        sourceReady: await page.locator("#source").evaluate((video) => video.readyState >= 1),
        controllerStarted: await page.evaluate(() => document.body.dataset.previewStarted === "true"),
        callbackMode: await page.evaluate(() => document.body.dataset.previewStarted ? "browser-scheduler" : null),
        pauseHeldFrame: frameAtPause.match(/Frame: [^ ]+ \/ [^ ]+/)?.[0] === frameAfterPause.match(/Frame: [^ ]+ \/ [^ ]+/)?.[0],
        resumed: frameAfterResume.match(/Frame: [^ ]+ \/ [^ ]+/)?.[0] !== frameAfterPause.match(/Frame: [^ ]+ \/ [^ ]+/)?.[0],
    };
}
