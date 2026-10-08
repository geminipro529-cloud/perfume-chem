# Start the perfume-chem filesystem MCP tunnel (browser ChatGPT Pro can then edit files
# without GitHub / without Codex credits).
#
# Prereqs (one-time, see SETUP.md):
#   1. Create a Tunnel + Runtime API key in Platform settings.
#   2. Put the real tunnel ID in tools/mcp-filesystem/perfume-chem-fs.yaml.
#   3. Set CONTROL_PLANE_API_KEY in the environment (user or system level).
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

Write-Output "Validating profile..."
& $tc doctor --profile-file $profile --explain 2>&1 | Select-Object -First 30
if ($LASTEXITCODE -ne 0) {
    throw "Tunnel profile validation failed with exit code $LASTEXITCODE"
}

Write-Output "Starting tunnel daemon (detached)..."
$p = Start-Process -FilePath $tc -ArgumentList @("run", "--profile-file", $profile) -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 4
if ($p.HasExited) {
    Write-Output "FAILED to start (exit $($p.ExitCode))"
    exit 1
}
Write-Output "TUNNEL RUNNING pid=$($p.Id)"
Write-Output "Local admin UI: http://127.0.0.1:8080/ui  (healthz / readyz on same port)"
Write-Output "Verify with: .\tools\mcp-filesystem\check_tunnel.ps1"
