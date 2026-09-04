"""Synthetic Preview benchmark for Python processing and Tkinter rendering."""

import argparse
import json
import sys
import time
import tkinter as tk
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.video.processing import DEFAULT_PALETTE, quantize_frame

SOURCE_WIDTH = 640
SOURCE_HEIGHT = 360
DIMENSIONS = (16, 32, 64, 96, 128)


def synthetic_frame():
    frame = np.empty((SOURCE_HEIGHT, SOURCE_WIDTH, 3), dtype=np.uint8)
    y_values = np.arange(SOURCE_HEIGHT, dtype=np.uint16)[:, None]
    x_values = np.arange(SOURCE_WIDTH, dtype=np.uint16)[None, :]
    frame[:, :, 0] = ((x_values * 3 + y_values * 5) % 256).astype(np.uint8)
    frame[:, :, 1] = ((x_values * 7 + y_values * 11) % 256).astype(np.uint8)
    frame[:, :, 2] = ((x_values * 13 + y_values * 17) % 256).astype(np.uint8)
    return frame


def checksum(quantized):
    return sum(sum(sum(pixel) for pixel in row) for row in quantized)


def benchmark_dimension(root, source, width, height, iterations):
    for _ in range(3):
        quantize_frame(source, width, height, DEFAULT_PALETTE)

    process_times = []
    render_times = []
    canvas = tk.Canvas(root, width=420, height=420, highlightthickness=0)
    canvas.pack()
    root.update_idletasks()
    quantized = None

    for _ in range(iterations):
        start = time.perf_counter_ns()
        quantized = quantize_frame(source, width, height, DEFAULT_PALETTE)
        process_times.append((time.perf_counter_ns() - start) / 1_000_000)

        start = time.perf_counter_ns()
        canvas.delete("all")
        cell_size = min(400 // max(width, 1), 400 // max(height, 1))
        for y, row in enumerate(quantized):
            for x, (red, green, blue) in enumerate(row):
                canvas.create_rectangle(
                    10 + x * cell_size,
                    10 + y * cell_size,
                    10 + (x + 1) * cell_size,
                    10 + (y + 1) * cell_size,
                    fill=f"#{red:02x}{green:02x}{blue:02x}",
                    outline="",
                )
        canvas.create_rectangle(
            10,
            10,
            10 + width * cell_size,
            10 + height * cell_size,
            outline="#D0D0D0",
        )
        root.update_idletasks()
        render_times.append((time.perf_counter_ns() - start) / 1_000_000)

    canvas.destroy()
    process_ms = sum(process_times) / len(process_times)
    render_ms = sum(render_times) / len(render_times)
    total_ms = process_ms + render_ms
    return {
        "width": width,
        "height": height,
        "pixels": width * height,
        "iterations": iterations,
        "process_ms": round(process_ms, 4),
        "render_ms": round(render_ms, 4),
        "total_ms": round(total_ms, 4),
        "fps": round(1000 / total_ms, 4) if total_ms else None,
        "checksum": checksum(quantized),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    source = synthetic_frame()
    root = tk.Tk()
    root.withdraw()
    results = [
        benchmark_dimension(root, source, width, width, args.iterations)
        for width in DIMENSIONS
    ]
    root.destroy()
    print(json.dumps({
        "runtime": "python",
        "source": {"width": SOURCE_WIDTH, "height": SOURCE_HEIGHT},
        "palette": [list(color) for color in DEFAULT_PALETTE],
        "results": results,
    }))


if __name__ == "__main__":
    main()
