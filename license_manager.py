#!/usr/bin/env python3
"""License management for the local Odoo installer UI.

Supports two formats:
1) v2: Signed license file (recommended)
    - Issued online after purchase
    - Verified offline using a public key (no shared secret inside the installer)
2) Legacy: HMAC-based Base64 key (kept only for backward compatibility)
"""

import base64
import hashlib
import hmac
import json
import os
import platform
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# Configuration
LICENSE_FILE = Path(__file__).parent / '.license'  # legacy encrypted cache
LICENSE_V2_FILE = Path(__file__).parent / '.license_v2.json'  # v2 cache
LICENSE_PUBLIC_KEY_FILE = Path(__file__).parent / 'license_public_key.pem'
AUTO_IMPORT_LICENSE_FILES = (
    'license.oml',
    'license.lic',
    'license.json',
    'license_v2.json',
)
BLACKLIST_FILE = Path(__file__).parent / '.license_blacklist.json'

# Legacy shared secret (NOT RECOMMENDED). Keep only for backward compatibility.
SECRET_KEY = b'OdooInstallerSecretKey2025'

# If a public key is configured, legacy keys are disabled by default.
ALLOW_LEGACY_HMAC_LICENSES = os.environ.get('ODOMASTER_ALLOW_LEGACY_LICENSE', '').strip() in ('1', 'true', 'True')


def _load_public_key_pem() -> Optional[bytes]:
    """Load PEM public key for verifying v2 license files.

    Priority:
    1) Env var ODOMASTER_LICENSE_PUBLIC_KEY_PEM (PEM text)
    2) File license_public_key.pem next to this script
    """
    env_pem = os.environ.get('ODOMASTER_LICENSE_PUBLIC_KEY_PEM')
    if env_pem and env_pem.strip():
        return env_pem.strip().encode('utf-8')
    try:
        if LICENSE_PUBLIC_KEY_FILE.exists():
            return LICENSE_PUBLIC_KEY_FILE.read_bytes()
    except Exception:
        pass
    return None


def _canonical_json_bytes(payload: dict) -> bytes:
    """Stable canonical JSON encoding for signature verification."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _verify_signature_rsa_pss_sha256(public_key_pem: bytes, message: bytes, signature_b64: str) -> Tuple[bool, str]:
    """Verify RSA-PSS(SHA256) signature using cryptography if installed."""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except Exception:
        return False, 'برای اعتبارسنجی این نوع لایسنس باید پکیج cryptography نصب باشد'

    try:
        sig = base64.b64decode(signature_b64.encode('utf-8'))
    except Exception:
        return False, 'امضای لایسنس نامعتبر است'

    try:
        pub = load_pem_public_key(public_key_pem)
        pub.verify(
            sig,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True, 'ok'
    except Exception:
        return False, 'امضای لایسنس نامعتبر است'


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _try_load_license_bundle_from_text(text: str) -> Optional[dict]:
    if not text:
        return None
    t = text.strip()
    if not t:
        return None
    if t.startswith('{') and t.endswith('}'):
        try:
            return json.loads(t)
        except Exception:
            return None
    return None


def _validate_v2_license_bundle(bundle: dict, hardware_id: str) -> Tuple[bool, str, Optional[dict]]:
    """Validate signed license bundle (v2)."""
    if not isinstance(bundle, dict):
        return False, 'فرمت لایسنس نامعتبر است', None

    if int(bundle.get('v') or 0) != 2:
        return False, 'نسخه لایسنس پشتیبانی نمی‌شود', None

    signature = bundle.get('sig')
    if not signature:
        return False, 'امضای لایسنس وجود ندارد', None

    public_key_pem = _load_public_key_pem()
    if not public_key_pem:
        return False, 'کلید عمومی برای اعتبارسنجی لایسنس تنظیم نشده است', None

    payload = dict(bundle)
    payload.pop('sig', None)
    message = _canonical_json_bytes(payload)
    ok, msg = _verify_signature_rsa_pss_sha256(public_key_pem, message, str(signature))
    if not ok:
        return False, msg, None

    # Optional hardware binding
    lic_hwid = (payload.get('hardware_id') or '').strip()
    if lic_hwid and lic_hwid != hardware_id:
        return False, 'این لایسنس برای این دستگاه معتبر نیست', None

    expires_at = _parse_iso_datetime(payload.get('expires_at') or '')
    if not expires_at:
        return False, 'تاریخ انقضای لایسنس نامعتبر است', None
    if datetime.now() > expires_at:
        return False, f"لایسنس منقضی شده است (تاریخ انقضا: {payload.get('expires_at')})", None

    # Revocation/blacklist support (by license_id if present)
    license_id = (payload.get('license_id') or payload.get('id') or '').strip()
    if license_id and is_blacklisted(license_id, hardware_id):
        return False, 'این لایسنس توسط مدیر سیستم لغو شده است', None

    days_left = (expires_at - datetime.now()).days
    return True, f'لایسنس معتبر است (باقیمانده: {days_left} روز)', payload


def load_blacklist() -> list:
    """Load the list of revoked license keys."""
    try:
        if BLACKLIST_FILE.exists():
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_blacklist(blacklist: list) -> bool:
    """Save the blacklist to file."""
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def add_to_blacklist(license_key: str, hardware_id: str = '', reason: str = '') -> bool:
    """Add a license key to the blacklist."""
    blacklist = load_blacklist()
    
    # Create a hash of the license key for comparison
    key_hash = hashlib.sha256(license_key.encode()).hexdigest()[:32] if license_key else ''
    
    # Check if already in blacklist
    for entry in blacklist:
        if entry.get('key_hash') == key_hash or entry.get('hardware_id') == hardware_id:
            return True  # Already blacklisted
    
    blacklist.append({
        'key_hash': key_hash,
        'hardware_id': hardware_id,
        'reason': reason,
        'revoked_at': datetime.now().isoformat()
    })
    
    return save_blacklist(blacklist)


def is_blacklisted(license_key: str = '', hardware_id: str = '') -> bool:
    """Check if a license key or hardware ID is blacklisted."""
    blacklist = load_blacklist()
    key_hash = hashlib.sha256(license_key.encode()).hexdigest()[:32] if license_key else ''
    
    for entry in blacklist:
        if key_hash and entry.get('key_hash') == key_hash:
            return True
        if hardware_id and entry.get('hardware_id') == hardware_id:
            return True
    
    return False


def get_hardware_id() -> str:
    """Generate a unique hardware ID based on machine characteristics."""
    try:
        # Try to get motherboard serial (most reliable on Windows)
        result = subprocess.run(
            ['wmic', 'baseboard', 'get', 'serialnumber'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                serial = lines[1].strip()
                if serial and serial != 'SerialNumber':
                    return hashlib.sha256(serial.encode()).hexdigest()[:16]
    except Exception:
        pass
    
    # Fallback to MAC address + Computer name
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                       for elements in range(0, 2*6, 2)][::-1])
        computer_name = platform.node()
        combined = f"{mac}-{computer_name}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    except Exception:
        # Last resort: just use a fixed string (not recommended)
        return hashlib.sha256(b'fallback-hardware-id').hexdigest()[:16]


def generate_license_key(hardware_id: str, expiry_days: int = 365) -> str:
    """Generate a license key for specific hardware ID.
    
    Format: BASE64(hardware_id:expiry_date:hmac_signature)
    """
    expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
    data = f"{hardware_id}:{expiry_date}"
    
    # Create HMAC signature
    signature = hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()[:16]
    
    # Combine and encode
    license_data = f"{data}:{signature}"
    license_key = base64.b64encode(license_data.encode()).decode()
    
    return license_key


def validate_license_key(license_key: str, hardware_id: str) -> Tuple[bool, str]:
    """Validate a license key against hardware ID.
    
    Returns: (is_valid, message)
    """
    try:
        # Decode license key
        decoded = base64.b64decode(license_key.encode()).decode()
        parts = decoded.split(':')
        
        # Format: hardware_id:expiry_date:signature
        # BUT expiry_date may contain ":" if it includes time (e.g. "2026-12-26 09:14")
        # So we expect 3 parts (date only) or 4 parts (date + HH:MM) or 5 parts (date + HH:MM:SS)
        if len(parts) < 3:
            return False, 'فرمت لایسنس نامعتبر است'
        
        lic_hardware_id = parts[0]
        signature = parts[-1]  # signature is always last
        expiry_date = ':'.join(parts[1:-1])  # everything between hardware_id and signature
        
        # Check hardware ID match
        if lic_hardware_id != hardware_id:
            return False, 'این لایسنس برای این دستگاه معتبر نیست'
        
        # Verify signature
        data = f"{lic_hardware_id}:{expiry_date}"
        expected_signature = hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()[:16]
        
        if signature != expected_signature:
            return False, 'لایسنس تقلبی است (امضا نامعتبر)'
        
        # Check expiry date - support formats: '%Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'
        expiry = None
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
            try:
                expiry = datetime.strptime(expiry_date, fmt)
                break
            except ValueError:
                continue
        
        if expiry is None:
            return False, f'فرمت تاریخ نامعتبر: {expiry_date}'
        
        if datetime.now() > expiry:
            return False, f'لایسنس منقضی شده است (تاریخ انقضا: {expiry_date})'
        
        days_left = (expiry - datetime.now()).days
        return True, f'لایسنس معتبر است (باقیمانده: {days_left} روز)'
        
    except Exception as e:
        return False, f'خطا در اعتبارسنجی: {str(e)}'


def save_license(license_key: str, hardware_id: str) -> bool:
    """Save validated license to encrypted file."""
    try:
        # Validate first
        is_valid, message = validate_license_key(license_key, hardware_id)
        if not is_valid:
            return False
        
        # Encrypt and save
        license_data = {
            'key': license_key,
            'hardware_id': hardware_id,
            'activated_at': datetime.now().isoformat(),
        }
        
        # Simple XOR encryption with hardware ID
        json_str = json.dumps(license_data)
        encrypted = bytes([
            ord(c) ^ ord(hardware_id[i % len(hardware_id)])
            for i, c in enumerate(json_str)
        ])
        
        LICENSE_FILE.write_bytes(base64.b64encode(encrypted))
        return True
        
    except Exception as e:
        print(f"Error saving license: {e}")
        return False


def load_license() -> Tuple[bool, Optional[str], str]:
    """Load and validate license from file.
    
    Returns: (is_valid, license_key, message)
    """
    try:
        # Prefer v2 cache
        if LICENSE_V2_FILE.exists():
            try:
                bundle = json.loads(LICENSE_V2_FILE.read_text(encoding='utf-8'))
                ok, msg, _payload = _validate_v2_license_bundle(bundle, get_hardware_id())
                if ok:
                    return True, 'v2', msg
                # If cache invalid, fall through and require re-activation.
            except Exception:
                pass

        # Auto-import a dropped license file (for user convenience)
        # First check explicit names
        for name in AUTO_IMPORT_LICENSE_FILES:
            p = Path(__file__).parent / name
            if not p.exists():
                continue
            try:
                maybe = _try_load_license_bundle_from_text(p.read_text(encoding='utf-8'))
                if maybe:
                    ok, msg, payload = _validate_v2_license_bundle(maybe, get_hardware_id())
                    if ok:
                        try:
                            LICENSE_V2_FILE.write_text(json.dumps(maybe, ensure_ascii=False, indent=2), encoding='utf-8')
                        except Exception:
                            pass
                        return True, 'v2', msg
            except Exception:
                continue
        
        # Also check for license_*.oml and *.oml patterns (dynamic filenames from download)
        parent_dir = Path(__file__).parent
        for pattern in ('license_*.oml', '*.oml', 'license_*.lic', '*.lic'):
            for p in parent_dir.glob(pattern):
                if not p.is_file():
                    continue
                try:
                    maybe = _try_load_license_bundle_from_text(p.read_text(encoding='utf-8'))
                    if maybe:
                        ok, msg, payload = _validate_v2_license_bundle(maybe, get_hardware_id())
                        if ok:
                            try:
                                LICENSE_V2_FILE.write_text(json.dumps(maybe, ensure_ascii=False, indent=2), encoding='utf-8')
                            except Exception:
                                pass
                            return True, 'v2', msg
                except Exception:
                    continue

        if not LICENSE_FILE.exists():
            return False, None, 'لایسنس یافت نشد - لطفاً فعال‌سازی کنید'
        
        # Read and decrypt
        encrypted = base64.b64decode(LICENSE_FILE.read_bytes())
        hardware_id = get_hardware_id()
        
        decrypted = ''.join([
            chr(b ^ ord(hardware_id[i % len(hardware_id)]))
            for i, b in enumerate(encrypted)
        ])
        
        license_data = json.loads(decrypted)
        license_key = license_data['key']
        stored_hw_id = license_data['hardware_id']
        
        # Verify hardware ID hasn't changed
        if stored_hw_id != hardware_id:
            return False, None, 'تغییر سخت‌افزار تشخیص داده شد - لایسنس نامعتبر است'
        
        # Validate license
        is_valid, message = validate_license_key(license_key, hardware_id)
        
        if is_valid:
            return True, license_key, message
        else:
            return False, None, message
            
    except Exception as e:
        return False, None, f'خطا در بارگذاری لایسنس: {str(e)}'


def check_license() -> Tuple[bool, str]:
    """Quick check if system is licensed.
    
    Returns: (is_licensed, message)
    """
    is_valid, license_key, message = load_license()
    
    # Check if license is blacklisted (revoked by admin)
    if is_valid and license_key:
        hardware_id = get_hardware_id()
        if is_blacklisted(license_key, hardware_id):
            return False, 'این لایسنس توسط مدیر سیستم لغو شده است'

        # Backward compatibility: if admin revoked the license before blacklist support
        # existed, it may only be marked in the local database.
        try:
            from database_manager import get_license_by_key  # type: ignore

            lic = get_license_by_key(license_key)
            if lic and lic.get('status') == 'revoked':
                return False, 'این لایسنس توسط مدیر سیستم لغو شده است'
        except Exception:
            pass
    
    return is_valid, message


def activate_license(license_key: str) -> Tuple[bool, str]:
    """Activate a new license key.
    
    Returns: (success, message)
    """
    hardware_id = get_hardware_id()

    # v2 JSON (license bundle pasted as text)
    bundle = _try_load_license_bundle_from_text(license_key)
    if bundle is not None:
        ok, message, _payload = _validate_v2_license_bundle(bundle, hardware_id)
        if not ok:
            return False, message
        try:
            LICENSE_V2_FILE.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            return False, 'خطا در ذخیره لایسنس'
        return True, message
    
    # Legacy licenses are disabled by default when a public key exists.
    if _load_public_key_pem() and not ALLOW_LEGACY_HMAC_LICENSES:
        return False, 'این نسخه از نرم‌افزار فقط فایل لایسنس امضاشده را می‌پذیرد'

    # First check if this license is blacklisted/revoked
    if is_blacklisted(license_key, hardware_id):
        return False, 'این لایسنس توسط مدیر سیستم لغو شده است'
    
    # Check database for revoked status
    try:
        from database_manager import get_license_by_key  # type: ignore
        lic = get_license_by_key(license_key)
        if lic and lic.get('status') == 'revoked':
            return False, 'این لایسنس توسط مدیر سیستم لغو شده است'
    except Exception:
        pass
    
    # Validate the license key cryptographically
    is_valid, message = validate_license_key(license_key, hardware_id)
    
    if is_valid:
        if save_license(license_key, hardware_id):
            return True, message
        else:
            return False, 'خطا در ذخیره لایسنس'
    else:
        return False, message


def deactivate_license() -> bool:
    """Remove license file (for transfer or reset)."""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
        if LICENSE_V2_FILE.exists():
            LICENSE_V2_FILE.unlink()
        return True
    except Exception:
        return False


def get_license_info() -> dict:
    """Get current license information."""
    is_valid, license_key, message = load_license()
    hardware_id = get_hardware_id()
    
    info = {
        'is_valid': is_valid,
        'message': message,
        'hardware_id': hardware_id,
        'license_key_partial': None,
        'format': None,
        'plan': None,
        'issued_to': None,
        'is_lifetime': False,
        'expiry_date': None,
        'days_remaining': None,
    }

    # v2 signed license
    if LICENSE_V2_FILE.exists():
        try:
            bundle = json.loads(LICENSE_V2_FILE.read_text(encoding='utf-8'))
            ok, _msg, payload = _validate_v2_license_bundle(bundle, hardware_id)
            if ok and payload:
                info['format'] = 'v2'
                info['plan'] = payload.get('plan')
                info['issued_to'] = payload.get('issued_to')
                info['license_key_partial'] = (payload.get('license_id') or '')[:20] + '...'

                exp = _parse_iso_datetime(payload.get('expires_at') or '')
                if exp:
                    info['expiry_date'] = payload.get('expires_at')
                    diff = exp - datetime.now()
                    info['days_remaining'] = diff.days
                    if diff.days > 3650:
                        info['is_lifetime'] = True
                return info
        except Exception:
            pass
    
    # legacy
    if is_valid and license_key and license_key not in ('v2',):
        info['format'] = 'legacy'
        info['license_key_partial'] = license_key[:20] + '...' if license_key else None
        try:
            decoded = base64.b64decode(license_key.encode()).decode()
            parts = decoded.split(':')
            
            # Get expiry date (could be second part)
            if len(parts) >= 2:
                # Signature is always last, so rebuild expiry from middle parts
                expiry_date = ':'.join(parts[1:-1]) if len(parts) > 3 else parts[1]
                info['expiry_date'] = expiry_date
                
                # Check for lifetime
                if 'lifetime' in expiry_date.lower() or 'unlimited' in expiry_date.lower():
                    info['is_lifetime'] = True
                    info['days_remaining'] = -1
                else:
                    # Try to parse with various formats
                    expiry = None
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                        try:
                            expiry = datetime.strptime(expiry_date, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if expiry:
                        diff = expiry - datetime.now()
                        info['days_remaining'] = diff.days
                        # If more than 10 years, consider it lifetime
                        if diff.days > 3650:
                            info['is_lifetime'] = True
        except Exception:
            pass
    
    return info


# For generating keys (run this script directly)
if __name__ == '__main__':
    print("=" * 60)
    print("🔐 Odoo Installer - License Key Generator")
    print("=" * 60)
    
    hw_id = get_hardware_id()
    print(f"\n📌 Hardware ID این دستگاه:")
    print(f"   {hw_id}")
    
    print("\n" + "=" * 60)
    print("کلید لایسنس برای این دستگاه:")
    print("=" * 60)
    
    # Generate keys with different validity periods
    for days in [30, 90, 365, 365*10]:
        key = generate_license_key(hw_id, days)
        years = days // 365
        if years >= 1:
            validity = f"{years} سال"
        else:
            validity = f"{days} روز"
        
        print(f"\n⏰ اعتبار {validity}:")
        print(f"   {key}")
    
    print("\n" + "=" * 60)
    print("\n💡 نکات:")
    print("   • این کلیدها فقط برای این دستگاه معتبرند")
    print("   • کلید دلخواه را کپی کرده و در نرم‌افزار وارد کنید")
    print("   • برای دستگاه دیگر باید کلید جدید تولید کنید")
    print("\n" + "=" * 60)
