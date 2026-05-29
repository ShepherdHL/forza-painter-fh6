#Requires -Version 5.1
<#
.SYNOPSIS
  Run --matrix-smoke on each built variant and capture startup evidence.
#>
param(
    [string] $MatrixRoot = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent (Split-Path -Parent $ScriptDir)
if (-not $MatrixRoot) {
    $MatrixRoot = Join-Path $Root "dist\defender-matrix"
}

$manifestPath = Join-Path $MatrixRoot "build_manifest.json"
if (-not (Test-Path $manifestPath)) {
    throw "Missing $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$smokeResults = @{
    ran_at   = (Get-Date).ToUniversalTime().ToString("o")
    variants = @()
}

foreach ($entry in $manifest.variants) {
    $id = $entry.id
    $exe = $entry.exe_path
    if (-not (Test-Path $exe)) {
        $exe = Join-Path $MatrixRoot "$id\forza-painter-fh6.exe"
    }
    if (-not (Test-Path $exe)) {
        $exe = Join-Path $MatrixRoot "$id\forza-painter-fh6\forza-painter-fh6.exe"
    }
    Write-Host "Smoke: $id -> $exe"

    $variantDir = Split-Path -Parent $exe
    $runtimeDir = Join-Path $variantDir "runtime"
    if (Test-Path $runtimeDir) {
        Remove-Item -LiteralPath $runtimeDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    $env:FORZA_PAINTER_DEFENDER_AUDIT = "1"
    $proc = Start-Process -FilePath $exe -ArgumentList "--matrix-smoke" -PassThru -Wait -WindowStyle Hidden
    Start-Sleep -Seconds 1

    $smokePath = Join-Path $variantDir "runtime\logs\matrix-smoke.json"
    $auditPath = Join-Path $variantDir "runtime\logs\defender-audit.log"
    $auditTail = @()
    if (Test-Path $auditPath) {
        $auditTail = @(Get-Content -LiteralPath $auditPath -Tail 15 -ErrorAction SilentlyContinue | ForEach-Object {
            [string]$_
        })
    }
    $meipass = @(Get-ChildItem -Path $env:TEMP -Filter "_MEI*" -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object { $_.FullName })

    $record = @{
        id              = $id
        exit_code       = $proc.ExitCode
        smoke_json      = $(if (Test-Path $smokePath) { Get-Content $smokePath -Raw } else { $null })
        audit_log_tail  = $auditTail
        temp_meipass    = $meipass
    }
    $smokeResults.variants += $record
}

$outPath = Join-Path $MatrixRoot "smoke_results.json"
$smokeResults | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "Wrote $outPath"
