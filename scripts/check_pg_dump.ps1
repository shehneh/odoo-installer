<#
check_pg_dump.ps1

Find installed pg_dump.exe binaries, test them for runtime errors,
and optionally update `pg_path` in the project's `odoo.conf` to a working bin.

Usage:
  .\check_pg_dump.ps1            # just test and report
  .\check_pg_dump.ps1 -Apply     # update odoo.conf pg_path to first working pg_dump bin
#>

Param(
    [switch]$Apply
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Base = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$log = Join-Path $Base 'fetch_setup.log'
function L { param($m) $t=(Get-Date).ToString('s'); "$t`t$m" | Out-File -FilePath $log -Append }

L 'Starting check_pg_dump.ps1'

# gather candidate pg_dump.exe files under Program Files
$candidates = @()
$roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)})
foreach ($r in $roots){
    if (-not $r) { continue }
    $pgRoot = Join-Path $r 'PostgreSQL'
    if (Test-Path $pgRoot){
        $found = Get-ChildItem -Path $pgRoot -Recurse -Filter pg_dump.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
        foreach ($f in $found){ if (-not ($candidates -contains $f)) { $candidates += $f } }
    }
}

# Also check PATH
$which = (Get-Command pg_dump -ErrorAction SilentlyContinue) | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue
if ($which){ if (-not ($candidates -contains $which)) { $candidates += $which } }

if (-not $candidates){
    Write-Host 'No pg_dump.exe found under Program Files or on PATH.'
    L 'No pg_dump found'
    Write-Host 'Ensure PostgreSQL is installed or add its bin folder to PATH.'
    exit 1
}

function Test-PgDump($exe){
    Write-Host "Testing: $exe"
    try{
        # call operator to run the exe; suppress stdout, capture exit code
        & $exe --version > $null 2>$null
        $ec = $LASTEXITCODE
        return @{Path=$exe; ExitCode=$ec}
    } catch {
        return @{Path=$exe; ExitCode=$LASTEXITCODE}
    }
}

$results = @()
foreach ($c in $candidates){
    $res = Test-PgDump $c
    $results += $res
    if ($res.ExitCode -eq 0){ Write-Host "OK: $($res.Path)"; L "pg_dump OK: $($res.Path)" } else {
        Write-Host "FAIL (exit $($res.ExitCode)): $($res.Path)"
        L "pg_dump FAIL exit $($res.ExitCode): $($res.Path)"
    }
}

$good = $results | Where-Object { $_.ExitCode -eq 0 }
if ($good.Count -gt 0){
    $first = $good[0].Path
    Write-Host "Working pg_dump found: $first"
    if ($Apply){
        # locate odoo.conf
        $confCandidates = @(
            Join-Path $Base 'odoo19\config\odoo.conf'
            Join-Path $Base '..\odoo19\config\odoo.conf'
            Join-Path $Base '..\..\odoo19\config\odoo.conf'
        )
        $confPath = $null
        foreach ($c in $confCandidates){ if (Test-Path $c){ $confPath = (Resolve-Path $c).Path; break } }
        if (-not $confPath){
            $found = Get-ChildItem -Path $Base -Recurse -Filter odoo.conf -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found){ $confPath = $found.FullName }
        }
        if (-not $confPath){ Write-Host 'odoo.conf not found; cannot apply pg_path update'; L 'odoo.conf not found (check_pg_dump)'; exit 2 }
        # backup and update
        $bak = "$confPath.bak.check_pg_dump"
        Copy-Item -Path $confPath -Destination $bak -Force
        $lines = Get-Content $confPath
        $binDir = (Split-Path $first -Parent)
        $foundLine = $false
        for ($i=0;$i -lt $lines.Count;$i++){
            if ($lines[$i] -match '^[\s#]*pg_path\s*='){
                $lines[$i] = "pg_path = $binDir"
                $foundLine = $true
            }
        }
        if (-not $foundLine){ $lines += "pg_path = $binDir" }
        $lines | Set-Content -Path $confPath -Encoding UTF8
        Write-Host "Updated odoo.conf pg_path -> $binDir (backup: $bak)"
        L "Updated odoo.conf pg_path -> $binDir"
    }
    exit 0
} else {
    Write-Host 'No working pg_dump found. This commonly means a required Visual C++ runtime is missing (STATUS_DLL_NOT_FOUND).' -ForegroundColor Yellow
    Write-Host 'Install the Microsoft Visual C++ Redistributable (2015-2022 x64) and retry:'
    Write-Host 'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist'
    L 'No working pg_dump found; advise installing Visual C++ redistributable'
    exit 3
}
