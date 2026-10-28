import sys
sys.path.insert(0, '.')

from src.rtg.format import load_pixel_template_from_file
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
)
from src.video.processing import WHITE, BLACK, GRAY
from src.rtg.uuid import reset_uuid_manager
from main import _add_canvas_gyro

reset_uuid_manager()

template_path = 'assets/builds/pixel/pixel.json'
template_build = load_pixel_template_from_file(template_path)
pixel_template = PixelTemplate(template_build)

matrix = (
    MatrixBuilder()
    .set_dimensions(1, 1)
    .set_spacing(0.75)
    .set_template(pixel_template)
    .build()
)

_add_canvas_gyro(matrix)

start_button_index = add_start_button(matrix.build, matrix.base_index)

colors = [WHITE, BLACK, GRAY, WHITE, BLACK, GRAY, WHITE, BLACK]
gate_or_count = max(len(list(matrix.iter_pixels())), len(colors) - 1)

gate_or_indexes = add_physical_gate_or_table(matrix.build, matrix.base_index, gate_or_count)

builder = SequenceBuilder()
for i, color in enumerate(colors):
    frame = FrameBuilder(duration=0.1).set_frame_number(len(builder.frames))
    frame.set_pixel_color(list(matrix.pixels.values())[0].uuid, color)
    builder.add_frame(frame.build())
sequence = builder.build()

timeline_delayer_indexes = build_animation_timeline(
    matrix.build,
    [frame.duration for frame in sequence.frames],
    start_source_index=start_button_index,
)

pixel_inputs = resolve_pixel_inputs(matrix.pixels.values())
frame_active_pixels = {
    index: [list(matrix.pixels.values())[0].uuid] for index in range(len(sequence.frames))
}

build_signal_network(
    matrix.build,
    frame_active_pixels,
    pixel_inputs,
    [frame.duration for frame in sequence.frames],
    gate_or_indexes,
    timeline_delayer_indexes,
)

print(f"\n=== FINAL BUILD ({len(matrix.build.blocks)} blocks) ===")

# Print all Gate-ORs with connections
print("\nGate-ORs:")
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Gate-OR':
        print(f"  [{i}] Gate-OR: conn={b.connections}")

# Print all Wires
print("\nWires:")
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Wire':
        print(f"  [{i}] Wire: conn={b.connections}")

# Print Delayers
print("\nDelayers:")
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Delayer':
        print(f"  [{i}] Delayer Frame={b.properties.get('Frame')}: conn={b.connections}")

# Print Splitter_3
print("\nSplitter_3:")
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Splitter_3':
        print(f"  [{i}] Splitter_3: conn={b.connections}")

# Count blocks
from collections import Counter
types = Counter(b.block_type for b in matrix.build.blocks)
print("\nBlock counts:")
for t, c in sorted(types.items()):
    print(f"  {t}: {c}")