<#
Auto-fetch and setup script for Odoo19 prerequisites.
- Creates a local package store under %USERPROFILE%\Setup_odoo19\offline
- Attempts to download Python, PostgreSQL, wkhtmltopdf using configurable URLs
- Downloads Python wheelhouse from requirements.txt (if internet) into offline\wheels
- Prompts before running installers (safety)

Run as Administrator when ready.
#>

param(
    [switch]$AutoRun,
    [string]$BasePath
)

# Determine target base directory. Prefer explicit BasePath, then script location, else user profile.
if ($BasePath){
    $Base = $BasePath
} elseif ($PSScriptRoot -and ($PSScriptRoot -ne '')){
    # Use the script's directory as the base
    $Base = $PSScriptRoot
} else {
    $Base = Join-Path $env:USERPROFILE 'Setup_odoo19'
}
$Offline = Join-Path $Base 'offline'
$Dirs = @('python','postgresql','wkhtmltopdf','wheels') | ForEach-Object { Join-Path $Offline $_ }
foreach ($d in $Dirs){ if (-not (Test-Path $d)){ New-Item -ItemType Directory -Path $d -Force | Out-Null } }
$Log = Join-Path $Base 'fetch_setup.log'
function L{ param($m) $t=(Get-Date).ToString('s'); "$t`t$m" | Out-File -FilePath $Log -Append }
L "Starting auto_fetch_and_setup.ps1"

# Default download URLs — adjust if you prefer different versions
$urls = @{
    python = 'https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe'
    postgresql = 'https://get.enterprisedb.com/postgresql/postgresql-16.0-1-windows-x64.exe'
    wkhtmltopdf = 'https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox-0.12.6.1-2.msvc2015-win64.exe'
}

function Download-IfMissing([string]$url,[string]$dest){
    if (Test-Path $dest){ L "Already exists: $dest"; return $true }
    try{
        Write-Host "Downloading $url -> $dest"
        L "Downloading $url -> $dest"
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -TimeoutSec 600
        L "Downloaded: $dest"
        # Attempt to also download checksum file if present (filename + .sha256)
        try{
            $shaUrl = "$url.sha256"
            $shaDest = "$dest.sha256"
            Invoke-WebRequest -Uri $shaUrl -OutFile $shaDest -UseBasicParsing -TimeoutSec 20 -ErrorAction Stop
            L "Downloaded checksum: $shaDest"
        } catch { }
        return $true
    }catch{
        L "Download failed: $url -> $($_.Exception.Message)"
        Write-Warning "Download failed: $url -> $($_.Exception.Message)"
        return $false
    }
}

function Verify-Checksum([string]$file){
    $sumFile = "$file.sha256"
    if (-not (Test-Path $sumFile)){ return $true }
    try{
        $expected = Get-Content $sumFile -ErrorAction Stop | Select-Object -First 1
        $actual = Get-FileHash -Algorithm SHA256 -Path $file | Select-Object -ExpandProperty Hash
        if ($expected -match $actual){ L "Checksum OK: $file"; return $true }
        else { L "Checksum MISMATCH: $file (expected $expected, got $actual)"; return $false }
    } catch { L "Checksum verify error: $file -> $($_.Exception.Message)"; return $false }
}

# Prepare file paths
$pyFile = Join-Path (Join-Path $Offline 'python') ([System.IO.Path]::GetFileName($urls.python))
$pgFile = Join-Path (Join-Path $Offline 'postgresql') ([System.IO.Path]::GetFileName($urls.postgresql))
$wkFile = Join-Path (Join-Path $Offline 'wkhtmltopdf') ([System.IO.Path]::GetFileName($urls.wkhtmltopdf))

# Attempt downloads
$haveInternet = $true
try{ $null = Invoke-WebRequest -Uri 'https://www.google.com' -UseBasicParsing -TimeoutSec 10 } catch { $haveInternet = $false }
if (-not $haveInternet){ Write-Warning 'No internet connectivity detected. Place installers manually into the offline folders.'; L 'No internet detected'; }

if ($haveInternet){
    Download-IfMissing $urls.python $pyFile | Out-Null
    Download-IfMissing $urls.postgresql $pgFile | Out-Null
    Download-IfMissing $urls.wkhtmltopdf $wkFile | Out-Null
    # Verify checksums when available
    foreach ($f in @($pyFile,$pgFile,$wkFile)){
        if ((Test-Path $f) -and -not (Verify-Checksum $f)){
            Write-Warning "Checksum failed for $f; consider redownloading or placing a trusted copy in the offline folder."
        }
    }
}

# If requirements.txt exists in the offline folder under the configured base, download wheels
$reqCandidate = Join-Path $Base 'offline\requirements.txt'
if (-not (Test-Path $reqCandidate)){
    Write-Host "No requirements.txt found at $reqCandidate. If you have odoo requirements, place the file there to populate wheelhouse."
    L "requirements.txt not found at $reqCandidate"
} elseif (-not $haveInternet){
    Write-Warning 'Cannot download wheelhouse without internet.'; L 'Wheelhouse download skipped (no internet)'
} else {
    $wheelDest = Join-Path $Offline 'wheels'
    Write-Host "Downloading wheels for requirements.txt to $wheelDest (may take time)"
    L "Downloading wheels to $wheelDest from $reqCandidate"
    & python -m pip download -r $reqCandidate -d $wheelDest
    if ($LASTEXITCODE -eq 0){ L 'pip download succeeded' } else { L "pip download exited: $LASTEXITCODE" }
}

# Prompt and run installers
function Prompt-Run([string]$path,[string]$arguments){
    if (-not (Test-Path $path)){ Write-Warning "File not found: $path"; return }
    if ($AutoRun){
        L "AutoRun enabled, running installer: $path $arguments"
        if ($arguments){
            try{ Start-Process -FilePath $path -ArgumentList $arguments -Wait -PassThru; L "Installer finished: $path" } catch { L "Installer error: $($_.Exception.Message)" }
        } else {
            try{ Start-Process -FilePath $path -Wait -PassThru; L "Installer finished: $path" } catch { L "Installer error: $($_.Exception.Message)" }
        }
        return
    }
    $q = Read-Host "Run installer $path with args '$arguments'? (Y/N)"
    if ($q -match '^[Yy]'){
        L "Running installer: $path $arguments"
        if ($arguments){
            try{ Start-Process -FilePath $path -ArgumentList $arguments -Wait -PassThru; L "Installer finished: $path" } catch { L "Installer error: $($_.Exception.Message)" }
        } else {
            try{ Start-Process -FilePath $path -Wait -PassThru; L "Installer finished: $path" } catch { L "Installer error: $($_.Exception.Message)" }
        }
    } else { L "User skipped installer: $path" }
}

if (Test-Path $pyFile){ Prompt-Run $pyFile '/quiet InstallAllUsers=1 PrependPath=1' }
if (Test-Path $pgFile){ Prompt-Run $pgFile '--mode unattended --superpassword=odoo' }
# If AutoRun was used and PostgreSQL installer was run unattended with known superpassword,
# attempt to create the Odoo DB role non-interactively using that password.
if ($AutoRun -and (Test-Path $pgFile)){
    $roleHelper = Join-Path $PSScriptRoot 'create_postgres_role.ps1'
    if (Test-Path $roleHelper){
        L "AutoRun: executing create_postgres_role.ps1 non-interactively"
        try{
            Start-Process -FilePath 'powershell' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File', $roleHelper, '-PostgresSuperPassword','odoo','-NonInteractive' -Wait -Verb RunAs
            L 'create_postgres_role.ps1 executed (AutoRun)'
        } catch { L "create_postgres_role failed: $($_.Exception.Message)" }
    } else { L 'create_postgres_role.ps1 not found; skipping role setup' }
}
if (Test-Path $wkFile){ Prompt-Run $wkFile '/quiet' }

Write-Host "All done. Log at: $Log"
L 'Script finished'
