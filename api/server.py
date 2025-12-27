# -*- coding: utf-8 -*-
"""
OdooMaster Website API Server
Backend for user authentication, licenses, and downloads
"""

from flask import Flask, request, jsonify, send_file, session, send_from_directory, abort, Response
from flask_cors import CORS
from functools import wraps
import base64
import hashlib
import secrets
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

# License v2 signing (requires cryptography on the server)
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# License private key - load from environment variable or file
LICENSE_PRIVATE_KEY_PEM = os.environ.get('LICENSE_PRIVATE_KEY')
LICENSE_PRIVATE_KEY_FILE = None

if not LICENSE_PRIVATE_KEY_PEM:
    # Try multiple possible file locations
    _possible_key_paths = [
        Path(__file__).parent.parent / 'license_private_key.pem',  # project root
        Path(__file__).parent / 'license_private_key.pem',  # api folder
        Path('/var/lib/odoo/license_private_key.pem'),  # Liara disk
    ]
    for _kp in _possible_key_paths:
        if _kp.exists():
            LICENSE_PRIVATE_KEY_FILE = _kp
            break
    if LICENSE_PRIVATE_KEY_FILE is None:
        LICENSE_PRIVATE_KEY_FILE = _possible_key_paths[0]  # fallback for error messages

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

# Database paths
BASE_DIR = Path(__file__).parent.parent

# Use persistent disk on Liara, fallback to local data/ for development
LIARA_DISK_PATH = Path("/var/lib/odoo/data")
LOCAL_DATA_PATH = BASE_DIR / "data"

# Check if running on Liara (disk mounted)
if Path("/var/lib/odoo").exists():
    DATA_DIR = LIARA_DISK_PATH
else:
    DATA_DIR = LOCAL_DATA_PATH

# Only create directory if filesystem is writable
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # Read-only filesystem on cloud platforms

USERS_FILE = DATA_DIR / "users.json"
LICENSES_FILE = DATA_DIR / "licenses.json"
DOWNLOADS_FILE = DATA_DIR / "downloads.json"
TICKETS_FILE = DATA_DIR / "tickets.json"
PLANS_FILE = DATA_DIR / "plans.json"

# Public catalog (checked into repo)
DOWNLOAD_CATALOG_FILE = BASE_DIR / "downloads.json"

# Private downloadable artifacts (NOT meant for direct public hosting)
DOWNLOAD_FILES_DIR = BASE_DIR / "private_downloads" / "installers"
# Only create directory if filesystem is writable (not on Liara/cloud)
try:
    DOWNLOAD_FILES_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # Read-only filesystem on cloud platforms

# Signed, short-lived download tokens
DOWNLOAD_TOKENS_FILE = DATA_DIR / "download_tokens.json"

# Purchases (for future real payment gateway integration)
PURCHASES_FILE = DATA_DIR / "purchases.json"

DOWNLOAD_TOKEN_TTL_SECONDS = 60 * 30  # 30 minutes

# Frontend files (single-port mode): serve from website/ while protecting private data
FRONTEND_DIR = BASE_DIR
FRONTEND_DENY_PREFIXES = (
    'api/',
    'data/',
    'private_downloads/',
    'tools/',
)

# ============================================
# Database Helpers
# ============================================

def load_json(filepath):
    """Load JSON file or return empty dict/list"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # If file is empty/corrupted, fall back to sane defaults.
            pass
    return {} if 'users' in str(filepath) or 'licenses' in str(filepath) else []


def load_json_default(filepath: Path, default):
    """Load JSON file or return provided default."""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def load_download_catalog() -> dict:
    """Load the public downloads catalog (website/downloads.json)."""
    return load_json_default(DOWNLOAD_CATALOG_FILE, {})


def find_catalog_item(download_id: str) -> dict | None:
    catalog = load_download_catalog()
    versions = catalog.get('versions') or []
    for v in versions:
        for item in (v.get('items') or []):
            if item.get('id') == download_id:
                return item
    return None


def get_optional_user():
    """Return current user dict if Authorization Bearer token is valid, else None."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    if not token:
        return None
    users = load_json(USERS_FILE)
    for u in users.values():
        if u.get('token') == token:
            return u
    return None


def user_has_paid_license(user_id: str) -> bool:
    """Check if user has an active non-trial license."""
    if not user_id:
        return False
    licenses = load_json(LICENSES_FILE)
    now = datetime.now()
    for lic in licenses.values():
        if lic.get('user_id') != user_id:
            continue
        if lic.get('status') != 'active':
            continue
        if (lic.get('plan') or '').strip().lower() == 'trial':
            continue
        exp = lic.get('expires_at')
        try:
            if exp and datetime.fromisoformat(exp) < now:
                continue
        except Exception:
            continue
        return True
    return False

def save_json(filepath, data):
    """Save data to JSON file"""
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except OSError as e:
        # Read-only filesystem (e.g., Liara without disk)
        print(f"[WARNING] Cannot save to {filepath}: {e}")
        return False


class StorageError(Exception):
    """Raised when storage is unavailable (read-only filesystem)"""
    pass


def save_json_or_raise(filepath, data):
    """Save data to JSON file or raise StorageError if filesystem is read-only"""
    if not save_json(filepath, data):
        raise StorageError("فایل سیستم فقط‌خواندنی است. لطفاً دیسک فعال کنید.")

def hash_password(password):
    """Hash password with SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================
# Default Admin User (created on first load)
# ============================================
def ensure_default_admin():
    """Create default admin user if no users exist"""
    users = load_json(USERS_FILE)
    admin_id = 'admin@odoomaster.ir'
    
    # Always ensure admin exists
    if admin_id not in users:
        users[admin_id] = {
            'id': admin_id,
            'name': 'مدیر سیستم',
            'email': admin_id,
            'phone': '09961979369',
            'password': hash_password('Admin@123'),
            'is_admin': True,
            'is_verified': True,
            'created_at': datetime.now().isoformat(),
            'xp': 0,
            'level': 999
        }
        try:
            save_json(USERS_FILE, users)
            print(f"[INFO] Admin user created: {admin_id}")
        except OSError as e:
            print(f"[ERROR] Could not save admin user: {e}")

# Run on startup
ensure_default_admin()

# Temporary endpoint to reset admin (remove after first use!)
@app.route('/api/reset-admin', methods=['GET'])
def reset_admin():
    """Reset admin user - TEMPORARY ENDPOINT"""
    users = load_json(USERS_FILE)
    admin_id = 'admin@odoomaster.ir'
    users[admin_id] = {
        'id': admin_id,
        'name': 'مدیر سیستم',
        'email': admin_id,
        'phone': '09961979369',
        'password': hash_password('Admin@123'),
        'is_admin': True,
        'is_verified': True,
        'created_at': datetime.now().isoformat(),
        'xp': 0,
        'level': 999
    }
    try:
        save_json(USERS_FILE, users)
        return jsonify({'success': True, 'message': 'Admin reset successfully', 'email': admin_id, 'password': 'Admin@123'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_license_key():
    """Generate a unique license key"""
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    parts = []
    for _ in range(4):
        part = ''.join(secrets.choice(chars) for _ in range(5))
        parts.append(part)
    return '-'.join(parts)

# ============================================
# Authentication Decorator
# ============================================

def extract_bearer_token() -> str:
    """Extract Bearer token from Authorization header.

    Accepts common variations like extra whitespace or different casing.
    Returns empty string if header is missing or malformed.
    """
    auth = (request.headers.get('Authorization') or '').strip()
    if not auth:
        return ''

    # Typical format: "Bearer <token>"
    parts = auth.split()
    if len(parts) >= 2 and parts[0].lower() == 'bearer':
        return parts[1].strip()

    # Fallback: tolerate "Bearer<space?>token" style
    if auth.lower().startswith('bearer'):
        return auth[6:].strip()

    return auth.strip()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = extract_bearer_token()
        if not token:
            return jsonify({'error': 'توکن احراز هویت یافت نشد'}), 401
        
        users = load_json(USERS_FILE)
        user = None
        for u in users.values():
            if (u.get('token') or '').strip() == token:
                user = u
                break
        
        if not user:
            return jsonify({'error': 'توکن نامعتبر است'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = extract_bearer_token()
        if not token:
            return jsonify({'error': 'توکن احراز هویت یافت نشد'}), 401
        
        users = load_json(USERS_FILE)
        user = None
        for u in users.values():
            if (u.get('token') or '').strip() == token:
                user = u
                break
        
        if not user:
            return jsonify({'error': 'توکن نامعتبر است'}), 401
        
        if not user.get('is_admin'):
            return jsonify({'error': 'دسترسی مدیریتی ندارید'}), 403
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated

# ============================================
# Auth Endpoints
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json
    
    # Validate required fields
    required = ['name', 'email', 'phone', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'فیلد {field} الزامی است'}), 400
    
    # Validate email format
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
        return jsonify({'error': 'ایمیل نامعتبر است'}), 400
    
    # Validate phone format
    if not re.match(r'^09\d{9}$', data['phone'].replace(' ', '')):
        return jsonify({'error': 'شماره موبایل نامعتبر است'}), 400
    
    # Check if email exists
    users = load_json(USERS_FILE)
    if data['email'] in users:
        return jsonify({'error': 'این ایمیل قبلاً ثبت شده است'}), 400
    
    # Create user
    user_id = secrets.token_hex(8)
    token = secrets.token_hex(32)
    
    user = {
        'id': user_id,
        'name': data['name'],
        'email': data['email'],
        'phone': data['phone'],
        'password': hash_password(data['password']),
        'token': token,
        'xp': 100,  # Welcome bonus
        'level': 1,
        'achievements': ['welcome'],
        'created_at': datetime.now().isoformat(),
        'last_login': datetime.now().isoformat(),
        'is_verified': False
    }
    
    users[data['email']] = user
    
    # Try to save - handle read-only filesystem
    try:
        save_json_or_raise(USERS_FILE, users)
    except StorageError as e:
        return jsonify({'error': str(e)}), 503
    
    # Create welcome license (trial)
    licenses = load_json(LICENSES_FILE)
    trial_license = {
        'key': generate_license_key(),
        'user_id': user_id,
        'user_email': data['email'],
        'plan': 'trial',
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
        'max_activations': 1,
        'activations': 0
    }
    licenses[trial_license['key']] = trial_license
    
    try:
        save_json_or_raise(LICENSES_FILE, licenses)
    except StorageError as e:
        return jsonify({'error': str(e)}), 503
    
    return jsonify({
        'success': True,
        'message': 'ثبت‌نام با موفقیت انجام شد',
        'user': {
            'id': user_id,
            'name': user['name'],
            'email': user['email'],
            'xp': user['xp'],
            'level': user['level'],
            'is_admin': bool(user.get('is_admin'))
        },
        'token': token,
        'trial_license': trial_license['key']
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.json

    identifier = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({'error': 'ایمیل/موبایل و رمز عبور الزامی است'}), 400

    users = load_json(USERS_FILE)

    # Support login by email or phone (identifier may be either).
    user = users.get(identifier)
    if not user:
        normalized_phone = re.sub(r'\s+', '', identifier)
        for u in users.values():
            if re.sub(r'\s+', '', str(u.get('phone') or '')) == normalized_phone:
                user = u
                break

    if not user or user.get('password') != hash_password(password):
        return jsonify({'error': 'ایمیل/موبایل یا رمز عبور اشتباه است'}), 401
    
    # Generate new token
    token = secrets.token_hex(32)
    user['token'] = token
    user['last_login'] = datetime.now().isoformat()
    
    # Add login XP
    user['xp'] = user.get('xp', 0) + 10
    
    save_json(USERS_FILE, users)
    
    return jsonify({
        'success': True,
        'message': 'ورود موفقیت‌آمیز',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'xp': user.get('xp', 0),
            'level': user.get('level', 1),
            'is_admin': bool(user.get('is_admin'))
        },
        'token': token
    })

@app.route('/api/auth/admin-login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    data = request.json
    
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    
    if not username or not password:
        return jsonify({'error': 'نام کاربری و رمز عبور الزامی است'}), 400
    
    # Load admin config
    try:
        from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD
    except ImportError:
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "odoo@2025"
    
    # Check admin credentials
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return jsonify({'error': 'نام کاربری یا رمز عبور اشتباه است'}), 401
    
    # Generate admin token
    token = secrets.token_hex(32)
    
    # Find or create admin user in database
    users = load_json(USERS_FILE)
    admin_email = "admin@odoomaster.com"
    
    if admin_email not in users:
        # Create admin user
        users[admin_email] = {
            'id': 'admin',
            'name': 'مدیر سیستم',
            'email': admin_email,
            'phone': '09000000000',
            'password': hash_password(ADMIN_PASSWORD),
            'token': token,
            'xp': 0,
            'level': 999,
            'achievements': ['admin'],
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat(),
            'is_admin': True,
            'is_verified': True
        }
    else:
        # Update token and last login
        users[admin_email]['token'] = token
        users[admin_email]['last_login'] = datetime.now().isoformat()
        users[admin_email]['is_admin'] = True
    
    save_json(USERS_FILE, users)
    
    return jsonify({
        'success': True,
        'message': 'ورود موفقیت‌آمیز',
        'user': {
            'id': 'admin',
            'name': 'مدیر سیستم',
            'email': admin_email,
            'is_admin': True
        },
        'token': token
    })

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    users = load_json(USERS_FILE)
    if request.current_user['email'] in users:
        users[request.current_user['email']]['token'] = None
        save_json(USERS_FILE, users)
    
    return jsonify({'success': True, 'message': 'خروج موفقیت‌آمیز'})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    user = request.current_user
    
    # Get user's licenses
    licenses = load_json(LICENSES_FILE)
    user_licenses = [l for l in licenses.values() if l.get('user_id') == user['id']]
    
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'phone': user.get('phone'),
            'xp': user.get('xp', 0),
            'level': user.get('level', 1),
            'achievements': user.get('achievements', []),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login'),
            'is_admin': bool(user.get('is_admin'))
        },
        'licenses': user_licenses,
        'stats': {
            'total_licenses': len(user_licenses),
            'active_licenses': len([l for l in user_licenses if l['status'] == 'active']),
            'total_downloads': user.get('downloads', 0)
        }
    })

# ============================================
# License Endpoints
# ============================================

@app.route('/api/licenses', methods=['GET'])
@login_required
def get_licenses():
    """Get user's licenses"""
    licenses = load_json(LICENSES_FILE)
    user_licenses = [l for l in licenses.values() if l.get('user_id') == request.current_user['id']]
    
    return jsonify({'licenses': user_licenses})

@app.route('/api/licenses/activate', methods=['POST'])
@login_required
def activate_license():
    """Activate a license on a device"""
    data = request.json
    license_key = data.get('license_key')
    hardware_id = data.get('hardware_id')
    
    if not license_key or not hardware_id:
        return jsonify({'error': 'کلید لایسنس و شناسه سخت‌افزار الزامی است'}), 400
    
    licenses = load_json(LICENSES_FILE)
    license_data = licenses.get(license_key)
    
    if not license_data:
        return jsonify({'error': 'لایسنس یافت نشد'}), 404
    
    if license_data['user_id'] != request.current_user['id']:
        return jsonify({'error': 'این لایسنس متعلق به شما نیست'}), 403
    
    if license_data['status'] != 'active':
        return jsonify({'error': 'این لایسنس فعال نیست'}), 400
    
    # Check expiration (expires_at can be null for unlimited licenses)
    exp = license_data.get('expires_at')
    if exp and datetime.fromisoformat(exp) < datetime.now():
        license_data['status'] = 'expired'
        save_json(LICENSES_FILE, licenses)
        return jsonify({'error': 'این لایسنس منقضی شده است'}), 400
    
    # Check activations
    if license_data['activations'] >= license_data['max_activations']:
        return jsonify({'error': 'تعداد فعال‌سازی به حداکثر رسیده است'}), 400
    
    # Activate
    license_data['activations'] += 1
    license_data['hardware_ids'] = license_data.get('hardware_ids', [])
    if hardware_id not in license_data['hardware_ids']:
        license_data['hardware_ids'].append(hardware_id)
    license_data['last_activated'] = datetime.now().isoformat()
    
    save_json(LICENSES_FILE, licenses)
    
    # Add XP for activation
    users = load_json(USERS_FILE)
    if request.current_user['email'] in users:
        users[request.current_user['email']]['xp'] += 50
        save_json(USERS_FILE, users)
    
    return jsonify({
        'success': True,
        'message': 'لایسنس با موفقیت فعال شد',
        'license': license_data
    })

@app.route('/api/licenses/verify', methods=['POST'])
def verify_license():
    """Verify a license (public endpoint for installer)"""
    data = request.json
    license_key = data.get('license_key')
    hardware_id = data.get('hardware_id')
    
    if not license_key:
        return jsonify({'valid': False, 'error': 'کلید لایسنس الزامی است'}), 400
    
    licenses = load_json(LICENSES_FILE)
    license_data = licenses.get(license_key)
    
    if not license_data:
        return jsonify({'valid': False, 'error': 'لایسنس یافت نشد'}), 404
    
    if license_data['status'] != 'active':
        return jsonify({'valid': False, 'error': 'لایسنس فعال نیست'}), 400
    
    # Check expiration (expires_at can be null for unlimited licenses)
    exp = license_data.get('expires_at')
    if exp and datetime.fromisoformat(exp) < datetime.now():
        return jsonify({'valid': False, 'error': 'لایسنس منقضی شده'}), 400
    
    # Check hardware if provided
    if hardware_id and license_data.get('hardware_ids'):
        if hardware_id not in license_data['hardware_ids']:
            return jsonify({'valid': False, 'error': 'این لایسنس روی دستگاه دیگری فعال شده'}), 400
    
    return jsonify({
        'valid': True,
        'plan': license_data['plan'],
        'expires_at': license_data['expires_at']
    })

# ============================================
# Download Endpoints
# ============================================

@app.route('/api/downloads', methods=['GET'])
def get_downloads():
    """Get available downloads (from public catalog)."""
    catalog = load_download_catalog()
    if not catalog:
        return jsonify({'downloads': []})

    # Flatten for API clients; website UI reads downloads.json directly.
    items = []
    for v in (catalog.get('versions') or []):
        for item in (v.get('items') or []):
            items.append(item)
    return jsonify({'downloads': items, 'generated_at': catalog.get('generated_at')})

@app.route('/api/downloads/<download_id>', methods=['POST'])
def request_download(download_id):
    """Request a signed download link.

    Auth is optional for public artifacts, but required when catalog says so.
    """
    item = find_catalog_item(download_id)
    if not item:
        return jsonify({'error': 'دانلود یافت نشد'}), 404

    requires_login = bool(item.get('requires_login'))
    requires_purchase = bool(item.get('requires_purchase'))

    user = get_optional_user()
    if requires_login and not user:
        return jsonify({'error': 'برای دانلود ابتدا وارد شوید'}), 401

    user_id = user.get('id') if user else ''
    if requires_purchase:
        if not user:
            return jsonify({'error': 'برای دانلود ابتدا وارد شوید'}), 401
        if not user_has_paid_license(user_id):
            return jsonify({'error': 'برای دانلود این فایل، خرید/لایسنس معتبر لازم است'}), 403

    # Log download request (best-effort)
    if user:
        users = load_json(USERS_FILE)
        if user.get('email') in users:
            users[user['email']]['downloads'] = users[user['email']].get('downloads', 0) + 1
            users[user['email']]['xp'] = users[user['email']].get('xp', 0) + 25
            save_json(USERS_FILE, users)

    token = secrets.token_hex(16)
    tokens = load_json_default(DOWNLOAD_TOKENS_FILE, {})
    expires_at = (datetime.now() + timedelta(seconds=DOWNLOAD_TOKEN_TTL_SECONDS)).isoformat()
    tokens[token] = {
        'download_id': download_id,
        'user_id': user_id,
        'expires_at': expires_at,
    }
    save_json(DOWNLOAD_TOKENS_FILE, tokens)

    return jsonify({
        'success': True,
        'download_url': f'/api/downloads/file/{download_id}?token={token}',
        'expires_in': DOWNLOAD_TOKEN_TTL_SECONDS,
    })


@app.route('/api/downloads/file/<download_id>', methods=['GET'])
def download_file(download_id):
    """Serve a private artifact if token is valid and requirements are met."""
    token = (request.args.get('token') or '').strip()
    if not token:
        return jsonify({'error': 'توکن دانلود الزامی است'}), 400

    item = find_catalog_item(download_id)
    if not item:
        return jsonify({'error': 'دانلود یافت نشد'}), 404

    tokens = load_json_default(DOWNLOAD_TOKENS_FILE, {})
    entry = tokens.get(token)
    if not entry or entry.get('download_id') != download_id:
        return jsonify({'error': 'توکن دانلود نامعتبر است'}), 403

    # expiry
    try:
        if datetime.fromisoformat(entry.get('expires_at', '')) < datetime.now():
            tokens.pop(token, None)
            save_json(DOWNLOAD_TOKENS_FILE, tokens)
            return jsonify({'error': 'توکن دانلود منقضی شده است'}), 403
    except Exception:
        return jsonify({'error': 'توکن دانلود نامعتبر است'}), 403

    requires_login = bool(item.get('requires_login'))
    requires_purchase = bool(item.get('requires_purchase'))

    user_id = (entry.get('user_id') or '').strip()
    if requires_login and not user_id:
        return jsonify({'error': 'این فایل نیازمند ورود است'}), 403

    if requires_purchase and not user_has_paid_license(user_id):
        return jsonify({'error': 'لایسنس معتبر برای دانلود لازم است'}), 403

    file_name = (item.get('file_name') or '').strip()
    if not file_name:
        return jsonify({'error': 'فایل Release تنظیم نشده است'}), 404

    file_path = (DOWNLOAD_FILES_DIR / file_name).resolve()
    if not file_path.exists():
        return jsonify({'error': 'فایل روی سرور موجود نیست'}), 404

    # IMPORTANT: Download managers may open multiple GETs (range requests, retries,
    # parallel connections). Treat the token as reusable until it expires.
    # This avoids 403s after an initial successful probe request.

    resp = send_file(
        str(file_path),
        as_attachment=True,
        download_name=file_name,
        mimetype='application/zip'
    )
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# ============================================
# Frontend (Optional single-port mode)
# ============================================

@app.route('/', methods=['GET'])
def serve_index():
    """Serve the website index page from the same Flask server."""
    return send_from_directory(str(FRONTEND_DIR), 'index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_frontend_file(path: str):
    """Serve static files for the website.

    Security: blocks access to `data/` and `private_downloads/`.
    """
    normalized = (path or '').replace('\\', '/').lstrip('/')

    # Block sensitive folders
    lowered = normalized.lower()
    for prefix in FRONTEND_DENY_PREFIXES:
        if lowered.startswith(prefix):
            abort(404)

    # Block dotfiles
    if any(part.startswith('.') for part in lowered.split('/') if part):
        abort(404)

    file_path = (FRONTEND_DIR / normalized).resolve()
    try:
        if not file_path.exists() or not file_path.is_file():
            abort(404)
        # ensure within FRONTEND_DIR
        if FRONTEND_DIR not in file_path.parents and file_path != FRONTEND_DIR:
            abort(404)
    except Exception:
        abort(404)

    return send_from_directory(str(FRONTEND_DIR), normalized)

# ============================================
# Ticket Endpoints
# ============================================

@app.route('/api/tickets', methods=['GET'])
@login_required
def get_tickets():
    """Get user's tickets"""
    tickets = load_json(TICKETS_FILE)
    user_tickets = [t for t in tickets if t.get('user_id') == request.current_user['id']]
    
    return jsonify({'tickets': user_tickets})

@app.route('/api/tickets', methods=['POST'])
@login_required
def create_ticket():
    """Create a new support ticket"""
    data = request.json
    
    if not data.get('subject') or not data.get('message'):
        return jsonify({'error': 'موضوع و پیام الزامی است'}), 400
    
    tickets = load_json(TICKETS_FILE)
    
    ticket = {
        'id': secrets.token_hex(8),
        'user_id': request.current_user['id'],
        'user_email': request.current_user['email'],
        'user_name': request.current_user['name'],
        'subject': data['subject'],
        'category': data.get('category', 'general'),
        'priority': data.get('priority', 'normal'),
        'status': 'open',
        'messages': [
            {
                'sender': 'user',
                'message': data['message'],
                'timestamp': datetime.now().isoformat()
            }
        ],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    tickets.append(ticket)
    save_json(TICKETS_FILE, tickets)
    
    return jsonify({
        'success': True,
        'message': 'تیکت با موفقیت ایجاد شد',
        'ticket': ticket
    })

# ============================================
# Gamification Endpoints
# ============================================

@app.route('/api/achievements', methods=['GET'])
def get_achievements():
    """Get all available achievements"""
    achievements = [
        {'id': 'welcome', 'name': 'خوش‌آمدید!', 'description': 'ثبت‌نام در سایت', 'xp': 100, 'icon': 'fa-door-open'},
        {'id': 'first_download', 'name': 'اولین دانلود', 'description': 'دانلود اولین نسخه', 'xp': 50, 'icon': 'fa-download'},
        {'id': 'first_install', 'name': 'نصاب', 'description': 'اولین نصب موفق Odoo', 'xp': 100, 'icon': 'fa-check-circle'},
        {'id': 'ticket_master', 'name': 'تیکت‌باز', 'description': 'ارسال ۵ تیکت', 'xp': 75, 'icon': 'fa-headset'},
        {'id': 'pro_user', 'name': 'کاربر حرفه‌ای', 'description': 'خرید لایسنس Pro', 'xp': 200, 'icon': 'fa-crown'},
        {'id': 'veteran', 'name': 'کهنه‌کار', 'description': '۱ سال عضویت', 'xp': 500, 'icon': 'fa-medal'},
        {'id': 'multi_install', 'name': 'چند نصبه', 'description': 'نصب روی ۳ سیستم', 'xp': 150, 'icon': 'fa-server'},
        {'id': 'feedback', 'name': 'نظردهنده', 'description': 'ارسال بازخورد', 'xp': 50, 'icon': 'fa-comment'}
    ]
    
    return jsonify({'achievements': achievements})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top users by XP"""
    users = load_json(USERS_FILE)
    
    leaderboard = []
    for user in users.values():
        leaderboard.append({
            'name': user['name'],
            'xp': user.get('xp', 0),
            'level': user.get('level', 1)
        })
    
    leaderboard.sort(key=lambda x: x['xp'], reverse=True)
    
    return jsonify({'leaderboard': leaderboard[:10]})

# ============================================
# Stats Endpoints
# ============================================

@app.route('/api/stats', methods=['GET'])
def get_public_stats():
    """Get public statistics"""
    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)
    
    return jsonify({
        'total_users': len(users),
        'total_licenses': len(licenses),
        'total_downloads': sum(u.get('downloads', 0) for u in users.values()),
        'active_licenses': len([l for l in licenses.values() if l['status'] == 'active'])
    })

# ============================================
# Pricing/Plans Endpoints
# ============================================

def get_default_plans():
    """Default plans if plans.json doesn't exist"""
    return {
        'starter': {
            'id': 'starter',
            'name': 'استارتر',
            'name_en': 'Starter',
            'price': 990000,
            'price_yearly': 9900000,
            'features': ['نصب روی ۱ سیستم', 'پشتیبانی ایمیلی', 'آپدیت ۶ ماهه', 'نسخه Odoo 19'],
            'features_en': ['Install on 1 system', 'Email support', '6 months updates', 'Odoo 19 version'],
            'max_activations': 1,
            'support_level': 'email',
            'duration_unit': 'days',
            'duration_value': 180,
            'duration_days': 180,
            'popular': False,
            'active': True,
            'sort_order': 1
        },
        'pro': {
            'id': 'pro',
            'name': 'حرفه‌ای',
            'name_en': 'Professional',
            'price': 1990000,
            'price_yearly': 19900000,
            'features': ['نصب روی ۳ سیستم', 'پشتیبانی تلفنی', 'آپدیت ۱ ساله', 'تمام نسخه‌های Odoo', 'افزونه‌های فارسی'],
            'features_en': ['Install on 3 systems', 'Phone support', '1 year updates', 'All Odoo versions', 'Persian add-ons'],
            'max_activations': 3,
            'support_level': 'phone',
            'duration_unit': 'days',
            'duration_value': 365,
            'duration_days': 365,
            'popular': True,
            'active': True,
            'sort_order': 2
        },
        'enterprise': {
            'id': 'enterprise',
            'name': 'سازمانی',
            'name_en': 'Enterprise',
            'price': 4990000,
            'price_yearly': 49900000,
            'features': ['نصب نامحدود', 'پشتیبانی ۲۴/۷', 'آپدیت مادام‌العمر', 'تمام نسخه‌های Odoo', 'افزونه‌های فارسی', 'آموزش اختصاصی', 'نصب و راه‌اندازی'],
            'features_en': ['Unlimited installs', '24/7 support', 'Lifetime updates', 'All Odoo versions', 'Persian add-ons', 'Custom training', 'Setup & installation'],
            'max_activations': 999,
            'support_level': 'priority',
            'duration_unit': 'days',
            'duration_value': 730,
            'duration_days': 730,
            'popular': False,
            'active': True,
            'sort_order': 3
        }
    }


def _plan_duration_delta(plan: dict) -> timedelta | None:
    """Return timedelta for plan duration.

    Supports:
      - duration_unit: 'hours'|'days'
      - duration_value: int
    Backward compatible with duration_days.
    Returns None for unlimited duration.
    """
    if not plan:
        return None

    unit = (plan.get('duration_unit') or '').strip().lower()
    value = plan.get('duration_value', None)

    # Backward compat
    if not unit:
        unit = 'days'
    if value is None:
        value = plan.get('duration_days', None)

    try:
        value_int = int(value)
    except Exception:
        value_int = 0

    if value_int <= 0:
        return None

    if unit == 'hours':
        return timedelta(hours=value_int)
    # default to days
    return timedelta(days=value_int)

def load_plans():
    """Load plans from JSON file or return defaults"""
    if PLANS_FILE.exists():
        try:
            plans = load_json(PLANS_FILE)
            if plans:
                return plans
        except Exception:
            pass
    # Create default plans file
    default_plans = get_default_plans()
    save_json(PLANS_FILE, default_plans)
    return default_plans

@app.route('/api/plans', methods=['GET'])
def get_plans():
    """Get available plans (public)"""
    plans_dict = load_plans()
    # Return only active plans, sorted by sort_order
    plans_list = [p for p in plans_dict.values() if p.get('active', True)]
    plans_list.sort(key=lambda x: x.get('sort_order', 999))
    return jsonify({'plans': plans_list})


@app.route('/api/admin/plans', methods=['GET'])
@login_required
def admin_get_plans():
    """Get all plans for admin (including inactive)"""
    if not request.current_user.get('is_admin'):
        return jsonify({'error': 'دسترسی مجاز نیست'}), 403
    
    plans_dict = load_plans()
    plans_list = list(plans_dict.values())
    plans_list.sort(key=lambda x: x.get('sort_order', 999))
    return jsonify({'plans': plans_list})


@app.route('/api/admin/plans', methods=['POST'])
@login_required
def admin_create_plan():
    """Create a new plan"""
    if not request.current_user.get('is_admin'):
        return jsonify({'error': 'دسترسی مجاز نیست'}), 403
    
    data = request.json or {}
    plan_id = (data.get('id') or '').strip().lower()
    
    if not plan_id:
        return jsonify({'error': 'شناسه پلن الزامی است'}), 400
    
    if not re.match(r'^[a-z0-9_-]+$', plan_id):
        return jsonify({'error': 'شناسه پلن فقط می‌تواند شامل حروف انگلیسی، اعداد، خط تیره و زیرخط باشد'}), 400
    
    plans = load_plans()
    if plan_id in plans:
        return jsonify({'error': 'این شناسه قبلاً استفاده شده است'}), 400
    
    # Build new plan
    duration_unit = (data.get('duration_unit') or '').strip().lower() or 'days'
    duration_value = data.get('duration_value', None)
    if duration_value is None:
        duration_value = data.get('duration_days', 30)

    new_plan = {
        'id': plan_id,
        'name': data.get('name', ''),
        'name_en': data.get('name_en', ''),
        'price': int(data.get('price', 0)),
        'price_yearly': int(data.get('price_yearly', 0)),
        'features': data.get('features', []),
        'features_en': data.get('features_en', []),
        'max_activations': int(data.get('max_activations', 1)),
        'support_level': data.get('support_level', 'email'),
        'duration_unit': duration_unit if duration_unit in ('hours', 'days') else 'days',
        'duration_value': int(duration_value),
        'duration_days': int(data.get('duration_days', duration_value)),
        'popular': bool(data.get('popular', False)),
        'active': bool(data.get('active', True)),
        'sort_order': int(data.get('sort_order', len(plans) + 1))
    }
    
    plans[plan_id] = new_plan
    save_json(PLANS_FILE, plans)
    
    return jsonify({'success': True, 'plan': new_plan})


@app.route('/api/admin/plans/<plan_id>', methods=['PUT'])
@login_required
def admin_update_plan(plan_id):
    """Update an existing plan"""
    if not request.current_user.get('is_admin'):
        return jsonify({'error': 'دسترسی مجاز نیست'}), 403
    
    plans = load_plans()
    if plan_id not in plans:
        return jsonify({'error': 'پلن یافت نشد'}), 404
    
    data = request.json or {}
    plan = plans[plan_id]
    
    # Update fields
    if 'name' in data:
        plan['name'] = data['name']
    if 'name_en' in data:
        plan['name_en'] = data['name_en']
    if 'price' in data:
        plan['price'] = int(data['price'])
    if 'price_yearly' in data:
        plan['price_yearly'] = int(data['price_yearly'])
    if 'features' in data:
        plan['features'] = data['features']
    if 'features_en' in data:
        plan['features_en'] = data['features_en']
    if 'max_activations' in data:
        plan['max_activations'] = int(data['max_activations'])
    if 'support_level' in data:
        plan['support_level'] = data['support_level']
    if 'duration_unit' in data:
        unit = (data.get('duration_unit') or '').strip().lower()
        if unit in ('hours', 'days'):
            plan['duration_unit'] = unit
    if 'duration_value' in data:
        plan['duration_value'] = int(data['duration_value'])
    if 'duration_days' in data:
        # Backward-compatible input
        plan['duration_days'] = int(data['duration_days'])
        if 'duration_value' not in plan:
            plan['duration_value'] = int(data['duration_days'])
        if 'duration_unit' not in plan:
            plan['duration_unit'] = 'days'
    if 'popular' in data:
        plan['popular'] = bool(data['popular'])
    if 'active' in data:
        plan['active'] = bool(data['active'])
    if 'sort_order' in data:
        plan['sort_order'] = int(data['sort_order'])
    
    plans[plan_id] = plan
    save_json(PLANS_FILE, plans)
    
    return jsonify({'success': True, 'plan': plan})


@app.route('/api/admin/plans/<plan_id>', methods=['DELETE'])
@login_required
def admin_delete_plan(plan_id):
    """Delete a plan"""
    if not request.current_user.get('is_admin'):
        return jsonify({'error': 'دسترسی مجاز نیست'}), 403
    
    plans = load_plans()
    if plan_id not in plans:
        return jsonify({'error': 'پلن یافت نشد'}), 404
    
    del plans[plan_id]
    save_json(PLANS_FILE, plans)
    
    return jsonify({'success': True})


def find_plan(plan_id: str) -> dict | None:
    """Return plan dict from the same plans list as /api/plans."""
    if not plan_id:
        return None
    plans = load_plans()
    return plans.get(plan_id)

@app.route('/api/purchase', methods=['POST'])
@login_required
def purchase_plan():
    """Initiate a purchase with hardware binding - STRICT VALIDATION"""
    import re
    
    data = request.json
    plan_id = data.get('plan_id')
    payment_type = data.get('payment_type', 'monthly')
    hardware_id = (data.get('hardware_id') or '').strip()
    customer_name = (data.get('customer_name') or '').strip()
    customer_email = (data.get('customer_email') or '').strip()
    customer_phone = (data.get('customer_phone') or '').strip()

    plan = find_plan(plan_id)
    if not plan:
        return jsonify({'error': 'پلن نامعتبر است'}), 400

    # === STRICT VALIDATION ===
    
    # 1. Validate hardware_id is required and has correct format (16 hex chars from installer)
    if not hardware_id:
        return jsonify({'error': 'شناسه سخت‌افزاری دستگاه الزامی است. از طریق نصب‌کننده اقدام کنید.'}), 400
    
    if not re.match(r'^[a-f0-9]{16}$', hardware_id, re.IGNORECASE):
        return jsonify({'error': 'شناسه سخت‌افزاری نامعتبر است. از طریق نصب‌کننده اقدام کنید.'}), 400

    # 2. Validate customer name
    if not customer_name or len(customer_name) < 3:
        return jsonify({'error': 'نام و نام خانوادگی الزامی است (حداقل ۳ کاراکتر)'}), 400

    # 3. Validate customer email
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not customer_email or not re.match(email_regex, customer_email):
        return jsonify({'error': 'ایمیل معتبر الزامی است'}), 400

    # 4. Validate customer phone (Iranian mobile)
    phone_regex = r'^(0|\+98)?9\d{9}$'
    clean_phone = re.sub(r'[\s\-]', '', customer_phone)
    if not clean_phone or not re.match(phone_regex, clean_phone):
        return jsonify({'error': 'شماره تلفن همراه معتبر الزامی است (مثال: 09123456789)'}), 400

    # === END VALIDATION ===

    user_id = request.current_user['id']
    licenses = load_json(LICENSES_FILE)
    now = datetime.now()

    # Check for duplicate active license for the same hardware_id (prevent abuse)
    for lic in licenses.values():
        if lic.get('user_id') != user_id:
            continue
        if lic.get('status') != 'active':
            continue
        # Skip trial licenses
        if (lic.get('plan') or '').strip().lower() == 'trial':
            continue
        # Check if not expired
        exp = lic.get('expires_at')
        try:
            if exp and datetime.fromisoformat(exp) < now:
                continue
        except Exception:
            continue
        # Check if same hardware_id already bound
        lic_hwids = lic.get('hardware_ids') or []
        if hardware_id in lic_hwids:
            return jsonify({
                'error': 'شما در حال حاضر یک لایسنس فعال برای این دستگاه دارید',
                'existing_license_key': lic.get('key'),
                'expires_at': lic.get('expires_at')
            }), 409

    # In production, integrate with payment gateway (Zarinpal, etc.).
    # For now (pre-gateway), we immediately issue a paid license so download gating can work.
    payment_id = secrets.token_hex(16)

    key = generate_license_key()
    # Ensure uniqueness
    while key in licenses:
        key = generate_license_key()

    delta = _plan_duration_delta(plan)
    expires_at = (now + delta).isoformat() if delta else None

    paid_license = {
        'key': key,
        'user_id': request.current_user['id'],
        'user_email': request.current_user['email'],
        'plan': plan.get('id'),
        'plan_name': plan.get('name'),
        'status': 'active',
        'created_at': now.isoformat(),
        'expires_at': expires_at,
        'max_activations': int(plan.get('max_activations') or 1),
        'activations': 1,
        'payment_id': payment_id,
        'payment_type': payment_type,
        'hardware_ids': [hardware_id],  # Bind to hardware immediately
        'customer_name': customer_name,  # Already validated
        'customer_email': customer_email,  # Already validated
        'customer_phone': clean_phone  # Already validated and cleaned
    }

    licenses[key] = paid_license
    save_json(LICENSES_FILE, licenses)
    
    # Generate signed license file immediately
    payload = {
        'v': 2,
        'license_id': key,
        'plan': plan.get('id'),
        'issued_to': paid_license['user_email'],
        'hardware_id': hardware_id,
        'expires_at': expires_at,
        'issued_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'nonce': secrets.token_hex(8),
    }
    license_file_bundle = _sign_license_v2(payload)

    return jsonify({
        'success': True,
        'message': 'خرید با موفقیت انجام شد و لایسنس صادر گردید',
        'payment_id': payment_id,
        'license_key': key,
        'license': paid_license,
        'license_file': license_file_bundle,  # Include signed license file for immediate download
        'can_download_license_file': license_file_bundle is not None
    })

# ============================================
# Signed License File (v2) Generation
# ============================================

def _canonical_json_bytes(payload: dict) -> bytes:
    """Stable canonical JSON for signing."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _sign_license_v2(payload: dict) -> dict | None:
    """Sign a license payload using RSA-PSS(SHA256).

    Returns the full bundle (payload + sig) or None if signing is unavailable.
    """
    if not CRYPTO_AVAILABLE:
        return None
    
    # Try to load private key from env var first, then from file
    private_key_pem = None
    if LICENSE_PRIVATE_KEY_PEM:
        private_key_pem = LICENSE_PRIVATE_KEY_PEM.encode('utf-8')
    elif LICENSE_PRIVATE_KEY_FILE and LICENSE_PRIVATE_KEY_FILE.exists():
        private_key_pem = LICENSE_PRIVATE_KEY_FILE.read_bytes()
    
    if not private_key_pem:
        return None
    
    try:
        private_key = load_pem_private_key(private_key_pem, password=None)
        message = _canonical_json_bytes(payload)
        sig = private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        bundle = dict(payload)
        bundle['sig'] = base64.b64encode(sig).decode('utf-8')
        return bundle
    except Exception:
        return None


@app.route('/api/licenses/<license_key>/file', methods=['POST'])
@login_required
def generate_license_file(license_key):
    """Generate a downloadable signed license file (v2) for a purchased license.

    Request body (optional):
      - hardware_id: bind to a specific device (recommended)

    Returns the license bundle JSON, or a .oml file download if `?download=1`.
    """
    licenses = load_json(LICENSES_FILE)
    lic = licenses.get(license_key)
    if not lic:
        return jsonify({'error': 'لایسنس یافت نشد'}), 404

    # Ownership check
    if lic.get('user_id') != request.current_user['id']:
        return jsonify({'error': 'شما مالک این لایسنس نیستید'}), 403

    if lic.get('status') != 'active':
        return jsonify({'error': 'لایسنس فعال نیست'}), 400

    data = request.json or {}
    hardware_id = (data.get('hardware_id') or '').strip()

    payload = {
        'v': 2,
        'license_id': license_key,
        'plan': lic.get('plan'),
        'issued_to': lic.get('user_email') or request.current_user.get('email') or '',
        'hardware_id': hardware_id,
        'expires_at': lic.get('expires_at'),
        'issued_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'nonce': secrets.token_hex(8),
    }

    bundle = _sign_license_v2(payload)
    if not bundle:
        return jsonify({'error': 'صدور فایل لایسنس در حال حاضر امکان‌پذیر نیست'}), 503

    # Track hardware binding
    if hardware_id:
        lic.setdefault('hardware_ids', [])
        if hardware_id not in lic['hardware_ids']:
            lic['hardware_ids'].append(hardware_id)
        save_json(LICENSES_FILE, licenses)

    # Return as downloadable file?
    if request.args.get('download') == '1':
        content = json.dumps(bundle, ensure_ascii=False, indent=2)
        return Response(
            content,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="license.oml"'
            }
        )

    return jsonify({'success': True, 'license_file': bundle})

# ============================================
# Admin Management API
# ============================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Get admin dashboard statistics."""
    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)
    
    total_revenue = 0
    for lic in licenses.values():
        plan = lic.get('plan', '')
        if plan == 'starter':
            total_revenue += 490000
        elif plan == 'professional':
            total_revenue += 990000
        elif plan == 'enterprise':
            total_revenue += 2490000
    
    active_licenses = len([l for l in licenses.values() if l.get('status') == 'active'])
    
    return jsonify({
        'users': len(users),
        'total_licenses': len(licenses),
        'active_licenses': active_licenses,
        'revoked_licenses': len([l for l in licenses.values() if l.get('status') == 'revoked']),
        'total_revenue': total_revenue,
        'hardware_ids': len(set(
            h for l in licenses.values() 
            for h in (l.get('hardware_ids') or [])
        ))
    })


@app.route('/api/admin/licenses', methods=['GET'])
@admin_required
def admin_list_licenses():
    """List all licenses with pagination."""
    licenses = load_json(LICENSES_FILE)
    users = load_json(USERS_FILE)
    
    # Build user lookup by id
    user_by_id = {u['id']: u for u in users.values()}
    
    result = []
    for key, lic in licenses.items():
        user = user_by_id.get(lic.get('user_id'))
        result.append({
            'key': key,
            'plan': lic.get('plan'),
            'plan_name': lic.get('plan_name') or lic.get('plan'),
            'status': lic.get('status'),
            'created_at': lic.get('created_at'),
            'expires_at': lic.get('expires_at'),
            'activations': lic.get('activations', 0),
            'max_activations': lic.get('max_activations', 1),
            'hardware_ids': lic.get('hardware_ids', []),
            'user_email': lic.get('user_email') or (user.get('email') if user else ''),
            'user_name': user.get('name') if user else '',
        })
    
    # Sort by created_at desc
    result.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    
    return jsonify({
        'licenses': result,
        'total': len(result)
    })


@app.route('/api/admin/licenses', methods=['POST'])
@admin_required
def admin_create_license():
    """Create a new license (admin)."""
    data = request.json or {}
    
    hardware_id = (data.get('hardware_id') or '').strip()
    customer_name = (data.get('customer_name') or '').strip()
    plan = (data.get('plan') or 'starter').strip()
    validity_days = int(data.get('validity_days') or 180)
    notes = (data.get('notes') or '').strip()
    
    licenses = load_json(LICENSES_FILE)
    key = generate_license_key()
    while key in licenses:
        key = generate_license_key()
    
    now = datetime.now()
    expires_at = (now + timedelta(days=validity_days)).isoformat()
    
    plan_names = {
        'trial': 'آزمایشی',
        'starter': 'استارتر',
        'professional': 'حرفه‌ای',
        'enterprise': 'سازمانی',
    }
    
    max_activations = {
        'trial': 1,
        'starter': 1,
        'professional': 3,
        'enterprise': 999,
    }.get(plan, 1)
    
    new_license = {
        'key': key,
        'user_id': '',
        'user_email': '',
        'plan': plan,
        'plan_name': plan_names.get(plan, plan),
        'status': 'active',
        'created_at': now.isoformat(),
        'expires_at': expires_at,
        'max_activations': max_activations,
        'activations': 0,
        'hardware_ids': [hardware_id] if hardware_id else [],
        'customer_name': customer_name,
        'notes': notes,
        'created_by_admin': request.current_user.get('email'),
    }
    
    licenses[key] = new_license
    save_json(LICENSES_FILE, licenses)
    
    # Generate signed license file if possible
    license_file = None
    if hardware_id and CRYPTO_AVAILABLE and LICENSE_PRIVATE_KEY_FILE.exists():
        payload = {
            'v': 2,
            'license_id': key,
            'plan': plan,
            'issued_to': customer_name or 'Admin Generated',
            'hardware_id': hardware_id,
            'expires_at': expires_at,
            'issued_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
            'nonce': secrets.token_hex(8),
        }
        license_file = _sign_license_v2(payload)
    
    return jsonify({
        'success': True,
        'license': new_license,
        'license_file': license_file,
    })


@app.route('/api/admin/licenses/<license_key>', methods=['PATCH'])
@admin_required
def admin_update_license(license_key):
    """Update a license (status, expiry, etc.)."""
    licenses = load_json(LICENSES_FILE)
    
    if license_key not in licenses:
        return jsonify({'error': 'لایسنس یافت نشد'}), 404
    
    data = request.json or {}
    lic = licenses[license_key]
    
    if 'status' in data:
        lic['status'] = data['status']
    if 'expires_at' in data:
        lic['expires_at'] = data['expires_at']
    if 'notes' in data:
        lic['notes'] = data['notes']
    if 'max_activations' in data:
        lic['max_activations'] = int(data['max_activations'])
    
    save_json(LICENSES_FILE, licenses)
    
    return jsonify({'success': True, 'license': lic})


@app.route('/api/admin/licenses/<license_key>', methods=['DELETE'])
@admin_required
def admin_revoke_license(license_key):
    """Revoke a license."""
    licenses = load_json(LICENSES_FILE)
    
    if license_key not in licenses:
        return jsonify({'error': 'لایسنس یافت نشد'}), 404
    
    licenses[license_key]['status'] = 'revoked'
    licenses[license_key]['revoked_at'] = datetime.now().isoformat()
    licenses[license_key]['revoked_by'] = request.current_user.get('email')
    
    save_json(LICENSES_FILE, licenses)
    
    return jsonify({'success': True, 'message': 'لایسنس لغو شد'})


@app.route('/api/admin/licenses/<license_key>/file', methods=['POST'])
@admin_required
def admin_generate_license_file(license_key):
    """Generate a signed license file for any license (admin)."""
    licenses = load_json(LICENSES_FILE)
    lic = licenses.get(license_key)
    
    if not lic:
        return jsonify({'error': 'لایسنس یافت نشد'}), 404
    
    data = request.json or {}
    hardware_id = (data.get('hardware_id') or '').strip()
    
    if not hardware_id:
        # Use first hardware_id if exists
        hwids = lic.get('hardware_ids') or []
        if hwids:
            hardware_id = hwids[0]
    
    payload = {
        'v': 2,
        'license_id': license_key,
        'plan': lic.get('plan'),
        'issued_to': lic.get('customer_name') or lic.get('user_email') or 'Admin Generated',
        'hardware_id': hardware_id,
        'expires_at': lic.get('expires_at'),
        'issued_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'nonce': secrets.token_hex(8),
    }
    
    bundle = _sign_license_v2(payload)
    if not bundle:
        return jsonify({'error': 'صدور فایل لایسنس امکان‌پذیر نیست'}), 503
    
    # Track hardware binding
    if hardware_id:
        lic.setdefault('hardware_ids', [])
        if hardware_id not in lic['hardware_ids']:
            lic['hardware_ids'].append(hardware_id)
        save_json(LICENSES_FILE, licenses)
    
    return jsonify({'success': True, 'license_file': bundle})


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    """List all users."""
    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)
    
    # Count licenses per user
    license_count = {}
    for lic in licenses.values():
        uid = lic.get('user_id')
        if uid:
            license_count[uid] = license_count.get(uid, 0) + 1
    
    result = []
    for email, user in users.items():
        result.append({
            'id': user.get('id'),
            'name': user.get('name'),
            'email': email,
            'phone': user.get('phone'),
            'is_admin': user.get('is_admin', False),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login'),
            'license_count': license_count.get(user.get('id'), 0),
            'downloads': user.get('downloads', 0),
        })
    
    result.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    
    return jsonify({
        'users': result,
        'total': len(result)
    })


@app.route('/api/admin/users/admin-status', methods=['PATCH'])
@admin_required
def admin_set_user_admin_status():
    """Promote/demote a user to/from admin.

    Body:
      - email: target user's email
      - is_admin: bool
    """
    data = request.json or {}
    email = (data.get('email') or '').strip()
    desired = data.get('is_admin')

    if not email:
        return jsonify({'error': 'ایمیل کاربر الزامی است'}), 400
    if not isinstance(desired, bool):
        return jsonify({'error': 'مقدار is_admin نامعتبر است'}), 400

    users = load_json(USERS_FILE)
    if email not in users:
        return jsonify({'error': 'کاربر یافت نشد'}), 404

    # Prevent removing the last admin
    if desired is False:
        admin_emails = [e for e, u in users.items() if u.get('is_admin')]
        if email in admin_emails and len(admin_emails) <= 1:
            return jsonify({'error': 'حداقل یک مدیر باید باقی بماند'}), 400

    users[email]['is_admin'] = desired
    save_json(USERS_FILE, users)

    return jsonify({'success': True, 'email': email, 'is_admin': desired})


# ============================================
# Run Server
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5001'))
    debug = os.environ.get('DEBUG', '0') == '1'

    print("\n" + "="*50)
    print("  🚀 OdooMaster API Server")
    print("="*50)
    print(f"\n  Running on: http://localhost:{port}")
    print(f"  API Docs: http://localhost:{port}/api")
    print("\n" + "="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
