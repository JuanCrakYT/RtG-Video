"""Generate the deterministic video used by the end-to-end preview benchmark."""

import argparse
from pathlib import Path

import cv2
import numpy as np


WIDTH = 640
HEIGHT = 360
FPS = 30
FRAME_COUNT = 180


def build_frame(frame_number):
    y_values = np.arange(HEIGHT, dtype=np.uint16)[:, None]
    x_values = np.arange(WIDTH, dtype=np.uint16)[None, :]
    time_offset = frame_number * 7
    frame = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:, :, 0] = ((x_values * 3 + y_values * 5 + time_offset) % 256).astype(np.uint8)
    frame[:, :, 1] = ((x_values * 7 + y_values * 11 + frame_number * 13) % 256).astype(np.uint8)
    frame[:, :, 2] = ((x_values * 13 + y_values * 17 + frame_number * 19) % 256).astype(np.uint8)

    center_x = int((WIDTH * (0.5 + 0.35 * np.sin(frame_number / 11))) % WIDTH)
    center_y = int(HEIGHT * (0.5 + 0.3 * np.cos(frame_number / 13)))
    cv2.circle(frame, (center_x, center_y), 46, (255, 255, 255), 3)
    cv2.rectangle(
        frame,
        (frame_number * 5 % (WIDTH - 100), 24),
        (frame_number * 5 % (WIDTH - 100) + 100, 88),
        (0, 0, 0),
        2,
    )
    cv2.putText(
        frame,
        f"RtG {frame_number:03d}",
        (24, HEIGHT - 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return frame


def generate(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    for codec in ("avc1", "mp4v"):
        candidate = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), FPS, (WIDTH, HEIGHT))
        if candidate.isOpened():
            writer = candidate
            break
        candidate.release()
    if writer is None:
        raise RuntimeError("OpenCV could not open an MP4 writer (tried avc1 and mp4v)")

    try:
        for frame_number in range(FRAME_COUNT):
            writer.write(build_frame(frame_number))
    finally:
        writer.release()
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=Path(__file__).with_name("synthetic_test.mp4"))
    args = parser.parse_args()
    output = generate(args.path)
    print(output)


if __name__ == "__main__":
    main()