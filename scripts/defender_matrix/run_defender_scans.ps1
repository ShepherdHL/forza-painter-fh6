#Requires -Version 5.1
<#
.SYNOPSIS
  Custom-scan each matrix EXE with Windows Defender MpCmdRun and record results.

.NOTES
  Requires Administrator for reliable MpCmdRun -ScanType 3.
  Does NOT submit to Microsoft — local scan only.
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

$mp = Join-Path ${env:ProgramFiles} "Windows Defender\MpCmdRun.exe"
if (-not (Test-Path $mp)) {
    throw "MpCmdRun.exe not found. Windows Defender required."
}

$manifestPath = Join-Path $MatrixRoot "build_manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

try {
    $sig = (Get-MpComputerStatus).AntivirusSignatureVersion
} catch {
    $sig = "unknown"
}

$scanResults = @{
    scanned_at        = (Get-Date).ToUniversalTime().ToString("o")
    signature_version = $sig
    variants          = @()
}

foreach ($entry in $manifest.variants) {
    $id = $entry.id
    $exe = $entry.exe_path
    if (-not (Test-Path $exe)) {
        $exe = Join-Path $MatrixRoot "$id\forza-painter-fh6.exe"
    }
    Write-Host "`nDefender scan: $id" -ForegroundColor Yellow
    Write-Host "  Path: $exe"

    $logPath = Join-Path $MatrixRoot "$id\defender_scan.log"
    $args = "-Scan -ScanType 3 -File `"$exe`" -DisableRemediation"
    $proc = Start-Process -FilePath $mp -ArgumentList $args -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $logPath -RedirectStandardError (Join-Path $MatrixRoot "$id\defender_scan_err.log")

    $threats = @()
    try {
        $events = Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational" -MaxEvents 40 -ErrorAction SilentlyContinue |
            Where-Object { $_.Id -in 1116, 1117 -and $_.TimeCreated -gt (Get-Date).AddMinutes(-5) }
        foreach ($ev in $events) {
            if ($ev.Message -match [regex]::Escape($exe)) {
                $threats += @{
                    time    = $ev.TimeCreated.ToString("o")
                    id      = $ev.Id
                    message = ($ev.Message -split "`n")[0]
                }
            }
        }
    } catch {
        $threats = @(@{ error = $_.Exception.Message })
    }

    $detected = ($proc.ExitCode -eq 2) -or ($threats.Count -gt 0)
    $record = @{
        id           = $id
        exit_code    = $proc.ExitCode
        detected     = $detected
        threats      = $threats
        scan_log     = $(if (Test-Path $logPath) { Get-Content $logPath -Tail 20 } else { @() })
    }
    $scanResults.variants += $record
    if ($detected) {
        Write-Host "  DETECTED (exit $($proc.ExitCode))" -ForegroundColor Red
    } else {
        Write-Host "  Clean (exit $($proc.ExitCode))" -ForegroundColor Green
    }
}

$outPath = Join-Path $MatrixRoot "defender_scan_results.json"
$scanResults | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "`nWrote $outPath"
