"""Debug script: inspect build state BEFORE export vs AFTER export."""
from src.rtg.uuid import reset_uuid_manager
from src.display.matrix import MatrixBuilder
from src.display.pixel import PixelTemplate
from src.rtg.format import load_pixel_template_from_file, build_to_json_string
from src.animation.signal_logic import (
    add_start_button, add_physical_gate_or_table,
    build_animation_timeline, build_signal_network, resolve_pixel_inputs
)
from src.video.processing import sequence_from_color_frames
import json

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Simulate generate_canvas_build video path with 2x2, 3 frames
reset_uuid_manager()
pixel_template = PixelTemplate(load_pixel_template_from_file('assets/builds/pixel/pixel.json'))
matrix = MatrixBuilder().set_dimensions(2, 2).set_palette([BLACK, WHITE]).set_template(pixel_template).build()

color_frames = [
    [[WHITE, BLACK], [BLACK, WHITE]],
    [[BLACK, WHITE], [WHITE, BLACK]],
    [[WHITE, WHITE], [BLACK, BLACK]],
]
duration = 0.1

start_button_index = add_start_button(matrix.build, matrix.base_index)
sequence = sequence_from_color_frames(matrix, duration, color_frames)

pixel_frame_counts = {
    pixel.uuid: sum(1 for frame in sequence.frames if pixel.uuid in frame.get_active_pixels())
    for pixel in matrix.iter_pixels()
}
gate_or_count = max(
    len(list(matrix.iter_pixels())),
    sum(max(0, count - 1) for count in pixel_frame_counts.values()),
)

gate_or_indexes = add_physical_gate_or_table(matrix.build, matrix.base_index, gate_or_count)
build_animation_timeline(matrix.build, [frame.duration for frame in sequence.frames], start_source_index=start_button_index)
build_signal_network(
    matrix.build,
    {index: frame.get_active_pixels() for index, frame in enumerate(sequence.frames)},
    resolve_pixel_inputs(matrix.iter_pixels()),
    [frame.duration for frame in sequence.frames],
    gate_or_indexes,
)

print('=== IN-MEMORY STATE BEFORE EXPORT ===')
print(f'Total blocks: {len(matrix.build.blocks)}')

wire_blocks = [b for b in matrix.build.blocks if b.block_type == 'Wire']
print(f'Wire blocks: {len(wire_blocks)}')
single_conn = sum(1 for b in wire_blocks if len(b.connections) == 1)
double_conn = sum(1 for b in wire_blocks if len(b.connections) == 2)
print(f'  Wires with 1 connection: {single_conn}')
print(f'  Wires with 2 connections: {double_conn}')

print('\nFirst 5 Wires in memory:')
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Wire' and i < 5:
        print(f'  Block {i}: type={b.block_type}, connections={b.connections}')

print('\nAll Wires with 2 connections:')
count = 0
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Wire' and len(b.connections) == 2:
        print(f'  Block {i}: {b.connections}')
        count += 1
        if count >= 5:
            print('  ...')
            break

# Export to JSON
json_str = build_to_json_string(matrix.build)
with open('output/debug_display.json', 'w') as f:
    f.write(json_str)

# Reload and check
with open('output/debug_display.json', 'r') as f:
    reloaded = json.load(f)

print('\n=== AFTER JSON RELOAD ===')
reloaded_wires = [b for b in reloaded if b[0] == 'Wire']
print(f'Wire blocks: {len(reloaded_wires)}')
single = sum(1 for b in reloaded_wires if len(b[1]) == 1)
double = sum(1 for b in reloaded_wires if len(b[1]) == 2)
print(f'  Wires with 1 connection: {single}')
print(f'  Wires with 2 connections: {double}')

print('\nFirst 5 Wires in JSON:')
for i, b in enumerate(reloaded):
    if b[0] == 'Wire' and i < 5:
        print(f'  Index {i+1}: {b}')
