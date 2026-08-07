[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$bridge = Join-Path $projectRoot ".opencode\scripts\cheapluna-bridge.ps1"

if (-not (Test-Path -LiteralPath $bridge -PathType Leaf)) {
    throw "CheapLuna bootstrap failed: project bridge is missing."
}

Push-Location -LiteralPath $projectRoot
try {
    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $bridge
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
