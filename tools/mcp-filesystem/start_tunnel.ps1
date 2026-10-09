# Start the perfume-chem filesystem MCP tunnel (browser ChatGPT Pro can then edit files
# without GitHub / without Codex credits).
#
# Prereqs (one-time, see SETUP.md):
#   1. Create a Tunnel + Runtime API key in Platform settings.
#   2. Put the real tunnel ID in tools/mcp-filesystem/perfume-chem-fs.yaml.
#   3. Set CONTROL_PLANE_API_KEY in the environment (user or system level).
#
# Each launch starts server.mjs on http://127.0.0.1:8765/mcp with a fresh random bearer
# token (kept only in this process's environment) and refuses to open the tunnel unless
# the server rejects requests without that token. The server is read-only unless
# -AllowWrites is given.
param([switch]$AllowWrites)
$ErrorActionPreference = "Stop"

$tcHome = "C:\Users\ASUS\AppData\Local\OpenCode\profiles\perfume-chem\tmp\opencode\tunnel-client"
$tc = Join-Path $tcHome "tunnel-client.exe"
$profile = Join-Path $PSScriptRoot "perfume-chem-fs.yaml"
if (-not (Test-Path -LiteralPath $tc)) {
    throw "tunnel-client not found at $tc — download the latest release from https://github.com/openai/tunnel-client/releases"
}
if (-not (Test-Path -LiteralPath $profile)) {
    throw "Tunnel profile not found at $profile"
}
if (-not $env:CONTROL_PLANE_API_KEY) {
    Write-Warning "CONTROL_PLANE_API_KEY is not set in this session. The daemon will fail auth until it is set."
}

# A stdio "commands" entry would let tunnel-client spawn the server with no token check.
$profileText = Get-Content -LiteralPath $profile -Raw
if ($profileText -match '(?m)^\s*commands\s*:' -or $profileText -notmatch 'Authorization:\s*env:FS_MCP_AUTH_HEADER') {
    throw "Refusing to open the tunnel: $profile must use server_urls with 'Authorization: env:FS_MCP_AUTH_HEADER', not a stdio command."
}

# Per-launch bearer token: lives only in this process's environment and its children.
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
$token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$env:FS_MCP_TOKEN = $token
$env:FS_MCP_AUTH_HEADER = "Bearer $token"
$env:FS_MCP_PORT = "8765"
if ($AllowWrites) { $env:FS_MCP_ALLOW_WRITES = "1" } else { Remove-Item Env:FS_MCP_ALLOW_WRITES -ErrorAction SilentlyContinue }

$node = "C:\Program Files\nodejs\node.exe"
if (-not (Test-Path -LiteralPath $node)) { $node = (Get-Command node -ErrorAction Stop).Source }
$serverScript = Join-Path $PSScriptRoot "server.mjs"
Write-Output "Starting filesystem MCP server (detached)..."
$srv = Start-Process -FilePath $node -ArgumentList @("`"$serverScript`"") -WindowStyle Hidden -PassThru

$mcpUrl = "http://127.0.0.1:$($env:FS_MCP_PORT)/mcp"
function Get-McpStatus([hashtable]$Headers) {
    $h = @{ Accept = "application/json, text/event-stream" } + $Headers
    try {
        return [int](Invoke-WebRequest -Uri $mcpUrl -Method Post -Body "{}" -ContentType "application/json" -Headers $h -UseBasicParsing -TimeoutSec 5).StatusCode
    } catch {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }
        return 0
    }
}
$anon = 0
for ($i = 0; $i -lt 20 -and $anon -eq 0 -and -not $srv.HasExited; $i++) {
    Start-Sleep -Milliseconds 500
    $anon = Get-McpStatus @{}
}
$authed = Get-McpStatus @{ Authorization = $env:FS_MCP_AUTH_HEADER }
if ($srv.HasExited -or $anon -ne 401 -or $authed -eq 401 -or $authed -eq 0) {
    if (-not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
    throw "Refusing to open the tunnel: the server at $mcpUrl is not enforcing this launch's bearer token (no token -> $anon, token -> $authed)."
}

Write-Output "Validating profile..."
& $tc doctor --profile-file $profile --explain 2>&1 | Select-Object -First 30
if ($LASTEXITCODE -ne 0) {
    Stop-Process -Id $srv.Id -Force
    throw "Tunnel profile validation failed with exit code $LASTEXITCODE"
}

Write-Output "Starting tunnel daemon (detached)..."
$p = Start-Process -FilePath $tc -ArgumentList @("run", "--profile-file", $profile) -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 4
if ($p.HasExited) {
    Stop-Process -Id $srv.Id -Force
    Write-Output "FAILED to start (exit $($p.ExitCode))"
    exit 1
}
Write-Output "PUBLIC: the tunnel URL is public; this launch's bearer token is the only thing keeping others out."
Write-Output "Bearer token for this launch (tunnel-client already sends it): $token"
if ($AllowWrites) { Write-Output "Server mode: WRITES ENABLED (write_file / edit_file allowed)" } else { Write-Output "Server mode: read-only (rerun with -AllowWrites to allow write_file / edit_file)" }
Write-Output "TUNNEL RUNNING pid=$($p.Id)  SERVER pid=$($srv.Id)"
Write-Output "Local admin UI: http://127.0.0.1:8080/ui  (healthz / readyz on same port)"
Write-Output "Verify with: .\tools\mcp-filesystem\check_tunnel.ps1"
