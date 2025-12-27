param(
    [Parameter(Mandatory = $false)]
    [string]$OdooMajor = "19",

    [Parameter(Mandatory = $false)]
    [string]$ReleaseDir = "D:\business\odoo\Setup odoo19\release",

    [Parameter(Mandatory = $false)]
    [string]$OutDir = "D:\business\odoo\Setup odoo19\dist",

    # وقتی فایل رو در GitHub Releases / S3 آپلود کردی، این base url رو بذار
    [Parameter(Mandatory = $false)]
    [string]$PublicBaseUrl = "",

    # GitHub Releases helper (optional)
    # Example:
    #   -GitHubRepo "youruser/odoomaster" -GitHubTag "v1.0.0"
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

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Read-Json([string]$Path) {
    Get-Content -Raw -Path $Path | ConvertFrom-Json
}

function Write-Json([object]$Obj) {
    $Obj | ConvertTo-Json -Depth 12
}

function Save-JsonFile([string]$Path, [object]$Obj) {
    $json = $Obj | ConvertTo-Json -Depth 20
    Set-Content -Path $Path -Value $json -Encoding UTF8
}

$releasePath = Resolve-Path $ReleaseDir
$buildInfoPath = Join-Path $releasePath "build_info.json"
if (-not (Test-Path $buildInfoPath)) {
    throw "build_info.json not found in release folder. Run BUILD_RELEASE.bat first."
}

$info = Read-Json $buildInfoPath
$version = $info.version
$buildType = $info.build_type

Ensure-Dir $OutDir

$artifactName = "OdooInstaller-odoo$OdooMajor-$version-$buildType.zip"
$artifactPath = Join-Path $OutDir $artifactName

Write-Host "[*] Packaging release -> $artifactPath"
if (Test-Path $artifactPath) { Remove-Item $artifactPath -Force }
Compress-Archive -Path (Join-Path $releasePath "*") -DestinationPath $artifactPath -Force

$hash = (Get-FileHash -Algorithm SHA256 -Path $artifactPath).Hash.ToLowerInvariant()
$sizeBytes = (Get-Item $artifactPath).Length

$OdooMajorInt = [int]$OdooMajor

if (-not $PublicBaseUrl -and $GitHubRepo -and $GitHubTag) {
    $PublicBaseUrl = "https://github.com/$GitHubRepo/releases/download/$GitHubTag"
}

$downloadUrl = if ($PublicBaseUrl) { "$PublicBaseUrl/$artifactName" } else { "" }

$snippet = [ordered]@{
    id = "odoo$OdooMajor-full-offline"
    title = "Full offline package"
    version = $version
    file_type = "zip"
    size_hint = "${sizeBytes} bytes"
    requires_login = $true
    download_url = $downloadUrl
    sha256 = $hash
}

Write-Host ""
Write-Host "[OK] SHA256: $hash"
Write-Host "[OK] Size:   $sizeBytes bytes"

if ($downloadUrl) {
    Write-Host "[OK] URL:    $downloadUrl"
}

if ($UpdateWebsiteJson) {
    $downloadsPath = Join-Path (Resolve-Path $WebsiteDir) "downloads.json"
    if (-not (Test-Path $downloadsPath)) {
        throw "downloads.json not found at: $downloadsPath"
    }

    $downloads = Read-Json $downloadsPath
    if (-not $downloads.versions) {
        throw "downloads.json is missing 'versions'"
    }

    $targetVersion = $downloads.versions | Where-Object { $_.odoo_major -eq $OdooMajorInt } | Select-Object -First 1
    if (-not $targetVersion) {
        throw "downloads.json has no entry for odoo_major=$OdooMajorInt"
    }

    if (-not $targetVersion.items) {
        $targetVersion | Add-Member -NotePropertyName items -NotePropertyValue @() -Force
    }

    $targetId = "odoo$OdooMajor-full-offline"
    $existing = $targetVersion.items | Where-Object { $_.id -eq $targetId } | Select-Object -First 1

    if (-not $existing) {
        $existing = [pscustomobject]@{
            id = $targetId
            title = "Full offline package"
            description = "Complete Release bundle: offline.7z + soft.7z + local installer UI. Suitable for offline installs."
            featured = $true
            version = $version
            file_type = "zip"
            size_hint = "${sizeBytes} bytes"
            requires_login = $true
            download_url = $downloadUrl
            sha256 = $hash
            features = @(
                "Python + PostgreSQL + Git + NodeJS + wheels (offline)",
                "Local installer UI (web)",
                "Auto-extract offline.7z and soft.7z",
                "Fast offline installation"
            )
        }

        $targetVersion.items = @($existing) + @($targetVersion.items)
    }

    $existing.version = $version
    $existing.sha256 = $hash
    $existing.size_hint = "${sizeBytes} bytes"
    $existing.download_url = $downloadUrl

    $downloads.generated_at = (Get-Date).ToString('yyyy-MM-dd')
    Save-JsonFile $downloadsPath $downloads

    Write-Host ""
    Write-Host "[OK] Updated: $downloadsPath"
}
Write-Host ""
Write-Host "Paste this into website/downloads.json (odoo_major=$OdooMajor -> items[0] etc):"
Write-Host ""
Write-Host (Write-Json $snippet)
Write-Host ""
Write-Host "Tip: Upload $artifactName to GitHub Releases (or any file host)."
Write-Host "- If using GitHub Releases, rerun with: -GitHubRepo 'owner/repo' -GitHubTag 'vX.Y.Z' -UpdateWebsiteJson"
