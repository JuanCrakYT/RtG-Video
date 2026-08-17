"""Signal logic helpers for RtG frame-to-pixel activation.

This module builds the logical circuit topology required by the project:

    Delayer -> OR-chain -> Pixel input

The goal is to let multiple frames feed the same pixel without creating a
shared signal path between unrelated pixels. Each pixel gets its own
independent OR-chain.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from ..rtg.blocks import RtGBuild, RtGBlock


def _connect_output_to_gate(build: RtGBuild, source_index: int, gate_index: int, gate_input: str) -> int:
    """Create a wire from a source block to a Gate-OR input."""
    wire = RtGBlock("Wire")
    wire.connections = [
        ["1", "Output", source_index],
        ["2", gate_input, gate_index],
    ]
    return build.add_block(wire)


def _connect_gate_output_to_note(build: RtGBuild, gate_index: int, note_index: int) -> int:
    """Create a wire from a Gate-OR output to a pixel input note."""
    wire = RtGBlock("Wire")
    wire.connections = [
        ["1", "Output", gate_index],
        ["2", "Input", note_index],
    ]
    return build.add_block(wire)


def build_signal_chain_for_pixel(frame_ids: Sequence[str], pixel_uuid: str) -> RtGBuild:
    """Build a per-pixel OR-chain combining all frame-delayed signals.

    The topology matches the intended physical logic:

        Delayer0 ──┐
                   ├── Gate-OR ──┐
        Delayer1 ──┘             │
                                ├── Gate-OR ──→ pixel input
        Delayer2 ───────────────┘

    This keeps each frame isolated and prevents signal feedback from one frame
    into another through a shared wire network.
    """
    build = RtGBuild()

    if not frame_ids:
        note = RtGBlock("Note", properties={"Text": "pixel input"})
        note.set_property("PixelUUID", pixel_uuid)
        build.add_block(note)
        return build

    delayer_indexes: List[int] = []
    for frame_id in frame_ids:
        delayer = RtGBlock("Delayer")
        delayer.properties = {
            "DelayDeactivation": True,
            "Delay": 0.1,
            "RGB": [21, 95, 163],
            "Frame": frame_id,
        }
        delayer_indexes.append(build.add_block(delayer))

    if len(frame_ids) == 1:
        note = RtGBlock("Note", properties={"Text": "pixel input"})
        note.set_property("PixelUUID", pixel_uuid)
        note_index = build.add_block(note)
        _connect_output_to_gate(build, delayer_indexes[0], note_index, "Input")
        return build

    current_or_index = None
    first_or = RtGBlock("Gate-OR")
    first_or_index = build.add_block(first_or)
    current_or_index = first_or_index

    _connect_output_to_gate(build, delayer_indexes[0], first_or_index, "InputA")
    _connect_output_to_gate(build, delayer_indexes[1], first_or_index, "InputB")

    for frame_index in range(2, len(frame_ids)):
        next_or = RtGBlock("Gate-OR")
        next_or_index = build.add_block(next_or)
        _connect_output_to_gate(build, current_or_index, next_or_index, "InputA")
        _connect_output_to_gate(build, delayer_indexes[frame_index], next_or_index, "InputB")
        current_or_index = next_or_index

    pixel_note = RtGBlock("Note", properties={"Text": "pixel input"})
    pixel_note.set_property("PixelUUID", pixel_uuid)
    note_index = build.add_block(pixel_note)
    _connect_gate_output_to_note(build, current_or_index, note_index)

    return build


def generate_2x2_eight_frame_demo() -> RtGBuild:
    """Create the first-stage 2x2 by 8-frame RtG signal network.

    The demo uses 4 pixels and 8 frames with a small repeating pattern. The
    topology is intentionally generated per pixel so that every pixel gets a
    dedicated OR-chain instead of sharing one global chain.
    """
    pixel_ids = [
        "pixel_00",
        "pixel_01",
        "pixel_10",
        "pixel_11",
    ]

    frame_patterns = {
        0: ["pixel_00", "pixel_11"],
        1: ["pixel_00", "pixel_01"],
        2: ["pixel_10", "pixel_11"],
        3: ["pixel_00", "pixel_10"],
        4: ["pixel_01", "pixel_11"],
        5: ["pixel_01", "pixel_10"],
        6: pixel_ids,
        7: ["pixel_00", "pixel_11"],
    }

    final_build = RtGBuild()

    for pixel_uuid in pixel_ids:
        frame_sequence = [
            str(frame_index)
            for frame_index, active_pixels in frame_patterns.items()
            if pixel_uuid in active_pixels
        ]
        if not frame_sequence:
            frame_sequence = ["idle"]

        pixel_build = build_signal_chain_for_pixel(frame_sequence, pixel_uuid)
        for block in pixel_build.blocks:
            final_build.add_block(block)

    return final_build
