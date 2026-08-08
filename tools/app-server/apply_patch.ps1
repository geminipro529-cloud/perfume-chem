param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PatchFile,
    [switch]$DryRun
)
# apply_patch.ps1 - Option A (A1): verify + apply a unified diff through the app server.
# Usage:  .\tools\app-server\apply_patch.ps1 output\patch-inbox\edit.patch
#         .\tools\app-server\apply_patch.ps1 output\patch-inbox\edit.patch -DryRun
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $here "..\..")).Path
$server = "http://127.0.0.1:4519"

# token from .env
$envFile = Join-Path $here ".env"
$token = ""
if (Test-Path -LiteralPath $envFile) {
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^APP_SERVER_TOKEN=" } | Select-Object -First 1
    if ($line) { $token = ($line -replace "^APP_SERVER_TOKEN=", "").Trim() }
}
if (-not $token) { Write-Error "APP_SERVER_TOKEN not found in $envFile - run .\tools\app-server\start.ps1 first"; exit 1 }

# resolve patch path (allow repo-relative)
$patchAbs = if ([System.IO.Path]::IsPathRooted($PatchFile)) { $PatchFile } else { Join-Path $root $PatchFile }
if (-not (Test-Path -LiteralPath $patchAbs)) { Write-Error "patch file not found: $patchAbs"; exit 1 }
$patchText = Get-Content -LiteralPath $patchAbs -Raw

$headers = @{ Authorization = "Bearer $token" }
$patchPlain = [string]$patchText
$body = (@{ patch = $patchPlain; dry_run = [bool]$DryRun } | ConvertTo-Json -Compress)

try {
    $resp = Invoke-RestMethod -Uri "$server/api/apply" -Method Post -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 30
    if ($DryRun) {
        if ($resp.ok) { Write-Output "DRY RUN OK - patch applies cleanly" } else { Write-Output "DRY RUN FAILED: $($resp.error)"; exit 2 }
    } else {
        Write-Output "PATCH APPLIED"
        Write-Output "---- git status ----"
        Write-Output $resp.status
        Write-Output "---- review with: git diff ----"
    }
} catch {
    Write-Error "apply failed: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Output $_.ErrorDetails.Message }
    exit 2
}
