# start_public.ps1 - expose the app-server over HTTPS for GPT Actions.
# GPT Actions require a public HTTPS URL; the MCP tunnel cannot serve generic HTTP.
# This script starts cloudflared quick tunnel (no account needed) pointed at the
# local app-server, then prints the public URL to paste into openapi.yaml's server.
#
# Prereq: cloudflared.exe on PATH or set CLOUDFLARED_PATH.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $here "..\..")).Path

# 1. Ensure the app-server is running
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:4519/api/health" -UseBasicParsing -TimeoutSec 3
    Write-Output "[ok] app-server already running on 127.0.0.1:4519"
} catch {
    Write-Output "[..] starting app-server..."
    & (Join-Path $here "start.ps1") | Out-Null
    Start-Sleep -Seconds 2
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:4519/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Output "[ok] app-server started"
}

# 2. Locate cloudflared
$cloudflared = $env:CLOUDFLARED_PATH
if (-not $cloudflared) {
    $candidate = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($candidate) { $cloudflared = $candidate.Source }
}
if (-not $cloudflared) {
    Write-Error "cloudflared not found. Install: winget install cloudflared  (or download from https://github.com/cloudflare/cloudflared/releases) and set CLOUDFLARED_PATH."
    exit 1
}
Write-Output "[ok] cloudflared: $cloudflared"

# 3. Start the quick tunnel (writes the URL line to a log)
$log = Join-Path $here "cloudflared.log"
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath $cloudflared -ArgumentList @("tunnel", "--url", "http://127.0.0.1:4519", "--no-autoupdate") -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru

# 4. Wait for the trycloudflare.com URL in the log
$url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $text = ""
    if (Test-Path -LiteralPath $log) { $text = Get-Content -LiteralPath $log -Raw -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath "$log.err") { $text += Get-Content -LiteralPath "$log.err" -Raw -ErrorAction SilentlyContinue }
    if ($text -match "https://[a-z0-9-]+\.trycloudflare\.com") {
        $url = $Matches[0]
        break
    }
}
if (-not $url) {
    Write-Error "cloudflared started but no public URL appeared. Check $log"
    exit 1
}

Write-Output ""
Write-Output "============================================================"
Write-Output " PUBLIC HTTPS URL: $url"
Write-Output "============================================================"
Write-Output "Next steps:"
Write-Output "  1. Paste this URL into tools/app-server/openapi.yaml servers[0].url"
Write-Output "  2. In ChatGPT: create a private GPT -> Actions -> Create new action"
Write-Output "     -> paste openapi.yaml -> set 'API Key' auth with the bearer token"
Write-Output "     (token lives in tools/app-server/.env as APP_SERVER_TOKEN)"
Write-Output "  3. Use the GPT with a NON-Pro model (Pro mode cannot use custom Actions)"
Write-Output ""
Write-Output "Note: the trycloudflare URL changes on each restart. For a stable URL,"
Write-Output "use a named cloudflared tunnel (cloudflared tunnel login) or a VPS."
