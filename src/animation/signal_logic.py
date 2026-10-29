"""Build physical RtG signal networks for animation frames.

The network owns one Delayer per frame. A pixel that appears in multiple
frames receives its own Gate-OR tree; no OR chain or Wire is shared between
pixels. Connection IDs are numeric because they are part of the RtG format.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple
from uuid import uuid4
from ..rtg.blocks import RtGBlock, RtGBuild, to_rtg_index
from ..rtg.cframe import CFrame


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

WIRE_POINT_LEFT = "2"
WIRE_POINT_RIGHT = "4"

GATE_OR_POINT_OUTPUT = "1"
GATE_OR_POINT_INPUT_A = "2"
GATE_OR_POINT_INPUT_B = "3"

# Delayer points (from functional builds and format)
DELAYER_POINT_OUTPUT = "1"   # Wire endpoint attaches to Delayer point 1
DELAYER_POINT_INPUT = "1"    # Wire endpoint attaches to Delayer point 1


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


def _base_attachment(build: RtGBuild, base_index: int) -> str:
    """Register a zero-offset UUID attachment on Base and return its UUID."""
    base = build.blocks[base_index]
    attachments = base.properties.setdefault("EphemeralAttachments", {})
    attachment_uuid = "{" + str(uuid4()) + "}"
    attachments[attachment_uuid] = {
        "partName": "Base",
        "cframe": CFrame.identity().to_list(),
    }
    return attachment_uuid


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


def _connect_splitter_input_to_wire(
    build: RtGBuild,
    endpoint: PixelSignalEndpoint,
    wire_index: int,
) -> None:
    """Replace the Splitter_3 input's previous parent with its signal Wire.

    The Splitter_3 input must reference the Wire itself. Keeping the old
    parent connection and appending another one leaves two parents on the
    same input and can make RtG reject the build.
    """
    splitter = build.blocks[endpoint.block_index]
    if not splitter.connections:
        raise ValueError(
            f"Splitter_3 at block {endpoint.block_index} has no input connection"
        )
    # The first connection in the pixel template is the Splitter_3 input.
    splitter.connections[0] = [
        TIPOLOCAL_SPLITTER,
        WIRE_POINT_RIGHT,
        to_rtg_index(wire_index),
    ]


def _add_delayers(
    build: RtGBuild,
    frame_durations: Sequence[float],
) -> List[int]:
    """Create exactly one configured Delayer for each logical frame."""
    indexes = []
    for frame_index, duration in enumerate(frame_durations):
        delayer = RtGBlock(
            "Delayer",
            connections=[],
            properties={
                "DelayDeactivation": True,
                "Delay": duration,
                "RGB": [21, 95, 163],
                "Frame": frame_index,
            },
        )
        indexes.append(build.add_block(delayer))
    return indexes


def build_animation_timeline(
    build: RtGBuild,
    frame_durations: Sequence[float],
    base_index: int = 0,
) -> List[int]:
    """Append one Delayer per frame in temporal order.

    Timeline chain:
    - First Delayer connects to a UUID attachment on Base.
    - Each later Delayer connects via a Wire from the previous Delayer.
    """
    if not frame_durations:
        raise ValueError("At least one frame duration is required")

    delayer_indexes = _add_delayers(build, frame_durations)

    # The first Delayer must attach directly to Base, using a Base UUID
    # attachment just like other blocks physically mounted to the build.
    if not 0 <= base_index < len(build.blocks):
        raise ValueError(f"Invalid Base index: {base_index}")
    if build.blocks[base_index].block_type != "Base":
        raise ValueError(
            f"Timeline Base index {base_index} refers to "
            f"{build.blocks[base_index].block_type}, not Base"
        )
    base_attachment_uuid = _base_attachment(build, base_index)
    build.blocks[delayer_indexes[0]].connections.append([
        TIPOLOCAL_DELAYER, base_attachment_uuid, to_rtg_index(base_index)
    ])

    # Create subsequent Delayers, each connected via a Wire from previous Delayer
    for frame_index in range(1, len(frame_durations)):
        # Create Wire connecting previous Delayer to this Delayer
        wire_index = _wire_between(
            build,
            delayer_indexes[frame_index - 1], DELAYER_POINT_OUTPUT,
            delayer_indexes[frame_index], DELAYER_POINT_INPUT,
        )
        # Both Delayers must reference the corresponding Wire endpoint.
        # In game builds the source Delayer attaches to Wire point 4,
        # while the receiving Delayer attaches to Wire point 2.
        build.blocks[delayer_indexes[frame_index - 1]].connections.append([
            TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(wire_index),
        ])
        build.blocks[delayer_indexes[frame_index]].connections.append([
            TIPOLOCAL_DELAYER, WIRE_POINT_LEFT, to_rtg_index(wire_index),
        ])

    return delayer_indexes


def add_start_button(
    build: RtGBuild,
    base_index: int,
) -> int:
    """Create a start Button physically mounted on the Base."""
    # Button has two physical endpoints; each uses its own Base UUID attachment.
    endpoint_a = _base_attachment(build, base_index)
    endpoint_b = _base_attachment(build, base_index)
    button = RtGBlock(
        "Button",
        connections=[
            [TIPOLOCAL_BUTTON, endpoint_a, to_rtg_index(base_index)],
            [TIPOLOCAL_BUTTON, endpoint_b, to_rtg_index(base_index)],
        ],
        properties={"RGB": [255, 0, 0]},
    )
    return build.add_block(button)


def add_physical_gate_or_table(
    build: RtGBuild,
    base_index: int,
    count: int,
) -> List[int]:
    """Create Gate-OR blocks physically attached to Base in a vertical stack.

    Gate-OR points: 1=Output (Front), 2=InputA (Left), 3=InputB (Right).
    """
    indexes = []
    for i in range(count):
        attachment_uuid = _base_attachment(build, base_index)
        gate = RtGBlock(
            "Gate-OR",
            connections=[
                [TIPOLOCAL_GATE_OR, attachment_uuid, to_rtg_index(base_index)],
            ],
        )
        indexes.append(build.add_block(gate))
    return indexes


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
            endpoint.block_index, "1",
        )
        # The source Delayer references the Wire's output-side point 4.
        build.blocks[source_indexes[0]].connections.append([
            TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(wire_index)
        ])
        _connect_splitter_input_to_wire(build, endpoint, wire_index)
        return [wire_index]

    # Convert to sets for O(1) lookup
    source_index_set = set(source_indexes)
    gate_or_index_set = set(physical_map.values())

    def get_source_tipo_local(source_index: int) -> str:
        """Return the correct TipoLocal for a source block index."""
        if source_index in gate_or_index_set:
            return TIPOLOCAL_GATE_OR
        return TIPOLOCAL_DELAYER

    def get_source_output_point(source_index: int) -> str:
        """Return the correct output point for a source block index."""
        # Both Delayer and Gate-OR use point "1" for output
        return "1"

    def resolve(node: int) -> int:
        info = or_tree[node]
        if info.is_leaf:
            return source_indexes[info.source_frame]
        gate_index = physical_map[node]
        left_index = resolve(info.child_a)
        right_index = resolve(info.child_b)
        # Left source -> Wire -> Gate-OR InputA
        left_tipo = get_source_tipo_local(left_index)
        left_point = get_source_output_point(left_index)
        wire_index = _wire_between(
            build,
            left_index, left_point,
            gate_index, GATE_OR_POINT_INPUT_A,
        )
        # Reciprocal connections refer to the Wire's left/right endpoints.
        if build.blocks[left_index].block_type == "Delayer":
            build.blocks[left_index].connections.append([
                TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(wire_index)
            ])
        # Right source -> Wire -> Gate-OR InputB
        right_tipo = get_source_tipo_local(right_index)
        right_point = get_source_output_point(right_index)
        wire_index = _wire_between(
            build,
            right_index, right_point,
            gate_index, GATE_OR_POINT_INPUT_B,
        )
        # Reciprocal connections refer to the Wire's left/right endpoints.
        if build.blocks[right_index].block_type == "Delayer":
            build.blocks[right_index].connections.append([
                TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(wire_index)
            ])
        return gate_index

    root_index = resolve(len(or_tree) - 1)
    # Root Gate-OR output -> Wire -> Pixel endpoint (Splitter_3)
    wire_index = _wire_between(
        build,
        root_index, GATE_OR_POINT_OUTPUT,
        endpoint.block_index, "1",
    )
    # Gate-OR blocks in in-game examples do not store reciprocal Wire entries.
    _connect_splitter_input_to_wire(build, endpoint, wire_index)
    return []


def build_signal_network(
    build: RtGBuild,
    pixel_color_frames: Dict[str, Dict[Tuple[int, int, int], List[int]]],
    pixel_inputs: Mapping[str, PixelSignalEndpoint],
    frame_durations: Sequence[float],
    gate_or_pool: Sequence[int] = (),
    timeline_delayer_indexes: Sequence[int] = (),
) -> Dict[str, Dict[Tuple[int, int, int], List[int]]]:
    """Append the physical frame signal network to an existing display build.

    The new architecture uses an intermediate logical table:
    ``pixel_color_frames`` maps pixel_uuid -> color -> list of frame delayer indexes.
    
    Each (pixel, color) combination gets its own independent OR tree.
    This is different from the old architecture which grouped by pixel only.

    ``gate_or_pool`` should contain the pre-generated physical Gate-OR indexes.
    ``timeline_delayer_indexes`` should contain the Delayer indexes created by
    ``build_animation_timeline``. If not provided, new Delayers will be created.
    The logical trees reuse those objects instead of creating new blocks.
    """
    if not frame_durations:
        raise ValueError("At least one frame duration is required")

    if timeline_delayer_indexes:
        delayer_indexes = list(timeline_delayer_indexes)
    else:
        delayer_indexes = _add_delayers(build, frame_durations)

    # Flatten all (pixel, color) combinations into a list of logical trees to build
    # Each entry: (pixel_uuid, color, source_delayer_indexes)
    logical_trees = []
    for pixel_uuid, color_frames_map in pixel_color_frames.items():
        for color, source_indexes in color_frames_map.items():
            if source_indexes:
                logical_trees.append((pixel_uuid, color, source_indexes))

    # Allocate Gate-ORs from pool for all logical trees
    pool = list(gate_or_pool)
    tree_allocations = []  # List of (pixel_uuid, color, or_tree, physical_map, endpoint)
    
    for pixel_uuid, color, source_indexes in logical_trees:
        or_tree = _allocate_pixel_or_tree(source_indexes)
        internal_nodes = _get_internal_nodes_level_order(or_tree)
        if len(internal_nodes) > len(pool):
            raise ValueError(
                f"Not enough physical Gate-ORs for pixel {pixel_uuid} color {color}: "
                f"need {len(internal_nodes)}, have {len(pool)}"
            )
        physical_map = {node_index: pool.pop(0) for node_index in internal_nodes}
        endpoint = pixel_inputs[pixel_uuid]
        tree_allocations.append((pixel_uuid, color, or_tree, physical_map, endpoint))

    # Build all trees
    for pixel_uuid, color, source_indexes, or_tree, physical_map, endpoint in [
        (p, c, next(s for p2, c2, s in logical_trees if p2 == p and c2 == c), ot, pm, ep)
        for p, c, ot, pm, ep in tree_allocations
    ]:
        _connect_pixel_sources(
            build,
            source_indexes,
            endpoint,
            or_tree,
            physical_map,
        )

    return pixel_color_frames


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

    # A Wire must be referenced by both blocks it connects. Checking only
    # the Wire's own parent indices misses the common failure where objects
    # are exported but their reciprocal connections were never written.
    for wire_index, wire in enumerate(build.blocks):
        if wire.block_type != "Wire":
            continue
        if len(wire.connections) != 2:
            errors.append(
                f"Wire {wire_index + 1}: expected exactly 2 endpoint connections, "
                f"found {len(wire.connections)}"
            )
            continue
        for endpoint in wire.connections:
            if len(endpoint) != 3:
                continue
            endpoint_index = endpoint[2]
            if not isinstance(endpoint_index, int) or not 1 <= endpoint_index <= len(build.blocks):
                continue
            connected_block = build.blocks[endpoint_index - 1]
            # Gate-OR blocks in the in-game examples keep their connections
            # empty; Delayers and Splitter_3 store the reciprocal Wire entry.
            if connected_block.block_type not in {"Delayer", "Splitter_3", "Wire"}:
                continue
            if not any(
                len(reciprocal) == 3 and reciprocal[2] == wire_index + 1
                for reciprocal in connected_block.connections
            ):
                errors.append(
                    f"Wire {wire_index + 1}: endpoint block {endpoint_index} "
                    "does not reference this Wire"
                )

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
                    f"Wire {block_index + 1}: Delayer endpoint must use point 1"
                )

    return errors