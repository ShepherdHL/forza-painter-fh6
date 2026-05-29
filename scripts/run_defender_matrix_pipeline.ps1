#Requires -Version 5.1
<#
.SYNOPSIS
  Full Defender comparative matrix: build → analyze → smoke → Defender scan → report.

.PARAMETER SkipBuild
  Use existing dist/defender-matrix builds.

.PARAMETER SkipDefender
  Skip MpCmdRun (e.g. no admin / third-party AV only).

.PARAMETER VariantId
  Single variant through the pipeline.

.EXAMPLE
  .\scripts\run_defender_matrix_pipeline.ps1
  .\scripts\run_defender_matrix_pipeline.ps1 -SkipBuild -VariantId onedir
#>
param(
    [switch] $SkipBuild,
    [switch] $SkipDefender,
    [string] $VariantId = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$MatrixRoot = Join-Path $Root "dist\defender-matrix"

Write-Host "=== Forza Painter Defender Matrix Pipeline ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not $SkipBuild) {
    $buildArgs = @("-File", (Join-Path $Root "scripts\build_defender_matrix.ps1"))
    if ($VariantId) { $buildArgs += @("-VariantId", $VariantId) }
    & powershell @buildArgs
}

& $Python (Join-Path $Root "scripts\defender_matrix\analyze_builds.py")

$smokeArgs = @("-File", (Join-Path $Root "scripts\defender_matrix\run_smoke_tests.ps1"), "-MatrixRoot", $MatrixRoot)
& powershell @smokeArgs

if (-not $SkipDefender) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
    if (-not $isAdmin) {
        Write-Warning "Defender scans work best as Administrator. Re-run elevated or use -SkipDefender."
    }
    $scanArgs = @("-File", (Join-Path $Root "scripts\defender_matrix\run_defender_scans.ps1"), "-MatrixRoot", $MatrixRoot)
    & powershell @scanArgs
} else {
    Write-Host "Skipping Defender scans (-SkipDefender)." -ForegroundColor Yellow
}

& $Python (Join-Path $Root "scripts\defender_matrix\generate_report.py")

Write-Host "`nDone. Open: $MatrixRoot\MATRIX_REPORT.md" -ForegroundColor Green
Write-Host "Artifacts:"
Write-Host "  build_manifest.json"
Write-Host "  analysis_results.json"
Write-Host "  smoke_results.json"
Write-Host "  defender_scan_results.json (if scanned)"
