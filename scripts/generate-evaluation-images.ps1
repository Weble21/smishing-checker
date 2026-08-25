param(
    [string]$ManifestPath = "evaluation/labels.json",
    [string]$OutputDirectory = "evaluation/images"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$projectRoot = Split-Path -Parent $PSScriptRoot
$manifestFullPath = Join-Path $projectRoot $ManifestPath
$outputFullPath = Join-Path $projectRoot $OutputDirectory

New-Item -ItemType Directory -Force -Path $outputFullPath | Out-Null
$cases = Get-Content -Raw -Encoding UTF8 $manifestFullPath | ConvertFrom-Json

function New-RoundedRectanglePath {
    param(
        [System.Drawing.RectangleF]$Rectangle,
        [float]$Radius
    )

    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $diameter = $Radius * 2
    $arc = [System.Drawing.RectangleF]::new(
        $Rectangle.X,
        $Rectangle.Y,
        $diameter,
        $diameter
    )
    $path.AddArc($arc, 180, 90)
    $arc.X = $Rectangle.Right - $diameter
    $path.AddArc($arc, 270, 90)
    $arc.Y = $Rectangle.Bottom - $diameter
    $path.AddArc($arc, 0, 90)
    $arc.X = $Rectangle.Left
    $path.AddArc($arc, 90, 90)
    $path.CloseFigure()
    return $path
}

foreach ($case in $cases) {
    $bitmap = [System.Drawing.Bitmap]::new(720, 900)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.Color]::FromArgb(246, 248, 252))

    $headerBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 255, 255))
    $textBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(25, 32, 45))
    $mutedBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(110, 119, 135))
    $bubbleBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(229, 234, 242))
    $accentBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(53, 99, 233))
    $headerFont = [System.Drawing.Font]::new("Malgun Gothic", 24, [System.Drawing.FontStyle]::Bold)
    $bodyFont = [System.Drawing.Font]::new("Malgun Gothic", 23, [System.Drawing.FontStyle]::Regular)
    $smallFont = [System.Drawing.Font]::new("Malgun Gothic", 15, [System.Drawing.FontStyle]::Regular)
    $statusFont = [System.Drawing.Font]::new("Malgun Gothic", 14, [System.Drawing.FontStyle]::Bold)

    try {
        $graphics.FillRectangle($headerBrush, 0, 0, 720, 150)
        $graphics.DrawString("9:41", $statusFont, $textBrush, 30, 18)
        $graphics.DrawString("Messages", $smallFont, $accentBrush, 30, 72)

        $senderFormat = [System.Drawing.StringFormat]::new()
        $senderFormat.Alignment = [System.Drawing.StringAlignment]::Center
        $graphics.DrawString(
            [string]$case.sender,
            $headerFont,
            $textBrush,
            [System.Drawing.RectangleF]::new(120, 62, 480, 55),
            $senderFormat
        )
        $senderFormat.Dispose()

        $graphics.DrawString("Today 2:18 PM", $smallFont, $mutedBrush, 286, 185)

        $bubbleRectangle = [System.Drawing.RectangleF]::new(38, 235, 644, 420)
        $bubblePath = New-RoundedRectanglePath -Rectangle $bubbleRectangle -Radius 26
        $graphics.FillPath($bubbleBrush, $bubblePath)

        $bodyFormat = [System.Drawing.StringFormat]::new()
        $bodyFormat.Trimming = [System.Drawing.StringTrimming]::Word
        $bodyFormat.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit
        $graphics.DrawString(
            [string]$case.message,
            $bodyFont,
            $textBrush,
            [System.Drawing.RectangleF]::new(70, 270, 580, 350),
            $bodyFormat
        )

        $graphics.DrawString("Read", $smallFont, $mutedBrush, 618, 670)

        $outputFile = Join-Path $outputFullPath ($case.id + ".png")
        $bitmap.Save($outputFile, [System.Drawing.Imaging.ImageFormat]::Png)

        $bodyFormat.Dispose()
        $bubblePath.Dispose()
    }
    finally {
        $headerBrush.Dispose()
        $textBrush.Dispose()
        $mutedBrush.Dispose()
        $bubbleBrush.Dispose()
        $accentBrush.Dispose()
        $headerFont.Dispose()
        $bodyFont.Dispose()
        $smallFont.Dispose()
        $statusFont.Dispose()
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

Write-Host ("Generated {0} evaluation images in {1}" -f $cases.Count, $outputFullPath)
