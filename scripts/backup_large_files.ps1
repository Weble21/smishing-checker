param(
    [string]$Destination = [Environment]::GetFolderPath('Desktop'),
    [long]$MinimumBytes = 100MB
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent)).TrimEnd('\')
$destinationRoot = [System.IO.Path]::GetFullPath($Destination)
$files = @(Get-ChildItem -LiteralPath $projectRoot -Recurse -File -Force |
    Where-Object { $_.FullName -notlike "$projectRoot\.git\*" -and $_.Length -ge $MinimumBytes } |
    Sort-Object FullName)
if ($files.Count -eq 0) { throw 'No large files found.' }

$archivePath = Join-Path $destinationRoot ('smishing-checker-large-files-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.zip')
$stream = [System.IO.File]::Open($archivePath, [System.IO.FileMode]::CreateNew)
try {
    $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create, $true)
    try {
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring($projectRoot.Length + 1).Replace('\', '/')
            Write-Output "Adding $relativePath"
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $file.FullName, $relativePath,
                [System.IO.Compression.CompressionLevel]::Fastest
            ) | Out-Null
        }
    } finally {
        $archive.Dispose()
    }
} finally {
    $stream.Dispose()
}

$verified = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    if ($verified.Entries.Count -ne $files.Count) { throw 'Archive entry count mismatch.' }
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($projectRoot.Length + 1).Replace('\', '/')
        $entry = $verified.GetEntry($relativePath)
        if ($null -eq $entry -or $entry.Length -ne $file.Length) {
            throw "Archive entry missing or size mismatch: $relativePath"
        }
    }
} finally {
    $verified.Dispose()
}

Write-Output "Verified $($files.Count) files in $archivePath"
Write-Output "Archive bytes: $((Get-Item -LiteralPath $archivePath).Length)"
