param(
    [string]$SourceImage = (Join-Path (Split-Path -Parent $PSScriptRoot) "aimnet-minecraft-icon.png"),
    [string]$OutputIcon = (Join-Path $PSScriptRoot "aimnet-minecraft.ico")
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $SourceImage)) {
    throw "Source image not found: $SourceImage"
}

$sizes = 16, 24, 32, 48, 64, 128, 256
$source = [System.Drawing.Image]::FromFile($SourceImage)
$frames = @()

try {
    foreach ($size in $sizes) {
        $bitmap = New-Object System.Drawing.Bitmap $size, $size
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.DrawImage($source, 0, 0, $size, $size)
        $graphics.Dispose()

        $stream = New-Object System.IO.MemoryStream
        $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
        $bitmap.Dispose()
        $frames += ,@($size, $stream.ToArray())
        $stream.Dispose()
    }
}
finally {
    $source.Dispose()
}

# Windows supports PNG-compressed icon frames; this keeps alpha transparency crisp.
$output = New-Object System.IO.MemoryStream
$writer = New-Object System.IO.BinaryWriter $output
$writer.Write([UInt16]0)
$writer.Write([UInt16]1)
$writer.Write([UInt16]$frames.Count)

$offset = 6 + (16 * $frames.Count)
foreach ($frame in $frames) {
    $size = $frame[0]
    $bytes = $frame[1]
    $writer.Write([Byte]$(if ($size -eq 256) { 0 } else { $size }))
    $writer.Write([Byte]$(if ($size -eq 256) { 0 } else { $size }))
    $writer.Write([Byte]0)
    $writer.Write([Byte]0)
    $writer.Write([UInt16]1)
    $writer.Write([UInt16]32)
    $writer.Write([UInt32]$bytes.Length)
    $writer.Write([UInt32]$offset)
    $offset += $bytes.Length
}

foreach ($frame in $frames) {
    $writer.Write($frame[1])
}

$writer.Flush()
[System.IO.File]::WriteAllBytes($OutputIcon, $output.ToArray())
$writer.Dispose()
$output.Dispose()
Write-Host "Windows icon created at: $OutputIcon"
