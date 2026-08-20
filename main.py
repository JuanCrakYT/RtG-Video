"""
RtG Display - Main entry point

Generates pixel matrices for animated displays compatible with Road To Gramby's (RtG).
Includes both GUI and CLI modes.
"""

import argparse
import json
import sys
from pathlib import Path

from src.config import DEFAULT_DISPLAY_WIDTH, DEFAULT_DISPLAY_HEIGHT, DEFAULT_PIXEL_SPACING
from src.rtg.format import load_pixel_template_from_file
from src.rtg.uuid import reset_uuid_manager
from src.display.pixel import PixelTemplate
from src.display.matrix import MatrixBuilder
from src.animation.frame import FrameBuilder
from src.animation.sequence import SequenceBuilder
from src.animation.signal_logic import build_signal_network, resolve_pixel_inputs
from src.export.rtg_exporter import CombinedExporter, RtGExporter
from src.ui.gui import launch_gui
from src.video.processing import BLACK, WHITE, GRAY, video_to_sequence


def load_real_pixel_template(template_path: str = None):
    """
    Load the real pixel template from file.
    
    Args:
        template_path: Path to pixel.json template file
        
    Returns:
        PixelTemplate: The loaded template
    """
    if template_path is None:
        # Try to find pixel.json in common locations
        candidates = [
            Path("assets/pixel/pixel.json"),
            Path("./assets/pixel/pixel.json"),
            Path("../../assets/pixel/pixel.json"),
        ]
        
        for candidate in candidates:
            if candidate.exists():
                template_path = str(candidate)
                break
        else:
            raise FileNotFoundError("Could not find pixel.json template")
    
    print(f"Loading pixel template from: {template_path}")
    template_build = load_pixel_template_from_file(template_path)
    return PixelTemplate(template_build)


def create_simple_pixel_build():
    """
    Create a simple pixel template for testing (fallback if pixel.json not found).
    
    Returns:
        PixelTemplate: A simple test template
    """
    from src.rtg.blocks import RtGBuild, RtGBlock
    
    build = RtGBuild()
    
    # Add a simple 3-block pixel structure
    build.create_base()
    
    # Add connector blocks
    for i in range(3):
        block = RtGBlock("Connector")
        build.add_block(block)
    
    return PixelTemplate(build)


def run_demo(
    width: int = 2,
    height: int = 2,
    output_dir: str = "output",
    use_fallback: bool = False
):
    """
    Run a demo of the RtG Display system.
    
    Args:
        width: Display width in pixels
        height: Display height in pixels
        output_dir: Directory to save output
        use_fallback: Use simple template if real one not found
    """
    print(f"\n{'='*60}")
    print("RtG Display - Demo")
    print(f"{'='*60}\n")
    
    # Reset UUID manager for fresh demo
    reset_uuid_manager()
    
    # Load pixel template
    try:
        pixel_template = load_real_pixel_template()
        print(f"✓ Loaded real pixel template\n")
    except FileNotFoundError as e:
        if use_fallback:
            print(f"⚠ {e}")
            print("Using fallback simple template...\n")
            pixel_template = create_simple_pixel_build()
        else:
            print(f"✗ Error: {e}")
            return False
    
    # Create display matrix
    print(f"Creating {width}×{height} display matrix...")
    matrix = (
        MatrixBuilder()
        .set_dimensions(width, height)
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
        .build()
    )
    
    stats = matrix.get_stats()
    print(f"✓ Display created:")
    print(f"  - Total pixels: {stats['total_pixels']}")
    print(f"  - Total blocks: {stats['total_blocks']}")
    print(f"  - Dimensions: {stats['width']}×{stats['height']}\n")
    
    # Export only the physical canvas at this stage.
    print(f"Exporting to {output_dir}...")
    output_path = Path(output_dir) / "display.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    RtGExporter.save_display(matrix, str(output_path), compact=False)
    print(f"✓ Physical canvas exported: {output_path}")
    
    print(f"\n{'='*60}")
    print("Demo completed successfully!")
    print(f"{'='*60}\n")
    
    return True


def generate_canvas_build(settings):
    """Generate only the physical canvas and export its display JSON."""
    reset_uuid_manager()
    pixel_template = load_real_pixel_template(
        settings.get("pixel_template")
    )
    matrix = (
        MatrixBuilder()
        .set_dimensions(int(settings["width"]), int(settings["height"]))
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
        .build()
    )
    output_path = Path(settings.get("output_dir", "output")) / "display.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    RtGExporter.save_display(matrix, str(output_path), compact=False)
    return {"display": str(output_path), "stats": matrix.get_stats()}


def run_color_demo(output_dir: str = "output/color_demo"):
    """Export one real pixel over eight black, white, and gray frames."""
    reset_uuid_manager()
    pixel_template = load_real_pixel_template()
    matrix = (
        MatrixBuilder()
        .set_dimensions(1, 1)
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
        .build()
    )
    pixel = matrix.get_pixel(0, 0)
    colors = [WHITE, BLACK, GRAY, WHITE, BLACK, GRAY, WHITE, BLACK]
    builder = SequenceBuilder()
    for color in colors:
        frame = FrameBuilder(duration=0.1).set_frame_number(len(builder.frames))
        frame.set_pixel_color(pixel.uuid, color)
        builder.add_frame(frame.build())
    sequence = builder.build()
    pixel_inputs = resolve_pixel_inputs(matrix.pixels.values())
    build_signal_network(
        matrix.build,
        {index: [pixel.uuid] for index in range(len(sequence.frames))},
        pixel_inputs,
        [frame.duration for frame in sequence.frames],
    )
    paths = CombinedExporter.export_complete(matrix, sequence, output_dir)
    print(f"Exported 1 pixel / 8 color frames to {output_dir}")
    print(f"Palette: black={BLACK}, white={WHITE}, gray={GRAY}")
    for key, path in paths.items():
        print(f"  - {key}: {path}")
    return True


def generate_video_build(settings):
    """Run resize, nearest-palette quantization, physical wiring, and export."""
    reset_uuid_manager()
    pixel_template = load_real_pixel_template(settings["pixel_template"] if "pixel_template" in settings else None)
    matrix = (
        MatrixBuilder()
        .set_dimensions(settings["width"], settings["height"])
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
        .build()
    )
    sequence = video_to_sequence(
        settings["video"],
        matrix,
        settings.get("palette", [BLACK, WHITE, GRAY]),
    )
    build_signal_network(
        matrix.build,
        {
            index: frame.get_active_pixels()
            for index, frame in enumerate(sequence.frames)
        },
        resolve_pixel_inputs(matrix.pixels.values()),
        [frame.duration for frame in sequence.frames],
    )
    return CombinedExporter.export_complete(matrix, sequence, "output")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RtG Display - Animated display generator"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode (CLI)"
    )

    parser.add_argument(
        "--color-demo",
        action="store_true",
        help="Export one pixel with eight black, white, and gray frames"
    )
    
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode (no GUI)"
    )
    
    parser.add_argument(
        "--gui-demo",
        action="store_true",
        help="Run interactive GUI demo"
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_DISPLAY_WIDTH,
        help=f"Display width in pixels (default: {DEFAULT_DISPLAY_WIDTH})"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_DISPLAY_HEIGHT,
        help=f"Display height in pixels (default: {DEFAULT_DISPLAY_HEIGHT})"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Use fallback simple pixel template if real one not found"
    )
    
    args = parser.parse_args()
    
    if args.color_demo:
        success = run_color_demo(output_dir=args.output)
        sys.exit(0 if success else 1)
    elif args.demo:
        success = run_demo(
            width=args.width,
            height=args.height,
            output_dir=args.output,
            use_fallback=args.fallback
        )
        sys.exit(0 if success else 1)
    elif args.gui_demo:
        # Import here to avoid issues on headless systems
        from demo_gui import demo_gui
        demo_gui()
    elif args.cli:
        parser.print_help()
    else:
        # Launch GUI
        try:
            launch_gui(on_generate=generate_canvas_build)
        except Exception as e:
            print(f"Error launching GUI: {e}")
            print("Try: python main.py --demo")
            sys.exit(1)


if __name__ == "__main__":
    main()
