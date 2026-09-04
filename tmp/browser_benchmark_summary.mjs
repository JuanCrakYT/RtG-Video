export default async function run(page) {
    await page.waitForSelector("body[data-ready], body[data-error]", { timeout: 180000 });
    return await page.evaluate(() => ({
        ready: document.body.dataset.ready,
        error: document.body.dataset.error || null,
        results: window.benchmarkResults?.results?.map((result) => ({
            width: result.width,
            frames_processed: result.frames_processed,
            frames_skipped: result.frames_skipped,
            duration_ms: result.duration_ms,
            process_ms_per_frame: result.process_ms_per_frame,
            render_ms_per_frame: result.render_ms_per_frame,
            total_ms_per_frame: result.total_ms_per_frame,
            effective_fps: result.effective_fps,
            callback_mode: result.callback_mode,
            checksum_sum: result.checksum_sum,
        })),
    }));
}