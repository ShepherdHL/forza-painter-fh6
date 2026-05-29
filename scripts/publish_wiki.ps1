# Sync root documentation to the GitHub Wiki (Home, FAQ, Acknowledgements, Changelog).
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

function Invoke-Git {
    param([string[]]$GitCommand)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git @GitCommand 2>&1
        $code = $LASTEXITCODE
        if ($output) {
            $output | ForEach-Object { Write-Host $_ }
        }
        return $code
    }
    finally {
        $ErrorActionPreference = $previous
    }
}

function Get-RemoteWikiUrl {
    $remote = (git -C $Root remote get-url origin 2>$null)
    if (-not $remote) {
        throw "No git remote 'origin' found."
    }
    if ($remote -match "^git@github\.com:(.+?)(?:\.git)?$") {
        return "git@github.com:$($Matches[1]).wiki.git"
    }
    if ($remote -match "^https://github\.com/(.+?)(?:\.git)?/?$") {
        return "https://github.com/$($Matches[1]).wiki.git"
    }
    throw "Unsupported origin remote: $remote"
}

function Get-WikiWebUrl {
    param([string]$WikiGitUrl)
    if ($WikiGitUrl -match "github\.com[:/](.+?)\.wiki\.git") {
        return "https://github.com/$($Matches[1])/wiki"
    }
    return $WikiGitUrl
}

function Convert-ToWikiLinks {
    param([string]$Text)
    $Text = $Text -replace '\]\(README\.md\)', '](Home)'
    $Text = $Text -replace '\]\(FAQ\.md\)', '](FAQ)'
    $Text = $Text -replace '\]\(ACKNOWLEDGEMENTS\.md\)', '](Acknowledgements)'
    $Text = $Text -replace '\]\(CHANGELOG\.md\)', '](Changelog)'
    $Text = $Text -replace '\]\(LICENSE\)', '](https://github.com/ShepherdHL/forza-painter-fh6/blob/main/LICENSE)'
    $Text = $Text -replace '<a href="README\.md"><strong>README</strong></a>', '<a href="Home"><strong>Home</strong></a>'
    $Text = $Text -replace '<a href="README\.md">README</a>', '<a href="Home">Home</a>'
    $Text = $Text -replace '<a href="FAQ\.md"><strong>FAQ</strong></a>', '<a href="FAQ"><strong>FAQ</strong></a>'
    $Text = $Text -replace '<a href="FAQ\.md">FAQ</a>', '<a href="FAQ">FAQ</a>'
    $Text = $Text -replace '<a href="ACKNOWLEDGEMENTS\.md"><strong>Acknowledgements</strong></a>', '<a href="Acknowledgements"><strong>Acknowledgements</strong></a>'
    $Text = $Text -replace '<a href="ACKNOWLEDGEMENTS\.md">Acknowledgements</a>', '<a href="Acknowledgements">Acknowledgements</a>'
    $Text = $Text -replace '<a href="CHANGELOG\.md"><strong>Changelog</strong></a>', '<a href="Changelog"><strong>Changelog</strong></a>'
    $Text = $Text -replace '<a href="CHANGELOG\.md">Changelog</a>', '<a href="Changelog">Changelog</a>'
    return $Text
}

function Read-RootDoc {
    param([string]$RelativePath)
    $path = Join-Path $Root $RelativePath
    if (-not (Test-Path $path)) {
        throw "Missing source doc: $RelativePath"
    }
    return Convert-ToWikiLinks (Get-Content -LiteralPath $path -Raw -Encoding UTF8)
}

$WikiUrl = Get-RemoteWikiUrl
$WikiWebUrl = Get-WikiWebUrl $WikiUrl
$WorkDir = Join-Path $env:TEMP "forza-painter-fh6-wiki-publish"
if (Test-Path $WorkDir) {
    Remove-Item -LiteralPath $WorkDir -Recurse -Force
}

Write-Host "Checking wiki remote: $WikiUrl"
$probeCode = Invoke-Git -GitCommand @("ls-remote", $WikiUrl)
if ($probeCode -ne 0) {
    Write-Host ""
    Write-Host "Wiki git repo is not available yet." -ForegroundColor Yellow
    Write-Host "Enabling Wikis is not enough - GitHub creates the wiki repo after the first page exists."
    Write-Host ""
    Write-Host "One-time setup (about 30 seconds):"
    Write-Host "  1. Open $WikiWebUrl"
    Write-Host "  2. Click Create the first page"
    Write-Host "  3. Title: Home   Body: placeholder   Save Page"
    Write-Host "  4. Run this script again from the repo root:"
    Write-Host ('     powershell -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"')
    exit 1
}

Write-Host "Cloning wiki from $WikiUrl ..."
$cloneCode = Invoke-Git -GitCommand @("clone", $WikiUrl, $WorkDir)
if ($cloneCode -ne 0) {
    throw "Wiki clone failed even though the remote exists. Check git credentials and try again."
}

$pages = @{
    "Home.md"             = Read-RootDoc "README.md"
    "FAQ.md"              = Read-RootDoc "FAQ.md"
    "Acknowledgements.md" = Read-RootDoc "ACKNOWLEDGEMENTS.md"
    "Changelog.md"        = Read-RootDoc "CHANGELOG.md"
}

foreach ($entry in $pages.GetEnumerator()) {
    $dest = Join-Path $WorkDir $entry.Key
    Set-Content -LiteralPath $dest -Value $entry.Value -Encoding UTF8 -NoNewline
    Write-Host "Wrote wiki/$($entry.Key)"
}

Push-Location $WorkDir
try {
    Invoke-Git -GitCommand @("add", "-A") | Out-Null
    $status = git status --porcelain
    if (-not $status) {
        Write-Host "Wiki already up to date."
        exit 0
    }
    Invoke-Git -GitCommand @("commit", "-m", "Sync docs from main ($(Get-Date -Format 'yyyy-MM-dd'))") | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Wiki commit failed."
    }
    $pushCode = Invoke-Git -GitCommand @("push", "origin", "HEAD")
    if ($pushCode -ne 0) {
        throw "Wiki push failed."
    }
    Write-Host ""
    Write-Host "Wiki published. Open: $WikiWebUrl" -ForegroundColor Green
}
finally {
    Pop-Location
}
