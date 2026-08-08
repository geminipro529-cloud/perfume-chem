@echo off
setlocal
cd /d "%~dp0"
echo.
set /p CAPTUREROOT=Enter the full path to PerfumeChem_Recovery_YYYYMMDD_HHMMSS: 
if "%CAPTUREROOT%"=="" (
  echo No capture path entered.
  pause
  exit /b 2
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Verify-PerfumeChemRecovery.ps1" -CaptureRoot "%CAPTUREROOT%"
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo Verification failed. Read 04_MANIFESTS\VERIFICATION_REPORT.json.
) else (
  echo Verification passed.
)
pause
exit /b %EXITCODE%
