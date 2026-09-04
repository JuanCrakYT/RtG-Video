const DEFAULT_PALETTE = [
    [0, 0, 0],
    [255, 255, 255],
    [128, 128, 128],
];

export function clampDimension(value, minimum = 2, maximum = 128) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
        throw new Error("Preview dimensions must be numeric");
    }
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
    const sourceWidth = imageData.width;
    const sourceHeight = imageData.height;

    for (let targetY = 0; targetY < height; targetY += 1) {
        const sourceTop = targetY * sourceHeight / height;
        const sourceBottom = (targetY + 1) * sourceHeight / height;
        const firstSourceY = Math.floor(sourceTop);
        const lastSourceY = Math.ceil(sourceBottom) - 1;

        for (let targetX = 0; targetX < width; targetX += 1) {
            const sourceLeft = targetX * sourceWidth / width;
            const sourceRight = (targetX + 1) * sourceWidth / width;
            const firstSourceX = Math.floor(sourceLeft);
            const lastSourceX = Math.ceil(sourceRight) - 1;
            const totals = [0, 0, 0, 0];
            let totalWeight = 0;

            for (let sourceY = firstSourceY; sourceY <= lastSourceY; sourceY += 1) {
                const yWeight = Math.min(sourceBottom, sourceY + 1) - Math.max(sourceTop, sourceY);
                for (let sourceX = firstSourceX; sourceX <= lastSourceX; sourceX += 1) {
                    const xWeight = Math.min(sourceRight, sourceX + 1) - Math.max(sourceLeft, sourceX);
                    const weight = xWeight * yWeight;
                    const offset = (sourceY * sourceWidth + sourceX) * 4;
                    for (let channel = 0; channel < 4; channel += 1) {
                        totals[channel] += imageData.data[offset + channel] * weight;
                    }
                    totalWeight += weight;
                }
            }

            const targetOffset = (targetY * width + targetX) * 4;
            for (let channel = 0; channel < 4; channel += 1) {
                resized[targetOffset + channel] = roundHalfEven(totals[channel] / totalWeight);
            }
        }
    }

    return { width, height, data: resized };
}

export function quantizeImageData(imageData, width, height, colors = DEFAULT_PALETTE) {
    if (!imageData || imageData.width < 1 || imageData.height < 1) {
        throw new Error("Image data must have positive dimensions");
    }
    if (width < 1 || height < 1) {
        throw new Error("Preview dimensions must be positive");
    }

    const quantized = quantizeImageDataFlat(imageData, width, height, colors);
    const result = [];
    for (let y = 0; y < height; y += 1) {
        const row = [];
        for (let x = 0; x < width; x += 1) {
            const offset = (y * width + x) * 4;
            row.push([
                quantized[offset],
                quantized[offset + 1],
                quantized[offset + 2],
            ]);
        }
        result.push(row);
    }
    return result;
}

export function quantizeImageDataFlat(imageData, width, height, colors = DEFAULT_PALETTE) {
    if (!imageData || imageData.width < 1 || imageData.height < 1) {
        throw new Error("Image data must have positive dimensions");
    }
    if (width < 1 || height < 1) {
        throw new Error("Preview dimensions must be positive");
    }

    const palette = normalizePalette(colors);
    const resized = resizeImageDataArea(imageData, width, height);
    const result = new Uint8ClampedArray(width * height * 4);
    for (let offset = 0; offset < result.length; offset += 4) {
        const color = nearestPaletteColor(
            resized.data[offset],
            resized.data[offset + 1],
            resized.data[offset + 2],
            palette,
        );
        result[offset] = color[0];
        result[offset + 1] = color[1];
        result[offset + 2] = color[2];
        result[offset + 3] = 255;
    }
    return result;
}

export function renderQuantizedGrid(context, quantized, width, height) {
    const canvasWidth = context.canvas.width;
    const canvasHeight = context.canvas.height;
    const image = context.createImageData(canvasWidth, canvasHeight);
    const cellSize = Math.min(400 / Math.max(width, 1), 400 / Math.max(height, 1));
    for (let pixelY = 0; pixelY < canvasHeight; pixelY += 1) {
        const gridY = Math.floor((pixelY - 10) / cellSize);
        if (gridY < 0 || gridY >= height) continue;
        for (let pixelX = 0; pixelX < canvasWidth; pixelX += 1) {
            const gridX = Math.floor((pixelX - 10) / cellSize);
            if (gridX < 0 || gridX >= width) continue;
            const sourceOffset = (gridY * width + gridX) * 4;
            const targetOffset = (pixelY * canvasWidth + pixelX) * 4;
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
    const sourceStart = performance.now();
    sourceContext.drawImage(video, 0, 0, sourceCanvas.width, sourceCanvas.height);
    const imageData = sourceContext.getImageData(
        0,
        0,
        sourceCanvas.width,
        sourceCanvas.height,
    );
    const quantized = quantizeImageDataFlat(imageData, width, height, palette);
    return {
        quantized,
        processMs: performance.now() - sourceStart,
    };
}

export class PreviewController {
    constructor({ video, width, height, palette = DEFAULT_PALETTE, windowTarget = window }) {
        this.video = video;
        this.width = clampDimension(width);
        this.height = clampDimension(height);
        this.palette = palette;
        this.windowTarget = windowTarget;
        this.previewWindow = null;
        this.previewCanvas = null;
        this.previewContext = null;
        this.previewCounter = null;
        this.animationFrame = null;
        this.sourceCanvas = null;
        this.sourceContext = null;
        this.frameNumber = 0;
        this.totalFrames = null;
        this.isPlaying = false;
        this.callbackMode = null;
        this.previousPresentedFrames = null;
        this.metrics = this.createMetrics();
        this.handleVideoError = () => this.close();
    }

    createMetrics() {
        return {
            processedFrames: 0,
            skippedFrames: 0,
            callbacks: 0,
            processMs: 0,
            renderMs: 0,
            callbackPending: false,
            callbackMode: this.callbackMode,
        };
    }

    open() {
        if (!this.video || this.video.readyState < 1) {
            throw new Error("Load a video before opening the preview");
        }
        this.close();

        this.previewWindow = this.windowTarget.open("", "rtg-preview", "width=560,height=520,resizable=no");
        if (!this.previewWindow) {
            throw new Error("The preview window was blocked by the browser");
        }
        this.previewWindow.document.title = `RtG Preview - ${this.video.dataset.name || "video"}`;
        this.previewWindow.document.body.style.margin = "0";
        this.previewWindow.document.body.style.background = "#f5f5f5";
        this.previewWindow.document.body.style.fontFamily = "Segoe UI, sans-serif";
        const icon = this.previewWindow.document.createElement("link");
        icon.rel = "icon";
        icon.href = "../assets/logo/favicon.ico";
        this.previewWindow.document.head.appendChild(icon);

        const canvas = this.previewWindow.document.createElement("canvas");
        canvas.width = 420;
        canvas.height = 420;
        canvas.style.display = "block";
        canvas.style.margin = "12px auto 8px";
        canvas.style.background = "#111111";
        this.previewWindow.document.body.appendChild(canvas);
        this.previewCanvas = canvas;
        this.previewContext = canvas.getContext("2d", { willReadFrequently: true });
        this.sourceCanvas = this.previewWindow.document.createElement("canvas");
        this.sourceCanvas.width = this.video.videoWidth;
        this.sourceCanvas.height = this.video.videoHeight;
        this.sourceContext = this.sourceCanvas.getContext("2d", { willReadFrequently: true });

        const info = this.previewWindow.document.createElement("div");
        info.textContent = `RtG preview: ${this.width} x ${this.height} pixels`;
        info.style.textAlign = "center";
        info.style.fontWeight = "bold";
        this.previewWindow.document.body.appendChild(info);

        this.previewCounter = this.previewWindow.document.createElement("div");
        this.previewCounter.textContent = "Frame: 0 / ?";
        this.previewCounter.style.textAlign = "center";
        this.previewWindow.document.body.appendChild(this.previewCounter);

        const controls = this.previewWindow.document.createElement("div");
        controls.style.textAlign = "center";
        controls.style.margin = "12px";
        const toggle = this.previewWindow.document.createElement("button");
        toggle.textContent = "Pause";
        toggle.onclick = () => this.togglePause(toggle);
        controls.appendChild(toggle);
        const close = this.previewWindow.document.createElement("button");
        close.textContent = "Close";
        close.onclick = () => this.close();
        controls.appendChild(close);
        this.previewWindow.document.body.appendChild(controls);

        this.video.currentTime = 0;
        this.video.loop = true;
        this.video.addEventListener("error", this.handleVideoError, { once: true });
        this.isPlaying = true;
        this.frameNumber = 0;
        this.previousPresentedFrames = null;
        this.metrics = this.createMetrics();
        this.video.play().catch(() => this.close());
        this.drawFrame();
    }

    togglePause(toggleButton) {
        if (!this.previewWindow || this.previewWindow.closed) {
            return;
        }
        this.isPlaying = !this.isPlaying;
        if (this.isPlaying) {
            this.video.play().catch(() => this.close());
            if (!this.metrics.callbackPending) this.drawFrame();
            toggleButton.textContent = "Pause";
        } else {
            this.cancelScheduledFrame();
            this.video.pause();
            toggleButton.textContent = "Play";
        }
    }

    cancelScheduledFrame() {
        if (this.animationFrame === null) return;
        if (
            this.callbackMode === "requestVideoFrameCallback"
            && typeof this.video?.cancelVideoFrameCallback === "function"
        ) {
            this.video.cancelVideoFrameCallback(this.animationFrame);
        } else if (this.callbackMode === "requestAnimationFrame") {
            this.windowTarget.cancelAnimationFrame(this.animationFrame);
        }
        this.animationFrame = null;
        this.metrics.callbackPending = false;
    }

    drawFrame(frameMetadata = null) {
        if (!this.previewWindow || this.previewWindow.closed) {
            this.close();
            return;
        }
        if (!this.previewCanvas || !this.isPlaying) {
            return;
        }
        this.animationFrame = null;
        this.metrics.callbackPending = false;
        this.metrics.callbacks += 1;
        const context = this.previewContext;
        if (frameMetadata?.presentedFrames !== undefined) {
            this.frameNumber = frameMetadata.presentedFrames;
            if (this.previousPresentedFrames !== null) {
                this.metrics.skippedFrames += Math.max(
                    0,
                    frameMetadata.presentedFrames - this.previousPresentedFrames - 1,
                );
            }
            this.previousPresentedFrames = frameMetadata.presentedFrames;
        } else if (!this.video.paused) {
            this.frameNumber += 1;
        }
        const processed = processVideoFrame(
            this.video,
            this.sourceCanvas,
            this.sourceContext,
            this.width,
            this.height,
            this.palette,
        );
        const renderStart = performance.now();
        context.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        renderQuantizedGrid(context, processed.quantized, this.width, this.height);
        this.metrics.processedFrames += 1;
        this.metrics.processMs += processed.processMs;
        this.metrics.renderMs += performance.now() - renderStart;
        this.previewCounter.textContent = `Frame: ${this.frameNumber} / ${this.totalFrames ?? "?"}`;
        if (typeof this.video.requestVideoFrameCallback === "function") {
            this.callbackMode = "requestVideoFrameCallback";
            this.metrics.callbackMode = this.callbackMode;
            this.metrics.callbackPending = true;
            this.animationFrame = this.video.requestVideoFrameCallback((_, metadata) => this.drawFrame(metadata));
        } else {
            this.callbackMode = "requestAnimationFrame";
            this.metrics.callbackMode = this.callbackMode;
            this.metrics.callbackPending = true;
            this.animationFrame = this.windowTarget.requestAnimationFrame(() => this.drawFrame());
        }
    }

    getMetrics() {
        const { processedFrames, processMs, renderMs } = this.metrics;
        return {
            ...this.metrics,
            averageProcessMs: processedFrames ? processMs / processedFrames : 0,
            averageRenderMs: processedFrames ? renderMs / processedFrames : 0,
            averageTotalMs: processedFrames ? (processMs + renderMs) / processedFrames : 0,
        };
    }

    close() {
        this.cancelScheduledFrame();
        if (this.video) {
            this.video.pause();
            this.video.removeEventListener("error", this.handleVideoError);
        }
        if (this.previewWindow && !this.previewWindow.closed) {
            this.previewWindow.close();
        }
        this.previewWindow = null;
        this.previewCanvas = null;
        this.previewContext = null;
        this.previewCounter = null;
        this.sourceCanvas = null;
        this.sourceContext = null;
        this.frameNumber = 0;
        this.isPlaying = false;
        this.callbackMode = null;
        this.previousPresentedFrames = null;
    }
}
