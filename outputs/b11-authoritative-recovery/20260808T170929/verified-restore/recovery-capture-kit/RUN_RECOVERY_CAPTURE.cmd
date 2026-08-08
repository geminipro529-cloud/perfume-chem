@echo off
setlocal
cd /d "%~dp0"
echo.
echo Perfume-Chem lossless recovery capture
echo Close Excel, VS Code, Codex, Git clients, and any process writing to Downloads or the repository.
echo Use a private destination on another drive with enough free space.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Capture-PerfumeChemRecovery.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo Capture stopped with exit code %EXITCODE%.
  echo Read the latest logs in the recovery destination before retrying.
) else (
  echo Capture completed successfully.
)
pause
exit /b %EXITCODE%
