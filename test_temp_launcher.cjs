const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const os = require('os');

// Create temp directory
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'rtg-preview-'));

// Write launcher script
const launcherScript = `
const { app, BrowserWindow } = require('electron');
const url = process.env.RTG_PREVIEW_URL;
console.log('URL:', url);

function createWindow() {
    const win = new BrowserWindow({
        title: 'RtG Video Preview',
        width: 560,
        height: 520,
        resizable: false,
        autoHideMenuBar: true,
        backgroundColor: '#f5f5f5',
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true,
        },
    });
    win.removeMenu();
    win.loadURL(url);
    win.on('closed', () => app.quit());
}

app.whenReady().then(createWindow).catch(err => {
    console.error(err);
    app.quit();
});
`;

const scriptPath = path.join(tmpDir, 'launcher.cjs');
fs.writeFileSync(scriptPath, launcherScript);

const electronPath = path.join(__dirname, 'node_modules', 'electron', 'dist', 'electron.exe');
const env = { ...process.env, RTG_PREVIEW_URL: 'https://example.com' };

const proc = spawn(electronPath, [scriptPath], { cwd: tmpDir, env, stdio: ['ignore', 'pipe', 'pipe'] });
proc.stdout.on('data', d => console.log('STDOUT:', d.toString()));
proc.stderr.on('data', d => console.log('STDERR:', d.toString()));
proc.on('close', c => { console.log('Exit code:', c); fs.rmSync(tmpDir, { recursive: true, force: true }); });
proc.on('error', e => console.log('Error:', e));
setTimeout(() => { console.log('Timeout'); proc.kill(); fs.rmSync(tmpDir, { recursive: true, force: true }); }, 15000);