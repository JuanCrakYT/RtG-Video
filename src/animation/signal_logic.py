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
    anchor_block_index: int
    anchor_point_id: str


@dataclass(frozen=True)
class MaterializedSignalPlan:
    """Indexes assigned while materializing one already-resolved analysis plan."""

    button_index: int
    node_indexes: Mapping[str, int]
    wire_indexes: Mapping[str, int]
    timeline_destinations: Mapping[str, PlannedWire]
    wire_source_links: Mapping[str, Tuple[str, int]]


def resolve_pixel_inputs(pixels: Iterable[object]) -> Dict[str, PixelSignalEndpoint]:
    """Resolve each cloned pixel UUID to its actual Splitter_3 input."""

    endpoints: Dict[str, PixelSignalEndpoint] = {}
    for pixel in pixels:
        block_index, point_id = pixel.get_signal_endpoint()
        splitter = pixel.blocks[
            next(
                template_index
                for template_index, global_index in pixel.block_indices.items()
                if global_index - 1 == block_index
            ) - 1
        ]
        original_input = splitter.connections[0]
        anchor_point, anchor_index = original_input[1], original_input[2]
        if not isinstance(anchor_point, str) or not isinstance(anchor_index, int):
            raise ValueError(
                f"Pixel {pixel.uuid} Splitter_3 input must declare a physical anchor"
            )
        endpoints[pixel.uuid] = PixelSignalEndpoint(
            block_index, point_id, anchor_index - 1, anchor_point
        )
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


def _wire_connections(
    wire: PlannedWire, node_indexes, pixel_endpoints, timeline_destinations=None,
    source_link: Tuple[str, int] | None = None,
) -> List[List[object]]:
    source_point, source_index = source_link or (
        wire.source_point,
        _endpoint_index(wire.source_node, node_indexes, pixel_endpoints),
    )
    if wire.purpose == "timeline":
        connections = [[
            TIPOLOCAL_WIRE,
            source_point, to_rtg_index(source_index),
        ]]
        destination = (timeline_destinations or {}).get(wire.id)
        if destination is None:
            return connections
        if destination.target_node in pixel_endpoints:
            endpoint = pixel_endpoints[destination.target_node]
            connections.append([
                TIPOLOCAL_BUTTON, endpoint.anchor_point_id,
                to_rtg_index(endpoint.anchor_block_index),
            ])
        else:
            connections.append([
                TIPOLOCAL_BUTTON, destination.target_point,
                to_rtg_index(_endpoint_index(destination.target_node, node_indexes, pixel_endpoints)),
            ])
        return connections
    # The Splitter_3 points to the Wire.  The Wire itself remains physically
    # anchored to the Stick/RemoteButton that was the Splitter's old parent.
    if wire.target_node in pixel_endpoints:
        endpoint = pixel_endpoints[wire.target_node]
        return [
            [TIPOLOCAL_WIRE, endpoint.anchor_point_id, to_rtg_index(endpoint.anchor_block_index)],
            [TIPOLOCAL_BUTTON, wire.source_point,
             to_rtg_index(source_index)],
        ]
    return [
        [TIPOLOCAL_WIRE, source_point, to_rtg_index(source_index)],
        [TIPOLOCAL_BUTTON, wire.target_point, to_rtg_index(_endpoint_index(wire.target_node, node_indexes, pixel_endpoints))],
    ]


def _planned_layout(build: RtGBuild, analysis: VideoAnalysisResult, gate_indexes: Sequence[int], skipped_wire_ids):
    """Assign deterministic indexes without deciding new topology."""

    by_frame = defaultdict(list)
    for wire in analysis.wires:
        by_frame[wire.frame_index].append(wire)
    # A temporal Wire is emitted after the frame's signal Wires so it can be
    # attached to the first signal Wire without changing any other fan-out.
    for wires in by_frame.values():
        wires.sort(key=lambda wire: wire.purpose == "timeline")
    node_indexes = {gate.id: gate_indexes[index] for index, gate in enumerate(analysis.gate_ors)}
    wire_indexes = {}
    next_index = len(build.blocks)
    for frame_index in analysis.included_frame_indices:
        node_indexes[_delayer_id(frame_index)] = next_index
        next_index += 1
        for wire in by_frame[frame_index]:
            if wire.id in skipped_wire_ids:
                continue
            wire_indexes[wire.id] = next_index
            next_index += 1
    return node_indexes, wire_indexes, by_frame


def _skipped_timeline_wire_ids(analysis: VideoAnalysisResult) -> set:
    """Timeline Wires are always materialized as explicit fan-out destinations."""

    return set()


def _materialize_delayer_fanout(
    build: RtGBuild,
    analysis: VideoAnalysisResult,
    node_indexes: Mapping[str, int],
    wire_indexes: Mapping[str, int],
    wire_source_links: Dict[str, Tuple[str, int]],
    pixel_endpoints: Mapping[str, PixelSignalEndpoint],
) -> None:
    """Fan out each Delayer through Splitter_3 blocks without sharing output ports.

    A Wire output point can have only one child in the saved RtG builds.  The
    old implementation chained several pixel Wires through point 4 while the
    corresponding pixel Splitter_3 also referenced that same point.  A
    Splitter_3 tree gives every outgoing signal its own physical output port.
    """

    output_points = ("5", "7", "9")

    def add_splitter(parent_index: int, parent_point: str) -> int:
        # Reserve the two indexes first so both sides of the connection can
        # reference each other using RtG's one-based block indexes.
        input_wire_index = build.add_block(RtGBlock(
            "Wire",
            connections=[
                [TIPOLOCAL_WIRE, parent_point, to_rtg_index(parent_index)],
            ],
        ))
        splitter_index = build.add_block(RtGBlock(
            "Splitter_3",
            connections=[["3", WIRE_POINT_RIGHT, to_rtg_index(input_wire_index)]],
        ))
        build.blocks[input_wire_index].connections.append([
            TIPOLOCAL_BUTTON, "3", to_rtg_index(splitter_index)
        ])
        return splitter_index

    def assign_outputs(splitter_index: int, pending: List[PlannedWire]) -> None:
        # Keep one output free for a child Splitter_3 whenever more than three
        # destinations remain.  Every physical output point is used once.
        if len(pending) <= len(output_points):
            for point, wire in zip(output_points, pending):
                source_link = (point, splitter_index)
                wire_source_links[wire.id] = source_link
                build.blocks[wire_indexes[wire.id]].connections = _wire_connections(
                    wire, node_indexes, pixel_endpoints, {}, source_link
                )
            return

        for point, wire in zip(output_points[:2], pending[:2]):
            source_link = (point, splitter_index)
            wire_source_links[wire.id] = source_link
            build.blocks[wire_indexes[wire.id]].connections = _wire_connections(
                wire, node_indexes, pixel_endpoints, {}, source_link
            )

        child_input_point = output_points[2]
        child_splitter = add_splitter(splitter_index, child_input_point)
        assign_outputs(child_splitter, pending[2:])

    for frame_index in analysis.included_frame_indices:
        delayer_id = _delayer_id(frame_index)
        outgoing = [
            wire for wire in analysis.wires
            if wire.source_node == delayer_id
        ]
        if len(outgoing) <= 1:
            continue

        root_splitter = add_splitter(
            node_indexes[delayer_id], DELAYER_OUTPUT_POINT
        )
        assign_outputs(root_splitter, outgoing)


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
        return MaterializedSignalPlan(-1, {}, {}, {}, {})

    button_index = add_start_button(build, base_index)
    gate_indexes = add_physical_gate_or_table(build, base_index, len(analysis.gate_ors))
    # Every planned Wire, including timeline links, remains an explicit
    # destination. Delayer fan-out is handled by physical Splitter_3 trees.
    timeline_destinations = {}
    skipped_wire_ids = set()

    node_indexes, wire_indexes, wires_by_frame = _planned_layout(
        build, analysis, gate_indexes, skipped_wire_ids
    )

    incoming_timeline = {
        wire.target_node: wire
        for wire in analysis.wires
        if wire.purpose == "timeline"
    }
    wire_source_links = {}
    for frame in (frame for frame in analysis.frames if frame.included_in_build):
        delayer_id = _delayer_id(frame.index)
        connections = []
        if delayer_id == analysis.start_target:
            connections.append([TIPOLOCAL_DELAYER, "2", to_rtg_index(button_index)])
        else:
            incoming = incoming_timeline[delayer_id]

            source_index = wire_indexes[incoming.id]

            connections.append([
                TIPOLOCAL_DELAYER,
                WIRE_POINT_RIGHT,
                to_rtg_index(source_index)
            ])
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
            source_link = (wire.source_point, _endpoint_index(
                wire.source_node, node_indexes, pixel_endpoints
            ))
            wire_source_links[wire.id] = source_link
            wire_connections = _wire_connections(
                wire, node_indexes, pixel_endpoints, timeline_destinations, source_link
            )
            actual_wire_index = build.add_block(RtGBlock(
                "Wire", wire_connections
            ))
            if actual_wire_index != wire_indexes[wire.id]:
                raise RuntimeError("Internal layout drift while materializing Wires")

    _materialize_delayer_fanout(
        build, analysis, node_indexes, wire_indexes,
        wire_source_links, pixel_endpoints,
    )

    # A Splitter_3 has one active signal input. It points to the Wire; the
    # Wire preserves the template's old Stick/RemoteButton physical anchor.
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

    materialized = MaterializedSignalPlan(
        button_index, dict(node_indexes), dict(wire_indexes), dict(timeline_destinations),
        dict(wire_source_links)
    )
    errors = validate_materialized_signal_plan(
        build, analysis, pixel_endpoints, materialized, skipped_wire_ids
    )
    if errors:
        raise ValueError("\n".join(errors))
    return materialized


def validate_materialized_signal_plan(
    build, analysis, pixel_endpoints, materialized, skipped_wire_ids=None
) -> List[str]:
    """Verify that physical JSON represents precisely the already-planned wires."""

    if skipped_wire_ids is None:
        skipped_wire_ids = _skipped_timeline_wire_ids(analysis)

    errors = []
    valid_json, json_error = validate_build_json(build.to_json())
    if not valid_json:
        return [f"[CONNECTION ERROR]\nComponent: Build\nConnection point: JSON\nExpected target: valid RtG tuple\nActual target: invalid\nReason: {json_error}"]
    for frame in (frame for frame in analysis.frames if frame.included_in_build):
        index = materialized.node_indexes[_delayer_id(frame.index)]
        block = build.blocks[index]
        if block.block_type != "Delayer" or block.properties.get("Delay") != frame.duration:
            errors.append(f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: Delay\nExpected target: {frame.duration}\nActual target: {block.properties.get('Delay')}\nReason: Frame duration was not preserved.")
        if len(block.connections) != 1:
            errors.append(
                f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: timeline\n"
                "Expected target: exactly one Button/Wire input\n"
                f"Actual target: {block.connections}\n"
                "Reason: Delayer signal fan-out belongs to Wire blocks, not Delayer."
            )
            continue

        delayer_id = _delayer_id(frame.index)
        if delayer_id == analysis.start_target:
            expected_input = [
                TIPOLOCAL_DELAYER, "2", to_rtg_index(materialized.button_index)
            ]
        else:
            incoming = next(
                (wire for wire in analysis.wires
                 if wire.purpose == "timeline" and wire.target_node == delayer_id),
                None,
            )
            if incoming is None:
                errors.append(
                    f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: timeline\n"
                    f"Expected target: incoming timeline Wire for {delayer_id}\n"
                    "Actual target: none\nReason: Missing logical timeline connection."
                )
                continue

            if incoming.id in skipped_wire_ids:
                previous_signal_wires = [
                    wire for wire in analysis.wires
                    if wire.frame_index == incoming.frame_index
                    and wire.purpose == "pixel-signal"
                    and wire.source_node == incoming.source_node
                ]
                if not previous_signal_wires:
                    errors.append(
                        f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: timeline\n"
                        f"Expected target: final signal Wire replacing {incoming.id}\n"
                        "Actual target: none\nReason: Skipped timeline Wire has no replacement."
                    )
                    continue
                source_wire = previous_signal_wires[-1]
                source_index = materialized.wire_indexes.get(source_wire.id)
            else:
                source_index = materialized.wire_indexes.get(incoming.id)

            if source_index is None:
                errors.append(
                    f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: timeline\n"
                    f"Expected target: materialized Wire for {incoming.id}\n"
                    "Actual target: missing index\nReason: Timeline input target was not materialized."
                )
                continue
            expected_input = [
                TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(source_index)
            ]

        if block.connections[0] != expected_input:
            errors.append(
                f"[CONNECTION ERROR]\nComponent: Delayer\nConnection point: timeline\n"
                f"Expected target: {expected_input}\nActual target: {block.connections[0]}\n"
                "Reason: Delayer does not reference the expected previous-frame Wire."
            )
    for wire in analysis.wires:
        if wire.id in skipped_wire_ids:
            continue
        index = materialized.wire_indexes.get(wire.id)
        if index is None:
            errors.append(f"Missing materialized Wire index: {wire.id}")
            continue
        if wire.id not in materialized.wire_source_links:
            errors.append(f"Missing materialized Wire source link: {wire.id}")
            continue
        block = build.blocks[index]
        expected = _wire_connections(
            wire, materialized.node_indexes, pixel_endpoints, materialized.timeline_destinations,
            materialized.wire_source_links[wire.id],
        )
        if wire.id in {item.id for item in materialized.timeline_destinations.values()}:
            continue
        if block.block_type != "Wire" or block.connections != expected:
            errors.append(f"[CONNECTION ERROR]\nComponent: Wire\nConnection point: {wire.id}\nExpected target: {expected}\nActual target: {block.connections}\nReason: Materialized endpoints differ from analysis plan.")
    for layer in analysis.pixel_layers:
        endpoint = pixel_endpoints[layer.id]
        wire = next(item for item in analysis.wires if item.target_node == layer.id)
        expected = [endpoint.point_id, WIRE_POINT_RIGHT, to_rtg_index(materialized.wire_indexes[wire.id])]
        actual = build.blocks[endpoint.block_index].connections[0]
        if actual != expected:
            errors.append(f"[CONNECTION ERROR]\nComponent: Splitter_3\nConnection point: {endpoint.point_id}\nExpected target: {expected}\nActual target: {actual}\nReason: Pixel input was not replaced by the planned Wire.")
        wire_block = build.blocks[materialized.wire_indexes[wire.id]]
        expected_anchor = [TIPOLOCAL_WIRE, endpoint.anchor_point_id, to_rtg_index(endpoint.anchor_block_index)]
        if not wire_block.connections or wire_block.connections[0] != expected_anchor:
            errors.append(
                f"[CONNECTION ERROR]\nComponent: Wire\nConnection point: physical anchor\n"
                f"Expected target: {expected_anchor}\nActual target: {wire_block.connections}\n"
                "Reason: Pixel Wire is not attached to the original Splitter_3 anchor."
            )
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
        incoming = [TIPOLOCAL_DELAYER, "2", to_rtg_index(button_index)] if frame_index == 0 else [TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(len(build.blocks) + 1)]
        indexes.append(build.add_block(RtGBlock("Delayer", [incoming], {"DelayDeactivation": True, "Delay": float(duration), "RGB": [21, 95, 163], "Frame": frame_index})))
        if frame_index:
            previous = indexes[-2]
            wire_index = build.add_block(RtGBlock("Wire", [
                [TIPOLOCAL_WIRE, DELAYER_OUTPUT_POINT, to_rtg_index(previous)],
            ]))
            build.blocks[indexes[-1]].connections[0] = [TIPOLOCAL_DELAYER, WIRE_POINT_RIGHT, to_rtg_index(wire_index)]
    return indexes


def validate_signal_connections(build: RtGBuild) -> List[str]:
    """Lightweight structural validator for callers without an analysis plan."""

    valid, error = validate_build_json(build.to_json())
    if not valid:
        return [error]
    errors = []
    for index, block in enumerate(build.blocks):
        if block.block_type != "Wire":
            continue
        if len(block.connections) == 2:
            continue
        # A timeline Wire may be one-ended. Its following Delayer owns the
        # reciprocal ["2", "4", Wire]; it may leave the prior signal Wire
        # through point 4.
        if len(block.connections) == 1:
            local_type, point_id, target_index = block.connections[0]
            if (
                local_type == TIPOLOCAL_WIRE
                and isinstance(target_index, int)
                and 1 <= target_index <= len(build.blocks)
                and (
                    (point_id == DELAYER_OUTPUT_POINT and build.blocks[target_index - 1].block_type == "Delayer")
                    or (point_id == WIRE_POINT_RIGHT and build.blocks[target_index - 1].block_type == "Wire")
                )
            ):
                continue
            errors.append(
                f"Wire {index + 1}: one-ended temporal Wire must start at Delayer point "
                f"{DELAYER_OUTPUT_POINT} or Wire point {WIRE_POINT_RIGHT}"
            )
            continue
        errors.append(f"Wire {index + 1}: expected one timeline endpoint or two signal endpoints")
    return errors
