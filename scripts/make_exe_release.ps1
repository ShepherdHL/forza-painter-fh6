$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$DistRoot = Join-Path $Root "dist"
$BuildRoot = Join-Path $Root "build\pyinstaller-release"
$SpecFile = Join-Path $Root "scripts\forza_painter.spec"
$VersionFile = Join-Path $Root "src\version.py"
$VersionMatch = Select-String -Path $VersionFile -Pattern '^__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $VersionMatch) {
    throw "Cannot read version from src\version.py"
}

$Version = $VersionMatch.Matches[0].Groups[1].Value
$PackageName = "forza-painter-fh6-v$Version-onefile"
$PackageDir = Join-Path $DistRoot $PackageName
$ZipPath = Join-Path $DistRoot "$PackageName.zip"
$VersionedExePath = Join-Path $DistRoot "forza-painter-fh6-v$Version.exe"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Missing .venv Python. Run start_app.bat or install_dependencies.bat first."
}

& $Python -m pip show pyinstaller 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install pyinstaller
}

& $Python -m pip install -r (Join-Path $Root "requirements.txt")

# Release profile: onefile, explicit no-UPX, bundled assets (no LHM / pythonnet)
$releaseProfile = @{
    variant_id            = "release"
    label                 = "Production release"
    onefile               = $true
    disable_elevation     = $false
    disable_generator     = $false
    disable_networking    = $false
    disable_memory_scan   = $false
} | ConvertTo-Json
$profilePath = Join-Path $BuildRoot "release_profile.json"
New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
Set-Content -LiteralPath $profilePath -Value $releaseProfile -Encoding UTF8
$srcProfile = Join-Path $Root "src\_build_profile.json"
Set-Content -LiteralPath $srcProfile -Value $releaseProfile -Encoding UTF8

$env:MATRIX_VARIANT_FILE = $profilePath
if (Test-Path $BuildRoot) {
    Remove-Item -LiteralPath (Join-Path $BuildRoot "forza-painter-fh6.exe") -Force -ErrorAction SilentlyContinue
}

& $Python -m PyInstaller --noconfirm --clean `
    --distpath $BuildRoot `
    --workpath (Join-Path $BuildRoot "work") `
    $SpecFile

$builtExe = Join-Path $BuildRoot "forza-painter-fh6.exe"
if (-not (Test-Path $builtExe)) {
    throw "PyInstaller did not produce $builtExe"
}

if (Test-Path $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null

Copy-Item -LiteralPath $builtExe -Destination $PackageDir
Copy-Item -LiteralPath $builtExe -Destination $VersionedExePath
Copy-Item -LiteralPath $srcProfile -Destination (Join-Path $PackageDir "_build_profile.json") -Force

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath
Write-Host "One-file EXE written to $VersionedExePath"
Write-Host "One-file EXE package written to $ZipPath"
Write-Host "Built with scripts/forza_painter.spec (no UPX, minimal hooks)"
