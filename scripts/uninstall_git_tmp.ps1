
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling Git..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$found = $false
foreach ($path in $regPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Git*" -and $_.DisplayName -notlike "*GitHub*" }
    foreach ($app in $apps) {
        $found = $true
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString) {
            $uninstaller = $app.UninstallString -replace '"', ''
            Write-Host "Running uninstaller: $uninstaller" -ForegroundColor Yellow
            if (Test-Path $uninstaller) {
                Start-Process -FilePath $uninstaller -ArgumentList "/VERYSILENT", "/NORESTART" -Wait -ErrorAction SilentlyContinue
            }
        }
    }
}

if (-not $found) {
    Write-Host "Git not found in registry." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Git uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
