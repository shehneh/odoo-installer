
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling wkhtmltopdf..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Method 1: Registry lookup
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$found = $false
foreach ($path in $regPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*wkhtmltopdf*" -or $_.DisplayName -like "*wkhtmltox*" }
    foreach ($app in $apps) {
        $found = $true
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString -like "*MsiExec*") {
            $productCode = $app.PSChildName
            Write-Host "Uninstalling via MSI..." -ForegroundColor Yellow
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/X", $productCode, "/quiet", "/norestart" -Wait
        } elseif ($app.UninstallString) {
            $uninstaller = $app.UninstallString -replace '"', ''
            Write-Host "Running uninstaller: $uninstaller" -ForegroundColor Yellow
            if (Test-Path $uninstaller) {
                Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait
            }
        }
    }
}

# Method 2: Check common install location
$wkPath = "C:\Program Files\wkhtmltopdf"
if (Test-Path $wkPath) {
    $uninstaller = Join-Path $wkPath "uninstall.exe"
    if (Test-Path $uninstaller) {
        Write-Host "Running uninstaller from $wkPath..." -ForegroundColor Yellow
        Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait
        $found = $true
    }
}

if (-not $found) {
    Write-Host "wkhtmltopdf not found in registry." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "wkhtmltopdf uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
