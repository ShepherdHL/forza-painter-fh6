$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$TargetDir = Join-Path $Root "bin\librehardwaremonitor"
$Version = "0.9.4"
$ZipName = "LibreHardwareMonitor-net472.zip"
$DownloadUrl = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v$Version/$ZipName"
$TempZip = Join-Path $env:TEMP "LibreHardwareMonitor-net472.zip"
$TempExtract = Join-Path $env:TEMP "LibreHardwareMonitor-extract"

$LhmDll = Join-Path $TargetDir "LibreHardwareMonitorLib.dll"
$HidDll = Join-Path $TargetDir "HidSharp.dll"
if ((Test-Path $LhmDll) -and (Test-Path $HidDll)) {
    Write-Host "LibreHardwareMonitor DLLs already present in $TargetDir"
    exit 0
}

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
if (Test-Path $TempExtract) {
    Remove-Item -LiteralPath $TempExtract -Recurse -Force
}
New-Item -ItemType Directory -Path $TempExtract -Force | Out-Null

Write-Host "Downloading LibreHardwareMonitor v$Version..."
Invoke-WebRequest -Uri $DownloadUrl -OutFile $TempZip
Expand-Archive -LiteralPath $TempZip -DestinationPath $TempExtract -Force

$SourceLhm = Get-ChildItem -Path $TempExtract -Recurse -Filter "LibreHardwareMonitorLib.dll" | Select-Object -First 1
$SourceHid = Get-ChildItem -Path $TempExtract -Recurse -Filter "HidSharp.dll" | Select-Object -First 1
if (-not $SourceLhm -or -not $SourceHid) {
    throw "Could not find LibreHardwareMonitor DLLs in downloaded archive."
}

Copy-Item -LiteralPath $SourceLhm.FullName -Destination $LhmDll -Force
Copy-Item -LiteralPath $SourceHid.FullName -Destination $HidDll -Force

Remove-Item -LiteralPath $TempZip -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $TempExtract -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "LibreHardwareMonitor DLLs installed to $TargetDir"
