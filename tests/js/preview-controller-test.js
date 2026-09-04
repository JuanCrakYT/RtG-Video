import assert from "node:assert/strict";
import { PreviewController } from "../../src/ui/preview/preview.js";

function context() {
    return { canvas: { width: 420, height: 420 }, createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }), putImageData() { }, clearRect() { }, strokeRect() { } };
}

function video(withVideoCallback) {
    const value = { readyState: 1, paused: false, videoWidth: 2, videoHeight: 2, dataset: {}, play: async () => { }, pause() { this.paused = true; }, addEventListener() { }, removeEventListener() { } };
    if (withVideoCallback) {
        value.requestVideoFrameCallback = (callback) => { value.callback = callback; return 7; };
        value.cancelVideoFrameCallback = (id) => { value.cancelled = id; };
    }
    return value;
}

function controller(source, target) {
    const instance = new PreviewController({ video: source, width: 2, height: 2, windowTarget: target });
    instance.previewWindow = { closed: false, close() { this.closed = true; } };
    instance.previewCanvas = { width: 420, height: 420 };
    instance.previewContext = context();
    instance.previewCounter = { textContent: "" };
    instance.sourceCanvas = { width: 2, height: 2 };
    instance.sourceContext = { drawImage() { }, getImageData: () => ({ width: 2, height: 2, data: new Uint8ClampedArray([0, 0, 0, 255, 255, 255, 255, 255, 128, 128, 128, 255, 0, 0, 0, 255]) }) };
    instance.isPlaying = true;
    return instance;
}

const source = video(true);
const target = { requestAnimationFrame() { throw new Error("fallback should not be used"); }, cancelAnimationFrame() { } };
const instance = controller(source, target);
instance.drawFrame({ presentedFrames: 4 });
assert.equal(instance.callbackMode, "requestVideoFrameCallback");
instance.togglePause({ textContent: "Pause" });
assert.equal(source.cancelled, 7);
assert.equal(source.paused, true);
instance.close();

const fallbackSource = video(false);
const fallbackTarget = { requestAnimationFrame(callback) { fallbackTarget.callback = callback; return 9; }, cancelAnimationFrame(id) { fallbackTarget.cancelled = id; } };
const fallback = controller(fallbackSource, fallbackTarget);
fallback.drawFrame();
assert.equal(fallback.callbackMode, "requestAnimationFrame");
fallback.close();
assert.equal(fallbackTarget.cancelled, 9);
assert.equal(fallback.isPlaying, false);

console.log("production preview controller checks passed");
