"""Build physical RtG signal networks for animation frames.

The network owns one Delayer per frame. A pixel that appears in multiple
frames receives its own Gate-OR chain; no OR chain or Wire is shared between
pixels. Connection IDs are numeric because they are part of the RtG format.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

from ..rtg.blocks import RtGBlock, RtGBuild, to_rtg_index


OR_OUTPUT = "1"
OR_INPUT_A = "2"
OR_INPUT_B = "3"


@dataclass(frozen=True)
class PixelSignalEndpoint:
    """The real block and point that receive a pixel activation signal."""

    block_index: int
    point_id: str


def resolve_pixel_inputs(pixels: Iterable[object]) -> Dict[str, PixelSignalEndpoint]:
    """Resolve pixel UUIDs to their real Splitter_3 signal endpoints."""
    endpoints: Dict[str, PixelSignalEndpoint] = {}
    for pixel in pixels:
        block_index, point_id = pixel.get_signal_endpoint()
        endpoints[pixel.uuid] = PixelSignalEndpoint(block_index, point_id)
    return endpoints


def _wire_between(
    build: RtGBuild,
    source_index: int,
    target_index: int,
    target_point: str,
) -> int:
    """Connect a signal source to a target using the reference Wire topology."""
    wire = RtGBlock("Wire", connections=[
        ["3", OR_OUTPUT, to_rtg_index(source_index)],
        ["1", target_point, to_rtg_index(target_index)],
    ])
    return build.add_block(wire)


def _add_delayers(
    build: RtGBuild,
    frame_durations: Sequence[float],
) -> List[int]:
    """Create exactly one configured Delayer for each logical frame."""
    indexes = []
    for frame_index, duration in enumerate(frame_durations):
        delayer = RtGBlock(
            "Delayer",
            properties={
                "DelayDeactivation": True,
                "Delay": duration,
                "RGB": [21, 95, 163],
                "Frame": frame_index,
            },
        )
        indexes.append(build.add_block(delayer))
    return indexes


def _connect_pixel_sources(
    build: RtGBuild,
    source_indexes: Sequence[int],
    endpoint: PixelSignalEndpoint,
) -> List[int]:
    """Connect frame sources to one physical pixel endpoint.

    For one source, a single Wire is enough. For two or more sources, the
    chain is left-associated and each Gate-OR is private to this pixel:

        source0 + source1 -> OR0
        OR0 + source2      -> OR1
        OR1 + source3      -> OR2
        ... -> pixel endpoint
    """
    if not source_indexes:
        return []

    created_indexes: List[int] = []
    if len(source_indexes) == 1:
        created_indexes.append(
            _wire_between(
                build,
                source_indexes[0],
                endpoint.block_index,
                endpoint.point_id,
            )
        )
        return created_indexes

    first_or = build.add_block(RtGBlock("Gate-OR"))
    created_indexes.append(first_or)
    _wire_between(build, source_indexes[0], first_or, OR_INPUT_A)
    _wire_between(build, source_indexes[1], first_or, OR_INPUT_B)
    current_output = first_or

    for source_index in source_indexes[2:]:
        next_or = build.add_block(RtGBlock("Gate-OR"))
        created_indexes.append(next_or)
        _wire_between(build, current_output, next_or, OR_INPUT_A)
        _wire_between(build, source_index, next_or, OR_INPUT_B)
        current_output = next_or

    _wire_between(build, current_output, endpoint.block_index, endpoint.point_id)
    return created_indexes


def build_signal_network(
    build: RtGBuild,
    frame_active_pixels: Mapping[int, Iterable[str]],
    pixel_inputs: Mapping[str, PixelSignalEndpoint],
    frame_durations: Sequence[float],
) -> Dict[str, List[int]]:
    """Append the physical frame signal network to an existing display build.

    ``pixel_inputs`` must resolve each UUID to a real block and numeric point
    in the display build. This function deliberately does not create Notes or
    synthetic PixelUUID properties.
    """
    if not frame_durations:
        raise ValueError("At least one frame duration is required")

    for pixel_uuid, endpoint in pixel_inputs.items():
        if endpoint.block_index < 0 or endpoint.block_index >= len(build.blocks):
            raise ValueError(f"Pixel {pixel_uuid} endpoint block is out of range")
        if build.blocks[endpoint.block_index].block_type != "Splitter_3":
            raise ValueError(
                f"Pixel {pixel_uuid} endpoint block must be Splitter_3, "
                f"got {build.blocks[endpoint.block_index].block_type}"
            )

    frame_count = len(frame_durations)
    unknown_frames = set(frame_active_pixels) - set(range(frame_count))
    if unknown_frames:
        raise ValueError(f"Frame indexes out of range: {sorted(unknown_frames)}")

    delayer_indexes = _add_delayers(build, frame_durations)
    active_frame_indexes: Dict[str, List[int]] = {
        pixel_uuid: [] for pixel_uuid in pixel_inputs
    }

    for frame_index in range(frame_count):
        for pixel_uuid in frame_active_pixels.get(frame_index, ()):
            if pixel_uuid not in pixel_inputs:
                raise ValueError(f"No physical input registered for pixel UUID {pixel_uuid}")
            active_frame_indexes[pixel_uuid].append(delayer_indexes[frame_index])

    for pixel_uuid, source_indexes in active_frame_indexes.items():
        _connect_pixel_sources(build, source_indexes, pixel_inputs[pixel_uuid])

    return active_frame_indexes


def validate_signal_connections(build: RtGBuild) -> List[str]:
    """Return topology errors for the generated numeric signal connections."""
    errors: List[str] = []
    for block_index, block in enumerate(build.blocks):
        for connection in block.connections:
            if len(connection) != 3:
                errors.append(f"block {block_index}: malformed connection")
                continue
            local_type, parent_point, parent_index = connection
            if not isinstance(parent_index, int) or not 1 <= parent_index <= len(build.blocks):
                errors.append(f"block {block_index}: invalid parent index {parent_index}")
            if not isinstance(local_type, str) or not isinstance(parent_point, str):
                errors.append(f"block {block_index}: non-string connection IDs")

    for block in build.blocks:
        if block.block_type in {"Gate-OR", "Wire", "Delayer"}:
            for connection in block.connections:
                if any(value in {"InputA", "InputB", "Output", "Input"} for value in connection):
                    errors.append(f"{block.block_type}: symbolic connection ID found")

    for block_index, block in enumerate(build.blocks):
        if block.block_type != "Wire" or len(block.connections) < 2:
            continue
        target_index = block.connections[1][2]
        if not isinstance(target_index, int) or not 1 <= target_index <= len(build.blocks):
            continue
        if build.blocks[target_index - 1].block_type == "Delayer":
            errors.append(f"Wire {block_index}: signal target cannot be a Delayer")
