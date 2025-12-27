
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling Python..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Find Python in registry (both HKLM and HKCU)
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$apps = @()
foreach ($path in $regPaths) {
    $apps += Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Python 3*" }
}

if ($apps.Count -eq 0) {
    Write-Host "No Python installation found." -ForegroundColor Yellow
} else {
    foreach ($app in $apps) {
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString -like "*MsiExec*") {
            # Extract product code from UninstallString
            $productCode = $app.PSChildName
            Write-Host "Uninstalling via MSI: $productCode" -ForegroundColor Yellow
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/X", $productCode, "/quiet", "/norestart" -Wait
        } elseif ($app.UninstallString) {
            Write-Host "Running uninstaller..." -ForegroundColor Yellow
            $uninstaller = $app.UninstallString -replace '"', ''
            if (Test-Path $uninstaller) {
                Start-Process -FilePath $uninstaller -ArgumentList "/quiet" -Wait
            }
        }
    }
}

Write-Host ""
Write-Host "Python uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
