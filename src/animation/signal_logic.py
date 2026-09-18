"""Build physical RtG signal networks for animation frames.

The network owns one Delayer per frame. A pixel that appears in multiple
frames receives its own Gate-OR tree; no OR chain or Wire is shared between
pixels. Connection IDs are numeric because they are part of the RtG format.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

from ..rtg.blocks import RtGBlock, RtGBuild, to_rtg_index


# TipoLocal values per object type (from RtG_Save_Format_Specification v0.406)
TIPOLOCAL_BASE = "3"
TIPOLOCAL_PART = "1"
TIPOLOCAL_CONNECTOR = "5"
TIPOLOCAL_BUTTON = "1"
TIPOLOCAL_SWITCH = "1"
TIPOLOCAL_INPUT_SENSOR = "2"
TIPOLOCAL_DELAYER = "2"
TIPOLOCAL_WIRE = "3"
TIPOLOCAL_GATE_OR = "4"
TIPOLOCAL_GATE_AND = "4"
TIPOLOCAL_GATE_NOT = "4"
TIPOLOCAL_SPLITTER = "3"
TIPOLOCAL_SERVO = "1"
TIPOLOCAL_GYRO = "1"
TIPOLOCAL_REMOTE_BUTTON = "1"

# Connection point IDs per object (from obj_ids-spanish.md)
BASE_POINT_LEFT = "1"
BASE_POINT_RIGHT = "2"
BASE_POINT_FRONT = "4"
BASE_POINT_TOP = "5"
BASE_POINT_BOTTOM = "6"

BUTTON_POINT_OUTPUT = "1"

WIRE_POINT_LEFT = "2"
WIRE_POINT_RIGHT = "4"

GATE_OR_POINT_OUTPUT = "1"
GATE_OR_POINT_INPUT_A = "2"
GATE_OR_POINT_INPUT_B = "3"

# Delayer points not documented; assume "1" for output based on convention
DELAYER_POINT_OUTPUT = "1"


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
    source_point: str,
    target_index: int,
    target_point: str,
) -> int:
    """Connect a signal source to a target using a Wire block.

    Wire connections are fixed per RtG format:
    - First connection (input side): ["3", source_point, source_index]
    - Second connection (output side): ["1", target_point, target_index]
    """
    wire = RtGBlock("Wire", connections=[
        ["3", source_point, to_rtg_index(source_index)],
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
    """Add one red Button wired to the Base physical mount and output port.

    Button (TipoLocal "1") connects to Base (TipoLocal "3"):
    - Physical mount: Base point 4 (Front)
    - Signal output: Base point 2 (Right) - carries the button signal
    """
    return build.add_block(
        RtGBlock(
            "Button",
            connections=[
                [TIPOLOCAL_BASE, BASE_POINT_FRONT, to_rtg_index(base_index)],  # physical mount
                [TIPOLOCAL_BASE, BASE_POINT_RIGHT, to_rtg_index(base_index)],   # signal output
            ],
            properties={"RGB": [255, 0, 0]},
        )
    )


def add_physical_gate_or_table(
    build: RtGBuild,
    base_index: int,
    gate_count: int,
) -> List[int]:
    """Add a physical Gate-OR table below Base without signal connections.

    Each Gate-OR (TipoLocal "4") mounts to Base (TipoLocal "3") at point 4 (Front)
    or to previous Gate-OR at point 2 (Left) for vertical stacking.
    """
    if gate_count < 0:
        raise ValueError("Gate-OR table size cannot be negative")

    gate_indexes: List[int] = []
    previous_index = None
    for _ in range(gate_count):
        parent_index = base_index if previous_index is None else previous_index
        parent_point = BASE_POINT_FRONT if previous_index is None else WIRE_POINT_LEFT
        gate_indexes.append(
            build.add_block(
                RtGBlock(
                    "Gate-OR",
                    connections=[[TIPOLOCAL_BASE, parent_point, to_rtg_index(parent_index)]],
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
    """Append one Delayer per frame in temporal order.

    Timeline chain:
    - First Delayer connects to Start Button (TipoLocal "1") at Button's output point (1)
    - Each later Delayer connects via a Wire from previous Delayer
    - Final Delayer gets an output Wire for the signal network
    """
    if not frame_durations:
        raise ValueError("At least one frame duration is required")

    delayer_indexes: List[int] = []

    # Create first Delayer connected to Start Button
    delayer_index = build.add_block(
        RtGBlock(
            "Delayer",
            connections=[["1", BUTTON_POINT_OUTPUT, to_rtg_index(start_source_index)]],
            properties={
                "DelayDeactivation": True,
                "Delay": frame_durations[0],
                "RGB": [21, 95, 163],
                "Frame": 0,
            },
        )
    )
    delayer_indexes.append(delayer_index)

    # Create subsequent Delayers, each connected via a Wire from previous Delayer
    for frame_index in range(1, len(frame_durations)):
        duration = frame_durations[frame_index]

        # Create Wire connecting previous Delayer to this Delayer
        # Wire: ["3", DELAYER_POINT_OUTPUT, prev_delayer], ["1", WIRE_POINT_RIGHT, this_delayer]
        wire_index = _wire_between(
            build,
            delayer_indexes[-1], DELAYER_POINT_OUTPUT,
            len(build.blocks) + 1, WIRE_POINT_RIGHT,
        )

        # Create this Delayer connecting to the Wire we just created
        # Delayer connects to Wire (Wire's TipoLocal is "3")
        build.add_block(
            RtGBlock(
                "Delayer",
                connections=[["3", WIRE_POINT_RIGHT, to_rtg_index(wire_index)]],
                properties={
                    "DelayDeactivation": True,
                    "Delay": duration,
                    "RGB": [21, 95, 163],
                    "Frame": frame_index,
                },
            )
        )
        delayer_indexes.append(len(build.blocks) - 1)

    # Final output Wire from last Delayer for signal network
    # This Wire connects last Delayer to... (target will be added by signal network)
    # We create it here so the timeline is complete, but signal network will connect to it
    # Actually, signal network connects from Delayers directly via new Wires
    # So we don't need a dangling wire. The last Delayer's output will be used by signal network.

    return delayer_indexes


def _allocate_pixel_or_tree(sources: Sequence[int]) -> List[GateORInfo]:
    """Allocate a balanced binary logical tree for the given frame sources.

    Returns nodes in post-order (leaves first, then internal nodes bottom-up).
    """
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


def _get_internal_nodes_level_order(or_tree: Sequence[GateORInfo]) -> List[int]:
    """Return internal node indices in level-order (breadth-first) for correct physical gate assignment."""
    if not or_tree:
        return []

    # Compute depth of each node
    depths: Dict[int, int] = {}

    def compute_depth(node: int) -> int:
        if node in depths:
            return depths[node]
        info = or_tree[node]
        if info.is_leaf:
            depths[node] = 0
        else:
            depths[node] = 1 + max(compute_depth(info.child_a), compute_depth(info.child_b))
        return depths[node]

    for i in range(len(or_tree)):
        compute_depth(i)

    # Internal nodes sorted by depth (level-order), then by index for stability
    internal_nodes = [i for i, node in enumerate(or_tree) if not node.is_leaf]
    internal_nodes.sort(key=lambda n: (depths[n], n))
    return internal_nodes


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
        wire_index = _wire_between(
            build,
            source_indexes[0], DELAYER_POINT_OUTPUT,
            endpoint.block_index, endpoint.point_id,
        )
        build.blocks[source_indexes[0]].connections.append(["3", WIRE_POINT_LEFT, to_rtg_index(wire_index)])
        return [wire_index]

    def resolve(node: int) -> int:
        info = or_tree[node]
        if info.is_leaf:
            return source_indexes[info.source_frame]
        gate_index = physical_map[node]
        left_index = resolve(info.child_a)
        right_index = resolve(info.child_b)
        # Left source -> Wire -> Gate-OR InputA
        wire_index = _wire_between(
            build,
            left_index, DELAYER_POINT_OUTPUT,
            gate_index, GATE_OR_POINT_INPUT_A,
        )
        build.blocks[left_index].connections.append(["3", WIRE_POINT_LEFT, to_rtg_index(wire_index)])
        # Gate-OR connects to this Wire (Wire's TipoLocal "3", Gate-OR point "2" = InputA)
        build.blocks[gate_index].connections.append(["3", GATE_OR_POINT_INPUT_A, to_rtg_index(wire_index)])
        # Right source -> Wire -> Gate-OR InputB
        wire_index = _wire_between(
            build,
            right_index, DELAYER_POINT_OUTPUT,
            gate_index, GATE_OR_POINT_INPUT_B,
        )
        build.blocks[right_index].connections.append(["3", WIRE_POINT_LEFT, to_rtg_index(wire_index)])
        # Gate-OR connects to this Wire (Wire's TipoLocal "3", Gate-OR point "3" = InputB)
        build.blocks[gate_index].connections.append(["3", GATE_OR_POINT_INPUT_B, to_rtg_index(wire_index)])
        return gate_index

    root_index = resolve(len(or_tree) - 1)
    # Root Gate-OR output -> Wire -> Pixel endpoint (Splitter_3)
    wire_index = _wire_between(
        build,
        root_index, GATE_OR_POINT_OUTPUT,
        endpoint.block_index, endpoint.point_id,
    )
    build.blocks[root_index].connections.append(["3", WIRE_POINT_LEFT, to_rtg_index(wire_index)])
    return []


def build_signal_network(
    build: RtGBuild,
    frame_active_pixels: Mapping[int, Iterable[str]],
    pixel_inputs: Mapping[str, PixelSignalEndpoint],
    frame_durations: Sequence[float],
    gate_or_pool: Sequence[int] = (),
    timeline_delayer_indexes: Sequence[int] = (),
) -> Dict[str, List[int]]:
    """Append the physical frame signal network to an existing display build.

    ``gate_or_pool`` should contain the pre-generated physical Gate-OR indexes.
    ``timeline_delayer_indexes`` should contain the Delayer indexes created by
    ``build_animation_timeline``. If not provided, new Delayers will be created.
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

    # Use timeline Delayers if provided, otherwise create new ones
    if timeline_delayer_indexes:
        if len(timeline_delayer_indexes) != frame_count:
            raise ValueError(
                f"Expected {frame_count} timeline Delayers, got {len(timeline_delayer_indexes)}"
            )
        delayer_indexes = list(timeline_delayer_indexes)
    else:
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
        internal_nodes = _get_internal_nodes_level_order(or_tree)
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
            if target_point != "4":
                errors.append(
                    f"Wire {block_index}: Delayer target must use point 4"
                )

    return errors
