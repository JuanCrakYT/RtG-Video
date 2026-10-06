console.log('Testing require("electron") inside Electron...');
const electron = require('electron');
console.log('electron:', electron);
console.log('typeof electron:', typeof electron);
console.log('electron keys:', electron ? Object.keys(electron) : 'null');
console.log('electron.app:', electron && electron.app);
console.log('electron.BrowserWindow:', electron && electron.BrowserWindow);

if (electron && electron.app) {
    console.log('SUCCESS: electron.app is available');
    electron.app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
    console.log('commandLine switch added');
    electron.app.whenReady().then(() => {
        console.log('app ready');
        const { BrowserWindow } = require('electron');
        const win = new BrowserWindow({ width: 400, height: 300, show: false });
        console.log('window created');
        win.loadURL('https://example.com');
        win.on('closed', () => electron.app.quit());
    }).catch(err => {
        console.error('Error:', err);
        electron.app.quit();
    });
} else {
    console.log('FAILURE: electron.app is not available');
    process.exit(1);
}