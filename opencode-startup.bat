@echo off
REM OpenCode + oh-my-opencode startup script for perfume-chem workspace

set "NODE_DIR=C:\Program Files\nodejs"
set "GH_DIR=C:\Program Files\GitHub CLI"
set "VENV_DIR=%~dp0.venv"
set "PATH=%NODE_DIR%;%GH_DIR%;%VENV_DIR%\Scripts;%PATH%"

echo Perfume-Chem Environment Startup
echo ================================
echo.

echo Checking for Node.js...
"%NODE_DIR%\node.exe" --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ✗ Node.js not found. Installing via winget...
    winget install OpenJS.NodeJS --accept-source-agreements --accept-package-agreements
) else (
    for /f "tokens=*" %%v in ('"%NODE_DIR%\node.exe" --version') do echo ✓ Node.js %%v
)

echo Checking for npm...
"%NODE_DIR%\npm.cmd" --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ✗ npm not found.
) else (
    for /f "tokens=*" %%v in ('"%NODE_DIR%\npm.cmd" --version') do echo ✓ npm %%v
)

echo Checking for OpenCode CLI...
if not exist "%APPDATA%\npm\lildax.cmd" (
    echo Installing @opencode-ai/cli...
    "%NODE_DIR%\npm.cmd" install -g @opencode-ai/cli
)
echo ✓ OpenCode CLI (lildax) ready

echo Checking for oh-my-opencode...
if not exist "%APPDATA%\npm\node_modules\oh-my-opencode" (
    echo Installing oh-my-opencode...
    "%NODE_DIR%\npm.cmd" install -g oh-my-opencode
    "%APPDATA%\npm\oh-my-opencode.cmd" install --no-tui --platform=opencode --claude=no --openai=no --gemini=no --copilot=yes --opencode-zen=no --skip-auth
)
echo ✓ oh-my-opencode ready

echo Checking Python virtual environment...
if exist "%VENV_DIR%\Scripts\python.exe" (
    for /f "tokens=*" %%v in ('"%VENV_DIR%\Scripts\python.exe" --version') do echo ✓ %%v
) else (
    echo ✗ .venv not found.
)

REM Copy node.exe to npm dir for wrapper compatibility
if not exist "%APPDATA%\npm\node.exe" copy "%NODE_DIR%\node.exe" "%APPDATA%\npm\node.exe" >nul

REM Create opencode.cmd wrapper if missing
if not exist "%APPDATA%\npm\opencode.cmd" (
    copy "%APPDATA%\npm\lildax.cmd" "%APPDATA%\npm\opencode.cmd" >nul
)

echo.
echo ============================================
echo Environment Ready!
echo ============================================
echo.
echo Quick commands:
echo   oh-my-opencode --help
echo   omo run ^<message^>
echo   lildax serve
echo.
pause
