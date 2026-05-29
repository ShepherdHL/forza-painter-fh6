#Requires -Version 5.1
<#
.SYNOPSIS
  Build all Defender matrix variants defined in scripts/build_matrix/variants.json.

.PARAMETER VariantId
  Build a single variant (default: all).

.PARAMETER SkipFetch
  Skip LibreHardwareMonitor download step.

.EXAMPLE
  .\scripts\build_defender_matrix.ps1
  .\scripts\build_defender_matrix.ps1 -VariantId onefile-noupx-explicit
#>
param(
    [string] $VariantId = "",
    [switch] $SkipFetch
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$VariantsFile = Join-Path $Root "scripts\build_matrix\variants.json"
$SpecFile = Join-Path $Root "scripts\forza_painter.spec"
$MatrixRoot = Join-Path $Root "dist\defender-matrix"
$Catalog = Get-Content -LiteralPath $VariantsFile -Raw | ConvertFrom-Json

if (-not (Test-Path $Python)) {
    throw "Missing .venv Python. Run install_dependencies.bat first."
}

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$pyiInstalled = cmd /c "`"$Python`" -m pip show pyinstaller 2>nul"
$ErrorActionPreference = $prevEap
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install pyinstaller
}
& $Python -m pip install -r (Join-Path $Root "requirements.txt") -q

$toBuild = @($Catalog.variants)
if ($VariantId) {
    $toBuild = @($Catalog.variants | Where-Object { $_.id -eq $VariantId })
    if (-not $toBuild) {
        throw "Unknown variant: $VariantId"
    }
}

$manifest = @{
    schema     = $Catalog.schema
    built_at   = (Get-Date).ToUniversalTime().ToString("o")
    variants   = @()
}
$manifestPath = Join-Path $MatrixRoot "build_manifest.json"

foreach ($variant in $toBuild) {
    $id = $variant.id
    Write-Host "`n========== Building $id ==========" -ForegroundColor Cyan

    $variantDir = Join-Path $MatrixRoot $id
    $workDir = Join-Path $Root "build\matrix\$id"
    $profilePath = Join-Path $variantDir "build_profile.json"

    if (Test-Path $variantDir) {
        Remove-Item -LiteralPath $variantDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $variantDir -Force | Out-Null
    if (Test-Path $workDir) {
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null

    # Full variant config for spec (includes PyInstaller knobs not stored in runtime profile).
    $variant | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $profilePath -Encoding UTF8

    $env:MATRIX_VARIANT_FILE = $profilePath
    & $Python (Join-Path $Root "scripts\build_matrix\generate_profile.py") `
        --variants $VariantsFile `
        --variant-id $id `
        --out $profilePath `
        --src-root (Join-Path $Root "src")

    # UPX / strip / onefile are controlled in forza_painter.spec via MATRIX_VARIANT_FILE.
    # PyInstaller disallows --noupx when a .spec file is supplied.
    $pyiArgs = @(
        "--noconfirm",
        "--clean",
        "--distpath", $variantDir,
        "--workpath", $workDir,
        $SpecFile
    )

    if ($variant.block_upx_path) {
        $savedPath = $env:PATH
        $env:PATH = ($env:PATH -split ';' | Where-Object { $_ -notmatch 'upx' -and $_ -notmatch 'UPX' }) -join ';'
    }

    & $Python -m PyInstaller @pyiArgs
    if ($variant.block_upx_path) {
        $env:PATH = $savedPath
    }

    $exePath = Join-Path $variantDir "forza-painter-fh6.exe"
    if (-not (Test-Path $exePath)) {
        $exePath = Join-Path $variantDir "forza-painter-fh6\forza-painter-fh6.exe"
    }
    if (-not (Test-Path $exePath)) {
        throw "Build failed: EXE not found for $id in $variantDir"
    }

    Copy-Item -LiteralPath $profilePath -Destination (Join-Path $variantDir "_build_profile.json") -Force

    $entry = @{
        id       = $id
        label    = $variant.label
        exe_path = $exePath
        built_at = (Get-Date).ToUniversalTime().ToString("o")
    }
    $manifest.variants += $entry
    Write-Host "Built: $exePath"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 6), $utf8NoBom)
Write-Host "`nManifest: $manifestPath" -ForegroundColor Green
