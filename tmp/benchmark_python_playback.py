"""End-to-end benchmark for the generated video using the Python Preview path."""

import argparse
import json
import sys
import time
import tkinter as tk
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.video.processing import DEFAULT_PALETTE, quantize_frame
from generate_test_video import generate


DIMENSIONS = (16, 32, 64, 96, 128)
VIDEO_PATH = Path(__file__).with_name("synthetic_test.mp4")


def checksum(quantized):
    return sum(sum(sum(pixel) for pixel in row) for row in quantized)


def render(canvas, quantized, width, height):
    cell_size = min(400 // max(width, 1), 400 // max(height, 1))
    canvas.delete("all")
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


def benchmark_dimension(root, video_path, width, height, frame_limit):
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    canvas = tk.Canvas(root, width=420, height=420, highlightthickness=0)
    canvas.pack()
    root.update_idletasks()
    process_ms = 0.0
    render_ms = 0.0
    frames_processed = 0
    total_checksum = 0
    benchmark_start = time.perf_counter()
    try:
        while frames_processed < frame_limit:
            process_start = time.perf_counter()
            success, frame = capture.read()
            if not success:
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            quantized = quantize_frame(rgb_frame, width, height, DEFAULT_PALETTE)
            process_ms += (time.perf_counter() - process_start) * 1000
            render_start = time.perf_counter()
            render(canvas, quantized, width, height)
            root.update_idletasks()
            render_ms += (time.perf_counter() - render_start) * 1000
            total_checksum += checksum(quantized)
            frames_processed += 1
    finally:
        capture.release()
        canvas.destroy()
    duration_ms = (time.perf_counter() - benchmark_start) * 1000
    total_ms = process_ms + render_ms
    return {
        "width": width,
        "height": height,
        "pixels": width * height,
        "frames_processed": frames_processed,
        "frames_skipped": 0,
        "duration_ms": duration_ms,
        "process_ms": process_ms,
        "render_ms": render_ms,
        "total_ms": total_ms,
        "process_ms_per_frame": process_ms / frames_processed if frames_processed else 0,
        "render_ms_per_frame": render_ms / frames_processed if frames_processed else 0,
        "total_ms_per_frame": total_ms / frames_processed if frames_processed else 0,
        "effective_fps": frames_processed * 1000 / duration_ms if duration_ms else 0,
        "callback_mode": "tk-main-loop",
        "checksum_sum": total_checksum,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--video", type=Path, default=VIDEO_PATH)
    args = parser.parse_args()
    if not args.video.exists():
        generate(args.video)
    root = tk.Tk()
    root.withdraw()
    try:
        results = [
            benchmark_dimension(root, args.video, dimension, dimension, args.frames)
            for dimension in DIMENSIONS
        ]
    finally:
        root.destroy()
    print(json.dumps({
        "benchmark": "End-to-end playback benchmark",
        "runtime": "python-opencv-tkinter",
        "source": {"path": str(args.video), "width": 640, "height": 360, "fps": 30},
        "palette": [list(color) for color in DEFAULT_PALETTE],
        "results": results,
    }))


if __name__ == "__main__":
    main()