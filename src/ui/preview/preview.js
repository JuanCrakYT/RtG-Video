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
    constructor({ video, width, height, frameCount = null, palette = DEFAULT_PALETTE, windowTarget = window, popup = true, onClose = null, onData = null, onError = null }) {
        this.video = video;
        this.width = clampDimension(width);
        this.height = clampDimension(height);
        this.palette = normalizePalette(palette);
        this.frameCount = frameCount;
        this.windowTarget = windowTarget;
        this.popup = popup;
        this.onClose = onClose;
        this.onData = onData;
        this.onError = onError;
        this.previewWindow = null;
        this.ownsPreviewWindow = false;
        this.animationFrame = null;
        this.sourceCanvas = null;
        this.sourceContext = null;
        this.previewCanvas = null;
        this.previewContext = null;
        this.previewCounter = null;
        this.frameNumber = 0;
        this.totalFrames = null;
        this.isPlaying = false;
        this.callbackMode = null;
        this.handleVideoError = () => {
            const error = new Error("The selected video could not be decoded");
            this.onError?.(error);
            this.close();
        };
    }

    open() {
        if (!this.video || this.video.readyState < 1) throw new Error("Load a video before opening the preview");
        this.close(false);
        this.previewWindow = this.popup ? this.windowTarget.open("", "rtg-preview", "width=560,height=520,resizable=no") : this.windowTarget;
        this.ownsPreviewWindow = this.popup;
        if (!this.previewWindow) throw new Error("The preview window was blocked by the browser");
        const document = this.previewWindow.document;
        if (this.popup) document.body.replaceChildren();
        document.title = `RtG Video Preview - ${this.video.dataset.name || "video"}`;
        document.body.style.margin = "0";
        document.body.style.background = "#f5f5f5";
        document.body.style.fontFamily = "Segoe UI, sans-serif";
        const canvas = document.createElement("canvas");
        canvas.width = 420;
        canvas.height = 420;
        canvas.style.display = "block";
        canvas.style.margin = "12px auto 8px";
        canvas.style.background = "#111111";
        document.body.appendChild(canvas);
        this.previewCanvas = canvas;
        this.previewContext = canvas.getContext("2d");
        this.sourceCanvas = document.createElement("canvas");
        this.sourceCanvas.width = this.video.videoWidth;
        this.sourceCanvas.height = this.video.videoHeight;
        this.sourceContext = this.sourceCanvas.getContext("2d", { willReadFrequently: true });
        const info = document.createElement("div");
        info.textContent = `RtG preview: ${this.width} x ${this.height} pixels`;
        info.style.textAlign = "center";
        info.style.fontWeight = "bold";
        document.body.appendChild(info);
        this.previewCounter = document.createElement("div");
        this.previewCounter.style.textAlign = "center";
        document.body.appendChild(this.previewCounter);
        const controls = document.createElement("div");
        controls.style.textAlign = "center";
        controls.style.margin = "12px";
        const toggle = document.createElement("button");
        toggle.textContent = "Pause";
        toggle.onclick = () => this.togglePause(toggle);
        controls.appendChild(toggle);
        const close = document.createElement("button");
        close.textContent = "Close";
        close.onclick = () => this.close();
        controls.appendChild(close);
        document.body.appendChild(controls);
        this.totalFrames = Number.isFinite(this.video.duration) && this.video.duration > 0 && this.video.dataset.fps
            ? Math.round(this.video.duration * Number(this.video.dataset.fps)) : Number(this.frameCount) || null;
        this.onData?.({
            Width: this.width,
            Height: this.height,
            "Frame-Count": this.totalFrames,
        });
        this.video.addEventListener("error", this.handleVideoError, { once: true });
        this.video.currentTime = 0;
        this.video.loop = true;
        this.isPlaying = true;
        this.video.play().catch((error) => {
            this.isPlaying = false;
            this.cancelScheduledFrame();
            this.onError?.(error);
        });
        this.drawFrame();
    }

    togglePause(toggleButton) {
        if (!this.previewWindow || (this.ownsPreviewWindow && this.previewWindow.closed)) return;
        this.isPlaying = !this.isPlaying;
        if (this.isPlaying) {
            this.video.play().catch((error) => {
                this.isPlaying = false;
                this.cancelScheduledFrame();
                this.onError?.(error);
            });
            if (this.animationFrame === null) this.drawFrame();
            toggleButton.textContent = "Pause";
        } else {
            this.cancelScheduledFrame();
            this.video.pause();
            toggleButton.textContent = "Play";
        }
    }

    cancelScheduledFrame() {
        if (this.animationFrame === null) return;
        if (this.callbackMode === "requestVideoFrameCallback" && this.video.cancelVideoFrameCallback) this.video.cancelVideoFrameCallback(this.animationFrame);
        if (this.callbackMode === "requestAnimationFrame") this.windowTarget.cancelAnimationFrame(this.animationFrame);
        this.animationFrame = null;
    }

    drawFrame(metadata = null) {
        if (!this.previewWindow || (this.ownsPreviewWindow && this.previewWindow.closed)) return this.close();
        if (!this.previewCanvas || !this.isPlaying) return;
        this.animationFrame = null;
        if (metadata?.presentedFrames !== undefined) this.frameNumber = metadata.presentedFrames;
        else if (!this.video.paused) this.frameNumber += 1;
        const processed = processVideoFrame(this.video, this.sourceCanvas, this.sourceContext, this.width, this.height, this.palette);
        this.previewContext.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        renderQuantizedGrid(this.previewContext, processed.quantized, this.width, this.height);
        this.previewCounter.textContent = `Frame: ${this.frameNumber} / ${this.totalFrames ?? "?"}`;
        if (typeof this.video.requestVideoFrameCallback === "function") {
            this.callbackMode = "requestVideoFrameCallback";
            this.animationFrame = this.video.requestVideoFrameCallback((_, nextMetadata) => this.drawFrame(nextMetadata));
        } else {
            this.callbackMode = "requestAnimationFrame";
            this.animationFrame = this.windowTarget.requestAnimationFrame(() => this.drawFrame());
        }
    }

    close(notify = true) {
        this.cancelScheduledFrame();
        this.video?.pause();
        this.video?.removeEventListener("error", this.handleVideoError);
        if (this.ownsPreviewWindow && this.previewWindow && !this.previewWindow.closed) this.previewWindow.close();
        this.previewWindow = null;
        this.previewCanvas = null;
        this.previewContext = null;
        this.previewCounter = null;
        this.sourceCanvas = null;
        this.sourceContext = null;
        this.isPlaying = false;
        if (notify) this.onClose?.();
    }
}
