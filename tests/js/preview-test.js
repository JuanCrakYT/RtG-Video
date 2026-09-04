import assert from "node:assert/strict";
import { clampDimension, normalizePalette, quantizeImageData, quantizeImageDataFlat, resizeImageDataArea } from "../../src/ui/preview/preview.js";

assert.equal(clampDimension(2), 2);
assert.equal(clampDimension(999), 128);
assert.equal(clampDimension(3.9), 3);
assert.throws(() => clampDimension("invalid"), /numeric/);

const palette = normalizePalette([[0, 0, 0], [255, 0, 0], [255, 0, 0], [0, 255, 0]]);
assert.deepEqual(palette, [[0, 0, 0], [255, 0, 0], [0, 255, 0]]);

const imageData = {
    width: 2,
    height: 1,
    data: new Uint8ClampedArray([255, 0, 0, 255, 0, 255, 0, 255]),
};
assert.deepEqual(quantizeImageData(imageData, 2, 1, palette), [[[255, 0, 0], [0, 255, 0]]]);
assert.deepEqual([...quantizeImageDataFlat(imageData, 2, 1, palette)], [255, 0, 0, 255, 0, 255, 0, 255]);
assert.deepEqual([...resizeImageDataArea(imageData, 1, 1).data], [128, 128, 0, 255]);

const source = { width: 640, height: 360, data: new Uint8ClampedArray(640 * 360 * 4) };
for (let y = 0; y < source.height; y += 1) {
    for (let x = 0; x < source.width; x += 1) {
        const offset = (y * source.width + x) * 4;
        source.data[offset] = (x * 3 + y * 5) % 256;
        source.data[offset + 1] = (x * 7 + y * 11) % 256;
        source.data[offset + 2] = (x * 13 + y * 17) % 256;
        source.data[offset + 3] = 255;
    }
}
const expected = new Map([[16, 98304], [32, 393216], [64, 1568994], [96, 3530736], [128, 6278430]]);
for (const dimension of expected.keys()) {
    const result = quantizeImageDataFlat(source, dimension, dimension, [[0, 0, 0], [255, 255, 255], [128, 128, 128]]);
    let checksum = 0;
    for (let index = 0; index < result.length; index += 4) checksum += result[index] + result[index + 1] + result[index + 2];
    assert.equal(checksum, expected.get(dimension));
}

console.log("production JavaScript preview checks passed");
