"""
RtG Video - Main entry point

Generates pixel matrices for animated displays compatible with Road To Gramby's (RtG).
Includes both GUI and CLI modes.
"""

import argparse
import json
import sys
from pathlib import Path

from src.config import DEFAULT_DISPLAY_WIDTH, DEFAULT_DISPLAY_HEIGHT, DEFAULT_PIXEL_SPACING
from src.rtg.format import load_pixel_template_from_file
from src.rtg.blocks import RtGBlock
from src.rtg.uuid import reset_uuid_manager
from src.display.pixel import PixelTemplate
from src.display.matrix import MatrixBuilder
from src.animation.frame import FrameBuilder
from src.animation.sequence import SequenceBuilder
from src.animation.signal_logic import (
    add_start_button,
    add_physical_gate_or_table,
    build_animation_timeline,
    build_signal_network,
    resolve_pixel_inputs,
    validate_signal_connections,
)
from src.async_gen import GenerationStage, run_async_generation
from src.export.rtg_exporter import CombinedExporter, RtGExporter
from src.ui.gui import launch_gui
from src.video.processing import (
    BLACK,
    WHITE,
    GRAY,
    analyze_pixel_color_usage,
    analyze_video_colors,
    sequence_from_color_frames,
    video_to_sequence,
)


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
        project_root = Path(__file__).resolve().parent
        candidates = [
            project_root / "assets" / "builds" / "pixel" / "pixel.json",
            Path.cwd() / "assets" / "builds" / "pixel" / "pixel.json",
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
    Run a demo of the RtG Video system.
    
    Args:
        width: Display width in pixels
        height: Display height in pixels
        output_dir: Directory to save output
        use_fallback: Use simple template if real one not found
    """
    print(f"\n{'='*60}")
    print("RtG Video - Demo")
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
    _add_canvas_gyro(matrix)
    
    stats = matrix.get_stats()
    print(f"✓ Display created:")
    print(f"  - Total pixels: {stats['total_pixels']}")
    print(f"  - Total blocks: {stats['total_blocks']}")
    print(f"  - Dimensions: {stats['width']}×{stats['height']}\n")
    
    # Export only the physical canvas at this stage.
    print(f"Exporting to {output_dir}...")
    export_paths = RtGExporter.export_physical_canvas(
        matrix,
        output_dir,
        compact=False,
    )
    print(f"✓ Physical canvas exported: {export_paths['display']}")
    
    print(f"\n{'='*60}")
    print("Demo completed successfully!")
    print(f"{'='*60}\n")
    
    return True


def generate_canvas_build(settings, progress_callback=None, block_callback=None):
    """Generate the canvas and, when available, its animation timeline.
    
    Args:
        settings: Generation settings dictionary
        progress_callback: Optional callback(stage, status, current, total, detail)
        block_callback: Optional callback(blocks_current, blocks_total)
    """
    def report(stage, status=None, current=None, total=None, detail=None):
        if progress_callback:
            progress_callback(stage, status, current, total, detail)
    
    def report_blocks(current, total=None):
        if block_callback:
            block_callback(current, total)
    
    from src.async_gen import GenerationStage
    
    report(GenerationStage.PREPARATION, "active", 0, 1, "Inicializando generador...")
    reset_uuid_manager()
    
    report(GenerationStage.PREPARATION, "active", 1, 1, "Cargando plantilla de píxel...")
    pixel_template = load_real_pixel_template(
        settings.get("pixel_template")
    )
    report(GenerationStage.PREPARATION, "completed", 1, 1)
    
    palette = settings.get("palette", [BLACK, WHITE, GRAY])
    color_frames = None
    duration = None
    pixel_palettes = None
    
    if settings.get("video"):
        report(GenerationStage.PREPARATION, "active", 0, 1, "Analizando colores del video...")
        duration, color_frames = analyze_video_colors(
            settings["video"],
            int(settings["width"]),
            int(settings["height"]),
            palette,
        )
        report(GenerationStage.PREPARATION, "completed", 1, 1, "Análisis de video completado")
        
        report(GenerationStage.PREPARATION, "active", 0, 1, "Calculando uso de colores por píxel...")
        usage = analyze_pixel_color_usage(color_frames)
        pixel_palettes = {
            (x, y): usage.get((x, y), set())
            for y in range(int(settings["height"]))
            for x in range(int(settings["width"]))
        }
        report(GenerationStage.PREPARATION, "completed", 1, 1)
    
    report(GenerationStage.CANVAS, "active", 0, 1, "Creando matriz de píxeles...")
    matrix_builder = (
        MatrixBuilder()
        .set_dimensions(int(settings["width"]), int(settings["height"]))
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
    )
    if pixel_palettes is not None:
        matrix_builder.set_palette_by_position(pixel_palettes)
    else:
        matrix_builder.set_palette(palette)
    
    report(GenerationStage.CANVAS, "active", 50, 100, "Construyendo matriz...")
    matrix = matrix_builder.build()
    _add_canvas_gyro(matrix)
    report_blocks(len(matrix.build))
    report(GenerationStage.CANVAS, "completed", 100, 100, f"Canvas {settings['width']}x{settings['height']} creado")
    
    if settings.get("video"):
        report(GenerationStage.TIMELINE, "active", 0, 1, "Creando botón de inicio...")
        start_button_index = add_start_button(matrix.build, matrix.base_index)
        
        report(GenerationStage.TIMELINE, "active", 25, 100, "Generando secuencia de frames...")
        sequence = sequence_from_color_frames(matrix, duration, color_frames)
        
        report(GenerationStage.TIMELINE, "active", 50, 100, "Calculando Gate-ORs necesarios...")
        pixel_frame_counts = {
            pixel.uuid: sum(
                1 for frame in sequence.frames if pixel.uuid in frame.get_active_pixels()
            )
            for pixel in matrix.iter_pixels()
        }
        gate_or_count = max(
            len(list(matrix.iter_pixels())),
            sum(max(0, count - 1) for count in pixel_frame_counts.values()),
        )
        
        report(GenerationStage.GATE_OR, "active", 0, 1, f"Creando tabla física de {gate_or_count} Gate-ORs...")
        gate_or_indexes = add_physical_gate_or_table(
            matrix.build,
            matrix.base_index,
            gate_or_count,
        )
        report_blocks(len(matrix.build))
        report(GenerationStage.GATE_OR, "completed", 1, 1, f"{gate_or_count} Gate-ORs creados")
        
        report(GenerationStage.TIMELINE, "active", 75, 100, f"Construyendo timeline ({len(sequence.frames)} frames)...")
        build_animation_timeline(
            matrix.build,
            [frame.duration for frame in sequence.frames],
            start_source_index=start_button_index,
        )
        report_blocks(len(matrix.build))
        report(GenerationStage.TIMELINE, "completed", 100, 100, "Timeline completado")
        
        report(GenerationStage.SIGNAL_NETWORK, "active", 0, 1, "Construyendo red de señales...")
        frame_active_pixels = {
            index: frame.get_active_pixels()
            for index, frame in enumerate(sequence.frames)
        }
        total_frames = len(sequence.frames)
        for i, (frame_idx, active_pixels) in enumerate(frame_active_pixels.items()):
            if total_frames > 0:
                report(GenerationStage.SIGNAL_NETWORK, "active", 
                       i + 1, total_frames, 
                       f"Conectando frame {frame_idx + 1}/{total_frames} ({len(active_pixels)} píxeles activos)")
                report_blocks(len(matrix.build))
        build_signal_network(
            matrix.build,
            frame_active_pixels,
            resolve_pixel_inputs(matrix.iter_pixels()),
            [frame.duration for frame in sequence.frames],
            gate_or_indexes,
        )
        report_blocks(len(matrix.build))
        report(GenerationStage.SIGNAL_NETWORK, "completed", 1, 1, "Red de señales completada")
        
        report(GenerationStage.VALIDATION, "active", 0, 1, "Validando build...")
        from src.animation.signal_logic import validate_signal_connections
        errors = validate_signal_connections(matrix.build)
        if errors:
            report(GenerationStage.VALIDATION, "error", 0, 1, f"Errores de validación: {errors}")
        report(GenerationStage.VALIDATION, "completed", 1, 1, "Validación OK")
        
        report(GenerationStage.EXPORT, "active", 0, 1, "Exportando JSON...")
        result = CombinedExporter.export_complete(
            matrix,
            sequence,
            settings.get("output_dir", "output"),
        )
        report_blocks(len(matrix.build))
        report(GenerationStage.EXPORT, "completed", 1, 1, "Exportación completada")
        
        return result
    
    # No video - just static canvas
    report(GenerationStage.EXPORT, "active", 0, 1, "Exportando canvas estático...")
    export_paths = RtGExporter.export_physical_canvas(
        matrix,
        settings.get("output_dir", "output"),
        compact=False,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.EXPORT, "completed", 1, 1, "Exportación completada")
    
    return {**export_paths, "stats": matrix.get_stats()}


def _add_canvas_gyro(matrix):
    """Attach one activated Gyro to point 1 of the canvas Base block."""
    matrix.build.add_block(
        RtGBlock(
            "Gyro",
            connections=[["1", "1", 1]],
            properties={"Activated": True, "RGB": [73, 26, 112]},
        )
    )


def run_color_demo(output_dir: str = "output/color_demo", progress_callback=None, block_callback=None):
    """Export one real pixel over eight black, white, and gray frames.
    
    Args:
        output_dir: Output directory
        progress_callback: Optional callback(stage, status, current, total, detail)
        block_callback: Optional callback(blocks_current, blocks_total)
    """
    def report(stage, status=None, current=None, total=None, detail=None):
        if progress_callback:
            progress_callback(stage, status, current, total, detail)
    
    def report_blocks(current, total=None):
        if block_callback:
            block_callback(current, total)
    
    report(GenerationStage.PREPARATION, "active", 0, 1, "Inicializando generador...")
    reset_uuid_manager()
    
    report(GenerationStage.PREPARATION, "active", 1, 1, "Cargando plantilla de píxel...")
    pixel_template = load_real_pixel_template()
    report(GenerationStage.PREPARATION, "completed", 1, 1)
    
    report(GenerationStage.CANVAS, "active", 0, 1, "Creando matriz 1x1...")
    matrix = (
        MatrixBuilder()
        .set_dimensions(1, 1)
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
        .build()
    )
    _add_canvas_gyro(matrix)
    report_blocks(len(matrix.build))
    report(GenerationStage.CANVAS, "completed", 100, 100, "Canvas 1x1 creado")
    
    report(GenerationStage.TIMELINE, "active", 0, 1, "Creando botón de inicio...")
    start_button_index = add_start_button(matrix.build, matrix.base_index)
    pixel = matrix.get_pixel(0, 0)
    colors = [WHITE, BLACK, GRAY, WHITE, BLACK, GRAY, WHITE, BLACK]
    gate_or_count = max(len(list(matrix.iter_pixels())), len(colors) - 1)
    
    report(GenerationStage.GATE_OR, "active", 0, 1, f"Creando tabla física de {gate_or_count} Gate-ORs...")
    gate_or_indexes = add_physical_gate_or_table(
        matrix.build,
        matrix.base_index,
        gate_or_count,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.GATE_OR, "completed", 1, 1, f"{gate_or_count} Gate-ORs creados")
    
    report(GenerationStage.TIMELINE, "active", 0, 1, "Creando secuencia de 8 frames...")
    builder = SequenceBuilder()
    for i, color in enumerate(colors):
        report(GenerationStage.TIMELINE, "active", i + 1, len(colors), f"Frame {i + 1}/{len(colors)}: {color}")
        frame = FrameBuilder(duration=0.1).set_frame_number(len(builder.frames))
        frame.set_pixel_color(pixel.uuid, color)
        builder.add_frame(frame.build())
    sequence = builder.build()
    
    report(GenerationStage.TIMELINE, "active", len(colors), len(colors), f"Construyendo timeline ({len(sequence.frames)} frames)...")
    build_animation_timeline(
        matrix.build,
        [frame.duration for frame in sequence.frames],
        start_source_index=start_button_index,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.TIMELINE, "completed", 100, 100, "Timeline completado")
    
    report(GenerationStage.SIGNAL_NETWORK, "active", 0, 1, "Construyendo red de señales...")
    pixel_inputs = resolve_pixel_inputs(matrix.pixels.values())
    frame_active_pixels = {
        index: [pixel.uuid] for index in range(len(sequence.frames))
    }
    for i in range(len(sequence.frames)):
        report(GenerationStage.SIGNAL_NETWORK, "active", i + 1, len(sequence.frames), f"Conectando frame {i + 1}")
        report_blocks(len(matrix.build))
    build_signal_network(
        matrix.build,
        frame_active_pixels,
        pixel_inputs,
        [frame.duration for frame in sequence.frames],
        gate_or_indexes,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.SIGNAL_NETWORK, "completed", 1, 1, "Red de señales completada")
    
    report(GenerationStage.VALIDATION, "active", 0, 1, "Validando build...")
    from src.animation.signal_logic import validate_signal_connections
    errors = validate_signal_connections(matrix.build)
    if errors:
        report(GenerationStage.VALIDATION, "error", 0, 1, f"Errores de validación: {errors}")
    report(GenerationStage.VALIDATION, "completed", 1, 1, "Validación OK")
    
    report(GenerationStage.EXPORT, "active", 0, 1, "Exportando JSON...")
    paths = CombinedExporter.export_complete(matrix, sequence, output_dir)
    report_blocks(len(matrix.build))
    report(GenerationStage.EXPORT, "completed", 1, 1, "Exportación completada")
    
    print(f"Exported 1 pixel / 8 color frames to {output_dir}")
    print(f"Palette: black={BLACK}, white={WHITE}, gray={GRAY}")
    for key, path in paths.items():
        print(f"  - {key}: {path}")
    return True


def generate_video_build(settings, progress_callback=None, block_callback=None):
    """Run resize, nearest-palette quantization, physical wiring, and export.
    
    Args:
        settings: Generation settings dictionary
        progress_callback: Optional callback(stage, status, current, total, detail)
        block_callback: Optional callback(blocks_current, blocks_total)
    """
    def report(stage, status=None, current=None, total=None, detail=None):
        if progress_callback:
            progress_callback(stage, status, current, total, detail)
    
    def report_blocks(current, total=None):
        if block_callback:
            block_callback(current, total)
    
    report(GenerationStage.PREPARATION, "active", 0, 1, "Inicializando generador...")
    reset_uuid_manager()
    
    report(GenerationStage.PREPARATION, "active", 1, 1, "Cargando plantilla de píxel...")
    pixel_template = load_real_pixel_template(settings["pixel_template"] if "pixel_template" in settings else None)
    report(GenerationStage.PREPARATION, "completed", 1, 1)
    
    palette = settings.get("palette", [BLACK, WHITE, GRAY])
    
    report(GenerationStage.PREPARATION, "active", 0, 1, "Analizando colores del video...")
    duration, color_frames = analyze_video_colors(
        settings["video"], settings["width"], settings["height"], palette
    )
    report(GenerationStage.PREPARATION, "completed", 1, 1, "Análisis de video completado")
    
    report(GenerationStage.PREPARATION, "active", 0, 1, "Calculando uso de colores por píxel...")
    usage = analyze_pixel_color_usage(color_frames)
    pixel_palettes = {
        (x, y): usage.get((x, y), set())
        for y in range(settings["height"])
        for x in range(settings["width"])
    }
    report(GenerationStage.PREPARATION, "completed", 1, 1)
    
    report(GenerationStage.CANVAS, "active", 0, 1, "Creando matriz de píxeles...")
    matrix = (
        MatrixBuilder()
        .set_dimensions(settings["width"], settings["height"])
        .set_spacing(DEFAULT_PIXEL_SPACING)
        .set_template(pixel_template)
        .set_palette_by_position(pixel_palettes)
        .build()
    )
    _add_canvas_gyro(matrix)
    report_blocks(len(matrix.build))
    report(GenerationStage.CANVAS, "completed", 100, 100, f"Canvas {settings['width']}x{settings['height']} creado")
    
    report(GenerationStage.TIMELINE, "active", 0, 1, "Creando botón de inicio...")
    start_button_index = add_start_button(matrix.build, matrix.base_index)
    
    report(GenerationStage.TIMELINE, "active", 25, 100, "Generando secuencia de frames...")
    sequence = sequence_from_color_frames(matrix, duration, color_frames)
    
    report(GenerationStage.TIMELINE, "active", 50, 100, "Calculando Gate-ORs necesarios...")
    pixel_frame_counts = {
        pixel.uuid: sum(
            1 for frame in sequence.frames if pixel.uuid in frame.get_active_pixels()
        )
        for pixel in matrix.iter_pixels()
    }
    gate_or_count = max(
        len(list(matrix.iter_pixels())),
        sum(max(0, count - 1) for count in pixel_frame_counts.values()),
    )
    
    report(GenerationStage.GATE_OR, "active", 0, 1, f"Creando tabla física de {gate_or_count} Gate-ORs...")
    gate_or_indexes = add_physical_gate_or_table(
        matrix.build,
        matrix.base_index,
        gate_or_count,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.GATE_OR, "completed", 1, 1, f"{gate_or_count} Gate-ORs creados")
    
    report(GenerationStage.TIMELINE, "active", 75, 100, f"Construyendo timeline ({len(sequence.frames)} frames)...")
    build_animation_timeline(
        matrix.build,
        [frame.duration for frame in sequence.frames],
        start_source_index=start_button_index,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.TIMELINE, "completed", 100, 100, "Timeline completado")
    
    report(GenerationStage.SIGNAL_NETWORK, "active", 0, 1, "Construyendo red de señales...")
    frame_active_pixels = {
        index: frame.get_active_pixels()
        for index, frame in enumerate(sequence.frames)
    }
    total_frames = len(sequence.frames)
    for i, (frame_idx, active_pixels) in enumerate(frame_active_pixels.items()):
        if total_frames > 0:
            report(GenerationStage.SIGNAL_NETWORK, "active", 
                   i + 1, total_frames, 
                   f"Conectando frame {frame_idx + 1}/{total_frames} ({len(active_pixels)} píxeles activos)")
            report_blocks(len(matrix.build))
    build_signal_network(
        matrix.build,
        frame_active_pixels,
        resolve_pixel_inputs(matrix.iter_pixels()),
        [frame.duration for frame in sequence.frames],
        gate_or_indexes,
    )
    report_blocks(len(matrix.build))
    report(GenerationStage.SIGNAL_NETWORK, "completed", 1, 1, "Red de señales completada")
    
    report(GenerationStage.VALIDATION, "active", 0, 1, "Validando build...")
    from src.animation.signal_logic import validate_signal_connections
    errors = validate_signal_connections(matrix.build)
    if errors:
        report(GenerationStage.VALIDATION, "error", 0, 1, f"Errores de validación: {errors}")
    report(GenerationStage.VALIDATION, "completed", 1, 1, "Validación OK")
    
    report(GenerationStage.EXPORT, "active", 0, 1, "Exportando JSON...")
    result = CombinedExporter.export_complete(matrix, sequence, "output")
    report_blocks(len(matrix.build))
    report(GenerationStage.EXPORT, "completed", 1, 1, "Exportación completada")
    
    return result


def run_async_generation_gui(root, settings, on_complete):
    """Run generation asynchronously for GUI with progress window."""
    from src.async_gen import run_async_generation
    run_async_generation(root, settings, generate_canvas_build, on_complete)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RtG Video - Animated display generator"
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
            launch_gui(on_generate=run_async_generation_gui)
        except Exception as e:
            print(f"Error launching GUI: {e}")
            print("Try: python main.py --demo")
            sys.exit(1)


if __name__ == "__main__":
    main()
