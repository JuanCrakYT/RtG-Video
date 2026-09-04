const { app, BrowserWindow } = require("electron");
const path = require("node:path");

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

function previewUrl() {
    if (process.env.RTG_PREVIEW_URL) return process.env.RTG_PREVIEW_URL;
    const argument = process.argv.find((value) => value.startsWith("--preview-url="));
    if (!argument) throw new Error("No Preview URL was supplied");
    return argument.slice("--preview-url=".length);
}

function createPreviewWindow() {
    const icon = path.join(__dirname, "../../../assets/logo/favicon.ico");
    const window = new BrowserWindow({
        title: "RtG Video Preview",
        width: 560,
        height: 520,
        resizable: false,
        autoHideMenuBar: true,
        backgroundColor: "#f5f5f5",
        icon,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true,
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
