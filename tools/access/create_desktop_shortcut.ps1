$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pythonwPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$mainPath = Join-Path $projectRoot 'main.py'
$iconPath = Join-Path $projectRoot 'assets\logo\favicon.ico'
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'RtG Display.lnk'

if (-not (Test-Path -LiteralPath $pythonwPath)) {
    throw "Could not find the virtual environment Python launcher: $pythonwPath"
}

if (-not (Test-Path -LiteralPath $mainPath)) {
    throw "Could not find the application entry point: $mainPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = '"' + $mainPath + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = 'Launch RtG Display'
if (Test-Path -LiteralPath $iconPath) {
    $shortcut.IconLocation = $iconPath
}
$shortcut.Save()

Write-Host "Created shortcut: $shortcutPath"
