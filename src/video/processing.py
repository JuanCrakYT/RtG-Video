"""Frame resizing and palette quantization helpers."""

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

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
                    if color == BLACK:
                        continue
                    pixel = matrix.get_pixel_for_color(x, y, color)
                    if pixel is not None:
                        frame_builder.set_pixel_color(pixel.uuid, color)
            sequence_builder.add_frame(frame_builder.build())
            frame_number += 1
    finally:
        capture.release()

    if frame_number == 0:
        raise ValueError(f"Video contains no readable frames: {video_path}")
    return sequence_builder.build()


def analyze_video_colors(video_path, width: int, height: int, palette: Iterable[Sequence[int]]):
    """Return frame durations and quantized colors before physical generation."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = 1.0 / fps if fps and fps > 0 else 0.05
    frames = []
    normalized_palette = normalize_palette(palette)
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(quantize_frame(rgb_frame, width, height, normalized_palette))
    finally:
        capture.release()

    if not frames:
        raise ValueError(f"Video contains no readable frames: {video_path}")
    return duration, frames


def sequence_from_color_frames(matrix, duration: float, color_frames):
    """Map analyzed coordinate colors to the generated physical pixel UUIDs."""
    from ..animation.frame import FrameBuilder
    from ..animation.sequence import SequenceBuilder

    sequence_builder = SequenceBuilder()
    for color_frame in color_frames:
        frame_builder = FrameBuilder(duration=duration)
        for y, row in enumerate(color_frame):
            for x, color in enumerate(row):
                if tuple(color) == BLACK:
                    continue
                pixel = matrix.get_pixel_for_color(x, y, color)
                if pixel is None:
                    raise ValueError(f"No generated pixel for position {(x, y)} and color {color}")
                frame_builder.set_pixel_color(pixel.uuid, color)
        sequence_builder.add_frame(frame_builder.build())
    return sequence_builder.build()


def analyze_pixel_color_usage(color_frames):
    """Return colors used by each coordinate and enforce one color per frame."""
    return {
        position: state["colors"]
        for position, state in analyze_pixel_states(color_frames).items()
    }


def analyze_pixel_states(color_frames):
    """Analyze used colors and one state per pixel for every frame."""
    states: Dict[Tuple[int, int], Dict[str, object]] = {}
    for frame_index, frame in enumerate(color_frames):
        for y, row in enumerate(frame):
            for x, color in enumerate(row):
                rgb = tuple(int(channel) for channel in color)
                if rgb == BLACK:
                    continue
                position = (x, y)
                state = states.setdefault(position, {"colors": set(), "frames": {}})
                frame_states = state["frames"]
                if frame_index in frame_states and frame_states[frame_index] != rgb:
                    raise ValueError(f"Pixel {position} has multiple colors in frame {frame_index}")
                state["colors"].add(rgb)
                frame_states[frame_index] = rgb
    return states
