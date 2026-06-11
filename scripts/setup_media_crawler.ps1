param(
    [string]$Target = "external/MediaCrawler",
    [string]$Repo = "https://github.com/NanmiCoder/MediaCrawler"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath "."
$targetPath = Join-Path $root $Target
$parent = Split-Path -Parent $targetPath

if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
}

if (-not (Test-Path -LiteralPath $targetPath)) {
    git clone --depth 1 $Repo $targetPath
} else {
    Write-Host "MediaCrawler already exists at $targetPath"
}

Push-Location $targetPath
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv is required. Install it from https://docs.astral.sh/uv/ and rerun this script."
    }
    uv sync
    uv run playwright install
} finally {
    Pop-Location
}

Write-Host "MediaCrawler is ready at $targetPath"

