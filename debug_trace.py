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
    _allocate_pixel_or_tree,
    _get_internal_nodes_level_order,
    _connect_pixel_sources,
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

print("=== BASE BUILD ===")
print(f"Base index: {matrix.base_index}")
print(f"Initial blocks: {len(matrix.build.blocks)}")
for i, b in enumerate(matrix.build.blocks):
    print(f"  [{i}] {b.block_type}: conn={b.connections}")

start_button_index = add_start_button(matrix.build, matrix.base_index)
print(f"\n=== AFTER START BUTTON ===")
print(f"Button index: {start_button_index}")
print(f"Blocks: {len(matrix.build.blocks)}")

colors = [WHITE, BLACK, GRAY, WHITE, BLACK, GRAY, WHITE, BLACK]
gate_or_count = max(len(list(matrix.iter_pixels())), len(colors) - 1)
print(f"\nGate-OR count needed: {gate_or_count}")

gate_or_indexes = add_physical_gate_or_table(matrix.build, matrix.base_index, gate_or_count)
print(f"Gate-OR indexes (0-based): {gate_or_indexes}")
print(f"Blocks after Gate-ORs: {len(matrix.build.blocks)}")

builder = SequenceBuilder()
for i, color in enumerate(colors):
    frame = FrameBuilder(duration=0.1).set_frame_number(len(builder.frames))
    frame.set_pixel_color(list(matrix.pixels.values())[0].uuid, color)
    builder.add_frame(frame.build())
sequence = builder.build()

print(f"\n=== TIMELINE ===")
timeline_delayer_indexes = build_animation_timeline(
    matrix.build,
    [frame.duration for frame in sequence.frames],
    start_source_index=start_button_index,
)
print(f"Timeline delayer indexes (0-based): {timeline_delayer_indexes}")
print(f"Blocks after timeline: {len(matrix.build.blocks)}")

for i in timeline_delayer_indexes:
    b = matrix.build.blocks[i]
    print(f"  Delayer[{i}] Frame={b.properties.get('Frame')}: conn={b.connections}")

print("\nTimeline wires:")
for i, b in enumerate(matrix.build.blocks):
    if b.block_type == 'Wire':
        print(f"  Wire[{i}]: conn={b.connections}")

pixel_inputs = resolve_pixel_inputs(matrix.pixels.values())
print(f"\n=== PIXEL INPUTS ===")
for uuid, ep in pixel_inputs.items():
    print(f"  {uuid}: block_index={ep.block_index}, point_id={ep.point_id}")

frame_active_pixels = {
    index: [list(matrix.pixels.values())[0].uuid] for index in range(len(sequence.frames))
}
print(f"\n=== FRAME ACTIVE PIXELS ===")
for fi, pixes in frame_active_pixels.items():
    print(f"  Frame {fi}: {pixes}")

print("\n=== INSTRUMENTING SIGNAL NETWORK ===")

delayer_indexes = list(timeline_delayer_indexes)
active_frame_indexes = {}
for frame_index in range(len(sequence.frames)):
    for pixel_uuid in frame_active_pixels.get(frame_index, ()):
        active_frame_indexes.setdefault(pixel_uuid, []).append(delayer_indexes[frame_index])

print(f"\nActive frame indexes per pixel:")
for uuid, indexes in active_frame_indexes.items():
    print(f"  {uuid}: {indexes}")

for pixel_uuid, source_indexes in active_frame_indexes.items():
    print(f"\n--- Pixel {pixel_uuid} ---")
    print(f"Source indexes (0-based): {source_indexes}")
    
    or_tree = _allocate_pixel_or_tree(source_indexes)
    print(f"OR Tree nodes ({len(or_tree)}):")
    for i, node in enumerate(or_tree):
        if node.is_leaf:
            print(f"  [{i}] LEAF source_frame={node.source_frame}")
        else:
            print(f"  [{i}] INTERNAL child_a={node.child_a} child_b={node.child_b}")
    
    internal_nodes = _get_internal_nodes_level_order(or_tree)
    print(f"Internal nodes (level-order): {internal_nodes}")
    
    pool = list(gate_or_indexes)
    physical_map = {node_index: pool.pop(0) for node_index in internal_nodes}
    print(f"Physical map (tree_node -> physical_gate_index):")
    for k, v in sorted(physical_map.items()):
        print(f"  tree[{k}] -> gate[{v}] (0-based)")
    
    print(f"\nTracing connections:")
    
    def resolve(node: int, depth=0) -> int:
        indent = "  " * depth
        info = or_tree[node]
        if info.is_leaf:
            src = source_indexes[info.source_frame]
            print(f"{indent}resolve({node}) -> leaf -> source_index={src} (delayer)")
            return src
        gate_index = physical_map[node]
        left_index = resolve(info.child_a, depth+1)
        right_index = resolve(info.child_b, depth+1)
        print(f"{indent}resolve({node}) -> gate_index={gate_index}")
        print(f"{indent}  LEFT: source={left_index} -> gate={gate_index} (InputA)")
        print(f"{indent}  RIGHT: source={right_index} -> gate={gate_index} (InputB)")
        return gate_index
    
    root_index = resolve(len(or_tree) - 1)
    ep = pixel_inputs[pixel_uuid]
    print(f"ROOT: gate_index={root_index} -> Splitter ({ep.block_index}, point={ep.point_id})")