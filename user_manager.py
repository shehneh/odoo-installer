import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent
USERS_FILE = BASE / '.users.json'
USER_AUTH_SECRET_FILE = BASE / '.user_auth_secret'


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MOBILE_RE = re.compile(r"^\+?\d{10,15}$")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _b64url_decode(text: str) -> bytes:
    pad = '=' * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + pad).encode('ascii'))


def _load_or_create_secret() -> bytes:
    try:
        if USER_AUTH_SECRET_FILE.exists():
            return USER_AUTH_SECRET_FILE.read_bytes()
        secret = os.urandom(32)
        USER_AUTH_SECRET_FILE.write_bytes(secret)
        return secret
    except Exception:
        # Fallback: process-level secret (tokens will invalidate on restart)
        return os.urandom(32)


_AUTH_SECRET = _load_or_create_secret()


def normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def normalize_mobile(mobile: str) -> str:
    m = (mobile or '').strip().replace(' ', '').replace('-', '')
    if m.startswith('00'):
        m = '+' + m[2:]
    return m


def is_valid_email(email: str) -> bool:
    email = normalize_email(email)
    return bool(email and _EMAIL_RE.match(email))


def is_valid_mobile(mobile: str) -> bool:
    mobile = normalize_mobile(mobile)
    return bool(mobile and _MOBILE_RE.match(mobile))


def hash_password(password: str, iterations: int = 200_000) -> str:
    if not password or len(password) < 6:
        raise ValueError('Password must be at least 6 characters')
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode('ascii')}${base64.b64encode(dk).decode('ascii')}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_b64, hash_b64 = stored.split('$', 3)
        if algo != 'pbkdf2_sha256':
            return False
        iterations = int(iters_s)
        salt = base64.b64decode(salt_b64.encode('ascii'))
        expected = base64.b64decode(hash_b64.encode('ascii'))
        got = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {'users': []}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get('users'), list):
            return data
    except Exception:
        pass
    return {'users': []}


def _save_users(data: dict) -> None:
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_user_by_identifier(identifier: str) -> Optional[dict]:
    identifier = (identifier or '').strip()
    if not identifier:
        return None

    email = normalize_email(identifier)
    mobile = normalize_mobile(identifier)

    data = _load_users()
    for u in data.get('users', []):
        if email and u.get('email') and normalize_email(u.get('email')) == email:
            return u
        if mobile and u.get('mobile') and normalize_mobile(u.get('mobile')) == mobile:
            return u
    return None


def get_user(user_id: str) -> Optional[dict]:
    data = _load_users()
    for u in data.get('users', []):
        if u.get('id') == user_id:
            return u
    return None


def find_user_by_google_sub(google_sub: str) -> Optional[dict]:
    google_sub = (google_sub or '').strip()
    if not google_sub:
        return None
    data = _load_users()
    for u in data.get('users', []):
        if str(u.get('google_sub', '')).strip() == google_sub:
            return u
    return None


def create_or_link_google_user(*, email: str, name: str, google_sub: str) -> dict:
    email_n = normalize_email(email)
    if email_n and not is_valid_email(email_n):
        raise ValueError('Invalid email')
    google_sub = (google_sub or '').strip()
    if not google_sub:
        raise ValueError('Missing google_sub')

    data = _load_users()

    # 1) If we already have this google_sub, return it
    for u in data.get('users', []):
        if str(u.get('google_sub', '')).strip() == google_sub:
            if name and not u.get('name'):
                u['name'] = name
                _save_users(data)
            return u

    # 2) If a local user exists with same email, link google_sub to it
    if email_n:
        for u in data.get('users', []):
            if u.get('email') and normalize_email(u.get('email')) == email_n:
                u['google_sub'] = google_sub
                if name and not u.get('name'):
                    u['name'] = name
                if not u.get('provider'):
                    u['provider'] = 'local'
                _save_users(data)
                return u

    # 3) Create a new google user
    user = {
        'id': f"USR-{uuid.uuid4().hex[:10].upper()}",
        'email': email_n or '',
        'mobile': '',
        'name': (name or '').strip(),
        'password_hash': '',
        'provider': 'google',
        'google_sub': google_sub,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active'
    }
    data['users'].insert(0, user)
    _save_users(data)
    return user


def create_user(*, email: str = '', mobile: str = '', password: str, name: str = '') -> dict:
    email_n = normalize_email(email)
    mobile_n = normalize_mobile(mobile)

    if not email_n and not mobile_n:
        raise ValueError('Email or mobile is required')
    if email_n and not is_valid_email(email_n):
        raise ValueError('Invalid email')
    if mobile_n and not is_valid_mobile(mobile_n):
        raise ValueError('Invalid mobile')

    data = _load_users()

    for u in data.get('users', []):
        if email_n and u.get('email') and normalize_email(u.get('email')) == email_n:
            raise ValueError('Email already registered')
        if mobile_n and u.get('mobile') and normalize_mobile(u.get('mobile')) == mobile_n:
            raise ValueError('Mobile already registered')

    user = {
        'id': f"USR-{uuid.uuid4().hex[:10].upper()}",
        'email': email_n or '',
        'mobile': mobile_n or '',
        'name': (name or '').strip(),
        'password_hash': hash_password(password),
        'provider': 'local',
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active'
    }

    data['users'].insert(0, user)
    _save_users(data)
    return user


def create_user_token(user_id: str, ttl_seconds: int = 7 * 24 * 3600) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    now = int(time.time())
    payload = {'sub': user_id, 'iat': now, 'exp': now + ttl_seconds}

    header_b = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f"{header_b}.{payload_b}".encode('ascii')
    sig = hmac.new(_AUTH_SECRET, signing_input, hashlib.sha256).digest()
    return f"{header_b}.{payload_b}.{_b64url_encode(sig)}"


@dataclass
class VerifiedUserToken:
    is_valid: bool
    user_id: str = ''
    error: str = ''


def verify_user_token(token: str) -> VerifiedUserToken:
    try:
        parts = (token or '').split('.')
        if len(parts) != 3:
            return VerifiedUserToken(False, error='invalid_token')

        header_b, payload_b, sig_b = parts
        signing_input = f"{header_b}.{payload_b}".encode('ascii')
        expected = hmac.new(_AUTH_SECRET, signing_input, hashlib.sha256).digest()
        got = _b64url_decode(sig_b)
        if not hmac.compare_digest(expected, got):
            return VerifiedUserToken(False, error='bad_signature')

        payload = json.loads(_b64url_decode(payload_b).decode('utf-8'))
        exp = int(payload.get('exp', 0))
        if exp and int(time.time()) > exp:
            return VerifiedUserToken(False, error='expired')

        user_id = str(payload.get('sub', '')).strip()
        if not user_id:
            return VerifiedUserToken(False, error='missing_sub')

        user = get_user(user_id)
        if not user or user.get('status') != 'active':
            return VerifiedUserToken(False, error='user_not_found')

        return VerifiedUserToken(True, user_id=user_id)
    except Exception:
        return VerifiedUserToken(False, error='invalid_token')


def public_user_view(user: dict) -> dict:
    return {
        'id': user.get('id', ''),
        'email': user.get('email', ''),
        'mobile': user.get('mobile', ''),
        'name': user.get('name', ''),
        'provider': user.get('provider', 'local'),
        'created_at': user.get('created_at', '')
    }
