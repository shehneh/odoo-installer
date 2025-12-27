param(
    [Parameter(Mandatory = $false)]
    [string]$OdooMajor = "19",

    [Parameter(Mandatory = $false)]
    [string]$Version = "1.0.0",

    [Parameter(Mandatory = $false)]
    [string]$OutDir = "D:\business\odoo\Setup odoo19\dist",

    # Optional: GitHub Releases helper
    [Parameter(Mandatory = $false)]
    [string]$GitHubRepo = "",

    [Parameter(Mandatory = $false)]
    [string]$GitHubTag = "",

    # Update website/downloads.json automatically
    [Parameter(Mandatory = $false)]
    [switch]$UpdateWebsiteJson,

    [Parameter(Mandatory = $false)]
    [string]$WebsiteDir = "D:\business\odoo\Setup odoo19\website"
)

$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Force -Path $Path | Out-Null }
}

function Read-Json([string]$Path) {
    Get-Content -Raw -Path $Path | ConvertFrom-Json
}

function Save-JsonFile([string]$Path, [object]$Obj) {
    $json = $Obj | ConvertTo-Json -Depth 30
    Set-Content -Path $Path -Value $json -Encoding UTF8
}

$root = Split-Path -Parent $PSScriptRoot
$odooMajorInt = [int]$OdooMajor

Ensure-Dir $OutDir

$artifactName = "OdooInstaller-odoo$OdooMajor-$Version-lite-online.zip"
$artifactPath = Join-Path $OutDir $artifactName

$stageRoot = Join-Path $OutDir "_stage_lite_online"
if (Test-Path $stageRoot) { Remove-Item $stageRoot -Recurse -Force }
Ensure-Dir $stageRoot

$pkgDir = Join-Path $stageRoot "odoo$OdooMajor-lite-online-$Version"
Ensure-Dir $pkgDir

Write-Host "[*] Building lite-online package -> $artifactPath"

function Copy-IfExists([string]$src, [string]$dst) {
    if (Test-Path $src) {
        Ensure-Dir (Split-Path -Parent $dst)
        Copy-Item -Force $src $dst
        return $true
    }
    return $false
}

# Prefer shipping a compiled EXE (no Python sources exposed)
$exeSrcCandidates = @(
    (Join-Path $root "ui_server.exe"),
    (Join-Path $root "dist\ui_server.exe"),
    (Join-Path $root "dist\ui_server.dist\ui_server.exe")
)

$exeCopied = $false
foreach ($c in $exeSrcCandidates) {
    if (Copy-IfExists $c (Join-Path $pkgDir "ui_server.exe")) {
        $exeCopied = $true
        Write-Host "[OK] Using compiled UI server: $c" -ForegroundColor Green
        break
    }
}

if (-not $exeCopied) {
    Write-Host "[WARN] ui_server.exe not found; falling back to Python sources." -ForegroundColor Yellow
    # Core Python sources (fallback mode)
    $filesToCopy = @(
        "ui_server.py",
        "license_manager.py",
        "admin_config.py",
        "database_manager.py",
        "payment_config.py"
    )
    foreach ($f in $filesToCopy) {
        $src = Join-Path $root $f
        if (Test-Path $src) {
            Copy-Item -Force $src (Join-Path $pkgDir $f)
        } else {
            Write-Host "[WARN] Missing file (skipped): $src" -ForegroundColor Yellow
        }
    }
}

# Sidecar config + scripts required at runtime
$runtimeFiles = @(
    "installer_config.json",
    "auto_fetch_and_setup.ps1",
    "check_status.ps1",
    "create_postgres_role.ps1",
    "install_wkhtmltopdf.ps1",
    "USER_GUIDE.md"
)

foreach ($f in $runtimeFiles) {
    $src = Join-Path $root $f
    if (Test-Path $src) {
        Copy-Item -Force $src (Join-Path $pkgDir $f)
    } else {
        Write-Host "[WARN] Missing file (skipped): $src" -ForegroundColor Yellow
    }
}

# Web UI assets served by ui_server.py
$webSrc = Join-Path $root "web"
if (Test-Path $webSrc) {
    Copy-Item -Recurse -Force $webSrc (Join-Path $pkgDir "web")
} else {
    Write-Host "[WARN] Missing folder (skipped): $webSrc" -ForegroundColor Yellow
}

# Optional structure placeholders (keeps folders intact for future fallback)
Ensure-Dir (Join-Path $pkgDir "offline")
Ensure-Dir (Join-Path $pkgDir "soft")
Ensure-Dir (Join-Path $pkgDir "offline\python")
Ensure-Dir (Join-Path $pkgDir "offline\postgresql")
Ensure-Dir (Join-Path $pkgDir "offline\wkhtmltopdf")
Ensure-Dir (Join-Path $pkgDir "offline\vc_redist")
Ensure-Dir (Join-Path $pkgDir "soft\git")
Ensure-Dir (Join-Path $pkgDir "soft\nodejs")

# Launcher
$launcherSrc = Join-Path $root "scripts\start_ui_online.bat"
if (-not (Test-Path $launcherSrc)) {
    throw "Missing launcher: $launcherSrc"
}
Copy-Item -Force $launcherSrc (Join-Path $pkgDir "start_ui_online.bat")

# Zip
if (Test-Path $artifactPath) { Remove-Item $artifactPath -Force }
Compress-Archive -Path (Join-Path $pkgDir "*") -DestinationPath $artifactPath -Force

$hash = (Get-FileHash -Algorithm SHA256 -Path $artifactPath).Hash.ToLowerInvariant()
$sizeBytes = (Get-Item $artifactPath).Length

$downloadUrl = ""
if ($GitHubRepo -and $GitHubTag) {
    $downloadUrl = "https://github.com/$GitHubRepo/releases/download/$GitHubTag/$artifactName"
}

Write-Host "[OK] SHA256: $hash"
Write-Host "[OK] Size:   $sizeBytes bytes"
if ($downloadUrl) { Write-Host "[OK] URL:    $downloadUrl" }

# Update website/downloads.json
if ($UpdateWebsiteJson) {
    $downloadsPath = Join-Path (Resolve-Path $WebsiteDir) "downloads.json"
    if (-not (Test-Path $downloadsPath)) { throw "downloads.json not found at: $downloadsPath" }

    $downloads = Read-Json $downloadsPath
    $targetVersion = $downloads.versions | Where-Object { $_.odoo_major -eq $odooMajorInt } | Select-Object -First 1
    if (-not $targetVersion) { throw "downloads.json has no entry for odoo_major=$odooMajorInt" }

    $targetId = "odoo$OdooMajor-lite-online"
    $existing = $targetVersion.items | Where-Object { $_.id -eq $targetId } | Select-Object -First 1
    if (-not $existing) { throw "downloads.json is missing item id=$targetId" }

    $existing.version = $Version
    $existing.file_type = "zip"
    $existing.size_hint = "${sizeBytes} bytes"
    $existing.sha256 = $hash
    if ($downloadUrl) { $existing.download_url = $downloadUrl }

    $downloads.generated_at = (Get-Date).ToString('yyyy-MM-dd')
    Save-JsonFile $downloadsPath $downloads
    Write-Host "[OK] Updated: $downloadsPath"
}

Write-Host ""
Write-Host "Next:" 
Write-Host "1) Upload $artifactName to GitHub Releases"
Write-Host "2) Rerun with -GitHubRepo owner/repo -GitHubTag vX.Y.Z -UpdateWebsiteJson"
