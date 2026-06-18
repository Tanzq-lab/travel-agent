param(
    [string]$Target = "external/MediaCrawler",
    [string[]]$Platforms = @("xhs", "zhihu", "bilibili", "weibo", "tieba"),
    [string]$LoginType = "qrcode",
    [string]$Keyword = "",
    [int]$Limit = 1,
    [int]$TimeoutSeconds = 300,
    [int]$CdpPort = 9222,
    [string]$InitStatePath = "data/media_crawler_init/status.json",
    [string]$InitRunsPath = "data/media_crawler_init/runs",
    [switch]$StartCdpBrowser,
    [switch]$NoCdpBrowser
)

$ErrorActionPreference = "Stop"

function Convert-PlatformAlias {
    param([Parameter(Mandatory = $true)][string]$Platform)

    switch ($Platform.ToLowerInvariant()) {
        "bilibili" { "bili"; break }
        "weibo" { "wb"; break }
        default { $Platform.ToLowerInvariant(); break }
    }
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait(1000)) {
            return $false
        }
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Get-BrowserPath {
    $candidates = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Chrome or Edge was not found. Install one, or start a browser manually with --remote-debugging-port=$CdpPort."
}

function Start-CdpBrowser {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$ProfilePath
    )

    if (Test-TcpPort -HostName "127.0.0.1" -Port $Port) {
        Write-Host "CDP browser is already available on port $Port."
        return
    }

    $browserPath = Get-BrowserPath
    New-Item -ItemType Directory -Force -Path $ProfilePath | Out-Null
    Write-Host "Starting browser for MediaCrawler login on CDP port $Port."
    Write-Host "Use the visible browser window to complete QR-code or web login when a platform asks for it."

    Start-Process -FilePath $browserPath -ArgumentList @(
        "--remote-debugging-port=$Port",
        "--user-data-dir=$ProfilePath",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank"
    ) | Out-Null

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-TcpPort -HostName "127.0.0.1" -Port $Port) {
            return
        }
        Start-Sleep -Seconds 1
    }

    throw "Browser was started but CDP port $Port did not become available."
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

function ConvertTo-CommandLineArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    $escaped = $Value -replace '"', '\"'
    return '"' + $escaped + '"'
}

function Get-JsonlRecordCount {
    param([Parameter(Mandatory = $true)][string]$Path)

    $docs = 0
    Get-ChildItem -LiteralPath $Path -Recurse -Filter *.jsonl -ErrorAction SilentlyContinue |
        ForEach-Object {
            $docs += @(Get-Content -LiteralPath $_.FullName -Encoding UTF8 -ErrorAction SilentlyContinue).Count
        }
    return $docs
}

function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    taskkill /PID $ProcessId /T /F | Out-Null
}

function Invoke-MediaCrawlerInitCheck {
    param(
        [Parameter(Mandatory = $true)][string]$MediaRoot,
        [Parameter(Mandatory = $true)][string]$Platform,
        [Parameter(Mandatory = $true)][string]$RunPath
    )

    New-Item -ItemType Directory -Force -Path $RunPath | Out-Null
    $arguments = @(
        "run",
        "main.py",
        "--platform", $Platform,
        "--lt", $LoginType,
        "--type", "search",
        "--keywords", $Keyword,
        "--crawler_max_notes_count", [string]$Limit,
        "--save_data_option", "jsonl",
        "--save_data_path", $RunPath,
        "--get_comment", "false",
        "--get_sub_comment", "false",
        "--headless", "false"
    )

    Write-Host "Initializing MediaCrawler platform '$Platform'. Complete login in the browser if prompted."

    $stdoutPath = Join-Path $RunPath "stdout.log"
    $stderrPath = Join-Path $RunPath "stderr.log"
    $argumentLine = ($arguments | ForEach-Object { ConvertTo-CommandLineArgument -Value $_ }) -join " "
    $process = Start-Process -FilePath "uv" -ArgumentList $argumentLine -WorkingDirectory $MediaRoot -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-ProcessTree -ProcessId $process.Id
        $docs = Get-JsonlRecordCount -Path $RunPath
        return @{
            platform = $Platform
            ok = ($docs -gt 0)
            docs = $docs
            error = if ($docs -gt 0) { $null } else { "MediaCrawler initialization timed out after $TimeoutSeconds seconds." }
        }
    }

    $process.Refresh()
    $docs = Get-JsonlRecordCount -Path $RunPath

    $stderr = ""
    if (Test-Path -LiteralPath $stderrPath) {
        $stderr = (Get-Content -LiteralPath $stderrPath -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -First 20) -join " "
    }

    return @{
        platform = $Platform
        ok = ($docs -gt 0)
        docs = $docs
        exit_code = $process.ExitCode
        error = if ($docs -gt 0) { $null } elseif ($stderr) { $stderr } else { "MediaCrawler completed but produced no jsonl records." }
    }
}

$root = Resolve-Path -LiteralPath "."
$mediaRoot = Join-Path $root $Target

if (-not $Keyword) {
    $Keyword = -join @([char]0x5317, [char]0x4EAC, [char]0x65C5, [char]0x6E38)
}

& (Join-Path $root "scripts\setup_media_crawler.ps1") -Target $Target

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/ and rerun this script."
}

if (-not (Test-Path -LiteralPath $mediaRoot)) {
    throw "MediaCrawler root does not exist after setup: $mediaRoot"
}

if (-not $NoCdpBrowser -and (Test-TcpPort -HostName "127.0.0.1" -Port $CdpPort)) {
    Write-Host "Using existing CDP browser on port $CdpPort."
} elseif ($StartCdpBrowser -and -not $NoCdpBrowser) {
    $cdpProfile = Join-Path $mediaRoot "browser_data\cdp_init_profile"
    Start-CdpBrowser -Port $CdpPort -ProfilePath $cdpProfile
} elseif (-not $NoCdpBrowser) {
    throw @"
CDP browser is not running on port $CdpPort.
Start Chrome or Edge yourself with --remote-debugging-port=$CdpPort, or rerun this script with -StartCdpBrowser to explicitly allow the script to launch a dedicated browser profile.
"@
}

$initStateFullPath = Join-Path $root $InitStatePath
$initStateDir = Split-Path -Parent $initStateFullPath
New-Item -ItemType Directory -Force -Path $initStateDir | Out-Null

$runsFullPath = Join-Path $root $InitRunsPath
New-Item -ItemType Directory -Force -Path $runsFullPath | Out-Null

$results = @()
$readyPlatforms = @()
foreach ($platform in $Platforms) {
    $mappedPlatform = Convert-PlatformAlias -Platform $platform
    $platformRunPath = Join-Path $runsFullPath $mappedPlatform
    $result = Invoke-MediaCrawlerInitCheck -MediaRoot $mediaRoot -Platform $mappedPlatform -RunPath $platformRunPath
    $results += $result
    if ($result.ok) {
        $readyPlatforms += $mappedPlatform
    }
}

$state = [ordered]@{
    initialized = ($readyPlatforms.Count -eq $Platforms.Count)
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    media_crawler_root = $mediaRoot
    cdp_port = if ($NoCdpBrowser) { $null } else { $CdpPort }
    keyword = $Keyword
    ready_platforms = $readyPlatforms
    platform_results = $results
}

$statusJson = $state | ConvertTo-Json -Depth 5
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($initStateFullPath, $statusJson, $utf8NoBom)

Write-Host "MediaCrawler initialization status written to $initStateFullPath"
if (-not $state.initialized) {
    throw "MediaCrawler initialization did not complete for all requested platforms. See $initStateFullPath."
}

Write-Host "MediaCrawler initialization completed for: $($readyPlatforms -join ', ')"
