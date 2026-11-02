"""Frame resizing and palette quantization helpers."""

import atexit
import os
import subprocess
import tempfile
from pathlib import Path
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



_PREPARED_VIDEO_FILES = set()


def _cleanup_prepared_video_files():
    for prepared_path in tuple(_PREPARED_VIDEO_FILES):
        try:
            Path(prepared_path).unlink(missing_ok=True)
        finally:
            _PREPARED_VIDEO_FILES.discard(prepared_path)


atexit.register(_cleanup_prepared_video_files)


def _duplicate_frame_ranges(video_path):
    """Return adjacent duplicate frame ranges and the decoded frame count.

    Equality is exact: every decoded pixel and channel must match the preceding
    frame. Non-adjacent repetitions are deliberately kept.
    """
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    duplicate_ranges = []
    previous_frame = None
    frame_index = 0
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            if previous_frame is not None and np.array_equal(frame, previous_frame):
                if duplicate_ranges and duplicate_ranges[-1][1] == frame_index - 1:
                    duplicate_ranges[-1] = (duplicate_ranges[-1][0], frame_index)
                else:
                    duplicate_ranges.append((frame_index, frame_index))

            previous_frame = frame.copy()
            frame_index += 1
    finally:
        capture.release()

    if frame_index == 0:
        raise ValueError(f"Video contains no readable frames: {video_path}")
    return duplicate_ranges, frame_index


def prepare_video_for_generation(video_path):
    """Remove adjacent, pixel-identical frames from a temporary video copy.

    Original frame timestamps are retained, so a kept frame occupies the time
    span of the duplicate frames that follow it. The source file is never
    modified. If no adjacent duplicates exist, the original path is returned.
    """
    source = Path(video_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    duplicate_ranges, total_frames = _duplicate_frame_ranges(source)
    if not duplicate_ranges:
        return video_path

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "Removing duplicate video frames requires imageio-ffmpeg. "
            "Install the project requirements and try again."
        ) from exc

    drop_expression = "+".join(
        f"eq(n\\,{start})" if start == end
        else f"between(n\\,{start}\\,{end})"
        for start, end in duplicate_ranges
    )
    filter_script = (
        f"[0:v:0]select='not({drop_expression})'[prepared_video]\n"
    )

    output_fd, output_name = tempfile.mkstemp(
        prefix="rtg-prepared-", suffix=".mp4"
    )
    os.close(output_fd)
    output = Path(output_name)

    script_fd, script_name = tempfile.mkstemp(
        prefix="rtg-frame-selection-", suffix=".ffscript"
    )
    os.close(script_fd)
    script_path = Path(script_name)

    try:
        script_path.write_text(filter_script, encoding="utf-8")
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source),
            "-filter_complex_script", str(script_path),
            "-map", "[prepared_video]",
            "-map", "0:a?",
            "-map_metadata", "0",
            "-map_chapters", "0",
            "-fps_mode:v", "vfr",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output),
        ]
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("FFmpeg produced an empty prepared video")

        verification = cv2.VideoCapture(str(output))
        try:
            output_frames = int(verification.get(cv2.CAP_PROP_FRAME_COUNT))
            if not verification.isOpened() or output_frames != total_frames - sum(
                end - start + 1 for start, end in duplicate_ranges
            ):
                raise RuntimeError(
                    "Prepared video frame count does not match the duplicate-frame plan"
                )
        finally:
            verification.release()

        _PREPARED_VIDEO_FILES.add(str(output))
        return output
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        output.unlink(missing_ok=True)
        details = getattr(exc, "stderr", "") or str(exc)
        raise RuntimeError(
            f"Could not remove consecutive duplicate frames: {details[-1600:]}"
        ) from exc
    finally:
        script_path.unlink(missing_ok=True)


def sequence_from_color_frames(matrix, duration, color_frames):
    """Map analyzed colours to physical pixels without recalculating frames.

    ``duration`` may be one fixed duration or the per-frame list produced by
    the analysis phase.
    """
    from ..animation.frame import FrameBuilder
    from ..animation.sequence import SequenceBuilder

    sequence_builder = SequenceBuilder()
    if isinstance(duration, (list, tuple)):
        if len(duration) != len(color_frames):
            raise ValueError("Frame duration list must match analyzed frame count")
        durations = duration
    else:
        durations = [duration] * len(color_frames)
    for frame_index, color_frame in enumerate(color_frames):
        frame_builder = FrameBuilder(duration=float(durations[frame_index]))
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
