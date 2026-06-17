param(
    [string]$Target = "external/MediaCrawler",
    [string]$Repo = "https://github.com/NanmiCoder/MediaCrawler",
    [string]$ZipFallbackUrl = "https://codeload.github.com/NanmiCoder/MediaCrawler/zip/refs/heads/main"
)

$ErrorActionPreference = "Stop"

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

function Remove-EmptyDirectoryIfPresent {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $children = @(Get-ChildItem -LiteralPath $Path -Force)
    if ($children.Count -gt 0) {
        throw "Target exists and is not empty: $Path"
    }

    Remove-Item -LiteralPath $Path -Force
}

function Install-FromZipFallback {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    Remove-EmptyDirectoryIfPresent -Path $TargetPath

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mediacrawler-" + [guid]::NewGuid().ToString("N"))
    $tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    $tempRootFull = [System.IO.Path]::GetFullPath($tempRoot)
    if (-not $tempRootFull.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to use unexpected temp path: $tempRootFull"
    }

    $zipPath = Join-Path $tempRoot "source.zip"
    $extractPath = Join-Path $tempRoot "extract"

    New-Item -ItemType Directory -Force -Path $tempRoot, $extractPath | Out-Null
    try {
        Write-Host "Downloading MediaCrawler source archive from $Url"
        Invoke-WebRequest -Uri $Url -OutFile $zipPath -UseBasicParsing
        Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force

        $sourceRoot = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
        if (-not $sourceRoot) {
            throw "Downloaded archive did not contain a source directory."
        }

        New-Item -ItemType Directory -Force -Path $TargetPath | Out-Null
        Get-ChildItem -LiteralPath $sourceRoot.FullName -Force |
            Copy-Item -Destination $TargetPath -Recurse -Force
    } finally {
        if (Test-Path -LiteralPath $tempRootFull) {
            Remove-Item -LiteralPath $tempRootFull -Recurse -Force
        }
    }
}

$root = Resolve-Path -LiteralPath "."
$targetPath = Join-Path $root $Target
$parent = Split-Path -Parent $targetPath

if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
}

if (-not (Test-Path -LiteralPath $targetPath)) {
    try {
        Invoke-Native git clone --depth 1 $Repo $targetPath
    } catch {
        Write-Warning "git clone failed: $($_.Exception.Message)"
        Install-FromZipFallback -Url $ZipFallbackUrl -TargetPath $targetPath
    }
} else {
    Write-Host "MediaCrawler already exists at $targetPath"
}

Push-Location $targetPath
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv is required. Install it from https://docs.astral.sh/uv/ and rerun this script."
    }
    Invoke-Native uv sync
    Invoke-Native uv run playwright install
} finally {
    Pop-Location
}

Write-Host "MediaCrawler is ready at $targetPath"
