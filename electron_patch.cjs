// electron_patch.cjs - Patch require('electron') to return built-in modules
// This runs via --require flag before the main script

console.log('[electron_patch] Patch loaded');

const Module = require('module');
const originalRequire = Module.prototype.require;

// Pre-load the built-in modules using internal mechanisms
let builtinModules = null;

function loadBuiltinModules() {
    if (builtinModules) return builtinModules;
    
    console.log('[electron_patch] Attempting to load builtin modules...');
    
    // Try multiple methods to get the built-in electron module
    
    // Method 1: Try Module._load with the internal electron module
    try {
        const builtin = Module._load('electron', null, true);
        if (builtin && builtin.app) {
            console.log('[electron_patch] Got builtin via Module._load(electron, null, true)');
            builtinModules = builtin;
            return builtinModules;
        }
    } catch (e) {
        console.log('[electron_patch] Module._load(electron) failed:', e.message);
    }
    
    // Method 2: Try to load the internal electron bundle
    try {
        const builtin = Module._load('electron/js2c/browser_init', null, true);
        if (builtin && builtin.app) {
            console.log('[electron_patch] Got builtin via browser_init');
            builtinModules = builtin;
            return builtinModules;
        }
    } catch (e) {
        console.log('[electron_patch] browser_init failed:', e.message);
    }
    
    // Method 3: Try to access through internal binding
    try {
        if (process.electronBinding) {
            const app = process.electronBinding('app');
            const BrowserWindow = process.electronBinding('browser-window');
            if (app && BrowserWindow) {
                console.log('[electron_patch] Got builtin via electronBinding');
                builtinModules = { app, BrowserWindow };
                return builtinModules;
            }
        }
    } catch (e) {
        console.log('[electron_patch] electronBinding failed:', e.message);
    }
    
    // Method 4: Try atomBinding
    try {
        if (process.atomBinding) {
            const app = process.atomBinding('app');
            const BrowserWindow = process.atomBinding('browser-window');
            if (app && BrowserWindow) {
                console.log('[electron_patch] Got builtin via atomBinding');
                builtinModules = { app, BrowserWindow };
                return builtinModules;
            }
        }
    } catch (e) {
        console.log('[electron_patch] atomBinding failed:', e.message);
    }
    
    // Method 5: Try to get from global (set by Electron after app ready)
    try {
        if (global.__electron_app && global.__electron_BrowserWindow) {
            console.log('[electron_patch] Got builtin from global');
            builtinModules = { app: global.__electron_app, BrowserWindow: global.__electron_BrowserWindow };
            return builtinModules;
        }
    } catch (e) {
        console.log('[electron_patch] global access failed:', e.message);
    }
    
    // Method 6: Try to require the internal asar_bundle
    try {
        const builtin = require('electron/js2c/asar_bundle');
        if (builtin && builtin.app) {
            console.log('[electron_patch] Got builtin via asar_bundle require');
            builtinModules = builtin;
            return builtinModules;
        }
    } catch (e) {
        console.log('[electron_patch] asar_bundle require failed:', e.message);
    }
    
    console.log('[electron_patch] All methods failed to load builtin modules');
    return null;
}

Module.prototype.require = function(id) {
    if (id === 'electron') {
        console.log('[electron_patch] Intercepted require(electron)');
        const builtin = loadBuiltinModules();
        if (builtin) {
            console.log('[electron_patch] Returning builtin modules');
            return builtin;
        }
        console.log('[electron_patch] No builtin modules available, returning fallback');
        // Return a minimal fallback
        return {
            app: { whenReady: () => Promise.resolve() },
            BrowserWindow: function() { console.log('[electron_patch] Fallback BrowserWindow'); },
        };
    }
    return originalRequire.apply(this, arguments);
};

console.log('[electron_patch] Patch installed');