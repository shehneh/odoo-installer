<#
create_postgres_role.ps1

Helper to create PostgreSQL role (user) for Odoo and an example database.
It reads `db_user` and `db_password` from the Odoo config if available, then
prompts for the PostgreSQL superuser password and executes the SQL using psql.

Run as Administrator and ensure PostgreSQL is started.
#>

Param(
    [string]$PostgresSuperPassword,
    [switch]$NonInteractive
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Base = $ScriptDir
$log = Join-Path $Base 'fetch_setup.log'
function L { param($m) $t=(Get-Date).ToString('s'); "$t`t$m" | Out-File -FilePath $log -Append }
L 'Starting create_postgres_role.ps1'

# Locate odoo.conf in a portable way: check a few candidate locations relative to the project,
# then fall back to a recursive search under the project root.
$confCandidates = @(
    Join-Path $Base 'odoo19\config\odoo.conf',
    Join-Path $Base '..\odoo19\config\odoo.conf',
    Join-Path $Base '..\..\odoo19\config\odoo.conf'
)
$confPath = $null
foreach ($c in $confCandidates){ if (Test-Path $c){ $confPath = (Resolve-Path $c).Path; break } }
if (-not $confPath){
    $found = Get-ChildItem -Path $Base -Recurse -Filter odoo.conf -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found){ $confPath = $found.FullName }
}
$db_user = $null; $db_password = $null
if (Test-Path $confPath){
    L "Reading config: $confPath"
    $lines = Get-Content $confPath
    foreach ($ln in $lines){
        if ($ln -match '^[\s#]*db_user\s*=\s*(.+)') { $db_user = $Matches[1].Trim() }
        if ($ln -match '^[\s#]*db_password\s*=\s*(.+)') { $db_password = $Matches[1].Trim() }
    }
}

if (-not $db_user){ $db_user = Read-Host 'db_user for Odoo (e.g. odoo19)' }
if (-not $db_password){ $db_password = Read-Host 'db_password for Odoo user (will be stored in DB role)' }

# Ask for postgres superuser password (or use provided one in non-interactive mode)
if ($PostgresSuperPassword){
    $pg_pass_plain = $PostgresSuperPassword
} elseif ($NonInteractive -and -not $PostgresSuperPassword){
    Write-Error 'NonInteractive requested but no PostgresSuperPassword provided.'
    exit 3
} else {
    $pg_super = Read-Host -AsSecureString 'Postgres superuser (postgres) password - input will be hidden'
    $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pg_super)
    $pg_pass_plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

# Find psql: prefer psql on PATH, then search common Program Files locations under the project
$psql = $null
$cmd = Get-Command psql -ErrorAction SilentlyContinue
if ($cmd){ $psql = $cmd.Source }
if (-not $psql){
    $programRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)})
    foreach ($r in $programRoots){
        if ($r){
            $candidateRoot = Join-Path $r 'PostgreSQL'
            if (Test-Path $candidateRoot){
                $psql = Get-ChildItem $candidateRoot -Recurse -Filter psql.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
                if ($psql){ break }
            }
        }
    }
}
if (-not $psql){
    Write-Error 'psql.exe not found (not on PATH and not under Program Files); please install PostgreSQL or add psql to PATH.'
    L 'psql.exe not found'
    exit 1
}
L "Found psql: $psql"

# Set temporary PGPASSWORD for non-interactive psql
$env:PGPASSWORD = $pg_pass_plain

# Create role (if not exists) and grant CREATEDB
$createRoleSql = @"
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$db_user') THEN
      PERFORM pg_catalog.set_config('search_path', '', false);
      CREATE ROLE \"$db_user\" WITH LOGIN PASSWORD '$db_password' CREATEDB;
   END IF;
END
$do$;
"@

& $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -c $createRoleSql
if ($LASTEXITCODE -ne 0){ L "Failed to create role $db_user (psql exit $LASTEXITCODE)"; Write-Error 'Role creation failed'; $env:PGPASSWORD = $null; exit 2 }
L "Role ensured: $db_user"

# Optionally create an example database to test Odoo connection
$exists = & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='odoo19_odoo';" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
if (-not $exists){
    Write-Host "Creating test database 'odoo19_odoo' owned by $db_user"
    L "Creating database odoo19_odoo owned by $db_user"
    & $psql -U postgres -h 127.0.0.1 -p 5432 -d postgres -c "CREATE DATABASE \"odoo19_odoo\" OWNER \"$db_user\";"
    if ($LASTEXITCODE -ne 0){ L "Failed to create database odoo19_odoo (psql exit $LASTEXITCODE)"; Write-Warning 'Database creation failed (you can retry manually)'} else { L 'Database odoo19_odoo created' }
} else { L 'Database odoo19_odoo already exists' }

# Clear sensitive env var
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
L 'Finished create_postgres_role.ps1'
Write-Host 'Done. Check fetch_setup.log for details.'
