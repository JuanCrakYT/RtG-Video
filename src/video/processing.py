"""Frame resizing and palette quantization helpers."""

from typing import Iterable, List, Sequence, Tuple

import cv2
import numpy as np

RGBColor = Tuple[int, int, int]
BLACK: RGBColor = (0, 0, 0)
WHITE: RGBColor = (255, 255, 255)
GRAY: RGBColor = (128, 128, 128)
DEFAULT_PALETTE: Tuple[RGBColor, ...] = (BLACK, WHITE, GRAY)


def normalize_palette(colors: Iterable[Sequence[int]]) -> List[RGBColor]:
    """Return a deduplicated RGB palette that always contains black."""
    palette: List[RGBColor] = [BLACK]
    for color in colors:
        rgb = tuple(max(0, min(255, int(channel))) for channel in color)
        if len(rgb) != 3:
            raise ValueError(f"RGB colors must have 3 channels: {color}")
        if rgb not in palette:
            palette.append(rgb)
    return palette


def nearest_palette_color(color: Sequence[int], palette: Sequence[RGBColor]) -> RGBColor:
    """Return the palette color with the smallest squared RGB distance."""
    if not palette:
        raise ValueError("Palette cannot be empty")
    source = np.asarray(color, dtype=np.int16)
    return min(
        palette,
        key=lambda candidate: int(np.sum((source - np.asarray(candidate)) ** 2)),
    )


def quantize_frame(
    frame: np.ndarray,
    width: int,
    height: int,
    palette: Iterable[Sequence[int]],
) -> List[List[RGBColor]]:
    """Resize a BGR/RGB frame and map every output pixel to the nearest color."""
    if width < 1 or height < 1:
        raise ValueError("Frame dimensions must be positive")

    normalized_palette = normalize_palette(palette)
    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    return [
        [
            nearest_palette_color(resized[y, x], normalized_palette)
            for x in range(width)
        ]
        for y in range(height)
    ]


def video_to_sequence(video_path, matrix, palette: Iterable[Sequence[int]]):
    """Convert a video into resized, palette-quantized animation frames."""
    from ..animation.frame import FrameBuilder
    from ..animation.sequence import SequenceBuilder

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = 1.0 / fps if fps and fps > 0 else 0.05
    normalized_palette = normalize_palette(palette)
    sequence_builder = SequenceBuilder()

    try:
        frame_number = 0
        while True:
            success, frame = capture.read()
            if not success:
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            quantized = quantize_frame(
                rgb_frame,
                matrix.width,
                matrix.height,
                normalized_palette,
            )
            frame_builder = FrameBuilder(duration=duration)
            for y, row in enumerate(quantized):
                for x, color in enumerate(row):
                    pixel = matrix.get_pixel(x, y)
                    if pixel is not None:
                        frame_builder.set_pixel_color(pixel.uuid, color)
            sequence_builder.add_frame(frame_builder.build())
            frame_number += 1
    finally:
        capture.release()

    if frame_number == 0:
        raise ValueError(f"Video contains no readable frames: {video_path}")
    return sequence_builder.build()
