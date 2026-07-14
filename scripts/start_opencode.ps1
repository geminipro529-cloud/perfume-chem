param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$OpenCodeArgs
)

$ErrorActionPreference = 'Stop'

# OpenCode keeps its mutable state under the XDG directories on Windows.
# In this environment, the default user profile locations are not always writable,
# so we pin the runtime data/cache/state paths into D:\tmp.
$xdgConfigHome = 'D:\tmp\xdg'
$xdgDataHome = 'D:\tmp\opencode-data'
$xdgCacheHome = 'D:\tmp\opencode-cache'
$xdgStateHome = 'D:\tmp\opencode-state'
$tmpDir = 'D:\tmp\opencode-tmp'

foreach ($path in @($xdgConfigHome, $xdgDataHome, $xdgCacheHome, $xdgStateHome, $tmpDir)) {
  New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$env:XDG_CONFIG_HOME = $xdgConfigHome
$env:XDG_DATA_HOME = $xdgDataHome
$env:XDG_CACHE_HOME = $xdgCacheHome
$env:XDG_STATE_HOME = $xdgStateHome
$env:TMPDIR = $tmpDir

& opencode @OpenCodeArgs
exit $LASTEXITCODE
