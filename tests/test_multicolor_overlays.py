"""Tests for palette-backed, overlaid physical pixel layers."""

from pathlib import Path

import numpy as np

from src.animation.frame import FrameBuilder
from src.display.matrix import MatrixBuilder
from src.display.pixel import PixelTemplate
from src.rtg.cframe import create_pixel_offset_cframe
from src.rtg.format import load_pixel_template_from_file, validate_build_json
from src.rtg.uuid import reset_uuid_manager
from src.video import processing


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "assets" / "builds" / "pixel" / "pixel.json"
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)


def build_overlay_matrix(palette):
    reset_uuid_manager()
    template = PixelTemplate(load_pixel_template_from_file(str(TEMPLATE_PATH)))
    return (
        MatrixBuilder()
        .set_dimensions(1, 1)
        .set_palette(palette)
        .set_template(template)
        .build()
    )


def layer_colors(matrix):
    return [
        tuple(next(block for block in pixel.blocks if block.block_type == "Splitter_3").properties["RGB"])
        for pixel in matrix.get_pixels(0, 0)
    ]


def layer_part_colors(matrix):
    return [
        tuple(
            next(
                block
                for block in pixel.blocks
                if block.block_type == "Part" and block.properties.get("RGB") != [0, 0, 0]
            ).properties["RGB"]
        )
        for pixel in matrix.get_pixels(0, 0)
    ]


def test_black_does_not_create_a_physical_layer():
    matrix = build_overlay_matrix([BLACK])
    assert matrix.get_pixels(0, 0) == []
    assert matrix.get_stats()["total_pixels"] == 0


def test_visible_colors_create_deduplicated_overlays():
    matrix = build_overlay_matrix([BLACK, RED, RED, GREEN, BLUE])
    layers = matrix.get_pixels(0, 0)

    assert layer_colors(matrix) == [RED, GREEN, BLUE]
    assert layer_part_colors(matrix) == [RED, GREEN, BLUE]
    assert len({pixel.uuid for pixel in layers}) == 3
    assert len(matrix.build.blocks[0].properties["EphemeralAttachments"]) == 3

    cframes = [
        tuple(matrix.build.blocks[0].properties["EphemeralAttachments"][pixel.uuid]["cframe"])
        for pixel in layers
    ]
    assert cframes == [cframes[0], cframes[0], cframes[0]]
    assert cframes[0] == (0.0, 0.75, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, -1e16, 0.0, 0.0, 1.0)


def test_overlay_layers_switch_without_accumulating_between_frames():
    matrix = build_overlay_matrix([BLACK, RED, GREEN, BLUE])
    layers = matrix.get_pixels(0, 0)
    by_color = {color: pixel for color, pixel in zip(layer_colors(matrix), layers)}

    frames = [
        FrameBuilder().set_pixel_color(by_color[RED].uuid, RED).build(),
        FrameBuilder().set_pixel_color(by_color[GREEN].uuid, GREEN).build(),
        FrameBuilder().set_pixel_color(by_color[BLUE].uuid, BLUE).build(),
    ]

    assert [frame.get_active_pixels() for frame in frames] == [
        [by_color[RED].uuid],
        [by_color[GREEN].uuid],
        [by_color[BLUE].uuid],
    ]
    assert all(len(frame.get_active_pixels()) == 1 for frame in frames)
    assert all(len(frame.get_pixel_colors()) == 1 for frame in frames)


def test_overlay_layers_can_be_active_simultaneously():
    matrix = build_overlay_matrix([BLACK, RED, GREEN, BLUE])
    layers = matrix.get_pixels(0, 0)
    frame = FrameBuilder()
    for pixel, color in zip(layers, [RED, GREEN, BLUE]):
        frame.set_pixel_color(pixel.uuid, color)

    built = frame.build()
    assert len(built.get_active_pixels()) == 3
    assert set(tuple(color) for color in built.get_pixel_colors().values()) == {RED, GREEN, BLUE}


def test_video_frames_switch_overlay_layers_without_accumulating(monkeypatch):
    matrix = build_overlay_matrix([BLACK, RED, GREEN, BLUE])
    layers = matrix.get_pixels(0, 0)
    by_color = {color: pixel for color, pixel in zip(layer_colors(matrix), layers)}

    frames = [
        np.array([[[0, 0, 255]]], dtype=np.uint8),
        np.array([[[0, 255, 0]]], dtype=np.uint8),
        np.array([[[255, 0, 0]]], dtype=np.uint8),
    ]

    class FakeCapture:
        def __init__(self, _path):
            self.frames = iter(frames)

        def isOpened(self):
            return True

        def get(self, property_id):
            return 30.0 if property_id == processing.cv2.CAP_PROP_FPS else 3.0

        def read(self):
            try:
                return True, next(self.frames)
            except StopIteration:
                return False, None

        def release(self):
            pass

    monkeypatch.setattr(processing.cv2, "VideoCapture", FakeCapture)
    sequence = processing.video_to_sequence("synthetic.mp4", matrix, [BLACK, RED, GREEN, BLUE])

    assert [frame.get_active_pixels() for frame in sequence.frames] == [
        [by_color[RED].uuid],
        [by_color[GREEN].uuid],
        [by_color[BLUE].uuid],
    ]
    assert all(len(frame.get_active_pixels()) == 1 for frame in sequence.frames)


def test_pixel_offset_cframe_uses_required_rotation_for_overlays():
    assert create_pixel_offset_cframe(0, 0, 1).to_list() == [
        0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, -1e16, 0.0, 0.0, 1.0
    ]
    assert create_pixel_offset_cframe(5, 3, 1).to_list() == [
        5.0, 3.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, -1e16, 0.0, 0.0, 1.0
    ]


def test_pixel_color_analysis_only_keeps_used_colors_per_pixel():
    frames = [
        [[RED, BLUE, BLACK, RED]],
        [[BLACK, BLUE, BLACK, RED]],
        [[RED, BLACK, BLACK, RED]],
        [[BLACK, BLUE, BLACK, RED]],
        [[RED, BLACK, BLACK, RED]],
    ]

    states = processing.analyze_pixel_states(frames)

    assert states[(0, 0)]["colors"] == {RED}
    assert states[(1, 0)]["colors"] == {BLUE}
    assert (2, 0) not in states
    assert states[(3, 0)]["colors"] == {RED}
    assert states[(0, 0)]["frames"] == {0: RED, 2: RED, 4: RED}
    assert states[(1, 0)]["frames"] == {0: BLUE, 1: BLUE, 3: BLUE}

    for state in states.values():
        assert all(isinstance(color, tuple) for color in state["frames"].values())


def test_empty_pixel_part_is_attached_to_base_with_uuid():
    reset_uuid_manager()
    template = PixelTemplate(load_pixel_template_from_file(str(TEMPLATE_PATH)))
    matrix = (
        MatrixBuilder()
        .set_dimensions(2, 1)
        .set_template(template)
        .set_palette_by_position({(0, 0): set(), (1, 0): {RED}})
        .build()
    )

    data = matrix.build.to_json()
    base = data[matrix.base_index]
    empty_parts = [
        block
        for block in data
        if block[0] == "Part" and block[2].get("RGB") == [0, 0, 0]
    ]

    assert len(empty_parts) == 2
    empty_part = empty_parts[0]
    assert len(empty_part[1]) == 1
    connection = empty_part[1][0]
    assert connection[0] == "1"
    assert connection[2] == matrix.base_index + 1
    assert connection[1] in base[2]["EphemeralAttachments"]
    assert validate_build_json(data) == (True, None)
