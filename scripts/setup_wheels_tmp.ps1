
$ErrorActionPreference = "Stop"
$wheelDir = "D:\business\odoo\Setup odoo19\offline\wheels"
$reqFile = "D:\business\odoo\Setup odoo19\offline\requirements.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  دانلود پکیج‌های pip برای نصب آفلاین" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Find Python
$pythonPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python312\python.exe"
)

$python = $null
foreach ($p in $pythonPaths) {
    if (Test-Path $p) {
        $python = $p
        break
    }
}

if (-not $python) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if (-not $python) {
    Write-Host "Python not found! Please install Python first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Using Python: $python" -ForegroundColor Green

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $python -m pip install --upgrade pip

# Download wheels
Write-Host "Downloading wheels to: $wheelDir" -ForegroundColor Yellow
& $python -m pip download -d $wheelDir -r $reqFile --prefer-binary

if ($LASTEXITCODE -eq 0) {
    $count = (Get-ChildItem $wheelDir -Filter *.whl).Count + (Get-ChildItem $wheelDir -Filter *.tar.gz).Count
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Download complete! $count packages" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "Some packages may have failed to download" -ForegroundColor Yellow
}

Read-Host "Press Enter to close"
