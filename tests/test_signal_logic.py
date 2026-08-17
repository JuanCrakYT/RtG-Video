"""Tests for the frame-to-pixel OR-chain signal logic."""

from src.animation.signal_logic import (
    build_signal_chain_for_pixel,
    generate_2x2_eight_frame_demo,
)


def test_signal_chain_for_pixel_extends_with_gate_or():
    """A pixel with multiple frame inputs should be combined with a Gate-OR chain."""
    build = build_signal_chain_for_pixel(
        ["frame0", "frame1", "frame2", "frame3"],
        pixel_uuid="pixel-1",
    )

    gate_ors = [block for block in build.blocks if block.block_type == "Gate-OR"]
    delayers = [block for block in build.blocks if block.block_type == "Delayer"]
    wires = [block for block in build.blocks if block.block_type == "Wire"]

    assert len(gate_ors) >= 2, "A 4-input signal should expand into a Gate-OR chain"
    assert len(delayers) == 4, "Each frame source should have its own Delayer"
    assert len(wires) >= 3, "The OR chain should include signal wires between stages"

    pixel_input = [
        block for block in build.blocks if getattr(block, "block_type", None) == "Note"
        and any(prop == "pixel input" for prop in (block.properties.get("Text"),))
    ]
    assert pixel_input, "The final signal should terminate at a pixel input note"


def test_generate_2x2_eight_frame_demo_builds_expected_network():
    """The first implementation should generate the 2x2 x 8-frame demo topology."""
    build = generate_2x2_eight_frame_demo()

    assert build is not None
    assert len(build.blocks) > 0

    gate_ors = [block for block in build.blocks if block.block_type == "Gate-OR"]
    assert len(gate_ors) >= 8, "Each pixel should have its own OR-chain network"

    # All pixels should have their own final input path, not a shared global chain.
    notes = [block for block in build.blocks if block.block_type == "Note"]
    pixel_outputs = [
        block for block in notes if block.properties.get("Text") == "pixel input"
    ]
    assert len(pixel_outputs) >= 4, "2x2 display should produce one pixel input per pixel"
