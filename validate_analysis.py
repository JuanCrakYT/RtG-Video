import json

with open('output/analysis_test/analysis.json') as f:
    data = json.load(f)

print('=== VALIDATION ===')

# Check 1: frame_count == len(frames)
print('\n1. frame_count == len(frames):')
all_ok = True
for pixel in data['pixels']:
    for color_usage in pixel['colors']:
        fc = color_usage['frame_count']
        fl = len(color_usage['frames'])
        if fc != fl:
            print(f'  FAIL: pos={pixel["position"]} color={color_usage["color"]} frame_count={fc} len(frames)={fl}')
            all_ok = False
if all_ok:
    print('  OK')

# Check 2: gate_or_needed == max(frame_count - 1, 0)
print('\n2. gate_or_needed == max(frame_count - 1, 0):')
all_ok = True
for pixel in data['pixels']:
    for color_usage in pixel['colors']:
        expected = max(color_usage['frame_count'] - 1, 0)
        actual = color_usage['gate_or_needed']
        if expected != actual:
            print(f'  FAIL: pos={pixel["position"]} color={color_usage["color"]} expected={expected} actual={actual}')
            all_ok = False
if all_ok:
    print('  OK')

# Check 3: pixel.total_gate_ors == sum(gate_or_needed)
print('\n3. pixel.total_gate_ors == sum(gate_or_needed):')
all_ok = True
for pixel in data['pixels']:
    expected = sum(c['gate_or_needed'] for c in pixel['colors'])
    actual = pixel['total_gate_ors']
    if expected != actual:
        print(f'  FAIL: pos={pixel["position"]} expected={expected} actual={actual}')
        all_ok = False
if all_ok:
    print('  OK')

# Check 4: total_gate_ors_needed == sum(pixel.total_gate_ors)
print('\n4. total_gate_ors_needed == sum(pixel.total_gate_ors):')
expected = sum(p['total_gate_ors'] for p in data['pixels'])
actual = data['total_gate_ors_needed']
if expected != actual:
    print(f'  FAIL: expected={expected} actual={actual}')
else:
    print(f'  OK: {actual}')

# Check 5: max_gate_ors_per_pixel == max(pixel.total_gate_ors)
print('\n5. max_gate_ors_per_pixel == max(pixel.total_gate_ors):')
expected = max((p['total_gate_ors'] for p in data['pixels']), default=0)
actual = data['max_gate_ors_per_pixel']
if expected != actual:
    print(f'  FAIL: expected={expected} actual={actual}')
else:
    print(f'  OK: {actual}')

# Check 6: color_totals validation
print('\n6. color_totals validation:')
all_ok = True
for color_str, total in data['color_totals'].items():
    computed = 0
    for pixel in data['pixels']:
        for color_usage in pixel['colors']:
            # Keys are stored as tuple string repr like "(128, 128, 128)"
            key = str(tuple(color_usage['color']))
            if key == color_str:
                computed += color_usage['frame_count']
    if computed != total:
        print(f'  FAIL: color={color_str} computed={computed} stored={total}')
        all_ok = False
if all_ok:
    print('  OK')

# Check 7: edge cases
print('\n7. Edge cases:')
single_use = [(p['position'], c) for p in data['pixels'] for c in p['colors'] if c['frame_count'] == 1]
multi_use = [(p['position'], c) for p in data['pixels'] for c in p['colors'] if c['frame_count'] > 1]
print(f'  Single-use colors: {len(single_use)}')
print(f'  Multi-use colors: {len(multi_use)}')
if single_use:
    pos, c = single_use[0]
    print(f'  Example single: pos={pos} frames={c["frames"]} gate_or_needed={c["gate_or_needed"]}')
if multi_use:
    pos, c = multi_use[0]
    print(f'  Example multi: pos={pos} frame_count={c["frame_count"]} gate_or_needed={c["gate_or_needed"]}')

print('\n=== ALL VALIDATIONS COMPLETE ===')