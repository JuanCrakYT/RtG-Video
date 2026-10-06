// Check what's available in process.electronBinding and other internals
console.log("process.electronBinding:", process.electronBinding);
console.log("process.atomBinding:", process.atomBinding);

// Try to find the app module
try {
    const binding = process.electronBinding;
    if (binding) {
        console.log("binding keys:", Object.keys(binding));
        for (const key of Object.keys(binding)) {
            try {
                console.log(`binding.${key}:`, typeof binding[key]);
            } catch (e) {
                console.log(`binding.${key}: ERROR -`, e.message);
            }
        }
    }
} catch (e) {
    console.log("electronBinding error:", e.message);
}

// Check Module._cache for electron-related modules
const Module = require('module');
for (const [key, value] of Object.entries(Module._cache || {})) {
    if (key.includes('electron') || key.includes('app') || key.includes('browser')) {
        console.log("Cached:", key, value ? Object.keys(value.exports || {}) : 'null');
    }
}

// Try require('electron') to see what the original returns
try {
    const orig = require('electron');
    console.log("Original require('electron'):", typeof orig, orig);
} catch (e) {
    console.log("Original require error:", e.message);
}