# Start the perfume-chem App Server (Option A local write backend).
# Reads APP_SERVER_TOKEN from tools/app-server/.env if present, else generates+stores one.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $here ".env"

# Ensure a token exists (persisted in .env, gitignored)
$token = $null
if (Test-Path -LiteralPath $envFile) {
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^APP_SERVER_TOKEN=" } | Select-Object -First 1
    if ($line) { $token = ($line -replace "^APP_SERVER_TOKEN=", "").Trim() }
}
if (-not $token) {
    $token = "app_" + ([guid]::NewGuid().ToString("N"))
    Set-Content -LiteralPath $envFile -Value "APP_SERVER_TOKEN=$token" -Encoding UTF8
    Write-Output "Generated new APP_SERVER_TOKEN (saved to $envFile)"
}

$root = (Resolve-Path (Join-Path $here "..\..")).Path
$env:APP_SERVER_ROOT = $root
$env:APP_SERVER_TOKEN = $token
$env:APP_SERVER_PORT = "4519"

# Kill any stale instance on the port
Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "tools[\\/]app-server[\\/]server\.mjs" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$p = Start-Process -FilePath "C:\Program Files\nodejs\node.exe" `
    -ArgumentList @("tools\app-server\server.mjs") `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2

try {
    $h = Invoke-WebRequest -Uri "http://127.0.0.1:4519/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Output "APP SERVER UP: $($h.Content)"
    Write-Output "TOKEN (for ChatGPT/scripts): $token"
} catch {
    Write-Output "APP SERVER FAILED TO START: $($_.Exception.Message)"
    exit 1
}
