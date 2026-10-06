// electron_main.cjs - Electron entry point for RtG Video Preview
// Uses internal Electron modules directly instead of require("electron")

const electron = require("electron/js2c/asar_bundle");
const { app, BrowserWindow } = electron;
const path = require("node:path");

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

function previewUrl() {
    if (process.env.RTG_PREVIEW_URL) return process.env.RTG_PREVIEW_URL;
    const argument = process.argv.find((value) => value.startsWith("--preview-url="));
    if (!argument) throw new Error("No Preview URL was supplied");
    return argument.slice("--preview-url=".length);
}

function createPreviewWindow() {
    const iconPath = process.env.RTG_PREVIEW_ICON 
        ? path.resolve(process.env.RTG_PREVIEW_ICON)
        : path.join(__dirname, "../../../assets/logo/favicon-preview.ico");
    const window = new BrowserWindow({
        title: "RtG Video Preview",
        width: 560,
        height: 520,
        minWidth: 400,
        minHeight: 400,
        resizable: true,
        autoHideMenuBar: true,
        backgroundColor: "#f5f5f5",
        icon: iconPath,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
            webSecurity: false,
        },
    });
    window.removeMenu();
    window.loadURL(previewUrl());
    window.on("closed", () => app.quit());
}

app.whenReady().then(createPreviewWindow).catch((error) => {
    console.error(error);
    app.quit();
});