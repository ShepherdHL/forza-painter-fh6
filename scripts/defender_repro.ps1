#Requires -Version 5.1
<#
.SYNOPSIS
  Helper for phased Windows Defender false-positive isolation.

.PARAMETER Phase
  A = idle launch (manual)
  B = admin idle (manual)
  C-H = see docs/DEFENDER_REPRO.md

.EXAMPLE
  .\scripts\defender_repro.ps1 -Phase A
#>
param(
    [ValidateSet("A", "B", "C", "D", "E", "F", "G", "H", "All")]
    [string] $Phase = "A"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$AuditLog = Join-Path $Root "runtime\logs\defender-audit.log"

$env:FORZA_PAINTER_DEFENDER_AUDIT = "1"

function Show-DefenderEvents {
    $logName = "Microsoft-Windows-Windows Defender/Operational"
    if (-not (Get-WinEvent -ListLog $logName -ErrorAction SilentlyContinue)) {
        Write-Host "Defender operational log not available."
        return
    }
    Write-Host "`n--- Recent Defender events (1116/1117) ---"
    try {
        Get-WinEvent -LogName $logName -MaxEvents 30 |
            Where-Object { $_.Id -in 1116, 1117 } |
            Select-Object -First 8 |
            ForEach-Object {
                Write-Host ("[{0}] Id={1}" -f $_.TimeCreated, $_.Id)
                Write-Host $_.Message.Split("`n")[0]
            }
    } catch {
        Write-Host $_.Exception.Message
    }
}

function Show-AuditTail {
    if (-not (Test-Path $AuditLog)) {
        Write-Host "No audit log yet: $AuditLog"
        return
    }
    Write-Host "`n--- defender-audit.log (last 40 lines) ---"
    Get-Content -LiteralPath $AuditLog -Tail 40
}

$instructions = @{
    A = @(
        "Phase A: Standard-user cold start"
        "1. Do NOT run as Administrator."
        "2. Launch start_app.bat OR the release EXE."
        "3. Wait 30 seconds without Import/Generate."
        "4. Close the app."
    )
    B = @(
        "Phase B: Administrator cold start"
        "1. Right-click EXE -> Run as administrator (or elevated dev Python)."
        "2. Wait 30 seconds idle, then close."
    )
    C = @(
        "Phase C: GPU generator"
        "1. Generate JSON from an image (no game required)."
        "2. Watch for PROCESS_SPAWN of forza-painter-geometrize-go.exe."
    )
    D = @(
        "Phase D: Process enumeration"
        "1. Start FH6 in Vinyl Group Editor."
        "2. Open Import and refresh/select PID."
    )
    E = @(
        "Phase E: Elevation prompt only"
        "1. Standard user -> Import -> accept consent -> approve UAC."
        "2. Note ELEVATION + new STARTUP in audit log."
    )
    F = @(
        "Phase F: Auto-locate"
        "1. After elevated restart, run Auto-locate with game running."
    )
    G = @(
        "Phase G: Import"
        "1. Run full import with consent."
    )
    H = @(
        "Phase H: LibreHardwareMonitor"
        "1. Ensure LHM DLLs exist under bin\librehardwaremonitor."
        "2. Enable resource monitor / eco GPU cooldown."
    )
}

function Run-Phase([string] $Key) {
    Write-Host "`n========================================"
    Write-Host "DEFENDER REPRO — Phase $Key"
    Write-Host "========================================"
    $instructions[$Key] | ForEach-Object { Write-Host $_ }
    Write-Host "`nAudit logging: FORZA_PAINTER_DEFENDER_AUDIT=1"
    Write-Host "Log path: $AuditLog"
    Read-Host "`nPress Enter when you have finished this phase"
    Show-AuditTail
    Show-DefenderEvents
}

Write-Host "Project root: $Root"
if ($Phase -eq "All") {
    foreach ($key in @("A", "B", "C", "D", "E", "F", "G", "H")) {
        Run-Phase $key
    }
} else {
    Run-Phase $Phase
}

Write-Host "`nDone. Compare timestamps in defender-audit.log with Windows Security protection history."
