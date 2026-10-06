const { app, BrowserWindow } = require('electron');
console.log('app:', typeof app);
console.log('BrowserWindow:', typeof BrowserWindow);
if (app) {
    console.log('app.commandLine:', typeof app.commandLine);
    app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
    console.log('commandLine switch added');
}
app.whenReady().then(() => {
    console.log('app ready');
    const win = new BrowserWindow({ width: 400, height: 300, show: false });
    console.log('window created');
    win.loadURL('https://example.com');
    win.on('closed', () => app.quit());
}).catch(err => {
    console.error('Error:', err);
    app.quit();
});