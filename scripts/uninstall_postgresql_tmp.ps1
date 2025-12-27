
$pgRoot = "C:\Program Files\PostgreSQL"
$versions = Get-ChildItem $pgRoot -Directory -ErrorAction SilentlyContinue
foreach ($v in $versions) {
    $uninstaller = Join-Path $v.FullName "uninstall-postgresql.exe"
    if (Test-Path $uninstaller) {
        Write-Host "Uninstalling PostgreSQL $($v.Name)..."
        Start-Process -FilePath $uninstaller -ArgumentList "--mode", "unattended" -Wait -Verb RunAs
    }
}
