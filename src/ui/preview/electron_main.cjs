// Electron entry point for the RtG Video preview.
// In Electron's main process, the public "electron" module exposes app and BrowserWindow.
const electron = require("electron");
const { app, BrowserWindow } = electron;
const path = require("node:path");

if (!app || !BrowserWindow) {
    console.error("Electron main-process API unavailable.", {
        processType: process.type,
        electronVersion: process.versions.electron,
        electronExportType: typeof electron,
        appType: typeof app,
        browserWindowType: typeof BrowserWindow,
        argv: process.argv,
    });
    process.exitCode = 1;
    throw new Error("Electron was not launched as an application main process.");
}

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
            sandbox: true,
            webSecurity: true,
        },
    });

    window.removeMenu();
    window.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
        console.error(
            "Preview failed to load (" + errorCode + "): " + errorDescription + "; URL: " + validatedURL
        );
    });
    window.loadURL(previewUrl()).catch((error) => {
        console.error("Could not load the RtG Video preview URL:", error);
        app.quit();
    });
    window.on("closed", () => app.quit());
}

app.whenReady()
    .then(createPreviewWindow)
    .catch((error) => {
        console.error("Electron preview startup failed:", error);
        app.quit();
    });
