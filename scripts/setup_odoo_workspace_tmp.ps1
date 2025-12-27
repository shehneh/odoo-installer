
$ErrorActionPreference = "Stop"
$odooRoot = "D:\business\odoo\odoo19"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    راه‌اندازی Odoo 19 Workspace" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan

# Create workspace folder
if (-not (Test-Path $odooRoot)) {
    Write-Host "Creating workspace folder..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $odooRoot -Force | Out-Null
}

Set-Location $odooRoot

# Check if Git is installed
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "Git is not installed! Installing Git..." -ForegroundColor Yellow
    # Try to install Git from winget
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    
    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $git = Get-Command git -ErrorAction SilentlyContinue
    
    if (-not $git) {
        Write-Host "Git installation failed. Please install Git manually." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "Git is installed: $($git.Source)" -ForegroundColor Green

# Create odoo-src folder
$odooSrc = Join-Path $odooRoot "odoo-src"
if (-not (Test-Path $odooSrc)) {
    New-Item -ItemType Directory -Path $odooSrc -Force | Out-Null
}

# Clone Odoo 19
$odoo19 = Join-Path $odooSrc "odoo-19.0"
if (-not (Test-Path $odoo19)) {
    Write-Host "Cloning Odoo 19.0 (this may take a while)..." -ForegroundColor Yellow
    git clone --depth 1 --branch 19.0 https://github.com/odoo/odoo.git $odoo19
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Clone failed! Check internet connection." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "Odoo 19.0 already exists at $odoo19" -ForegroundColor Green
}

# Find Python
$pythonPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files\Python312\python.exe"
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

# Create venv
$venvPath = Join-Path $odooRoot "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    & $python -m venv $venvPath
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

# Upgrade pip in venv
Write-Host "Upgrading pip in venv..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip

# Install requirements
Write-Host "Installing Odoo requirements..." -ForegroundColor Yellow
$reqFile = Join-Path $odoo19 "requirements.txt"
if (Test-Path $reqFile) {
    & $venvPip install -r $reqFile
}

# Create start_odoo.ps1
$startScript = @"
param([switch]`$NoBrowser)
`$venv = Join-Path `$PSScriptRoot "venv\Scripts\python.exe"
`$odooBin = Join-Path `$PSScriptRoot "odoo-src\odoo-19.0\odoo-bin"
if (-not `$NoBrowser) {
    Start-Process "http://localhost:8069" -ErrorAction SilentlyContinue
}
& `$venv `$odooBin -c (Join-Path `$PSScriptRoot "odoo.conf")
"@

$startFile = Join-Path $odooRoot "start_odoo.ps1"
Set-Content -Path $startFile -Value $startScript -Encoding UTF8

# Create odoo.conf
$odooConf = @"
[options]
addons_path = $odooSrc/odoo-19.0/addons
data_dir = $odooRoot/data
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
http_port = 8069
admin_passwd = admin
"@

$confFile = Join-Path $odooRoot "odoo.conf"
if (-not (Test-Path $confFile)) {
    Set-Content -Path $confFile -Value $odooConf -Encoding UTF8
}

# Create data folder
$dataDir = Join-Path $odooRoot "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Odoo workspace created successfully!" -ForegroundColor Green
Write-Host "  Location: $odooRoot" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Read-Host "Press Enter to close"
