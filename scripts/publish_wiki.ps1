# Sync root documentation to the GitHub Wiki (Home, FAQ, Acknowledgements, Changelog).
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

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
$WorkDir = Join-Path $env:TEMP "forza-painter-fh6-wiki-publish"
if (Test-Path $WorkDir) {
    Remove-Item -LiteralPath $WorkDir -Recurse -Force
}

Write-Host "Cloning wiki from $WikiUrl ..."
git clone $WikiUrl $WorkDir 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw @"
Wiki clone failed. Enable Wikis on the repository (Settings -> Features -> Wikis),
then run this script again. First-time setup may require creating one page on github.com manually.
"@
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
    git add -A
    $status = git status --porcelain
    if (-not $status) {
        Write-Host "Wiki already up to date."
        exit 0
    }
    git commit -m "Sync docs from main ($(Get-Date -Format 'yyyy-MM-dd'))"
    git push origin HEAD
    Write-Host "Wiki published. Open: https://github.com/ShepherdHL/forza-painter-fh6/wiki"
}
finally {
    Pop-Location
}
