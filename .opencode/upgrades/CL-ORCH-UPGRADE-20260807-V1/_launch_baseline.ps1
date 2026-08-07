$ErrorActionPreference = "Stop"
$root = "D:\chatbots\perfume-chem"
$u = "$root\.opencode\upgrades\CL-ORCH-UPGRADE-20260807-V1"
$runtime = "$env:LOCALAPPDATA\OpenCode\CheapLuna\runtime\b98f913fe8e87a17d697a86f0fe035eabef9517642dee1fe3f33651f76fdb44f"
$server = "$runtime\server.mjs"
$baselineHome = "$u\benchmark\state\BASELINE"
$baselineProject = "perfume-chem-cheapluna-baseline"
if (Test-Path -LiteralPath $baselineHome) { Remove-Item -LiteralPath $baselineHome -Recurse -Force }
New-Item -ItemType Directory -Force -Path $baselineHome | Out-Null

$env:DEEPLUNA_PROJECT_ID = $baselineProject
$env:DEEPSEEK_ORCHESTRATOR_HOME = $baselineHome
$env:DEEPLUNA_PRIMARY_PROFILE = "cheapluna-chat"
$env:DEEPLUNA_FAST_ONLY = "0"
$env:DEEPLUNA_CODEX_ORCHESTRATION = "disabled"
$env:DEEPLUNA_READER_POOL_MODE = "DYNAMIC"
$env:DEEPLUNA_EMBEDDED_COMPAT = ""
$env:DEEPLUNA_PROJECT_SCOPE = "project"
$env:DEEPSEEK_ALLOWED_ROOT = $root
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("PERFUME_DEEPSEEK_API_KEY", "Process")
$env:CHEAPLUNA_SERVER = $server
$env:UPGRADE_DIR = $u
$env:BASELINE_OUT = "$u\evidence\baseline_results.json"

if (-not $env:DEEPSEEK_API_KEY) { throw "PERFUME_DEEPSEEK_API_KEY not present" }

# Bootstrap the isolated BASELINE store standalone (daemon created=true path is not reliable in this environment)
& "C:\Program Files\nodejs\node.exe" "$u\_bootstrap_baseline_store.mjs" "$runtime\lib\scheduler-store.mjs" $baselineHome $baselineProject $root
if ($LASTEXITCODE -ne 0) { throw "BASELINE store bootstrap failed" }
Write-Output "BASELINE_STORE_BOOTSTRAPPED"

$daemon = Start-Process -FilePath "C:\Program Files\nodejs\node.exe" -ArgumentList @($server, "--daemon", "--project-id=$baselineProject") -WorkingDirectory $root -WindowStyle Hidden -PassThru

$ready = $false
$deadline = [DateTime]::UtcNow.AddSeconds(20)
do {
    Start-Sleep -Milliseconds 500
    & "C:\Program Files\nodejs\node.exe" "$u\_health_baseline.mjs" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    if ($daemon.HasExited) { throw "baseline daemon exited during startup (code $($daemon.ExitCode))" }
} while ([DateTime]::UtcNow -lt $deadline)
if (-not $ready) { throw "baseline daemon did not become READY" }
Write-Output "BASELINE_DAEMON_READY pid=$($daemon.Id)"

try {
    & "C:\Program Files\nodejs\node.exe" "$u\_run_baseline.mjs"
    $rc = $LASTEXITCODE
} finally {
    if (-not $daemon.HasExited) { Stop-Process -Id $daemon.Id -Force -ErrorAction SilentlyContinue }
}
exit $rc
