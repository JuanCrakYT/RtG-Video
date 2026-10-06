console.log("Testing different require paths:");

// Try various internal module paths
const paths = [
    "@electron/internal/main-process/app",
    "@electron/internal/main-process/browser-window",
    "electron",
    "electron/main",
    "electron/common",
    "electron/renderer",
    "@electron/internal",
];

for (const p of paths) {
    try {
        const m = require(p);
        console.log(`require("${p}"):`, typeof m, m ? Object.keys(m).slice(0, 10) : m);
    } catch (e) {
        console.log(`require("${p}") ERROR:`, e.message);
    }
}

// Check global
console.log("global.app:", typeof global.app);
console.log("global.BrowserWindow:", typeof global.BrowserWindow);
console.log("process.type:", process.type);