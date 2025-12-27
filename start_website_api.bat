@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ============================================================
rem  OdooMaster Website API Server - Startup Script
rem  Runs the online sales/licensing API on http://127.0.0.1:5001
rem ============================================================

pushd "%~dp0"

echo.
echo ═══════════════════════════════════════════════════════════
echo   OdooMaster Website API Server - Starting...
echo ═══════════════════════════════════════════════════════════
echo.

set "PYTHON_FOUND=0"
set "PY="

rem Check for venv first
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
    set "PYTHON_FOUND=1"
    goto :python_check_done
)

rem Check common Python locations
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
) do (
    if exist %%P (
        set "PY=%%~P"
        set "PYTHON_FOUND=1"
        goto :python_check_done
    )
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        set "PY=%%i"
        set "PYTHON_FOUND=1"
        goto :python_check_done
    )
)

:python_check_done

if "%PYTHON_FOUND%"=="0" (
    echo [ERROR] Python not found!
    echo [ERROR] Please install Python 3.10+ first.
    pause
    exit /b 1
)

echo [OK] Python found: %PY%
echo.

rem ============================================================
rem  Check/Install Flask dependencies
rem ============================================================
echo [*] Checking dependencies...

"%PY%" -c "import flask" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing Flask and dependencies...
    "%PY%" -m pip --disable-pip-version-check --no-input install flask flask-cors cryptography
)

rem ============================================================
rem  Start the API server
rem ============================================================
echo.
echo [*] Starting API server...
echo [*] URL: http://127.0.0.1:5001
echo [*] Press Ctrl+C to stop
echo.
echo ═══════════════════════════════════════════════════════════
echo.

"%PY%" "%~dp0website\api\server.py"

echo.
echo [!] API server stopped.
pause

