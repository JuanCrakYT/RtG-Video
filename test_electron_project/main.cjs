console.log('Testing different import paths...');

try {
    const electron = require('electron');
    console.log('require(electron):', electron);
} catch (e) {
    console.log('require(electron) error:', e.message);
}

try {
    const electronMain = require('electron/main');
    console.log('require(electron/main):', electronMain);
} catch (e) {
    console.log('require(electron/main) error:', e.message);
}

try {
    const { app } = require('electron/common');
    console.log('require(electron/common):', app);
} catch (e) {
    console.log('require(electron/common) error:', e.message);
}

try {
    const { app } = require('@electron/internal/main-process/app');
    console.log('require(@electron/internal/main-process/app):', app);
} catch (e) {
    console.log('require(@electron/internal/main-process/app) error:', e.message);
}

try {
    const { BrowserWindow } = require('@electron/internal/main-process/browser-window');
    console.log('require(@electron/internal/main-process/browser-window):', BrowserWindow);
} catch (e) {
    console.log('require(@electron/internal/main-process/browser-window) error:', e.message);
}