import json
with open('output/display.json', 'r', encoding='utf-8') as f:
    blocks = json.load(f)

gate_ors = [(i+1, b) for i, b in enumerate(blocks) if b[0] == 'Gate-OR']
wires = [(i+1, b) for i, b in enumerate(blocks) if b[0] == 'Wire']
delayers = [(i+1, b) for i, b in enumerate(blocks) if b[0] == 'Delayer']

print('=== Representative Gate-OR blocks ===')
for idx, b in gate_ors[:3]:
    print(f'Index {idx}: {b}')
print('...')
for idx, b in gate_ors[-2:]:
    print(f'Index {idx}: {b}')

print('\n=== Representative Wire blocks ===')
for idx, b in wires[:3]:
    print(f'Index {idx}: {b}')
print('...')
for idx, b in wires[-2:]:
    print(f'Index {idx}: {b}')

print(f'\nDelayer count: {len(delayers)}')
print(f'Wire count: {len(wires)}')

single = sum(1 for _, b in wires if len(b[1]) == 1)
double = sum(1 for _, b in wires if len(b[1]) == 2)
print(f'Wires with 1 connection: {single}')
print(f'Wires with 2 connections: {double}')

# Show which blocks Gate-ORs are connected to physically
print('\n=== Gate-OR physical chain ===')
for idx, b in gate_ors:
    print(f'Gate-OR {idx}: {b[1]}')
