<#
.SYNOPSIS
    Check the status of offline packages for Odoo installation.

.DESCRIPTION
    Displays which packages are downloaded and their sizes.
    Useful for verifying the offline package collection is complete.
#>

param(
    [string]$BasePath
)

if ($BasePath){
    $Base = $BasePath
} elseif ($PSScriptRoot -and ($PSScriptRoot -ne '')){
    $Base = $PSScriptRoot
} else {
    $Base = Join-Path $env:USERPROFILE 'Setup_odoo19'
}

$Offline = Join-Path $Base 'offline'

Write-Host ""
Write-Host "=== Odoo Offline Package Status ===" -ForegroundColor Cyan
Write-Host "Base Path: $Base" -ForegroundColor Gray
Write-Host ""

function Check-Package([string]$folder, [string]$pattern){
    $path = Join-Path $Offline $folder
    if (-not (Test-Path $path)){
        Write-Host "[$folder] " -NoNewline -ForegroundColor Yellow
        Write-Host "Directory not found" -ForegroundColor Red
        return
    }
    
    $files = Get-ChildItem -Path $path -Filter $pattern -File -ErrorAction SilentlyContinue
    if ($files.Count -eq 0){
        Write-Host "[$folder] " -NoNewline -ForegroundColor Yellow
        Write-Host "No files found" -ForegroundColor Red
    } else {
        Write-Host "[$folder] " -NoNewline -ForegroundColor Green
        foreach ($f in $files){
            $sizeMB = [math]::Round($f.Length / 1MB, 2)
            Write-Host "$($f.Name) ($sizeMB MB)" -ForegroundColor White
            
            # Check for checksum file
            $shaFile = "$($f.FullName).sha256"
            if (Test-Path $shaFile){
                Write-Host "    ✓ Checksum file present" -ForegroundColor DarkGreen
            }
        }
    }
}

Check-Package 'python' '*.exe'
Check-Package 'postgresql' '*.exe'
Check-Package 'wkhtmltopdf' '*.exe'

# Check wheels
$wheelsPath = Join-Path $Offline 'wheels'
if (Test-Path $wheelsPath){
    $wheelCount = (Get-ChildItem -Path $wheelsPath -File -ErrorAction SilentlyContinue).Count
    if ($wheelCount -gt 0){
        Write-Host "[wheels] " -NoNewline -ForegroundColor Green
        Write-Host "$wheelCount packages downloaded" -ForegroundColor White
    } else {
        Write-Host "[wheels] " -NoNewline -ForegroundColor Yellow
        Write-Host "Empty (place requirements.txt in offline/ and re-run)" -ForegroundColor Gray
    }
} else {
    Write-Host "[wheels] " -NoNewline -ForegroundColor Yellow
    Write-Host "Directory not found" -ForegroundColor Red
}

# Check requirements.txt
$reqFile = Join-Path $Base 'offline\requirements.txt'
if (Test-Path $reqFile){
    $reqLines = (Get-Content $reqFile | Where-Object { $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*$' }).Count
    Write-Host "`n[requirements.txt] " -NoNewline -ForegroundColor Cyan
    Write-Host "Found ($reqLines packages specified)" -ForegroundColor White
} else {
    Write-Host "`n[requirements.txt] " -NoNewline -ForegroundColor Yellow
    Write-Host "Not found" -ForegroundColor Gray
}

# Log file
$logFile = Join-Path $Base 'fetch_setup.log'
if (Test-Path $logFile){
    $lastLog = Get-Content $logFile -Tail 1
    Write-Host "`n[Log] Last entry: " -NoNewline -ForegroundColor Gray
    Write-Host $lastLog -ForegroundColor DarkGray
}

Write-Host "`n=================================`n" -ForegroundColor Cyan
