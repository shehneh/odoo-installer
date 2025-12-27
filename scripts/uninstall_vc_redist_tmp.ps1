
$apps = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like "*Visual C++*2015*2022*x64*" }
foreach ($app in $apps) {
    if ($app.UninstallString) {
        Write-Host "Uninstalling: $($app.DisplayName)"
        $cmd = $app.UninstallString -replace '"', ''
        Start-Process -FilePath $cmd -ArgumentList "/quiet", "/norestart" -Wait -Verb RunAs -ErrorAction SilentlyContinue
    }
}
