"""Regression tests for synchronized physical-canvas output generations."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.display.matrix import MatrixBuilder
from src.display.pixel import PixelTemplate
from src.export.rtg_exporter import RtGExporter
from src.rtg.format import load_pixel_template_from_file
from src.rtg.uuid import reset_uuid_manager


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "assets" / "pixel" / "pixel.json"


def generate_physical_canvas(width: int, height: int, output_dir: str):
    reset_uuid_manager()
    template = PixelTemplate(load_pixel_template_from_file(str(TEMPLATE_PATH)))
    matrix = (
        MatrixBuilder()
        .set_dimensions(width, height)
        .set_spacing(4.0)
        .set_template(template)
        .build()
    )
    return matrix, RtGExporter.export_physical_canvas(matrix, output_dir)


def read_generation(output_dir: Path):
    display = json.loads((output_dir / "display.json").read_text(encoding="utf-8"))
    info = json.loads((output_dir / "info.json").read_text(encoding="utf-8"))
    return display, info


def assert_generation(output_dir: Path, width: int, height: int):
    display, info = read_generation(output_dir)
    display_info = info["display"]
    expected_pixels = width * height
    expected_blocks = 1 + expected_pixels * 21

    assert display_info["width"] == width
    assert display_info["height"] == height
    assert display_info["total_pixels"] == expected_pixels
    assert display_info["total_blocks"] == expected_blocks
    assert sum(block[0] == "Base" for block in display) == 1
    assert sum(block[0] == "Splitter_3" for block in display) == expected_pixels
    assert not (output_dir / "animation.json").exists()
    assert set(path.name for path in output_dir.iterdir()) == {"display.json", "info.json"}


def test_repeated_physical_generations_stay_synchronized():
    with TemporaryDirectory() as temporary_directory:
        output_dir = Path(temporary_directory)
        (output_dir / "animation.json").write_text("stale animation", encoding="utf-8")

        generate_physical_canvas(2, 2, str(output_dir))
        assert_generation(output_dir, 2, 2)

        generate_physical_canvas(5, 5, str(output_dir))
        assert_generation(output_dir, 5, 5)

        generate_physical_canvas(2, 2, str(output_dir))
        assert_generation(output_dir, 2, 2)
