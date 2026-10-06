const { app, BrowserWindow } = require("electron/js2c/asar_bundle");
const path = require("node:path");

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

async function testImport() {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
            webSecurity: false,
        },
    });
    
    win.webContents.on("console-message", (event, level, message) => {
        console.log("[RENDERER CONSOLE]", level, message);
    });
    
    win.webContents.on("did-fail-load", (event, errorCode, errorDescription, validatedURL) => {
        console.log("[DID FAIL LOAD]", errorCode, errorDescription, validatedURL);
    });
    
    // Load the preview page
    await win.loadURL("http://127.0.0.1:" + PORT + "/preview.html?video=/video/" + TOKEN + "&name=test&fps=30&frame_count=100&width=16&height=16&palette=%5B%5B0%2C0%2C0%5D%2C%5B255%2C255%2C255%5D%2C%5B128%2C128%2C128%5D%5D");
    
    // Wait a bit then test the dynamic import
    setTimeout(async () => {
        const result = await win.webContents.executeJavaScript(
            "(async () => {" +
            "try {" +
            "  const m = await import('/plyr/plyr.js');" +
            "  console.log('PLYR IMPORT OK', m);" +
            "  return 'OK';" +
            "} catch (e) {" +
            "  console.error('PLYR IMPORT FAILED', e);" +
            "  return 'FAILED: ' + e.message;" +
            "}" +
            "})()"
        );
        console.log("Dynamic import test result:", result);
    }, 5000);
}

app.whenReady().then(testImport).catch(console.error);