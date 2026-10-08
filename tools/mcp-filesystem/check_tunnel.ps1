# Check the perfume-chem filesystem MCP tunnel health + readiness.
$ErrorActionPreference = "Continue"
Write-Output "=== tunnel-client health/readyz ==="
try {
    $h = Invoke-WebRequest -Uri "http://127.0.0.1:8080/healthz" -UseBasicParsing -TimeoutSec 5
    Write-Output "healthz: $($h.StatusCode) $($h.Content)"
} catch { Write-Output "healthz: NOT REACHABLE — daemon not running?" }
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/readyz" -UseBasicParsing -TimeoutSec 5
    Write-Output "readyz:  $($r.StatusCode) $($r.Content)"
} catch { Write-Output "readyz:  NOT REACHABLE" }

Write-Output ""
Write-Output "=== doctor (profile validation) ==="
$tc = "C:\Users\ASUS\AppData\Local\OpenCode\profiles\perfume-chem\tmp\opencode\tunnel-client\tunnel-client.exe"
$profile = Join-Path $PSScriptRoot "perfume-chem-fs.yaml"
if (Test-Path -LiteralPath $tc) {
    # Avoid colliding with the live daemon's loopback listener during validation.
    & $tc doctor --profile-file $profile --health.listen-addr 127.0.0.1:0 --explain 2>&1 | Select-Object -First 25
} else {
    Write-Output "tunnel-client.exe not found"
}
