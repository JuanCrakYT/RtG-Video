"""Focused tests for the physical pixel canvas only."""

import json
from pathlib import Path

from src.display.matrix import MatrixBuilder
from src.display.pixel import PixelTemplate
from src.rtg.format import load_pixel_template_from_file, save_build
from src.rtg.uuid import reset_uuid_manager


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "assets" / "pixel" / "pixel.json"


def build_canvas(width: int, height: int):
    reset_uuid_manager()
    template = PixelTemplate(load_pixel_template_from_file(str(TEMPLATE_PATH)))
    return (
        MatrixBuilder()
        .set_dimensions(width, height)
        .set_spacing(4.0)
        .set_template(template)
        .build()
    )


def test_3x2_physical_canvas():
    matrix = build_canvas(3, 2)
    template = load_pixel_template_from_file(str(TEMPLATE_PATH))
    blocks = matrix.build.blocks

    assert sum(block.block_type == "Base" for block in blocks) == 1
    assert len(matrix.pixels) == 6
    assert len({pixel.uuid for pixel in matrix.pixels.values()}) == 6
    assert all(
        pixel.get_block_count() == len(template.blocks)
        for pixel in matrix.pixels.values()
    )
    for pixel in matrix.pixels.values():
        assert [block.block_type for block in pixel.blocks] == [
            block.block_type for block in template.blocks
        ]
        assert [block.properties for block in pixel.blocks] == [
            block.properties for block in template.blocks
        ]
    assert all(block.block_type != "Delayer" for block in blocks)
    assert all(block.block_type != "Gate-OR" for block in blocks)
    assert all(block.block_type != "Wire" for block in blocks)
    assert all(block.block_type != "Note" for block in blocks)

    positions = matrix.build.blocks[matrix.base_index].properties["EphemeralAttachments"]
    assert len(positions) == 6
    assert len({tuple(attachment["cframe"][:2]) for attachment in positions.values()}) == 6

    for (x, y), pixel in matrix.pixels.items():
        assert matrix.get_pixel(x, y) is pixel
        assert positions[pixel.uuid]["cframe"][:3] == [x * 4.0, y * 4.0, 0.0]


def test_2x2_export_is_one_physical_build():
    matrix = build_canvas(2, 2)
    output_path = ROOT / "output" / "canvas_2x2" / "display.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_build(matrix.build, str(output_path))

    data = json.loads(output_path.read_text())
    assert sum(block[0] == "Base" for block in data) == 1
    assert sum(block[0] == "Splitter_3" for block in data) == 4
    assert not any(block[0] in {"Delayer", "Gate-OR", "Wire", "Note"} for block in data)
