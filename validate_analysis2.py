import json

with open('output/analysis_test/analysis.json') as f:
    data = json.load(f)

print('JSON is valid')
print('Keys:', list(data.keys()))

# Validate structure
for pixel in data['pixels']:
    for color_usage in pixel['colors']:
        assert color_usage['frame_count'] == len(color_usage['frames']), 'frame_count mismatch'
        assert color_usage['gate_or_needed'] == max(color_usage['frame_count'] - 1, 0), 'gate_or_needed mismatch'
    assert pixel['total_gate_ors'] == sum(c['gate_or_needed'] for c in pixel['colors']), 'pixel total_gate_ors mismatch'

assert data['total_gate_ors_needed'] == sum(p['total_gate_ors'] for p in data['pixels']), 'total_gate_ors mismatch'
assert data['max_gate_ors_per_pixel'] == max(p['total_gate_ors'] for p in data['pixels']), 'max_gate_ors mismatch'

# color_totals validation
for color_str, total in data['color_totals'].items():
    computed = sum(c['frame_count'] for p in data['pixels'] for c in p['colors'] if str(tuple(c['color'])) == color_str)
    assert computed == total, f'color_totals mismatch for {color_str}: computed={computed}, stored={total}'

print('All validations PASSED')
print(f'  total_gate_ors_needed: {data["total_gate_ors_needed"]}')
print(f'  max_gate_ors_per_pixel: {data["max_gate_ors_per_pixel"]}')
print(f'  pixels: {len(data["pixels"])}')
print(f'  unique_colors: {len(data["unique_colors"])}')