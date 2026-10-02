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
    validate_signal_connections,
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

errors = validate_signal_connections(matrix.build)
if errors:
    print('Validation: FAILED')
    for e in errors:
        print(f'  {e}')
else:
    print('Validation: PASSED')

print('\n=== SUMMARY ===')
from collections import Counter
types = Counter(b.block_type for b in matrix.build.blocks)
for t, c in sorted(types.items()):
    print(f'  {t}: {c}')
print(f'  Total: {len(matrix.build.blocks)}')

print('\n=== DELAYERS ===')
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Delayer':
        frame = b.properties.get('Frame', '?')
        for conn in b.connections:
            parent_idx = conn[2]
            parent_block = matrix.build.blocks[parent_idx - 1] if 1 <= parent_idx <= len(matrix.build.blocks) else None
            parent_type = parent_block.block_type if parent_block else '?'
            print(f'  Delayer[{i}] Frame={frame}: TipoLocal={conn[0]}, point={conn[1]}, parent={parent_type}[{parent_idx}]')

print('\n=== WIRE-TIMELINE (Delayer to Delayer) ===')
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Wire' and len(b.connections) == 2:
        # Check if it connects two Delayers (timeline wire)
        src = b.connections[0][2]
        tgt = b.connections[1][2]
        src_block = matrix.build.blocks[src - 1]
        tgt_block = matrix.build.blocks[tgt - 1]
        if src_block.block_type == 'Delayer' and tgt_block.block_type == 'Delayer':
            print(f'  Wire[{i}]: input=["{b.connections[0][0]}",{b.connections[0][1]},{src}] -> output=["{b.connections[1][0]}",{b.connections[1][1]},{tgt}]')

print('\n=== WIRE-SIGNAL (Delayer/Gate-OR to Gate-OR/Splitter) ===')
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Wire' and len(b.connections) == 2:
        src = b.connections[0][2]
        tgt = b.connections[1][2]
        src_block = matrix.build.blocks[src - 1]
        tgt_block = matrix.build.blocks[tgt - 1]
        if src_block.block_type == 'Delayer' or src_block.block_type == 'Gate-OR':
            src_type = src_block.block_type
            tgt_type = tgt_block.block_type
            print(f'  Wire[{i}]: ["3",{b.connections[0][1]},{src}] -> ["1",{b.connections[1][1]},{tgt}]  ({src_type} -> {tgt_type})')

print('\n=== GATE-OR (signal connections only) ===')
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Gate-OR':
        for conn in b.connections:
            parent_idx = conn[2]
            parent_block = matrix.build.blocks[parent_idx - 1] if 1 <= parent_idx <= len(matrix.build.blocks) else None
            parent_type = parent_block.block_type if parent_block else '?'
            if parent_type == 'Wire':
                print(f'  Gate-OR[{i}]: TipoLocal={conn[0]}, point={conn[1]}, parent=Wire[{parent_idx-1}]')

print('\n=== SPLITTER_3 (pixel endpoint) ===')
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Splitter_3':
        print(f'  Splitter_3[{i}]: connections={b.connections}')