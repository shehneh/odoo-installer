#!/usr/bin/env python3
"""
Lightweight local web UI for Odoo offline installer status and controls.
No external Python packages required.
"""
import http.server
import socketserver
import os
import json
import urllib.parse
import subprocess
import threading
import socket
import time
import winreg
import platform
import struct
import tempfile
import hashlib
import hmac
import base64
import uuid
import sys
import webbrowser
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import json

# Import license manager
try:
    from license_manager import check_license, activate_license, deactivate_license, get_license_info, get_hardware_id, generate_license_key
    LICENSE_ENABLED = True
except ImportError:
    LICENSE_ENABLED = False
    print("⚠️  License manager not found - running in unlicensed mode")

# Import admin config
try:
    from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD, JWT_SECRET, SESSION_TIMEOUT
except ImportError:
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "odoo@2025"
    JWT_SECRET = "DefaultJWTSecretKey2025"
    SESSION_TIMEOUT = 86400



def _get_base_dir() -> Path:
    """Return the directory that contains the app's sidecar files.

    When compiled (PyInstaller/Nuitka), __file__ can point to a temp extraction
    directory. We want the directory of the launched executable so we can read
    sibling folders like ./web, ./offline, ./soft.
    """
    try:
        if getattr(sys, "frozen", False):
            return Path(sys.argv[0]).resolve().parent
    except Exception:
        pass

    try:
        argv0 = Path(sys.argv[0]).resolve()
        if argv0.suffix.lower() == ".exe" and argv0.exists():
            return argv0.parent
    except Exception:
        pass

    return Path(__file__).resolve().parent


BASE = _get_base_dir()
OFFLINE = BASE / 'offline'
SOFT = BASE / 'soft'
LOG = BASE / 'fetch_setup.log'
TEMP_DIR = Path(tempfile.gettempdir()) / 'odoo_setup_scripts'
CONFIG_FILE = BASE / 'installer_config.json'
LICENSE_DB_FILE = BASE / '.license_db.json'

PORT = int(os.environ.get('PORT', 5000))


# ============ ADMIN AUTH ============
def create_admin_token(username: str) -> str:
    """Create a JWT-like token for admin authentication."""
    expiry = (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).timestamp()
    data = f"{username}:{expiry}"
    signature = hmac.new(JWT_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    token = base64.b64encode(f"{data}:{signature}".encode()).decode()
    return token


def verify_admin_token(token: str) -> tuple:
    """Verify admin token. Returns (is_valid, username)."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.split(':')
        if len(parts) != 3:
            return False, None
        
        username, expiry_str, signature = parts
        expiry = float(expiry_str)
        
        # Check expiry
        if datetime.now().timestamp() > expiry:
            return False, None
        
        # Verify signature
        data = f"{username}:{expiry_str}"
        expected_sig = hmac.new(JWT_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
        
        if signature != expected_sig:
            return False, None
        
        return True, username
    except Exception:
        return False, None


# ============ LICENSE DATABASE ============
def load_license_db() -> dict:
    """Load license database from file."""
    default_db = {
        'licenses': [],
        'stats': {
            'total': 0,
            'active': 0,
            'expired': 0,
            'devices': 0
        }
    }
    try:
        if LICENSE_DB_FILE.exists():
            with open(LICENSE_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default_db


def save_license_db(db: dict) -> bool:
    """Save license database to file."""
    try:
        with open(LICENSE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def add_license_to_db(license_data: dict) -> bool:
    """Add a new license to database."""
    db = load_license_db()
    db['licenses'].insert(0, license_data)  # Add to beginning
    db['stats']['total'] = len(db['licenses'])
    
    # Count unique devices
    devices = set(lic['hardware_id'] for lic in db['licenses'])
    db['stats']['devices'] = len(devices)
    
    # Count active/expired
    now = datetime.now()
    active = 0
    expired = 0
    for lic in db['licenses']:
        if lic.get('validity_hours') == -1:
            active += 1  # Unlimited
        else:
            try:
                expiry = datetime.fromisoformat(lic['expiry_iso'])
                if now < expiry:
                    active += 1
                else:
                    expired += 1
            except:
                pass
    
    db['stats']['active'] = active
    db['stats']['expired'] = expired
    
    return save_license_db(db)


# ============ PENDING PAYMENTS ============
PENDING_PAYMENTS_FILE = BASE / '.pending_payments.json'
SALES_LOG_FILE = BASE / '.sales_log.json'

def load_pending_payments() -> dict:
    """Load pending payments from file."""
    try:
        if PENDING_PAYMENTS_FILE.exists():
            with open(PENDING_PAYMENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_pending_payments(payments: dict) -> bool:
    """Save pending payments to file."""
    try:
        with open(PENDING_PAYMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(payments, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# ============ PLANS MANAGEMENT ============
PLANS_FILE = BASE / '.plans.json'

DEFAULT_PLANS = [
    {
        'id': 'starter',
        'name': 'پلن پایه',
        'hours': 720,
        'hours_display': '۳۰ روز',
        'price': 290000,
        'price_display': '۲۹۰,۰۰۰ تومان',
        'features': ['پشتیبانی از یک دستگاه', 'آپدیت رایگان', 'پشتیبانی تلگرامی'],
        'is_popular': False,
        'is_active': True,
        'order': 1
    },
    {
        'id': 'professional',
        'name': 'پلن حرفه‌ای',
        'hours': 4320,
        'hours_display': '۶ ماه',
        'price': 790000,
        'price_display': '۷۹۰,۰۰۰ تومان',
        'features': ['پشتیبانی از یک دستگاه', 'آپدیت رایگان', 'پشتیبانی تلگرامی', 'پشتیبانی تلفنی'],
        'is_popular': True,
        'is_active': True,
        'order': 2
    },
    {
        'id': 'unlimited',
        'name': 'پلن نامحدود',
        'hours': -1,
        'hours_display': 'نامحدود',
        'price': 1990000,
        'price_display': '۱,۹۹۰,۰۰۰ تومان',
        'features': ['پشتیبانی از یک دستگاه', 'آپدیت رایگان مادام‌العمر', 'پشتیبانی تلگرامی', 'پشتیبانی تلفنی', 'نصب حضوری'],
        'is_popular': False,
        'is_active': True,
        'order': 3
    }
]

def load_plans() -> list:
    """Load plans from file or return defaults."""
    try:
        if PLANS_FILE.exists():
            with open(PLANS_FILE, 'r', encoding='utf-8') as f:
                plans = json.load(f)
                # Only return active plans for public view
                return sorted([p for p in plans if p.get('is_active', True)], 
                             key=lambda x: x.get('order', 999))
    except Exception:
        pass
    return DEFAULT_PLANS

def load_all_plans() -> list:
    """Load all plans including inactive ones (for admin)."""
    try:
        if PLANS_FILE.exists():
            with open(PLANS_FILE, 'r', encoding='utf-8') as f:
                return sorted(json.load(f), key=lambda x: x.get('order', 999))
    except Exception:
        pass
    return DEFAULT_PLANS

def save_plans(plans: list) -> bool:
    """Save plans to file."""
    try:
        with open(PLANS_FILE, 'w', encoding='utf-8') as f:
            json.dump(plans, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def get_plan_by_id(plan_id: str) -> dict:
    """Get a plan by its ID."""
    plans = load_all_plans()
    for plan in plans:
        if plan['id'] == plan_id:
            return plan
    return None


def log_sale(payment_info: dict, license_data: dict, ref_id: str) -> None:
    """Log a successful sale."""
    try:
        sales = []
        if SALES_LOG_FILE.exists():
            with open(SALES_LOG_FILE, 'r', encoding='utf-8') as f:
                sales = json.load(f)
        
        sales.insert(0, {
            'ref_id': ref_id,
            'hardware_id': payment_info['hardware_id'],
            'plan_id': payment_info['plan_id'],
            'amount': payment_info['amount'],
            'user_id': payment_info.get('user_id', ''),
            'customer_name': payment_info.get('customer_name', ''),
            'customer_email': payment_info.get('customer_email', ''),
            'customer_phone': payment_info.get('customer_phone', ''),
            'license_key': license_data['license_key'],
            'validity_text': license_data.get('validity_text', ''),
            'sold_at': datetime.now().isoformat()
        })
        
        with open(SALES_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(sales, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Import database manager
try:
    from database_manager import (
        create_customer, get_customer, list_customers, update_customer, delete_customer,
        create_license as db_create_license, get_license, list_licenses as db_list_licenses,
        get_licenses_by_customer, revoke_license, record_activation,
        get_stats as db_get_stats, get_dashboard_data, search_customers, search_licenses
    )
    DATABASE_ENABLED = True
except ImportError:
    DATABASE_ENABLED = False
    print("⚠️  Database manager not found")


def _get_private_key_path() -> Path:
    """Get the path to the private key for license signing."""
    return _get_base_dir() / 'license_private_key.pem'

def _sign_license_v2(license_data: dict) -> str:
    """Sign license data using RSA-PSS and return base64-encoded signature."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        
        private_key_path = _get_private_key_path()
        if not private_key_path.exists():
            raise FileNotFoundError(f"Private key not found: {private_key_path}")
        
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        # Create canonical JSON (sorted keys, no whitespace after separators)
        # MUST match _canonical_json_bytes in license_manager.py
        data_to_sign = json.dumps(license_data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        
        # Sign with RSA-PSS
        signature = private_key.sign(
            data_to_sign,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('ascii')
    except ImportError:
        raise RuntimeError("cryptography package is required for v2 license signing")

def generate_license_with_hours(hardware_id: str, validity_hours: int, 
                                 customer_id: str = None, price: float = 0,
                                 customer_name: str = '', user_id: str = None) -> dict:
    """Generate a v2 signed license with specific validity in hours."""
    import secrets
    
    if validity_hours == -1:
        # Unlimited - set expiry to 100 years from now
        expiry_dt = datetime.now() + timedelta(days=365*100)
        validity_text = "نامحدود"
    else:
        expiry_dt = datetime.now() + timedelta(hours=validity_hours)
        
        # Format validity text
        if validity_hours < 24:
            validity_text = f"{validity_hours} ساعت"
        elif validity_hours < 720:
            days = validity_hours // 24
            validity_text = f"{days} روز"
        elif validity_hours < 8760:
            months = validity_hours // 720
            validity_text = f"{months} ماه"
        else:
            years = validity_hours // 8760
            validity_text = f"{years} سال"
    
    expiry_date = expiry_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate unique license ID
    license_id = f"LIC-{uuid.uuid4().hex[:12].upper()}"
    
    # Create license payload for signing
    license_payload = {
        'v': 2,
        'license_id': license_id,
        'plan': validity_text,
        'issued_to': customer_name or 'Customer',
        'hardware_id': hardware_id,
        'expires_at': expiry_dt.isoformat(),
        'issued_at': datetime.now().isoformat(),
        'nonce': secrets.token_hex(16)
    }
    
    # Sign the license
    try:
        signature = _sign_license_v2(license_payload)
        license_payload['sig'] = signature
        
        # Create the license file content (base64-encoded JSON bundle)
        license_bundle = base64.b64encode(
            json.dumps(license_payload, ensure_ascii=False).encode('utf-8')
        ).decode('ascii')
        
    except Exception as e:
        # Fallback to legacy HMAC if signing fails (no private key)
        print(f"⚠️  V2 signing failed, using legacy HMAC: {e}")
        from license_manager import SECRET_KEY
        data = f"{hardware_id}:{expiry_date}"
        signature = hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()[:16]
        license_bundle = base64.b64encode(f"{data}:{signature}".encode()).decode()
        license_payload = None  # Mark as legacy
    
    result = {
        'license_key': license_bundle,
        'license_id': license_id if license_payload else None,
        'license_v2': license_payload is not None,
        'license_bundle': license_payload,  # Full v2 payload for .oml file download
        'hardware_id': hardware_id,
        'validity_hours': validity_hours,
        'validity_text': validity_text,
        'expiry_date': expiry_date,
        'expiry_iso': expiry_dt.isoformat(),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'is_expired': False
    }
    
    # Save to database if enabled
    if DATABASE_ENABLED:
        db_record = db_create_license(
            hardware_id=hardware_id,
            validity_hours=validity_hours,
            customer_id=customer_id,
            license_key=license_bundle,
            price=price,
            customer_name=customer_name,
            user_id=user_id
        )
        result['id'] = db_record['id']
        result['customer_id'] = customer_id
        result['customer_name'] = customer_name
        result['user_id'] = user_id
    
    return result


# ============ SETTINGS MANAGEMENT ============
def load_settings() -> dict:
    """Load settings from config file."""
    default_settings = {
        'odoo_path': '',
        'postgres_password': 'odoo',
        'odoo_port': 8069,
        'postgres_port': 5432,
    }
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                default_settings.update(saved)
    except Exception:
        pass
    return default_settings


def save_settings(settings: dict) -> bool:
    """Save settings to config file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def get_system_info():
    """Get Windows version and architecture info."""
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'os_release': platform.release(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'is_64bit': struct.calcsize('P') * 8 == 64,
        'arch': 'x64' if struct.calcsize('P') * 8 == 64 else 'x86',
        'windows_edition': '',
    }
    
    # Get Windows edition
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            info['windows_edition'] = winreg.QueryValueEx(key, "ProductName")[0]
    except Exception:
        pass
    
    return info


def get_compatible_installer(folder_name: str, prefer_arch: str = None) -> Optional[Path]:
    """Find the best compatible installer based on system architecture.
    
    Args:
        folder_name: Name of folder in soft/ directory (e.g., 'VSCode')
        prefer_arch: Preferred architecture ('x64' or 'x86'), auto-detected if None
    
    Returns:
        Path to the best matching installer, or None if not found
    """
    sys_info = get_system_info()
    arch = prefer_arch or sys_info['arch']
    
    folder = SOFT / folder_name
    if not folder.exists():
        return None
    
    # Look for installers
    exe_files = list(folder.glob('*.exe'))
    msi_files = list(folder.glob('*.msi'))
    all_installers = exe_files + msi_files
    
    if not all_installers:
        return None
    
    # Score installers based on compatibility
    def score_installer(path: Path) -> int:
        name = path.name.lower()
        score = 0
        
        # Architecture matching (higher is better)
        if arch == 'x64':
            if 'x64' in name or 'amd64' in name or '64bit' in name or '-64' in name:
                score += 100
            elif 'x86' in name or '32bit' in name or '-32' in name:
                score += 10  # Can still run on 64-bit
        else:  # x86
            if 'x86' in name or '32bit' in name or '-32' in name:
                score += 100
            elif 'x64' in name or 'amd64' in name:
                score += 0  # Cannot run on 32-bit
        
        # Prefer .exe over .zip/.rar
        if path.suffix.lower() == '.exe':
            score += 50
        elif path.suffix.lower() == '.msi':
            score += 40
        
        # Prefer larger files (usually more complete)
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            score += min(int(size_mb), 20)  # Up to 20 points for size
        except Exception:
            pass
        
        return score
    
    # Sort by score (highest first)
    all_installers.sort(key=score_installer, reverse=True)
    
    # Return best match
    best = all_installers[0] if all_installers else None
    
    # If best match is not compatible with current arch, return None
    if best and arch == 'x86':
        name = best.name.lower()
        if 'x64' in name or 'amd64' in name or '64bit' in name:
            return None  # x64 installer cannot run on x86
    
    return best


def check_software_installed(software_name: str) -> tuple[bool, str]:
    """Check if a software is installed on the system.
    
    Returns (is_installed, details)
    """
    software_name_lower = software_name.lower()
    
    # Check for VSCode
    if 'vscode' in software_name_lower or 'visual studio code' in software_name_lower:
        # Check common paths
        vscode_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Microsoft VS Code' / 'Code.exe',
            Path(r'C:\Program Files\Microsoft VS Code\Code.exe'),
            Path(r'C:\Program Files (x86)\Microsoft VS Code\Code.exe'),
        ]
        for p in vscode_paths:
            if p.exists():
                return True, str(p)
        
        # Check via registry
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            name, _ = winreg.QueryValueEx(subkey, 'DisplayName')
                            if 'Visual Studio Code' in str(name):
                                return True, name
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Check if code command exists
        code_path = shutil_which('code')
        if code_path:
            return True, code_path
        
        return False, ''
    
    # Check for WinRAR
    if 'winrar' in software_name_lower:
        winrar_paths = [
            Path(r'C:\Program Files\WinRAR\WinRAR.exe'),
            Path(r'C:\Program Files (x86)\WinRAR\WinRAR.exe'),
        ]
        for p in winrar_paths:
            if p.exists():
                return True, str(p)
        
        # Check registry
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            name, _ = winreg.QueryValueEx(subkey, 'DisplayName')
                            if 'WinRAR' in str(name):
                                return True, name
                    except Exception:
                        continue
        except Exception:
            pass
        
        return False, ''
    
    # Check for speedtop (likely a portable app, check if running or in common locations)
    if 'speedtop' in software_name_lower:
        # This is likely a portable app, check if it exists in soft folder
        speedtop_path = SOFT / 'speedtop.exe'
        if speedtop_path.exists():
            return True, 'موجود در پوشه soft (برنامه قابل حمل)'
        return False, ''
    
    # Check for Git
    if 'git' in software_name_lower and 'copilot' not in software_name_lower:
        git_path = shutil_which('git')
        if git_path:
            return True, git_path
        
        git_paths = [
            Path(r'C:\Program Files\Git\bin\git.exe'),
            Path(r'C:\Program Files (x86)\Git\bin\git.exe'),
        ]
        for p in git_paths:
            if p.exists():
                return True, str(p)
        
        return False, ''
    
    # Check for copilot-rtl (VS Code extension)
    if 'copilot-rtl' in software_name_lower:
        # This is a VS Code extension - check if VS Code extensions folder has it
        vscode_ext_paths = [
            Path(os.environ.get('USERPROFILE', '')) / '.vscode' / 'extensions',
        ]
        for ext_path in vscode_ext_paths:
            if ext_path.exists():
                for ext_dir in ext_path.iterdir():
                    if 'rtl' in ext_dir.name.lower():
                        return True, str(ext_dir)
        return False, 'افزونه VS Code - نیاز به نصب دستی'
    
    return False, ''


def get_download_url(software_name: str, arch: str) -> Optional[str]:
    """Get download URL for software based on architecture.
    
    Returns URL to download the appropriate version.
    """
    download_urls = {
        'VSCode': {
            'x64': 'https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user',
            'x86': 'https://code.visualstudio.com/sha/download?build=stable&os=win32-user',
        },
        'Python': {
            'x64': 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe',
            'x86': 'https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe',
        },
        'WinRAR': {
            'x64': 'https://www.win-rar.com/fileadmin/winrar-versions/winrar/winrar-x64-624.exe',
            'x86': 'https://www.win-rar.com/fileadmin/winrar-versions/winrar/wrar624.exe',
        },
        'Git': {
            'x64': 'https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe',
            'x86': 'https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-32-bit.exe',
        },
        'NodeJS': {
            'x64': 'https://nodejs.org/dist/v22.12.0/node-v22.12.0-x64.msi',
            'x86': 'https://nodejs.org/dist/v22.12.0/node-v22.12.0-x86.msi',
        },
        'PostgreSQL': {
            'x64': 'https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64.exe',
            'x86': 'https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows.exe',
        },
        'wkhtmltopdf': {
            'x64': 'https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox-0.12.6.1-3.msvc2015-win64.exe',
            'x86': 'https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox-0.12.6.1-3.msvc2015-win32.exe',
        },
    }
    
    if software_name in download_urls:
        return download_urls[software_name].get(arch)
    
    return None


def ps_sq(value: str) -> str:
    """Single-quote a value for PowerShell and escape single quotes."""
    return "'" + str(value).replace("'", "''") + "'"


def detect_odoo_version(path: Path) -> Optional[str]:
    """Detect Odoo version from folder name or source code.
    
    Returns version number (e.g. '18', '19') or None if not detected.
    """
    import re
    
    if not path:
        return None
    
    path_str = str(path)
    
    # Try to detect from folder name (e.g. 'odoo 18', 'odoo-19', 'odoo19')
    folder_name = path.name.lower()
    version_match = re.search(r'odoo[\s\-_]*(\d+)', folder_name, re.IGNORECASE)
    if version_match:
        return version_match.group(1)
    
    # Try to detect from odoo-src subfolder
    if (path / 'odoo-src').exists():
        for child in (path / 'odoo-src').iterdir():
            if child.is_dir():
                child_match = re.search(r'odoo-?(\d+)[\.\-]', child.name, re.IGNORECASE)
                if child_match:
                    return child_match.group(1)
    
    # Try to detect from release.py if exists
    release_candidates = [
        path / 'odoo-src' / 'odoo' / 'odoo' / 'release.py',
        path / 'odoo' / 'release.py',
        path / 'release.py',
    ]
    for release_file in release_candidates:
        if release_file.exists():
            try:
                content = release_file.read_text(encoding='utf-8')
                ver_match = re.search(r"version_info\s*=\s*\(\s*(\d+)", content)
                if ver_match:
                    return ver_match.group(1)
            except Exception:
                pass
    
    return None


def validate_odoo_folder(path: Path) -> dict:
    """Validate if a folder is a valid Odoo installation.
    
    Returns dict with:
    - valid: bool
    - version: str or None
    - message: str
    - has_venv: bool
    - has_source: bool
    - has_config: bool
    """
    result = {
        'valid': False,
        'version': None,
        'message': '',
        'has_venv': False,
        'has_source': False,
        'has_config': False,
    }
    
    if not path or not path.exists():
        result['message'] = 'پوشه وجود ندارد'
        return result
    
    if not path.is_dir():
        result['message'] = 'مسیر یک پوشه نیست'
        return result
    
    # Check for Odoo indicators
    has_odoo_src = (path / 'odoo-src').exists()
    has_venv = (path / 'venv').exists()
    has_config = (path / 'config').exists() or (path / 'odoo.conf').exists()
    
    # Look for odoo-bin
    odoo_bin_found = False
    odoo_bin_candidates = [
        path / 'odoo-src' / 'odoo-19.0' / 'odoo-bin',
        path / 'odoo-src' / 'odoo-18.0' / 'odoo-bin',
        path / 'odoo-src' / 'odoo-17.0' / 'odoo-bin',
        path / 'odoo-src' / 'odoo-16.0' / 'odoo-bin',
        path / 'odoo-src' / 'odoo' / 'odoo-bin',
        path / 'odoo-bin',
        path / 'odoo' / 'odoo-bin',
    ]
    for candidate in odoo_bin_candidates:
        if candidate.exists():
            odoo_bin_found = True
            break
    
    # Look for requirements.txt (another Odoo indicator)
    has_requirements = False
    req_candidates = [
        path / 'odoo-src',
        path / 'odoo',
        path,
    ]
    for req_parent in req_candidates:
        if req_parent.exists() and req_parent.is_dir():
            for item in req_parent.rglob('requirements.txt'):
                has_requirements = True
                break
    
    result['has_venv'] = has_venv
    result['has_source'] = has_odoo_src or odoo_bin_found
    result['has_config'] = has_config
    
    # Determine if it's a valid Odoo folder
    if has_odoo_src or odoo_bin_found:
        result['valid'] = True
        result['version'] = detect_odoo_version(path)
        if result['version']:
            result['message'] = f'پوشه معتبر Odoo {result["version"]} شناسایی شد'
        else:
            result['message'] = 'پوشه Odoo شناسایی شد (نسخه نامشخص)'
    elif has_requirements and 'odoo' in str(path).lower():
        # Might be a fresh installation folder
        result['valid'] = True
        result['version'] = detect_odoo_version(path)
        result['message'] = 'پوشه Odoo احتمالی شناسایی شد (منتظر نصب کامل)'
    else:
        result['message'] = 'پوشه Odoo نامعتبر است - فایل‌های ضروری یافت نشد'
    
    return result


def resolve_odoo_root() -> Optional[Path]:
    """Try to locate the odoo19 workspace folder."""
    # First check saved settings
    settings = load_settings()
    if settings.get('odoo_path'):
        custom_path = Path(settings['odoo_path'])
        if custom_path.exists():
            return custom_path
    
    # Then try common locations
    candidates = [
        (BASE.parent / 'odoo19'),
        (BASE.parent / 'odoo 19'),  # With space
        (BASE.parent / 'odoo-19'),  # With dash
        Path(r'C:\Program Files\odoo19'),
        Path(r'C:\Program Files\odoo 19'),
        Path(r'C:\odoo19'),
        Path(r'C:\odoo 19'),
    ]
    for c in candidates:
        try:
            if c and c.exists():
                # Verify it has the expected structure
                if (c / 'odoo-src').exists() or (c / 'venv').exists():
                    return c
                # Also check if odoo-bin is directly in the folder
                if (c / 'odoo-bin').exists():
                    return c
        except Exception:
            continue
    return None


def find_odoo_config(odoo_root: Optional[Path] = None) -> Optional[Path]:
    """Find the odoo.conf file in the Odoo workspace.
    
    Searches in common locations:
    - config/odoo.conf (standard structure)
    - odoo.conf (root level)
    - conf/odoo.conf
    - etc/odoo.conf
    """
    if odoo_root is None:
        odoo_root = resolve_odoo_root()
    
    if not odoo_root or not odoo_root.exists():
        return None
    
    # Common config file locations
    config_paths = [
        odoo_root / 'config' / 'odoo.conf',
        odoo_root / 'odoo.conf',
        odoo_root / 'conf' / 'odoo.conf',
        odoo_root / 'etc' / 'odoo.conf',
        odoo_root / '.odoo.conf',
    ]
    
    for cfg_path in config_paths:
        try:
            if cfg_path.exists() and cfg_path.is_file():
                return cfg_path
        except Exception:
            continue
    
    return None


def parse_odoo_config(config_path: Optional[Path] = None) -> dict:
    """Parse odoo.conf and return configuration as a dictionary.
    
    Returns a dict with keys like:
    - http_port: The HTTP port (default 8069)
    - db_host, db_port, db_user, db_password, db_name
    - addons_path
    - data_dir
    - admin_passwd
    - dbfilter
    - And other odoo.conf options
    """
    if config_path is None:
        config_path = find_odoo_config()
    
    default_config = {
        'http_port': 8069,
        'db_host': '127.0.0.1',
        'db_port': 5432,
        'db_user': 'odoo',
        'db_password': '',
        'addons_path': '',
        'data_dir': '',
        'admin_passwd': '',
        'dbfilter': '',
        'config_path': str(config_path) if config_path else '',
        'config_found': False,
    }
    
    if not config_path or not config_path.exists():
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        default_config['config_found'] = True
        
        # Parse INI-style config
        for line in content.splitlines():
            line = line.strip()
            # Skip comments and section headers
            if not line or line.startswith('#') or line.startswith(';') or line.startswith('['):
                continue
            
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                
                # Convert numeric values
                if key in ('http_port', 'db_port', 'xmlrpc_port', 'longpolling_port', 'workers', 'max_cron_threads'):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif key in ('list_db', 'proxy_mode', 'test_enable', 'without_demo'):
                    value = value.lower() in ('true', '1', 'yes')
                
                default_config[key] = value
        
        return default_config
        
    except Exception as e:
        default_config['parse_error'] = str(e)
        return default_config


def get_odoo_info() -> dict:
    """Get comprehensive information about the Odoo installation.
    
    Returns a dict with:
    - odoo_root: Path to the Odoo workspace
    - config: Parsed configuration from odoo.conf
    - http_port: The port Odoo will run on
    - venv_exists: Whether the venv exists
    - odoo_bin_exists: Whether odoo-bin exists
    - run_scripts: List of available run scripts
    - version: Detected Odoo version (from folder name or source)
    - validation: Validation result for the folder
    """
    odoo_root = resolve_odoo_root()
    config = parse_odoo_config()
    
    # Validate the odoo folder
    validation = validate_odoo_folder(odoo_root) if odoo_root else {
        'valid': False,
        'version': None,
        'message': 'پوشه Odoo انتخاب نشده',
        'has_venv': False,
        'has_source': False,
        'has_config': False,
    }
    
    info = {
        'odoo_root': str(odoo_root) if odoo_root else None,
        'config': config,
        'http_port': config.get('http_port', 8069),
        'venv_exists': False,
        'odoo_bin_exists': False,
        'odoo_bin_path': None,
        'run_scripts': [],
        'version': validation.get('version'),  # Use version from validation
        'ready_to_run': False,
        'issues': [],
        'validation': validation,  # Include validation result
    }
    
    if not odoo_root:
        info['issues'].append('پوشه Odoo پیدا نشد')
        return info
    
    if not validation['valid']:
        info['issues'].append(validation['message'])
        return info
    
    # Check venv
    venv_python = odoo_root / 'venv' / 'Scripts' / 'python.exe'
    info['venv_exists'] = venv_python.exists()
    if not info['venv_exists']:
        info['issues'].append('محیط مجازی Python (venv) ایجاد نشده')
    
    # Check odoo-bin
    odoo_bin_candidates = [
        odoo_root / 'odoo-src' / 'odoo-19.0' / 'odoo-bin',
        odoo_root / 'odoo-src' / 'odoo-18.0' / 'odoo-bin',
        odoo_root / 'odoo-src' / 'odoo-17.0' / 'odoo-bin',
        odoo_root / 'odoo-src' / 'odoo' / 'odoo-bin',
        odoo_root / 'odoo-bin',
        odoo_root / 'odoo' / 'odoo-bin',
    ]
    
    for candidate in odoo_bin_candidates:
        if candidate.exists():
            info['odoo_bin_exists'] = True
            info['odoo_bin_path'] = str(candidate)
            
            # If version not detected from folder, try from path
            if not info['version']:
                import re
                version_match = re.search(r'odoo-?(\d+)\.0', str(candidate))
                if version_match:
                    info['version'] = version_match.group(1)
            break
    
    if not info['odoo_bin_exists']:
        info['issues'].append('فایل odoo-bin پیدا نشد')
    
    # Check run scripts
    script_names = ['run_odoo.ps1', 'start_odoo.ps1', 'run_odoo.bat', 'start_odoo.bat']
    for name in script_names:
        script_path = odoo_root / name
        if script_path.exists():
            info['run_scripts'].append(str(script_path))
    
    if not info['run_scripts']:
        info['issues'].append('اسکریپت اجرای Odoo پیدا نشد')
    
    # Check if ready to run
    info['ready_to_run'] = (
        info['venv_exists'] and 
        info['odoo_bin_exists'] and 
        len(info['run_scripts']) > 0
    )
    
    return info


# ============ DEPENDENCY COMPATIBILITY CHECKER ============
import re
from typing import Tuple, List, Dict

def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string to tuple for comparison."""
    # Remove any leading/trailing whitespace and 'v' prefix
    version_str = version_str.strip().lstrip('v')
    # Extract numeric parts only
    parts = re.findall(r'\d+', version_str)
    return tuple(int(p) for p in parts) if parts else (0,)


def compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings.
    Returns: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    t1, t2 = parse_version(v1), parse_version(v2)
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    return 0


def version_satisfies(installed_version: str, required_spec: str) -> bool:
    """Check if installed version satisfies the requirement spec.
    Handles ==, >=, <=, >, <, ~= operators.
    """
    installed = parse_version(installed_version)
    
    # Parse requirement spec
    match = re.match(r'^([<>=!~]+)?(.+)$', required_spec.strip())
    if not match:
        return True
    
    operator, version = match.groups()
    operator = operator or '=='
    required = parse_version(version)
    
    if operator == '==':
        # Allow minor version differences (e.g., 2.17.0 satisfies 2.10.3)
        # For exact match, at least major.minor should match or installed should be newer
        return installed >= required
    elif operator == '>=':
        return installed >= required
    elif operator == '<=':
        return installed <= required
    elif operator == '>':
        return installed > required
    elif operator == '<':
        return installed < required
    elif operator == '!=':
        return installed != required
    elif operator == '~=':
        # Compatible release: ~=1.4.2 means >=1.4.2 and <1.5.0
        if len(required) < 2:
            return installed >= required
        return installed >= required and installed[:len(required)-1] == required[:len(required)-1]
    
    return True


def parse_requirements_file(req_path: Path) -> Dict[str, Dict]:
    """Parse a requirements.txt file and extract package requirements.
    
    Returns dict with package names as keys and requirement info as values.
    Handles conditional requirements (python_version, sys_platform).
    """
    requirements = {}
    
    if not req_path.exists():
        return requirements
    
    try:
        with open(req_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse the line
                # Format: package==version ; condition
                parts = line.split(';', 1)
                pkg_spec = parts[0].strip()
                condition = parts[1].strip() if len(parts) > 1 else ''
                
                # Extract package name and version
                match = re.match(r'^([a-zA-Z0-9_\-\.]+)\s*([<>=!~]+.+)?$', pkg_spec)
                if not match:
                    continue
                
                pkg_name = match.group(1).lower().replace('-', '_').replace('.', '_')
                version_spec = match.group(2) or ''
                
                # Check if this requirement applies to current system
                applies = True
                python_version_req = None
                platform_req = None
                
                if condition:
                    # Check python_version conditions
                    py_match = re.search(r"python_version\s*([<>=!]+)\s*['\"]?(\d+\.\d+)['\"]?", condition)
                    if py_match:
                        python_version_req = (py_match.group(1), py_match.group(2))
                    
                    # Check sys_platform conditions
                    if "sys_platform" in condition:
                        if "win32" in condition:
                            if "!=" in condition or "not" in condition.lower():
                                platform_req = 'not_windows'
                            else:
                                platform_req = 'windows'
                
                # Get current Python version
                import sys
                current_py = f"{sys.version_info.major}.{sys.version_info.minor}"
                
                # Check if requirement applies to current environment
                if python_version_req:
                    op, ver = python_version_req
                    current = parse_version(current_py)
                    required = parse_version(ver)
                    
                    if op == '>=':
                        applies = current >= required
                    elif op == '<=':
                        applies = current <= required
                    elif op == '>':
                        applies = current > required
                    elif op == '<':
                        applies = current < required
                    elif op == '==':
                        applies = current == required
                    elif op == '!=':
                        applies = current != required
                
                if platform_req:
                    is_windows = platform.system() == 'Windows'
                    if platform_req == 'windows':
                        applies = applies and is_windows
                    elif platform_req == 'not_windows':
                        applies = applies and not is_windows
                
                if applies:
                    # Store or update requirement
                    if pkg_name not in requirements:
                        requirements[pkg_name] = {
                            'name': match.group(1),
                            'version_spec': version_spec,
                            'condition': condition,
                            'python_version_req': python_version_req,
                            'platform_req': platform_req,
                        }
                    else:
                        # If same package with different conditions, keep the one that applies
                        requirements[pkg_name]['version_spec'] = version_spec
    
    except Exception as e:
        print(f"Error parsing requirements: {e}")
    
    return requirements


def parse_wheel_filename(filename: str) -> Dict:
    """Parse wheel filename to extract package info.
    
    Wheel format: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    """
    if not filename.endswith('.whl'):
        return None
    
    name = filename[:-4]  # Remove .whl
    parts = name.split('-')
    
    if len(parts) < 5:
        return None
    
    # Handle case where version might contain hyphens
    # Standard format: name-version-pytag-abi-platform
    pkg_name = parts[0].lower().replace('_', '_')
    version = parts[1]
    
    # Extract Python version and platform info
    python_tag = parts[2] if len(parts) > 2 else ''
    abi_tag = parts[3] if len(parts) > 3 else ''
    platform_tag = parts[4] if len(parts) > 4 else ''
    
    # Determine Python version compatibility
    py_versions = []
    if python_tag:
        if python_tag.startswith('cp'):
            # e.g., cp311 means Python 3.11
            match = re.match(r'cp(\d)(\d+)', python_tag)
            if match:
                py_versions.append(f"{match.group(1)}.{match.group(2)}")
        elif python_tag.startswith('py'):
            # e.g., py3 means Python 3.x, py2.py3 means both
            if 'py3' in python_tag:
                py_versions.append('3')
            if 'py2' in python_tag:
                py_versions.append('2')
    
    # Determine platform compatibility
    platforms = []
    if platform_tag:
        if 'win' in platform_tag.lower():
            if 'amd64' in platform_tag.lower() or 'x64' in platform_tag.lower():
                platforms.append('win64')
            elif 'win32' in platform_tag.lower():
                platforms.append('win32')
            else:
                platforms.append('windows')
        elif platform_tag == 'any':
            platforms.append('any')
    
    return {
        'name': pkg_name,
        'version': version,
        'python_tag': python_tag,
        'abi_tag': abi_tag,
        'platform_tag': platform_tag,
        'py_versions': py_versions,
        'platforms': platforms,
        'filename': filename,
    }


def get_available_wheels(wheels_dir: Path) -> Dict[str, List[Dict]]:
    """Get all available wheel packages grouped by package name."""
    available = {}
    
    if not wheels_dir.exists():
        return available
    
    for whl_file in wheels_dir.glob('*.whl'):
        info = parse_wheel_filename(whl_file.name)
        if info:
            pkg_name = info['name'].lower().replace('-', '_')
            if pkg_name not in available:
                available[pkg_name] = []
            info['path'] = str(whl_file)
            available[pkg_name].append(info)
    
    return available


def find_odoo_requirements(odoo_root: Path) -> Optional[Path]:
    """Find the requirements.txt file for the Odoo installation."""
    if not odoo_root or not odoo_root.exists():
        return None
    
    # Search patterns for requirements file
    patterns = [
        # Standard Odoo structure
        odoo_root / 'odoo-src' / 'odoo-19.0' / 'requirements.txt',
        odoo_root / 'odoo-src' / 'odoo-18.0' / 'requirements.txt',
        odoo_root / 'odoo-src' / 'odoo-17.0' / 'requirements.txt',
        odoo_root / 'odoo-src' / 'odoo-saas-18' / 'requirements.txt',
        odoo_root / 'odoo-src' / 'odoo' / 'requirements.txt',
        # Direct in odoo folder
        odoo_root / 'requirements.txt',
        odoo_root / 'odoo' / 'requirements.txt',
        # Packages folder
        odoo_root / 'packages' / 'requirements.txt',
    ]
    
    for p in patterns:
        if p.exists():
            return p
    
    # Try to find any requirements.txt in odoo-src
    odoo_src = odoo_root / 'odoo-src'
    if odoo_src.exists():
        for subdir in odoo_src.iterdir():
            if subdir.is_dir():
                req_file = subdir / 'requirements.txt'
                if req_file.exists():
                    return req_file
    
    return None


def check_dependency_compatibility(odoo_root: Optional[Path] = None) -> Dict:
    """Check compatibility between Odoo requirements and available offline wheels.
    
    Returns a comprehensive compatibility report.
    """
    import sys
    
    if odoo_root is None:
        odoo_root = resolve_odoo_root()
    
    result = {
        'odoo_root': str(odoo_root) if odoo_root else None,
        'requirements_file': None,
        'odoo_version': None,
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'python_version_short': f"{sys.version_info.major}.{sys.version_info.minor}",
        'platform': platform.system(),
        'arch': 'x64' if struct.calcsize('P') * 8 == 64 else 'x86',
        'wheels_dir': str(OFFLINE / 'wheels'),
        'total_requirements': 0,
        'compatible': 0,
        'incompatible': 0,
        'missing': 0,
        'newer_available': 0,
        'status': 'unknown',  # ok, warning, error
        'packages': [],
        'summary': '',
        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    if not odoo_root:
        result['status'] = 'error'
        result['summary'] = 'پوشه Odoo پیدا نشد'
        return result
    
    # Find requirements file
    req_file = find_odoo_requirements(odoo_root)
    if not req_file:
        result['status'] = 'error'
        result['summary'] = 'فایل requirements.txt پیدا نشد'
        return result
    
    result['requirements_file'] = str(req_file)
    
    # Detect Odoo version from path
    path_str = str(req_file)
    version_match = re.search(r'odoo[-_]?(\d+)[\.\-]0', path_str, re.IGNORECASE)
    if version_match:
        result['odoo_version'] = version_match.group(1)
    elif 'saas' in path_str.lower():
        saas_match = re.search(r'saas[-_]?(\d+)', path_str, re.IGNORECASE)
        if saas_match:
            result['odoo_version'] = f"saas-{saas_match.group(1)}"
    
    # Parse requirements
    requirements = parse_requirements_file(req_file)
    result['total_requirements'] = len(requirements)
    
    # Get available wheels
    wheels_dir = OFFLINE / 'wheels'
    available = get_available_wheels(wheels_dir)
    
    # Check each requirement
    for pkg_key, req_info in requirements.items():
        pkg_status = {
            'name': req_info['name'],
            'required_version': req_info['version_spec'],
            'condition': req_info.get('condition', ''),
            'installed_version': None,
            'installed_file': None,
            'status': 'missing',  # compatible, incompatible, missing, newer_available
            'message': '',
            'download_url': None,
        }
        
        # Find matching wheel
        if pkg_key in available:
            wheels = available[pkg_key]
            
            # Find best matching wheel for current Python version and platform
            best_match = None
            for whl in wheels:
                # Check Python version compatibility
                py_compat = False
                if not whl['py_versions']:
                    py_compat = True
                elif 'py3' in whl['python_tag'] or 'py2.py3' in whl['python_tag']:
                    py_compat = True
                else:
                    for pv in whl['py_versions']:
                        if result['python_version_short'].startswith(pv):
                            py_compat = True
                            break
                
                # Check platform compatibility
                plat_compat = False
                if 'any' in whl['platforms'] or not whl['platforms']:
                    plat_compat = True
                elif result['arch'] == 'x64' and ('win64' in whl['platforms'] or 'windows' in whl['platforms']):
                    plat_compat = True
                elif result['arch'] == 'x86' and 'win32' in whl['platforms']:
                    plat_compat = True
                
                if py_compat and plat_compat:
                    if best_match is None or compare_versions(whl['version'], best_match['version']) > 0:
                        best_match = whl
            
            if best_match:
                pkg_status['installed_version'] = best_match['version']
                pkg_status['installed_file'] = best_match['filename']
                
                # Compare versions
                if req_info['version_spec']:
                    required_ver = req_info['version_spec'].lstrip('=<>!~').strip()
                    cmp = compare_versions(best_match['version'], required_ver)
                    
                    if cmp >= 0:
                        # Installed version is same or newer
                        pkg_status['status'] = 'compatible'
                        if cmp > 0:
                            pkg_status['status'] = 'newer_available'
                            pkg_status['message'] = f'نسخه جدیدتر موجود: {best_match["version"]} (نیاز: {required_ver})'
                            result['newer_available'] += 1
                        else:
                            pkg_status['message'] = 'سازگار ✓'
                        result['compatible'] += 1
                    else:
                        # Installed version is older
                        pkg_status['status'] = 'incompatible'
                        pkg_status['message'] = f'نسخه قدیمی: {best_match["version"]} (نیاز: {required_ver})'
                        pkg_status['download_url'] = f'https://pypi.org/project/{req_info["name"]}/'
                        result['incompatible'] += 1
                else:
                    pkg_status['status'] = 'compatible'
                    pkg_status['message'] = 'سازگار ✓'
                    result['compatible'] += 1
            else:
                pkg_status['status'] = 'missing'
                pkg_status['message'] = 'wheel سازگار موجود نیست'
                pkg_status['download_url'] = f'https://pypi.org/project/{req_info["name"]}/'
                result['missing'] += 1
        else:
            pkg_status['status'] = 'missing'
            pkg_status['message'] = 'پکیج موجود نیست'
            pkg_status['download_url'] = f'https://pypi.org/project/{req_info["name"]}/'
            result['missing'] += 1
        
        result['packages'].append(pkg_status)
    
    # Sort packages: missing first, then incompatible, then compatible
    status_order = {'missing': 0, 'incompatible': 1, 'newer_available': 2, 'compatible': 3}
    result['packages'].sort(key=lambda x: status_order.get(x['status'], 4))
    
    # Determine overall status
    if result['missing'] > 0:
        result['status'] = 'error'
        result['summary'] = f'{result["missing"]} پکیج مفقود، {result["incompatible"]} ناسازگار'
    elif result['incompatible'] > 0:
        result['status'] = 'warning'
        result['summary'] = f'{result["incompatible"]} پکیج نیاز به بروزرسانی دارد'
    else:
        result['status'] = 'ok'
        result['summary'] = f'همه {result["compatible"]} پکیج سازگار هستند ✓'
    
    return result


def download_missing_package(package_name: str, version: str = None) -> Dict:
    """Download a missing package from PyPI.
    
    Returns download result info.
    """
    import urllib.request
    import urllib.error
    import ssl
    
    result = {
        'success': False,
        'package': package_name,
        'version': version,
        'message': '',
        'downloaded_file': None,
    }
    
    wheels_dir = OFFLINE / 'wheels'
    wheels_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use pip to download the wheel
        import sys
        python_exe = sys.executable
        
        # Build pip download command
        cmd = [
            python_exe, '-m', 'pip', 'download',
            '--only-binary=:all:',
            '--platform', 'win_amd64',
            '--python-version', f'{sys.version_info.major}.{sys.version_info.minor}',
            '-d', str(wheels_dir),
        ]
        
        if version:
            cmd.append(f'{package_name}=={version}')
        else:
            cmd.append(package_name)
        
        # Run pip download
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if proc.returncode == 0:
            result['success'] = True
            result['message'] = f'پکیج {package_name} با موفقیت دانلود شد'
            
            # Find the downloaded file
            for line in proc.stdout.split('\n'):
                if 'Saved' in line or 'Downloaded' in line:
                    match = re.search(r'[\\/]([^\\/]+\.whl)', line)
                    if match:
                        result['downloaded_file'] = match.group(1)
        else:
            result['message'] = f'خطا در دانلود: {proc.stderr[:500]}'
    
    except subprocess.TimeoutExpired:
        result['message'] = 'زمان دانلود به پایان رسید'
    except Exception as e:
        result['message'] = f'خطا: {str(e)}'
    
    return result


def run_exe_elevated(exe_path: Path, arguments: Optional[str] = None, wait: bool = False) -> int:
    exe = str(exe_path)
    if arguments is None:
        cmd = f"Start-Process -FilePath {ps_sq(exe)} -Verb RunAs" + (" -Wait" if wait else "")
    else:
        cmd = f"Start-Process -FilePath {ps_sq(exe)} -Verb RunAs" + (" -Wait" if wait else "") + f" -ArgumentList {ps_sq(arguments)}"
    p = subprocess.Popen(['powershell.exe', '-NoProfile', '-Command', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.pid


def run_powershell_elevated_file(ps1_path: Path, ps_args: Optional[list[str]] = None, wait: bool = False) -> int:
    """Start a PowerShell script elevated (UAC prompt) with visible window. Returns PID."""
    ps_args = ps_args or []
    script = str(ps1_path)
    arg_list = [
        '-NoProfile',
        '-NoExit',  # Keep window open so user can see output
        '-ExecutionPolicy', 'Bypass',
        '-File', script,
        *ps_args,
    ]
    arg_expr = '@(' + ','.join(ps_sq(a) for a in arg_list) + ')'
    cmd = f"Start-Process -FilePath 'powershell.exe' -Verb RunAs" + (" -Wait" if wait else "") + f" -ArgumentList {arg_expr}"
    p = subprocess.Popen(['powershell.exe', '-NoProfile', '-Command', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.pid


def run_powershell_elevated_file_sync(ps1_path: Path, ps_args: Optional[list[str]] = None) -> int:
    """Run a PowerShell script elevated and wait for it to finish.

    Returns the exit code of the non-elevated wrapper PowerShell process.
    """
    ps_args = ps_args or []
    script = str(ps1_path)
    arg_list = [
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', script,
        *ps_args,
    ]
    arg_expr = '@(' + ','.join(ps_sq(a) for a in arg_list) + ')'
    cmd = f"Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -ArgumentList {arg_expr}"
    r = subprocess.run(['powershell.exe', '-NoProfile', '-Command', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Avoid stale dashboard assets/API responses due to browser caching.
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        return super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # ============ OFFLINE ADMIN (REMOVED) ============
        if parsed.path.startswith('/api/admin/'):
            self.send_response(404)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Offline admin is disabled'}).encode('utf-8'))
            return
        if parsed.path in ('/admin_login.html', '/admin_dashboard.html'):
            self.send_response(404)
            self.send_header('Content-Type','text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Offline admin is disabled'.encode('utf-8'))
            return

        # ============ USER AUTH (GOOGLE OAUTH) ============
        if parsed.path == '/api/user/google/start':
            self.send_response(302)
            try:
                client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
                redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', '').strip() or 'http://127.0.0.1:5000/api/user/google/callback'
                if not client_id:
                    # Redirect back with an error
                    self.send_header('Location', '/user_login.html?err=google_not_configured')
                    self.end_headers()
                    return

                state = uuid.uuid4().hex
                # Lightweight state store
                try:
                    tmp_state_file = BASE / '.google_oauth_state.json'
                    states = []
                    if tmp_state_file.exists():
                        with open(tmp_state_file, 'r', encoding='utf-8') as f:
                            states = json.load(f) or []
                    states.insert(0, {'state': state, 'created_at': datetime.now().isoformat()})
                    states = states[:50]
                    with open(tmp_state_file, 'w', encoding='utf-8') as f:
                        json.dump(states, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

                params = {
                    'client_id': client_id,
                    'redirect_uri': redirect_uri,
                    'response_type': 'code',
                    'scope': 'openid email profile',
                    'state': state,
                    'prompt': 'select_account'
                }
                auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
                self.send_header('Location', auth_url)
            except Exception:
                self.send_header('Location', '/user_login.html?err=google_failed')
            self.end_headers()
            return

        if parsed.path == '/api/user/google/callback':
            # Exchange code for tokens and create a local user session
            q = urllib.parse.parse_qs(parsed.query)
            code = (q.get('code', ['']) or [''])[0]
            state = (q.get('state', ['']) or [''])[0]

            try:
                client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
                client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
                redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', '').strip() or 'http://127.0.0.1:5000/api/user/google/callback'
                if not client_id or not client_secret:
                    self.send_response(302)
                    self.send_header('Location', '/user_login.html?err=google_not_configured')
                    self.end_headers()
                    return

                # Verify state (best-effort)
                try:
                    tmp_state_file = BASE / '.google_oauth_state.json'
                    if tmp_state_file.exists():
                        with open(tmp_state_file, 'r', encoding='utf-8') as f:
                            states = json.load(f) or []
                        if state and not any(s.get('state') == state for s in states):
                            raise ValueError('invalid_state')
                except Exception:
                    pass

                if not code:
                    self.send_response(302)
                    self.send_header('Location', '/user_login.html?err=google_no_code')
                    self.end_headers()
                    return

                import urllib.request as urllib_request

                token_body = urllib.parse.urlencode({
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri
                }).encode('utf-8')

                req = urllib_request.Request(
                    'https://oauth2.googleapis.com/token',
                    data=token_body,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    method='POST'
                )

                with urllib_request.urlopen(req, timeout=15) as resp:
                    token_data = json.loads(resp.read().decode('utf-8'))

                access_token = token_data.get('access_token', '')
                if not access_token:
                    raise ValueError('no_access_token')

                # Fetch user info
                ui_req = urllib_request.Request(
                    'https://openidconnect.googleapis.com/v1/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'},
                    method='GET'
                )
                with urllib_request.urlopen(ui_req, timeout=15) as resp:
                    userinfo = json.loads(resp.read().decode('utf-8'))

                email = userinfo.get('email', '')
                name = userinfo.get('name', '')
                google_sub = userinfo.get('sub', '')

                from user_manager import create_or_link_google_user, public_user_view, create_user_token
                user = create_or_link_google_user(email=email, name=name, google_sub=google_sub)
                token = create_user_token(user['id'])

                # Put token in URL fragment so browser JS can store it
                self.send_response(302)
                self.send_header('Location', f"/user_dashboard.html#token={urllib.parse.quote(token)}")
                self.end_headers()
                return
            except Exception:
                self.send_response(302)
                self.send_header('Location', '/user_login.html?err=google_failed')
                self.end_headers()
                return

        # ============ USER AUTH API ============
        if parsed.path == '/api/user/me':
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            try:
                from user_manager import verify_user_token, get_user, public_user_view
                auth_header = self.headers.get('Authorization', '')
                if not auth_header.startswith('Bearer '):
                    self.wfile.write(json.dumps({'success': False, 'message': 'Unauthorized'}).encode('utf-8'))
                    return
                verified = verify_user_token(auth_header[7:])
                if not verified.is_valid:
                    self.wfile.write(json.dumps({'success': False, 'message': 'Invalid token'}).encode('utf-8'))
                    return
                user = get_user(verified.user_id)
                self.wfile.write(json.dumps({'success': True, 'user': public_user_view(user)}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({'success': False, 'message': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/api/user/purchases':
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            try:
                from user_manager import verify_user_token
                auth_header = self.headers.get('Authorization', '')
                if not auth_header.startswith('Bearer '):
                    self.wfile.write(json.dumps({'success': False, 'message': 'Unauthorized'}).encode('utf-8'))
                    return
                verified = verify_user_token(auth_header[7:])
                if not verified.is_valid:
                    self.wfile.write(json.dumps({'success': False, 'message': 'Invalid token'}).encode('utf-8'))
                    return

                purchases = []
                if SALES_LOG_FILE.exists():
                    try:
                        with open(SALES_LOG_FILE, 'r', encoding='utf-8') as f:
                            sales = json.load(f)
                        purchases = [s for s in (sales or []) if str(s.get('user_id', '')).strip() == verified.user_id]
                    except Exception:
                        purchases = []

                self.wfile.write(json.dumps({'success': True, 'purchases': purchases}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({'success': False, 'message': str(e)}).encode('utf-8'))
            return
        if parsed.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            resp = get_status()
            self.wfile.write(json.dumps(resp, default=str).encode('utf-8'))
            return
        
        if parsed.path == '/api/settings':
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            settings = load_settings()
            # Add detected odoo path if not set
            if not settings.get('odoo_path'):
                detected = resolve_odoo_root()
                settings['detected_odoo_path'] = str(detected) if detected else ''
            self.wfile.write(json.dumps(settings, default=str).encode('utf-8'))
            return
        
        if parsed.path == '/api/browse_folder':
            # Open Windows folder browser dialog using PowerShell
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            try:
                # Use PowerShell to show folder browser dialog
                ps_script = '''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.Application]::EnableVisualStyles()
                $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                $folderBrowser.Description = "پوشه Odoo را انتخاب کنید"
                $folderBrowser.ShowNewFolderButton = $true
                $folderBrowser.RootFolder = [System.Environment+SpecialFolder]::MyComputer
                
                # Create a form to be the owner and bring to front
                $form = New-Object System.Windows.Forms.Form
                $form.TopMost = $true
                $form.WindowState = [System.Windows.Forms.FormWindowState]::Minimized
                $form.Show()
                $form.Hide()
                
                $result = $folderBrowser.ShowDialog($form)
                $form.Dispose()
                
                if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                    Write-Output $folderBrowser.SelectedPath
                } else {
                    Write-Output "CANCELLED"
                }
                '''
                result = subprocess.run(
                    ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout for user to select folder
                )
                selected_path = result.stdout.strip()
                if selected_path == "CANCELLED" or not selected_path:
                    self.wfile.write(json.dumps({'path': '', 'cancelled': True}).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({'path': selected_path}).encode('utf-8'))
            except subprocess.TimeoutExpired:
                self.wfile.write(json.dumps({'error': 'زمان انتخاب پوشه به پایان رسید'}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return
        
        if parsed.path == '/api/check_install_status':
            # Check installation status by re-checking dependencies
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            resp = get_status()
            # Return just the deps status for quick polling
            self.wfile.write(json.dumps({'deps': resp['deps']}, default=str).encode('utf-8'))
            return
        
        if parsed.path == '/api/odoo_info':
            # Get comprehensive Odoo installation info including config
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            info = get_odoo_info()
            self.wfile.write(json.dumps(info, default=str).encode('utf-8'))
            return
        
        if parsed.path == '/api/validate_folder':
            # Validate if a folder is a valid Odoo installation
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            q = urllib.parse.parse_qs(parsed.query)
            folder_path = q.get('path', [None])[0]
            
            if folder_path:
                validation = validate_odoo_folder(Path(folder_path))
            else:
                validation = {
                    'valid': False,
                    'version': None,
                    'message': 'مسیر پوشه ارسال نشده',
                    'has_venv': False,
                    'has_source': False,
                    'has_config': False,
                }
            self.wfile.write(json.dumps(validation, default=str).encode('utf-8'))
            return
        
        if parsed.path == '/api/license/status':
            # Get license status
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            if not LICENSE_ENABLED:
                result = {
                    'licensed': True,  # Bypass if license system not available
                    'is_valid': True,
                    'message': 'License system disabled',
                    'hardware_id': 'N/A',
                    'is_lifetime': True,
                    'expiry_date': None,
                    'days_remaining': -1
                }
            else:
                is_licensed, message = check_license()
                result = {
                    'licensed': is_licensed,
                    'is_valid': is_licensed,
                    'message': message,
                    'hardware_id': get_hardware_id(),
                }
                if is_licensed:
                    info = get_license_info()
                    result.update(info)
            
            self.wfile.write(json.dumps(result, default=str).encode('utf-8'))
            return
        
        # ============ ADMIN GET APIs ============
        if parsed.path == '/api/admin/verify':
            # Verify admin token
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({'valid': False}).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, username = verify_admin_token(token)
            
            self.wfile.write(json.dumps({
                'valid': is_valid,
                'username': username
            }).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/stats':
            # Get license statistics
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({'error': 'Invalid token'}).encode('utf-8'))
                return
            
            db = load_license_db()
            
            # Recalculate stats
            now = datetime.now()
            active = 0
            expired = 0
            for lic in db.get('licenses', []):
                if lic.get('validity_hours') == -1:
                    active += 1
                else:
                    try:
                        expiry = datetime.fromisoformat(lic['expiry_iso'])
                        if now < expiry:
                            active += 1
                        else:
                            expired += 1
                    except:
                        pass
            
            stats = {
                'total': len(db.get('licenses', [])),
                'active': active,
                'expired': expired,
                'devices': len(set(lic['hardware_id'] for lic in db.get('licenses', [])))
            }
            
            self.wfile.write(json.dumps(stats).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/licenses':
            # Get all licenses from database
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({'error': 'Invalid token'}).encode('utf-8'))
                return
            
            if DATABASE_ENABLED:
                licenses = db_list_licenses()
            else:
                db = load_license_db()
                licenses = db.get('licenses', [])
            
            # Update is_expired flag
            now = datetime.now()
            for lic in licenses:
                if lic.get('validity_hours') == -1:
                    lic['is_expired'] = False
                    lic['status'] = 'active'
                elif lic.get('status') != 'revoked':
                    try:
                        expiry = datetime.fromisoformat(lic['expiry_iso'])
                        lic['is_expired'] = now > expiry
                        lic['status'] = 'expired' if lic['is_expired'] else 'active'
                    except:
                        lic['is_expired'] = True
                        lic['status'] = 'expired'
            
            self.wfile.write(json.dumps({'licenses': licenses}).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/customers':
            # Get all customers
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({'error': 'Invalid token'}).encode('utf-8'))
                return
            
            if DATABASE_ENABLED:
                customers = list_customers()
            else:
                customers = []
            
            self.wfile.write(json.dumps({'customers': customers}).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/dashboard':
            # Get dashboard data
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({'error': 'Invalid token'}).encode('utf-8'))
                return
            
            if DATABASE_ENABLED:
                data = get_dashboard_data()
            else:
                data = {
                    'stats': {'total_customers': 0, 'total_licenses': 0, 'active_licenses': 0, 'expired_licenses': 0, 'total_revenue': 0},
                    'recent_licenses': [],
                    'recent_customers': []
                }
            
            self.wfile.write(json.dumps(data, default=str).encode('utf-8'))
            return
        
        # ============ PLANS API ============
        if parsed.path == '/api/plans':
            # Get plans for public display (no auth required)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            plans = load_plans()
            self.wfile.write(json.dumps({'success': True, 'plans': plans}).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/plans':
            # Get all plans for admin (auth required) - includes inactive
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({'error': 'Invalid token'}).encode('utf-8'))
                return
            
            plans = load_all_plans()  # Get all plans including inactive
            self.wfile.write(json.dumps({'success': True, 'plans': plans}).encode('utf-8'))
            return
        
        if parsed.path == '/api/check_compatibility':
            # Check dependency compatibility between Odoo requirements and offline wheels
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            q = urllib.parse.parse_qs(parsed.query)
            
            # Allow specifying a custom path
            custom_path = q.get('path', [None])[0]
            if custom_path:
                odoo_root = Path(custom_path)
            else:
                odoo_root = resolve_odoo_root()
            
            result = check_dependency_compatibility(odoo_root)
            self.wfile.write(json.dumps(result, default=str).encode('utf-8'))
            return
        
        if parsed.path == '/api/download_package':
            # Download a missing package from PyPI
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            q = urllib.parse.parse_qs(parsed.query)
            
            package_name = q.get('package', [None])[0]
            version = q.get('version', [None])[0]
            
            if not package_name:
                self.wfile.write(json.dumps({'error': 'نام پکیج مشخص نشده'}).encode('utf-8'))
                return
            
            result = download_missing_package(package_name, version)
            self.wfile.write(json.dumps(result, default=str).encode('utf-8'))
            return

        # installation/uninstallation endpoints
        if parsed.path.startswith('/api/install') or parsed.path.startswith('/api/uninstall') or parsed.path.startswith('/api/run') or parsed.path.startswith('/api/start') or parsed.path.startswith('/api/check'):
            q = urllib.parse.parse_qs(parsed.query)
            # normalize command token (last path component)
            cmd = parsed.path.strip('/').split('/')[-1]
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            res = run_command(cmd, q)
            self.wfile.write(json.dumps(res, default=str).encode('utf-8'))
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))

        # ============ OFFLINE ADMIN (REMOVED) ============
        if parsed.path.startswith('/api/admin/'):
            self.send_response(404)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Offline admin is disabled'}).encode('utf-8'))
            return

        # ============ USER AUTH API ============
        if parsed.path == '/api/user/register':
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                email = data.get('email', '')
                mobile = data.get('mobile', '')
                password = data.get('password', '')
                name = data.get('name', '')
                from user_manager import create_user, public_user_view, create_user_token
                user = create_user(email=email, mobile=mobile, password=password, name=name)
                token = create_user_token(user['id'])
                self.wfile.write(json.dumps({'success': True, 'token': token, 'user': public_user_view(user)}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({'success': False, 'message': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/api/user/login':
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                identifier = data.get('identifier', '')
                password = data.get('password', '')
                from user_manager import find_user_by_identifier, verify_password, public_user_view, create_user_token
                user = find_user_by_identifier(identifier)
                if not user or user.get('status') != 'active':
                    self.wfile.write(json.dumps({'success': False, 'message': 'کاربر یافت نشد'}).encode('utf-8'))
                    return
                if user.get('provider') != 'local':
                    self.wfile.write(json.dumps({'success': False, 'message': 'این حساب با روش دیگری ساخته شده است'}).encode('utf-8'))
                    return
                if not verify_password(password, user.get('password_hash', '')):
                    self.wfile.write(json.dumps({'success': False, 'message': 'رمز عبور اشتباه است'}).encode('utf-8'))
                    return
                token = create_user_token(user['id'])
                self.wfile.write(json.dumps({'success': True, 'token': token, 'user': public_user_view(user)}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({'success': False, 'message': str(e)}).encode('utf-8'))
            return
        
        if parsed.path == '/api/shutdown':
            # Shutdown the server
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'message': 'Shutting down...'}).encode('utf-8'))
            
            # Schedule shutdown
            def shutdown():
                time.sleep(0.5)
                os._exit(0)
            threading.Thread(target=shutdown, daemon=True).start()
            return
        
        if parsed.path == '/api/settings':
            try:
                body = self.rfile.read(content_length)
                new_settings = json.loads(body.decode('utf-8'))
                
                # Validate odoo_path if provided
                if new_settings.get('odoo_path'):
                    path = Path(new_settings['odoo_path'])
                    if not path.exists():
                        self.send_response(400)
                        self.send_header('Content-Type','application/json; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'مسیر وارد شده وجود ندارد'}).encode('utf-8'))
                        return
                
                # Merge with existing settings
                settings = load_settings()
                settings.update(new_settings)
                
                if save_settings(settings):
                    self.send_response(200)
                    self.send_header('Content-Type','application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True, 'settings': settings}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type','application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'خطا در ذخیره تنظیمات'}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return
        
        if parsed.path == '/api/license/activate':
            # Activate a license key
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            if not LICENSE_ENABLED:
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'License system disabled - running in bypass mode'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                license_key = data.get('license_key', '').strip()
                
                if not license_key:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'کلید لایسنس خالی است'
                    }).encode('utf-8'))
                    return
                
                # ========== USER OWNERSHIP CHECK ==========
                # Check if this license belongs to a specific user
                current_user_id = None
                auth_header = self.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    try:
                        from user_manager import verify_user_token
                        verified = verify_user_token(auth_header[7:])
                        if verified and getattr(verified, 'is_valid', False):
                            current_user_id = getattr(verified, 'user_id', None)
                    except Exception:
                        pass
                
                # Get license from database to check ownership
                try:
                    from database_manager import get_license_by_key
                    lic_record = get_license_by_key(license_key)
                    if lic_record:
                        license_owner_id = lic_record.get('user_id')
                        # If license has an owner (user_id), verify current user matches
                        if license_owner_id:
                            if not current_user_id:
                                self.wfile.write(json.dumps({
                                    'success': False,
                                    'message': 'این لایسنس متعلق به یک کاربر است. لطفاً ابتدا وارد حساب کاربری خود شوید.'
                                }).encode('utf-8'))
                                return
                            if current_user_id != license_owner_id:
                                self.wfile.write(json.dumps({
                                    'success': False,
                                    'message': 'این لایسنس متعلق به حساب کاربری شما نیست. با حساب صحیح وارد شوید.'
                                }).encode('utf-8'))
                                return
                except Exception:
                    pass  # If DB check fails, proceed with normal activation
                # ========== END OWNERSHIP CHECK ==========
                
                success, message = activate_license(license_key)
                self.wfile.write(json.dumps({
                    'success': success,
                    'message': message
                }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'خطا: {str(e)}'
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/license/deactivate':
            # Deactivate license
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            if not LICENSE_ENABLED:
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'License system disabled'
                }).encode('utf-8'))
                return
            
            try:
                success = deactivate_license()
                self.wfile.write(json.dumps({
                    'success': success,
                    'message': 'لایسنس با موفقیت غیرفعال شد' if success else 'خطا در غیرفعال‌سازی'
                }).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        # ============ ADMIN API ============
        if parsed.path == '/api/admin/login':
            # Admin login
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                username = data.get('username', '')
                password = data.get('password', '')
                
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    token = create_admin_token(username)
                    self.wfile.write(json.dumps({
                        'success': True,
                        'token': token,
                        'message': 'ورود موفق'
                    }).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'نام کاربری یا رمز عبور اشتباه است'
                    }).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/plans':
            # Save/update plans (admin only)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                plans = data.get('plans', [])
                
                if not plans:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'لیست پلن‌ها خالی است'
                    }).encode('utf-8'))
                    return
                
                # Validate plans
                for plan in plans:
                    if not plan.get('id') or not plan.get('name') or plan.get('price') is None:
                        self.wfile.write(json.dumps({
                            'success': False,
                            'message': 'اطلاعات پلن ناقص است (id, name, price الزامی هستند)'
                        }).encode('utf-8'))
                        return
                
                if save_plans(plans):
                    self.wfile.write(json.dumps({
                        'success': True,
                        'message': 'پلن‌ها با موفقیت ذخیره شدند',
                        'plans': plans
                    }).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'خطا در ذخیره پلن‌ها'
                    }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/generate_license':
            # Generate license (admin only)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, username = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                
                hardware_id = data.get('hardware_id', '').strip()
                validity_hours = int(data.get('validity_hours', 8760))
                customer_name = data.get('customer_name', '')
                note = data.get('note', '')
                
                if not hardware_id:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'شناسه سخت‌افزاری الزامی است'
                    }).encode('utf-8'))
                    return
                
                # Generate license (will also save to new database if enabled)
                license_data = generate_license_with_hours(hardware_id, validity_hours, 
                                                           customer_name=customer_name)
                license_data['customer_name'] = customer_name
                license_data['note'] = note
                license_data['generated_by'] = username
                
                # Save to legacy database (for backward compatibility)
                if not DATABASE_ENABLED:
                    add_license_to_db(license_data)
                
                self.wfile.write(json.dumps({
                    'success': True,
                    **license_data
                }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/customers':
            # Create new customer (admin only)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            if not DATABASE_ENABLED:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'دیتابیس فعال نیست'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                
                name = data.get('name', '').strip()
                phone = data.get('phone', '').strip()
                email = data.get('email', '').strip()
                company = data.get('company', '').strip()
                notes = data.get('notes', '').strip()
                
                if not name:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'نام مشتری الزامی است'
                    }).encode('utf-8'))
                    return
                
                customer = create_customer(
                    name=name,
                    phone=phone,
                    email=email,
                    company=company,
                    notes=notes
                )
                
                self.wfile.write(json.dumps({
                    'success': True,
                    'customer': customer
                }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path.startswith('/api/admin/customers/') and parsed.path.count('/') == 4:
            # Update customer (admin only) - PUT method via POST
            customer_id = parsed.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            if not DATABASE_ENABLED:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'دیتابیس فعال نیست'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                
                customer = update_customer(customer_id, data)
                
                if customer:
                    self.wfile.write(json.dumps({
                        'success': True,
                        'customer': customer
                    }).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'مشتری یافت نشد'
                    }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/licenses/revoke':
            # Revoke a license (admin only)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                license_id = data.get('license_id', '').strip()
                
                if not license_id:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'شناسه لایسنس الزامی است'
                    }).encode('utf-8'))
                    return
                
                if DATABASE_ENABLED:
                    success = revoke_license(license_id)
                else:
                    success = False
                
                if success:
                    self.wfile.write(json.dumps({
                        'success': True,
                        'message': 'لایسنس با موفقیت لغو شد'
                    }).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'لایسنس یافت نشد'
                    }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/admin/search':
            # Search customers and licenses (admin only)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            try:
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                query = data.get('query', '').strip()
                search_type = data.get('type', 'all')  # 'customers', 'licenses', 'all'
                
                results = {'customers': [], 'licenses': []}
                
                if DATABASE_ENABLED:
                    if search_type in ['customers', 'all']:
                        results['customers'] = search_customers(query)
                    if search_type in ['licenses', 'all']:
                        results['licenses'] = search_licenses(query)
                
                self.wfile.write(json.dumps({
                    'success': True,
                    **results
                }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        # ============ PAYMENT API (ZarinPal) ============
        if parsed.path == '/api/payment/request':
            # Create payment request
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            try:
                # Require logged-in user
                auth_header = self.headers.get('Authorization', '')
                if not auth_header.startswith('Bearer '):
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'برای خرید لازم است وارد حساب کاربری شوید.'
                    }).encode('utf-8'))
                    return
                try:
                    from user_manager import verify_user_token
                    verified = verify_user_token(auth_header[7:])
                except Exception:
                    verified = None
                if not verified or not getattr(verified, 'is_valid', False):
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'توکن نامعتبر است. لطفاً دوباره وارد شوید.'
                    }).encode('utf-8'))
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                
                hardware_id = data.get('hardware_id', '').strip()
                plan_id = data.get('plan_id', '').strip()
                amount = int(data.get('amount', 0))
                validity_hours = int(data.get('validity_hours', 0))
                customer_name = data.get('customer_name', '')
                customer_email = data.get('customer_email', '')
                customer_phone = data.get('customer_phone', '')

                user_id = getattr(verified, 'user_id', '')
                if not user_id:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'خطا در تشخیص کاربر. لطفاً دوباره وارد شوید.'
                    }).encode('utf-8'))
                    return
                
                if not hardware_id or not plan_id or amount <= 0:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'اطلاعات ناقص است'
                    }).encode('utf-8'))
                    return
                
                # Try to import payment config
                try:
                    from payment_config import (
                        ZARINPAL_MERCHANT_ID, ZARINPAL_SANDBOX, 
                        ZARINPAL_CALLBACK_URL, ZARINPAL_DESCRIPTION,
                        get_zarinpal_urls, FAKE_PAYMENT_MODE
                    )
                except ImportError:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'تنظیمات درگاه پرداخت یافت نشد'
                    }).encode('utf-8'))
                    return
                
                # ===== FAKE PAYMENT MODE (for testing) =====
                if FAKE_PAYMENT_MODE:
                    # Generate license directly without ZarinPal
                    import uuid
                    fake_authority = f"FAKE_{uuid.uuid4().hex[:16].upper()}"
                    
                    # Generate license
                    license_data = generate_license_with_hours(
                        hardware_id=hardware_id,
                        validity_hours=validity_hours,
                        customer_name=customer_name,
                        price=amount,
                        user_id=user_id
                    )
                    
                    # Log the sale
                    log_sale({
                        'hardware_id': hardware_id,
                        'plan_id': plan_id,
                        'amount': amount,
                        'validity_hours': validity_hours,
                        'user_id': user_id,
                        'customer_name': customer_name,
                        'customer_email': customer_email,
                        'customer_phone': customer_phone,
                    }, license_data, f"FAKE_{fake_authority}")
                    
                    # Build response with v2 license bundle for download
                    response_data = {
                        'success': True,
                        'fake_mode': True,
                        'license_key': license_data['license_key'],
                        'license_id': license_data.get('license_id'),
                        'license_v2': license_data.get('license_v2', False),
                        'license_bundle': license_data.get('license_bundle'),
                        'validity_text': license_data.get('validity_text', ''),
                        'expiry_date': license_data.get('expiry_date', '')
                    }
                    
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    return
                
                # ===== REAL ZARINPAL PAYMENT =====
                urls = get_zarinpal_urls()
                
                # Store pending payment info
                pending_payments = load_pending_payments()
                
                # Create ZarinPal request
                import urllib.request as urllib_request
                zp_data = json.dumps({
                    "merchant_id": ZARINPAL_MERCHANT_ID,
                    "amount": amount * 10,  # Convert to Rial
                    "callback_url": ZARINPAL_CALLBACK_URL,
                    "description": f"{ZARINPAL_DESCRIPTION} - {plan_id}",
                    "metadata": {
                        "mobile": customer_phone,
                        "email": customer_email
                    }
                }).encode('utf-8')
                
                req = urllib_request.Request(
                    urls['request'],
                    data=zp_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                try:
                    with urllib_request.urlopen(req, timeout=30) as resp:
                        zp_response = json.loads(resp.read().decode('utf-8'))
                except Exception as e:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': f'خطا در ارتباط با زرین‌پال: {str(e)}'
                    }).encode('utf-8'))
                    return
                
                if zp_response.get('data', {}).get('code') == 100:
                    authority = zp_response['data']['authority']
                    
                    # Save pending payment
                    pending_payments[authority] = {
                        'hardware_id': hardware_id,
                        'plan_id': plan_id,
                        'amount': amount,
                        'validity_hours': validity_hours,
                        'user_id': user_id,
                        'customer_name': customer_name,
                        'customer_email': customer_email,
                        'customer_phone': customer_phone,
                        'created_at': datetime.now().isoformat()
                    }
                    save_pending_payments(pending_payments)
                    
                    payment_url = urls['startpay'] + authority
                    
                    self.wfile.write(json.dumps({
                        'success': True,
                        'payment_url': payment_url,
                        'authority': authority
                    }).encode('utf-8'))
                else:
                    errors = zp_response.get('errors', {})
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': f"خطای زرین‌پال: {errors}"
                    }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': str(e)
                }).encode('utf-8'))
            return
        
        if parsed.path == '/api/payment/verify':
            # Verify payment and generate license
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            try:
                # Require logged-in user (bind verification to purchaser)
                auth_header = self.headers.get('Authorization', '')
                if not auth_header.startswith('Bearer '):
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'برای تأیید پرداخت لازم است وارد حساب کاربری شوید.'
                    }).encode('utf-8'))
                    return
                try:
                    from user_manager import verify_user_token
                    verified = verify_user_token(auth_header[7:])
                except Exception:
                    verified = None
                if not verified or not getattr(verified, 'is_valid', False):
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'توکن نامعتبر است. لطفاً دوباره وارد شوید.'
                    }).encode('utf-8'))
                    return

                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                authority = data.get('authority', '').strip()
                
                if not authority:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'Authority نامعتبر'
                    }).encode('utf-8'))
                    return
                
                # Load pending payment
                pending_payments = load_pending_payments()
                payment_info = pending_payments.get(authority)
                
                if not payment_info:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'پرداخت یافت نشد یا قبلاً پردازش شده'
                    }).encode('utf-8'))
                    return

                purchaser_user_id = str(payment_info.get('user_id', '')).strip()
                if not purchaser_user_id:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'این پرداخت به هیچ حساب کاربری متصل نیست و قابل تأیید نیست. لطفاً با پشتیبانی تماس بگیرید.'
                    }).encode('utf-8'))
                    return
                if getattr(verified, 'user_id', '') != purchaser_user_id:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'این پرداخت متعلق به حساب کاربری شما نیست.'
                    }).encode('utf-8'))
                    return
                
                # Try to import payment config
                try:
                    from payment_config import (
                        ZARINPAL_MERCHANT_ID, get_zarinpal_urls
                    )
                except ImportError:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'تنظیمات درگاه پرداخت یافت نشد'
                    }).encode('utf-8'))
                    return
                
                urls = get_zarinpal_urls()
                
                # Verify with ZarinPal
                import urllib.request as urllib_request
                zp_data = json.dumps({
                    "merchant_id": ZARINPAL_MERCHANT_ID,
                    "amount": payment_info['amount'] * 10,  # Rial
                    "authority": authority
                }).encode('utf-8')
                
                req = urllib_request.Request(
                    urls['verify'],
                    data=zp_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                try:
                    with urllib_request.urlopen(req, timeout=30) as resp:
                        zp_response = json.loads(resp.read().decode('utf-8'))
                except Exception as e:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': f'خطا در تأیید پرداخت: {str(e)}'
                    }).encode('utf-8'))
                    return
                
                zp_code = zp_response.get('data', {}).get('code')
                
                if zp_code in [100, 101]:  # 100=success, 101=already verified
                    ref_id = zp_response['data'].get('ref_id', '')
                    
                    # Generate license
                    license_data = generate_license_with_hours(
                        hardware_id=payment_info['hardware_id'],
                        validity_hours=payment_info['validity_hours'],
                        customer_name=payment_info['customer_name'],
                        price=payment_info['amount'],
                        user_id=purchaser_user_id
                    )
                    
                    # Remove from pending
                    del pending_payments[authority]
                    save_pending_payments(pending_payments)
                    
                    # Log the sale
                    log_sale(payment_info, license_data, ref_id)
                    
                    # Build response with v2 license bundle for download
                    response_data = {
                        'success': True,
                        'license_key': license_data['license_key'],
                        'license_id': license_data.get('license_id'),
                        'license_v2': license_data.get('license_v2', False),
                        'license_bundle': license_data.get('license_bundle'),
                        'ref_id': ref_id,
                        'validity_text': license_data.get('validity_text', ''),
                        'expiry_date': license_data.get('expiry_date', '')
                    }
                    
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'error': 'پرداخت تأیید نشد'
                    }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': str(e)
                }).encode('utf-8'))
            return
        
        # Fallback to GET handler for other POST requests
        self.do_GET()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path.startswith('/api/admin/customers/') and parsed.path.count('/') == 4:
            # Delete customer (admin only)
            customer_id = parsed.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.end_headers()
            
            # Verify admin token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن احراز هویت یافت نشد'
                }).encode('utf-8'))
                return
            
            token = auth_header[7:]
            is_valid, _ = verify_admin_token(token)
            
            if not is_valid:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'توکن نامعتبر یا منقضی شده'
                }).encode('utf-8'))
                return
            
            if not DATABASE_ENABLED:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': 'دیتابیس فعال نیست'
                }).encode('utf-8'))
                return
            
            try:
                success = delete_customer(customer_id)
                
                if success:
                    self.wfile.write(json.dumps({
                        'success': True,
                        'message': 'مشتری با موفقیت حذف شد'
                    }).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({
                        'success': False,
                        'message': 'مشتری یافت نشد'
                    }).encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': str(e)
                }).encode('utf-8'))
            return
        
        # Default response for unknown DELETE requests
        self.send_response(404)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))

def tail(file_path, lines=200):
    try:
        with open(file_path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 4096
            data = b''
            while size > 0 and data.count(b'\n') <= lines:
                start = max(0, size - block)
                f.seek(start)
                data = f.read(size - start) + data
                size = start

        # PowerShell output is often UTF-16LE; detect by presence of many NUL bytes.
        if data and data.count(b'\x00') > (len(data) // 10):
            try:
                text = data.decode('utf-16', errors='replace')
            except Exception:
                text = data.decode(errors='replace')
        else:
            text = data.decode(errors='replace')

        return text.splitlines()[-lines:]
    except Exception:
        return []


def port_listening(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        r = s.connect_ex(('127.0.0.1', port))
        return r == 0
    except Exception:
        return False
    finally:
        s.close()


def get_status():
    offline = {}
    offline['python_installer_exists'] = (OFFLINE / 'python').exists() and any((OFFLINE / 'python').glob('*.exe'))
    offline['postgres_installer_exists'] = (OFFLINE / 'postgresql').exists() and any((OFFLINE / 'postgresql').glob('*.exe'))
    offline['wkhtmltopdf_installer_exists'] = (OFFLINE / 'wkhtmltopdf').exists() and any((OFFLINE / 'wkhtmltopdf').glob('*.exe'))
    offline['vc_redist_exists'] = (OFFLINE / 'vc_redist').exists() and any((OFFLINE / 'vc_redist').glob('*.exe'))
    offline['nodejs_installer_exists'] = (OFFLINE / 'nodejs').exists() and any((OFFLINE / 'nodejs').glob('*.msi'))
    offline['git_installer_exists'] = (OFFLINE / 'git').exists() and any((OFFLINE / 'git').glob('*.exe'))
    wheels = OFFLINE / 'wheels'
    offline['wheels_count'] = len(list(wheels.iterdir())) if wheels.exists() else 0
    offline['requirements_exists'] = (OFFLINE / 'requirements.txt').exists()

    # Check soft folder tools with compatibility info
    sys_info = get_system_info()
    soft_tools = []
    if SOFT.exists():
        for item in SOFT.iterdir():
            if item.is_file() and item.suffix.lower() in ('.exe', '.msi'):
                name_lower = item.name.lower()
                is_compatible = True
                arch_info = 'universal'
                
                # Check architecture compatibility
                if sys_info['arch'] == 'x86':
                    if 'x64' in name_lower or 'amd64' in name_lower or '64bit' in name_lower:
                        is_compatible = False
                        arch_info = 'x64 only'
                    elif 'x86' in name_lower or '32bit' in name_lower:
                        arch_info = 'x86'
                else:
                    if 'x64' in name_lower or 'amd64' in name_lower or '64bit' in name_lower:
                        arch_info = 'x64'
                    elif 'x86' in name_lower or '32bit' in name_lower:
                        arch_info = 'x86 (compatible)'
                
                # Check if software is installed
                is_installed, install_details = check_software_installed(item.stem)
                
                soft_tools.append({
                    'name': item.name,
                    'path': str(item),
                    'size': item.stat().st_size,
                    'compatible': is_compatible,
                    'arch': arch_info,
                    'type': 'file',
                    'installed': is_installed,
                    'install_details': install_details,
                })
            elif item.is_dir():
                # For directories (VSCode, copilot-rtl, etc.), find best compatible installer
                best_installer = get_compatible_installer(item.name, sys_info['arch'])
                
                # Check if software is installed
                is_installed, install_details = check_software_installed(item.name)
                
                if best_installer:
                    name_lower = best_installer.name.lower()
                    arch_info = 'universal'
                    if 'x64' in name_lower or 'amd64' in name_lower:
                        arch_info = 'x64'
                    elif 'x86' in name_lower or '32bit' in name_lower:
                        arch_info = 'x86'
                    
                    soft_tools.append({
                        'name': item.name,
                        'path': str(best_installer),
                        'size': best_installer.stat().st_size,
                        'compatible': True,
                        'arch': arch_info,
                        'type': 'folder',
                        'folder': str(item),
                        'installed': is_installed,
                        'install_details': install_details,
                    })
                else:
                    # No compatible installer found - check if needs download
                    all_files = list(item.glob('*.exe')) + list(item.glob('*.msi'))
                    download_url = get_download_url(item.name, sys_info['arch'])
                    
                    soft_tools.append({
                        'name': item.name,
                        'path': None,
                        'size': 0,
                        'compatible': False if not download_url else True,
                        'arch': 'نیاز به دانلود' if download_url else 'ناسازگار',
                        'type': 'folder',
                        'folder': str(item),
                        'needs_download': True if download_url else False,
                        'download_url': download_url,
                        'installed': is_installed,
                        'install_details': install_details,
                    })

    log_tail = tail(LOG) if LOG.exists() else []

    # Get Odoo config to determine the actual port
    odoo_config = parse_odoo_config()
    config_port = odoo_config.get('http_port', 8069)
    
    # Check standard ports plus the configured port
    ports_to_check = {8019, 8069, config_port}
    odoo_ports = {}
    for port in ports_to_check:
        odoo_ports[str(port)] = port_listening(port)

    odoo_root = resolve_odoo_root()

    def run_and_get(cmd: list[str], timeout: int = 4) -> tuple[bool, str]:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
            return True, out.decode(errors='replace').strip()
        except Exception as e:
            return False, str(e)

    # Python (prefer workspace venv)
    python_ok = False
    python_detail = ''
    venv_python = None
    if odoo_root:
        venv_python = odoo_root / 'venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            ok, detail = run_and_get([str(venv_python), '--version'])
            if ok and 'Python' in detail:
                python_ok = True
                python_detail = f"venv: {detail}"

    if not python_ok:
        candidates = [
            shutil_which('python'),
            shutil_which('python3'),
            r'C:\Program Files\Python311\python.exe',
            r'C:\Program Files\Python3.11\python.exe',
            os.path.expandvars(r'%LOCALAPPDATA%\Programs\Python\Python311\python.exe'),
        ]
        candidates = [c for c in candidates if c and Path(c).exists()]
        for c in candidates:
            ok, detail = run_and_get([c, '--version'])
            if ok and 'Python' in detail:
                python_ok = True
                python_detail = f"system: {detail}"
                break

    # PostgreSQL installed (folder presence)
    pg_ok = False
    pg_detail = ''
    try:
        roots = [Path(r'C:\Program Files\PostgreSQL'), Path(r'C:\Program Files (x86)\PostgreSQL')]
        for root in roots:
            if root.exists():
                for d in root.iterdir():
                    if (d / 'bin' / 'pg_ctl.exe').exists() or (d / 'bin' / 'postgres.exe').exists():
                        pg_ok = True
                        pg_detail = str(d)
                        break
            if pg_ok:
                break
    except Exception:
        pg_ok = False

    # pg_dump works (backup dependency)
    pg_dump_ok = False
    pg_dump_detail = ''
    try:
        pg_dump_candidates = []
        for root in [Path(r'C:\Program Files\PostgreSQL'), Path(r'C:\Program Files (x86)\PostgreSQL')]:
            if not root.exists():
                continue
            for d in sorted(root.iterdir(), key=lambda p: p.name, reverse=True):
                exe = d / 'bin' / 'pg_dump.exe'
                if exe.exists():
                    pg_dump_candidates.append(exe)
        for exe in pg_dump_candidates:
            # Set PATH to include PostgreSQL bin directory for DLL loading
            bin_dir = str(exe.parent)
            env = os.environ.copy()
            env['PATH'] = bin_dir + ';' + env.get('PATH', '')
            try:
                result = subprocess.run([str(exe), '--version'], capture_output=True, timeout=5, env=env)
                detail = result.stdout.decode(errors='replace').strip()
                if 'pg_dump' in detail:
                    pg_dump_ok = True
                    pg_dump_detail = f"{exe.parent} :: {detail}"
                    break
            except Exception:
                continue
    except Exception as e:
        pg_dump_ok = False
        pg_dump_detail = str(e)

    # wkhtmltopdf installed
    wk_ok = False
    wk_detail = ''
    try:
        wk = shutil_which('wkhtmltopdf')
        if wk:
            wk_ok = True
            wk_detail = wk
        else:
            common = Path(r'C:\Program Files\wkhtmltopdf')
            if common.exists():
                hits = list(common.glob('**/wkhtmltopdf.exe'))
                if hits:
                    wk_ok = True
                    wk_detail = str(hits[0])
    except Exception:
        wk_ok = False

    # VC++ 2015-2022 Redistributable (x64) installed
    vc_ok = False
    vc_detail = ''
    try:
        uninstall_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, subkey in uninstall_paths:
            try:
                with winreg.OpenKey(hive, subkey) as k:
                    count = winreg.QueryInfoKey(k)[0]
                    for i in range(0, count):
                        try:
                            skn = winreg.EnumKey(k, i)
                            with winreg.OpenKey(k, skn) as sk:
                                name, _ = winreg.QueryValueEx(sk, 'DisplayName')
                                if not name:
                                    continue
                                # Accept VC++ 2015, 2017, 2019, or 2022 (x64)
                                if 'Microsoft Visual C++' in name and ('x64' in name or 'X64' in name):
                                    if '2015' in name or '2017' in name or '2019' in name or '2022' in name:
                                        vc_ok = True
                                        vc_detail = name
                                        break
                        except Exception:
                            continue
            except Exception:
                continue
            if vc_ok:
                break
    except Exception as e:
        vc_ok = False
        vc_detail = str(e)

    # Node.js installed (for assets compilation)
    node_ok = False
    node_detail = ''
    try:
        # Check common paths directly (in case PATH not updated in this process)
        node_paths = [
            Path(r'C:\Program Files\nodejs\node.exe'),
            Path(os.environ.get('LOCALAPPDATA', '') + r'\Programs\node\node.exe'),
            Path(os.environ.get('PROGRAMFILES', '') + r'\nodejs\node.exe'),
        ]
        node_path = None
        for p in node_paths:
            if p.exists():
                node_path = str(p)
                break
        if not node_path:
            node_path = shutil_which('node')
        
        if node_path:
            result = subprocess.run([node_path, '--version'], capture_output=True, timeout=5)
            version = result.stdout.decode(errors='replace').strip()
            if version:
                node_ok = True
                node_detail = f"{version} ({node_path})"
    except Exception as e:
        node_ok = False
        node_detail = str(e)

    # Git installed (for updates and cloning)
    git_ok = False
    git_detail = ''
    try:
        # Check common paths directly (in case PATH not updated in this process)
        git_paths = [
            Path(r'C:\Program Files\Git\bin\git.exe'),
            Path(r'C:\Program Files (x86)\Git\bin\git.exe'),
            Path(os.environ.get('LOCALAPPDATA', '') + r'\Programs\Git\bin\git.exe'),
        ]
        git_path = None
        for p in git_paths:
            if p.exists():
                git_path = str(p)
                break
        if not git_path:
            git_path = shutil_which('git')
        
        if git_path:
            result = subprocess.run([git_path, '--version'], capture_output=True, timeout=5)
            version = result.stdout.decode(errors='replace').strip()
            if version:
                git_ok = True
                git_detail = version
    except Exception as e:
        git_ok = False
        git_detail = str(e)

    # Odoo workspace
    odoo_ok = False
    odoo_detail = ''
    if odoo_root:
        odoo_bin = odoo_root / 'odoo-src' / 'odoo-19.0' / 'odoo-bin'
        if odoo_bin.exists():
            odoo_ok = True
            odoo_detail = str(odoo_root)

    wheel_ok = offline['wheels_count'] > 0

    deps = [
        {
            'id': 'python',
            'label': 'Python (venv/system)',
            'ok': python_ok,
            'details': python_detail,
            'offline_ready': offline['python_installer_exists'],
            'install_cmd': 'install_python_offline',
        },
        {
            'id': 'postgres',
            'label': 'PostgreSQL',
            'ok': pg_ok,
            'details': pg_detail,
            'offline_ready': offline['postgres_installer_exists'],
            'install_cmd': 'install_postgresql_offline',
        },
        {
            'id': 'pg_dump',
            'label': 'pg_dump works (Backup)',
            'ok': pg_dump_ok,
            'details': pg_dump_detail,
            'offline_ready': False,
            'install_cmd': None,
        },
        {
            'id': 'wkhtmltopdf',
            'label': 'wkhtmltopdf',
            'ok': wk_ok,
            'details': wk_detail,
            'offline_ready': offline['wkhtmltopdf_installer_exists'],
            'install_cmd': 'install_wkhtmltopdf_offline',
        },
        {
            'id': 'vc_redist',
            'label': 'VC++ 2015-2022 Redistributable (x64)',
            'ok': vc_ok,
            'details': vc_detail,
            'offline_ready': offline['vc_redist_exists'],
            'install_cmd': 'install_vc_redist_offline',
        },
        {
            'id': 'nodejs',
            'label': 'Node.js (برای assets)',
            'ok': node_ok,
            'details': node_detail,
            'offline_ready': offline.get('nodejs_installer_exists', False),
            'install_cmd': 'install_nodejs_offline',
        },
        {
            'id': 'git',
            'label': 'Git (برای بروزرسانی)',
            'ok': git_ok,
            'details': git_detail,
            'offline_ready': offline.get('git_installer_exists', False),
            'install_cmd': 'install_git_offline',
        },
        {
            'id': 'wheelhouse',
            'label': 'Offline wheels (pip)',
            'ok': wheel_ok,
            'details': f"{offline['wheels_count']} files" + ("; requirements.txt present" if offline['requirements_exists'] else ""),
            'offline_ready': wheel_ok,
            'install_cmd': 'setup_wheels',
            'install_label': 'دانلود پکیج‌ها' if not wheel_ok else 'نصب شده',
        },
        {
            'id': 'odoo',
            'label': 'Odoo workspace',
            'ok': odoo_ok,
            'details': odoo_detail,
            'offline_ready': True,
            'install_cmd': 'setup_odoo_workspace',
            'install_label': 'راه‌اندازی Workspace' if not odoo_ok else 'نصب شده',
        },
    ]

    return {
        'offline': offline,
        'deps': deps,
        'log_tail': log_tail[-200:],
        'odoo_ports': odoo_ports,
        'python_ok': python_ok,
        'postgres_ok': pg_ok,
        'wkhtmltopdf_ok': wk_ok,
        'soft_tools': soft_tools,
        'system_info': sys_info,
    }


def shutil_which(name):
    # simple wrapper that returns path or None
    try:
        import shutil
        p = shutil.which(name)
        return p
    except Exception:
        return None


def run_command(cmd, query):
    # cmd values: run_fetch, start_odoo, run_check
    try:
        if cmd == 'run_fetch':
            script = str(BASE / 'auto_fetch_and_setup.ps1')
            args = ['-ExecutionPolicy','Bypass','-File', script]
            if query.get('autorun', ['0'])[0] in ('1','true','True'):
                args += ['-AutoRun']
            p = subprocess.Popen(['powershell'] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {'pid': p.pid}
        if cmd == 'start_odoo':
            odoo_root = resolve_odoo_root()
            if not odoo_root:
                return {'error': 'پوشه Odoo پیدا نشد! ابتدا روی "نصب کامل" کلیک کنید یا پوشه odoo 19 را کنار Setup ایجاد کنید.'}
            
            # Get Odoo configuration to determine port
            odoo_config = parse_odoo_config()
            http_port = odoo_config.get('http_port', 8069)
            
            # Try different script names
            script_names = ['run_odoo.ps1', 'start_odoo.ps1', 'run_odoo.bat', 'start_odoo.bat']
            script = None
            for name in script_names:
                candidate = odoo_root / name
                if candidate.exists():
                    script = candidate
                    break
            
            if not script:
                return {'error': f'اسکریپت اجرا پیدا نشد در {odoo_root}. لطفاً فایل run_odoo.ps1 یا run_odoo.bat ایجاد کنید.'}
            
            # Check if venv exists
            venv_python = odoo_root / 'venv' / 'Scripts' / 'python.exe'
            if not venv_python.exists():
                return {'error': 'محیط مجازی Python (venv) ایجاد نشده! ابتدا روی "نصب کامل" کلیک کنید.'}
            
            # Check if odoo-bin exists
            odoo_bin_paths = [
                odoo_root / 'odoo-src' / 'odoo-19.0' / 'odoo-bin',
                odoo_root / 'odoo-src' / 'odoo-18.0' / 'odoo-bin',
                odoo_root / 'odoo-src' / 'odoo-17.0' / 'odoo-bin',
                odoo_root / 'odoo-bin',
                odoo_root / 'odoo' / 'odoo-bin',
            ]
            odoo_bin_found = any(p.exists() for p in odoo_bin_paths)
            if not odoo_bin_found:
                return {'error': 'فایل odoo-bin پیدا نشد! ابتدا Odoo را دانلود/کلون کنید.'}
            
            # Run based on extension
            try:
                if script.suffix.lower() == '.bat':
                    p = subprocess.Popen(
                        ['cmd.exe', '/c', str(script)], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL, 
                        cwd=str(odoo_root),
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    p = subprocess.Popen(
                        ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL, 
                        cwd=str(odoo_root),
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                return {
                    'pid': p.pid, 
                    'script': str(script),
                    'http_port': http_port,
                    'odoo_root': str(odoo_root),
                    'config_found': odoo_config.get('config_found', False),
                    'config_path': odoo_config.get('config_path', ''),
                }
            except Exception as e:
                return {'error': f'خطا در اجرای اسکریپت: {str(e)}'}
        if cmd == 'run_check':
            script = str(BASE / 'check_status.ps1')
            p = subprocess.Popen(['powershell','-ExecutionPolicy','Bypass','-File', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err = p.communicate(timeout=30)
            return {'pid': p.pid, 'stdout': out.decode(errors='replace')[:2000], 'stderr': err.decode(errors='replace')[:2000]}
        # installers: install from Setup\offline
        if cmd in ('python', 'install_python', 'install_python_offline'):
            inst = find_installer('python')
            if not inst:
                return {'error': 'python installer not found in offline/python'}
            # Show installation UI so user can see progress
            pid = run_exe_elevated(Path(inst), "InstallAllUsers=1 PrependPath=1", wait=False)
            return {'pid': pid}
        if cmd in ('postgres', 'install_postgres', 'install_postgresql_offline'):
            inst = find_installer('postgresql')
            if not inst:
                return {'error': 'postgres installer not found in offline/postgresql'}
            # Show installation UI so user can see progress
            pid = run_exe_elevated(Path(inst), "--superpassword odoo", wait=False)
            return {'pid': pid}
        if cmd in ('wkhtmltopdf', 'install_wkhtmltopdf', 'install_wkhtmltopdf_offline'):
            # Run installer directly so user can see the UI
            inst = find_installer('wkhtmltopdf')
            if not inst:
                return {'error': 'wkhtmltopdf installer not found in offline/wkhtmltopdf'}
            # Show installation UI so user can see progress
            pid = run_exe_elevated(Path(inst), None, wait=False)
            return {'pid': pid}
            return {'pid': pid}
        if cmd in ('vc_redist', 'install_vc_redist', 'install_vc_redist_offline'):
            inst = find_installer('vc_redist')
            if not inst:
                return {'error': 'VC_redist installer not found in offline/vc_redist'}
            # Show installation UI so user can see progress
            pid = run_exe_elevated(Path(inst), '/norestart', wait=False)
            return {'pid': pid}
        if cmd in ('nodejs', 'install_nodejs', 'install_nodejs_offline'):
            inst = find_installer('nodejs')
            if not inst:
                # Try to install via winget if online
                script = '''
$Host.UI.RawUI.WindowTitle = "Installing Node.js..."
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Installing Node.js via winget...       " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements
Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "Node.js installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Installation failed. Please download Node.js from https://nodejs.org" -ForegroundColor Red
}
Write-Host ""
Write-Host "You can close this window now." -ForegroundColor Yellow
'''
                tmp = TEMP_DIR / 'install_nodejs_tmp.ps1'
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(script, encoding='utf-8')
                pid = run_powershell_elevated_file(tmp, wait=False)
                return {'pid': pid, 'status': 'installing via winget'}
            # Show installation UI so user can see progress
            inst_path = Path(inst)
            if inst_path.suffix.lower() == '.msi':
                # Use msiexec for MSI files - create a script to run it
                script = f'''
$Host.UI.RawUI.WindowTitle = "Installing Node.js..."
Write-Host "Installing Node.js..." -ForegroundColor Cyan
Start-Process msiexec.exe -ArgumentList '/i "{inst}"' -Wait
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "You can close this window now." -ForegroundColor Yellow
'''
                tmp = TEMP_DIR / 'install_nodejs_msi_tmp.ps1'
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(script, encoding='utf-8')
                pid = run_powershell_elevated_file(tmp, wait=False)
            else:
                pid = run_exe_elevated(inst_path, None, wait=False)
            return {'pid': pid}
        if cmd in ('git', 'install_git', 'install_git_offline'):
            inst = find_installer('git')
            if not inst:
                # Try to install via winget if online
                script = '''
$Host.UI.RawUI.WindowTitle = "Installing Git..."
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Installing Git via winget...            " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "Git installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Installation failed. Please download Git from https://git-scm.com" -ForegroundColor Red
}
Write-Host ""
Write-Host "You can close this window now." -ForegroundColor Yellow
'''
                tmp = TEMP_DIR / 'install_git_tmp.ps1'
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(script, encoding='utf-8')
                pid = run_powershell_elevated_file(tmp, wait=False)
                return {'pid': pid, 'status': 'installing via winget'}
            # Show installation UI
            pid = run_exe_elevated(Path(inst), None, wait=False)
            return {'pid': pid}
        if cmd in ('install_pip_wheels', 'pip_wheels'):
            odoo_root = resolve_odoo_root()
            if not odoo_root:
                return {'error': 'odoo19 workspace not found for venv wheels install'}
            pip_exe = odoo_root / 'venv' / 'Scripts' / 'pip.exe'
            if not pip_exe.exists():
                return {'error': f'pip.exe not found at {pip_exe} (create venv first)'}
            wheel_dir = OFFLINE / 'wheels'
            if not wheel_dir.exists():
                return {'error': 'offline/wheels folder not found'}
            req = OFFLINE / 'requirements.txt'
            if not req.exists():
                return {'error': 'offline/requirements.txt not found (needed to install wheels)'}

            tmp = TEMP_DIR / 'install_pip_wheels_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(
                f"& {ps_sq(str(pip_exe))} install --no-index --find-links {ps_sq(str(wheel_dir))} -r {ps_sq(str(req))}\n",
                encoding='utf-8'
            )
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid}
        if cmd in ('create_pg_role','install_pg_role'):
            # Run the create_postgres_role.ps1 in an elevated window so user can enter postgres password
            helper = str(BASE / 'create_postgres_role.ps1')
            if not Path(helper).exists():
                return {'error': 'create_postgres_role.ps1 not found in project root'}
            pid = run_powershell_elevated_file(Path(helper), wait=False)
            return {'pid': pid}
        if cmd in ('restart_odoo','odoo_restart'):
            odoo_root = resolve_odoo_root()
            stop = (odoo_root / 'stop_odoo.ps1') if (odoo_root and (odoo_root / 'stop_odoo.ps1').exists()) else (BASE / 'stop_odoo.ps1')
            start = (odoo_root / 'start_odoo.ps1') if (odoo_root and (odoo_root / 'start_odoo.ps1').exists()) else (BASE / 'start_odoo.ps1')
            if not stop.exists() and not start.exists():
                return {'error': 'no stop_odoo.ps1 or start_odoo.ps1 found'}

            def worker():
                try:
                    if stop.exists():
                        run_powershell_elevated_file_sync(stop)
                    if start.exists():
                        subprocess.Popen(
                            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(start), '-NoBrowser'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                except Exception:
                    return

            threading.Thread(target=worker, daemon=True).start()
            return {'status': 'restart triggered'}
        if cmd in ('full_install','install_all'):
            fetch = BASE / 'auto_fetch_and_setup.ps1'
            wk = BASE / 'install_wkhtmltopdf.ps1'
            role = BASE / 'create_postgres_role.ps1'
            odoo_root = resolve_odoo_root()
            start = (odoo_root / 'start_odoo.ps1') if (odoo_root and (odoo_root / 'start_odoo.ps1').exists()) else None

            def worker():
                try:
                    if fetch.exists():
                        run_powershell_elevated_file_sync(fetch, ps_args=['-AutoRun'])
                    if wk.exists():
                        run_powershell_elevated_file_sync(wk)
                    if role.exists():
                        run_powershell_elevated_file_sync(role)
                    if start and start.exists():
                        subprocess.Popen(
                            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(start), '-NoBrowser'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                except Exception:
                    return

            threading.Thread(target=worker, daemon=True).start()
            return {'status': 'full_install triggered'}
        
        # ============ UNINSTALL COMMANDS ============
        if cmd == 'uninstall_python':
            # Python uninstall - uses MSI, need to use /X for uninstall
            script = r'''
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling Python..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Find Python in registry (both HKLM and HKCU)
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$apps = @()
foreach ($path in $regPaths) {
    $apps += Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Python 3*" }
}

if ($apps.Count -eq 0) {
    Write-Host "No Python installation found." -ForegroundColor Yellow
} else {
    foreach ($app in $apps) {
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString -like "*MsiExec*") {
            # Extract product code from UninstallString
            $productCode = $app.PSChildName
            Write-Host "Uninstalling via MSI: $productCode" -ForegroundColor Yellow
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/X", $productCode, "/quiet", "/norestart" -Wait
        } elseif ($app.UninstallString) {
            Write-Host "Running uninstaller..." -ForegroundColor Yellow
            $uninstaller = $app.UninstallString -replace '"', ''
            if (Test-Path $uninstaller) {
                Start-Process -FilePath $uninstaller -ArgumentList "/quiet" -Wait
            }
        }
    }
}

Write-Host ""
Write-Host "Python uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'uninstall_python_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'uninstall triggered'}
        
        if cmd == 'uninstall_postgresql':
            script = r'''
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling PostgreSQL..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Stop PostgreSQL service first
Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Stop-Service -Force -ErrorAction SilentlyContinue

$pgRoot = "C:\Program Files\PostgreSQL"
if (Test-Path $pgRoot) {
    $versions = Get-ChildItem $pgRoot -Directory -ErrorAction SilentlyContinue
    foreach ($v in $versions) {
        $uninstaller = Join-Path $v.FullName "uninstall-postgresql.exe"
        if (Test-Path $uninstaller) {
            Write-Host "Uninstalling PostgreSQL $($v.Name)..." -ForegroundColor Yellow
            Start-Process -FilePath $uninstaller -ArgumentList "--mode", "unattended" -Wait
        }
    }
} else {
    Write-Host "PostgreSQL folder not found at $pgRoot" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "PostgreSQL uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'uninstall_postgresql_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'uninstall triggered'}
        
        if cmd == 'uninstall_wkhtmltopdf':
            script = r'''
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling wkhtmltopdf..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Method 1: Registry lookup
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$found = $false
foreach ($path in $regPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*wkhtmltopdf*" -or $_.DisplayName -like "*wkhtmltox*" }
    foreach ($app in $apps) {
        $found = $true
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString -like "*MsiExec*") {
            $productCode = $app.PSChildName
            Write-Host "Uninstalling via MSI..." -ForegroundColor Yellow
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/X", $productCode, "/quiet", "/norestart" -Wait
        } elseif ($app.UninstallString) {
            $uninstaller = $app.UninstallString -replace '"', ''
            Write-Host "Running uninstaller: $uninstaller" -ForegroundColor Yellow
            if (Test-Path $uninstaller) {
                Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait
            }
        }
    }
}

# Method 2: Check common install location
$wkPath = "C:\Program Files\wkhtmltopdf"
if (Test-Path $wkPath) {
    $uninstaller = Join-Path $wkPath "uninstall.exe"
    if (Test-Path $uninstaller) {
        Write-Host "Running uninstaller from $wkPath..." -ForegroundColor Yellow
        Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait
        $found = $true
    }
}

if (-not $found) {
    Write-Host "wkhtmltopdf not found in registry." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "wkhtmltopdf uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'uninstall_wkhtmltopdf_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'uninstall triggered'}
        
        if cmd == 'uninstall_vc_redist':
            script = r'''
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling VC++ Redistributable..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$found = $false
foreach ($path in $regPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { 
        $_.DisplayName -like "*Visual C++*2015*" -or $_.DisplayName -like "*Visual C++*2017*" -or 
        $_.DisplayName -like "*Visual C++*2019*" -or $_.DisplayName -like "*Visual C++*2022*"
    }
    foreach ($app in $apps) {
        $found = $true
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString) {
            $uninstaller = $app.UninstallString -replace '"', ''
            Write-Host "Running uninstaller..." -ForegroundColor Yellow
            Start-Process -FilePath $uninstaller -ArgumentList "/quiet", "/norestart" -Wait -ErrorAction SilentlyContinue
        }
    }
}

if (-not $found) {
    Write-Host "VC++ Redistributable not found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "VC++ Redistributable uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'uninstall_vc_redist_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'uninstall triggered'}
        
        if cmd == 'uninstall_nodejs':
            script = r'''
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling Node.js..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$found = $false
foreach ($path in $regPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Node.js*" -or $_.DisplayName -like "*Node*" }
    foreach ($app in $apps) {
        $found = $true
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString -like "*MsiExec*") {
            $productCode = $app.PSChildName
            Write-Host "Uninstalling via MSI..." -ForegroundColor Yellow
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/X", $productCode, "/quiet", "/norestart" -Wait
        } elseif ($app.UninstallString) {
            $uninstaller = $app.UninstallString -replace '"', ''
            Write-Host "Running uninstaller..." -ForegroundColor Yellow
            Start-Process -FilePath $uninstaller -ArgumentList "/quiet" -Wait -ErrorAction SilentlyContinue
        }
    }
}

if (-not $found) {
    Write-Host "Node.js not found in registry." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Node.js uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'uninstall_nodejs_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'uninstall triggered'}
        
        if cmd == 'uninstall_git':
            script = r'''
$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Uninstalling Git..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$found = $false
foreach ($path in $regPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Git*" -and $_.DisplayName -notlike "*GitHub*" }
    foreach ($app in $apps) {
        $found = $true
        Write-Host "Found: $($app.DisplayName)" -ForegroundColor Green
        
        if ($app.UninstallString) {
            $uninstaller = $app.UninstallString -replace '"', ''
            Write-Host "Running uninstaller: $uninstaller" -ForegroundColor Yellow
            if (Test-Path $uninstaller) {
                Start-Process -FilePath $uninstaller -ArgumentList "/VERYSILENT", "/NORESTART" -Wait -ErrorAction SilentlyContinue
            }
        }
    }
}

if (-not $found) {
    Write-Host "Git not found in registry." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Git uninstall complete!" -ForegroundColor Green
Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'uninstall_git_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'uninstall triggered'}
        
        # ============ SOFT TOOLS INSTALLATION ============
        if cmd == 'install_soft_tool':
            tool_path = query.get('path', [None])[0]
            if not tool_path:
                return {'error': 'path parameter required'}
            tool = Path(tool_path)
            if not tool.exists():
                return {'error': f'file not found: {tool_path}'}
            
            # Determine installer type and run appropriately
            if tool.suffix.lower() == '.msi':
                # MSI installer - show UI
                pid = run_exe_elevated(tool, None, wait=False)
            else:
                # EXE installer - show UI
                pid = run_exe_elevated(tool, None, wait=False)
            
            return {'pid': pid, 'status': 'installation started'}
        
        # ============ DOWNLOAD AND INSTALL ============
        if cmd == 'download_and_install':
            software = query.get('software', [None])[0]
            if not software:
                return {'error': 'software parameter required'}
            
            sys_info = get_system_info()
            url = get_download_url(software, sys_info['arch'])
            
            if not url:
                return {'error': f'No download URL available for {software} ({sys_info["arch"]})'}
            
            # Determine target folder
            target_folder = SOFT / software
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate filename from URL
            filename = url.split('/')[-1].split('?')[0]
            if not filename.endswith('.exe') and not filename.endswith('.msi'):
                filename = f'{software}-{sys_info["arch"]}.exe'
            
            target_file = target_folder / filename
            
            # Create PowerShell script for download and install
            script = f'''
$ErrorActionPreference = "Stop"
$url = "{url}"
$output = "{str(target_file)}"

Write-Host "Downloading {software} for {sys_info['arch']}..."
Write-Host "URL: $url"
Write-Host "Target: $output"

# Download using System.Net.WebClient
$webClient = New-Object System.Net.WebClient
$webClient.DownloadFile($url, $output)

if (Test-Path $output) {{
    Write-Host "Download complete!"
    Write-Host "Starting installation..."
    
    # Run installer
    Start-Process -FilePath $output -ArgumentList "/S" -Wait
    
    Write-Host "Installation complete!"
}} else {{
    Write-Host "Download failed!"
    exit 1
}}
'''
            tmp = TEMP_DIR / f'download_install_{software}_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': f'downloading and installing {software}', 'target': str(target_file)}
        
        # ============ GET SYSTEM INFO ============
        if cmd == 'system_info':
            return get_system_info()
        
        # ============ SETUP WHEELS (Download from PyPI) ============
        if cmd in ('setup_wheels', 'download_wheels', 'install_pip_wheels_online'):
            odoo_root = resolve_odoo_root()
            # Create requirements.txt if missing
            req = OFFLINE / 'requirements.txt'
            wheel_dir = OFFLINE / 'wheels'
            wheel_dir.mkdir(parents=True, exist_ok=True)
            
            # Default requirements for Odoo 19
            default_requirements = """
Babel>=2.6.0
chardet>=3.0.4
cryptography>=2.6.1
decorator>=4.3.0
docutils>=0.14
ebaysdk>=2.1.5
freezegun>=0.3.11
gevent>=1.4.0
greenlet>=0.4.15
idna>=2.8
Jinja2>=2.10.1
libsass>=0.17.0
lxml>=4.3.2
MarkupSafe>=1.1.1
num2words>=0.5.6
ofxparse>=0.19
passlib>=1.7.1
Pillow>=5.4.1
polib>=1.1.0
psutil>=5.6.1
psycopg2-binary>=2.8.2
pydot>=1.4.1
pyopenssl>=19.0.0
PyPDF2>=1.26.0
pyserial>=3.4
python-dateutil>=2.7.3
python-ldap>=3.1.0;sys_platform!='win32'
python-stdnum>=1.11
pytz>=2019.1
pyusb>=1.0.2
qrcode>=6.1
reportlab>=3.5.13
requests>=2.21.0
urllib3>=1.24.2
vobject>=0.9.6.1
Werkzeug>=0.14.1
xlrd>=1.2.0
xlsxwriter>=1.1.5
xlwt>=1.3.0
zeep>=3.2.0
"""
            if not req.exists():
                req.write_text(default_requirements.strip(), encoding='utf-8')
            
            # Create script to download wheels
            script = f'''
$ErrorActionPreference = "Stop"
$wheelDir = "{str(wheel_dir)}"
$reqFile = "{str(req)}"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  دانلود پکیج‌های pip برای نصب آفلاین" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Find Python
$pythonPaths = @(
    "$env:LOCALAPPDATA\\Programs\\Python\\Python311\\python.exe",
    "$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe",
    "C:\\Program Files\\Python311\\python.exe",
    "C:\\Program Files\\Python312\\python.exe",
    "C:\\Python311\\python.exe",
    "C:\\Python312\\python.exe"
)

$python = $null
foreach ($p in $pythonPaths) {{
    if (Test-Path $p) {{
        $python = $p
        break
    }}
}}

if (-not $python) {{
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}}

if (-not $python) {{
    Write-Host "Python not found! Please install Python first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}}

Write-Host "Using Python: $python" -ForegroundColor Green

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $python -m pip install --upgrade pip

# Download wheels
Write-Host "Downloading wheels to: $wheelDir" -ForegroundColor Yellow
& $python -m pip download -d $wheelDir -r $reqFile --prefer-binary

if ($LASTEXITCODE -eq 0) {{
    $count = (Get-ChildItem $wheelDir -Filter *.whl).Count + (Get-ChildItem $wheelDir -Filter *.tar.gz).Count
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Download complete! $count packages" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}} else {{
    Write-Host "Some packages may have failed to download" -ForegroundColor Yellow
}}

Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'setup_wheels_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'downloading pip wheels'}
        
        # ============ SETUP ODOO WORKSPACE ============
        if cmd in ('setup_odoo', 'setup_odoo_workspace', 'install_odoo_workspace'):
            # Determine workspace location
            odoo_root = BASE.parent / 'odoo19'
            
            script = f'''
$ErrorActionPreference = "Stop"
$odooRoot = "{str(odoo_root)}"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    راه‌اندازی Odoo 19 Workspace" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan

# Create workspace folder
if (-not (Test-Path $odooRoot)) {{
    Write-Host "Creating workspace folder..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $odooRoot -Force | Out-Null
}}

Set-Location $odooRoot

# Check if Git is installed
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {{
    Write-Host "Git is not installed! Installing Git..." -ForegroundColor Yellow
    # Try to install Git from winget
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    
    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $git = Get-Command git -ErrorAction SilentlyContinue
    
    if (-not $git) {{
        Write-Host "Git installation failed. Please install Git manually." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }}
}}

Write-Host "Git is installed: $($git.Source)" -ForegroundColor Green

# Create odoo-src folder
$odooSrc = Join-Path $odooRoot "odoo-src"
if (-not (Test-Path $odooSrc)) {{
    New-Item -ItemType Directory -Path $odooSrc -Force | Out-Null
}}

# Clone Odoo 19
$odoo19 = Join-Path $odooSrc "odoo-19.0"
if (-not (Test-Path $odoo19)) {{
    Write-Host "Cloning Odoo 19.0 (this may take a while)..." -ForegroundColor Yellow
    git clone --depth 1 --branch 19.0 https://github.com/odoo/odoo.git $odoo19
    
    if ($LASTEXITCODE -ne 0) {{
        Write-Host "Clone failed! Check internet connection." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }}
}} else {{
    Write-Host "Odoo 19.0 already exists at $odoo19" -ForegroundColor Green
}}

# Find Python
$pythonPaths = @(
    "$env:LOCALAPPDATA\\Programs\\Python\\Python311\\python.exe",
    "$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe",
    "C:\\Program Files\\Python311\\python.exe",
    "C:\\Program Files\\Python312\\python.exe"
)

$python = $null
foreach ($p in $pythonPaths) {{
    if (Test-Path $p) {{
        $python = $p
        break
    }}
}}

if (-not $python) {{
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}}

if (-not $python) {{
    Write-Host "Python not found! Please install Python first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}}

# Create venv
$venvPath = Join-Path $odooRoot "venv"
if (-not (Test-Path $venvPath)) {{
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    & $python -m venv $venvPath
}}

$venvPython = Join-Path $venvPath "Scripts\\python.exe"
$venvPip = Join-Path $venvPath "Scripts\\pip.exe"

# Upgrade pip in venv
Write-Host "Upgrading pip in venv..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip

# Install requirements
Write-Host "Installing Odoo requirements..." -ForegroundColor Yellow
$reqFile = Join-Path $odoo19 "requirements.txt"
if (Test-Path $reqFile) {{
    & $venvPip install -r $reqFile
}}

# Create start_odoo.ps1
$startScript = @"
param([switch]`$NoBrowser)
`$venv = Join-Path `$PSScriptRoot "venv\\Scripts\\python.exe"
`$odooBin = Join-Path `$PSScriptRoot "odoo-src\\odoo-19.0\\odoo-bin"
if (-not `$NoBrowser) {{
    Start-Process "http://localhost:8069" -ErrorAction SilentlyContinue
}}
& `$venv `$odooBin -c (Join-Path `$PSScriptRoot "odoo.conf")
"@

$startFile = Join-Path $odooRoot "start_odoo.ps1"
Set-Content -Path $startFile -Value $startScript -Encoding UTF8

# Create odoo.conf
$odooConf = @"
[options]
addons_path = $odooSrc/odoo-19.0/addons
data_dir = $odooRoot/data
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
http_port = 8069
admin_passwd = admin
"@

$confFile = Join-Path $odooRoot "odoo.conf"
if (-not (Test-Path $confFile)) {{
    Set-Content -Path $confFile -Value $odooConf -Encoding UTF8
}}

# Create data folder
$dataDir = Join-Path $odooRoot "data"
if (-not (Test-Path $dataDir)) {{
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}}

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Odoo workspace created successfully!" -ForegroundColor Green
Write-Host "  Location: $odooRoot" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Read-Host "Press Enter to close"
'''
            tmp = TEMP_DIR / 'setup_odoo_workspace_tmp.ps1'
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(script, encoding='utf-8')
            pid = run_powershell_elevated_file(tmp, wait=False)
            return {'pid': pid, 'status': 'setting up Odoo workspace'}
            
    except Exception as e:
        return {'error': str(e)}
    return {'error': 'unknown command'}


def find_installer(folder):
    p = OFFLINE / folder
    if not p.exists():
        return None
    # Find .exe and .msi installers
    exes = list(p.glob('*.exe')) + list(p.glob('*.msi'))
    if not exes:
        return None
    # prefer largest file (likely full installer)
    exes.sort(key=lambda x: x.stat().st_size, reverse=True)
    return str(exes[0].resolve())


if __name__ == '__main__':
    web_dir_candidates = [
        BASE / 'web',
        Path.cwd() / 'web',
        Path(__file__).resolve().parent / 'web',
    ]
    web_dir = next((p for p in web_dir_candidates if p.exists()), None)
    if not web_dir:
        raise FileNotFoundError(
            "Could not find 'web' folder. Looked in: "
            + ", ".join(str(p) for p in web_dir_candidates)
        )

    os.chdir(str(web_dir))
    handler = Handler

    class _ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    def _is_listening(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except Exception:
            return False

    def _open_browser(url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            try:
                os.startfile(url)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _run_server(port: int) -> None:
        with _ReusableThreadingTCPServer(('127.0.0.1', port), handler) as httpd:
            url = f"http://127.0.0.1:{port}"
            print(f"Serving UI on {url}")
            _open_browser(url)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                httpd.shutdown()

    try:
        _run_server(PORT)
    except OSError as e:
        winerr = getattr(e, "winerror", None)
        if winerr == 10048:
            # Port in use: if an instance is already running, just open it.
            if _is_listening(PORT):
                _open_browser(f"http://127.0.0.1:{PORT}")
                sys.exit(0)

            # Otherwise try a small range of fallback ports.
            for p in range(PORT + 1, PORT + 21):
                try:
                    _run_server(p)
                    break
                except OSError:
                    continue
            else:
                raise
        else:
            raise
