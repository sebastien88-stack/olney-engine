# Keep the black spade body and white ornaments; remove only the outer background.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetDir = Join-Path $PSScriptRoot '..\assets'
$sourcePath = (Resolve-Path (Join-Path $assetDir 'olney_spade_source.png')).Path
$original = [System.Drawing.Bitmap]::FromFile($sourcePath)
$source = New-Object System.Drawing.Bitmap($original.Width, $original.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
try {
    for ($y = 0; $y -lt $original.Height; $y++) {
        $first = $original.Width
        $last = -1
        for ($x = 0; $x -lt $original.Width; $x++) {
            $pixel = $original.GetPixel($x, $y)
            if ([Math]::Max($pixel.R, [Math]::Max($pixel.G, $pixel.B)) -gt 96) {
                $first = [Math]::Min($first, $x)
                $last = $x
            }
        }
        for ($x = $first; $x -le $last; $x++) {
            $pixel = $original.GetPixel($x, $y)
            $source.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, $pixel.R, $pixel.G, $pixel.B))
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
            # Classic 32-bit DIB plus an explicit AND mask: also supported by
            # Windows consumers that do not honor PNG icon alpha correctly.
            $dib = New-Object System.IO.BinaryWriter($buffer)
            $maskStride = 4 * [int][Math]::Ceiling($size / 32.0)
            $dib.Write([UInt32]40)
            $dib.Write([Int32]$size); $dib.Write([Int32](2 * $size))
            $dib.Write([UInt16]1); $dib.Write([UInt16]32)
            $dib.Write([UInt32]0); $dib.Write([UInt32]($size * $size * 4))
            $dib.Write([Int32]0); $dib.Write([Int32]0)
            $dib.Write([UInt32]0); $dib.Write([UInt32]0)
            for ($row = $size - 1; $row -ge 0; $row--) {
                for ($column = 0; $column -lt $size; $column++) {
                    $color = $bitmap.GetPixel($column, $row)
                    $dib.Write([Byte]$color.B); $dib.Write([Byte]$color.G)
                    $dib.Write([Byte]$color.R); $dib.Write([Byte]$color.A)
                }
            }
            for ($row = $size - 1; $row -ge 0; $row--) {
                $mask = New-Object byte[] $maskStride
                for ($column = 0; $column -lt $size; $column++) {
                    if ($bitmap.GetPixel($column, $row).A -eq 0) {
                        $index = [int][Math]::Floor($column / 8)
                        $mask[$index] = $mask[$index] -bor (128 -shr ($column % 8))
                    }
                }
                $dib.Write($mask)
            }
            $dib.Flush()
            $images.Add($buffer.ToArray())
            if ($size -eq 256) {
                $bitmap.Save((Join-Path $assetDir 'olney_icon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
                $header = New-Object System.Drawing.Bitmap(40, 40)
                $headerGraphics = [System.Drawing.Graphics]::FromImage($header)
                try {
                    $headerGraphics.Clear([System.Drawing.Color]::Transparent)
                    $headerGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                    $headerGraphics.DrawImage($source, 0, 0, 40, 40)
                    $header.Save((Join-Path $assetDir 'olney_header.png'), [System.Drawing.Imaging.ImageFormat]::Png)
                } finally { $headerGraphics.Dispose(); $header.Dispose() }
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
Copy-Item -LiteralPath (Join-Path $assetDir 'olney_icon.ico') -Destination (Join-Path $assetDir 'olney_windows_v3.ico') -Force
Write-Output 'Transparent spade: original strokes preserved; 9 ICO sizes written.'
