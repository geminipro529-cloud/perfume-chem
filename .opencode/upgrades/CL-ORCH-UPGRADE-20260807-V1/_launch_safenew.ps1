# SAFE_NEW characterization (PATH 2, no promotion) through the candidate daemon,
# in an isolated benchmark state namespace per REV-9 17 (no active-project contamination).
$ErrorActionPreference = "Stop"
$root = "D:\chatbots\perfume-chem"
$u = "$root\.opencode\upgrades\CL-ORCH-UPGRADE-20260807-V1"
$runtime = "$env:LOCALAPPDATA\OpenCode\CheapLuna\runtime\a60f192b5f70230134499a2ef26b3e0816710c2a44b629a867aaec1a5aec064d"
$server = "$runtime\server.mjs"
$stateHome = Join-Path $env:TEMP "cl_bench_safenew"
$stateProject = "perfume-chem-cheapluna-safenew"
# Windows/node:sqlite CANTOPEN boundary: the migration's temporary backup path
# (daemon-v2/scheduler.schema-v2.<ts>-bootstrap.backup.sqlite3.candidate-<uuid>.tmp)
# fails to open above ~216 characters. The deep repo path
# (.opencode\upgrades\...\benchmark\state\...) crosses that boundary; a short TEMP
# root keeps the temp backup path under it. Root cause verified 2026-08-07.
if (Test-Path -LiteralPath $stateHome) { Remove-Item -LiteralPath $stateHome -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stateHome | Out-Null

$env:DEEPLUNA_PROJECT_ID = $stateProject
$env:DEEPSEEK_ORCHESTRATOR_HOME = $stateHome
$env:DEEPLUNA_PRIMARY_PROFILE = "cheapluna-chat"
$env:DEEPLUNA_FAST_ONLY = "0"
$env:DEEPLUNA_CODEX_ORCHESTRATION = "disabled"
$env:DEEPLUNA_READER_POOL_MODE = "DYNAMIC"
$env:DEEPLUNA_EMBEDDED_COMPAT = ""
$env:DEEPLUNA_PROJECT_SCOPE = "project"
$env:NANODRUG_DEEPINFRA_READER_LANES = "5"
$env:NANODRUG_DEEPINFRA_WRITER_LANES = "1"
$env:DEEPSEEK_ALLOWED_ROOT = $root
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("PERFUME_DEEPSEEK_API_KEY", "Process")
$env:CHEAPLUNA_SERVER = $server
$env:UPGRADE_DIR = $u
$env:PROFILE_MARKER = "SAFE_NEW"

if (-not $env:DEEPSEEK_API_KEY) { throw "PERFUME_DEEPSEEK_API_KEY not present" }

& "C:\Program Files\nodejs\node.exe" "$u\_bootstrap_baseline_store.mjs" "$runtime\lib\scheduler-store.mjs" $stateHome $stateProject $root
if ($LASTEXITCODE -ne 0) { throw "SAFE_NEW store bootstrap failed" }
Write-Output "SAFE_NEW_STORE_BOOTSTRAPPED"

$daemon = Start-Process -FilePath "C:\Program Files\nodejs\node.exe" -ArgumentList @($server, "--daemon", "--project-id=$stateProject") -WorkingDirectory $root -WindowStyle Hidden -PassThru

$ready = $false
$deadline = [DateTime]::UtcNow.AddSeconds(25)
do {
    Start-Sleep -Milliseconds 500
    & "C:\Program Files\nodejs\node.exe" "$u\_health_baseline.mjs" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    if ($daemon.HasExited) { throw "SAFE_NEW daemon exited during startup (code $($daemon.ExitCode))" }
} while ([DateTime]::UtcNow -lt $deadline)
if (-not $ready) { throw "SAFE_NEW daemon did not become READY" }
Write-Output "SAFE_NEW_DAEMON_READY pid=$($daemon.Id)"

try {
    & "C:\Program Files\nodejs\node.exe" "$u\_char_run.mjs"
    $rc = $LASTEXITCODE
} finally {
    if (-not $daemon.HasExited) { Stop-Process -Id $daemon.Id -Force -ErrorAction SilentlyContinue }
}
exit $rc
