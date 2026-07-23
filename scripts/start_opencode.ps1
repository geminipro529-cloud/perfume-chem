<#
.SYNOPSIS
  Launch OpenCode with perfume-chem-only configuration, credentials, and state.

.DESCRIPTION
  OpenCode is invoked through the exact npm shim, never through the PowerShell
  wrapper function. Process variables are restored after OpenCode exits so the
  calling Codex or VS Code terminal does not inherit OpenCode routing.
#>

param(
  [switch]$NoCache,
  [switch]$Quiet,
  [Alias("Args")]
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$OpenCodeArgs = @()
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$opencodeConfig = Join-Path $repoRoot "opencode.json"
$opencodeConfigDir = Join-Path $repoRoot ".opencode"
$profileRoot = Join-Path $env:LOCALAPPDATA "OpenCode\profiles\perfume-chem"
$opencodeCommand = Join-Path $env:APPDATA "npm\opencode.cmd"

if (-not (Test-Path -LiteralPath $opencodeConfig -PathType Leaf)) {
  throw "Perfume-Chem OpenCode config was not found: $opencodeConfig"
}
if (-not (Test-Path -LiteralPath $opencodeCommand -PathType Leaf)) {
  throw "OpenCode npm shim was not found: $opencodeCommand"
}

$scopedVariables = @(
  "PERFUME_PROJECT_ROOT",
  "PERFUME_DEEPINFRA_API_KEY",
  "PERFUME_DEEPSEEK_API_KEY",
  "DEEPINFRA_API_KEY",
  "DEEPINFRA_API_TOKEN",
  "DEEPSEEK_API_KEY",
  "OPENAI_API_KEY",
  "OPENAI_BASE_URL",
  "OPENAI_ORGANIZATION",
  "OPENAI_PROJECT",
  "CODEX_API_KEY",
  "CODEX_HOME",
  "CHATGPT_ACCOUNT_ID",
  "OPENCODE_CONFIG",
  "OPENCODE_CONFIG_DIR",
  "OPENCODE_PROJECT_ROOT",
  "OPENCODE_DISABLE_CLAUDE_CODE",
  "OPENCODE_SESSION_ID",
  "TEMP",
  "TMP",
  "XDG_CONFIG_HOME",
  "XDG_DATA_HOME",
  "XDG_STATE_HOME",
  "XDG_CACHE_HOME"
)

$environmentSnapshot = @{}
foreach ($name in $scopedVariables) {
  $environmentSnapshot[$name] = @{
    Exists = Test-Path -LiteralPath "Env:$name"
    Value = [Environment]::GetEnvironmentVariable($name, "Process")
  }
}

function Get-UserEnvironmentValue {
  param([Parameter(Mandatory = $true)][string[]]$Names)

  foreach ($name in $Names) {
    $value = [Environment]::GetEnvironmentVariable($name, "User")
    if ($value) {
      return $value
    }
  }
  return $null
}

$exitCode = 1
$locationPushed = $false
try {
  $tempRoot = Join-Path $profileRoot "tmp"
  $cacheRoot = Join-Path $profileRoot "cache"
  if ($NoCache) {
    $cacheRoot = Join-Path $tempRoot "cache-session-$PID"
  }

  $runtimePaths = @(
    (Join-Path $profileRoot "config"),
    (Join-Path $profileRoot "data"),
    (Join-Path $profileRoot "state"),
    $tempRoot,
    $cacheRoot
  )
  foreach ($path in $runtimePaths) {
    if (-not (Test-Path -LiteralPath $path)) {
      New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
  }

  $env:PERFUME_PROJECT_ROOT = $repoRoot
  $env:OPENCODE_CONFIG = $opencodeConfig
  $env:OPENCODE_CONFIG_DIR = $opencodeConfigDir
  $env:OPENCODE_PROJECT_ROOT = $repoRoot
  $env:OPENCODE_DISABLE_CLAUDE_CODE = "1"
  $env:OPENCODE_SESSION_ID = "perfume-chem-$PID-$([Guid]::NewGuid().ToString('N'))"
  $env:TEMP = $tempRoot
  $env:TMP = $tempRoot
  $env:XDG_CONFIG_HOME = Join-Path $profileRoot "config"
  $env:XDG_DATA_HOME = Join-Path $profileRoot "data"
  $env:XDG_STATE_HOME = Join-Path $profileRoot "state"
  $env:XDG_CACHE_HOME = $cacheRoot

  $deepInfraKey = Get-UserEnvironmentValue @(
    "PERFUME_DEEPINFRA_API_KEY",
    "DEEPINFRA_API_KEY",
    "DEEPINFRA_API_TOKEN"
  )
  $deepSeekKey = Get-UserEnvironmentValue @(
    "PERFUME_DEEPSEEK_API_KEY",
    "DEEPSEEK_API_KEY"
  )

  if ($deepInfraKey) {
    $env:PERFUME_DEEPINFRA_API_KEY = $deepInfraKey
  }
  if ($deepSeekKey) {
    $env:PERFUME_DEEPSEEK_API_KEY = $deepSeekKey
  }

  # Keep generic provider variables out of the OpenCode process. The project
  # config reads PERFUME_* variables explicitly; env-guard maps them only into
  # tool subprocesses that require the providers' conventional variable names.
  foreach ($name in @(
    "DEEPINFRA_API_KEY",
    "DEEPINFRA_API_TOKEN",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_ORGANIZATION",
    "OPENAI_PROJECT",
    "CODEX_API_KEY",
    "CODEX_HOME",
    "CHATGPT_ACCOUNT_ID"
  )) {
    [Environment]::SetEnvironmentVariable($name, $null, "Process")
  }

  if (-not $Quiet) {
    Write-Host "=== Perfume-Chem OpenCode (isolated) ===" -ForegroundColor Cyan
    Write-Host "Project: $repoRoot" -ForegroundColor Gray
    Write-Host "Config: $opencodeConfig" -ForegroundColor Gray
    Write-Host "Runtime: $profileRoot" -ForegroundColor Gray
    Write-Host "DeepSeek credential available: $([bool]$deepSeekKey)" -ForegroundColor Gray
    Write-Host "DeepInfra credential available: $([bool]$deepInfraKey)" -ForegroundColor Gray
    Write-Host "Codex/OpenAI inheritance: disabled" -ForegroundColor Gray
    Write-Host ""
  }

  Push-Location -LiteralPath $repoRoot
  $locationPushed = $true
  # Windows PowerShell converts any native stderr line into an ErrorRecord.
  # OpenCode writes diagnostics and progress to stderr even on success, so do
  # not let ErrorActionPreference=Stop terminate a healthy child process.
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & $opencodeCommand @OpenCodeArgs
    $exitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
}
finally {
  if ($locationPushed) {
    Pop-Location
  }
  foreach ($name in $scopedVariables) {
    $snapshot = $environmentSnapshot[$name]
    if ($snapshot.Exists) {
      [Environment]::SetEnvironmentVariable($name, $snapshot.Value, "Process")
    }
    else {
      [Environment]::SetEnvironmentVariable($name, $null, "Process")
    }
  }
  $global:LASTEXITCODE = $exitCode
}
