@echo off
chcp 65001 >nul
title Build Protected Odoo Installer
cd /d "%~dp0"

:: Force UTF-8 output for Python (helps avoid garbled text)
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo.
echo ============================================================
echo   Building protected + compressed Odoo Installer
echo ============================================================
echo.

:: Ensure 7-Zip CLI exists (download portable 7za.exe if missing)
echo.
echo [0/2] Ensuring 7-Zip CLI...
echo.

if exist "%~dp0\7za.exe" (
    echo [OK] Found local 7za.exe
) else if exist "C:\Program Files\7-Zip\7z.exe" (
    echo [OK] Found installed 7-Zip
) else if exist "C:\Program Files (x86)\7-Zip\7z.exe" (
    echo [OK] Found installed 7-Zip
) else (
    echo [INFO] 7-Zip not found. Downloading portable 7za.exe to .\soft\7zip ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root='%~dp0'.TrimEnd('\\'); $soft=Join-Path $root 'soft\\7zip'; New-Item -ItemType Directory -Force -Path $soft | Out-Null; $pkg=Join-Path $soft '7zip.commandline.nupkg'; if (!(Test-Path $pkg)) { Invoke-WebRequest -Uri 'https://www.nuget.org/api/v2/package/7-Zip.CommandLine' -OutFile $pkg; }; $extract=Join-Path $soft 'pkg'; if (Test-Path $extract) { Remove-Item -Recurse -Force $extract; }; Expand-Archive -Path $pkg -DestinationPath $extract -Force; $exe=Join-Path $extract 'tools\\7za.exe'; if (!(Test-Path $exe)) { throw '7za.exe not found in downloaded package.' }; Copy-Item $exe -Destination (Join-Path $root '7za.exe') -Force; Write-Host '[OK] Downloaded and installed local 7za.exe'"
    if errorlevel 1 (
        echo [ERR] Failed to download portable 7za.exe.
        echo       Install 7-Zip from https://7-zip.org or place 7za.exe next to this BAT.
        pause
        exit /b 1
    )
)

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Python not found on PATH.
    pause
    exit /b 1
)

:: Install dependencies (show progress)
echo.
echo [1/2] Installing build dependencies (may take a few minutes)...
echo.
python -m pip install --upgrade pip
python -m pip install nuitka ordered-set zstandard pyinstaller

:: Run build script
echo.
echo [2/2] Starting build...
echo.
python build_release.py %*
set BUILD_EXIT=%ERRORLEVEL%

if not "%BUILD_EXIT%"=="0" (
    echo.
    echo [ERR] Build failed with exit code %BUILD_EXIT%.
    echo.
    pause
    exit /b %BUILD_EXIT%
)

echo.
echo ============================================================
echo   Build finished successfully
echo ============================================================
echo   Output: .\release
echo   Run on target PC: release\OdooInstaller.bat
echo.

echo Opening output folder...
start "" "%~dp0release"

pause
