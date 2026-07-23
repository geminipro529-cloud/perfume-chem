param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$OpenCodeArgs
)

$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\scripts\start_opencode.ps1" @OpenCodeArgs
exit $LASTEXITCODE
