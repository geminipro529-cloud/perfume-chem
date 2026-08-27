[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$bridgeRoot = "C:\Users\ASUS\.codex\tools\opencode-deepseek-mcp"
$bridgeServer = Join-Path $bridgeRoot "server.mjs"
$bridgeDaemon = Join-Path $bridgeRoot "orchestrator-daemon.mjs"
$bridgeProtocol = Join-Path $bridgeRoot "lib\daemon-protocol-v2.mjs"
$nodeExecutable = "C:\Program Files\nodejs\node.exe"
$isolatedRuntime = Join-Path $projectRoot ".deepluna-home"
$daemonMarker = "--project-id=perfume-chem"
$daemonHealthProbe = @"
import { pathToFileURL } from 'node:url';
const bridge = await import(pathToFileURL(process.argv[2]).href);
const client = await bridge.connectProductionCandidateDaemon();
try {
  const health = await client.request('health', {});
  if (
    health.readiness !== 'READY' ||
    health.project_id !== 'perfume-chem' ||
    health.capacity?.read_limit !== 5 ||
    health.capacity?.write_limit !== 1
  ) process.exitCode = 2;
} finally {
  client.close();
}
"@
$daemonOwnerProbe = @"
import { pathToFileURL } from 'node:url';
const protocol = await import(pathToFileURL(process.argv[2]).href);
const daemon = await import(pathToFileURL(process.argv[3]).href);
const address = protocol.candidateDaemonPipeNameForProject('perfume-chem');
try {
  const owner = daemon.getCandidateWindowsNamedPipeServerProcessId(address);
  if (
    owner.status !== 'PROVEN' ||
    !Number.isSafeInteger(owner.processId) ||
    owner.processId < 1
  ) process.exit(3);
  process.stdout.write(String(owner.processId));
} catch {
  process.exit(4);
}
"@

if (-not (Test-Path -LiteralPath $nodeExecutable -PathType Leaf)) {
    throw "DeepLuna bootstrap failed: Node.js executable is missing."
}
if (-not (Test-Path -LiteralPath $bridgeServer -PathType Leaf)) {
    throw "DeepLuna bootstrap failed: bridge server is missing."
}
if (
    -not (Test-Path -LiteralPath $bridgeDaemon -PathType Leaf) -or
    -not (Test-Path -LiteralPath $bridgeProtocol -PathType Leaf)
) {
    throw "DeepLuna bootstrap failed: bridge daemon identity modules are missing."
}

$requiredEnvironment = @{
    "DEEPLUNA_PRIMARY_PROFILE" = "deepinfra-fast"
    "DEEPLUNA_FAST_ONLY" = "1"
    "DEEPLUNA_CODEX_ORCHESTRATION" = "disabled"
    "DEEPLUNA_READER_POOL_MODE" = "DYNAMIC"
    "NANODRUG_DEEPINFRA_READER_LANES" = "5"
    "DEEPLUNA_PROJECT_ID" = "perfume-chem"
    "DEEPLUNA_PROJECT_SCOPE" = "project"
    "DEEPSEEK_ALLOWED_ROOT" = $projectRoot
    "DEEPSEEK_ORCHESTRATOR_HOME" = $isolatedRuntime
}

# Force DEEPSEEK_ORCHESTRATOR_HOME to the workspace-rooted store so the
# sandbox identity (CodexSandboxUsers) has Modify on the daemon-v2 dir.
# The AppData default is read-only under the sandbox token.
$env:DEEPSEEK_ORCHESTRATOR_HOME = $isolatedRuntime

foreach ($entry in $requiredEnvironment.GetEnumerator()) {
    $actual = [Environment]::GetEnvironmentVariable($entry.Key, "Process")
    if ($actual -ne $entry.Value) {
        throw "DeepLuna bootstrap failed: project isolation environment is not exact."
    }
}

$embeddedCompatibility = [Environment]::GetEnvironmentVariable(
    "DEEPLUNA_EMBEDDED_COMPAT",
    "Process"
)
if ($null -ne $embeddedCompatibility -and $embeddedCompatibility -ne "") {
    throw "DeepLuna bootstrap failed: embedded compatibility must be disabled."
}

# Authenticate before process discovery. A daemon may run under a different
# Windows token, making its command line unreadable even though it owns the
# exact project pipe.
$daemonReady = $false
$savedErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    & $nodeExecutable `
        --input-type=module `
        --eval $daemonHealthProbe `
        "deepluna-initial-health-probe" `
        $bridgeServer `
        2>$null
    $daemonReady = $LASTEXITCODE -eq 0
}
finally {
    $ErrorActionPreference = $savedErrorActionPreference
}

if (-not $daemonReady) {
    # If authentication failed, prove whether the exact project pipe is still
    # owned before attempting a start. This catches hidden stale/incompatible
    # daemons and prevents an EADDRINUSE duplicate-start loop.
    $savedErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $pipeOwnerPid = & $nodeExecutable `
            --input-type=module `
            --eval $daemonOwnerProbe `
            "deepluna-pipe-owner-probe" `
            $bridgeProtocol `
            $bridgeDaemon `
            2>$null
        $pipeOwnerProbeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    if ($pipeOwnerProbeExitCode -eq 0 -and $pipeOwnerPid -match "^[1-9][0-9]*$") {
        throw (
            "DeepLuna bootstrap failed: stale or incompatible daemon owns " +
            "the project pipe (PID $pipeOwnerPid). Refusing duplicate start."
        )
    }

    # Command-line discovery is only a secondary guard. WMI may be denied or
    # may redact another-token process details, so it is never readiness proof.
    $daemon = $null
    try {
        $daemon = Get-CimInstance Win32_Process -ErrorAction Stop |
            Where-Object {
                $_.Name -eq "node.exe" -and
                $_.CommandLine -like "*opencode-deepseek-mcp*server.mjs*" -and
                $_.CommandLine -like "*--daemon*" -and
                $_.CommandLine -like "*$daemonMarker*"
            } |
            Select-Object -First 1
    } catch {
        $daemon = $null
    }
    if ($null -ne $daemon) {
        throw (
            "DeepLuna bootstrap failed: matching daemon process is not " +
            "authenticated READY. Refusing duplicate start."
        )
    }

    $daemonProcess = Start-Process `
        -FilePath $nodeExecutable `
        -ArgumentList @($bridgeServer, "--daemon", $daemonMarker) `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru
}

$readinessDeadline = [DateTime]::UtcNow.AddSeconds(12)
while (-not $daemonReady -and [DateTime]::UtcNow -lt $readinessDeadline) {
    $savedErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $nodeExecutable `
            --input-type=module `
            --eval $daemonHealthProbe `
            "deepluna-readiness-probe" `
            $bridgeServer `
            2>$null
        $probeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    if ($probeExitCode -eq 0) {
        $daemonReady = $true
        break
    }
    if ($null -ne $daemonProcess -and $daemonProcess.HasExited) {
        throw "DeepLuna bootstrap failed: the project daemon exited during startup."
    }
    Start-Sleep -Milliseconds 250
}

if (-not $daemonReady) {
    throw "DeepLuna bootstrap failed: the project daemon did not become READY."
}

Push-Location -LiteralPath $projectRoot
try {
    & $nodeExecutable $bridgeServer
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
