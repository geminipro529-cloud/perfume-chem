<#
.SYNOPSIS
Swaps the active Codex config between Codex-native and DeepLuna-fallback modes.

.DESCRIPTION
Codex reads .codex/config.toml. This script copies one of the two templates
into config.toml so you can switch without manual editing.

    Codex Native:      gpt-5.6-sol + DeepLuna delegation (Codex tokens available)
    DeepLuna Fallback: GLM 5.2 + DeepLuna primary routing (tokens exhausted)

.PARAMETER Mode
Which config to activate: "native" or "fallback".

.PARAMETER Status
Show which config is currently active without swapping.

.EXAMPLE
.\scripts\swap_codex_config.ps1 -Mode native
# Switches to Codex-native + DeepLuna delegation mode (tokens available).

.EXAMPLE
.\scripts\swap_codex_config.ps1 -Mode fallback
# Switches to DeepLuna fallback mode (tokens exhausted, GLM 5.2 primary).

.EXAMPLE
.\scripts\swap_codex_config.ps1 -Status
# Prints the currently active config.
#>

param(
    [ValidateSet("native", "fallback")]
    [string]$Mode,

    [switch]$Status
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ConfigToml = Join-Path $Root ".codex\config.toml"
$Native = Join-Path $Root ".codex\config_codex_native.toml"
$Fallback = Join-Path $Root ".codex\config_deepluna_fallback.toml"

function Get-ActiveConfig {
    if (-not (Test-Path $ConfigToml)) {
        return "MISSING -- no config.toml found"
    }
    $content = Get-Content $ConfigToml -Raw
    if ($content -match 'model\s*=\s*"gpt-5\.6-sol"') {
        return "Codex Native + DeepLuna delegation (gpt-5.6-sol, tokens available)"
    }
    elseif ($content -match 'model\s*=\s*"deepinfra/zai-org/GLM-5\.2"') {
        return "DeepLuna Fallback (GLM 5.2 primary, tokens exhausted)"
    }
    else {
        return "UNKNOWN -- model does not match either template"
    }
}

if ($Status) {
    Write-Host "Active: $(Get-ActiveConfig)" -ForegroundColor Cyan
    Write-Host "Templates:" -ForegroundColor Gray
    Write-Host "  native   -> config_codex_native.toml     (gpt-5.6-sol + DeepLuna delegation)" -ForegroundColor Gray
    Write-Host "  fallback -> config_deepluna_fallback.toml (GLM 5.2 primary + DeepLuna routing)" -ForegroundColor Gray
    exit 0
}

if (-not $Mode) {
    Write-Host "Usage: swap_codex_config.ps1 -Mode <native|fallback>   OR   -Status" -ForegroundColor Yellow
    Write-Host "Active: $(Get-ActiveConfig)" -ForegroundColor Cyan
    exit 1
}

# Validate templates exist
if ($Mode -eq "native" -and -not (Test-Path $Native)) {
    Write-Error "Template not found: $Native"
    exit 1
}
if ($Mode -eq "fallback" -and -not (Test-Path $Fallback)) {
    Write-Error "Template not found: $Fallback"
    exit 1
}

$source = if ($Mode -eq "native") { $Native } else { $Fallback }
$label = if ($Mode -eq "native") {
    "Codex Native + DeepLuna delegation (gpt-5.6-sol, tokens available)"
} else {
    "DeepLuna Fallback (GLM 5.2 primary, tokens exhausted)"
}

# Backup existing config if it differs from both templates
if (Test-Path $ConfigToml) {
    $current = Get-Content $ConfigToml -Raw
    $nativeContent = Get-Content $Native -Raw
    $fallbackContent = Get-Content $Fallback -Raw
    if ($current -ne $nativeContent -and $current -ne $fallbackContent) {
        $backup = "$ConfigToml.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $ConfigToml $backup
        Write-Host "Backed up custom config to: $backup" -ForegroundColor Yellow
    }
}

Copy-Item $source $ConfigToml -Force
Write-Host "Switched to: $label" -ForegroundColor Green
