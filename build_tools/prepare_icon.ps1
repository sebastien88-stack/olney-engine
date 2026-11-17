# Rebuild Windows icons from the original white-on-black spade without redrawing it.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetDir = Join-Path $PSScriptRoot '..\assets'
$sourcePath = (Resolve-Path (Join-Path $assetDir 'olney_spade_source.png')).Path
$original = [System.Drawing.Bitmap]::FromFile($sourcePath)
$source = New-Object System.Drawing.Bitmap($original.Width, $original.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
try {
    for ($y = 0; $y -lt $original.Height; $y++) {
        for ($x = 0; $x -lt $original.Width; $x++) {
            $pixel = $original.GetPixel($x, $y)
            $alpha = [Math]::Max($pixel.R, [Math]::Max($pixel.G, $pixel.B))
            # Discard faint compression noise in the black background, retaining
            # smooth antialiasing on the original bright strokes.
            $alpha = if ($alpha -le 64) { 0 } else { [int](255 * ($alpha - 64) / 191) }
            $source.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($alpha, 255, 255, 255))
        }
    }
} finally { $original.Dispose() }
$images = New-Object 'System.Collections.Generic.List[byte[]]'
$sizes = @(16, 20, 24, 32, 40, 48, 64, 128, 256)
try {
    $source.Save((Join-Path $assetDir 'olney_spade_transparent.png'), [System.Drawing.Imaging.ImageFormat]::Png)
    foreach ($size in $sizes) {
        $bitmap = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.DrawImage($source, 0, 0, $size, $size)
        } finally { $graphics.Dispose() }
        $buffer = New-Object System.IO.MemoryStream
        try {
            $bitmap.Save($buffer, [System.Drawing.Imaging.ImageFormat]::Png)
            $images.Add($buffer.ToArray())
            if ($size -eq 256) {
                $bitmap.Save((Join-Path $assetDir 'olney_icon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
                if ($bitmap.GetPixel(0, 0).A -ne 0) { throw 'Icon corner must be transparent' }
            }
        } finally { $buffer.Dispose(); $bitmap.Dispose() }
    }
} finally { $source.Dispose() }
$stream = [System.IO.File]::Create((Join-Path $assetDir 'olney_icon.ico'))
$writer = New-Object System.IO.BinaryWriter($stream)
try {
    $writer.Write([UInt16]0); $writer.Write([UInt16]1); $writer.Write([UInt16]$sizes.Count)
    $offset = 6 + 16 * $sizes.Count
    for ($i = 0; $i -lt $sizes.Count; $i++) {
        $dimension = if ($sizes[$i] -eq 256) { 0 } else { $sizes[$i] }
        $writer.Write([Byte]$dimension); $writer.Write([Byte]$dimension)
        $writer.Write([Byte]0); $writer.Write([Byte]0)
        $writer.Write([UInt16]1); $writer.Write([UInt16]32)
        $writer.Write([UInt32]$images[$i].Length); $writer.Write([UInt32]$offset)
        $offset += $images[$i].Length
    }
    foreach ($bytes in $images) { $writer.Write($bytes) }
} finally { $writer.Dispose(); $stream.Dispose() }
Write-Output 'Transparent spade: original strokes preserved; 9 ICO sizes written.'
