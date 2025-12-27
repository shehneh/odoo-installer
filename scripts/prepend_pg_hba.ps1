Param(
    [string]$PgData = 'C:\Program Files\PostgreSQL\16\data'
)
$p = Join-Path $PgData 'pg_hba.conf'
$bak = "$p.bak.scripted"
Copy-Item -Path $p -Destination $bak -Force
$tmp = Join-Path $PgData 'pg_hba.conf.tmp'
"host all all 127.0.0.1/32 trust" | Out-File -FilePath $tmp -Encoding ascii
Get-Content $p | Out-File -FilePath $tmp -Append -Encoding ascii
Move-Item -Force $tmp $p
Write-Output "Prepended trust line and backed up to $bak"
