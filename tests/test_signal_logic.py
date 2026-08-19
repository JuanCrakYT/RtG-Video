"""Tests for physical frame-to-pixel RtG signal logic."""

from pathlib import Path

from src.animation.signal_logic import (
    PixelSignalEndpoint,
    build_signal_network,
    resolve_pixel_inputs,
    validate_signal_connections,
)
from src.rtg.blocks import RtGBlock, RtGBuild
from src.rtg.format import load_pixel_template_from_file
from src.display.matrix import MatrixBuilder
from src.display.pixel import PixelTemplate


def _make_display_endpoints():
    """Create physical endpoint blocks used by the topology test."""
    build = RtGBuild()
    build.create_base()
    endpoints = {}
    for pixel_number in range(4):
        block_index = build.add_block(
            RtGBlock("Splitter_3", connections=[
                ["3", "1", 0],
                ["5", "3", 0],
                ["7", "4", 0],
                ["9", "4", 0],
            ])
        )
        endpoints[f"pixel_{pixel_number}"] = PixelSignalEndpoint(block_index, "3")
    return build, endpoints


def test_signal_network_uses_one_delayer_per_frame_and_numeric_ports():
    build, endpoints = _make_display_endpoints()
    active_pixels = {
        0: ["pixel_0", "pixel_1", "pixel_3"],
        1: ["pixel_0", "pixel_2"],
        2: ["pixel_1", "pixel_2", "pixel_3"],
        3: ["pixel_0"],
        4: ["pixel_1", "pixel_3"],
        5: ["pixel_2", "pixel_3"],
        6: list(endpoints),
        7: ["pixel_0", "pixel_3"],
    }

    build_signal_network(build, active_pixels, endpoints, [0.1] * 8)

    delayers = [block for block in build.blocks if block.block_type == "Delayer"]
    gate_ors = [block for block in build.blocks if block.block_type == "Gate-OR"]
    notes = [block for block in build.blocks if block.block_type == "Note"]
    wires = [block for block in build.blocks if block.block_type == "Wire"]

    assert len(delayers) == 8
    assert len(gate_ors) == 15
    assert not notes
    assert len(wires) > 0
    assert not validate_signal_connections(build)

    for wire in wires:
        assert wire.connections[0][0:2] == ["3", "1"]
        assert wire.connections[1][0] == "1"
        assert wire.connections[1][1] in {"1", "2", "3", "6"}


def test_pixel_with_three_frames_gets_a_private_two_gate_chain():
    build, endpoints = _make_display_endpoints()
    build_signal_network(
        build,
        {0: ["pixel_0"], 1: ["pixel_0"], 2: ["pixel_0"]},
        endpoints,
        [0.1, 0.1, 0.1],
    )

    gate_indexes = [
        index for index, block in enumerate(build.blocks)
        if block.block_type == "Gate-OR"
    ]
    wires = [block for block in build.blocks if block.block_type == "Wire"]

    assert len(gate_indexes) == 2
    assert len(wires) == 5
    assert wires[-1].connections[0] == ["3", "1", gate_indexes[-1]]
    assert wires[-1].connections[1] == ["1", "3", endpoints["pixel_0"].block_index]


def test_one_pixel_on_off_on_uses_one_or_and_real_splitter_input():
    build, endpoints = _make_display_endpoints()
    build_signal_network(
        build,
        {0: ["pixel_0"], 1: [], 2: ["pixel_0"]},
        {"pixel_0": endpoints["pixel_0"]},
        [0.1, 0.1, 0.1],
    )

    assert sum(block.block_type == "Delayer" for block in build.blocks) == 3
    assert sum(block.block_type == "Gate-OR" for block in build.blocks) == 1
    assert not any(block.block_type == "Note" for block in build.blocks)
    output_wire = [block for block in build.blocks if block.block_type == "Wire"][-1]
    assert output_wire.connections[1] == ["1", "3", endpoints["pixel_0"].block_index]


def test_three_active_frames_extend_to_two_ors_and_resolve_uuid_to_splitter():
    build, endpoints = _make_display_endpoints()
    pixels = [type("PixelStub", (), {"uuid": "pixel_0", "get_signal_endpoint": lambda self: (endpoints["pixel_0"].block_index, "3")})()]
    resolved = resolve_pixel_inputs(pixels)

    build_signal_network(
        build,
        {0: ["pixel_0"], 1: ["pixel_0"], 2: ["pixel_0"]},
        resolved,
        [0.1, 0.1, 0.1],
    )

    assert sum(block.block_type == "Delayer" for block in build.blocks) == 3
    assert sum(block.block_type == "Gate-OR" for block in build.blocks) == 2
    assert not validate_signal_connections(build)


def test_real_pixel_asset_generates_three_frame_reference_counts():
    template_path = Path(__file__).parents[1] / "assets" / "pixel" / "pixel.json"
    template = PixelTemplate(load_pixel_template_from_file(str(template_path)))
    matrix = MatrixBuilder().set_dimensions(1, 1).set_template(template).build()
    pixel = matrix.get_pixel(0, 0)

    endpoints = resolve_pixel_inputs([pixel])
    assert endpoints[pixel.uuid].block_index == next(
        index for index, block in enumerate(matrix.build.blocks)
        if block.block_type == "Splitter_3"
    )
    assert endpoints[pixel.uuid].point_id == "3"

    build_signal_network(
        matrix.build,
        {0: [pixel.uuid], 1: [pixel.uuid], 2: [pixel.uuid]},
        endpoints,
        [0.1, 0.1, 0.1],
    )

    assert sum(block.block_type == "Delayer" for block in matrix.build.blocks) == 3
    assert sum(block.block_type == "Gate-OR" for block in matrix.build.blocks) == 2
    assert sum(block.block_type == "Wire" for block in matrix.build.blocks) == 5
    assert not validate_signal_connections(matrix.build)
