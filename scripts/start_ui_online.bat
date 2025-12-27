@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ============================================================
rem  OdooMaster Online Bootstrapper - Startup Script
rem  هدف: اجرای UI محلی + نصب Python در صورت نیاز (آنلاین + fallback)
rem ============================================================

pushd "%~dp0"

echo.
echo ═══════════════════════════════════════════════════════════
echo   OdooMaster Online Installer - Starting...
echo ═══════════════════════════════════════════════════════════
echo.

rem ============================================================
rem  FAST PATH: If compiled EXE exists, run it (no Python needed)
rem ============================================================
if exist "%~dp0ui_server.exe" (
    echo [1/3] Found compiled UI server: ui_server.exe
    echo [2/3] Starting local UI server...
    start "OdooMaster UI Server" "%~dp0ui_server.exe"
    echo [3/3] Opening browser...
    rem The server may fall back to another port if 5000 is busy.
    rem Probe 5000-5020 and open the first listening port.
    timeout /t 2 /nobreak >nul
    set "FOUND_PORT="
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$found=$null; for($p=5000; $p -le 5020; $p++){ try { $c=New-Object Net.Sockets.TcpClient; $iar=$c.BeginConnect('127.0.0.1',$p,$null,$null); if($iar.AsyncWaitHandle.WaitOne(250)){ $c.EndConnect($iar); $c.Close(); $found=$p; break } } catch {} }; if($found){ Write-Output $found }"`) do set "FOUND_PORT=%%P"
    if not "%FOUND_PORT%"=="" (
        start "" "http://127.0.0.1:%FOUND_PORT%"
    ) else (
        start "" "http://127.0.0.1:5000"
    )
    echo.
    echo ═══════════════════════════════════════════════════════════
    echo   Local Installer UI is running
    echo   http://127.0.0.1:5000
    echo ═══════════════════════════════════════════════════════════
    echo.
    popd
    endlocal
    exit /b 0
)

rem ---- Config (optional) ----
set "PYTHON_OFFICIAL_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
rem اگر خواستی fallback خودت رو فعال کنی، اینو ست کن (مثال):
rem set "PYTHON_FALLBACK_URL=https://YOURDOMAIN/downloads/installers/python-3.11.9-amd64.exe"
set "PYTHON_FALLBACK_URL=%PYTHON_FALLBACK_URL%"

set "TMP_DIR=%TEMP%\odoomaster_bootstrap"
if not exist "%TMP_DIR%" mkdir "%TMP_DIR%" >nul 2>&1
set "PYTHON_INSTALLER=%TMP_DIR%\python-3.11.9-amd64.exe"

rem ============================================================
rem  STEP 1: Check if Python is installed
rem ============================================================
echo [1/3] Checking for Python installation...

set "PYTHON_FOUND=0"
set "PY="

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

rem ============================================================
rem  STEP 2: Python not found - Try offline then online download
rem ============================================================
echo.
echo [!] Python is NOT installed.
echo [*] Installing Python...
echo.

set "LOCAL_OFFLINE_PY="
for %%F in ("%~dp0offline\python\python*.exe") do (
    set "LOCAL_OFFLINE_PY=%%~F"
)

if defined LOCAL_OFFLINE_PY (
    echo [*] Found offline installer: %LOCAL_OFFLINE_PY%
    start /wait "" "%LOCAL_OFFLINE_PY%" InstallAllUsers=1 PrependPath=1
    goto :verify_python
)

echo [*] Offline installer not found. Downloading from official source...
echo     %PYTHON_OFFICIAL_URL%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%PYTHON_OFFICIAL_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing } catch { exit 1 }" >nul 2>&1
if exist "%PYTHON_INSTALLER%" (
    echo [OK] Downloaded Python installer to: %PYTHON_INSTALLER%
    start /wait "" "%PYTHON_INSTALLER%" InstallAllUsers=1 PrependPath=1
    goto :verify_python
)

if not "%PYTHON_FALLBACK_URL%"=="" (
    echo [!] Official download failed. Trying fallback URL...
    echo     %PYTHON_FALLBACK_URL%
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%PYTHON_FALLBACK_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing } catch { exit 1 }" >nul 2>&1
    if exist "%PYTHON_INSTALLER%" (
        echo [OK] Downloaded Python installer (fallback) to: %PYTHON_INSTALLER%
        start /wait "" "%PYTHON_INSTALLER%" InstallAllUsers=1 PrependPath=1
        goto :verify_python
    )
)

echo [ERROR] Python installer could not be downloaded.
echo [ERROR] Please install Python 3.11 manually and run again.
echo.
pause
exit /b 1

:verify_python

echo.
echo [*] Verifying Python installation...

timeout /t 3 /nobreak >nul

set "PYTHON_FOUND=0"
set "PY="

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        set "PY=%%i"
        set "PYTHON_FOUND=1"
        goto :verify_done
    )
)

:verify_done

if "%PYTHON_FOUND%"=="0" (
    echo [ERROR] Python installation verification failed.
    pause
    exit /b 1
)

echo [OK] Python ready: %PY%

rem ============================================================
rem  STEP 3: Start local UI server
rem ============================================================
:start_server

echo.
echo [2/3] Starting local UI server...
echo [*] Using Python: %PY%
echo.

if not exist "%~dp0ui_server.py" (
    echo [ERROR] ui_server.py not found next to installer package.
    pause
    exit /b 1
)

start "OdooMaster UI Server" "%PY%" "%~dp0ui_server.py"

echo [3/3] Opening browser...
rem The server will also try to open the browser itself.
timeout /t 2 /nobreak >nul
set "FOUND_PORT="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$found=$null; for($p=5000; $p -le 5020; $p++){ try { $c=New-Object Net.Sockets.TcpClient; $iar=$c.BeginConnect('127.0.0.1',$p,$null,$null); if($iar.AsyncWaitHandle.WaitOne(250)){ $c.EndConnect($iar); $c.Close(); $found=$p; break } } catch {} }; if($found){ Write-Output $found }"`) do set "FOUND_PORT=%%P"
if not "%FOUND_PORT%"=="" (
    start "" "http://127.0.0.1:%FOUND_PORT%"
) else (
    start "" "http://127.0.0.1:5000"
)

echo.
echo ═══════════════════════════════════════════════════════════
echo   Local Installer UI is running
echo   http://127.0.0.1:5000
echo ═══════════════════════════════════════════════════════════
echo.

popd
endlocal
exit /b 0
