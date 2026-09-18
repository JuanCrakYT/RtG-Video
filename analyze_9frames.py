import json
from collections import defaultdict

with open('output/test_9frames_display.json', 'r', encoding='utf-8') as f:
    blocks = json.load(f)

print(f'Total blocks: {len(blocks)}')

# Count block types
from collections import Counter
counts = Counter(b[0] for b in blocks)
print('Block types:', dict(counts))

# Find all block indexes by type
gate_ors = [i+1 for i, b in enumerate(blocks) if b[0] == 'Gate-OR']
wires = [i+1 for i, b in enumerate(blocks) if b[0] == 'Wire']
delayers = [i+1 for i, b in enumerate(blocks) if b[0] == 'Delayer']
splitters = [i+1 for i, b in enumerate(blocks) if b[0] == 'Splitter_3']
buttons = [i+1 for i, b in enumerate(blocks) if b[0] == 'Button']

print(f'\nDelayers: {len(delayers)} (indexes: {delayers[:5]}...)')
print(f'Gate-ORs: {len(gate_ors)} (indexes: {gate_ors[:5]}...)')
print(f'Wires: {len(wires)}')
print(f'Splitters: {len(splitters)}')
print(f'Buttons: {len(buttons)}')

# Build connection map
feeds = defaultdict(list)  # target -> list of (wire_idx, src_idx, src_point, tgt_point)
for i, b in enumerate(blocks):
    if b[0] == 'Wire':
        conns = b[1]
        if len(conns) >= 2:
            src = conns[0][2]
            tgt = conns[1][2]
            src_point = conns[0][1]
            tgt_point = conns[1][1]
            feeds[tgt].append((i+1, src, src_point, tgt_point))

# Analyze Delayer connections
print('\n=== Delayer Analysis ===')
for d in delayers:
    incoming = feeds.get(d, [])
    print(f'Delayer {d}: {len(incoming)} incoming wire(s)')
    for w in incoming:
        src_type = blocks[w[1]-1][0]
        print(f'  <- Wire {w[0]}: {src_type} {w[1]} point {w[2]} -> point {w[3]}')

# Analyze Gate-OR connections
print('\n=== Gate-OR Analysis ===')
or_signal_inputs = 0
or_physical_mounts = 0
for g in gate_ors:
    b = blocks[g-1]
    physical_conns = [c for c in b[1] if c[0] == '4']
    signal_incoming = feeds.get(g, [])
    
    if physical_conns:
        or_physical_mounts += 1
        print(f'Gate-OR {g}: {len(physical_conns)} physical mount(s)')
        for c in physical_conns:
            print(f'  mount ["4"] -> {c[2]} point {c[1]}')
    
    if signal_incoming:
        or_signal_inputs += 1
        print(f'Gate-OR {g}: {len(signal_incoming)} signal wire(s)')
        for w in signal_incoming:
            src_type = blocks[w[1]-1][0]
            print(f'  <- Wire {w[0]}: {src_type} {w[1]} point {w[2]} -> point {w[3]}')
    
    if not physical_conns and not signal_incoming:
        print(f'Gate-OR {g}: ORPHAN (no connections)')

print(f'\nGate-ORs with physical mounts: {or_physical_mounts}')
print(f'Gate-ORs with signal inputs: {or_signal_inputs}')

# Analyze Splitter_3 (Pixel) inputs
print('\n=== Pixel (Splitter_3) Analysis ===')
pixel_signal_inputs = 0
for s in splitters:
    incoming = feeds.get(s, [])
    if incoming:
        pixel_signal_inputs += 1
        print(f'Splitter_3 {s}: {len(incoming)} signal wire(s)')
        for w in incoming:
            src_type = blocks[w[1]-1][0]
            print(f'  <- Wire {w[0]}: {src_type} {w[1]} point {w[2]} -> point {w[3]}')
    else:
        print(f'Splitter_3 {s}: NO signal inputs')

print(f'\nSplitters with signal inputs: {pixel_signal_inputs}/{len(splitters)}')

# Check Wire connection types
print('\n=== Wire Types ===')
timeline_wires = 0
signal_wires = 0
for w_idx in wires:
    w = blocks[w_idx-1]
    conns = w[1]
    if len(conns) == 1:
        timeline_wires += 1
    elif len(conns) >= 2:
        signal_wires += 1
        # Check if source is Delayer
        src = conns[0][2]
        src_type = blocks[src-1][0]
        tgt = conns[1][2]
        tgt_type = blocks[tgt-1][0]
        if src_type == 'Delayer' and tgt_type == 'Gate-OR':
            pass  # Delayer -> Gate-OR
        elif src_type == 'Gate-OR' and tgt_type == 'Gate-OR':
            pass  # Gate-OR -> Gate-OR
        elif src_type == 'Gate-OR' and tgt_type == 'Splitter_3':
            pass  # Gate-OR -> Pixel
        elif src_type == 'Delayer' and tgt_type == 'Splitter_3':
            pass  # Delayer -> Pixel (direct, for single source)
        else:
            print(f'  Wire {w_idx}: {src_type} -> {tgt_type}')

print(f'Timeline wires (1 conn): {timeline_wires}')
print(f'Signal wires (2+ conn): {signal_wires}')

# Trace one pixel's signal path
print('\n=== Sample Pixel Signal Path (Splitter_3 10) ===')
def trace(target, depth=0):
    prefix = '  ' * depth
    incoming = feeds.get(target, [])
    for w in incoming:
        src = w[1]
        src_type = blocks[src-1][0]
        print(f'{prefix}<- Wire {w[0]}: {src_type} {src} point {w[2]} -> point {w[3]}')
        if src_type in ['Gate-OR', 'Delayer']:
            trace(src, depth+1)

trace(10)