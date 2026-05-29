# Build one-file EXE, compute SHA-256, and write release notes snippet for GitHub.
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$DistRoot = Join-Path $Root "dist"

& (Join-Path $ScriptDir "make_exe_release.ps1")

$VersionFile = Join-Path $Root "src\version.py"
$VersionMatch = Select-String -Path $VersionFile -Pattern '^__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
$Version = $VersionMatch.Matches[0].Groups[1].Value
$ExePath = Join-Path $DistRoot "forza-painter-fh6-v$Version.exe"

if (!(Test-Path $ExePath)) {
    throw "Expected EXE not found: $ExePath"
}

$Hash = (Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
$SnippetPath = Join-Path $DistRoot "RELEASE_SNIPPET-v$Version.md"

$Snippet = @"
## forza-painter-fh6 v$Version

### Downloads
- ``forza-painter-fh6-v$Version.exe`` (one-file Windows build)

### Integrity
- SHA-256: ``$Hash``

### Signing
- [ ] Authenticode-signed (recommended before wide distribution)

### Smoke test
- [ ] Launch without admin; Generate tab works
- [ ] Import shows consent + UAC when needed
- [ ] Helper line appears in log during import

### Optional
- VirusTotal scan link: _paste here_
"@

Set-Content -LiteralPath $SnippetPath -Value $Snippet -Encoding UTF8
Write-Host ""
Write-Host "EXE: $ExePath"
Write-Host "SHA-256: $Hash"
Write-Host "Snippet: $SnippetPath"
Write-Host ""
Write-Host "Upload the EXE to GitHub Releases and paste the snippet into release notes."
