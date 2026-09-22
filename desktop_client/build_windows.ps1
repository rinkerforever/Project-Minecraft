param(
    [string]$PythonCommand = "py"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildRoot = Join-Path $projectRoot "build"
$distRoot = Join-Path $projectRoot "dist"
$clientDist = Join-Path $distRoot "MinecraftControlPlane"
$iconPath = Join-Path $PSScriptRoot "aimnet-minecraft.ico"

& (Join-Path $PSScriptRoot "create_windows_icon.ps1") -OutputIcon $iconPath

& $PythonCommand -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

& $PythonCommand -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --icon $iconPath `
    --name "MinecraftControlPlane" `
    --distpath $distRoot `
    --workpath $buildRoot `
    --specpath $buildRoot `
    (Join-Path $PSScriptRoot "client.py")

if (-not (Test-Path (Join-Path $clientDist "MinecraftControlPlane.exe"))) {
    throw "PyInstaller did not produce the desktop executable."
}

Write-Host "Desktop app built at: $clientDist"
Write-Host "Compile installer.iss with Inno Setup to create the installer."
