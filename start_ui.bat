@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ============================================================
rem  Odoo 19 Offline Installer - Startup Script
rem  This script checks for Python and installs it if needed
rem ============================================================

pushd "%~dp0"

echo.
echo ═══════════════════════════════════════════════════════════
echo   Odoo 19 Offline Installer - Starting...
echo ═══════════════════════════════════════════════════════════
echo.

rem ============================================================
rem  STEP 1: Check if Python is installed
rem ============================================================
echo [1/3] Checking for Python installation...

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
    if "%PYTHON_FOUND%"=="0" if exist %%P (
        set "PY=%%~P"
        set "PYTHON_FOUND=1"
    )
)

rem Try python command
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if "%PYTHON_FOUND%"=="0" (
            set "PY=%%i"
            set "PYTHON_FOUND=1"
        )
    )
)

:python_check_done

if "%PYTHON_FOUND%"=="1" echo [OK] Python found: %PY%
if "%PYTHON_FOUND%"=="1" goto :start_server

rem ============================================================
rem  STEP 2: Python not found - Install from offline folder
rem ============================================================
echo.
echo [!] Python is NOT installed on this system.
echo [!] Starting offline Python installation...
echo.

rem Find Python installer in offline folder
set "PYTHON_INSTALLER="
for %%F in ("%~dp0offline\python\python*.exe") do (
    set "PYTHON_INSTALLER=%%F"
)

if not defined PYTHON_INSTALLER (
    echo [ERROR] No Python installer found in offline\python folder!
    echo [ERROR] Please download Python installer and place it in:
    echo         %~dp0offline\python\
    echo.
    pause
    exit /b 1
)

echo [*] Found installer: %PYTHON_INSTALLER%
echo [*] Installing Python...
echo [*] Please follow the installation wizard.
echo.

rem Run Python installer - Show installation UI so user can see progress
rem InstallAllUsers=1 - Install for all users
rem PrependPath=1 - Add Python to PATH
start /wait "" "%PYTHON_INSTALLER%" InstallAllUsers=1 PrependPath=1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python installation may have failed!
    echo [ERROR] Please try installing Python manually.
    pause
    exit /b 1
)

echo.
echo [*] Python installation completed. Verifying...

rem Wait a moment for installation to register
timeout /t 3 /nobreak >nul

rem Re-check for Python
set "PYTHON_FOUND=0"
for %%P in (
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if "%PYTHON_FOUND%"=="0" if exist %%P (
        set "PY=%%~P"
        set "PYTHON_FOUND=1"
    )
)

:verify_done

if "%PYTHON_FOUND%"=="0" (
    echo [ERROR] Python installation verification failed!
    echo [ERROR] Please restart this script or install Python manually.
    pause
    exit /b 1
)

echo [OK] Python successfully installed: %PY%
echo.

rem ============================================================
rem  STEP 3: Start the UI Server
rem ============================================================
:start_server

echo [2/3] Starting UI server...
echo [*] Using Python: %PY%
echo.

rem ============================================================
rem  Optional: Ensure cryptography is available for signed license files
rem ============================================================
"%PY%" -c "import cryptography" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%~dp0offline\wheels" (
        echo [*] Installing required package (offline): cryptography
        "%PY%" -m pip --disable-pip-version-check --no-input install --no-index --find-links "%~dp0offline\wheels" cryptography
    )
)

rem Start the UI server in a new window
start "Odoo UI Server" "%PY%" "%~dp0ui_server.py"

rem Wait for server to start
echo [3/3] Waiting for server to start...
timeout /t 2 /nobreak >nul

rem Open browser
echo [*] Opening browser...
start "" "http://127.0.0.1:5000"

echo.
echo ═══════════════════════════════════════════════════════════
echo   Odoo 19 Installer UI is now running!
echo   
echo   Browser: http://127.0.0.1:5000
echo   
echo   Close the "Odoo UI Server" window to stop the server.
echo ═══════════════════════════════════════════════════════════
echo.

popd
endlocal
exit /b 0
