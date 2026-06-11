param(
    [Parameter(Mandatory=$true)]
    [string]$Query,

    [string]$ProjectRoot = "",
    [string]$CollectionMode = "auto",
    [string]$Platforms = "xhs,zhihu,bilibili,weibo,tieba",
    [int]$Limit = 5,
    [string]$Format = "markdown"
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path -LiteralPath ".").Path
}

$scriptPath = Join-Path $ProjectRoot "scripts\run_travel_research.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Travel agent script not found: $scriptPath. Run this skill from the repository root or pass -ProjectRoot."
}

python $scriptPath $Query --collection-mode $CollectionMode --platforms $Platforms --limit $Limit --format $Format

