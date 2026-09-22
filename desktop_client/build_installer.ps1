param(
    [string]$PythonCommand = "py"
)

$ErrorActionPreference = "Stop"
$innoCompiler = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$innoCompilerPath = if ($innoCompiler) { $innoCompiler.Source } else { $null }

if (-not $innoCompiler) {
    $defaultCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $defaultCompiler) {
        $innoCompilerPath = $defaultCompiler
    }
}

if (-not $innoCompilerPath) {
    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php and run this script again."
}

& (Join-Path $PSScriptRoot "build_windows.ps1") -PythonCommand $PythonCommand
& $innoCompilerPath (Join-Path $PSScriptRoot "installer.iss")

$installer = Join-Path (Split-Path -Parent $PSScriptRoot) "installer-output\Minecraft-Control-Plane-Setup-0.1.0.exe"
if (-not (Test-Path $installer)) {
    throw "Inno Setup did not produce the installer."
}

Write-Host "Installer built at: $installer"
