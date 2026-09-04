import assert from "node:assert/strict";
import { PreviewController } from "./preview.js";

function makeContext() {
    return {
        canvas: { width: 420, height: 420 },
        createImageData: (width, height) => ({ data: new Uint8ClampedArray(width * height * 4) }),
        putImageData() { },
        clearRect() { },
        strokeRect() { },
    };
}

function makeVideo({ withVideoFrameCallback }) {
    const video = {
        paused: false,
        videoWidth: 2,
        videoHeight: 2,
        dataset: {},
        play: async () => { },
        pause() { this.paused = true; },
        addEventListener() { },
        removeEventListener() { },
    };
    if (withVideoFrameCallback) {
        video.requestVideoFrameCallback = (callback) => {
            video.callback = callback;
            return 7;
        };
        video.cancelVideoFrameCallback = (id) => {
            video.cancelled = id;
        };
    }
    return video;
}

function prepareController(video, windowTarget) {
    const controller = new PreviewController({ video, width: 2, height: 2, windowTarget });
    controller.previewWindow = { closed: false, close() { this.closed = true; } };
    controller.previewCanvas = { width: 420, height: 420 };
    controller.previewContext = makeContext();
    controller.previewCounter = { textContent: "" };
    controller.sourceCanvas = { width: 2, height: 2 };
    controller.sourceContext = {
        drawImage() { },
        getImageData: () => ({
            width: 2,
            height: 2,
            data: new Uint8ClampedArray([
                0, 0, 0, 255,
                255, 255, 255, 255,
                128, 128, 128, 255,
                0, 0, 0, 255,
            ]),
        }),
    };
    controller.isPlaying = true;
    return controller;
}

const videoCallback = makeVideo({ withVideoFrameCallback: true });
const videoWindow = {
    requestAnimationFrame() { throw new Error("fallback should not be used"); },
    cancelAnimationFrame() { },
};
const videoController = prepareController(videoCallback, videoWindow);
videoController.drawFrame({ presentedFrames: 4 });
assert.equal(videoController.getMetrics().callbackMode, "requestVideoFrameCallback");
assert.equal(videoController.getMetrics().callbackPending, true);
videoController.togglePause({ textContent: "Pause" });
assert.equal(videoController.getMetrics().callbackPending, false);
assert.equal(videoCallback.cancelled, 7);
videoController.close();
assert.equal(videoController.getMetrics().callbackPending, false);

const fallbackVideo = makeVideo({ withVideoFrameCallback: false });
const fallbackWindow = {
    requestAnimationFrame(callback) {
        fallbackWindow.callback = callback;
        return 9;
    },
    cancelAnimationFrame(id) {
        fallbackWindow.cancelled = id;
    },
};
const fallbackController = prepareController(fallbackVideo, fallbackWindow);
fallbackController.drawFrame();
assert.equal(fallbackController.getMetrics().callbackMode, "requestAnimationFrame");
fallbackController.close();
assert.equal(fallbackWindow.cancelled, 9);
assert.equal(fallbackController.isPlaying, false);

console.log("experimental preview controller checks passed");