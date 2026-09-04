import assert from "node:assert/strict";
import { normalizePalette, quantizeImageData } from "./preview.js";

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

console.log("experimental JavaScript preview checks passed");
