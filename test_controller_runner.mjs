global.requestAnimationFrame = (cb) => { global.rafCallback = cb; return 9; };
global.cancelAnimationFrame = (id) => { global.rafCancelled = id; };
global.window = { Audio: class { constructor() { this.currentTime = 0; this.played = false; } play() { this.played = true; return Promise.resolve(); } } };
global.document = { createElement: function(tag) { if (tag === 'canvas') { return { width: 0, height: 0, getContext: function() { return { canvas: { width: 2, height: 2 }, drawImage: function() { }, getImageData: function() { return { width: 2, height: 2, data: new Uint8ClampedArray([0, 0, 0, 255, 255, 255, 255, 255, 128, 128, 128, 255, 0, 0, 0, 255]) } }; } }; } return {}; } };
import './tests/js/preview-controller-test.js';