# OpenCode + oh-my-opencode startup script for perfume-chem workspace
# PowerShell version

Write-Host "Perfume-Chem Environment Startup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$RepoRoot = Split-Path $MyInvocation.MyCommand.Definition -Parent
$NodeDir = "C:\Program Files\nodejs"
$GhDir = "C:\Program Files\GitHub CLI"
$VenvDir = Join-Path $RepoRoot ".venv"
$OmoDir = "$env:APPDATA\npm\node_modules\oh-my-opencode"

# Fix PATH for this session
$env:PATH = "$NodeDir;$GhDir;$VenvDir\Scripts;$env:PATH"

# Check Node.js
Write-Host "Checking for Node.js..." -ForegroundColor Yellow
$nodeVer = & "$NodeDir\node.exe" --version 2>$null
if (-not $nodeVer) {
    Write-Host "✗ Node.js not found. Installing via winget..." -ForegroundColor Red
    & winget install OpenJS.NodeJS --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "✓ Node.js $nodeVer" -ForegroundColor Green
}

# Check npm
Write-Host "Checking for npm..." -ForegroundColor Yellow
$npmVer = & "$NodeDir\npm.cmd" --version 2>$null
if (-not $npmVer) {
    Write-Host "✗ npm not found." -ForegroundColor Red
} else {
    Write-Host "✓ npm $npmVer" -ForegroundColor Green
}

# Check/install opencode CLI (lildax)
Write-Host "Checking for OpenCode CLI..." -ForegroundColor Yellow
$opencodeBin = "$env:APPDATA\npm\lildax.cmd"
if (-not (Test-Path $opencodeBin)) {
    Write-Host "Installing @opencode-ai/cli..." -ForegroundColor Yellow
    & "$NodeDir\npm.cmd" install -g @opencode-ai/cli
}
Write-Host "✓ OpenCode CLI (lildax) ready" -ForegroundColor Green

# Check/install oh-my-opencode
Write-Host "Checking for oh-my-opencode..." -ForegroundColor Yellow
if (-not (Test-Path $OmoDir)) {
    Write-Host "Installing oh-my-opencode..." -ForegroundColor Yellow
    & "$NodeDir\npm.cmd" install -g oh-my-opencode
    & "$env:APPDATA\npm\oh-my-opencode.cmd" install --no-tui --platform=opencode --claude=no --openai=no --gemini=no --copilot=yes --opencode-zen=no --skip-auth
}
Write-Host "✓ oh-my-opencode ready" -ForegroundColor Green

# Activate Python virtual environment
Write-Host "Activating Python virtual environment..." -ForegroundColor Yellow
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
if (Test-Path $venvPython) {
    $pyVer = & $venvPython --version 2>$null
    Write-Host "✓ Python $pyVer" -ForegroundColor Green
} else {
    Write-Host "✗ .venv not found. Run: python -m venv .venv" -ForegroundColor Red
}

# Copy node.exe to npm dir for CLI wrapper compatibility
if (-not (Test-Path "$env:APPDATA\npm\node.exe")) {
    Copy-Item "$NodeDir\node.exe" "$env:APPDATA\npm\node.exe" -Force
}
# Create opencode.cmd wrapper if missing
if (-not (Test-Path "$env:APPDATA\npm\opencode.cmd")) {
    Copy-Item "$env:APPDATA\npm\lildax.cmd" "$env:APPDATA\npm\opencode.cmd" -Force
    Copy-Item "$env:APPDATA\npm\lildax.ps1" "$env:APPDATA\npm\opencode.ps1" -Force
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "Environment Ready!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Cyan
Write-Host "  oh-my-opencode --help     OpenCode agent harness" -ForegroundColor White
Write-Host "  omo run <message>          Run with todo/task enforcement" -ForegroundColor White
Write-Host "  lildax serve               Start OpenCode v2 API server" -ForegroundColor White
Write-Host "  .venv\Scripts\python.exe   Python (engine + backend)" -ForegroundColor White
Write-Host ""
Write-Host "Pipeline:" -ForegroundColor Cyan
Write-Host "  python scripts/formula_release_gate.py --formula-file <path> --expected-concentrate-ul <ul> --brief <family> --json" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
