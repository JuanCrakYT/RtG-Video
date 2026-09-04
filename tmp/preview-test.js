import assert from "node:assert/strict";
import {
    clampDimension,
    normalizePalette,
    quantizeImageData,
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

const averaged = resizeImageDataArea({
    width: 2,
    height: 1,
    data: new Uint8ClampedArray([
        255, 0, 0, 255,
        0, 255, 0, 255,
    ]),
}, 1, 1);
assert.deepEqual([...averaged.data], [128, 128, 0, 255]);

console.log("experimental JavaScript preview checks passed");
