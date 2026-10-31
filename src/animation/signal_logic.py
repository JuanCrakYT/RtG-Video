"""Physical materialization of the pre-validated RtG video signal plan.

No topology is discovered here.  ``src.video.analysis`` owns every logical
node and Wire; this module maps those identifiers onto physical RtG blocks.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple
from uuid import uuid4

from ..rtg.blocks import RtGBlock, RtGBuild, to_rtg_index
from ..rtg.cframe import CFrame
from ..rtg.format import validate_build_json
from ..video.analysis import (
    DELAYER_INPUT_POINT,
    DELAYER_OUTPUT_POINT,
    GATE_OR_INPUT_A_POINT,
    GATE_OR_INPUT_B_POINT,
    GATE_OR_OUTPUT_POINT,
    PlannedWire,
    VideoAnalysisResult,
    _delayer_id,
    _validate_signal_plan,
)


TIPOLOCAL_BUTTON = "1"
TIPOLOCAL_DELAYER = "2"
TIPOLOCAL_SPLITTER = "3"
TIPOLOCAL_WIRE = "3"
TIPOLOCAL_GATE_OR = "4"
WIRE_POINT_RIGHT = "4"


@dataclass(frozen=True)
class PixelSignalEndpoint:
    """The cloned Splitter_3 block that receives a colour-layer signal."""

    block_index: int
    point_id: str


@dataclass(frozen=True)
class MaterializedSignalPlan:
    """Indexes assigned while materializing one already-resolved analysis plan."""

    button_index: int
    node_indexes: Mapping[str, int]
    wire_indexes: Mapping[str, int]


def resolve_pixel_inputs(pixels: Iterable[object]) -> Dict[str, PixelSignalEndpoint]:
    """Resolve each cloned pixel UUID to its actual Splitter_3 input."""

    endpoints: Dict[str, PixelSignalEndpoint] = {}
    for pixel in pixels:
        block_index, point_id = pixel.get_signal_endpoint()
        endpoints[pixel.uuid] = PixelSignalEndpoint(block_index, point_id)
    return endpoints


def _base_attachment(build: RtGBuild, base_index: int) -> str:
    base = build.blocks[base_index]
    attachment_uuid = "{" + str(uuid4()) + "}"
    base.properties.setdefault("EphemeralAttachments", {})[attachment_uuid] = {
        "partName": "Base",
        "cframe": CFrame.identity().to_list(),
    }
    return attachment_uuid


def add_start_button(build: RtGBuild, base_index: int) -> int:
    """Add the Base-mounted Button which directly starts the first Delayer."""

    if not 0 <= base_index < len(build.blocks) or build.blocks[base_index].block_type != "Base":
        raise ValueError(f"Invalid Base index for start Button: {base_index}")
    return build.add_block(RtGBlock(
        "Button",
        connections=[
            ["1", "2", to_rtg_index(base_index)],
            ["3", "4", to_rtg_index(base_index)],
        ],
        properties={"RGB": [255, 0, 0]},
    ))


def add_physical_gate_or_table(build: RtGBuild, base_index: int, count: int) -> List[int]:
    """Add exactly the Gate-ORs calculated by analysis, physically on Base."""

    if count < 0:
        raise ValueError("Gate-OR count must be non-negative")
    if not 0 <= base_index < len(build.blocks) or build.blocks[base_index].block_type != "Base":
        raise ValueError(f"Invalid Base index for Gate-OR table: {base_index}")
    indexes = []
    for _ in range(count):
        attachment_uuid = _base_attachment(build, base_index)
        indexes.append(build.add_block(RtGBlock(
            "Gate-OR",
            connections=[[TIPOLOCAL_GATE_OR, attachment_uuid, to_rtg_index(base_index)]],
        )))
    return indexes


def _node_local_type(node_id: str) -> str:
    if node_id.startswith("delayer:"):
        return TIPOLOCAL_DELAYER
    if node_id.startswith("gate:"):
        return TIPOLOCAL_GATE_OR
    raise ValueError(f"Node {node_id!r} has no mutable local signal connection")


def _endpoint_index(node_id: str, node_indexes: Mapping[str, int], pixel_endpoints: Mapping[str, PixelSignalEndpoint]) -> int:
    if node_id in node_indexes:
        return node_indexes[node_id]
    if node_id in pixel_endpoints:
        return pixel_endpoints[node_id].block_index
    raise ValueError(f"[CONNECTION ERROR]\nComponent: Wire\nConnection point: endpoint\nExpected target: materialized node\nActual target: {node_id}\nReason: Missing physical binding.")


def _wire_connections(wire: PlannedWire, node_indexes, pixel_endpoints) -> List[List[object]]:
    return [
        [TIPOLOCAL_WIRE, wire.source_point, to_rtg_index(_endpoint_index(wire.source_node, node_indexes, pixel_endpoints))],
        [TIPOLOCAL_BUTTON, wire.target_point, to_rtg_index(_endpoint_index(wire.target_node, node_indexes, pixel_endpoints))],
    ]


def _planned_layout(build: RtGBuild, analysis: VideoAnalysisResult, gate_indexes: Sequence[int]):
    """Assign deterministic indexes without deciding new topology."""

    by_frame = defaultdict(list)
    for wire in analysis.wires:
        by_frame[wire.frame_index].append(wire)
    node_indexes = {gate.id: gate_indexes[index] for index, gate in enumerate(analysis.gate_ors)}
    wire_indexes = {}
    next_index = len(build.blocks)
    for frame_index in analysis.included_frame_indices:
        node_indexes[_delayer_id(frame_index)] = next_index
        next_index += 1
        for wire in by_frame[frame_index]:
            wire_indexes[wire.id] = next_index
            next_index += 1
    return node_indexes, wire_indexes, by_frame


def _gate_connections(analysis: VideoAnalysisResult, gate_id: str, wire_indexes: Mapping[str, int]) -> List[List[object]]:
    connections = []
    for wire in analysis.wires:
        wire_index = to_rtg_index(wire_indexes[wire.id])
        if wire.source_node == gate_id:
            connections.append([TIPOLOCAL_GATE_OR, wire.source_point, wire_index])
        if wire.target_node == gate_id:
            connections.append([TIPOLOCAL_GATE_OR, wire.target_point, wire_index])
    return connections


def materialize_signal_plan(
    build: RtGBuild,
    analysis: VideoAnalysisResult,
    pixel_endpoints: Mapping[str, PixelSignalEndpoint],
    *,
    base_index: int,
) -> MaterializedSignalPlan:
    """Materialize a pre-validated analysis plan in the required block order.

    Block order is Base/canvas (already present), Button, physical Gate-ORs,
    and then each Delayer immediately followed by that frame's Wires.  The
    method neither computes the OR tree nor discovers signal endpoints.
    """

    _validate_signal_plan(analysis)
    missing_layers = [layer.id for layer in analysis.pixel_layers if layer.id not in pixel_endpoints]
    if missing_layers:
        raise ValueError(
            "[CONNECTION ERROR]\nComponent: Splitter_3\nConnection point: input\n"
            "Expected target: cloned pixel layer\n"
            f"Actual target: {missing_layers[0]}\nReason: Build canvas does not contain the analysed colour layer."
        )
    if not analysis.included_frame_indices:
        return MaterializedSignalPlan(-1, {}, {})

    button_index = add_start_button(build, base_index)
    gate_indexes = add_physical_gate_or_table(build, base_index, len(analysis.gate_ors))
    node_indexes, wire_indexes, wires_by_frame = _planned_layout(build, analysis, gate_indexes)

    # Gate connections are known entirely from the plan and their reserved Wire
    # indexes, so they can be created before the timeline blocks.
    for gate, gate_index in zip(analysis.gate_ors, gate_indexes):
        build.blocks[gate_index].connections.extend(_gate_connections(analysis, gate.id, wire_indexes))

    incoming_timeline = {
        wire.target_node: wire
        for wire in analysis.wires
        if wire.purpose == "timeline"
    }
    for frame in (frame for frame in analysis.frames if frame.included_in_build):
        delayer_id = _delayer_id(frame.index)
        connections = []
        if delayer_id == analysis.start_target:
            connections.append([TIPOLOCAL_DELAYER, "2", to_rtg_index(button_index)])
        else:
            incoming = incoming_timeline[delayer_id]
            connections.append([TIPOLOCAL_DELAYER, DELAYER_INPUT_POINT, to_rtg_index(wire_indexes[incoming.id])])
        for wire in wires_by_frame[frame.index]:
            if wire.source_node == delayer_id:
                connections.append([TIPOLOCAL_DELAYER, wire.source_point, to_rtg_index(wire_indexes[wire.id])])
        actual_index = build.add_block(RtGBlock(
            "Delayer",
            connections=connections,
            properties={
                "DelayDeactivation": True,
                "Delay": frame.duration,
                "RGB": [21, 95, 163],
                "Frame": frame.index,
            },
        ))
        if actual_index != node_indexes[delayer_id]:
            raise RuntimeError("Internal layout drift while materializing Delayers")
        for wire in wires_by_frame[frame.index]:
            actual_wire_index = build.add_block(RtGBlock(
                "Wire", _wire_connections(wire, node_indexes, pixel_endpoints)
            ))
            if actual_wire_index != wire_indexes[wire.id]:
                raise RuntimeError("Internal layout drift while materializing Wires")

    # A Splitter_3 has one active signal input. Replace the template's old
    # parent instead of leaving a second, conflicting parent connection.
    for layer in analysis.pixel_layers:
        incoming = next(wire for wire in analysis.wires if wire.target_node == layer.id)
        endpoint = pixel_endpoints[layer.id]
        splitter = build.blocks[endpoint.block_index]
        if splitter.block_type != "Splitter_3" or not splitter.connections:
            raise ValueError(
                "[CONNECTION ERROR]\nComponent: Splitter_3\nConnection point: input\n"
                "Expected target: cloned Splitter_3 connection\n"
                f"Actual target: block {endpoint.block_index + 1}\nReason: Pixel endpoint is not a usable Splitter_3."
            )
        splitter.connections[0] = [endpoint.point_id, WIRE_POINT_RIGHT, to_rtg_index(wire_indexes[incoming.id])]

    materialized = MaterializedSignalPlan(button_index, dict(node_indexes), dict(wire_indexes))
    errors = validate_materialized_signal_plan(build, analysis, pixel_endpoints, materialized)
    if errors:
        raise ValueError("\n".join(errors))
    return materialized


def validate_materialized_signal_plan(build, analysis, pixel_endpoints, materialized) -> List[str]:
    """Verify that physical JSON represents precisely the already-planned wires."""

    errors = []
    valid_json, json_error = validate_build_json(build.to_json())
    if not valid_json:
        return [f"[CONNECTION ERROR]\nComponent: Build\nConnection point: JSON\nExpected target: valid RtG tuple\nActual target: invalid\nReason: {json_error}"]
    for frame in (frame for frame in analysis.frames if frame.included_in_build):
        index = materialized.node_indexes[_delayer_id(frame.index)]
        block = build.blocks[index]
        if block.block_type != "Delayer" or block.properties.get("Delay") != frame.duration:
            errors.append(f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: Delay\nExpected target: {frame.duration}\nActual target: {block.properties.get('Delay')}\nReason: Frame duration was not preserved.")
    for wire in analysis.wires:
        index = materialized.wire_indexes[wire.id]
        block = build.blocks[index]
        expected = _wire_connections(wire, materialized.node_indexes, pixel_endpoints)
        if block.block_type != "Wire" or block.connections != expected:
            errors.append(f"[CONNECTION ERROR]\nComponent: Wire\nConnection point: {wire.id}\nExpected target: {expected}\nActual target: {block.connections}\nReason: Materialized endpoints differ from analysis plan.")
    for layer in analysis.pixel_layers:
        endpoint = pixel_endpoints[layer.id]
        wire = next(item for item in analysis.wires if item.target_node == layer.id)
        expected = [endpoint.point_id, WIRE_POINT_RIGHT, to_rtg_index(materialized.wire_indexes[wire.id])]
        actual = build.blocks[endpoint.block_index].connections[0]
        if actual != expected:
            errors.append(f"[CONNECTION ERROR]\nComponent: Splitter_3\nConnection point: {endpoint.point_id}\nExpected target: {expected}\nActual target: {actual}\nReason: Pixel input was not replaced by the planned Wire.")
    return errors


def build_animation_timeline(build: RtGBuild, frame_durations: Sequence[float], base_index: int = 0, omit_last_frame: bool = False) -> List[int]:
    """Compatibility helper: create a direct Button-to-Delayer timeline.

    New video generation uses :func:`materialize_signal_plan`; this helper is
    retained for the static colour demo and always keeps delays individual.
    """

    durations = list(frame_durations[:-1] if omit_last_frame else frame_durations)
    if not durations:
        return []
    button_index = add_start_button(build, base_index)
    indexes = []
    for frame_index, duration in enumerate(durations):
        incoming = [TIPOLOCAL_DELAYER, "2", to_rtg_index(button_index)] if frame_index == 0 else [TIPOLOCAL_DELAYER, DELAYER_INPUT_POINT, to_rtg_index(len(build.blocks) + 1)]
        indexes.append(build.add_block(RtGBlock("Delayer", [incoming], {"DelayDeactivation": True, "Delay": float(duration), "RGB": [21, 95, 163], "Frame": frame_index})))
        if frame_index:
            previous = indexes[-2]
            wire_index = build.add_block(RtGBlock("Wire", [
                [TIPOLOCAL_WIRE, DELAYER_OUTPUT_POINT, to_rtg_index(previous)],
                [TIPOLOCAL_BUTTON, DELAYER_INPUT_POINT, to_rtg_index(indexes[-1])],
            ]))
            build.blocks[previous].connections.append([TIPOLOCAL_DELAYER, DELAYER_OUTPUT_POINT, to_rtg_index(wire_index)])
            build.blocks[indexes[-1]].connections[0] = [TIPOLOCAL_DELAYER, DELAYER_INPUT_POINT, to_rtg_index(wire_index)]
    return indexes


def validate_signal_connections(build: RtGBuild) -> List[str]:
    """Lightweight structural validator for callers without an analysis plan."""

    valid, error = validate_build_json(build.to_json())
    if not valid:
        return [error]
    errors = []
    for index, block in enumerate(build.blocks):
        if block.block_type == "Wire" and len(block.connections) != 2:
            errors.append(f"Wire {index + 1}: expected exactly two endpoint connections")
    return errors
