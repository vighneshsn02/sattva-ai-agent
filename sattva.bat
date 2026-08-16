@echo off
setlocal
cd /d "%~dp0"

if "%1"=="" goto menu
python sattva.py %*
goto end

:menu
cls
echo ========================================================
echo       SATTVA AI AGENT — Local AI Coding Assistant
echo ========================================================
echo.
echo   1. Launch Interactive CLI
echo   2. Launch Web UI (Browser)
echo   3. Scan Codebase
echo   4. List Installed Ollama Models
echo   5. Exit
echo.
set /p choice="Select an option [1-5]: "

if "%choice%"=="1" python sattva.py cli
if "%choice%"=="2" python sattva.py web
if "%choice%"=="3" python sattva.py scan & pause
if "%choice%"=="4" python sattva.py models & pause
if "%choice%"=="5" goto end

:end
