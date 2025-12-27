@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ============================================================
rem  Odoo Installer - Online (Lite) Startup Script
rem  - Ensures Python exists (downloads from official if missing)
rem  - Starts ui_server.py locally on http://127.0.0.1:5000
rem ============================================================

pushd "%~dp0"

echo.
echo ═══════════════════════════════════════════════════════════
echo   Odoo Installer (Lite - Online) - Starting...
echo ═══════════════════════════════════════════════════════════
echo.

set "PYTHON_FOUND=0"
set "PY="

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
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
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

if "%PYTHON_FOUND%"=="1" (
    echo [OK] Python found: %PY%
    goto :start_server
)

echo.
echo [!] Python is NOT installed on this system.
echo [*] Downloading Python installer (official) ...
echo.

set "PY_VER=3.11.9"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe"
set "PY_EXE=%TEMP%\python-%PY_VER%-amd64.exe"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_EXE%'" 
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to download Python from python.org
    echo [ERROR] URL: %PY_URL%
    echo.
    pause
    exit /b 1
)

echo [*] Running Python installer...
echo [*] Please follow the installation wizard.
echo.

start /wait "" "%PY_EXE%" InstallAllUsers=1 PrependPath=1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python installation may have failed!
    pause
    exit /b 1
)

rem Re-check python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found after install.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    set "PY=%%i"
    goto :start_server
)

:start_server

echo.
echo [*] Starting local UI server...
echo [*] URL: http://127.0.0.1:5000
echo.

rem ============================================================
rem  STEP: Ensure cryptography is installed (needed for signed license files)
rem ============================================================
"%PY%" -c "import cryptography" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required package: cryptography
    "%PY%" -m pip --disable-pip-version-check --no-input install cryptography
)

"%PY%" "%~dp0ui_server.py"

echo.
echo [!] UI server exited.
pause
