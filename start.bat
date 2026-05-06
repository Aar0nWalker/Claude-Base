@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

rem ── TODO: project settings ────────────────────────────────────────────────────
set "PROJECT_NAME=[Project Name]"
set "HEALTH_CHECK_URL=http://localhost:8000/health"
rem ─────────────────────────────────────────────────────────────────────────────

title %PROJECT_NAME% - Docker Control
set "DOCKER_BUILDKIT=1"
set "COMPOSE_DOCKER_CLI_BUILD=1"

:menu
cls
echo ==========================================
echo   %PROJECT_NAME% - Docker Menu
echo ==========================================
echo.
echo 1^) Start project
echo 2^) Stop project
echo 3^) Restart project
echo 4^) Rebuild project
echo 5^) Logs
echo 6^) Cleanup project
echo 7^) Exit
echo.
choice /c 1234567 /n /m "Select action [1-7]: "
set "choice=%errorlevel%"

if "%choice%"=="1" goto start_project
if "%choice%"=="2" goto stop_project
if "%choice%"=="3" goto restart_project
if "%choice%"=="4" goto rebuild_project
if "%choice%"=="5" goto logs_menu
if "%choice%"=="6" goto cleanup_project
if "%choice%"=="7" goto end

:start_project
echo.
echo Starting project...
docker compose up -d
echo.
goto end

:stop_project
echo.
echo Stopping project...
docker compose down --remove-orphans
echo.
goto end

:restart_project
echo.
echo Restarting project...
docker compose down --remove-orphans
docker compose up -d
echo.
goto end

:rebuild_project
echo.
echo Rebuilding images...
docker compose down --remove-orphans
docker compose build
if errorlevel 1 (
    echo.
    echo Build failed. Fix errors above and try again.
    goto end
)
echo.
docker compose up -d
echo.
echo Waiting for API to be healthy...
:wait_healthy
docker compose exec api python -c "import urllib.request; urllib.request.urlopen('%HEALTH_CHECK_URL%')" >nul 2>&1
if errorlevel 1 (
    timeout /t 3 /nobreak >nul
    goto wait_healthy
)
echo API is ready.
echo.
echo Running tests...
docker compose exec api sh -c "pytest --tb=short -q"
if errorlevel 1 (
    echo.
    echo [WARNING] Some tests failed. Check output above.
    echo Press any key to continue anyway, or Ctrl+C to abort.
    pause >nul
)
rem TODO: uncomment if project has a seed script
rem echo Seeding database...
rem docker compose exec api python seed.py
echo.
goto end

:logs_menu
cls
echo ==========================================
echo   Logs  ^(Ctrl+C to stop^)
echo ==========================================
echo.
rem TODO: adjust service names to match your docker-compose.yml
echo 1^) All services
echo 2^) API
echo 3^) Web
echo 4^) DB
echo 5^) Redis
echo 6^) Back
echo.
choice /c 123456 /n /m "Select logs [1-6]: "
set "log_choice=%errorlevel%"

if "%log_choice%"=="1" docker compose logs -f
if "%log_choice%"=="2" docker compose logs -f api
if "%log_choice%"=="3" docker compose logs -f web
if "%log_choice%"=="4" docker compose logs -f db
if "%log_choice%"=="5" docker compose logs -f redis
if "%log_choice%"=="6" goto menu
goto end

:cleanup_project
cls
echo ==========================================
echo   CLEANUP PROJECT
echo ==========================================
echo.
echo  Removes: containers, volumes, networks,
echo  project images AND all dangling images.
echo  ALL DATABASE DATA WILL BE LOST.
echo.
choice /c YN /n /m "Continue? [Y/N]: "
if errorlevel 2 goto menu

echo.
echo [1/3] Removing containers, volumes, networks, project images...
docker compose down --remove-orphans -v --rmi local

echo.
echo [2/3] Removing dangling images...
for /f "tokens=*" %%i in ('docker images -f "dangling=true" -q') do docker rmi %%i 2>nul

echo.
echo [3/3] Removing unused volumes...
docker volume prune -f

echo.
echo Done. All project data removed.
goto end

:end
endlocal
exit /b 0
