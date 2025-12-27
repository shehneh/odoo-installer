#!/usr/bin/env python3
"""Build a protected, compact release package for the offline installer.

Features:
- Compile Python to an executable (.exe) using Nuitka
- Compress large folders with 7z (LZMA2)
- Generate a self-extracting first-run flow (via batch scripts)

Usage:
    python build_release.py [--no-compile] [--no-compress] [--pyinstaller] [--test]
"""

import os
import sys
import shutil
import subprocess
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
import json

# ============ Settings ============
PROJECT_NAME = "OdooInstaller"
VERSION = "1.0.0"
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")
RELEASE_DIR = Path("release")


def _force_utf8_stdio() -> None:
    """Best-effort: force UTF-8 stdio to reduce garbled console output on Windows."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Main Python entrypoints to compile
MAIN_FILES = [
    "ui_server.py",
]

# Extra Python modules to include
INCLUDE_MODULES = [
    "license_manager.py",
    "admin_config.py",
    "database_manager.py",
    "payment_config.py",
]

# Web folders to copy
WEB_FOLDERS = [
    "web",
]

# Large folders to compress separately
LARGE_FOLDERS = [
    ("offline", "offline.7z"),
    ("soft", "soft.7z"),
]

# Extra files to copy
EXTRA_FILES = [
    "installer_config.json",
    "start_ui.bat",
    "README.md",
    "payment_config.py",  # Payment gateway configuration
    # Optional: if present, bundle a standalone 7-Zip CLI for extraction on customer machines
    "7za.exe",
]

# 7z compression settings
COMPRESSION_LEVEL = 9  # 0-9 (9 = maximum)
COMPRESSION_METHOD = "LZMA2"


def print_header(text):
    """Print a simple section header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(step, text):
    """Print a numbered step."""
    print(f"[{step}] {text}")


def print_success(text):
    """Print a success message."""
    print(f"  [OK] {text}")


def print_error(text):
    """Print an error message."""
    print(f"  [ERR] {text}")


def get_folder_size(path):
    """Compute folder size in bytes."""
    total = 0
    for entry in Path(path).rglob('*'):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def format_size(size):
    """Format a byte size into a human-friendly string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def check_dependencies():
    """Detect optional build tools.

    Returns:
        (seven_zip_path, have_nuitka, have_pyinstaller)
    """
    print_step(1, "Checking dependencies...")

    # Detect Nuitka
    have_nuitka = False
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"], capture_output=True, text=True
        )
        have_nuitka = result.returncode == 0
    except Exception:
        have_nuitka = False

    if have_nuitka:
        print_success("Nuitka: available")
    else:
        print_error("Nuitka: not found")

    # Detect PyInstaller
    have_pyinstaller = False
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, text=True
        )
        have_pyinstaller = result.returncode == 0
    except Exception:
        have_pyinstaller = False

    if have_pyinstaller:
        print_success("PyInstaller: available")
    else:
        print_error("PyInstaller: not found")

    # Detect 7-Zip (accept: SEVENZIP env, local 7za.exe, installed 7z.exe, PATH)
    env_sevenzip = os.environ.get("SEVENZIP")
    seven_zip_paths = [
        env_sevenzip,
        str(Path("7za.exe").resolve()) if Path("7za.exe").exists() else None,
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        shutil.which("7z"),
    ]

    seven_zip = None
    for path in seven_zip_paths:
        if path and Path(path).exists():
            seven_zip = path
            break

    if seven_zip:
        print_success(f"7-Zip: {seven_zip}")
    else:
        print_error("7-Zip: not found")

    return seven_zip, have_nuitka, have_pyinstaller


def clean_build():
    """Remove previous build artifacts and recreate output folders."""
    print_step(2, "Cleaning previous artifacts...")
    
    for folder in [BUILD_DIR, DIST_DIR, RELEASE_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
            print_success(f"Removed {folder}")
    
    # Create directories
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    RELEASE_DIR.mkdir(exist_ok=True)


def compile_with_nuitka():
    """Compile entrypoints with Nuitka."""
    print_step(3, "Compiling Python to EXE (Nuitka)...")
    
    for main_file in MAIN_FILES:
        if not Path(main_file).exists():
            print_error(f"Missing file: {main_file}")
            continue
        
        print(f"  -> Compiling {main_file}...")
        
        # Nuitka command with protection options
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",                    # Create standalone distribution
            "--onefile",                       # Single file output
            "--windows-disable-console",      # No console window (comment for debugging)
            "--windows-icon-from-ico=web/favicon.ico" if Path("web/favicon.ico").exists() else "",
            f"--output-dir={DIST_DIR}",
            "--remove-output",                # Remove build artifacts
            "--assume-yes-for-downloads",     # Auto download dependencies
            # Protection options:
            "--lto=yes",                      # Link time optimization
            "--python-flag=no_site",          # Don't include site-packages
            "--python-flag=no_warnings",      # Disable warnings
            "--python-flag=-O",               # Optimize
            # Include modules
            *[f"--include-module={m.replace('.py', '')}" for m in INCLUDE_MODULES if Path(m).exists()],
            main_file
        ]
        
        # Remove empty strings
        cmd = [c for c in cmd if c]
        
        try:
            # Stream output for live monitoring
            result = subprocess.run(cmd)
            if result.returncode == 0:
                print_success(f"Compiled: {main_file}")
            else:
                print_error(f"Compilation failed (exit code {result.returncode}).")
                return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False
    
    return True


def compile_with_pyinstaller():
    """Compile entrypoints with PyInstaller (fallback)."""
    print_step(3, "Compiling with PyInstaller...")

    # NOTE: PyInstaller removed bytecode encryption (--key) in v6.0.
    # Keep compatibility with older versions when available.
    pyinstaller_key_arg = []
    try:
        from PyInstaller import __version__ as _pyi_version  # type: ignore

        major = int(str(_pyi_version).split(".")[0])
        if major < 6:
            import secrets

            encryption_key = secrets.token_hex(8)
            pyinstaller_key_arg = [f"--key={encryption_key}"]
    except Exception:
        pyinstaller_key_arg = []
    
    for main_file in MAIN_FILES:
        if not Path(main_file).exists():
            print_error(f"Missing file: {main_file}")
            continue
        
        print(f"  -> Compiling {main_file}...")
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            # Keep console window so server logs are visible and process stays alive
            # "--noconsole",
            *pyinstaller_key_arg,
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            "--clean",
            *[f"--add-data={m};." for m in INCLUDE_MODULES if Path(m).exists()],
            main_file
        ]
        
        try:
            # Stream output for live monitoring
            result = subprocess.run(cmd)
            if result.returncode == 0:
                print_success(f"Compiled: {main_file}")
            else:
                print_error(f"PyInstaller failed (exit code {result.returncode}).")
                return False
        except Exception:
            print_error("PyInstaller is not available. Install: pip install pyinstaller")
            return False
    
    return True


def compress_large_folders(seven_zip):
    """Compress large folders using 7-Zip."""
    print_step(4, "Compressing large folders (7z)...")
    
    for folder, archive_name in LARGE_FOLDERS:
        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"  [WARN] Missing folder '{folder}', skipping")
            continue
        
        original_size = get_folder_size(folder_path)
        print(f"  -> Compressing {folder} ({format_size(original_size)})...")
        
        archive_path = RELEASE_DIR / archive_name
        
        # 7z command with ultra compression
        cmd = [
            seven_zip,
            "a",                              # Add
            "-t7z",                           # 7z format
            f"-mx={COMPRESSION_LEVEL}",       # Compression level
            f"-m0={COMPRESSION_METHOD}",      # Method
            "-ms=on",                         # Solid archive
            "-mmt=on",                        # Multi-threading
            "-bsp1",                           # Show percent progress
            "-mfb=273",                       # Fast bytes
            "-md=64m",                        # Dictionary size
            str(archive_path),
            str(folder_path / "*"),
        ]
        
        try:
            result = subprocess.run(cmd)
            if result.returncode == 0:
                compressed_size = archive_path.stat().st_size
                ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                print_success(f"{archive_name}: {format_size(original_size)} -> {format_size(compressed_size)} ({ratio:.1f}% smaller)")
            else:
                print_error(f"Compression failed for: {folder}")
        except Exception as e:
            print_error(f"Error: {e}")


def copy_web_files():
    """Copy web assets into the release folder."""
    print_step(5, "Copying web files...")
    
    for folder in WEB_FOLDERS:
        src = Path(folder)
        dst = RELEASE_DIR / folder
        if src.exists():
            shutil.copytree(src, dst)
            print_success(f"Copied: {folder}")


def copy_extra_files():
    """Copy extra files into the release folder."""
    print_step(6, "Copying extra files...")
    
    for file in EXTRA_FILES:
        src = Path(file)
        if src.exists():
            shutil.copy2(src, RELEASE_DIR / file)
            print_success(f"Copied: {file}")


def create_extractor():
    """Create the first-run extractor batch script."""
    print_step(7, "Creating extractor script...")
    
    extractor_code = '''@echo off
title Odoo Installer - Extracting Files...
echo.
echo ============================================================
echo   Extracting bundled files...
echo ============================================================
echo.

:: Check if 7z exists
if exist "%~dp0\\7za.exe" (
    set "SEVENZIP=%~dp0\\7za.exe"
) else if exist "C:\\Program Files\\7-Zip\\7z.exe" (
    set "SEVENZIP=C:\\Program Files\\7-Zip\\7z.exe"
) else if exist "C:\\Program Files (x86)\\7-Zip\\7z.exe" (
    set "SEVENZIP=C:\\Program Files (x86)\\7-Zip\\7z.exe"
) else (
    echo [ERR] 7-Zip not found. Please install 7-Zip.
    pause
    exit /b 1
)

:: Extract offline.7z
if exist "%~dp0\\offline.7z" (
    if not exist "%~dp0\\offline" (
        echo Extracting offline.7z ...
        "%SEVENZIP%" x "%~dp0\\offline.7z" -o"%~dp0\\offline" -y >nul
        echo [OK] offline extracted
    )
)

:: Extract soft.7z
if exist "%~dp0\\soft.7z" (
    if not exist "%~dp0\\soft" (
        echo Extracting soft.7z ...
        "%SEVENZIP%" x "%~dp0\\soft.7z" -o"%~dp0\\soft" -y >nul
        echo [OK] soft extracted
    )
)

echo.
echo [OK] Extraction finished
echo.
'''
    
    with open(RELEASE_DIR / "extract_files.bat", "w", encoding="utf-8") as f:
        f.write(extractor_code)
    
    print_success("Created: extract_files.bat")


def create_launcher():
    """Create the main launcher batch script."""
    print_step(8, "Creating launcher...")
    
    launcher_code = '''@echo off
title Odoo Offline Installer
cd /d "%~dp0"

:: Check if files need extraction
if exist "offline.7z" (
    if not exist "offline" (
        echo Preparing files for first run...
        call extract_files.bat
    )
)

:: Start the server
if exist "ui_server.exe" (
    start "" "ui_server.exe"
) else if exist "ui_server.py" (
    python ui_server.py
) else (
    echo [ERR] Executable not found.
    pause
    exit /b 1
)

:: Wait a moment then open browser
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000"
'''
    
    with open(RELEASE_DIR / "OdooInstaller.bat", "w", encoding="utf-8") as f:
        f.write(launcher_code)
    
    print_success("Created: OdooInstaller.bat")


def create_build_info():
    """Write build metadata."""
    info = {
        "name": PROJECT_NAME,
        "version": VERSION,
        "build_date": datetime.now().isoformat(),
        "build_type": "protected",
        "python_version": sys.version,
    }
    
    with open(RELEASE_DIR / "build_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)


def create_final_package(seven_zip):
    """Create a final single archive of the release directory."""
    print_step(9, "Creating final package...")
    
    # Calculate total size
    total_size = get_folder_size(RELEASE_DIR)
    
    # Create final archive
    timestamp = datetime.now().strftime("%Y%m%d")
    final_name = f"{PROJECT_NAME}_v{VERSION}_{timestamp}.7z"
    final_path = Path(final_name)
    
    cmd = [
        seven_zip,
        "a",
        "-t7z",
        f"-mx={COMPRESSION_LEVEL}",
        f"-m0={COMPRESSION_METHOD}",
        "-ms=on",
        "-mmt=on",
        "-bsp1",
        str(final_path),
        str(RELEASE_DIR / "*"),
    ]
    
    result = subprocess.run(cmd)
    if result.returncode == 0:
        final_size = final_path.stat().st_size
        print_success(f"Final package: {final_name}")
        print_success(f"Size: {format_size(final_size)}")
    else:
        print_error("Failed to create final package")


def main():
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description="Build protected release")
    parser.add_argument("--no-compile", action="store_true", help="Skip compilation")
    parser.add_argument("--no-compress", action="store_true", help="Skip compression")
    parser.add_argument("--pyinstaller", action="store_true", help="Use PyInstaller instead of Nuitka")
    parser.add_argument("--test", action="store_true", help="Test mode (skip large operations)")
    args = parser.parse_args()
    
    print_header("Odoo Installer - Build Release")
    print(f"Version: {VERSION}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Check dependencies
    seven_zip, have_nuitka, have_pyinstaller = check_dependencies()

    if not args.test:
        missing_required = []

        # Compilation tool requirements
        if not args.no_compile:
            if args.pyinstaller:
                if not have_pyinstaller:
                    missing_required.append("pyinstaller")
            else:
                # Prefer Nuitka, but allow fallback to PyInstaller
                if not (have_nuitka or have_pyinstaller):
                    missing_required.append("nuitka-or-pyinstaller")

        # Compression tool requirements
        if not args.no_compress:
            if not seven_zip:
                missing_required.append("7-zip")

        if missing_required:
            print("\n[ERR] Missing required build dependencies:")
            for dep in missing_required:
                print(f"  - {dep}")
            print("\nInstall options:")
            print("  - Nuitka:      pip install nuitka ordered-set zstandard")
            print("  - PyInstaller: pip install pyinstaller")
            print("  - 7-Zip:       https://7-zip.org  (or put 7za.exe next to build_release.py)")
            return 1
    
    # Clean
    clean_build()
    
    # Compile
    if not args.no_compile and not args.test:
        if args.pyinstaller or not have_nuitka:
            if not compile_with_pyinstaller():
                return 1
        else:
            if not compile_with_nuitka():
                if have_pyinstaller:
                    print("  -> Falling back to PyInstaller...")
                    if not compile_with_pyinstaller():
                        return 1
                else:
                    return 1
        
        # Copy compiled exe to release
        for exe in DIST_DIR.glob("*.exe"):
            shutil.copy2(exe, RELEASE_DIR / exe.name)
            print_success(f"Copied: {exe.name} -> release")
    
    # Compress large folders
    if not args.no_compress and not args.test and seven_zip:
        compress_large_folders(seven_zip)
    
    # Copy web files
    copy_web_files()
    
    # Copy extra files
    copy_extra_files()
    
    # Create extractor
    create_extractor()
    
    # Create launcher
    create_launcher()
    
    # Create build info
    create_build_info()
    
    # Create final package
    if seven_zip and not args.test:
        create_final_package(seven_zip)
    
    print_header("Build finished")
    print(f"Output folder: {RELEASE_DIR.absolute()}")
    
    # Show summary
    if RELEASE_DIR.exists():
        total = get_folder_size(RELEASE_DIR)
        print(f"Total size: {format_size(total)}")
        print("\nGenerated files:")
        for f in sorted(RELEASE_DIR.iterdir()):
            size = f.stat().st_size if f.is_file() else get_folder_size(f)
            print(f"  - {f.name}: {format_size(size)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
