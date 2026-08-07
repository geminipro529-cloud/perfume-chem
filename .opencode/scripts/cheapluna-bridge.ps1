[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$cheapLunaBuild = "a60f192b5f70230134499a2ef26b3e0816710c2a44b629a867aaec1a5aec064d"
$cheapLunaRuntime = Join-Path $env:LOCALAPPDATA (
    "OpenCode\CheapLuna\runtime\" + $cheapLunaBuild
)
$cheapLunaServer = Join-Path $cheapLunaRuntime "server.mjs"
$cheapLunaState = [System.IO.Path]::GetFullPath(
    (Join-Path $projectRoot ".opencode\.deepluna-home")
)
$projectBoundary = $projectRoot.TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
) + [System.IO.Path]::DirectorySeparatorChar
if (-not $cheapLunaState.StartsWith(
    $projectBoundary,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "CheapLuna bootstrap failed: mutable state escaped the Perfume-Chem project root."
}
$cheapLunaProjectId = "perfume-chem-cheapluna-isolated"
$nodeExecutable = "C:\Program Files\nodejs\node.exe"

if (-not (Test-Path -LiteralPath $nodeExecutable -PathType Leaf)) {
    throw "CheapLuna bootstrap failed: Node.js executable is missing."
}
if (-not (Test-Path -LiteralPath $cheapLunaServer -PathType Leaf)) {
    throw "CheapLuna bootstrap failed: candidate immutable runtime is missing."
}

# Direct DeepSeek credential (DEEPSEEK_DIRECT provider lock; no DeepInfra).
$providerToken = [Environment]::GetEnvironmentVariable(
    "PERFUME_DEEPSEEK_API_KEY",
    "Process"
)
if (-not $providerToken) {
    foreach ($name in @(
        "PERFUME_DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY"
    )) {
        $providerToken = [Environment]::GetEnvironmentVariable($name, "User")
        if ($providerToken) {
            break
        }
    }
}
if (-not $providerToken) {
    throw "CheapLuna bootstrap failed: direct DeepSeek credential is unavailable."
}

$requiredEnvironment = @{
    "DEEPLUNA_PRIMARY_PROFILE" = "cheapluna-chat"
    "DEEPLUNA_FAST_ONLY" = "0"
    "DEEPLUNA_CODEX_ORCHESTRATION" = "disabled"
    "DEEPLUNA_READER_POOL_MODE" = "DYNAMIC"
    "DEEPLUNA_EMBEDDED_COMPAT" = ""
    "DEEPLUNA_PROJECT_SCOPE" = "project"
    "DEEPLUNA_PROJECT_ID" = $cheapLunaProjectId
    "DEEPSEEK_ALLOWED_ROOT" = $projectRoot
    "DEEPSEEK_ORCHESTRATOR_HOME" = $cheapLunaState
    "NANODRUG_DEEPINFRA_READER_LANES" = "5"
    "NANODRUG_DEEPINFRA_WRITER_LANES" = "1"
    "DEEPSEEK_API_KEY" = $providerToken
}
foreach ($entry in $requiredEnvironment.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable(
        $entry.Key,
        $entry.Value,
        "Process"
    )
}
[Environment]::SetEnvironmentVariable(
    "DEEPLUNA_CODEX_EXECUTABLE",
    $null,
    "Process"
)
# Ensure no DeepInfra route is configured for this profile.
[Environment]::SetEnvironmentVariable(
    "DEEPINFRA_API_TOKEN",
    $null,
    "Process"
)

$daemonMarker = "--project-id=$cheapLunaProjectId"
$projectDaemonOwners = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "node.exe" -and
            $_.CommandLine -like "*--daemon*" -and
            $_.CommandLine -like "*$daemonMarker*"
        }
)
if ($projectDaemonOwners.Count -gt 1) {
    throw "CheapLuna bootstrap failed: multiple project daemon owners were found."
}
if (
    $projectDaemonOwners.Count -eq 1 -and
    $projectDaemonOwners[0].CommandLine.IndexOf(
        $cheapLunaServer,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -lt 0
) {
    throw "CheapLuna bootstrap failed: foreign project daemon owner holds the pipe."
}
$daemonMatches = $projectDaemonOwners

$daemonProcess = $null
if ($daemonMatches.Count -eq 0) {
    $daemonProcess = Start-Process `
        -FilePath $nodeExecutable `
        -ArgumentList @($cheapLunaServer, "--daemon", $daemonMarker) `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru
}

$healthProbe = @"
import { pathToFileURL } from 'node:url';
const bridge = await import(pathToFileURL(process.argv[2]).href);
const client = await bridge.connectProductionCandidateDaemon();
try {
  const health = await client.request('health', {});
  if (
    health.readiness !== 'READY' ||
    health.project_id !== '$cheapLunaProjectId' ||
    health.capacity?.read_limit !== 5 ||
    health.capacity?.write_limit !== 1
  ) process.exitCode = 2;
} finally {
  client.close();
}
"@

$ready = $false
$deadline = [DateTime]::UtcNow.AddSeconds(15)
do {
    $probeExitCode = 1
    $priorErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        & $nodeExecutable `
            --input-type=module `
            --eval $healthProbe `
            "cheapluna-readiness-probe" `
            $cheapLunaServer `
            2>$null
        $probeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $priorErrorActionPreference
    }
    if ($probeExitCode -eq 0) {
        $ready = $true
        break
    }
    if ($null -ne $daemonProcess -and $daemonProcess.HasExited) {
        throw "CheapLuna bootstrap failed: project daemon exited during startup."
    }
    Start-Sleep -Milliseconds 250
} while ([DateTime]::UtcNow -lt $deadline)
if (-not $ready) {
    throw "CheapLuna bootstrap failed: exact project daemon did not become READY."
}

Push-Location -LiteralPath $projectRoot
try {
    & $nodeExecutable $cheapLunaServer
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
