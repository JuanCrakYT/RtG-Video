"""Tests for physical frame-to-pixel RtG signal logic."""

from pathlib import Path
from typing import Dict, List, Tuple

from src.animation.signal_logic import (
    PixelSignalEndpoint,
    add_start_button,
    add_physical_gate_or_table,
    build_signal_network,
    build_animation_timeline,
    resolve_pixel_inputs,
    validate_signal_connections,
)
from src.rtg.blocks import RtGBlock, RtGBuild
from src.rtg.format import load_pixel_template_from_file
from src.display.matrix import MatrixBuilder
from src.display.pixel import Pixel, PixelTemplate


def _make_display_endpoints():
    """Create physical endpoint blocks used by the topology test."""
    build = RtGBuild()
    build.create_base()
    endpoints = {}
    for pixel_number in range(4):
        block_index = build.add_block(
            RtGBlock("Splitter_3", connections=[
                ["3", "1", 1],
                ["5", "3", 1],
                ["7", "4", 1],
                ["9", "4", 1],
            ])
        )
        endpoints[f"pixel_{pixel_number}"] = PixelSignalEndpoint(block_index, "1")
    return build, endpoints


def _frame_active_to_pixel_color(
    frame_active_pixels: Dict[int, List[str]],
    delayer_indexes: List[int],
    default_color: Tuple[int, int, int] = (255, 255, 255),
) -> Dict[str, Dict[Tuple[int, int, int], List[int]]]:
    """
    Convert old frame_active_pixels format to new pixel_color_frames format.
    
    Old format: {frame_index: [pixel_uuid, ...]}
    New format: {pixel_uuid: {color: [delayer_index, ...]}}
    
    This assumes a single default color for all active pixels.
    """
    pixel_color_frames: Dict[str, Dict[Tuple[int, int, int], List[int]]] = {}
    
    for frame_index, pixel_uuids in frame_active_pixels.items():
        for pixel_uuid in pixel_uuids:
            if pixel_uuid not in pixel_color_frames:
                pixel_color_frames[pixel_uuid] = {}
            if default_color not in pixel_color_frames[pixel_uuid]:
                pixel_color_frames[pixel_uuid][default_color] = []
            pixel_color_frames[pixel_uuid][default_color].append(delayer_indexes[frame_index])
    
    # Sort delayer indexes for each pixel+color
    for pixel_uuid in pixel_color_frames:
        for color in pixel_color_frames[pixel_uuid]:
            pixel_color_frames[pixel_uuid][color].sort()
    
    return pixel_color_frames


def test_start_button_and_timeline_delayers_connect_to_base_and_wires():
    build = RtGBuild()
    base_index = build.create_base()

    button_index = add_start_button(build, base_index)
    delayer_indexes = build_animation_timeline(
        build,
        [0.1, 0.1, 0.1],
        base_index=base_index,
    )

    button = build.blocks[button_index]
    assert sum(block.block_type == "Button" for block in build.blocks) == 1
    assert button.properties == {"RGB": [255, 0, 0]}
    assert len(button.connections) == 2
    base_attachments = build.blocks[base_index].properties["EphemeralAttachments"]
    button_uuids = [connection[1] for connection in button.connections]
    assert all(connection[0] == "1" and connection[2] == base_index + 1 for connection in button.connections)
    assert len(set(button_uuids)) == 2
    assert all(uuid in base_attachments for uuid in button_uuids)
    assert all(base_attachments[uuid]["cframe"][:3] == [0.0, 0.0, 0.0] for uuid in button_uuids)
    assert [build.blocks[index].properties["Frame"] for index in delayer_indexes] == [0, 1, 2]

    wire_indexes = [
        index for index, block in enumerate(build.blocks)
        if block.block_type == "Wire"
    ]
    assert len(wire_indexes) == 2
    wire0_index, wire1_index = wire_indexes

    # Each Delayer stores exactly one connection: the first to Base, and
    # each later Delayer to the Wire that feeds it.
    assert build.blocks[delayer_indexes[0]].connections == [
        ["2", "5", base_index + 1],
    ]
    assert build.blocks[delayer_indexes[1]].connections == [
        ["2", "4", wire0_index + 1],
    ]
    assert build.blocks[delayer_indexes[2]].connections == [
        ["2", "4", wire1_index + 1],
    ]
    assert all(len(build.blocks[index].connections) == 1 for index in delayer_indexes)

    # Each Wire records both neighboring Delayers; the previous Delayer does
    # not receive a second connection to its outgoing Wire.
    assert build.blocks[wire0_index].connections == [
        ["3", "1", delayer_indexes[0] + 1],
        ["1", "1", delayer_indexes[1] + 1],
    ]
    assert build.blocks[wire1_index].connections == [
        ["3", "1", delayer_indexes[1] + 1],
        ["1", "1", delayer_indexes[2] + 1],
    ]


def test_physical_gate_or_table_uses_mounting_connections_only():
    build = RtGBuild()
    base_index = build.create_base()

    gate_indexes = add_physical_gate_or_table(build, base_index, 3)

    assert len(gate_indexes) == 3
    assert [build.blocks[index].block_type for index in gate_indexes] == [
        "Gate-OR",
        "Gate-OR",
        "Gate-OR",
    ]
    # Each Gate-OR mounts to Base through a unique UUID attachment at zero offset.
    base_attachments = build.blocks[base_index].properties["EphemeralAttachments"]
    gate_uuids = [build.blocks[idx].connections[0][1] for idx in gate_indexes]
    for idx, attachment_uuid in zip(gate_indexes, gate_uuids):
        assert build.blocks[idx].connections == [["4", attachment_uuid, base_index + 1]]
        assert attachment_uuid in base_attachments
        assert base_attachments[attachment_uuid]["partName"] == "Base"
        assert base_attachments[attachment_uuid]["cframe"][:3] == [0.0, 0.0, 0.0]
    assert len(set(gate_uuids)) == len(gate_uuids)


def test_signal_network_uses_one_delayer_per_frame_and_numeric_ports():
    build, endpoints = _make_display_endpoints()
    frame_active_pixels = {
        0: ["pixel_0", "pixel_1", "pixel_3"],
        1: ["pixel_0", "pixel_2"],
        2: ["pixel_1", "pixel_2", "pixel_3"],
        3: ["pixel_0"],
        4: ["pixel_1", "pixel_3"],
        5: ["pixel_2", "pixel_3"],
        6: list(endpoints),
        7: ["pixel_0", "pixel_3"],
    }

    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1] * 8)
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 16)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(build, pixel_color_frames, endpoints, [0.1] * 8, gate_or_pool, delayer_indexes)

    delayers = [block for block in build.blocks if block.block_type == "Delayer"]
    gate_ors = [block for block in build.blocks if block.block_type == "Gate-OR"]
    notes = [block for block in build.blocks if block.block_type == "Note"]
    wires = [block for block in build.blocks if block.block_type == "Wire"]

    assert len(delayers) == 8
    assert not notes
    assert len(wires) > 0
    assert not validate_signal_connections(build)

    # Verify Wire connections use fixed "3" (input) and "1" (output)
    for wire in wires:
        assert len(wire.connections) == 2
        assert wire.connections[0][0] == "3"  # Wire input side
        assert wire.connections[1][0] == "1"  # Wire output side


def test_one_pixel_on_off_on_uses_one_or_and_real_splitter_input():
    build, endpoints = _make_display_endpoints()
    frame_active_pixels = {0: ["pixel_0"], 1: [], 2: ["pixel_0"]}
    
    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1, 0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 1)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        build,
        pixel_color_frames,
        {"pixel_0": endpoints["pixel_0"]},
        [0.1, 0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    assert sum(block.block_type == "Delayer" for block in build.blocks) == 3
    assert sum(block.block_type == "Gate-OR" for block in build.blocks) == 1
    assert not any(block.block_type == "Note" for block in build.blocks)
    wires = [block for block in build.blocks if block.block_type == "Wire"]
    # 3 frames = 2 timeline wires + 3 signal wires (2 Delayer->Gate-OR, 1 Gate-OR->Pixel) = 5
    assert len(wires) == 5
    # All Wires use fixed "3" (input) and "1" (output)
    for wire in wires:
        assert len(wire.connections) == 2
        assert wire.connections[0][0] == "3"  # Wire input side
        assert wire.connections[1][0] == "1"  # Wire output side
    # Last wire connects Gate-OR output to Splitter_3.
    splitter = build.blocks[endpoints["pixel_0"].block_index]
    assert wires[-1].connections[1][2] == endpoints["pixel_0"].block_index + 1
    # Reuse the Splitter input for the Wire; do not leave the old parent
    # connection and append a second connection to the same input.
    assert len(splitter.connections) == 4
    last_wire_index = build.blocks.index(wires[-1]) + 1
    assert splitter.connections[0] == ["3", "4", last_wire_index]

    # Every endpoint named by a generated Wire must point back to that Wire.
    for wire_index, wire in enumerate(build.blocks):
        if wire.block_type != "Wire":
            continue
        for connection in wire.connections:
            endpoint_block = build.blocks[connection[2] - 1]
            if endpoint_block.block_type in {"Gate-OR", "Delayer"}:
                # Gate-ORs and Delayers do not store reciprocal entries for
                # every Wire. A Delayer keeps only its parent connection.
                continue
            assert any(
                reciprocal[2] == wire_index + 1
                for reciprocal in endpoint_block.connections
                if len(reciprocal) == 3
            )


def test_pixel_with_three_frames_uses_one_balanced_or_tree():
    build, endpoints = _make_display_endpoints()
    frame_active_pixels = {0: ["pixel_0"], 1: ["pixel_0"], 2: ["pixel_0"]}
    
    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1, 0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 2)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        build,
        pixel_color_frames,
        endpoints,
        [0.1, 0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    gate_indexes = [
        index for index, block in enumerate(build.blocks)
        if block.block_type == "Gate-OR"
    ]
    wires = [block for block in build.blocks if block.block_type == "Wire"]

    assert len(gate_indexes) == 2
    # 3 frames = 2 timeline wires + 5 signal wires = 7
    assert len(wires) == 7
    # All Wires use fixed "3" (input) and "1" (output)
    for wire in wires:
        assert len(wire.connections) == 2
        assert wire.connections[0][0] == "3"  # Wire input side
        assert wire.connections[1][0] == "1"  # Wire output side
    # Last wire connects Gate-OR output to Splitter_3
    assert wires[-1].connections[1][2] == endpoints["pixel_0"].block_index + 1


def test_three_active_frames_use_balanced_tree_and_resolve_uuid_to_splitter():
    build, endpoints = _make_display_endpoints()
    pixels = [type("PixelStub", (), {"uuid": "pixel_0", "get_signal_endpoint": lambda self: (endpoints["pixel_0"].block_index, "1")})()]
    resolved = resolve_pixel_inputs(pixels)
    frame_active_pixels = {0: ["pixel_0"], 1: ["pixel_0"], 2: ["pixel_0"]}
    
    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1, 0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 2)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        build,
        pixel_color_frames,
        resolved,
        [0.1, 0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    assert sum(block.block_type == "Delayer" for block in build.blocks) == 3
    assert sum(block.block_type == "Gate-OR" for block in build.blocks) == 2
    assert not validate_signal_connections(build)


def test_four_frames_form_balanced_or_tree_with_three_gates():
    build, endpoints = _make_display_endpoints()
    frame_active_pixels = {0: ["pixel_0"], 1: ["pixel_0"], 2: ["pixel_0"], 3: ["pixel_0"]}
    
    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1, 0.1, 0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 3)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        build,
        pixel_color_frames,
        endpoints,
        [0.1, 0.1, 0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    gate_indexes = [
        index for index, block in enumerate(build.blocks)
        if block.block_type == "Gate-OR"
    ]
    assert len(gate_indexes) == 3

    gate_input_counts = []
    for gate_index in gate_indexes:
        inputs = sum(
            1
            for wire in build.blocks
            if wire.block_type == "Wire" and wire.connections[1][2] == gate_index + 1
        )
        gate_input_counts.append(inputs)
    assert all(count >= 2 for count in gate_input_counts)

    root_inputs = gate_input_counts[-1]
    assert root_inputs >= 2


def test_multiple_pixels_get_independent_or_trees():
    build, endpoints = _make_display_endpoints()
    frame_active_pixels = {
        0: ["pixel_0", "pixel_1"],
        1: ["pixel_0", "pixel_1"],
    }
    
    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 2)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        build,
        pixel_color_frames,
        endpoints,
        [0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    pixel_0_inputs = sum(
        1
        for wire in build.blocks
        if wire.block_type == "Wire" and wire.connections[1][2] == endpoints["pixel_0"].block_index + 1
    )
    pixel_1_inputs = sum(
        1
        for wire in build.blocks
        if wire.block_type == "Wire" and wire.connections[1][2] == endpoints["pixel_1"].block_index + 1
    )
    assert pixel_0_inputs == 1
    assert pixel_1_inputs == 1


def test_physical_gate_ors_remain_attached_to_build():
    build, endpoints = _make_display_endpoints()
    frame_active_pixels = {0: ["pixel_0"], 1: ["pixel_0"]}
    
    # Build timeline first to get delayer indexes
    build_animation_timeline(build, [0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(build, 0, 1)
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        build,
        pixel_color_frames,
        endpoints,
        [0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    gate_ors = [block for block in build.blocks if block.block_type == "Gate-OR"]
    assert len(gate_ors) == 1
    assert any(block.block_type == "Wire" for block in build.blocks)


def test_real_pixel_parent_references_are_one_based():
    template_path = Path(__file__).parents[1] / "assets" / "builds" / "pixel" / "pixel.json"
    template = PixelTemplate(load_pixel_template_from_file(str(template_path)))
    matrix = MatrixBuilder().set_dimensions(2, 1).set_template(template).build()

    for block in matrix.build.blocks:
        for connection in block.connections:
            assert 1 <= connection[2] <= len(matrix.build.blocks)


def test_splitter_endpoint_uses_point_field_not_tipo_local():
    build = RtGBuild()
    build.create_base()
    splitter = RtGBlock("Splitter_3", connections=[["3", "4", 1]])
    splitter_index = build.add_block(splitter)
    pixel = Pixel(
        x=0,
        y=0,
        blocks=[splitter],
        uuid="pixel-template-port",
        block_indices={1: splitter_index + 1},
    )

    endpoint = resolve_pixel_inputs([pixel])[pixel.uuid]
    assert endpoint.block_index == splitter_index
    assert endpoint.point_id == "4"


def test_real_pixel_asset_generates_balanced_tree_counts():
    template_path = Path(__file__).parents[1] / "assets" / "builds" / "pixel" / "pixel.json"
    template = PixelTemplate(load_pixel_template_from_file(str(template_path)))
    matrix = MatrixBuilder().set_dimensions(1, 1).set_template(template).build()
    pixel = matrix.get_pixel(0, 0)

    endpoints = resolve_pixel_inputs([pixel])
    assert endpoints[pixel.uuid].block_index == next(
        index for index, block in enumerate(matrix.build.blocks)
        if block.block_type == "Splitter_3"
    )
    assert endpoints[pixel.uuid].point_id == "1"

    # Build timeline first to get delayer indexes
    build_animation_timeline(matrix.build, [0.1, 0.1, 0.1])
    delayer_indexes = [
        idx for idx, block in enumerate(matrix.build.blocks)
        if block.block_type == "Delayer"
    ]
    
    gate_or_pool = add_physical_gate_or_table(matrix.build, matrix.base_index, 2)
    frame_active_pixels = {0: [pixel.uuid], 1: [pixel.uuid], 2: [pixel.uuid]}
    pixel_color_frames = _frame_active_to_pixel_color(frame_active_pixels, delayer_indexes)
    build_signal_network(
        matrix.build,
        pixel_color_frames,
        endpoints,
        [0.1, 0.1, 0.1],
        gate_or_pool,
        delayer_indexes,
    )

    assert sum(block.block_type == "Delayer" for block in matrix.build.blocks) == 3
    assert sum(block.block_type == "Gate-OR" for block in matrix.build.blocks) == 2
    # 3 frames = 2 timeline wires + 5 signal wires = 7
    assert sum(block.block_type == "Wire" for block in matrix.build.blocks) == 7
    assert not validate_signal_connections(matrix.build)
