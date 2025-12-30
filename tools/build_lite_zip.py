#!/usr/bin/env python3
"""Build the lightweight (online) installer ZIP for website downloads.

This ZIP intentionally excludes large offline payloads (offline/, offline_packages/, soft/).
It bundles only the local UI + scripts needed to download/install dependencies at runtime.

Output is placed under: website/private_downloads/installers/
"""

from __future__ import annotations

import argparse
import hashlib
import os
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def should_exclude(rel: str, exclude_files: set = None) -> bool:
    rel = rel.replace("\\", "/")
    excluded_prefixes = (
        ".git/",
        ".venv/",
        "offline/",
        "offline_packages/",
        "soft/",
        "__pycache__/",
        "website/",
    )
    if rel.startswith(excluded_prefixes):
        return True
    # don't ship logs/cache
    if rel.endswith((".log", ".pyc")):
        return True
    # explicit file exclusions (e.g., private key)
    if exclude_files:
        basename = rel.rsplit("/", 1)[-1]
        if basename in exclude_files:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root (folder that contains ui_server.py)",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[1] / "private_downloads" / "installers" / "odoo19-lite-online.zip"),
        help="Output zip path",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    include_paths = [
        "ui_server.py",
        # Note: ui_server.exe excluded from lite-online to keep size small (~130KB vs 12MB)
        # Users will use Python directly via start_ui_online.bat
        "license_manager.py",
        "database_manager.py",
        "user_manager.py",
        "payment_config.py",
        "admin_config.py",
        "installer_config.json",
        "README.md",
        "LICENSE_README.md",
        "CHANGELOG.md",
        "check_status.ps1",
        "create_postgres_role.ps1",
        "install_wkhtmltopdf.ps1",
        "auto_fetch_and_setup.ps1",
        "start_ui_online.bat",
        # v2 license verification (public key only, NEVER ship private key)
        "license_public_key.pem",
        "web",
        "scripts",
    ]

    # SECURITY: Never include private key in distribution
    exclude_files = {
        "license_private_key.pem",
        ".license",
        ".license_v2.json",
        ".license_db.json",
        ".license_blacklist.json",
    }

    files_to_add: list[tuple[Path, str]] = []

    for p in include_paths:
        src = (root / p).resolve()
        if not src.exists():
            continue
        if src.is_file():
            rel = src.relative_to(root).as_posix()
            if not should_exclude(rel, exclude_files):
                files_to_add.append((src, rel))
        else:
            for f in src.rglob("*"):
                if not f.is_file():
                    continue
                rel = f.relative_to(root).as_posix()
                if should_exclude(rel, exclude_files):
                    continue
                files_to_add.append((f, rel))

    # deterministic-ish ordering
    files_to_add.sort(key=lambda t: t[1])

    # Special handling: 
    # 1. ui_server.exe should be in app/, not release/
    # 2. All files except start_ui_online.bat go inside 'app/' subfolder
    final_files: list[tuple[Path, str]] = []
    for src, rel in files_to_add:
        # Fix release/ path for exe
        if rel.startswith("release/"):
            rel = rel.replace("release/", "")
        
        # start_ui_online.bat stays at root, everything else goes in app/
        if rel == "start_ui_online.bat":
            final_files.append((src, rel))
        else:
            final_files.append((src, f"app/{rel}"))
    
    files_to_add = final_files

    # write zip
    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, rel in files_to_add:
            z.write(src, rel)

    print(f"OK: wrote {out}")
    print(f"SHA256: {sha256_file(out)}")
    print(f"Size: {out.stat().st_size / (1024*1024):.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
