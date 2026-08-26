param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Message
)
# commit.ps1 - Option A: one-line commit of applied/placed changes through the app server.
# Usage:  .\tools\app-server\commit.ps1 "message"
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$server = "http://127.0.0.1:4519"

$envFile = Join-Path $here ".env"
$token = ""
if (Test-Path -LiteralPath $envFile) {
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^APP_SERVER_TOKEN=" } | Select-Object -First 1
    if ($line) { $token = ($line -replace "^APP_SERVER_TOKEN=", "").Trim() }
}
if (-not $token) { Write-Error "APP_SERVER_TOKEN not found in $envFile - run .\tools\app-server\start.ps1 first"; exit 1 }

$headers = @{ Authorization = "Bearer $token" }
$body = (@{ message = [string]$Message } | ConvertTo-Json -Compress)

try {
    $resp = Invoke-RestMethod -Uri "$server/api/commit" -Method Post -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 30
    if ($resp.ok) {
        Write-Output "COMMITTED"
        Write-Output "head: $($resp.head)"
        Write-Output "message: $Message"
    } else {
        Write-Error "commit failed: $($resp.error)"
        exit 2
    }
} catch {
    Write-Error "commit failed: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Output $_.ErrorDetails.Message }
    exit 2
}
