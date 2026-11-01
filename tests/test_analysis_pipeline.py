"""Regression tests for the analysis-first RtG video pipeline."""

from pathlib import Path
from collections import defaultdict

import pytest

from src.animation.signal_logic import (
    materialize_signal_plan,
    resolve_pixel_inputs,
    validate_signal_connections,
    validate_materialized_signal_plan,
)
from src.display.matrix import MatrixBuilder
from src.display.pixel import PixelTemplate
from src.rtg.format import load_pixel_template_from_file, validate_build_json
from src.rtg.uuid import reset_uuid_manager
from src.video.analysis import ConnectionPlanError, analyze_color_frames, export_analysis_json
from src.video.processing import BLACK


ROOT = Path(__file__).resolve().parents[1]
PIXEL_TEMPLATE = ROOT / "assets" / "builds" / "pixel" / "pixel.json"
REMOTE_PIXEL_TEMPLATE = ROOT / "assets" / "builds" / "pixel" / "remote-pixel.json"
RED = (255, 0, 0)
GREEN = (0, 255, 0)


def _materialize(analysis):
    reset_uuid_manager()
    template = PixelTemplate(load_pixel_template_from_file(str(PIXEL_TEMPLATE)))
    palettes = defaultdict(set)
    for layer in analysis.pixel_layers:
        palettes[layer.position].add(layer.color)
    matrix = (
        MatrixBuilder()
        .set_dimensions(analysis.width, analysis.height)
        .set_template(template)
        .set_palette_by_position(palettes)
        .build()
    )
    by_uuid = resolve_pixel_inputs(matrix.iter_pixels())
    endpoints = {}
    for layer in analysis.pixel_layers:
        pixel = matrix.get_pixel_for_color(*layer.position, layer.color)
        endpoints[layer.id] = by_uuid[pixel.uuid]
    materialized = materialize_signal_plan(
        matrix.build, analysis, endpoints, base_index=matrix.base_index
    )
    return matrix, endpoints, materialized


def test_analysis_exports_complete_plan_before_build(tmp_path):
    frames = [[[RED]], [[BLACK]], [[GREEN]]]
    analysis = analyze_color_frames(frames, 1, 1, frame_durations=[0.1, 0.2, 0.3])
    output = tmp_path / "data.json"
    export_analysis_json(analysis, str(output))

    import json
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema"] == "rtg-video.analysis/v1"
    assert data["video_info"]["frame_durations"] == [0.1, 0.2, 0.3]
    assert len(data["signal_plan"]["frames"]) == 3
    assert data["signal_plan"]["button"]["target"] == "delayer:0"
    assert data["signal_plan"]["wires"]


def test_intermediate_black_frame_keeps_delayer_but_no_pixel_wire():
    analysis = analyze_color_frames(
        [[[RED]], [[BLACK]], [[RED]]], 1, 1, frame_durations=[0.1, 0.2, 0.3]
    )
    assert analysis.included_frame_indices == [0, 1, 2]
    assert analysis.frames[1].is_black
    assert analysis.frames[1].duration == 0.2
    assert not [wire for wire in analysis.wires if wire.purpose == "pixel-signal" and wire.frame_index == 1]

    matrix, endpoints, materialized = _materialize(analysis)
    delayers = [block for block in matrix.build.blocks if block.block_type == "Delayer"]
    assert [block.properties["Delay"] for block in delayers] == [0.1, 0.2, 0.3]
    assert validate_build_json(matrix.build.to_json()) == (True, None)
    assert not validate_materialized_signal_plan(matrix.build, analysis, endpoints, materialized)


def test_trailing_black_frame_is_not_materialized():
    analysis = analyze_color_frames(
        [[[RED]], [[BLACK]]], 1, 1, frame_durations=[0.1, 0.2]
    )
    assert analysis.included_frame_indices == [0]
    assert analysis.frames[-1].is_black
    assert not analysis.frames[-1].included_in_build
    matrix, _, _ = _materialize(analysis)
    assert [block.properties["Frame"] for block in matrix.build.blocks if block.block_type == "Delayer"] == [0]


def test_splitter_input_comes_from_first_declared_splitter_port():
    analysis = analyze_color_frames([[[RED]]], 1, 1, frame_durations=[0.1])
    matrix, endpoints, materialized = _materialize(analysis)
    layer = analysis.pixel_layers[0]
    endpoint = endpoints[layer.id]
    splitter = matrix.build.blocks[endpoint.block_index]
    pixel_wire = next(wire for wire in analysis.wires if wire.target_node == layer.id)
    assert endpoint.point_id == "3"
    assert splitter.connections[0] == ["3", "4", materialized.wire_indexes[pixel_wire.id] + 1]
    pixel_wire_block = matrix.build.blocks[materialized.wire_indexes[pixel_wire.id]]
    assert pixel_wire_block.connections[0] == [
        "3", endpoint.anchor_point_id, endpoint.anchor_block_index + 1
    ]
    assert matrix.build.blocks[endpoint.anchor_block_index].block_type == "Stick"


def test_wires_own_signal_endpoints_while_delayers_keep_one_timeline_input():
    analysis = analyze_color_frames(
        [[[RED]], [[BLACK]], [[RED]]], 1, 1, frame_durations=[0.1, 0.2, 0.3]
    )
    matrix, _, materialized = _materialize(analysis)
    delayers = [block for block in matrix.build.blocks if block.block_type == "Delayer"]
    assert all(len(block.connections) == 1 for block in delayers)
    gates = [block for block in matrix.build.blocks if block.block_type == "Gate-OR"]
    assert len(gates) == 1
    assert gates[0].connections == [["4", gates[0].connections[0][1], 1]]
    reused_signal_wire_ids = {
        wire.id for wire in materialized.timeline_destinations.values()
    }
    for wire in analysis.wires:
        if wire.id in reused_signal_wire_ids:
            continue
        block = matrix.build.blocks[materialized.wire_indexes[wire.id]]
        assert len(block.connections) == (
            1 if wire.purpose == "timeline" and wire.id not in materialized.timeline_destinations else 2
        )
    assert not validate_signal_connections(matrix.build)

    timeline = next(wire for wire in analysis.wires if wire.purpose == "timeline")
    timeline_block = matrix.build.blocks[materialized.wire_indexes[timeline.id]]
    destination = materialized.timeline_destinations[timeline.id]
    assert timeline_block.connections == [
        ["3", "1", materialized.node_indexes["delayer:0"] + 1],
        ["1", destination.target_point, materialized.node_indexes[destination.target_node] + 1],
    ]
    assert materialized.wire_indexes[destination.id] == materialized.wire_indexes[timeline.id]
    frame_zero_wires = [
        wire for wire in analysis.wires
        if wire.frame_index == 0 and wire.id not in reused_signal_wire_ids
    ]
    for previous, current in zip(frame_zero_wires, frame_zero_wires[1:]):
        assert matrix.build.blocks[materialized.wire_indexes[current.id]].connections[0] == [
            "3", "1", materialized.wire_indexes[previous.id] + 1
        ]
    assert matrix.build.blocks[materialized.node_indexes["delayer:1"]].connections == [
        ["2", "4", materialized.wire_indexes[timeline.id] + 1]
    ]


def test_multiple_active_signals_form_a_wire_chain_from_one_delayer():
    analysis = analyze_color_frames(
        [[[RED, GREEN]], [[RED, GREEN]], [[RED, GREEN]]],
        2, 1, frame_durations=[0.1, 0.1, 0.1],
    )
    matrix, _, materialized = _materialize(analysis)
    reused = {wire.id for wire in materialized.timeline_destinations.values()}
    frame_wires = [
        wire for wire in analysis.wires
        if wire.frame_index == 0 and wire.id not in reused
    ]
    assert len(frame_wires) >= 2
    first, second = frame_wires[:2]
    assert matrix.build.blocks[materialized.wire_indexes[first.id]].connections[0] == [
        "3", "1", materialized.node_indexes["delayer:0"] + 1
    ]
    assert matrix.build.blocks[materialized.wire_indexes[second.id]].connections[0] == [
        "3", "1", materialized.wire_indexes[first.id] + 1
    ]


def test_remote_pixel_template_declares_the_same_splitter_input_port():
    reset_uuid_manager()
    template = PixelTemplate(load_pixel_template_from_file(str(REMOTE_PIXEL_TEMPLATE)))
    matrix = MatrixBuilder().set_dimensions(1, 1).set_template(template).build()
    pixel = matrix.get_pixel(0, 0)
    endpoint = resolve_pixel_inputs([pixel])[pixel.uuid]
    assert endpoint.point_id == "3"


def test_reference_builds_keep_one_based_connections_and_expected_signal_ports():
    """Protect the observations extracted from pixel.json, test.json and test2.json."""
    import json

    for relative in (
        "assets/builds/pixel/pixel.json",
        "assets/builds/pixel/remote-pixel.json",
        "assets/builds/working/test.json",
        "assets/builds/working/test2.json",
    ):
        blocks = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert all(isinstance(block, list) and len(block) == 3 for block in blocks)
        for _, connections, _ in blocks:
            for _, _, parent_index in connections:
                assert 1 <= parent_index <= len(blocks)

    template = json.loads(PIXEL_TEMPLATE.read_text(encoding="utf-8"))
    splitter = next(block for block in template if block[0] == "Splitter_3")
    assert splitter[1][0][0] == "3"
    assert [connection[0] for connection in splitter[1]] == ["3", "5", "7", "9"]

    test2 = json.loads((ROOT / "assets/builds/working/test2.json").read_text(encoding="utf-8"))
    delays = [block[2]["Delay"] for block in test2 if block[0] == "Delayer"]
    assert delays and all(delay == 1 / 3 for delay in delays)

    # In a real saved build, a Wire reaches a Delayer at endpoint 1.  The
    # Delayer's own reference back to its incoming Wire is endpoint 4.
    for blocks in (json.loads((ROOT / "assets/builds/working/test.json").read_text(encoding="utf-8")), test2):
        types = {index: block[0] for index, block in enumerate(blocks, 1)}
        for block_type, connections, _ in blocks:
            if block_type == "Wire":
                for local_type, point_id, target_index in connections:
                    if types[target_index] == "Delayer":
                        assert local_type in {"1", "3"}
                        assert point_id == "1"


def test_invalid_connection_plan_aborts_before_build():
    analysis = analyze_color_frames([[[RED]], [[RED]]], 1, 1, frame_durations=[0.1, 0.1])
    bad_wire = analysis.wires[-1]
    analysis.wires[-1] = type(bad_wire)(
        bad_wire.id, bad_wire.source_node, bad_wire.source_point,
        bad_wire.target_node, "99", bad_wire.frame_index, bad_wire.purpose,
    )
    with pytest.raises(ConnectionPlanError, match=r"\[CONNECTION ERROR\]") as error:
        export_analysis_json(analysis, "unused.json")
    assert "Connection point: target point" in str(error.value)
