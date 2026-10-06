// electron_patch.cjs - Explore Electron internals
console.log('[PATCH] Electron patch loaded in:', process.type);
console.log('[PATCH] process.versions:', process.versions);
console.log('[PATCH] process.type:', process.type);
console.log('[PATCH] process.electronBinding:', typeof process.electronBinding);
console.log('[PATCH] process.atomBinding:', typeof process.atomBinding);
console.log('[PATCH] global.app:', typeof global.app);
console.log('[PATCH] global.BrowserWindow:', typeof global.BrowserWindow);
console.log('[PATCH] global.require:', typeof global.require);

// Try to access internal modules
try {
    const binding = process.electronBinding;
    if (binding) {
        console.log('[PATCH] electronBinding keys:', Object.keys(binding));
        // Try to get app module
        if (binding.app) {
            console.log('[PATCH] binding.app:', typeof binding.app);
        }
        if (binding['atom_browser_app']) {
            console.log('[PATCH] binding.atom_browser_app:', typeof binding['atom_browser_app']);
        }
    }
} catch (e) {
    console.log('[PATCH] electronBinding error:', e.message);
}

try {
    const atomBinding = process.atomBinding;
    if (atomBinding) {
        console.log('[PATCH] atomBinding keys:', Object.keys(atomBinding));
    }
} catch (e) {
    console.log('[PATCH] atomBinding error:', e.message);
}

// Try require('electron') normally to see what happens
try {
    const electron = require('electron');
    console.log('[PATCH] Normal require(electron):', electron);
} catch (e) {
    console.log('[PATCH] Normal require error:', e.message);
}