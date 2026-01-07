# -*- coding: utf-8 -*-
"""
OdooMaster Multi-Tenant SaaS Platform
Flask server with auto-provisioning API for creating Odoo instances
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, Response, session, redirect, url_for, send_file
from flask_cors import CORS
import psycopg2
import string
import random
import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import xmlrpc.client
import socket
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

# Allow OAuth over HTTP for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Set global socket timeout for XMLRPC operations
def set_socket_timeout(timeout):
    """Set socket timeout for XMLRPC operations"""
    socket.setdefaulttimeout(timeout)

app = Flask(__name__, 
            static_folder=None,  # Disable automatic static serving
            template_folder='website')
CORS(app)

# Secret key for session management - MUST be fixed, not random!
# Random key causes session loss on every server restart
app.secret_key = os.environ.get('SECRET_KEY', 'OdooMaster-Fixed-Secret-Key-2025-Do-Not-Change!')

# Session configuration - make sessions persistent
app.config['SESSION_COOKIE_SECURE'] = False  # Set True only for HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # 7 days session

# =====================================
# Page Access Control
# =====================================

# Public pages - accessible without login
PUBLIC_PAGES = [
    '/', 'index.html', 
    'docs.html', 
    'downloads.html',
    'install.html',  # Online installer page
    'user-login.html', 'user-register.html',
    'verify-account.html', 'email-verified.html',
    'app-details.html',  # App information pages
    'apps.html',  # App listing
    'favicon.svg', 'css/', 'js/', 'images/', 'api/'
]

# Protected pages - require login AND verification
PROTECTED_PAGES = [
    'profile.html',
    'module_wizard.html',
    'auto_login.html',
    'dashboard.html',
    'dashboard-unified.html',
    'onboarding.html'  # Require login for onboarding
]

# Legacy/deprecated pages - redirect to new pages
LEGACY_REDIRECTS = {
    'login.html': '/user-login.html',
    'register.html': '/user-register.html',
    'dashboard.html': '/dashboard-unified.html',
    'profile.html': '/dashboard-unified.html',
    'admin_panel.html': '/dashboard-unified.html'
}

# Middleware to check authentication before serving protected pages
@app.before_request
def check_authentication():
    """Check if user is authenticated before serving protected pages"""
    from flask import request as flask_request
    
    # Get requested path
    path = flask_request.path.lstrip('/')
    
    # Skip static assets completely
    if path.startswith(('css/', 'js/', 'images/', 'fonts/', 'assets/')):
        return None
    
    # Skip API endpoints
    if path.startswith('api/'):
        return None
    
    # Skip favicon
    if 'favicon' in path:
        return None
    
    # Handle legacy redirects (exact match only)
    if path in LEGACY_REDIRECTS:
        return redirect(LEGACY_REDIRECTS[path])
    
    # Check if it's explicitly a public page (exact match)
    if path == '' or path in ['', 'index.html', 'docs.html', 'downloads.html', 
                               'install.html',
                               'user-login.html', 'user-register.html', 
                               'verify-account.html', 'email-verified.html']:
        return None  # Allow access
    
    # Check if it's a protected page (exact match)
    is_protected = path in PROTECTED_PAGES
    
    if is_protected:
        # Check if user is logged in
        if 'user_id' not in session:
            # Redirect to login with return_to parameter
            return redirect(f'/user-login.html?return_to={flask_request.path}')
        
        # Check if user is verified based on auth method
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT auth_method, email_verified, phone_verified, status 
            FROM website_users WHERE id = ?
        ''', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            session.clear()
            return redirect('/user-login.html')
        
        auth_method, email_verified, phone_verified, status = user
        
        # Check verification based on auth method
        if auth_method == 'phone':
            if not phone_verified:
                return redirect('/verify-account.html')
        else:  # email
            if not email_verified:
                return redirect('/verify-account.html')
        
        # Check status
        if status not in ['active', 'pending']:
            session.clear()
            return redirect('/user-login.html?error=inactive')

# Email configuration (Gmail SMTP)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-app-password')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'OdooMaster <noreply@odoomaster.ir>')

# Admin Users - These emails have full admin access
ADMIN_EMAILS = [
    'shehneh.m@gmail.com',
    'shehneh@gmail.com',
    'admin@odoomaster.ir',
    'support@odoomaster.ir'
]

# SMS configuration (Kavenegar)
KAVENEGAR_API_KEY = os.environ.get('KAVENEGAR_API_KEY', '')
KAVENEGAR_TEMPLATE = os.environ.get('KAVENEGAR_TEMPLATE', 'verify')  # نام template در کاوه‌نگار
KAVENEGAR_SENDER = os.environ.get('KAVENEGAR_SENDER', '2000660110')  # شماره فرستنده

# Google OAuth Configuration (MUST be set via environment variables)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
# Auto-detect redirect URI from request or use environment variable
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5001/callback/google')

# Configuration - همیشه از متغیر محیطی استفاده کن (امن‌تر)
ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo-online.liara.run')
ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'OdooMaster2025!')
DB_HOST = os.environ.get('DB_HOST', 'odoo-db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'lu46zbfKF1s8j04thKOUI24b')

# Local SQLite database for customer management
# Use /app/data for persistent storage on Liara (disk mounted here)
DATA_DIR = os.environ.get('DATA_DIR', '/app/data')
CUSTOMERS_DB = os.path.join(DATA_DIR, 'customers.db')

def init_customers_db():
    """Initialize SQLite database for customer management"""
    global DATA_DIR, CUSTOMERS_DB
    
    # Ensure directory exists
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError:
        # If /app/data fails, fall back to current directory
        print(f"⚠️  Could not create {DATA_DIR}, using current directory")
        DATA_DIR = '.'
        CUSTOMERS_DB = 'customers.db'
    
    conn = sqlite3.connect(CUSTOMERS_DB)
    cursor = conn.cursor()
    
    # Customers table (existing tenants)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            admin_email TEXT UNIQUE NOT NULL,
            admin_name TEXT NOT NULL,
            phone TEXT,
            database_name TEXT UNIQUE NOT NULL,
            admin_password TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            plan TEXT DEFAULT 'starter',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            installed_modules TEXT,
            demo_users TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES website_users (id)
        )
    ''')
    
    # Add user_id column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE customers ADD COLUMN user_id INTEGER')
        conn.commit()
        print("✓ Added user_id column to customers table")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Demo users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS demo_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            login TEXT NOT NULL,
            password TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    
    # Website users table (برای احراز هویت سایت)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS website_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            password_hash TEXT NOT NULL,
            auth_method TEXT DEFAULT 'email',
            profile_picture TEXT,
            email_verified INTEGER DEFAULT 0,
            email_verification_token TEXT,
            email_verification_expires TIMESTAMP,
            phone_verified INTEGER DEFAULT 0,
            phone_verification_code TEXT,
            phone_verification_expires TIMESTAMP,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Try to add auth_method column if it doesn't exist (for existing DBs)
    try:
        cursor.execute('ALTER TABLE website_users ADD COLUMN auth_method TEXT DEFAULT "email"')
    except:
        pass
    
    # Try to add profile_picture column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE website_users ADD COLUMN profile_picture TEXT')
    except:
        pass  # Column already exists
    
    # Plans table for dynamic plan management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT UNIQUE NOT NULL,
            name_fa TEXT NOT NULL,
            name_en TEXT NOT NULL,
            price INTEGER NOT NULL,
            duration_months INTEGER NOT NULL,
            duration_display_fa TEXT,
            duration_display_en TEXT,
            discount_percent INTEGER DEFAULT 0,
            features TEXT,
            is_popular INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default plans if table is empty
    cursor.execute('SELECT COUNT(*) FROM plans')
    if cursor.fetchone()[0] == 0:
        default_plans = [
            ('monthly', 'ماهانه', 'Monthly', 500000, 1, 'یک ماه', 'One Month', 0, 
             'دسترسی کامل به اودو|پشتیبانی 24 ساعته|آپدیت خودکار|1GB فضای ذخیره‌سازی', 0, 1, 1),
            ('quarterly', 'سه‌ماهه', 'Quarterly', 1350000, 3, 'سه ماه', 'Three Months', 10,
             'دسترسی کامل به اودو|پشتیبانی 24 ساعته|آپدیت خودکار|3GB فضای ذخیره‌سازی|10% تخفیف', 1, 1, 2),
            ('yearly', 'سالانه', 'Yearly', 4800000, 12, 'یک سال', 'One Year', 20,
             'دسترسی کامل به اودو|پشتیبانی اختصاصی|آپدیت خودکار|10GB فضای ذخیره‌سازی|20% تخفیف|پشتیبان‌گیری روزانه', 0, 1, 3)
        ]
        cursor.executemany('''
            INSERT INTO plans (plan_id, name_fa, name_en, price, duration_months, 
                             duration_display_fa, duration_display_en, discount_percent, 
                             features, is_popular, is_active, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_plans)
    
    # Tickets table for support system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES website_users(id)
        )
    ''')
    
    # Ticket messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            is_admin INTEGER DEFAULT 0,
            message TEXT NOT NULL,
            attachments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id),
            FOREIGN KEY (user_id) REFERENCES website_users(id)
        )
    ''')
    
    # User licenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            license_key TEXT UNIQUE NOT NULL,
            plan_id TEXT NOT NULL,
            plan_name TEXT,
            hardware_id TEXT,
            status TEXT DEFAULT 'active',
            price INTEGER,
            duration_months INTEGER,
            activated_at TIMESTAMP,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES website_users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_db_name(company_name, email=None, phone=None):
    """Generate unique database name from email or phone (readable format)"""
    import re
    
    base_name = None
    
    # Priority: email > phone > company_name
    if email:
        # Extract username from email (before @)
        # example@gmail.com -> example
        username = email.split('@')[0]
        # Clean: only keep alphanumeric
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', username)[:25]
        if clean_name:
            base_name = f"odoo_{clean_name.lower()}"
    
    if not base_name and phone:
        # Use phone number (remove leading 0)
        # 09123456789 -> 9123456789
        clean_phone = re.sub(r'[^0-9]', '', phone)
        if clean_phone.startswith('0'):
            clean_phone = clean_phone[1:]
        if clean_phone:
            base_name = f"odoo_m{clean_phone}"
    
    if not base_name:
        # Fallback: company name
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name)[:20]
        if not clean_name:
            clean_name = 'tenant'
        base_name = f"odoo_{clean_name.lower()}"
    
    # Check if database already exists in customers table
    conn = sqlite3.connect(CUSTOMERS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM customers WHERE database_name = ?', (base_name,))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count > 0:
        # Add random suffix if name exists
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{base_name}_{suffix}"
    
    return base_name

def generate_password(length=12):
    """Generate secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

# =====================================
# Authentication Helper Functions
# =====================================

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def generate_verification_token():
    """Generate secure verification token"""
    return secrets.token_urlsafe(32)

def generate_sms_code():
    """Generate 6-digit SMS verification code"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, token):
    """Send email verification link"""
    try:
        verification_url = f"http://localhost:5001/verify-email?token={token}"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'تایید ایمیل - OdooMaster'
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        
        html = f"""
        <html dir="rtl">
            <body style="font-family: Tahoma, Arial;">
                <h2>تایید ایمیل شما</h2>
                <p>برای تایید ایمیل خود، روی لینک زیر کلیک کنید:</p>
                <a href="{verification_url}" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    تایید ایمیل
                </a>
                <p>یا این لینک را در مرورگر خود کپی کنید:</p>
                <p style="background: #f7fafc; padding: 10px; direction: ltr;">{verification_url}</p>
                <p>این لینک تا 24 ساعت معتبر است.</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True, "ایمیل تایید ارسال شد"
    except Exception as e:
        return False, f"خطا در ارسال ایمیل: {str(e)}"

def send_sms_verification(phone, code):
    """Send SMS verification code using Kavenegar"""
    try:
        if not KAVENEGAR_API_KEY:
            return False, "API Key کاوه‌نگار تنظیم نشده است"
        
        # Use simple SMS send API (no template required)
        url = f"https://api.kavenegar.com/v1/{KAVENEGAR_API_KEY}/sms/send.json"
        message = f"کد تایید OdooMaster: {code}"
        
        params = {
            'receptor': phone,
            'message': message,
            'sender': KAVENEGAR_SENDER
        }
        
        response = requests.post(url, data=params)
        result = response.json()
        
        if result.get('return', {}).get('status') == 200:
            return True, "کد تایید ارسال شد"
        else:
            error_msg = result.get('return', {}).get('message', 'Unknown error')
            return False, f"خطا در ارسال پیامک: {error_msg}"
    except Exception as e:
        return False, f"خطا در ارسال پیامک: {str(e)}"

def login_required(f):
    """Decorator to protect routes - requires user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        
        # Check if user is verified
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email_verified, phone_verified, status FROM website_users WHERE id = ?', 
                      (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or user[2] != 'active':
            session.clear()
            return redirect(url_for('login_page'))
        
        if not user[0] or not user[1]:
            return redirect(url_for('verify_account_page'))
        
        return f(*args, **kwargs)
    return decorated_function

def create_odoo_database(db_name, admin_email, admin_password, company_name, lang='fa_IR', country='IR'):
    """Create new Odoo database using XML-RPC (more reliable than web form)"""
    import xmlrpc.client
    import time
    
    try:
        # Connect to Odoo database service via XML-RPC
        db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db', allow_none=True)
        
        # Create database using XML-RPC
        result = db.create_database(
            ODOO_MASTER_PASSWORD,  # master password
            db_name,               # database name
            False,                 # demo data
            lang,                  # language
            admin_password,        # admin password
            admin_email,           # admin login
            country.lower(),       # country code (lowercase)
            ''                     # phone
        )
        
        if not result:
            return False, "Odoo returned False for database creation"
        
        # Wait for database to be fully created
        time.sleep(5)
        
        # Verify database exists in the list
        db_list = db.list()
        if db_name in db_list:
            return True, f"Database {db_name} created and verified successfully"
        else:
            return False, f"Database '{db_name}' not found after creation"
            
    except xmlrpc.client.Fault as e:
        if 'AccessDenied' in str(e.faultString):
            return False, "Master password incorrect. Check ODOO_MASTER_PASSWORD."
        return False, f"XML-RPC Error: {e.faultString}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_customer_exists(admin_email):
    """Check if customer with this email already exists"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT database_name, created_at FROM customers WHERE admin_email = ?', (admin_email,))
        result = cursor.fetchone()
        conn.close()
        return result  # Returns (database_name, created_at) or None
    except Exception as e:
        print(f"Error checking customer: {e}")
        return None

def save_customer(company_name, admin_email, admin_name, phone, database_name, admin_password, user_id=None):
    """Save customer information to local database"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customers (company_name, admin_email, admin_name, phone, database_name, admin_password, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (company_name, admin_email, admin_name, phone, database_name, admin_password, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving customer: {e}")
        return False

# Routes
@app.route('/')
def index():
    return send_from_directory('website', 'index.html')

@app.route('/install')
def install():
    # Redirect to onboarding page instead
    return redirect('/onboarding.html')

@app.route('/installer')
def installer():
    # Redirect to onboarding page instead
    return redirect('/onboarding.html')

# Removed old serve_static route - now handled at the end of file with middleware

# =====================================
# API Endpoints for Module Installation
# =====================================

import xmlrpc.client


def get_odoo_modules_status(db_name, admin_email, admin_password, modules):
    """Return module availability/state for given database."""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(60)  # 60 seconds for status check
        common_url = f"{ODOO_URL}/xmlrpc/2/common"
        object_url = f"{ODOO_URL}/xmlrpc/2/object"

        common = xmlrpc.client.ServerProxy(common_url, allow_none=True)
        uid = common.authenticate(db_name, admin_email, admin_password, {})
        if not uid:
            return False, "Authentication failed", None

        models = xmlrpc.client.ServerProxy(object_url, allow_none=True)

        # Best-effort refresh
        try:
            models.execute_kw(db_name, uid, admin_password, 'ir.module.module', 'update_list', [])
        except Exception as e:
            print(f"⚠ Could not update module list (status check): {e}")

        statuses = {}
        installed = []
        not_found = []
        available = []

        for module_name in modules:
            try:
                module_ids = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'search',
                    [[('name', '=', module_name)]],
                )

                if not module_ids:
                    statuses[module_name] = 'not_found'
                    not_found.append(module_name)
                    continue

                module_data = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'read',
                    [module_ids], {'fields': ['state']},
                )
                state = (module_data[0] or {}).get('state')
                if state == 'installed':
                    statuses[module_name] = 'installed'
                    installed.append(module_name)
                else:
                    statuses[module_name] = 'available'
                    available.append(module_name)
            except Exception as e:
                print(f"⚠ Status check failed for {module_name}: {e}")
                statuses[module_name] = 'unknown'

        return True, "OK", {
            'statuses': statuses,
            'installed': installed,
            'not_found': not_found,
            'available': available,
        }
    except Exception as e:
        return False, str(e), None
    finally:
        socket.setdefaulttimeout(old_timeout)

def install_odoo_modules_stream(db_name, admin_email, admin_password, modules=None):
    """Install Odoo modules with streaming progress (generator)"""
    if modules is None:
        modules = ['l10n_ir', 'web_responsive', 'base_setup']
    
    import json
    import time
    
    try:
        yield json.dumps({'event': 'status', 'module': None, 'status': 'connecting', 'message': 'در حال اتصال به Odoo...'})
        
        # Set socket timeout for long operations (5 minutes)
        socket.setdefaulttimeout(300)
        
        common_url = f"{ODOO_URL}/xmlrpc/2/common"
        object_url = f"{ODOO_URL}/xmlrpc/2/object"
        
        common = xmlrpc.client.ServerProxy(common_url, allow_none=True)
        
        yield json.dumps({'event': 'status', 'module': None, 'status': 'authenticating', 'message': 'در حال احراز هویت...'})
        
        uid = common.authenticate(db_name, admin_email, admin_password, {})
        if not uid:
            yield json.dumps({'event': 'error', 'message': 'Authentication failed'})
            return
        
        models = xmlrpc.client.ServerProxy(object_url, allow_none=True)
        
        # Update module list
        yield json.dumps({'event': 'status', 'module': None, 'status': 'updating', 'message': 'به‌روزرسانی لیست ماژول‌ها...'})
        try:
            models.execute_kw(db_name, uid, admin_password, 'ir.module.module', 'update_list', [])
            time.sleep(1)
        except Exception as e:
            print(f"⚠ Could not update module list: {e}")
        
        newly_installed = []
        already_installed = []
        skipped = []
        failed = []
        
        total = len(modules)
        for idx, module_name in enumerate(modules, 1):
            try:
                yield json.dumps({'event': 'progress', 'module': module_name, 'status': 'searching', 'current': idx, 'total': total})
                
                module_ids = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'search',
                    [[('name', '=', module_name)]]
                )
                
                if not module_ids:
                    skipped.append(module_name)
                    yield json.dumps({'event': 'module_status', 'module': module_name, 'status': 'skipped', 'message': 'ماژول موجود نیست'})
                    continue
                
                # Get module state
                module_data = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'read',
                    [module_ids], {'fields': ['state']}
                )
                
                if module_data[0]['state'] == 'installed':
                    already_installed.append(module_name)
                    yield json.dumps({'event': 'module_status', 'module': module_name, 'status': 'already-installed', 'message': 'از قبل نصب بود'})
                    continue
                
                # Install module
                yield json.dumps({'event': 'progress', 'module': module_name, 'status': 'installing', 'current': idx, 'total': total})
                
                models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'button_immediate_install',
                    [module_ids]
                )
                
                newly_installed.append(module_name)
                yield json.dumps({'event': 'module_status', 'module': module_name, 'status': 'installed', 'message': 'نصب شد'})
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error installing '{module_name}': {e}")
                failed.append(module_name)
                yield json.dumps({'event': 'module_status', 'module': module_name, 'status': 'failed', 'message': str(e)[:100]})
        
        # Final report
        details_parts = []
        if newly_installed:
            details_parts.append(f"✓ Newly Installed: {', '.join(newly_installed)}")
        if already_installed:
            details_parts.append(f"↺ Already Installed: {', '.join(already_installed)}")
        if skipped:
            details_parts.append(f"⊘ Skipped (not found): {', '.join(skipped)}")
        if failed:
            details_parts.append(f"✗ Failed: {', '.join(failed)}")

        details = " | ".join(details_parts) if details_parts else "No changes"

        report = {
            'requested': list(modules) if modules else [],
            'installed': newly_installed,
            'already_installed': already_installed,
            'skipped': skipped,
            'failed': failed,
        }

        success = bool(newly_installed or already_installed)
        yield json.dumps({'event': 'complete', 'success': success, 'report': report, 'details': details})
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        yield json.dumps({'event': 'error', 'message': str(e)})


@app.route('/api/modules-status', methods=['POST', 'OPTIONS'])
def api_modules_status():
    """Check which modules are installed/available in a given database."""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json() or {}
        db_name = data.get('db_name')
        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')
        modules = data.get('modules') or []

        if not all([db_name, admin_email, admin_password]):
            return jsonify({'success': False, 'error': 'Database name, email and password are required'}), 400
        if not isinstance(modules, list) or not modules:
            return jsonify({'success': False, 'error': 'Modules list is required'}), 400

        ok, msg, payload = get_odoo_modules_status(db_name, admin_email, admin_password, modules)
        if not ok:
            return jsonify({'success': False, 'error': msg}), 500

        return jsonify({'success': True, **payload})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def install_odoo_modules(db_name, admin_email, admin_password, modules=None):
    """Install Odoo modules using XML-RPC"""
    if modules is None:
        modules = ['l10n_ir', 'web_responsive', 'base_setup']
    
    try:
        print(f"🔌 Connecting to Odoo XML-RPC: {ODOO_URL}")
        
        common_url = f"{ODOO_URL}/xmlrpc/2/common"
        object_url = f"{ODOO_URL}/xmlrpc/2/object"
        
        common = xmlrpc.client.ServerProxy(common_url, allow_none=True)
        
        print(f"🔐 Authenticating with db={db_name}, user={admin_email}")
        uid = common.authenticate(db_name, admin_email, admin_password, {})
        if not uid:
            return False, "Authentication failed"
        
        print(f"✓ Authenticated as user ID: {uid}")
        
        models = xmlrpc.client.ServerProxy(object_url, allow_none=True)
        
        # Update module list
        print(f"📦 Updating module list...")
        try:
            models.execute_kw(db_name, uid, admin_password, 'ir.module.module', 'update_list', [[]])
            import time
            time.sleep(2)
        except Exception as e:
            print(f"⚠ Could not update module list: {e}")
        
        newly_installed = []
        already_installed = []
        skipped = []
        failed = []
        
        for module_name in modules:
            try:
                print(f"🔍 Searching for module: {module_name}")
                
                module_ids = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'search',
                    [[('name', '=', module_name)]]
                )
                
                if not module_ids:
                    # Some modules might not exist in the current Odoo build/edition.
                    # Treat as skipped (not a hard failure).
                    print(f"⏭ Module '{module_name}' not found (skipped)")
                    skipped.append(module_name)
                    continue
                
                # Get module state
                module_data = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'read',
                    [module_ids], {'fields': ['state']}
                )
                
                if module_data[0]['state'] == 'installed':
                    print(f"✓ Module '{module_name}' already installed (skipping)")
                    already_installed.append(module_name)
                    continue
                
                # Install module
                print(f"⚙️ Installing module '{module_name}'...")
                models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'button_immediate_install',
                    [module_ids]
                )
                
                print(f"✅ Module '{module_name}' installed!")
                newly_installed.append(module_name)
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error installing '{module_name}': {e}")
                failed.append(module_name)
        
        # Combine all installed for backward compatibility
        all_installed = newly_installed + already_installed
        
        details_parts = []
        if newly_installed:
            details_parts.append(f"✓ Newly Installed: {', '.join(newly_installed)}")
        if already_installed:
            details_parts.append(f"↺ Already Installed: {', '.join(already_installed)}")
        if skipped:
            details_parts.append(f"⊘ Skipped (not found): {', '.join(skipped)}")
        if failed:
            details_parts.append(f"✗ Failed: {', '.join(failed)}")

        details = " | ".join(details_parts) if details_parts else "No changes"

        report = {
            'requested': list(modules) if modules else [],
            'installed': newly_installed,
            'already_installed': already_installed,
            'skipped': skipped,
            'failed': failed,
        }

        # Success rules:
        # - If we installed new modules or skipped already-installed -> success
        # - If everything was skipped because not found -> not successful (user selected modules but none applicable)
        # - If failures happened but some installed -> still success with warnings
        if newly_installed or already_installed:
            return True, details, report
        if skipped and not failed:
            return False, f"No selected modules were found in this Odoo build. {details}", report
        return False, details, report
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e), {
            'requested': list(modules) if modules else [],
            'installed': [],
            'already_installed': [],
            'skipped': [],
            'failed': [],
        }


@app.route('/api/test', methods=['GET'])
def api_test():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'API is working!',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/install-modules-stream', methods=['POST', 'OPTIONS'])
def api_install_modules_stream():
    """Install Odoo modules with streaming progress (SSE)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        db_name = data.get('db_name')
        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')
        modules = data.get('modules', ['l10n_ir', 'web_responsive', 'base_setup'])
        
        if not all([db_name, admin_email, admin_password]):
            return jsonify({
                'success': False,
                'error': 'Database name, email and password are required'
            }), 400
        
        def generate():
            for event in install_odoo_modules_stream(db_name, admin_email, admin_password, modules):
                yield f"data: {event}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500


@app.route('/api/install-modules', methods=['POST', 'OPTIONS'])
def api_install_modules():
    """Install Odoo modules for a specific database"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        db_name = data.get('db_name')
        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')
        modules = data.get('modules', ['l10n_ir', 'web_responsive', 'base_setup'])
        
        if not all([db_name, admin_email, admin_password]):
            return jsonify({
                'success': False,
                'error': 'Database name, email and password are required'
            }), 400
        
        print(f"📦 Installing modules for: {db_name}")
        
        success, details, report = install_odoo_modules(
            db_name=db_name,
            admin_email=admin_email,
            admin_password=admin_password,
            modules=modules
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'ماژول‌ها با موفقیت نصب شدند',
                'details': details,
                'report': report
            })
        else:
            return jsonify({
                'success': False,
                'error': details,
                'report': report
            }), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500


# =====================================
# Main API Endpoints
# =====================================

@app.route('/api/create-tenant', methods=['POST'])
def create_tenant():
    """API endpoint to create new tenant (customer Odoo instance)"""
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'لطفاً ابتدا وارد شوید'}), 401
        
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'داده‌ای دریافت نشد', 'debug': 'request.json is None'}), 400
        
        company_name = data.get('company_name')
        admin_email = data.get('admin_email')
        admin_name = data.get('admin_name', 'Admin')
        phone = data.get('phone', '')
        
        if not company_name or not admin_email:
            return jsonify({'success': False, 'message': 'نام شرکت و ایمیل الزامی است'}), 400
        
        # چک تکراری نبودن
        existing = check_customer_exists(admin_email)
        if existing:
            db_name, created_at = existing
            return jsonify({
                'success': False, 
                'message': f'این ایمیل قبلاً ثبت شده است',
                'existing': True,
                'data': {
                    'database_name': db_name,
                    'login_url': f"{ODOO_URL}/web/login?db={db_name}",
                    'created_at': str(created_at)
                }
            }), 409  # 409 Conflict
        
        # Generate readable database name from email or phone
        db_name = generate_db_name(company_name, email=admin_email, phone=phone)
        admin_password = generate_password()
        
        success, message = create_odoo_database(db_name, admin_email, admin_password, company_name)
        
        if not success:
            return jsonify({'success': False, 'message': f'خطا در ساخت دیتابیس: {message}'}), 500
        
        # Save customer with user_id
        save_customer(company_name, admin_email, admin_name, phone, db_name, admin_password, user_id)
        
        return jsonify({
            'success': True,
            'message': 'سرور Odoo شما با موفقیت ساخته شد',
            'data': {
                'company_name': company_name,
                'database_name': db_name,
                'admin_email': admin_email,
                'admin_password': admin_password,
                'url': f"{ODOO_URL}/web?db={db_name}",
                'login_url': f"{ODOO_URL}/web/login?db={db_name}"
            }
        }), 201
    except Exception as e:
        import traceback
        return jsonify({
            'success': False, 
            'message': f'خطا: {str(e)}',
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/list-customers', methods=['GET'])
def list_customers():
    """List customers - filtered by user_id for regular users, all for admins"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        
        # Get user info to check if admin
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_email = user_result['email']
        is_admin = user_email.lower() in [e.lower() for e in ADMIN_EMAILS]
        
        # Query customers based on user role
        if is_admin:
            # Admin sees all databases
            cursor.execute('SELECT * FROM customers ORDER BY created_at DESC')
        else:
            # Regular user sees only their own databases
            cursor.execute('SELECT * FROM customers WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        
        customers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True, 
            'count': len(customers), 
            'customers': customers,
            'is_admin': is_admin
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/migrate-customers', methods=['POST'])
def migrate_customers():
    """Link existing customers to users based on admin_email matching"""
    try:
        # Only admins can run this
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'لطفاً ابتدا وارد شوید'}), 401
        
        # Check if admin
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user_result = cursor.fetchone()
        conn.close()
        
        if not user_result:
            return jsonify({'success': False, 'message': 'کاربر یافت نشد'}), 404
        
        user_email = user_result[0]
        if user_email.lower() not in [e.lower() for e in ADMIN_EMAILS]:
            return jsonify({'success': False, 'message': 'فقط ادمین‌ها می‌توانند این عملیات را انجام دهند'}), 403
        
        # Get all customers without user_id
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, admin_email FROM customers WHERE user_id IS NULL')
        customers_without_user = cursor.fetchall()
        
        updated_count = 0
        for customer_id, admin_email in customers_without_user:
            # Find matching user by email
            conn_users = sqlite3.connect(USERS_DB)
            cursor_users = conn_users.cursor()
            cursor_users.execute('SELECT id FROM website_users WHERE email = ?', (admin_email,))
            user_match = cursor_users.fetchone()
            conn_users.close()
            
            if user_match:
                # Update customer with user_id
                cursor.execute('UPDATE customers SET user_id = ? WHERE id = ?', (user_match[0], customer_id))
                updated_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{updated_count} دیتابیس به کاربران متصل شد',
            'updated_count': updated_count,
            'total_without_user': len(customers_without_user)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/verify-database', methods=['POST'])
def verify_database():
    """Verify if database actually exists in Odoo"""
    try:
        data = request.get_json()
        database = data.get('database')
        
        if not database:
            return jsonify({'success': False, 'error': 'نام دیتابیس الزامی است'}), 400
        
        # Check if database exists in Odoo
        set_socket_timeout(10)
        db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db', allow_none=True)
        db_list = db.list()
        
        exists = database in db_list
        
        return jsonify({'success': True, 'exists': exists, 'database': database})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete-customer-record', methods=['POST'])
def delete_customer_record():
    """Delete customer record from SQLite (for recreating database)"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not email and not phone:
            return jsonify({'success': False, 'error': 'ایمیل یا شماره تلفن الزامی است'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        if email:
            cursor.execute('DELETE FROM customers WHERE admin_email = ?', (email,))
        elif phone:
            cursor.execute('DELETE FROM customers WHERE phone = ?', (phone,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'{deleted_count} رکورد حذف شد',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/delete-databases', methods=['POST'])
def admin_delete_databases():
    """Delete multiple databases from Odoo (admin only with master password)"""
    try:
        print("=" * 60)
        print("🗑️  DELETE DATABASES REQUEST RECEIVED")
        print("=" * 60)
        
        # Check if user is admin
        if 'user_id' not in session:
            print("❌ No user_id in session - user not logged in")
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        print(f"✓ User ID: {user_id}")
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print(f"❌ User {user_id} not found in database")
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_email = result[0]
        print(f"✓ User email: {user_email}")
        
        is_admin = user_email.lower() in [e.lower() for e in ADMIN_EMAILS]
        print(f"✓ Is admin: {is_admin}")
        
        if not is_admin:
            print(f"❌ User {user_email} is not an admin")
            return jsonify({'success': False, 'error': 'فقط ادمین‌ها اجازه حذف دیتابیس دارند'}), 403
        
        data = request.get_json()
        databases = data.get('databases', [])
        master_password = data.get('master_password', '')
        
        print(f"✓ Databases to delete: {databases}")
        print(f"✓ Password provided: {'Yes' if master_password else 'No'}")
        
        if not databases:
            print("❌ No databases specified")
            return jsonify({'success': False, 'error': 'لیست دیتابیس‌ها خالی است'}), 400
        
        if not master_password:
            print("❌ No master password provided")
            return jsonify({'success': False, 'error': 'رمز حذف الزامی است'}), 400
        
        # Verify master password
        CORRECT_MASTER_PASSWORD = 'OdooMaster2025!'
        if master_password != CORRECT_MASTER_PASSWORD:
            print(f"❌ Wrong password: {master_password}")
            return jsonify({'success': False, 'error': '❌ رمز حذف اشتباه است! دسترسی رد شد.'}), 403
        
        print("✓ Master password verified!")
        print(f"🗑️  Starting deletion of {len(databases)} database(s)...")
        
        # Delete databases from Odoo
        set_socket_timeout(30)
        db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db', allow_none=True)
        
        deleted_count = 0
        failed_databases = []
        
        for database in databases:
            try:
                print(f"   Deleting: {database}...")
                db.drop(master_password, database)
                deleted_count += 1
                print(f"   ✓ Deleted from Odoo: {database}")
                
                # Also delete from SQLite
                conn = sqlite3.connect(CUSTOMERS_DB)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM customers WHERE database_name = ?', (database,))
                conn.commit()
                conn.close()
                print(f"   ✓ Deleted from SQLite: {database}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ Failed to delete {database}: {error_msg}")
                failed_databases.append(f"{database}: {error_msg}")
        
        message = f'✅ {deleted_count} دیتابیس حذف شد'
        if failed_databases:
            message += f'\n\n❌ {len(failed_databases)} دیتابیس حذف نشد:\n' + '\n'.join(failed_databases)
        
        print("=" * 60)
        print(f"✅ DELETION COMPLETE")
        print(f"   Deleted: {deleted_count}")
        print(f"   Failed: {len(failed_databases)}")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'failed_count': len(failed_databases),
            'message': message
        })
        
    except Exception as e:
        import traceback
        print("=" * 60)
        print("❌ EXCEPTION IN DELETE API:")
        traceback.print_exc()
        print("=" * 60)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/create-demo-data', methods=['POST', 'OPTIONS'])
def api_create_demo_data():
    """Create demo data (users, products, customers, suppliers) in an Odoo database"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        db_name = data.get('db_name')
        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')
        users = data.get('users', [])
        products = data.get('products', [])
        customers = data.get('customers', [])
        suppliers = data.get('suppliers', [])
        
        if not all([db_name, admin_email, admin_password]):
            return jsonify({
                'success': False,
                'error': 'Database name, email and password are required'
            }), 400
        
        # Set timeout for XMLRPC
        set_socket_timeout(120)
        
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(db_name, admin_email, admin_password, {})
        
        if not uid:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        results = {
            'users_created': [],
            'products_created': [],
            'customers_created': [],
            'suppliers_created': []
        }
        
        # Create Users
        for user_data in users:
            try:
                # Get groups - ALWAYS include base.group_user for Internal User access
                group_ids = []
                
                # Add base internal user group first (essential for Odoo 19)
                try:
                    base_user_group = models.execute_kw(
                        db_name, uid, admin_password,
                        'ir.model.data', 'check_object_reference',
                        ['base', 'group_user']
                    )
                    if base_user_group:
                        group_ids.append(base_user_group[1])
                except:
                    pass
                
                # Add additional groups
                for group_ref in user_data.get('groups', []):
                    try:
                        module, xml_id = group_ref.split('.')
                        group_id = models.execute_kw(
                            db_name, uid, admin_password,
                            'ir.model.data', 'check_object_reference',
                            [module, xml_id]
                        )
                        if group_id:
                            group_ids.append(group_id[1])
                    except:
                        pass
                
                # Create user with groups
                user_id = models.execute_kw(
                    db_name, uid, admin_password,
                    'res.users', 'create',
                    [{
                        'name': user_data['name'],
                        'login': user_data['login'],
                        'password': user_data['password'],
                        'groups_id': [(6, 0, group_ids)]
                    }]
                )
                results['users_created'].append({
                    'name': user_data['name'],
                    'login': user_data['login'],
                    'id': user_id
                })
            except Exception as e:
                print(f"Error creating user {user_data.get('login')}: {e}")
        
        # Create Products
        for product_data in products:
            try:
                product_id = models.execute_kw(
                    db_name, uid, admin_password,
                    'product.product', 'create',
                    [{
                        'name': product_data['name'],
                        'list_price': product_data.get('price', 0),
                        'standard_price': product_data.get('price', 0) * 0.7,  # 30% margin
                        'type': 'product',
                        'default_code': f"SKU-{product_data['name'][:3].upper()}"
                    }]
                )
                
                # Update stock quantity if stock module installed
                try:
                    # Find stock location
                    location_ids = models.execute_kw(
                        db_name, uid, admin_password,
                        'stock.location', 'search',
                        [[['usage', '=', 'internal']]],
                        {'limit': 1}
                    )
                    
                    if location_ids and product_data.get('qty', 0) > 0:
                        models.execute_kw(
                            db_name, uid, admin_password,
                            'stock.quant', 'create',
                            [{
                                'product_id': product_id,
                                'location_id': location_ids[0],
                                'quantity': product_data.get('qty', 0)
                            }]
                        )
                except:
                    pass  # Stock module might not be installed
                
                results['products_created'].append({
                    'name': product_data['name'],
                    'id': product_id
                })
            except Exception as e:
                print(f"Error creating product {product_data.get('name')}: {e}")
        
        # Create Customers
        for customer_data in customers:
            try:
                customer_vals = {
                    'name': customer_data['name'],
                    'phone': customer_data.get('phone', ''),
                    'email': customer_data.get('email', ''),
                    'is_company': customer_data.get('is_company', False),
                }
                
                # Try to add customer_rank, skip if field doesn't exist
                try:
                    customer_vals['customer_rank'] = 1
                    customer_id = models.execute_kw(
                        db_name, uid, admin_password,
                        'res.partner', 'create',
                        [customer_vals]
                    )
                except xmlrpc.client.Fault as e:
                    if 'customer_rank' in str(e):
                        # Field doesn't exist, retry without it
                        del customer_vals['customer_rank']
                        customer_id = models.execute_kw(
                            db_name, uid, admin_password,
                            'res.partner', 'create',
                            [customer_vals]
                        )
                    else:
                        raise
                results['customers_created'].append({
                    'name': customer_data['name'],
                    'id': customer_id
                })
            except Exception as e:
                print(f"Error creating customer {customer_data.get('name')}: {e}")
        
        # Create Suppliers
        for supplier_data in suppliers:
            try:
                supplier_vals = {
                    'name': supplier_data['name'],
                    'phone': supplier_data.get('phone', ''),
                    'email': supplier_data.get('email', ''),
                    'is_company': supplier_data.get('is_company', True),
                }
                
                # Try to add supplier_rank, skip if field doesn't exist
                try:
                    supplier_vals['supplier_rank'] = 1
                    supplier_id = models.execute_kw(
                        db_name, uid, admin_password,
                        'res.partner', 'create',
                        [supplier_vals]
                    )
                except xmlrpc.client.Fault as e:
                    if 'supplier_rank' in str(e):
                        # Field doesn't exist, retry without it
                        del supplier_vals['supplier_rank']
                        supplier_id = models.execute_kw(
                            db_name, uid, admin_password,
                            'res.partner', 'create',
                            [supplier_vals]
                        )
                    else:
                        raise
                results['suppliers_created'].append({
                    'name': supplier_data['name'],
                    'id': supplier_id
                })
            except Exception as e:
                print(f"Error creating supplier {supplier_data.get('name')}: {e}")
        
        # Save demo users to database
        try:
            conn = sqlite3.connect(CUSTOMERS_DB)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM customers WHERE admin_email = ?', (admin_email,))
            customer = cursor.fetchone()
            
            if customer:
                customer_id = customer[0]
                # Delete old demo users
                cursor.execute('DELETE FROM demo_users WHERE customer_id = ?', (customer_id,))
                
                # Insert new demo users
                for user_data in users:
                    cursor.execute('''
                        INSERT INTO demo_users (customer_id, role, name, login, password)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (customer_id, user_data.get('role', ''), user_data['name'], 
                          user_data['login'], user_data['password']))
                
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving demo users: {e}")
        
        return jsonify({
            'success': True,
            'message': 'داده‌های نمونه با موفقیت ایجاد شدند',
            'results': results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500


@app.route('/api/profile/<email>', methods=['GET'])
def get_profile(email):
    """Get customer profile with demo users"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get customer info
        cursor.execute('SELECT * FROM customers WHERE admin_email = ?', (email,))
        customer = cursor.fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'success': False, 'error': 'Customer not found'}), 404
        
        customer_dict = dict(customer)
        
        # Get demo users
        cursor.execute('SELECT * FROM demo_users WHERE customer_id = ?', (customer['id'],))
        demo_users = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'customer': customer_dict,
            'demo_users': demo_users
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'ok', 
        'message': 'OdooMaster API is running',
        'version': '3.2.0',
        'deploy_test': 'SUCCESS - Liara Deploy Working!',
        'app_file': 'app.py',
        'odoo_url': ODOO_URL,
        'master_password_set': bool(ODOO_MASTER_PASSWORD),
        'master_password_preview': ODOO_MASTER_PASSWORD[:4] + '...' if ODOO_MASTER_PASSWORD else 'NOT SET',
        'timestamp': datetime.now().isoformat(),
        'routes': {
            'create_tenant': '/api/create-tenant [POST]',
            'list_customers': '/api/list-customers [GET]',
            'health': '/api/health [GET]'
        }
    })


# =====================================
# Authentication API Endpoints
# =====================================

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register new website user"""
    try:
        data = request.get_json()
        
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip().lower() if data.get('email') else None
        phone = data.get('phone', '').strip() if data.get('phone') else None
        password = data.get('password', '')
        auth_method = data.get('auth_method', 'email')  # 'email' or 'phone'
        
        if not full_name or not password:
            return jsonify({'success': False, 'error': 'نام و رمز عبور الزامی است'}), 400
        
        # Validate based on auth method
        import re
        if auth_method == 'email':
            if not email:
                return jsonify({'success': False, 'error': 'ایمیل الزامی است'}), 400
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return jsonify({'success': False, 'error': 'فرمت ایمیل نامعتبر است'}), 400
        else:  # phone
            if not phone:
                return jsonify({'success': False, 'error': 'شماره موبایل الزامی است'}), 400
            if not re.match(r'^09\d{9}$', phone):
                return jsonify({'success': False, 'error': 'شماره تلفن باید 11 رقم و با 09 شروع شود'}), 400
        
        # Check if user already exists
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        if auth_method == 'email' and email:
            cursor.execute('SELECT id FROM website_users WHERE email = ?', (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': 'این ایمیل قبلاً ثبت شده است'}), 409
        
        if auth_method == 'phone' and phone:
            cursor.execute('SELECT id FROM website_users WHERE phone = ?', (phone,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': 'این شماره موبایل قبلاً ثبت شده است'}), 409
        
        # Hash password
        password_hash = hash_password(password)
        
        if auth_method == 'email':
            # Generate email verification token
            verification_token = generate_verification_token()
            token_expires = datetime.now() + timedelta(hours=24)
            
            # Insert user with email auth
            cursor.execute('''
                INSERT INTO website_users 
                (full_name, email, phone, password_hash, auth_method, email_verification_token, email_verification_expires)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (full_name, email, phone, password_hash, 'email', verification_token, token_expires))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            # Send verification email
            success, message = send_verification_email(email, verification_token)
            
            return jsonify({
                'success': True,
                'message': 'ثبت‌نام موفق! لطفاً ایمیل خود را تایید کنید.',
                'user_id': user_id,
                'email_sent': success
            }), 201
        else:
            # Phone auth - no need to send verification now, will be done after login
            cursor.execute('''
                INSERT INTO website_users 
                (full_name, email, phone, password_hash, auth_method)
                VALUES (?, ?, ?, ?, ?)
            ''', (full_name, email, phone, password_hash, 'phone'))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'ثبت‌نام موفق! لطفاً شماره موبایل خود را تایید کنید.',
                'user_id': user_id
            }), 201
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def api_login():
    """Login website user"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower() if data.get('email') else None
        phone = data.get('phone', '').strip() if data.get('phone') else None
        password = data.get('password', '')
        auth_method = data.get('auth_method', 'email')  # 'email' or 'phone'
        
        if auth_method == 'email':
            if not email or not password:
                return jsonify({'success': False, 'error': 'ایمیل و رمز عبور الزامی است'}), 400
        else:
            if not phone or not password:
                return jsonify({'success': False, 'error': 'شماره موبایل و رمز عبور الزامی است'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        if auth_method == 'email':
            cursor.execute('''
                SELECT id, full_name, email, phone, password_hash, auth_method, email_verified, phone_verified, status 
                FROM website_users WHERE email = ?
            ''', (email,))
        else:
            cursor.execute('''
                SELECT id, full_name, email, phone, password_hash, auth_method, email_verified, phone_verified, status 
                FROM website_users WHERE phone = ?
            ''', (phone,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            if auth_method == 'email':
                return jsonify({'success': False, 'error': 'ایمیل یا رمز عبور اشتباه است'}), 401
            else:
                return jsonify({'success': False, 'error': 'شماره موبایل یا رمز عبور اشتباه است'}), 401
        
        user_id, full_name, user_email, user_phone, password_hash, user_auth_method, email_verified, phone_verified, status = user
        
        # Verify password
        if not verify_password(password, password_hash):
            conn.close()
            if auth_method == 'email':
                return jsonify({'success': False, 'error': 'ایمیل یا رمز عبور اشتباه است'}), 401
            else:
                return jsonify({'success': False, 'error': 'شماره موبایل یا رمز عبور اشتباه است'}), 401
        
        # Check status
        if status != 'active' and status != 'pending':
            conn.close()
            return jsonify({'success': False, 'error': 'حساب کاربری شما غیرفعال شده است'}), 403
        
        # Check if verification is needed based on CURRENT login method (not stored auth_method)
        # اگه کاربر الان با موبایل لاگین کرد، باید phone_verified رو چک کنیم
        # اگه کاربر الان با ایمیل لاگین کرد، باید email_verified رو چک کنیم
        if auth_method == 'phone':
            needs_verification = not phone_verified
        else:
            needs_verification = not email_verified
        
        # If phone login needs verification, send SMS code now
        if needs_verification and auth_method == 'phone' and user_phone:
            # Generate phone verification code
            phone_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            phone_code_expires = datetime.now() + timedelta(minutes=10)
            
            # Save code to database
            cursor.execute('''
                UPDATE website_users 
                SET phone_verification_code = ?, phone_verification_expires = ?, auth_method = ?
                WHERE id = ?
            ''', (phone_code, phone_code_expires, 'phone', user_id))
            conn.commit()
            
            # Send SMS
            sms_success, sms_message = send_sms_verification(user_phone, phone_code)
            print(f"[LOGIN] SMS verification code sent to {user_phone}: {sms_success}, {sms_message}")
        
        # Update last login
        cursor.execute('UPDATE website_users SET last_login = ? WHERE id = ?', 
                      (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        # Set session - use CURRENT auth_method (what user chose to login with)
        session.permanent = True  # Keep session for 7 days
        session['user_id'] = user_id
        session['user_email'] = user_email
        session['user_phone'] = user_phone
        session['user_name'] = full_name
        session['auth_method'] = auth_method  # روش فعلی لاگین
        
        return jsonify({
            'success': True,
            'message': 'ورود موفق',
            'user': {
                'id': user_id,
                'name': full_name,
                'email': user_email,
                'phone': user_phone,
                'auth_method': auth_method,  # روش فعلی لاگین
                'email_verified': bool(email_verified),
                'phone_verified': bool(phone_verified)
            },
            'needs_verification': needs_verification
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Logout website user"""
    session.clear()
    return jsonify({'success': True, 'message': 'خروج موفق'})


# =====================================
# Password Change API
# =====================================

@app.route('/api/change-password', methods=['POST'])
def api_change_password():
    """Change user password (site or Odoo)"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        data = request.get_json()
        password_type = data.get('type', 'site')  # 'site' or 'odoo'
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'error': 'رمز عبور فعلی و جدید الزامی است'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'رمز عبور جدید باید حداقل 6 کاراکتر باشد'}), 400
        
        user_id = session['user_id']
        user_email = session.get('user_email', '')
        
        if password_type == 'site':
            # Change website password
            conn = sqlite3.connect(CUSTOMERS_DB)
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash FROM website_users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
            
            # Check if user logged in with Google (no password set)
            if not result[0]:
                # No password set - allow setting new password
                new_hash = hash_password(new_password)
                cursor.execute('UPDATE website_users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
                conn.commit()
                conn.close()
                return jsonify({'success': True, 'message': 'رمز عبور با موفقیت تنظیم شد'})
            
            # Verify current password
            if not verify_password(current_password, result[0]):
                conn.close()
                return jsonify({'success': False, 'error': 'رمز عبور فعلی اشتباه است'}), 401
            
            # Update password
            new_hash = hash_password(new_password)
            cursor.execute('UPDATE website_users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'رمز عبور سایت با موفقیت تغییر کرد'})
            
        elif password_type == 'odoo':
            # Change Odoo password
            conn = sqlite3.connect(CUSTOMERS_DB)
            cursor = conn.cursor()
            cursor.execute('SELECT database_name, admin_password FROM customers WHERE admin_email = ?', (user_email.lower(),))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return jsonify({'success': False, 'error': 'دیتابیس Odoo یافت نشد'}), 404
            
            db_name, stored_password = result
            
            # Verify current Odoo password
            if current_password != stored_password:
                conn.close()
                return jsonify({'success': False, 'error': 'رمز عبور Odoo فعلی اشتباه است'}), 401
            
            # Try to change password in Odoo via XML-RPC
            try:
                common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', allow_none=True)
                uid = common.authenticate(db_name, user_email, current_password, {})
                
                if uid:
                    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', allow_none=True)
                    models.execute_kw(db_name, uid, current_password, 'res.users', 'write', [[uid], {'password': new_password}])
            except Exception as odoo_error:
                print(f"[WARN] Could not change Odoo password via XML-RPC: {odoo_error}")
                # Continue anyway to update local database
            
            # Update password in local database
            cursor.execute('UPDATE customers SET admin_password = ? WHERE admin_email = ?', (new_password, user_email.lower()))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'رمز عبور Odoo با موفقیت تغییر کرد'})
        
        else:
            return jsonify({'success': False, 'error': 'نوع رمز عبور نامعتبر است'}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/update-profile', methods=['POST'])
def api_update_profile():
    """Update user profile information"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        data = request.get_json()
        user_id = session['user_id']
        
        # Fields that can be updated
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if full_name:
            updates.append('full_name = ?')
            params.append(full_name)
            session['user_name'] = full_name
        
        if phone:
            updates.append('phone = ?')
            params.append(phone)
        
        if updates:
            params.append(user_id)
            cursor.execute(f'UPDATE website_users SET {", ".join(updates)} WHERE id = ?', params)
            conn.commit()
        
        conn.close()
        
        return jsonify({'success': True, 'message': 'پروفایل با موفقیت به‌روزرسانی شد'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================
# Unified OTP Login/Register (Like Numberland)
# =====================================

@app.route('/api/send-otp-unified', methods=['POST'])
def api_send_otp_unified():
    """ارسال کد OTP برای لاگین/ثبت‌نام یکپارچه - اگر کاربر وجود نداشت ثبت‌نام می‌شود"""
    try:
        data = request.json or {}
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'error': 'شماره موبایل الزامی است'}), 400
        
        # Normalize phone
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('98'):
            phone = '0' + phone[2:]
        
        # Validate phone format
        if not phone.startswith('09') or len(phone) != 11:
            return jsonify({'success': False, 'error': 'فرمت شماره موبایل صحیح نیست'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id, full_name, phone FROM website_users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        
        is_new_user = False
        
        if user:
            user_id = user[0]
        else:
            # Create new user with just phone number
            is_new_user = True
            cursor.execute('''
                INSERT INTO website_users (phone, status, created_at, auth_method)
                VALUES (?, 'pending', ?, 'phone')
            ''', (phone, datetime.now()))
            user_id = cursor.lastrowid
            conn.commit()
            print(f"[UNIFIED-OTP] New user created with phone: {phone}, id: {user_id}")
        
        # Generate 5-digit OTP code
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        otp_expires = datetime.now() + timedelta(minutes=5)
        
        # Save OTP to database
        cursor.execute('''
            UPDATE website_users 
            SET phone_verification_code = ?, phone_verification_expires = ?
            WHERE id = ?
        ''', (otp_code, otp_expires, user_id))
        conn.commit()
        conn.close()
        
        # Send SMS
        sms_success, sms_message = send_sms_verification(phone, otp_code)
        
        if sms_success:
            print(f"[UNIFIED-OTP] Code sent to {phone}: {otp_code}")
            return jsonify({
                'success': True,
                'message': 'کد تایید ارسال شد',
                'phone': phone,
                'is_new_user': is_new_user,
                'expires_in': 300
            })
        else:
            print(f"[UNIFIED-OTP] Failed to send SMS: {sms_message}")
            return jsonify({'success': False, 'error': sms_message}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/verify-otp-unified', methods=['POST'])
def api_verify_otp_unified():
    """تایید کد OTP و لاگین/ثبت‌نام یکپارچه"""
    try:
        data = request.json or {}
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        
        if not phone or not code:
            return jsonify({'success': False, 'error': 'شماره موبایل و کد الزامی است'}), 400
        
        # Normalize phone
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('98'):
            phone = '0' + phone[2:]
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, full_name, email, phone, phone_verification_code, 
                   phone_verification_expires, status
            FROM website_users WHERE phone = ?
        ''', (phone,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_id, full_name, user_email, user_phone, stored_code, code_expires, status = user
        
        # Verify OTP code
        if not stored_code:
            conn.close()
            return jsonify({'success': False, 'error': 'ابتدا درخواست کد تایید کنید'}), 400
        
        if stored_code != code:
            conn.close()
            return jsonify({'success': False, 'error': 'کد تایید اشتباه است'}), 401
        
        # Check expiration
        if code_expires:
            if isinstance(code_expires, str):
                code_expires = datetime.fromisoformat(code_expires)
            if datetime.now() > code_expires:
                conn.close()
                return jsonify({'success': False, 'error': 'کد تایید منقضی شده است'}), 401
        
        # OTP verified - activate user and clear the code
        cursor.execute('''
            UPDATE website_users 
            SET phone_verified = 1, 
                status = 'active',
                phone_verification_code = NULL, 
                phone_verification_expires = NULL,
                last_login = ?,
                auth_method = 'phone'
            WHERE id = ?
        ''', (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        # Set session
        session.permanent = True
        session['user_id'] = user_id
        session['user_email'] = user_email
        session['user_phone'] = user_phone
        session['user_name'] = full_name or f'کاربر {phone[-4:]}'
        session['auth_method'] = 'phone'
        
        print(f"[UNIFIED-OTP] User {user_id} logged in with phone: {phone}")
        
        return jsonify({
            'success': True,
            'message': 'ورود موفق',
            'user': {
                'id': user_id,
                'name': full_name or f'کاربر {phone[-4:]}',
                'email': user_email,
                'phone': user_phone
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/check-email', methods=['POST'])
def api_check_email():
    """بررسی وجود کاربر با ایمیل"""
    try:
        data = request.json or {}
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'error': 'ایمیل الزامی است'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, full_name FROM website_users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({
                'success': True,
                'exists': True,
                'message': 'کاربر یافت شد'
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'message': 'کاربر یافت نشد - می‌توانید ثبت‌نام کنید'
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================
# OTP Login Endpoints (Passwordless Phone Login)
# =====================================

@app.route('/api/send-login-otp', methods=['POST'])
def api_send_login_otp():
    """ارسال کد OTP برای لاگین با موبایل (بدون رمز عبور)"""
    try:
        data = request.json or {}
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'error': 'شماره موبایل الزامی است'}), 400
        
        # Normalize phone
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('98'):
            phone = '0' + phone[2:]
        
        # Check if user exists with this phone
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, full_name, phone FROM website_users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'این شماره موبایل ثبت نشده است'}), 404
        
        user_id, full_name, user_phone = user
        
        # Generate 6-digit OTP code
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        otp_expires = datetime.now() + timedelta(minutes=5)
        
        # Save OTP to database
        cursor.execute('''
            UPDATE website_users 
            SET phone_verification_code = ?, phone_verification_expires = ?
            WHERE id = ?
        ''', (otp_code, otp_expires, user_id))
        conn.commit()
        conn.close()
        
        # Send SMS
        sms_success, sms_message = send_sms_verification(phone, otp_code)
        
        if sms_success:
            print(f"[LOGIN-OTP] Code sent to {phone}: {otp_code}")
            return jsonify({
                'success': True,
                'message': 'کد ورود ارسال شد',
                'phone': phone,
                'expires_in': 300  # 5 minutes in seconds
            })
        else:
            print(f"[LOGIN-OTP] Failed to send SMS: {sms_message}")
            return jsonify({'success': False, 'error': sms_message}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/login-with-otp', methods=['POST'])
def api_login_with_otp():
    """لاگین با کد OTP (بدون رمز عبور)"""
    try:
        data = request.json or {}
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        
        if not phone or not code:
            return jsonify({'success': False, 'error': 'شماره موبایل و کد الزامی است'}), 400
        
        # Normalize phone
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('98'):
            phone = '0' + phone[2:]
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, full_name, email, phone, phone_verification_code, 
                   phone_verification_expires, status
            FROM website_users WHERE phone = ?
        ''', (phone,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_id, full_name, user_email, user_phone, stored_code, code_expires, status = user
        
        # Check status
        if status not in ('active', 'pending'):
            conn.close()
            return jsonify({'success': False, 'error': 'حساب کاربری غیرفعال است'}), 403
        
        # Verify OTP code
        if not stored_code:
            conn.close()
            return jsonify({'success': False, 'error': 'ابتدا درخواست کد ورود کنید'}), 400
        
        if stored_code != code:
            conn.close()
            return jsonify({'success': False, 'error': 'کد ورود اشتباه است'}), 401
        
        # Check expiration
        if code_expires:
            if isinstance(code_expires, str):
                code_expires = datetime.fromisoformat(code_expires)
            if datetime.now() > code_expires:
                conn.close()
                return jsonify({'success': False, 'error': 'کد ورود منقضی شده است'}), 401
        
        # OTP verified - mark phone as verified and clear the code
        cursor.execute('''
            UPDATE website_users 
            SET phone_verified = 1, 
                phone_verification_code = NULL, 
                phone_verification_expires = NULL,
                last_login = ?,
                auth_method = 'phone'
            WHERE id = ?
        ''', (datetime.now(), user_id))
        conn.commit()
        conn.close()
        
        # Set session
        session.permanent = True  # Keep session for 7 days
        session['user_id'] = user_id
        session['user_email'] = user_email
        session['user_phone'] = user_phone
        session['user_name'] = full_name
        session['auth_method'] = 'phone'
        
        print(f"[LOGIN-OTP] User {user_id} logged in with phone OTP")
        
        return jsonify({
            'success': True,
            'message': 'ورود موفق',
            'user': {
                'id': user_id,
                'name': full_name,
                'email': user_email,
                'phone': user_phone
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================
# Google OAuth Endpoints
# =====================================

@app.route('/auth/google')
def google_login():
    """Redirect to Google OAuth login"""
    try:
        from requests_oauthlib import OAuth2Session
    except ImportError:
        return redirect('/user-login.html?error=oauth_not_available')
    
    # Save the page user wants to return to
    return_to = request.args.get('return_to', request.referrer or '/onboarding.html')
    # Filter out login/register pages from return_to
    if return_to and any(x in return_to for x in ['/user-login', '/user-register', '/auth/', '/callback/']):
        return_to = '/onboarding.html'
    session['return_to'] = return_to
    
    # Use dynamic redirect URI if needed
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
    if not redirect_uri:
        # Auto-detect from current request
        redirect_uri = request.url_root.rstrip('/') + '/callback/google'
    
    google = OAuth2Session(
        GOOGLE_CLIENT_ID,
        redirect_uri=redirect_uri,
        scope=['openid', 'email', 'profile']
    )
    
    authorization_url, state = google.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        access_type='offline',
        prompt='select_account'
    )
    
    session['oauth_state'] = state
    return redirect(authorization_url)


@app.route('/callback/google')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        from requests_oauthlib import OAuth2Session
    except ImportError:
        return "خطا: requests-oauthlib نصب نیست. لطفاً pip install requests-oauthlib را اجرا کنید", 500
    
    try:
        # Use dynamic redirect URI if needed
        redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
        if not redirect_uri:
            # Auto-detect from current request
            redirect_uri = request.url_root.rstrip('/') + '/callback/google'
        
        google = OAuth2Session(
            GOOGLE_CLIENT_ID,
            redirect_uri=redirect_uri,
            state=session.get('oauth_state')
        )
        
        # Get token
        token = google.fetch_token(
            'https://oauth2.googleapis.com/token',
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=request.url
        )
        
        # Get user info
        resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info = resp.json()
        
        email = user_info.get('email', '')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')  # Google profile picture URL
        
        if not email:
            return redirect('/user-login.html?error=no_email')
        
        # Check if user exists
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, email_verified, phone_verified, status FROM website_users WHERE email = ?', (email.lower(),))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # User exists - login
            user_id = existing_user[0]
            cursor.execute('''
                UPDATE website_users 
                SET last_login = ?, email_verified = 1, profile_picture = ?, auth_method = 'google'
                WHERE id = ?
            ''', (datetime.now(), picture, user_id))
            conn.commit()
            conn.close()
            
            session.permanent = True  # Keep session for 7 days
            session['user_id'] = user_id
            session['user_email'] = email.lower()
            session['user_name'] = name
            session['auth_method'] = 'google'  # Google OAuth login
            session['google_login'] = True
            
            # Redirect to the page user came from or onboarding
            return_to = session.pop('return_to', '/onboarding.html')
            return redirect(return_to)
        else:
            # New user - create account with active status
            # Use 'google_oauth' as placeholder for password_hash since user logs in via Google
            cursor.execute('''
                INSERT INTO website_users 
                (full_name, email, phone, password_hash, profile_picture, email_verified, phone_verified, status, auth_method)
                VALUES (?, ?, '', 'google_oauth', ?, 1, 0, 'active', 'google')
            ''', (name, email.lower(), picture))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            session.permanent = True  # Keep session for 7 days
            session['user_id'] = user_id
            session['user_email'] = email.lower()
            session['user_name'] = name
            session['auth_method'] = 'google'  # Google OAuth login
            session['google_login'] = True
            
            # Redirect to the page user came from or onboarding
            return_to = session.pop('return_to', '/onboarding.html')
            return redirect(return_to)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(f'/user-login.html?error={str(e)}')


@app.route('/api/send-phone-verification', methods=['POST'])
def api_send_phone_verification():
    """Send SMS verification code"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        data = request.get_json() or {}
        phone = data.get('phone', '').strip()
        
        # Validate phone format
        import re
        if not phone or not re.match(r'^09\d{9}$', phone):
            return jsonify({'success': False, 'error': 'شماره موبایل باید با 09 شروع شود و 11 رقم باشد'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        # Update phone number for user
        cursor.execute('UPDATE website_users SET phone = ? WHERE id = ?', (phone, user_id))
        
        # Generate code
        code = generate_sms_code()
        code_expires = datetime.now() + timedelta(minutes=5)
        
        # Save code
        cursor.execute('''
            UPDATE website_users 
            SET phone_verification_code = ?, phone_verification_expires = ?
            WHERE id = ?
        ''', (code, code_expires, user_id))
        conn.commit()
        conn.close()
        
        # Send SMS
        success, message = send_sms_verification(phone, code)
        
        if not success:
            return jsonify({'success': False, 'error': message}), 500
        
        return jsonify({
            'success': True,
            'message': 'کد تایید به شماره شما ارسال شد',
            'phone': phone[:4] + '***' + phone[-4:]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/verify-phone', methods=['POST'])
def api_verify_phone():
    """Verify phone with SMS code"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'success': False, 'error': 'کد تایید الزامی است'}), 400
        
        user_id = session['user_id']
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT phone_verification_code, phone_verification_expires 
            FROM website_users WHERE id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        saved_code, expires = result
        
        if not saved_code:
            conn.close()
            return jsonify({'success': False, 'error': 'ابتدا کد تایید را درخواست کنید'}), 400
        
        # Check expiration
        if datetime.now() > datetime.fromisoformat(expires):
            conn.close()
            return jsonify({'success': False, 'error': 'کد تایید منقضی شده است'}), 400
        
        # Verify code
        if code != saved_code:
            conn.close()
            return jsonify({'success': False, 'error': 'کد تایید اشتباه است'}), 400
        
        # Mark phone as verified and activate user if phone auth
        cursor.execute('''
            UPDATE website_users 
            SET phone_verified = 1, 
                phone_verification_code = NULL,
                status = CASE 
                    WHEN auth_method = 'phone' THEN 'active'
                    WHEN email_verified = 1 THEN 'active' 
                    ELSE status 
                END
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'شماره تلفن با موفقیت تایید شد'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user-status', methods=['GET'])
@app.route('/api/auth/me', methods=['GET'])
def api_user_status():
    """Get current user status"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
        
        user_id = session['user_id']
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, full_name, email, phone, auth_method, profile_picture, email_verified, phone_verified, status
            FROM website_users WHERE id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user_id, full_name, email, phone, db_auth_method, profile_picture, email_verified, phone_verified, status = result
        
        # Use session auth_method (current login method) instead of database value
        current_auth_method = session.get('auth_method', db_auth_method or 'email')
        
        # Check if user is admin
        is_admin = email.lower() in [e.lower() for e in ADMIN_EMAILS]
        
        # Get user's licenses
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, license_key, plan_id, plan_name, hardware_id, status, 
                   price, duration_months, activated_at, expires_at, created_at
            FROM user_licenses WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        license_rows = cursor.fetchall()
        conn.close()
        
        licenses = []
        for row in license_rows:
            licenses.append({
                'id': row['id'],
                'license_key': row['license_key'],
                'plan_id': row['plan_id'],
                'plan_name': row['plan_name'],
                'hardware_id': row['hardware_id'],
                'status': row['status'],
                'price': row['price'],
                'duration_months': row['duration_months'],
                'activated_at': row['activated_at'],
                'expires_at': row['expires_at'],
                'created_at': row['created_at']
            })
        
        return jsonify({
            'success': True,
            'logged_in': True,
            'user': {
                'id': user_id,
                'name': full_name,
                'email': email,
                'phone': phone,
                'auth_method': current_auth_method,
                'profile_picture': profile_picture,
                'email_verified': bool(email_verified),
                'phone_verified': bool(phone_verified),
                'status': status,
                'is_admin': is_admin
            },
            'licenses': licenses
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plans', methods=['GET'])
def api_get_plans():
    """Get available license plans from database"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get active plans ordered by display_order
        cursor.execute('''
            SELECT id, plan_id, name_fa, name_en, price, duration_months,
                   duration_display_fa, duration_display_en, discount_percent,
                   features, is_popular, display_order
            FROM plans
            WHERE is_active = 1
            ORDER BY display_order ASC, id ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        plans = []
        for row in rows:
            # Format price for display
            price_formatted = f"{row['price']:,}".replace(',', ',')
            price_display_fa = f"{price_formatted} تومان"
            
            # Parse features (stored as pipe-separated string)
            features_str = row['features'] or ''
            features_list = [f.strip() for f in features_str.split('|') if f.strip()]
            
            # Calculate discount message
            discount_msg = None
            if row['discount_percent'] and row['discount_percent'] > 0:
                discount_msg = f"{row['discount_percent']}٪ تخفیف"
            
            plan = {
                'id': row['plan_id'],
                'name': row['name_fa'],
                'name_en': row['name_en'],
                'price': row['price'],
                'price_display': price_display_fa,
                'duration': row['duration_display_fa'],
                'duration_en': row['duration_display_en'],
                'duration_months': row['duration_months'],
                'discount': discount_msg,
                'features': features_list,
                'popular': bool(row['is_popular'])
            }
            plans.append(plan)
        
        return jsonify({'success': True, 'plans': plans})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/plans', methods=['GET'])
def api_admin_get_all_plans():
    """Get all plans including inactive ones (admin only)"""
    try:
        # Check admin
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or result[0].lower() not in [e.lower() for e in ADMIN_EMAILS]:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        # Get all plans
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM plans ORDER BY display_order ASC, id ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        plans = []
        for row in rows:
            plan = dict(row)
            # Parse features
            if plan['features']:
                plan['features'] = [f.strip() for f in plan['features'].split('|') if f.strip()]
            else:
                plan['features'] = []
            plans.append(plan)
        
        return jsonify({'success': True, 'plans': plans})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/plans', methods=['POST'])
def api_admin_create_plan():
    """Create new plan (admin only)"""
    try:
        # Check admin
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or result[0].lower() not in [e.lower() for e in ADMIN_EMAILS]:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required = ['plan_id', 'name_fa', 'name_en', 'price', 'duration_months']
        for field in required:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'فیلد {field} الزامی است'}), 400
        
        # Prepare features string
        features = data.get('features', [])
        features_str = '|'.join(features) if isinstance(features, list) else features
        
        # Insert plan
        cursor.execute('''
            INSERT INTO plans (plan_id, name_fa, name_en, price, duration_months, duration_display_fa,
                             duration_display_en, discount_percent, features, is_popular, is_active, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['plan_id'],
            data['name_fa'],
            data['name_en'],
            data['price'],
            data['duration_months'],
            data.get('duration_display_fa', ''),
            data.get('duration_display_en', ''),
            data.get('discount_percent', 0),
            features_str,
            1 if data.get('is_popular') else 0,
            1 if data.get('is_active', True) else 0,
            data.get('display_order', 0)
        ))
        
        conn.commit()
        plan_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'plan_id': plan_id, 'message': 'پلن با موفقیت ایجاد شد'})
        
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'این شناسه پلن قبلاً استفاده شده است'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/plans/<int:plan_id>', methods=['PUT'])
def api_admin_update_plan(plan_id):
    """Update plan (admin only)"""
    try:
        # Check admin
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or result[0].lower() not in [e.lower() for e in ADMIN_EMAILS]:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        
        # Prepare features string
        features = data.get('features', [])
        features_str = '|'.join(features) if isinstance(features, list) else features
        
        # Update plan
        cursor.execute('''
            UPDATE plans SET
                name_fa = ?, name_en = ?, price = ?, duration_months = ?,
                duration_display_fa = ?, duration_display_en = ?, discount_percent = ?,
                features = ?, is_popular = ?, is_active = ?, display_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('name_fa'),
            data.get('name_en'),
            data.get('price'),
            data.get('duration_months'),
            data.get('duration_display_fa', ''),
            data.get('duration_display_en', ''),
            data.get('discount_percent', 0),
            features_str,
            1 if data.get('is_popular') else 0,
            1 if data.get('is_active', True) else 0,
            data.get('display_order', 0),
            plan_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'پلن با موفقیت به‌روزرسانی شد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/plans/<int:plan_id>', methods=['DELETE'])
def api_admin_delete_plan(plan_id):
    """Delete plan (admin only)"""
    try:
        # Check admin
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or result[0].lower() not in [e.lower() for e in ADMIN_EMAILS]:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        # Delete plan
        cursor.execute('DELETE FROM plans WHERE id = ?', (plan_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'پلن با موفقیت حذف شد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ========================================
# TICKET SYSTEM APIS
# ========================================

@app.route('/api/tickets', methods=['GET'])
def api_get_tickets():
    """Get tickets - users see their own, admins see all"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if admin
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        is_admin = user and user['email'].lower() in [e.lower() for e in ADMIN_EMAILS]
        
        # Build query based on admin status
        if is_admin:
            cursor.execute('''
                SELECT t.*, u.full_name as user_name, u.email as user_email,
                       (SELECT COUNT(*) FROM ticket_messages WHERE ticket_id = t.id) as message_count
                FROM tickets t
                JOIN website_users u ON t.user_id = u.id
                ORDER BY t.updated_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT t.*, u.full_name as user_name, u.email as user_email,
                       (SELECT COUNT(*) FROM ticket_messages WHERE ticket_id = t.id) as message_count
                FROM tickets t
                JOIN website_users u ON t.user_id = u.id
                WHERE t.user_id = ?
                ORDER BY t.updated_at DESC
            ''', (user_id,))
        
        tickets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'tickets': tickets, 'is_admin': is_admin})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickets', methods=['POST'])
def api_create_ticket():
    """Create new ticket"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        data = request.get_json()
        
        # Validate required fields
        if not data.get('subject') or not data.get('message') or not data.get('category'):
            return jsonify({'success': False, 'error': 'لطفاً تمام فیلدها را پر کنید'}), 400
        
        # Generate ticket number
        import time
        ticket_number = f"TKT-{int(time.time())}"
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        # Create ticket
        cursor.execute('''
            INSERT INTO tickets (ticket_number, user_id, subject, category, priority, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        ''', (ticket_number, user_id, data['subject'], data['category'], data.get('priority', 'medium')))
        
        ticket_id = cursor.lastrowid
        
        # Add first message
        cursor.execute('''
            INSERT INTO ticket_messages (ticket_id, user_id, is_admin, message)
            VALUES (?, ?, 0, ?)
        ''', (ticket_id, user_id, data['message']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'ticket_number': ticket_number, 'ticket_id': ticket_id})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def api_get_ticket_details(ticket_id):
    """Get ticket details with all messages"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if admin
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        is_admin = user and user['email'].lower() in [e.lower() for e in ADMIN_EMAILS]
        
        # Get ticket
        cursor.execute('''
            SELECT t.*, u.full_name as user_name, u.email as user_email
            FROM tickets t
            JOIN website_users u ON t.user_id = u.id
            WHERE t.id = ?
        ''', (ticket_id,))
        
        ticket = cursor.fetchone()
        
        if not ticket:
            conn.close()
            return jsonify({'success': False, 'error': 'تیکت یافت نشد'}), 404
        
        # Check permission (admin or owner)
        if not is_admin and ticket['user_id'] != user_id:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        # Get messages
        cursor.execute('''
            SELECT m.*, u.full_name as sender_name, u.email as sender_email
            FROM ticket_messages m
            JOIN website_users u ON m.user_id = u.id
            WHERE m.ticket_id = ?
            ORDER BY m.created_at ASC
        ''', (ticket_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'ticket': dict(ticket),
            'messages': messages,
            'is_admin': is_admin
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickets/<int:ticket_id>/messages', methods=['POST'])
def api_add_ticket_message(ticket_id):
    """Add message to ticket"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        data = request.get_json()
        
        if not data.get('message'):
            return jsonify({'success': False, 'error': 'پیام نمی‌تواند خالی باشد'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        # Check if admin
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        is_admin = user and user[0].lower() in [e.lower() for e in ADMIN_EMAILS]
        
        # Check ticket exists and user has permission
        cursor.execute('SELECT user_id, status FROM tickets WHERE id = ?', (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            conn.close()
            return jsonify({'success': False, 'error': 'تیکت یافت نشد'}), 404
        
        if not is_admin and ticket[0] != user_id:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        # Add message
        cursor.execute('''
            INSERT INTO ticket_messages (ticket_id, user_id, is_admin, message)
            VALUES (?, ?, ?, ?)
        ''', (ticket_id, user_id, 1 if is_admin else 0, data['message']))
        
        # Update ticket timestamp and status if was closed
        if ticket[1] == 'closed':
            cursor.execute('''
                UPDATE tickets SET status = 'open', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (ticket_id,))
        else:
            cursor.execute('''
                UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (ticket_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'پیام با موفقیت ارسال شد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickets/<int:ticket_id>/status', methods=['PUT'])
def api_update_ticket_status(ticket_id):
    """Update ticket status (admin only)"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        # Check if admin
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0].lower() not in [e.lower() for e in ADMIN_EMAILS]:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['open', 'in_progress', 'waiting', 'closed']:
            conn.close()
            return jsonify({'success': False, 'error': 'وضعیت نامعتبر'}), 400
        
        # Update status
        if new_status == 'closed':
            cursor.execute('''
                UPDATE tickets SET status = ?, closed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, ticket_id))
        else:
            cursor.execute('''
                UPDATE tickets SET status = ?, closed_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, ticket_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'وضعیت تیکت به‌روزرسانی شد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickets/<int:ticket_id>/priority', methods=['PUT'])
def api_update_ticket_priority(ticket_id):
    """Update ticket priority (admin only)"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        # Check if admin
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0].lower() not in [e.lower() for e in ADMIN_EMAILS]:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی غیرمجاز'}), 403
        
        data = request.get_json()
        new_priority = data.get('priority')
        
        if new_priority not in ['low', 'medium', 'high', 'urgent']:
            conn.close()
            return jsonify({'success': False, 'error': 'اولویت نامعتبر'}), 400
        
        # Update priority
        cursor.execute('''
            UPDATE tickets SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (new_priority, ticket_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'اولویت تیکت به‌روزرسانی شد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    """Get list of all site users (admin only)"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        # Get current user's email to check admin status
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_email = result[0]
        is_admin = user_email.lower() in [e.lower() for e in ADMIN_EMAILS]
        
        if not is_admin:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی مجاز نیست'}), 403
        
        # Get all users from website_users table
        cursor.execute('''
            SELECT id, full_name, email, phone, auth_method, profile_picture, 
                   email_verified, phone_verified, status, created_at, last_login
            FROM website_users
            ORDER BY created_at DESC
        ''')
        users_data = cursor.fetchall()
        conn.close()
        
        users = []
        for user in users_data:
            user_id, full_name, email, phone, auth_method, profile_picture, \
                email_verified, phone_verified, status, created_at, last_login = user
            
            # Check if user is in admin list
            check_is_admin = email and email.lower() in [e.lower() for e in ADMIN_EMAILS]
            
            users.append({
                'id': user_id,
                'name': full_name or '',
                'email': email or '',
                'phone': phone or '',
                'auth_method': auth_method or 'email',
                'profile_picture': profile_picture,
                'email_verified': bool(email_verified),
                'phone_verified': bool(phone_verified),
                'status': status or 'active',
                'created_at': created_at,
                'last_login': last_login,
                'is_admin': check_is_admin
            })
        
        return jsonify({
            'success': True,
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/users/status', methods=['PATCH'])
def api_admin_update_user_status():
    """Update user status (admin only)"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        # Get current user's email to check admin status
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_email = result[0]
        is_admin = user_email.lower() in [e.lower() for e in ADMIN_EMAILS]
        
        if not is_admin:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی مجاز نیست'}), 403
        
        data = request.get_json()
        target_user_id = data.get('user_id')
        new_status = data.get('status')
        
        if not target_user_id or not new_status:
            conn.close()
            return jsonify({'success': False, 'error': 'پارامترهای لازم ارسال نشده است'}), 400
        
        if new_status not in ['active', 'inactive', 'pending']:
            conn.close()
            return jsonify({'success': False, 'error': 'وضعیت نامعتبر است'}), 400
        
        # Update user status
        cursor.execute('UPDATE website_users SET status = ? WHERE id = ?', (new_status, target_user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'وضعیت کاربر به {new_status} تغییر کرد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/users/admin-status', methods=['PATCH'])
def api_admin_toggle_admin():
    """Toggle admin status for user (admin only)"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        # Get current user's email to check admin status
        user_id = session['user_id']
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_email = result[0]
        is_admin = user_email.lower() in [e.lower() for e in ADMIN_EMAILS]
        
        if not is_admin:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی مجاز نیست'}), 403
        
        data = request.get_json()
        target_user_id = data.get('user_id')
        new_admin_status = data.get('is_admin')
        
        if target_user_id is None or new_admin_status is None:
            conn.close()
            return jsonify({'success': False, 'error': 'پارامترهای لازم ارسال نشده است'}), 400
        
        # Get target user email
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (target_user_id,))
        target = cursor.fetchone()
        
        if not target:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر هدف یافت نشد'}), 404
        
        target_email = target[0]
        
        # Note: This updates the ADMIN_EMAILS list in memory only
        # For production, you should store admin status in database
        if new_admin_status:
            if target_email.lower() not in [e.lower() for e in ADMIN_EMAILS]:
                ADMIN_EMAILS.append(target_email)
                message = f'دسترسی ادمین به {target_email} داده شد'
            else:
                message = 'این کاربر قبلاً ادمین بود'
        else:
            ADMIN_EMAILS[:] = [e for e in ADMIN_EMAILS if e.lower() != target_email.lower()]
            message = f'دسترسی ادمین از {target_email} حذف شد'
        
        conn.close()
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def api_admin_delete_user(user_id):
    """Delete user (admin only)"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        # Get current user's email to check admin status
        current_user_id = session['user_id']
        
        # Prevent self-deletion
        if current_user_id == user_id:
            return jsonify({'success': False, 'error': 'نمی‌توانید خودتان را حذف کنید'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM website_users WHERE id = ?', (current_user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        user_email = result[0]
        is_admin = user_email.lower() in [e.lower() for e in ADMIN_EMAILS]
        
        if not is_admin:
            conn.close()
            return jsonify({'success': False, 'error': 'دسترسی مجاز نیست'}), 403
        
        # Delete user
        cursor.execute('DELETE FROM website_users WHERE id = ?', (user_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'کاربر یافت نشد'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'کاربر با موفقیت حذف شد'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/verify-email', methods=['GET'])
def verify_email():
    """Verify email with token from link"""
    token = request.args.get('token', '')
    
    if not token:
        return "توکن نامعتبر است", 400
    
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, email_verification_expires 
            FROM website_users 
            WHERE email_verification_token = ?
        ''', (token,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return "توکن نامعتبر است", 404
        
        user_id, expires = result
        
        # Check expiration
        if datetime.now() > datetime.fromisoformat(expires):
            conn.close()
            return "توکن منقضی شده است. لطفاً مجدداً درخواست دهید.", 400
        
        # Mark email as verified
        cursor.execute('''
            UPDATE website_users 
            SET email_verified = 1, 
                email_verification_token = NULL,
                status = CASE WHEN phone_verified = 1 THEN 'active' ELSE 'pending' END
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        
        return redirect('/email-verified.html')
        
    except Exception as e:
        return f"خطا: {str(e)}", 500


@app.route('/api/odoo-login', methods=['POST'])
def api_odoo_login():
    """Login to Odoo and return session URL for redirection"""
    try:
        data = request.get_json()
        db = data.get('db')
        login = data.get('login')
        password = data.get('password')
        
        if not db or not login or not password:
            return jsonify({'success': False, 'error': 'اطلاعات ناقص است'}), 400
        
        # Create a session to maintain cookies
        session_obj = requests.Session()
        
        # Step 1: Authenticate via Odoo JSON-RPC
        auth_url = f"{ODOO_URL}/web/session/authenticate"
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": db,
                "login": login,
                "password": password
            }
        }
        
        response = session_obj.post(auth_url, json=auth_payload, timeout=10)
        result = response.json()
        
        if 'error' in result:
            error_msg = result['error'].get('data', {}).get('message', 'خطای نامشخص')
            return jsonify({'success': False, 'error': error_msg}), 401
        
        if not result.get('result', {}).get('uid'):
            return jsonify({'success': False, 'error': 'نام کاربری یا رمز عبور اشتباه است'}), 401
        
        # Success! Get the session cookie
        session_id = session_obj.cookies.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'دریافت session ناموفق بود'}), 500
        
        # Return the session_id so frontend can set it
        return jsonify({
            'success': True,
            'session_id': session_id,
            'odoo_url': ODOO_URL,
            'message': 'ورود موفقیت‌آمیز بود'
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'زمان اتصال به سرور تمام شد'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'خطا در اتصال به سرور Odoo'}), 503
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# HTML Pages for Authentication

@app.route('/register')
def register_page():
    """Registration page"""
    return send_from_directory('website', 'register.html')

@app.route('/login')
def login_page():
    """Login page"""
    return send_from_directory('website', 'login.html')

@app.route('/verify-account')
def verify_account_page():
    """Account verification page"""
    return send_from_directory('website', 'verify-account.html')

@app.route('/email-verified.html')
def email_verified_page():
    """Email verified success page"""
    return send_from_directory('website', 'email-verified.html')

# Protect onboarding page with login (middleware handles this now)
@app.route('/onboarding.html')
def onboarding_protected():
    """Protected onboarding page - authentication checked in middleware"""
    return send_from_directory('website', 'onboarding.html')

# Protect profile page
@app.route('/profile.html')
def profile_protected():
    """Protected profile page - authentication checked in middleware"""
    return send_from_directory('website', 'profile.html')

# Download lite-online installer ZIP
@app.route('/downloads/odoo19-lite-online.zip')
def download_lite_online_zip():
    """
    Serve the pre-built lite online installer ZIP file
    """
    try:
        zip_path = Path('private_downloads/installers/odoo19-lite-online.zip')
        if zip_path.exists():
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='odoo19-lite-online.zip'
            )
        else:
            return jsonify({'error': 'Installer file not found'}), 404
    except Exception as e:
        print(f"Error serving ZIP: {e}")
        return jsonify({'error': 'Failed to serve ZIP file', 'detail': str(e)}), 500


# ============================================
# Purchase API
# ============================================

@app.route('/api/purchase', methods=['POST'])
def purchase_plan():
    """خرید پلن"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        hardware_id = data.get('hardware_id')
        customer_name = data.get('customer_name')
        customer_email = data.get('customer_email')
        customer_phone = data.get('customer_phone')
        
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            user_email = request.cookies.get('user_email')
            if user_email:
                conn = sqlite3.connect(CUSTOMERS_DB)
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM customers WHERE admin_email = ?', (user_email,))
                result = cursor.fetchone()
                conn.close()
                if result:
                    user_id = result[0]
        
        if not user_id:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        # Validate required fields
        if not plan_id:
            return jsonify({'success': False, 'error': 'پلن انتخاب نشده است'}), 400
        
        if not hardware_id:
            return jsonify({'success': False, 'error': 'شناسه سخت‌افزاری الزامی است'}), 400
        
        if not customer_name:
            return jsonify({'success': False, 'error': 'نام و نام خانوادگی الزامی است'}), 400
        
        if not customer_email:
            return jsonify({'success': False, 'error': 'ایمیل الزامی است'}), 400
        
        if not customer_phone:
            return jsonify({'success': False, 'error': 'شماره تماس الزامی است'}), 400
        
        # Get plan details from plans table (using plan_id TEXT field, not id INTEGER)
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM plans WHERE plan_id = ?', (plan_id,))
        plan = cursor.fetchone()
        conn.close()
        
        if not plan:
            return jsonify({'success': False, 'error': 'پلن یافت نشد'}), 404
        
        # Generate unique license key
        import uuid
        import hashlib
        from datetime import datetime, timedelta
        
        unique_str = f"{user_id}-{plan_id}-{hardware_id}-{datetime.now().isoformat()}"
        license_key = hashlib.sha256(unique_str.encode()).hexdigest()[:32].upper()
        license_key = f"LIC-{license_key[:8]}-{license_key[8:16]}-{license_key[16:24]}-{license_key[24:32]}"
        
        # Calculate expiry date
        duration_months = plan['duration_months']
        expires_at = datetime.now() + timedelta(days=duration_months * 30)
        
        # Save license to database
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_licenses 
            (user_id, license_key, plan_id, plan_name, hardware_id, status, price, duration_months, activated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, CURRENT_TIMESTAMP, ?)
        ''', (user_id, license_key, plan_id, plan['name_fa'], hardware_id, plan['price'], duration_months, expires_at.isoformat()))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'خرید با موفقیت انجام شد',
            'license_key': license_key,
            'expires_at': expires_at.isoformat(),
            'plan_name': plan['name_fa']
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/licenses/<license_key>/file', methods=['POST'])
def api_generate_license_file(license_key):
    """Generate signed license file for download"""
    import json
    import hashlib
    import base64
    from datetime import datetime
    
    try:
        # Get user from session
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'لطفاً ابتدا وارد شوید'}), 401
        
        user_id = session['user_id']
        
        # Get license from database
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ul.*, wu.email, wu.full_name
            FROM user_licenses ul
            JOIN website_users wu ON ul.user_id = wu.id
            WHERE ul.license_key = ? AND ul.user_id = ?
        ''', (license_key, user_id))
        license_row = cursor.fetchone()
        conn.close()
        
        if not license_row:
            return jsonify({'success': False, 'error': 'لایسنس یافت نشد'}), 404
        
        # Get hardware_id from request body or from license
        data = request.get_json() or {}
        hardware_id = data.get('hardware_id') or license_row['hardware_id']
        
        if not hardware_id:
            return jsonify({'success': False, 'error': 'شناسه سخت‌افزاری یافت نشد'}), 400
        
        # Create v2 license file content (compatible with offline installer)
        # Build payload (without signature)
        payload = {
            'v': 2,
            'license_key': license_row['license_key'],
            'license_id': license_row['license_key'],  # For blacklist support
            'hardware_id': hardware_id,
            'user_email': license_row['email'],
            'user_name': license_row['full_name'],
            'plan_id': license_row['plan_id'],
            'plan_name': license_row['plan_name'],
            'status': license_row['status'],
            'activated_at': license_row['activated_at'],
            'expires_at': license_row['expires_at'],
            'issued_at': datetime.now().isoformat()
        }
        
        # Generate RSA-PSS signature using private key
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            
            # Load private key from env var or file
            private_key_pem = os.environ.get('LICENSE_PRIVATE_KEY_PEM', '').strip()
            if private_key_pem:
                # From environment variable (replace escaped newlines)
                private_key_pem = private_key_pem.replace('\\n', '\n')
                private_key = load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
            else:
                # From file (for local development)
                private_key_path = os.path.join(os.path.dirname(__file__), 'license_private_key.pem')
                with open(private_key_path, 'rb') as f:
                    private_key = load_pem_private_key(f.read(), password=None)
            
            # Canonical JSON for signing
            message = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
            
            # Sign with RSA-PSS SHA256
            import base64
            signature = private_key.sign(
                message,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            # Add signature to payload
            license_file = dict(payload)
            license_file['sig'] = signature_b64
            
        except Exception as sign_error:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'خطا در امضای لایسنس: {str(sign_error)}'}), 500
        
        return jsonify({
            'success': True,
            'license_file': license_file
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# General route for serving static files (CSS, JS, HTML)
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from website folder"""
    # Don't intercept API routes
    if filename.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory('website', filename)

# Initialize database on module load (for gunicorn in Liara)
init_customers_db()

if __name__ == "__main__":
    # Get port from environment variable or default to 5002 (offline version uses different port)
    port = int(os.environ.get('PORT', 5002))
    
    # Set UTF-8 encoding for console output
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    print(f"\n{'='*60}")
    print(f"  OdooMaster Multi-Tenant SaaS Platform")
    print(f"{'='*60}")
    print(f"\n  Flask Server: http://localhost:{port}")
    print(f"  Odoo Server: {ODOO_URL}")
    print(f"\n  Pages:")
    print(f"    - Home:        http://localhost:{port}/")
    print(f"    - Install:     http://localhost:{port}/install")
    print(f"    - Register:    http://localhost:{port}/register_tenant.html")
    print(f"\n  API:")
    print(f"    - POST /api/create-tenant")
    print(f"    - GET  /api/list-customers")
    print(f"\n  Press Ctrl+C to stop\n")
    print(f"{'='*60}\n")
    
    # Use debug=False in production (Liara)
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)

