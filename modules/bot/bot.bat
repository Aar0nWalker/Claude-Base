@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "PROJECT_NAME={{PROJECT_NAME}} Worker Bot"
title %PROJECT_NAME%

where wsl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] WSL is not installed or not available in PATH.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%i in (`wsl wslpath -a "%CD%"`) do set "WSL_PROJECT_DIR=%%i"
if "%WSL_PROJECT_DIR%"=="" (
    echo [ERROR] Could not resolve project path in WSL.
    pause
    exit /b 1
)

:menu
cls
echo ==========================================
echo %PROJECT_NAME%
echo ==========================================
echo.
echo 1^) Start bot
echo 2^) Stop bot
echo 3^) Restart bot
echo 4^) Status
echo 5^) Queue
echo 6^) Logs
echo 7^) Exit
echo.
choice /c 1234567 /n /m "Select action [1-7]: "
set "choice=%errorlevel%"

if "%choice%"=="1" goto start_bot
if "%choice%"=="2" goto stop_bot
if "%choice%"=="3" goto restart_bot
if "%choice%"=="4" goto status_bot
if "%choice%"=="5" goto queue_bot
if "%choice%"=="6" goto logs_bot
if "%choice%"=="7" goto end

:start_bot
echo.
echo Starting worker bot...
wsl bash -lc "cd '%WSL_PROJECT_DIR%' && ./scripts/start-worker-bot.sh"
echo.
pause
goto menu

:stop_bot
echo.
echo Stopping worker bot...
wsl bash -lc "cd '%WSL_PROJECT_DIR%' && ./scripts/stop-worker-bot.sh"
echo.
pause
goto menu

:restart_bot
echo.
echo Restarting worker bot...
wsl bash -lc "cd '%WSL_PROJECT_DIR%' && ./scripts/stop-worker-bot.sh; ./scripts/start-worker-bot.sh"
echo.
pause
goto menu

:status_bot
echo.
echo Checking worker bot...
wsl bash -lc "cd '%WSL_PROJECT_DIR%' && ./scripts/worker-bot.sh check && docker compose --profile worker-bot ps worker-bot && if [ -f .agents/worker-bot/dispatcher.pid ]; then ps -fp \$(cat .agents/worker-bot/dispatcher.pid); else echo 'Dispatcher pid not found'; fi"
echo.
pause
goto menu

:queue_bot
echo.
echo Worker bot queue...
wsl bash -lc "cd '%WSL_PROJECT_DIR%' && ./scripts/worker-bot.sh queue"
echo.
pause
goto menu

:logs_bot
echo.
echo Worker bot logs. Press Ctrl+C to stop watching logs.
wsl bash -lc "cd '%WSL_PROJECT_DIR%' && docker compose --profile worker-bot logs -f worker-bot"
echo.
pause
goto menu

:end
endlocal
