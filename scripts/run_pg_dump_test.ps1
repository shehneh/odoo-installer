$env:PGPASSWORD='odoo'
$out = Join-Path $env:TEMP 'odoo_backup_test2.sql'
Write-Output "Running pg_dump -> $out"
& 'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe' -U postgres -h 127.0.0.1 -p 5432 --no-owner -f $out odoo19_odoo
Write-Output "EXIT=$LASTEXITCODE"
if (Test-Path $out) { Get-Item $out | Select-Object FullName,Length } else { Write-Output 'DUMP_NOT_FOUND' }
