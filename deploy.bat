@echo off

rem ── TODO: project settings ────────────────────────────────────────────────────
rem Path to WinSCP CLI (adjust to your install location)
set "WINSCP_PATH=C:\Program Files (x86)\WinSCP\WinSCP.com"
rem WinSCP script file (sits next to this bat)
set "WINSCP_SCRIPT=%~dp0deploy.winscp"
rem ─────────────────────────────────────────────────────────────────────────────

set "LOG_FILE=%~dp0deploy.log"
del "%LOG_FILE%" 2>nul

echo [1/2] Uploading files...
"%WINSCP_PATH%" /script="%WINSCP_SCRIPT%" /log="%LOG_FILE%" /console
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Deploy failed. See deploy.log for details.
    exit /b 1
)

echo.
echo [OK] Deploy complete.
