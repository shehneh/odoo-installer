$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
# Find the largest exe under offline\wkhtmltopdf
$wkDir = Join-Path $ScriptDir 'offline\wkhtmltopdf'
if (-not (Test-Path $wkDir)) { Write-Error "wkhtmltopdf folder not found: $wkDir"; exit 2 }
$exe = Get-ChildItem -Path $wkDir -Filter *.exe -File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $exe){ Write-Error "No installer exe found in $wkDir"; exit 2 }
Write-Output "Starting wkhtmltopdf installer: $exe"
# Show installation UI so user can see progress
$p = Start-Process -FilePath $exe -Verb RunAs -Wait -PassThru
Write-Output "Installer ExitCode: $($p.ExitCode)"
$log = Join-Path $ScriptDir 'fetch_setup.log'
Add-Content -Path $log -Value ("$(Get-Date -Format s)`tinstall_wkhtmltopdf exitcode=$($p.ExitCode)")
if ($p.ExitCode -ne 0) { Write-Warning 'wkhtmltopdf installer returned non-zero exit code' } else { Write-Output 'wkhtmltopdf installed (exit 0)'}
