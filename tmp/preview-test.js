import assert from "node:assert/strict";
import {
    clampDimension,
    normalizePalette,
    quantizeImageData,
    quantizeImageDataFlat,
    resizeImageDataArea,
} from "./preview.js";

assert.equal(clampDimension(2), 2);
assert.equal(clampDimension(999), 128);
assert.equal(clampDimension(3.9), 3);
assert.throws(() => clampDimension("invalid"), /numeric/);

const palette = normalizePalette([
    [0, 0, 0],
    [255, 0, 0],
    [255, 0, 0],
    [0, 255, 0],
]);
assert.deepEqual(palette, [[0, 0, 0], [255, 0, 0], [0, 255, 0]]);

const imageData = {
    width: 2,
    height: 1,
    data: new Uint8ClampedArray([
        255, 0, 0, 255,
        0, 255, 0, 255,
    ]),
};
assert.deepEqual(
    quantizeImageData(imageData, 2, 1, palette),
    [[[255, 0, 0], [0, 255, 0]]],
);
assert.deepEqual(
    [...quantizeImageDataFlat(imageData, 2, 1, palette)],
    [255, 0, 0, 255, 0, 255, 0, 255],
);

const averaged = resizeImageDataArea({
    width: 2,
    height: 1,
    data: new Uint8ClampedArray([
        255, 0, 0, 255,
        0, 255, 0, 255,
    ]),
}, 1, 1);
assert.deepEqual([...averaged.data], [128, 128, 0, 255]);

const sourceWidth = 640;
const sourceHeight = 360;
const source = {
    width: sourceWidth,
    height: sourceHeight,
    data: new Uint8ClampedArray(sourceWidth * sourceHeight * 4),
};
for (let y = 0; y < sourceHeight; y += 1) {
    for (let x = 0; x < sourceWidth; x += 1) {
        const offset = (y * sourceWidth + x) * 4;
        source.data[offset] = (x * 3 + y * 5) % 256;
        source.data[offset + 1] = (x * 7 + y * 11) % 256;
        source.data[offset + 2] = (x * 13 + y * 17) % 256;
        source.data[offset + 3] = 255;
    }
}

const expectedChecksums = new Map([
    [16, 98304],
    [32, 393216],
    [64, 1568994],
    [96, 3530736],
    [128, 6278430],
]);
const benchmarkPalette = [[0, 0, 0], [255, 255, 255], [128, 128, 128]];
for (const dimension of expectedChecksums.keys()) {
    const quantized = quantizeImageDataFlat(source, dimension, dimension, benchmarkPalette);
    let checksum = 0;
    for (let index = 0; index < quantized.length; index += 4) {
        checksum += quantized[index] + quantized[index + 1] + quantized[index + 2];
    }
    assert.equal(checksum, expectedChecksums.get(dimension));
}

console.log("experimental JavaScript preview checks passed");
