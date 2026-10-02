const DEFAULT_PALETTE = [[0, 0, 0], [255, 255, 255], [128, 128, 128]];

export function clampDimension(value, minimum = 2, maximum = 128) {
    const number = Number(value);
    if (!Number.isFinite(number)) throw new Error("Preview dimensions must be numeric");
    return Math.max(minimum, Math.min(maximum, Math.trunc(number)));
}

export function normalizePalette(colors) {
    const palette = [[0, 0, 0]];
    for (const color of colors) {
        if (!Array.isArray(color) || color.length !== 3) {
            throw new Error(`RGB colors must contain exactly 3 channels: ${color}`);
        }
        const rgb = color.map((channel) => Math.max(0, Math.min(255, Number(channel))));
        if (!palette.some((candidate) => candidate.every((value, index) => value === rgb[index]))) {
            palette.push(rgb);
        }
    }
    return palette;
}

function nearestPaletteColor(red, green, blue, palette) {
    let nearest = palette[0];
    let nearestDistance = Number.POSITIVE_INFINITY;
    for (const candidate of palette) {
        const distance = (red - candidate[0]) ** 2
            + (green - candidate[1]) ** 2
            + (blue - candidate[2]) ** 2;
        if (distance < nearestDistance) {
            nearest = candidate;
            nearestDistance = distance;
        }
    }
    return nearest;
}

function roundHalfEven(value) {
    const lower = Math.floor(value);
    const fraction = value - lower;
    if (fraction < 0.5) return lower;
    if (fraction > 0.5) return lower + 1;
    return lower % 2 === 0 ? lower : lower + 1;
}

export function resizeImageDataArea(imageData, width, height) {
    const resized = new Uint8ClampedArray(width * height * 4);
    for (let targetY = 0; targetY < height; targetY += 1) {
        const sourceTop = targetY * imageData.height / height;
        const sourceBottom = (targetY + 1) * imageData.height / height;
        for (let targetX = 0; targetX < width; targetX += 1) {
            const sourceLeft = targetX * imageData.width / width;
            const sourceRight = (targetX + 1) * imageData.width / width;
            const totals = [0, 0, 0, 0];
            let totalWeight = 0;
            for (let sourceY = Math.floor(sourceTop); sourceY <= Math.ceil(sourceBottom) - 1; sourceY += 1) {
                const yWeight = Math.min(sourceBottom, sourceY + 1) - Math.max(sourceTop, sourceY);
                for (let sourceX = Math.floor(sourceLeft); sourceX <= Math.ceil(sourceRight) - 1; sourceX += 1) {
                    const weight = (Math.min(sourceRight, sourceX + 1) - Math.max(sourceLeft, sourceX)) * yWeight;
                    const offset = (sourceY * imageData.width + sourceX) * 4;
                    for (let channel = 0; channel < 4; channel += 1) totals[channel] += imageData.data[offset + channel] * weight;
                    totalWeight += weight;
                }
            }
            const targetOffset = (targetY * width + targetX) * 4;
            for (let channel = 0; channel < 4; channel += 1) resized[targetOffset + channel] = roundHalfEven(totals[channel] / totalWeight);
        }
    }
    return { width, height, data: resized };
}

export function quantizeImageData(imageData, width, height, colors = DEFAULT_PALETTE) {
    const flat = quantizeImageDataFlat(imageData, width, height, colors);
    return Array.from({ length: height }, (_, y) => Array.from({ length: width }, (_, x) => {
        const offset = (y * width + x) * 4;
        return [flat[offset], flat[offset + 1], flat[offset + 2]];
    }));
}

export function quantizeImageDataFlat(imageData, width, height, colors = DEFAULT_PALETTE) {
    if (!imageData || imageData.width < 1 || imageData.height < 1) throw new Error("Image data must have positive dimensions");
    if (width < 1 || height < 1) throw new Error("Preview dimensions must be positive");
    const palette = normalizePalette(colors);
    const resized = resizeImageDataArea(imageData, width, height);
    const result = new Uint8ClampedArray(width * height * 4);
    for (let offset = 0; offset < result.length; offset += 4) {
        const color = nearestPaletteColor(resized.data[offset], resized.data[offset + 1], resized.data[offset + 2], palette);
        result[offset] = color[0];
        result[offset + 1] = color[1];
        result[offset + 2] = color[2];
        result[offset + 3] = 255;
    }
    return result;
}

export function renderQuantizedGrid(context, quantized, width, height) {
    const image = context.createImageData(context.canvas.width, context.canvas.height);
    const cellSize = Math.min(400 / Math.max(width, 1), 400 / Math.max(height, 1));
    for (let pixelY = 0; pixelY < context.canvas.height; pixelY += 1) {
        const gridY = Math.floor((pixelY - 10) / cellSize);
        if (gridY < 0 || gridY >= height) continue;
        for (let pixelX = 0; pixelX < context.canvas.width; pixelX += 1) {
            const gridX = Math.floor((pixelX - 10) / cellSize);
            if (gridX < 0 || gridX >= width) continue;
            const sourceOffset = (gridY * width + gridX) * 4;
            const targetOffset = (pixelY * context.canvas.width + pixelX) * 4;
            image.data[targetOffset] = quantized[sourceOffset];
            image.data[targetOffset + 1] = quantized[sourceOffset + 1];
            image.data[targetOffset + 2] = quantized[sourceOffset + 2];
            image.data[targetOffset + 3] = 255;
        }
    }
    context.putImageData(image, 0, 0);
    context.strokeStyle = "#d0d0d0";
    context.strokeRect(10, 10, width * cellSize, height * cellSize);
}

export function processVideoFrame(video, sourceCanvas, sourceContext, width, height, palette) {
    const start = performance.now();
    sourceContext.drawImage(video, 0, 0, sourceCanvas.width, sourceCanvas.height);
    const imageData = sourceContext.getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);
    return { quantized: quantizeImageDataFlat(imageData, width, height, palette), processMs: performance.now() - start };
}

export class PreviewController {
    constructor({ video, plyr, canvas, width, height, frameCount = null, palette = DEFAULT_PALETTE, onError = null, onData = null, onClose = null, onFrameUpdate = null }) {
        this.video = video;
        this.plyr = plyr;
        this.canvas = canvas;
        this.width = clampDimension(width);
        this.height = clampDimension(height);
        this.palette = normalizePalette(palette);
        this.frameCount = frameCount;
        this.onError = onError;
        this.onData = onData;
        this.onClose = onClose;
        this.onFrameUpdate = onFrameUpdate;

        this.context = canvas.getContext("2d");
        this.sourceCanvas = null;
        this.sourceContext = null;
        this.animationFrame = null;
        this.callbackMode = null;
        this.frameNumber = 0;
        this.totalFrames = null;
        this.lastMediaTime = null;
        this.isPlaying = false;
        this.isInitialized = false;
        this.wasPlayingBeforeSeek = false;
        this.toggleSound = null;
        this._boundHandleVideoError = this._handleVideoError.bind(this);

        this._initAudio();
    }

    _initAudio() {
        if (typeof window === "undefined" || typeof window.Audio !== "function") {
            this.toggleSound = null;
            return;
        }
        this.toggleSound = new window.Audio("/asset/notification.mp3");
    }

    _handleVideoError() {
        const error = new Error("The selected video could not be decoded");
        this.onError?.(error);
        this.destroy();
    }

    initialize() {
        if (this.isInitialized) return;

        if (!this.video || this.video.readyState < 1) throw new Error("Load a video before initializing the preview");

        this.sourceCanvas = document.createElement("canvas");
        this.sourceContext = this.sourceCanvas.getContext("2d", { willReadFrequently: true });
        this.sourceCanvas.width = this.video.videoWidth;
        this.sourceCanvas.height = this.video.videoHeight;

        const suppliedFrameCount = Number(this.frameCount);
        const videoFrameRate = Number(this.video.dataset?.fps);
        this.totalFrames = Number.isFinite(suppliedFrameCount) && suppliedFrameCount > 0
            ? Math.trunc(suppliedFrameCount)
            : Number.isFinite(this.video.duration) && this.video.duration > 0 && Number.isFinite(videoFrameRate) && videoFrameRate > 0
                ? Math.round(this.video.duration * videoFrameRate) : null;

        this.video.addEventListener("error", this._boundHandleVideoError, { once: true });
        this.video.loop = true;

        this.onData?.({
            Width: this.width,
            Height: this.height,
            "Frame-Count": this.totalFrames,
        });

        this.isInitialized = true;
        this.isPlaying = !this.video.paused;

        if (this.isPlaying) {
            this._startRenderLoop();
        } else {
            this._renderCurrentFrame();
        }
    }

    play() {
        if (!this.isInitialized) return;
        this.isPlaying = true;
        this.video.play().catch((error) => {
            this.isPlaying = false;
            this._stopRenderLoop();
            this.onError?.(error);
        });
        if (this.animationFrame === null) this._startRenderLoop();
    }

    pause() {
        if (!this.isInitialized) return;
        this.isPlaying = false;
        this._stopRenderLoop();
        this.video.pause();
    }

    stop() {
        this.pause();
        this.video.currentTime = 0;
        this.frameNumber = 0;
        this._renderCurrentFrame();
    }

    reset() {
        this.stop();
    }

    seek(time) {
        if (!this.isInitialized) return;
        const duration = this.video.duration || 0;
        const newTime = Math.max(0, Math.min(time, duration));
        this.wasPlayingBeforeSeek = this.isPlaying;
        if (this.isPlaying) {
            this.pause();
        }
        this.video.currentTime = newTime;
        this._renderCurrentFrame();
        if (this.wasPlayingBeforeSeek) {
            this.play();
        }
    }

    seekFrame(frameIndex) {
        if (!this.isInitialized || !this.video.duration || this.totalFrames <= 0) return;
        const newTime = (frameIndex / this.totalFrames) * this.video.duration;
        this.seek(newTime);
    }

    nextFrame() {
        if (!this.isInitialized || this.totalFrames <= 0) return;
        const next = Math.min(this.frameNumber + 1, this.totalFrames - 1);
        this.seekFrame(next);
    }

    previousFrame() {
        if (!this.isInitialized || this.totalFrames <= 0) return;
        const prev = Math.max(this.frameNumber - 1, 0);
        this.seekFrame(prev);
    }

    setFPS(fps) {
        if (!this.isInitialized) return;
        this.video.dataset.fps = String(fps);
        const newTotalFrames = Number.isFinite(this.video.duration) && this.video.duration > 0 && fps > 0
            ? Math.round(this.video.duration * fps) : null;
        if (newTotalFrames !== null) {
            this.totalFrames = newTotalFrames;
            this.onData?.({
                Width: this.width,
                Height: this.height,
                "Frame-Count": this.totalFrames,
            });
        }
    }

    getCurrentFrame() {
        return this.frameNumber;
    }

    getTotalFrames() {
        return this.totalFrames;
    }

    setSource(src) {
        if (!this.isInitialized) return;
        this.video.src = src;
        this.video.load();
    }

    destroy() {
        this._stopRenderLoop();
        this.video?.pause();
        this.video?.removeEventListener("error", this._boundHandleVideoError);
        this.toggleSound = null;
        this.sourceCanvas = null;
        this.sourceContext = null;
        this.lastMediaTime = null;
        this.isPlaying = false;
        this.isInitialized = false;
        this.onClose?.();
    }

    onPlyrPlay() {
        if (!this.isInitialized) return;
        this.isPlaying = true;
        if (this.animationFrame === null) this._startRenderLoop();
    }

    onPlyrPause() {
        if (!this.isInitialized) return;
        this.isPlaying = false;
        this._stopRenderLoop();
    }

    onPlyrSeeked() {
        if (!this.isInitialized) return;
        this._renderCurrentFrame();
        if (this.wasPlayingBeforeSeek && !this.isPlaying) {
            this.play();
        }
        this.wasPlayingBeforeSeek = false;
    }

    onPlyrTimeUpdate() {
        if (!this.isInitialized || !this.isPlaying) return;
        this._renderCurrentFrame();
    }

    onPlyrEnded() {
        if (!this.isInitialized) return;
        this.isPlaying = false;
        this._stopRenderLoop();
        this.video.currentTime = 0;
        this.frameNumber = 0;
        this._renderCurrentFrame();
    }

    onPlyrRateChange() {
        // Playback rate changed, frame timing will adjust automatically via timeupdate
    }

    onPlyrVolumeChange() {
        // Volume/mute changed - handled by Plyr UI
    }

    onPlyrFullscreenChange(isFullscreen) {
        // Fullscreen state changed - canvas rendering continues
    }

    _startRenderLoop() {
        if (this.animationFrame !== null) return;
        this._scheduleNextFrame();
    }

    _stopRenderLoop() {
        if (this.animationFrame === null) return;
        if (this.callbackMode === "requestVideoFrameCallback" && this.video.cancelVideoFrameCallback) {
            this.video.cancelVideoFrameCallback(this.animationFrame);
        } else if (this.callbackMode === "requestAnimationFrame") {
            cancelAnimationFrame(this.animationFrame);
        }
        this.animationFrame = null;
        this.callbackMode = null;
    }

    _scheduleNextFrame() {
        if (typeof this.video.requestVideoFrameCallback === "function") {
            this.callbackMode = "requestVideoFrameCallback";
            this.animationFrame = this.video.requestVideoFrameCallback((_, metadata) => this._onVideoFrame(metadata));
        } else {
            this.callbackMode = "requestAnimationFrame";
            this.animationFrame = requestAnimationFrame(() => this._onVideoFrame(null));
        }
    }

    _onVideoFrame(metadata) {
        this.animationFrame = null;
        if (!this.isPlaying || !this.isInitialized) return;
        this._renderCurrentFrame(metadata);
        this._scheduleNextFrame();
    }

    _renderCurrentFrame(metadata = null) {
        if (!this.canvas || !this.context || !this.sourceContext) return;

        const mediaTime = Number.isFinite(metadata?.mediaTime) ? metadata.mediaTime : this.video.currentTime;
        const frameRate = Number(this.video.dataset?.fps);

        if (Number.isFinite(mediaTime) && mediaTime >= 0 && Number.isFinite(frameRate) && frameRate > 0) {
            this.frameNumber = this.totalFrames
                ? Math.floor(mediaTime * frameRate) % this.totalFrames
                : Math.floor(mediaTime * frameRate);
        } else if (!this.video.paused && this.isPlaying) {
            this.frameNumber = this.totalFrames ? (this.frameNumber + 1) % this.totalFrames : this.frameNumber + 1;
        }

        this.lastMediaTime = mediaTime;

        const processed = processVideoFrame(this.video, this.sourceCanvas, this.sourceContext, this.width, this.height, this.palette);

        this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
        renderQuantizedGrid(this.context, processed.quantized, this.width, this.height);

        this.onFrameUpdate?.(this.frameNumber, this.totalFrames);
    }
}

export const PreviewAPI = {
    create: (options) => new PreviewController(options),
    clampDimension,
    normalizePalette,
    quantizeImageData,
    quantizeImageDataFlat,
    resizeImageDataArea,
    renderQuantizedGrid,
    processVideoFrame,
};