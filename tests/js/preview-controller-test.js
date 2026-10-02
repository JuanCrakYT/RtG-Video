import assert from "node:assert/strict";
import { PreviewController } from "../../src/ui/preview/preview.js";

// Mock browser globals for Node.js test environment
global.window = {
    Audio: class {
        constructor() { this.currentTime = 0; this.played = false; }
        play() { this.played = true; return Promise.resolve(); }
    },
    requestAnimationFrame: (cb) => { global.rafCallback = cb; return 9; },
    cancelAnimationFrame: (id) => { global.rafCancelled = id; },
};
global.document = {
    createElement: (tag) => {
        if (tag === "canvas") {
            return {
                width: 0,
                height: 0,
                getContext: () => ({
                    canvas: { width: 2, height: 2 },
                    drawImage() { },
                    getImageData: () => ({ width: 2, height: 2, data: new Uint8ClampedArray([0, 0, 0, 255, 255, 255, 255, 255, 128, 128, 128, 255, 0, 0, 0, 255]) })
                }),
            };
        }
        return {};
    },
};

function mockCanvas() {
    return {
        width: 420,
        height: 420,
        getContext: () => ({
            canvas: { width: 420, height: 420 },
            createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }),
            putImageData() { },
            clearRect() { },
            strokeRect() { },
        }),
    };
}

function mockVideo(withVideoCallback, metadata = {}) {
    const value = {
        readyState: 1,
        paused: false,
        currentTime: 0,
        duration: 0.8,
        videoWidth: 2,
        videoHeight: 2,
        dataset: { ...metadata },
        loop: false,
        play: async () => { value.paused = false; },
        pause() { value.paused = true; },
        addEventListener() { },
        removeEventListener() { },
        load() { },
    };
    if (withVideoCallback) {
        value.requestVideoFrameCallback = (callback) => { value.callback = callback; return 7; };
        value.cancelVideoFrameCallback = (id) => { value.cancelled = id; };
    }
    return value;
}

function mockPlyr() {
    return {
        on: (event, callback) => { },
        play: () => { },
        pause: () => { },
    };
}

const canvas = mockCanvas();
const source = mockVideo(true, { fps: "10" });
const plyr = mockPlyr();

let frameUpdateCalled = false;
let lastFrame = -1;
let lastTotal = -1;

const instance = new PreviewController({
    video: source,
    plyr,
    canvas,
    width: 2,
    height: 2,
    frameCount: 8,
    palette: [[0, 0, 0], [255, 255, 255], [128, 128, 128]],
    onFrameUpdate: (frame, total) => {
        frameUpdateCalled = true;
        lastFrame = frame;
        lastTotal = total;
    },
    onData: () => { },
    onError: () => { },
    onClose: () => { },
});

instance.initialize();

assert.equal(instance.isInitialized, true);
assert.equal(instance.totalFrames, 8);
assert.equal(instance.width, 2);
assert.equal(instance.height, 2);

// Test frame calculation
source.currentTime = 0.7;
instance._renderCurrentFrame({ mediaTime: 0.7 });
assert.equal(instance.frameNumber, 7);
assert.equal(frameUpdateCalled, true);
assert.equal(lastFrame, 7);
assert.equal(lastTotal, 8);

frameUpdateCalled = false;
source.currentTime = 0;
instance._renderCurrentFrame({ mediaTime: 0 });
assert.equal(instance.frameNumber, 0);
assert.equal(lastFrame, 0);

// Test play/pause
instance.play();
assert.equal(instance.isPlaying, true);
assert.equal(source.paused, false);

instance.pause();
assert.equal(instance.isPlaying, false);
assert.equal(source.paused, true);

// Test seek
instance.seek(0.5);
assert.equal(source.currentTime, 0.5);

// Test seekFrame
instance.seekFrame(4);
assert.equal(source.currentTime, 0.4); // 4/8 * 0.8 duration (mock)

// Test next/previous frame
instance.frameNumber = 3;
instance.nextFrame();
assert.equal(instance.frameNumber, 4);

instance.previousFrame();
assert.equal(instance.frameNumber, 3);

// Test setFPS
instance.setFPS(20);
assert.equal(source.dataset.fps, "20");
assert.equal(instance.totalFrames, 16); // 0.8 * 20

// Test getCurrentFrame/getTotalFrames
assert.equal(instance.getCurrentFrame(), 3);
assert.equal(instance.getTotalFrames(), 16);

// Test destroy
instance.destroy();
assert.equal(instance.isInitialized, false);
assert.equal(instance.isPlaying, false);

// Test fallback render loop (requestAnimationFrame)
const fallbackCanvas = mockCanvas();
const fallbackSource = mockVideo(false);
const fallbackPlyr = mockPlyr();
const fallbackInstance = new PreviewController({
    video: fallbackSource,
    plyr: fallbackPlyr,
    canvas: fallbackCanvas,
    width: 2,
    height: 2,
    frameCount: 8,
    onFrameUpdate: () => { },
    onData: () => { },
    onError: () => { },
    onClose: () => { },
});

fallbackInstance.initialize();
fallbackInstance._renderCurrentFrame();
assert.equal(fallbackInstance.callbackMode, "requestAnimationFrame");

fallbackInstance.destroy();

console.log("preview controller checks passed");