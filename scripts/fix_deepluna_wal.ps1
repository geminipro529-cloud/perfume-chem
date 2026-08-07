$ErrorActionPreference = 'Stop'
$dbDir = 'D:\chatbots\perfume-chem\.deepluna-home\projects\perfume-chem\daemon-v2'
foreach ($f in 'scheduler.sqlite3-wal','scheduler.sqlite3-shm') {
  $p = Join-Path $dbDir $f
  for ($i=0; $i -lt 6; $i++) {
    if (-not (Test-Path -LiteralPath $p)) { Write-Host "$f removed"; break }
    try { Remove-Item -LiteralPath $p -Force -ErrorAction Stop; Write-Host "Removed $f"; break }
    catch { Write-Host "Retry $($i+1) for ${f}: $($_.Exception.Message)"; Start-Sleep -Milliseconds 800 }
  }
}
Write-Host 'Starting daemon...'
& 'C:\Program Files\nodejs\node.exe' 'C:\Users\ASUS\.codex\tools\opencode-deepseek-mcp\server.mjs' --daemon --project-id=perfume-chem
