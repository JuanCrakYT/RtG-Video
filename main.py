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
from src.export.rtg_exporter import CombinedExporter
from src.ui.gui import launch_gui


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
    
    # Create animation sequence
    print("Creating animation sequence...")
    
    builder = SequenceBuilder()
    
    # Frame 1: Checkerboard pattern (corners active)
    frame1 = (
        FrameBuilder(duration=0.1)
        .set_frame_number(0)
        .build()
    )
    for x in range(width):
        for y in range(height):
            if (x + y) % 2 == 0:
                pixel = matrix.get_pixel(x, y)
                if pixel:
                    frame1.add_pixel(pixel.uuid)
    builder.add_frame(frame1)
    
    # Frame 2: Inverse checkerboard
    frame2 = (
        FrameBuilder(duration=0.1)
        .set_frame_number(1)
        .build()
    )
    for x in range(width):
        for y in range(height):
            if (x + y) % 2 == 1:
                pixel = matrix.get_pixel(x, y)
                if pixel:
                    frame2.add_pixel(pixel.uuid)
    builder.add_frame(frame2)
    
    # Frame 3: All active
    frame3 = (
        FrameBuilder(duration=0.1)
        .set_frame_number(2)
        .build()
    )
    for x in range(width):
        for y in range(height):
            pixel = matrix.get_pixel(x, y)
            if pixel:
                frame3.add_pixel(pixel.uuid)
    builder.add_frame(frame3)
    
    sequence = builder.build()
    
    print(f"✓ Animation created:")
    print(f"  - Frames: {sequence.get_frame_count()}")
    print(f"  - Total duration: {sequence.get_total_duration():.2f}s\n")
    
    # Export
    print(f"Exporting to {output_dir}...")
    
    export_paths = CombinedExporter.export_complete(
        matrix, sequence, output_dir, compact=False
    )
    
    print(f"✓ Export complete:")
    for key, path in export_paths.items():
        print(f"  - {key}: {path}")
    
    print(f"\n{'='*60}")
    print("Demo completed successfully!")
    print(f"{'='*60}\n")
    
    return True


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
        "--cli",
        action="store_true",
        help="Run in CLI mode (no GUI)"
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
    
    if args.demo:
        success = run_demo(
            width=args.width,
            height=args.height,
            output_dir=args.output,
            use_fallback=args.fallback
        )
        sys.exit(0 if success else 1)
    elif args.cli:
        parser.print_help()
    else:
        # Launch GUI
        launch_gui()


if __name__ == "__main__":
    main()
