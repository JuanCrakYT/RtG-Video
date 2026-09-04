const DEFAULT_PALETTE = [
    [0, 0, 0],
    [255, 255, 255],
    [128, 128, 128],
];

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

export function quantizeImageData(imageData, width, height, colors = DEFAULT_PALETTE) {
    if (!imageData || imageData.width < 1 || imageData.height < 1) {
        throw new Error("Image data must have positive dimensions");
    }
    if (width < 1 || height < 1) {
        throw new Error("Preview dimensions must be positive");
    }

    const palette = normalizePalette(colors);
    const result = [];
    for (let y = 0; y < height; y += 1) {
        const row = [];
        const sourceY = Math.min(imageData.height - 1, Math.floor(y * imageData.height / height));
        for (let x = 0; x < width; x += 1) {
            const sourceX = Math.min(imageData.width - 1, Math.floor(x * imageData.width / width));
            const offset = (sourceY * imageData.width + sourceX) * 4;
            row.push(nearestPaletteColor(
                imageData.data[offset],
                imageData.data[offset + 1],
                imageData.data[offset + 2],
                palette,
            ));
        }
        result.push(row);
    }
    return result;
}

export class PreviewController {
    constructor({ video, width, height, palette = DEFAULT_PALETTE, windowTarget = window }) {
        this.video = video;
        this.width = width;
        this.height = height;
        this.palette = palette;
        this.windowTarget = windowTarget;
        this.previewWindow = null;
        this.previewCanvas = null;
        this.previewContext = null;
        this.previewCounter = null;
        this.animationFrame = null;
        this.isPlaying = false;
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

        const canvas = this.previewWindow.document.createElement("canvas");
        canvas.width = 420;
        canvas.height = 420;
        canvas.style.display = "block";
        canvas.style.margin = "12px auto 8px";
        canvas.style.background = "#111111";
        this.previewWindow.document.body.appendChild(canvas);
        this.previewCanvas = canvas;
        this.previewContext = canvas.getContext("2d", { willReadFrequently: true });

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
        this.isPlaying = true;
        this.video.play();
        this.drawFrame();
    }

    togglePause(toggleButton) {
        this.isPlaying = !this.isPlaying;
        if (this.isPlaying) {
            this.video.play();
            toggleButton.textContent = "Pause";
        } else {
            this.video.pause();
            toggleButton.textContent = "Play";
        }
    }

    drawFrame() {
        if (!this.previewWindow || this.previewWindow.closed || !this.previewCanvas) {
            return;
        }
        const context = this.previewContext;
        context.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        context.drawImage(this.video, 0, 0, this.previewCanvas.width, this.previewCanvas.height);
        const imageData = context.getImageData(0, 0, this.previewCanvas.width, this.previewCanvas.height);
        const quantized = quantizeImageData(imageData, this.width, this.height, this.palette);
        const cellSize = Math.min(400 / Math.max(this.width, 1), 400 / Math.max(this.height, 1));
        const baseX = 10;
        const baseY = 10;
        for (let y = 0; y < this.height; y += 1) {
            for (let x = 0; x < this.width; x += 1) {
                const [red, green, blue] = quantized[y][x];
                context.fillStyle = `rgb(${red}, ${green}, ${blue})`;
                context.fillRect(baseX + x * cellSize, baseY + y * cellSize, cellSize, cellSize);
            }
        }
        context.strokeStyle = "#d0d0d0";
        context.strokeRect(baseX, baseY, this.width * cellSize, this.height * cellSize);
        this.previewCounter.textContent = `Frame: ${Math.floor(this.video.currentTime * 1000)} ms`;
        this.animationFrame = this.windowTarget.requestAnimationFrame(() => this.drawFrame());
    }

    close() {
        if (this.animationFrame !== null) {
            this.windowTarget.cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
        if (this.video) {
            this.video.pause();
        }
        if (this.previewWindow && !this.previewWindow.closed) {
            this.previewWindow.close();
        }
        this.previewWindow = null;
        this.previewCanvas = null;
        this.previewContext = null;
        this.previewCounter = null;
        this.isPlaying = false;
    }
}
