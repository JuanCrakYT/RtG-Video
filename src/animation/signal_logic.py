"""Build physical RtG signal networks for animation frames.

The network owns one Delayer per frame. A pixel that appears in multiple
frames receives its own Gate-OR tree; no OR chain or Wire is shared between
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


@dataclass
class GateORInfo:
    """Logical information about a pre-generated Gate-OR object."""

    source_frame: int = -1
    child_a: int = -1
    child_b: int = -1

    @property
    def is_leaf(self) -> bool:
        return self.source_frame >= 0


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


def add_start_button(build: RtGBuild, base_index: int) -> int:
    """Add one red Button wired to the Base physical and output ports."""
    return build.add_block(
        RtGBlock(
            "Button",
            connections=[
                ["1", "2", to_rtg_index(base_index)],
                ["3", "4", to_rtg_index(base_index)],
            ],
            properties={"RGB": [255, 0, 0]},
        )
    )


def add_physical_gate_or_table(
    build: RtGBuild,
    base_index: int,
    gate_count: int,
) -> List[int]:
    """Add a physical Gate-OR table below Base without signal connections."""
    if gate_count < 0:
        raise ValueError("Gate-OR table size cannot be negative")

    gate_indexes: List[int] = []
    previous_index = None
    for _ in range(gate_count):
        parent_index = base_index if previous_index is None else previous_index
        parent_point = "4" if previous_index is None else "2"
        gate_indexes.append(
            build.add_block(
                RtGBlock(
                    "Gate-OR",
                    connections=[["4", parent_point, to_rtg_index(parent_index)]],
                )
            )
        )
        previous_index = gate_indexes[-1]

    return gate_indexes


def build_animation_timeline(
    build: RtGBuild,
    frame_durations: Sequence[float],
    start_source_index: int = 0,
) -> List[int]:
    """Append one Delayer/Wire pair per frame in temporal order.

    The first Delayer is attached to Base point 2. Each later Delayer is
    reached from the previous Delayer through its preceding Wire.
    """
    if not frame_durations:
        raise ValueError("At least one frame duration is required")

    delayer_indexes: List[int] = []
    previous_wire_index = None
    for frame_index, duration in enumerate(frame_durations):
        delayer_connections = (
            [["2", "2", to_rtg_index(start_source_index)]]
            if previous_wire_index is None
            else [["2", "4", to_rtg_index(previous_wire_index)]]
        )
        delayer_index = build.add_block(
            RtGBlock(
                "Delayer",
                connections=delayer_connections,
                properties={
                    "DelayDeactivation": True,
                    "Delay": duration,
                    "RGB": [21, 95, 163],
                    "Frame": frame_index,
                },
            )
        )
        delayer_indexes.append(delayer_index)

        wire_index = build.add_block(
            RtGBlock(
                "Wire",
                connections=[["3", OR_OUTPUT, to_rtg_index(delayer_index)]],
            )
        )
        previous_wire_index = wire_index

    return delayer_indexes


def _allocate_pixel_or_tree(sources: Sequence[int]) -> List[GateORInfo]:
    """Allocate a balanced binary logical tree for the given frame sources."""
    if len(sources) <= 1:
        return []

    nodes: List[GateORInfo] = []

    def build_tree(source_indices: Sequence[int]) -> int:
        if len(source_indices) == 1:
            gate = GateORInfo(source_frame=source_indices[0])
            nodes.append(gate)
            return len(nodes) - 1
        mid = len(source_indices) // 2
        left = build_tree(source_indices[:mid])
        right = build_tree(source_indices[mid:])
        gate = GateORInfo()
        gate.child_a = left
        gate.child_b = right
        nodes.append(gate)
        return len(nodes) - 1

    build_tree(list(range(len(sources))))
    return nodes


def _connect_pixel_sources(
    build: RtGBuild,
    source_indexes: Sequence[int],
    endpoint: PixelSignalEndpoint,
    or_tree: Sequence[GateORInfo],
    physical_map: Mapping[int, int],
) -> List[int]:
    """Connect frame sources to one physical pixel endpoint using pre-built Gate-ORs."""
    if not source_indexes:
        return []

    if len(source_indexes) == 1:
        return [
            _wire_between(
                build,
                source_indexes[0],
                endpoint.block_index,
                endpoint.point_id,
            )
        ]

    def resolve(node: int) -> int:
        info = or_tree[node]
        if info.is_leaf:
            return source_indexes[info.source_frame]
        gate_index = physical_map[node]
        left_index = resolve(info.child_a)
        right_index = resolve(info.child_b)
        _wire_between(build, left_index, gate_index, OR_INPUT_A)
        _wire_between(build, right_index, gate_index, OR_INPUT_B)
        return gate_index

    root_index = resolve(len(or_tree) - 1)
    _wire_between(build, root_index, endpoint.block_index, endpoint.point_id)
    return []


def build_signal_network(
    build: RtGBuild,
    frame_active_pixels: Mapping[int, Iterable[str]],
    pixel_inputs: Mapping[str, PixelSignalEndpoint],
    frame_durations: Sequence[float],
    gate_or_pool: Sequence[int] = (),
) -> Dict[str, List[int]]:
    """Append the physical frame signal network to an existing display build.

    ``gate_or_pool`` should contain the pre-generated physical Gate-OR indexes.
    The logical trees reuse those objects instead of creating new blocks.
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

    pool = list(gate_or_pool)
    or_allocations: Dict[str, tuple] = {}
    for pixel_uuid, source_indexes in active_frame_indexes.items():
        or_tree = _allocate_pixel_or_tree(source_indexes)
        internal_nodes = [i for i, node in enumerate(or_tree) if not node.is_leaf]
        if len(internal_nodes) > len(pool):
            raise ValueError(
                f"Not enough physical Gate-ORs for pixel {pixel_uuid}: "
                f"need {len(internal_nodes)}, have {len(pool)}"
            )
        physical_map = {node_index: pool.pop(0) for node_index in internal_nodes}
        or_allocations[pixel_uuid] = (or_tree, physical_map)

    for pixel_uuid, endpoint in pixel_inputs.items():
        source_indexes = active_frame_indexes[pixel_uuid]
        if not source_indexes:
            continue
        or_tree, physical_map = or_allocations[pixel_uuid]
        _connect_pixel_sources(
            build,
            source_indexes,
            endpoint,
            or_tree,
            physical_map,
        )

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
            target_point = block.connections[1][1]
            if target_point != "1":
                errors.append(
                    f"Wire {block_index}: Delayer target must use point 1"
                )
