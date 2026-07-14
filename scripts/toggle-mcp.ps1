<#
.SYNOPSIS
    Toggle MCP (Model Context Protocol) servers in opencode.json for token optimization.

.DESCRIPTION
    Enables or disables specific MCP servers, or applies named profiles:
    - formula : pubchem + memory + sequential_thinking ON, github + playwright OFF (chemistry work)
    - dev     : all MCPs ON (full development)
    - minimal : all MCPs OFF (maximum token efficiency)
    - full    : all MCPs ON (same as dev)

.EXAMPLE
    .\scripts\toggle-mcp.ps1 -Profile formula
    .\scripts\toggle-mcp.ps1 -Enable github,playwright
    .\scripts\toggle-mcp.ps1 -Disable playwright
    .\scripts\toggle-mcp.ps1 -Status

.NOTES
    Restart OpenCode after running this script for changes to take effect.
#>

param(
    [ValidateSet('formula', 'dev', 'minimal', 'full')]
    [string]$Profile,

    [string[]]$Enable,

    [string[]]$Disable,

    [switch]$Status
)

$configPath = Join-Path (Join-Path $PSScriptRoot '..') 'opencode.json'

if (-not (Test-Path $configPath)) {
    Write-Error "opencode.json not found at: $configPath"
    exit 1
}

try {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-Error "Failed to parse opencode.json: $_"
    exit 1
}

# Profile definitions
$profiles = @{
    'formula' = @{
        'github'              = $false
        'playwright'          = $false
        'sequential_thinking' = $true
        'pubchem'             = $true
        'memory'              = $true
    }
    'dev' = @{
        'github'              = $true
        'playwright'          = $true
        'sequential_thinking' = $true
        'pubchem'             = $true
        'memory'              = $true
    }
    'minimal' = @{
        'github'              = $false
        'playwright'          = $false
        'sequential_thinking' = $false
        'pubchem'             = $false
        'memory'              = $false
    }
    'full' = @{
        'github'              = $true
        'playwright'          = $true
        'sequential_thinking' = $true
        'pubchem'             = $true
        'memory'              = $true
    }
}

# Apply profile
if ($Profile) {
    Write-Host "`n=== Applying profile: $Profile ===" -ForegroundColor Cyan
    $profileConfig = $profiles[$Profile]
    foreach ($mcpName in $profileConfig.Keys) {
        if ($config.mcp.PSObject.Properties.Name -contains $mcpName) {
            $oldState = $config.mcp.$mcpName.enabled
            $newState = $profileConfig[$mcpName]
            $config.mcp.$mcpName.enabled = $newState
            $icon = if ($newState) { '+' } else { '-' }
            Write-Host "  $icon $mcpName : $oldState -> $newState"
        } else {
            Write-Host "  ? $mcpName : not found in config (skipped)" -ForegroundColor Yellow
        }
    }
}

# Apply explicit enable/disable
foreach ($name in $Enable) {
    if ($config.mcp.PSObject.Properties.Name -contains $name) {
        $oldState = $config.mcp.$name.enabled
        $config.mcp.$name.enabled = $true
        Write-Host "  + $name : $oldState -> True"
    } else {
        Write-Host "  ? $name : not found in config (skipped)" -ForegroundColor Yellow
    }
}

foreach ($name in $Disable) {
    if ($config.mcp.PSObject.Properties.Name -contains $name) {
        $oldState = $config.mcp.$name.enabled
        $config.mcp.$name.enabled = $false
        Write-Host "  - $name : $oldState -> False"
    } else {
        Write-Host "  ? $name : not found in config (skipped)" -ForegroundColor Yellow
    }
}

# Save config
if ($Profile -or $Enable -or $Disable) {
    $json = $config | ConvertTo-Json -Depth 10
    # ConvertTo-Json may produce compressed JSON; use a consistent format
    Set-Content -Path $configPath -Value $json -Encoding UTF8
    Write-Host "`nConfig saved to: $configPath" -ForegroundColor Green
    Write-Host "RESTART OpenCode for changes to take effect." -ForegroundColor Yellow
}

# Show status
if ($Status -or (-not $Profile -and -not $Enable -and -not $Disable)) {
    Write-Host "`n=== Current MCP Status ===" -ForegroundColor Cyan
    $totalEnabled = 0
    $totalDisabled = 0
    foreach ($prop in $config.mcp.PSObject.Properties) {
        $state = if ($prop.Value.enabled) {
            $totalEnabled++
            "ON "
        } else {
            $totalDisabled++
            "OFF"
        }
        $color = if ($prop.Value.enabled) { 'Green' } else { 'DarkGray' }
        Write-Host "  [$state] $($prop.Name)" -ForegroundColor $color
    }
    Write-Host "`n  Enabled: $totalEnabled | Disabled: $totalDisabled | Token impact: ~${totalEnabled} MCPs consuming context" -ForegroundColor Cyan
}

Write-Host ""
