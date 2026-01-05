#!/usr/bin/env python3
"""
OdooMaster Backend API Server
سرور API برای مدیریت دموها، تیکت‌ها و کاربران

Requirements:
    pip install flask flask-cors

Usage:
    python api_server.py
    
    Server will run on: http://localhost:5001
"""

from flask import Flask, request, jsonify, send_from_directory, make_response, redirect, session
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import uuid
import requests
import random
import string
from pathlib import Path
import sqlite3

import xmlrpc.client

app = Flask(
    __name__,
    static_folder='website',
    template_folder='website',
)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.environ.get('SECRET_KEY', 'odoomaster-super-secret-key-2025')

# ============================================
# Multi-tenant SaaS configuration (Liara)
# ============================================

ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo-online.liara.run')
ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'admin')

# Local SQLite database for customer management
CUSTOMERS_DB = 'customers.db'
WEBSITE_DB = 'website_users.db'  # Database for website users and tickets


def init_customers_db():
    """Initialize SQLite database for customer management"""
    conn = sqlite3.connect(CUSTOMERS_DB)
    cursor = conn.cursor()
    cursor.execute(
        '''
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
            last_login TIMESTAMP
        )
        '''
    )
    conn.commit()
    conn.close()


def generate_tenant_db_name(company_name: str) -> str:
    """Generate unique database name from company name"""
    clean_name = ''.join(c for c in (company_name or '') if c.isalnum())[:20]
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"odoo_{clean_name.lower()}_{suffix}" if clean_name else f"odoo_{suffix}"


def generate_tenant_password(length: int = 12) -> str:
    """Generate secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))


def create_odoo_tenant_database(
    db_name: str,
    admin_email: str,
    admin_password: str,
    company_name: str,
    lang: str = 'fa_IR',
    country: str = 'IR',
    with_demo: bool = True,
):
    """Create new Odoo database using web_db API (JSON-RPC)."""
    url = f"{ODOO_URL}/web/database/create"

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "master_pwd": ODOO_MASTER_PASSWORD,
            "name": db_name,
            "login": admin_email,
            "password": admin_password,
            "lang": lang,
            "country_code": country,
            "phone": "",
            "demo": "true" if with_demo else "false",
        },
        "id": random.randint(1, 1000000),
    }

    headers = {'Content-Type': 'application/json'}

    try:
        print(f"📦 Creating database: {db_name} with lang={lang}, country={country}, demo={with_demo}")
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        result = response.json()

        if 'error' in result:
            error_msg = result.get('error', {}).get('data', {}).get('message', 'Unknown error')
            print(f"❌ Error creating database: {error_msg}")
            return False, error_msg

        print(f"✅ Database {db_name} created successfully with Persian language")
        return True, f"Database {db_name} created successfully"
    except Exception as e:
        print(f"❌ Exception creating database: {str(e)}")
        return False, str(e)


def save_customer(company_name, admin_email, admin_name, phone, database_name, admin_password):
    """Save customer information to local database"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO customers (company_name, admin_email, admin_name, phone, database_name, admin_password)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (company_name, admin_email, admin_name, phone, database_name, admin_password),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving customer: {e}")
        return False


# Ensure DB exists when running under gunicorn
try:
    init_customers_db()
except Exception as e:
    print(f"Warning: failed to init customers db: {e}")

# Data storage (در محیط واقعی از Database استفاده کنید)
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

DEMOS_FILE = DATA_DIR / 'demos.json'
TICKETS_FILE = DATA_DIR / 'tickets.json'
USERS_FILE = DATA_DIR / 'users.json'

# تنظیمات Odoo Instances
ODOO_INSTANCES = [
    {'url': 'http://localhost:8069', 'available': True, 'name': 'Demo Server 1'},
    {'url': 'http://localhost:8070', 'available': True, 'name': 'Demo Server 2'},
    {'url': 'http://localhost:8071', 'available': True, 'name': 'Demo Server 3'},
]


# Helper Functions
def load_json(file_path, default=None):
    """Load JSON data from file"""
    if default is None:
        default = []
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    return default


def save_json(file_path, data):
    """Save JSON data to file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False


def generate_db_name():
    """تولید نام دیتابیس یونیک"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"demo_{random_str}"


def generate_password():
    """تولید پسورد تصادفی"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


def get_available_instance():
    """پیدا کردن اولین instance موجود"""
    demos = load_json(DEMOS_FILE, [])
    used_urls = [d.get('odoo_url') for d in demos if d.get('status') == 'active']
    
    for instance in ODOO_INSTANCES:
        if instance['available'] and instance['url'] not in used_urls:
            return instance
    
    return None


def create_odoo_database(url, db_name, company_name, admin_email='admin', admin_password='admin'):
    """ساخت دیتابیس جدید در Odoo"""
    try:
        create_url = f"{url}/web/database/create"
        data = {
            'master_pwd': 'admin',
            'name': db_name,
            'login': admin_email,
            'password': admin_password,
            'lang': 'fa_IR',
            'country_code': 'IR',
            'phone': '',
            'demo': 'true',
        }
        
        response = requests.post(create_url, data=data, timeout=300)
        return response.status_code == 200
    except Exception as e:
        print(f"خطا در ساخت دیتابیس: {e}")
        return False


def delete_odoo_database(url, db_name):
    """حذف دیتابیس از Odoo"""
    try:
        delete_url = f"{url}/web/database/drop"
        data = {
            'master_pwd': 'admin',
            'name': db_name
        }
        
        response = requests.post(delete_url, data=data, timeout=60)
        return response.status_code == 200
    except Exception as e:
        print(f"خطا در حذف دیتابیس: {e}")
        return False


# ============================================
# DEMO MANAGEMENT APIs
# ============================================

# SPA ROUTES - All frontend routes go through app.html
SPA_ROUTES = ['/', '/features', '/downloads', '/support', '/dashboard', '/login', '/register', '/onboarding', '/settings', '/profile', '/docs', '/faq', '/contact', '/about', '/privacy', '/terms', '/forgot-password']

@app.route('/')
def spa_index():
    """Main SPA entry point"""
    return send_from_directory('website', 'app.html')

@app.route('/install', methods=['GET'])
def site_install():
    return send_from_directory('website', 'install.html')

@app.route('/installer', methods=['GET'])
def site_installer():
    return send_from_directory('website', 'install.html')

# SPA catch-all for client-side routing
@app.route('/<path:path>', methods=['GET'])
def site_static(path):
    # Static files (css, js, images, etc.)
    if '.' in path:
        return send_from_directory('website', path)
    # SPA routes - return app.html for client-side routing
    return send_from_directory('website', 'app.html')

@app.route('/api/demo/list', methods=['GET'])
def list_demos():
    """لیست تمام دموهای کاربر"""
    demos = load_json(DEMOS_FILE, [])
    
    # محاسبه روزهای باقی‌مانده
    now = datetime.now()
    for demo in demos:
        expires_at = datetime.fromisoformat(demo['expiresAt'])
        remaining = (expires_at - now).days
        demo['remainingDays'] = max(0, remaining)
        demo['status'] = 'active' if remaining > 0 else 'expired'
    
    # فیلتر دموهای فعال
    active_demos = [d for d in demos if d['status'] == 'active']
    
    return jsonify({
        'success': True,
        'demos': active_demos,
        'count': len(active_demos)
    })


@app.route('/api/demo/create', methods=['POST'])
def create_demo():
    """ساخت دموی جدید با Odoo واقعی"""
    data = request.get_json()
    
    company_name = data.get('name', 'شرکت نمونه')
    duration_days = int(data.get('duration', 14))
    
    # Load existing demos
    demos = load_json(DEMOS_FILE, [])
    
    # Check max limit (3 demos per user)
    active_demos = [d for d in demos if d.get('status') == 'active']
    if len(active_demos) >= 3:
        return jsonify({
            'success': False,
            'error': 'حداکثر تعداد دمو (۳) محدود است'
        }), 400
    
    # پیدا کردن instance موجود
    instance = get_available_instance()
    if not instance:
        return jsonify({
            'success': False,
            'error': 'هیچ سرور موجودی در دسترس نیست. لطفاً بعداً تلاش کنید.'
        }), 503
    
    # تولید اطلاعات دمو
    db_name = generate_db_name()
    admin_password = generate_password()
    
    # ساخت دیتابیس در Odoo
    print(f"🔨 Creating Odoo database: {db_name} on {instance['url']}")
    success = create_odoo_database(
        url=instance['url'],
        db_name=db_name,
        company_name=company_name,
        admin_email='admin',
        admin_password=admin_password
    )
    
    if not success:
        return jsonify({
            'success': False,
            'error': 'خطا در ساخت دمو. لطفاً دوباره تلاش کنید.'
        }), 500
    
    # Create new demo
    demo_id = str(uuid.uuid4())
    created_at = datetime.now()
    expires_at = created_at + timedelta(days=duration_days)
    
    demo = {
        'id': demo_id,
        'name': company_name,
        'database': db_name,
        'odoo_url': instance['url'],
        'url': f"{instance['url']}/web?db={db_name}",
        'username': 'admin',
        'password': admin_password,
        'createdAt': created_at.isoformat(),
        'expiresAt': expires_at.isoformat(),
        'remainingDays': duration_days,
        'status': 'active',
        'instance_name': instance['name']
    }
    
    demos.append(demo)
    save_json(DEMOS_FILE, demos)
    
    print(f"✅ Demo created successfully: {db_name}")
    
    return jsonify({
        'success': True,
        'message': 'دمو با موفقیت ساخته شد',
        'demo': demo
    })


@app.route('/api/demo/<demo_id>', methods=['DELETE'])
def delete_demo(demo_id):
    """حذف دمو از Odoo"""
    demos = load_json(DEMOS_FILE, [])
    
    # Find demo
    demo = next((d for d in demos if d['id'] == demo_id), None)
    if not demo:
        return jsonify({
            'success': False,
            'error': 'دمو یافت نشد'
        }), 404
    
    # حذف از Odoo
    print(f"🗑️  Deleting Odoo database: {demo['database']} from {demo['odoo_url']}")
    delete_odoo_database(demo['odoo_url'], demo['database'])
    
    # Remove from list
    demos = [d for d in demos if d['id'] != demo_id]
    save_json(DEMOS_FILE, demos)
    
    print(f"✅ Demo deleted: {demo['database']}")
    
    return jsonify({
        'success': True,
        'message': 'دمو با موفقیت حذف شد'
    })


# ============================================
# TICKET SYSTEM APIs
# ============================================

def init_tickets_db():
    """Initialize tickets database tables"""
    conn = sqlite3.connect(WEBSITE_DB)
    cursor = conn.cursor()
    
    # Create tickets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticket_number TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES website_users (id)
        )
    ''')
    
    # Create ticket_messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            user_id INTEGER,
            message TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            FOREIGN KEY (user_id) REFERENCES website_users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize tickets DB
try:
    init_tickets_db()
except Exception as e:
    print(f"Warning: Could not initialize tickets DB: {e}")


@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    """Get user's tickets or all tickets for admin"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'لطفاً وارد سیستم شوید'
            }), 401
        
        conn = sqlite3.connect(WEBSITE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user is admin
        cursor.execute('SELECT is_admin FROM website_users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        is_admin = user_row['is_admin'] if user_row else False
        
        # Get tickets
        if is_admin:
            cursor.execute('''
                SELECT t.*, u.name as user_name, u.email as user_email,
                    (SELECT COUNT(*) FROM ticket_messages WHERE ticket_id = t.id) as message_count
                FROM tickets t
                LEFT JOIN website_users u ON t.user_id = u.id
                ORDER BY t.updated_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT t.*,
                    (SELECT COUNT(*) FROM ticket_messages WHERE ticket_id = t.id) as message_count
                FROM tickets t
                WHERE t.user_id = ?
                ORDER BY t.updated_at DESC
            ''', (user_id,))
        
        tickets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'tickets': tickets,
            'is_admin': is_admin
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در دریافت تیکت‌ها: {str(e)}'
        }), 500


@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    """Create new ticket"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'لطفاً وارد سیستم شوید'
            }), 401
        
        data = request.get_json()
        subject = data.get('subject', '').strip()
        category = data.get('category', 'general')
        priority = data.get('priority', 'medium')
        message = data.get('message', '').strip()
        
        if not subject or not message:
            return jsonify({
                'success': False,
                'error': 'موضوع و پیام الزامی است'
            }), 400
        
        conn = sqlite3.connect(WEBSITE_DB)
        cursor = conn.cursor()
        
        # Generate ticket number
        ticket_number = f'TKT-{datetime.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}'
        
        # Create ticket
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO tickets (user_id, ticket_number, subject, category, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
        ''', (user_id, ticket_number, subject, category, priority, now, now))
        
        ticket_id = cursor.lastrowid
        
        # Add first message
        cursor.execute('''
            INSERT INTO ticket_messages (ticket_id, user_id, message, is_admin, created_at)
            VALUES (?, ?, ?, 0, ?)
        ''', (ticket_id, user_id, message, now))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تیکت با موفقیت ثبت شد',
            'ticket_number': ticket_number,
            'ticket_id': ticket_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در ثبت تیکت: {str(e)}'
        }), 500


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket_detail(ticket_id):
    """Get ticket details with messages"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'لطفاً وارد سیستم شوید'
            }), 401
        
        conn = sqlite3.connect(WEBSITE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user is admin
        cursor.execute('SELECT is_admin FROM website_users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        is_admin = user_row['is_admin'] if user_row else False
        
        # Get ticket
        cursor.execute('''
            SELECT t.*, u.name as user_name, u.email as user_email
            FROM tickets t
            LEFT JOIN website_users u ON t.user_id = u.id
            WHERE t.id = ?
        ''', (ticket_id,))
        
        ticket_row = cursor.fetchone()
        if not ticket_row:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'تیکت یافت نشد'
            }), 404
        
        ticket = dict(ticket_row)
        
        # Check permission
        if not is_admin and ticket['user_id'] != user_id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'دسترسی غیرمجاز'
            }), 403
        
        # Get messages
        cursor.execute('''
            SELECT m.*, u.name as sender_name, u.email as sender_email
            FROM ticket_messages m
            LEFT JOIN website_users u ON m.user_id = u.id
            WHERE m.ticket_id = ?
            ORDER BY m.created_at ASC
        ''', (ticket_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'ticket': ticket,
            'messages': messages,
            'is_admin': is_admin
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در دریافت جزئیات تیکت: {str(e)}'
        }), 500


@app.route('/api/tickets/<int:ticket_id>/messages', methods=['POST'])
def add_ticket_message(ticket_id):
    """Add message to ticket"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'لطفاً وارد سیستم شوید'
            }), 401
        
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'پیام نمی‌تواند خالی باشد'
            }), 400
        
        conn = sqlite3.connect(WEBSITE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user is admin
        cursor.execute('SELECT is_admin FROM website_users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        is_admin = user_row['is_admin'] if user_row else False
        
        # Get ticket
        cursor.execute('SELECT user_id, status FROM tickets WHERE id = ?', (ticket_id,))
        ticket_row = cursor.fetchone()
        
        if not ticket_row:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'تیکت یافت نشد'
            }), 404
        
        # Check permission
        if not is_admin and ticket_row['user_id'] != user_id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'دسترسی غیرمجاز'
            }), 403
        
        # Add message
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO ticket_messages (ticket_id, user_id, message, is_admin, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticket_id, user_id, message, 1 if is_admin else 0, now))
        
        # Update ticket timestamp and status if needed
        new_status = ticket_row['status']
        if is_admin and new_status == 'open':
            new_status = 'in_progress'
        elif not is_admin and new_status == 'waiting':
            new_status = 'in_progress'
        
        cursor.execute('''
            UPDATE tickets
            SET updated_at = ?, status = ?
            WHERE id = ?
        ''', (now, new_status, ticket_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'پیام ارسال شد'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در ارسال پیام: {str(e)}'
        }), 500


@app.route('/api/tickets/<int:ticket_id>/status', methods=['PUT'])
def update_ticket_status(ticket_id):
    """Update ticket status (admin only)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'لطفاً وارد سیستم شوید'
            }), 401
        
        conn = sqlite3.connect(WEBSITE_DB)
        cursor = conn.cursor()
        
        # Check if user is admin
        cursor.execute('SELECT is_admin FROM website_users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row or not user_row[0]:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'دسترسی غیرمجاز'
            }), 403
        
        data = request.get_json()
        status = data.get('status', '')
        
        if status not in ['open', 'in_progress', 'waiting', 'closed']:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'وضعیت نامعتبر است'
            }), 400
        
        # Update status
        cursor.execute('''
            UPDATE tickets
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (status, datetime.now().isoformat(), ticket_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'وضعیت تیکت به‌روزرسانی شد'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در به‌روزرسانی وضعیت: {str(e)}'
        }), 500


@app.route('/api/tickets/<int:ticket_id>/priority', methods=['PUT'])
def update_ticket_priority(ticket_id):
    """Update ticket priority (admin only)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'لطفاً وارد سیستم شوید'
            }), 401
        
        conn = sqlite3.connect(WEBSITE_DB)
        cursor = conn.cursor()
        
        # Check if user is admin
        cursor.execute('SELECT is_admin FROM website_users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row or not user_row[0]:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'دسترسی غیرمجاز'
            }), 403
        
        data = request.get_json()
        priority = data.get('priority', '')
        
        if priority not in ['low', 'medium', 'high', 'urgent']:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'اولویت نامعتبر است'
            }), 400
        
        # Update priority
        cursor.execute('''
            UPDATE tickets
            SET priority = ?, updated_at = ?
            WHERE id = ?
        ''', (priority, datetime.now().isoformat(), ticket_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'اولویت تیکت به‌روزرسانی شد'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در به‌روزرسانی اولویت: {str(e)}'
        }), 500


# ============================================
# AUTHENTICATION APIs
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    """ثبت نام کاربر جدید"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        
        if not all([name, email, phone, password]):
            return jsonify({
                'success': False,
                'error': 'لطفاً همه فیلدهای الزامی را تکمیل کنید'
            }), 400
        
        # Check if user already exists
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM customers WHERE admin_email = ?', (email,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'این ایمیل قبلاً ثبت شده است'
            }), 400
        
        # Create new user
        cursor.execute(
            '''
            INSERT INTO customers (company_name, admin_email, admin_name, phone, database_name, admin_password, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (name, email, name, phone, '', password, 'pending', datetime.now().isoformat())
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate token (simple demo token)
        token = f"token_{user_id}_{uuid.uuid4().hex[:16]}"
        
        user = {
            'id': user_id,
            'name': name,
            'email': email,
            'phone': phone,
            'level': 1,
            'xp': 0,
            'avatar': f'https://ui-avatars.com/api/?name={name}&background=714B67&color=fff'
        }
        
        return jsonify({
            'success': True,
            'message': 'ثبت نام با موفقیت انجام شد',
            'user': user,
            'token': token
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در ثبت نام: {str(e)}'
        }), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """ورود کاربر"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'ایمیل و رمز عبور الزامی است'
            }), 400
        
        # Find user
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, company_name, admin_name, admin_email, phone, admin_password FROM customers WHERE admin_email = ?',
            (email,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'ایمیل یا رمز عبور اشتباه است'
            }), 401
        
        user_id, company_name, admin_name, admin_email, phone, stored_password = row
        
        # Verify password (in production, use proper hashing!)
        if password != stored_password:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'ایمیل یا رمز عبور اشتباه است'
            }), 401
        
        # Update last login
        cursor.execute(
            'UPDATE customers SET last_login = ? WHERE id = ?',
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()
        conn.close()
        
        # Generate token
        token = f"token_{user_id}_{uuid.uuid4().hex[:16]}"
        
        user = {
            'id': user_id,
            'name': admin_name or company_name,
            'email': admin_email,
            'phone': phone,
            'level': 3,
            'xp': 750,
            'avatar': f'https://ui-avatars.com/api/?name={admin_name or company_name}&background=714B67&color=fff'
        }
        
        return jsonify({
            'success': True,
            'message': 'ورود موفقیت آمیز',
            'user': user,
            'token': token
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در ورود: {str(e)}'
        }), 500


@app.route('/api/auth/admin-login', methods=['POST'])
def auth_admin_login():
    """ورود مدیر سیستم"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Simple admin check (در production از database استفاده کنید)
        ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
        ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            return jsonify({
                'success': False,
                'error': 'نام کاربری یا رمز عبور مدیر اشتباه است'
            }), 401
        
        # Generate admin token
        token = f"admin_token_{uuid.uuid4().hex[:16]}"
        
        user = {
            'id': 0,
            'name': 'مدیر سیستم',
            'email': 'admin@odoomaster.com',
            'role': 'admin',
            'avatar': 'https://ui-avatars.com/api/?name=Admin&background=FF6B6B&color=fff'
        }
        
        return jsonify({
            'success': True,
            'message': 'ورود مدیر موفقیت آمیز',
            'user': user,
            'token': token
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'خطا در ورود مدیر: {str(e)}'
        }), 500


@app.route('/api/test', methods=['GET'])
def api_test():
    """Test endpoint to verify API is working"""
    return jsonify({'status': 'ok', 'message': 'API is working'})


@app.route('/auth/google')
def google_login():
    """Redirect to Google OAuth login"""
    try:
        from requests_oauthlib import OAuth2Session
    except ImportError:
        return '''
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
        <h2>خطا: ماژول OAuth نصب نیست</h2>
        <p>لطفاً دستور زیر را اجرا کنید:</p>
        <code style="background: #f0f0f0; padding: 10px; display: inline-block;">
        pip install requests-oauthlib
        </code>
        <br><br>
        <a href="/user-login.html">بازگشت به صفحه ورود</a>
        </body></html>
        '''
    
    # Dynamic redirect URI
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
    if not redirect_uri:
        redirect_uri = request.url_root.rstrip('/') + '/callback/google'
    
    # Google OAuth configuration (use environment variables)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    if not GOOGLE_CLIENT_ID:
        return "خطا: GOOGLE_CLIENT_ID تنظیم نشده است", 500
    
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
    
    # Store state in session
    from flask import session
    session['oauth_state'] = state
    session['redirect_after_login'] = request.args.get('redirect', '/onboarding.html')
    
    return redirect(authorization_url)


@app.route('/callback/google')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        from requests_oauthlib import OAuth2Session
        from flask import session
    except ImportError:
        return "خطا: requests-oauthlib نصب نیست", 500
    
    try:
        # Dynamic redirect URI
        redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
        if not redirect_uri:
            redirect_uri = request.url_root.rstrip('/') + '/callback/google'
        
        # Google OAuth configuration (use environment variables)
        GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
        GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
        
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return "خطا: تنظیمات Google OAuth ناقص است", 500
        
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
        picture = user_info.get('picture', '')
        
        if not email:
            return redirect('/user-login.html?error=no_email')
        
        # Check if user exists in database
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT admin_name, admin_email, company_name FROM customers WHERE admin_email = ?', (email.lower(),))
        existing = cursor.fetchone()
        conn.close()
        
        # Set cookies for session
        redirect_url = session.get('redirect_after_login', '/onboarding.html')
        response = make_response(redirect(redirect_url))
        response.set_cookie('user_email', email.lower(), max_age=30*24*60*60)
        response.set_cookie('user_name', name, max_age=30*24*60*60)
        response.set_cookie('auth_method', 'google', max_age=30*24*60*60)
        
        return response
        
    except Exception as e:
        print(f"Error in Google callback: {str(e)}")
        return redirect(f'/user-login.html?error=oauth_failed')


# Remove the old mock endpoints
@app.route('/api/auth/google-callback', methods=['POST'])
def auth_google_callback_old():
    """Deprecated - use /callback/google instead"""
    return jsonify({'error': 'This endpoint is deprecated. Use /callback/google instead'}), 410
    return jsonify({
        'success': True,
        'message': 'API is working!',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/install-modules', methods=['POST', 'OPTIONS'])
def api_install_modules():
    """نصب ماژول‌های Odoo برای یک دیتابیس خاص"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'داده‌ای دریافت نشد'
            }), 400
        
        db_name = data.get('db_name')
        admin_email = data.get('admin_email')
        admin_password = data.get('admin_password')
        modules = data.get('modules', ['l10n_ir', 'web_responsive', 'home_menu_fullscreen', 'base_setup'])
        
        if not all([db_name, admin_email, admin_password]):
            return jsonify({
                'success': False,
                'error': 'اطلاعات دیتابیس، ایمیل و رمز عبور الزامی است'
            }), 400
        
        print(f"📦 Installing modules for database: {db_name}")
        print(f"   Modules to install: {modules}")
        
        success, message = install_odoo_modules(
            db_name=db_name,
            admin_email=admin_email,
            admin_password=admin_password,
            modules=modules
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'ماژول‌ها با موفقیت نصب شدند',
                'details': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'خطا در نصب ماژول‌ها: {str(e)}'
        }), 500


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """خروج کاربر"""
    return jsonify({
        'success': True,
        'message': 'خروج موفقیت آمیز'
    })


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """اطلاعات کاربر فعلی از روی توکن"""
    # Extract token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return jsonify({
            'success': False,
            'error': 'توکن معتبر نیست'
        }), 401
    
    token = auth_header.replace('Bearer ', '').strip()
    
    # Parse token to get user_id
    if token.startswith('token_'):
        try:
            user_id = int(token.split('_')[1])
            
            conn = sqlite3.connect(CUSTOMERS_DB)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, company_name, admin_name, admin_email, phone FROM customers WHERE id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                user_id, company_name, admin_name, admin_email, phone = row
                user = {
                    'id': user_id,
                    'name': admin_name or company_name,
                    'email': admin_email,
                    'phone': phone,
                    'level': 3,
                    'xp': 750,
                    'avatar': f'https://ui-avatars.com/api/?name={admin_name or company_name}&background=714B67&color=fff'
                }
                return jsonify({'success': True, 'user': user})
        except:
            pass
    
    return jsonify({
        'success': False,
        'error': 'کاربر یافت نشد'
    }), 401


# ============================================
# USER & STATS APIs
# ============================================

@app.route('/api/user-status', methods=['GET'])
def get_user_status():
    """وضعیت کاربر و اطلاعات session"""
    try:
        # Check if user has session or token
        token = request.headers.get('Authorization')
        session_email = request.cookies.get('user_email')
        session_name = request.cookies.get('user_name')
        auth_method = request.cookies.get('auth_method', 'email')
        
        if not token and not session_email:
            return jsonify({
                'success': True,
                'logged_in': False,
                'user': None
            })
        
        # Try to get user from database
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        
        if session_email:
            cursor.execute(
                'SELECT admin_name, admin_email, phone, company_name FROM customers WHERE admin_email = ? LIMIT 1',
                (session_email,)
            )
            user_data = cursor.fetchone()
            
            if user_data:
                conn.close()
                return jsonify({
                    'success': True,
                    'logged_in': True,
                    'user': {
                        'name': user_data[0],
                        'email': user_data[1],
                        'phone': user_data[2] or '',
                        'company': user_data[3],
                        'auth_method': auth_method
                    }
                })
            else:
                # User logged in but not in database yet (new Google user)
                conn.close()
                return jsonify({
                    'success': True,
                    'logged_in': True,
                    'user': {
                        'name': session_name or 'کاربر',
                        'email': session_email,
                        'phone': '',
                        'company': None,
                        'auth_method': auth_method
                    }
                })
        
        conn.close()
        
        # If no user found, return not logged in
        return jsonify({
            'success': True,
            'logged_in': False,
            'user': None
        })
        
    except Exception as e:
        print(f"Error in user-status: {str(e)}")
        return jsonify({
            'success': False,
            'logged_in': False,
            'user': None,
            'error': str(e)
        })


@app.route('/api/user/me', methods=['GET'])
def get_user():
    """اطلاعات کاربر جاری"""
    # Demo user data
    user = {
        'id': 1,
        'name': 'کاربر دمو',
        'email': 'demo@odoomaster.com',
        'level': 3,
        'xp': 750,
        'avatar': 'https://ui-avatars.com/api/?name=Demo+User&background=714B67&color=fff'
    }
    
    # Load user licenses
    licenses = [
        {
            'id': 1,
            'plan': 'پلن حرفه‌ای',
            'key': 'DEMO-1234-5678-ABCD',
            'status': 'active',
            'expires_at': (datetime.now() + timedelta(days=28)).isoformat()
        },
        {
            'id': 2,
            'plan': 'پلن رایگان',
            'key': 'FREE-0000-0000-XXXX',
            'status': 'active',
            'expires_at': None
        }
    ]
    
    # Calculate stats
    demos = load_json(DEMOS_FILE, [])
    tickets = load_json(TICKETS_FILE, [])
    
    stats = {
        'active_licenses': len([l for l in licenses if l['status'] == 'active']),
        'total_downloads': 5,
        'open_tickets': len([t for t in tickets if t['status'] == 'open']),
        'active_demos': len(demos)
    }
    
    return jsonify({
        'success': True,
        'user': user,
        'licenses': licenses,
        'stats': stats
    })


@app.route('/api/user/stats', methods=['GET'])
def get_stats():
    """آمار کاربر"""
    demos = load_json(DEMOS_FILE, [])
    tickets = load_json(TICKETS_FILE, [])
    
    stats = {
        'active_licenses': 2,
        'total_downloads': 5,
        'open_tickets': len([t for t in tickets if t['status'] == 'open']),
        'active_demos': len(demos)
    }
    
    return jsonify({
        'success': True,
        'stats': stats
    })


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """بررسی سلامت API"""
    return jsonify({
        'status': 'ok',
        'message': 'OdooMaster API is running',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'app': 'api_server.py',
        'odoo_url': ODOO_URL,
        'routes': {
            'create_tenant': '/api/create-tenant [POST]',
            'list_customers': '/api/list-customers [GET]',
            'health': '/api/health [GET]',
        },
    })


# ============================================
# TENANT PROVISIONING APIs
# ============================================


def check_database_exists_in_odoo(db_name):
    """Check if database actually exists in Odoo server"""
    try:
        url = f"{ODOO_URL}/web/database/list"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {},
            "id": random.randint(1, 1000000)
        }
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        
        if 'result' in result:
            db_list = result['result']
            return db_name in db_list
        
        return False
    except Exception as e:
        print(f"Error checking database existence: {e}")
        return False


def install_odoo_modules(db_name, admin_email, admin_password, modules=None):
    """
    Install Odoo modules using XML-RPC after database creation
    
    Args:
        db_name: Name of the database
        admin_email: Admin email (username)
        admin_password: Admin password
        modules: List of module names to install. Defaults to Persian and UI modules.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if modules is None:
        # Use only modules that are commonly available
        modules = ['web_responsive', 'l10n_ir', 'home_menu_fullscreen', 'base_setup']
    
    try:
        print(f"🔌 Connecting to Odoo XML-RPC: {ODOO_URL}")
        
        # XML-RPC URLs
        common_url = f"{ODOO_URL}/xmlrpc/2/common"
        object_url = f"{ODOO_URL}/xmlrpc/2/object"
        
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(common_url, allow_none=True, verbose=False)
        
        # Authenticate
        print(f"🔐 Authenticating with db={db_name}, user={admin_email}")
        uid = common.authenticate(db_name, admin_email, admin_password, {})
        if not uid:
            return False, "Authentication failed - incorrect credentials"
        
        print(f"✓ Authenticated successfully as user ID: {uid}")
        
        # Connect to object endpoint
        models = xmlrpc.client.ServerProxy(object_url, allow_none=True, verbose=False)
        
        # First, update module list to ensure all modules are visible
        print(f"📦 Updating module list...")
        try:
            models.execute_kw(
                db_name, uid, admin_password,
                'ir.module.module', 'update_list', [[]]
            )
            print(f"✓ Module list updated")
            
            # Wait a bit after update
            import time
            time.sleep(2)
        except Exception as e:
            print(f"⚠ Could not update module list: {str(e)}")
        
        installed_modules = []
        failed_modules = []
        skipped_modules = []
        
        for module_name in modules:
            try:
                print(f"🔍 Searching for module: {module_name}")
                
                # Search for module
                module_ids = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'search',
                    [[('name', '=', module_name)]]
                )
                
                if not module_ids:
                    print(f"⚠ Module '{module_name}' not found in module list")
                    skipped_modules.append(module_name)
                    continue
                
                print(f"✓ Module '{module_name}' found with ID: {module_ids[0]}")
                
                # Get module state
                module_data = models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'read',
                    [module_ids], {'fields': ['name', 'state', 'shortdesc']}
                )
                
                current_state = module_data[0]['state']
                module_title = module_data[0].get('shortdesc', module_name)
                
                print(f"📊 Module '{module_title}' state: {current_state}")
                
                if current_state == 'installed':
                    print(f"✓ Module '{module_name}' already installed")
                    installed_modules.append(module_name)
                    continue
                
                # Install module
                print(f"⚙️ Installing module '{module_name}'...")
                models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'button_immediate_install',
                    [module_ids]
                )
                
                print(f"✅ Module '{module_name}' installed successfully!")
                installed_modules.append(module_name)
                
                # Wait a bit between installations
                time.sleep(2)
                
            except Exception as e:
                error_detail = str(e)
                print(f"❌ Error installing '{module_name}': {error_detail}")
                failed_modules.append(module_name)
        
        # Prepare result message
        success_parts = []
        if installed_modules:
            success_parts.append(f"✓ {', '.join(installed_modules)}")
        if skipped_modules:
            success_parts.append(f"⊗ {', '.join(skipped_modules)}")
        if failed_modules:
            success_parts.append(f"✗ {', '.join(failed_modules)}")
        
        if installed_modules or skipped_modules:
            return True, " | ".join(success_parts)
        else:
            return False, f"هیچ ماژولی نصب نشد: {', '.join(failed_modules)}"
            
    except Exception as e:
        error_msg = f"خطا در نصب ماژول‌ها: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg


@app.route('/api/create-tenant', methods=['POST'])
def create_tenant():
    """API endpoint to create new tenant (customer Odoo instance)"""
    try:
        data = request.get_json(silent=True) or {}

        company_name = data.get('company_name')
        admin_email = data.get('admin_email')
        admin_name = data.get('admin_name', 'Admin')
        phone = data.get('phone', '')
        install_modules = data.get('install_modules', False)

        if not company_name or not admin_email:
            return jsonify({'success': False, 'message': 'نام شرکت و ایمیل الزامی است'}), 400

        # Check if customer already exists in our database
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT database_name, created_at, admin_password, company_name, admin_name FROM customers WHERE admin_email = ?', (admin_email,))
        existing = cursor.fetchone()
        
        if existing:
            db_name, created_at, admin_password, company_name_db, admin_name_db = existing
            
            # Check if the database actually exists in Odoo
            db_exists_in_odoo = check_database_exists_in_odoo(db_name)
            
            if db_exists_in_odoo:
                # Database still exists in Odoo - return existing info including password
                conn.close()
                
                # Create response with cookie
                response_data = {
                    'success': True,
                    'existing': True,
                    'redirect_to_profile': True,
                    'message': 'این ایمیل قبلاً ثبت شده است',
                    'data': {
                        'database_name': db_name,
                        'admin_email': admin_email,
                        'admin_password': admin_password,
                        'company_name': company_name_db,
                        'admin_name': admin_name_db,
                        'created_at': created_at,
                        'login_url': f"{ODOO_URL}/web/login?db={db_name}",
                    }
                }
                
                response = make_response(jsonify(response_data), 200)
                # Set cookie for user session
                response.set_cookie('user_email', admin_email, max_age=30*24*60*60)  # 30 days
                return response
            else:
                # Database was deleted from Odoo - remove old record and create new one
                print(f"Database {db_name} was deleted from Odoo. Removing old record and creating new one.")
                cursor.execute('DELETE FROM customers WHERE admin_email = ?', (admin_email,))
                conn.commit()
        
        conn.close()

        # Generate new database credentials
        db_name = generate_tenant_db_name(company_name)
        admin_password = generate_tenant_password()

        print(f"Creating database {db_name}...")
        success, message = create_odoo_tenant_database(
            db_name=db_name,
            admin_email=admin_email,
            admin_password=admin_password,
            company_name=company_name,
        )

        if not success:
            return jsonify({'success': False, 'message': f'خطا در ساخت دیتابیس: {message}'}), 500

        print(f"✓ Database {db_name} created successfully")
        
        # Install modules if requested
        modules_installed_msg = ""
        if install_modules:
            print(f"⏳ Waiting 15 seconds for database to be fully initialized...")
            import time
            time.sleep(15)  # Wait even longer for database to be fully ready
            
            print(f"📦 Starting module installation for {db_name}...")
            
            # Try to install commonly available modules
            # Include home_menu_fullscreen for beautiful dashboard
            basic_modules = ['l10n_ir', 'web_responsive', 'home_menu_fullscreen', 'base_setup']
            
            modules_success, modules_msg = install_odoo_modules(
                db_name=db_name,
                admin_email=admin_email,
                admin_password=admin_password,
                modules=basic_modules
            )
            
            if modules_success:
                print(f"✅ Modules installed successfully: {modules_msg}")
                modules_installed_msg = f" ✓ ماژول‌های فارسی و UI نصب شد"
            else:
                print(f"⚠️ Module installation had issues: {modules_msg}")
                modules_installed_msg = f" ⚠ نصب ماژول‌ها: {modules_msg}"

        save_customer(company_name, admin_email, admin_name, phone, db_name, admin_password)

        response_data = {
            'success': True,
            'message': 'سرور Odoo شما با موفقیت ساخته شد' + modules_installed_msg,
            'data': {
                'company_name': company_name,
                'database_name': db_name,
                'admin_email': admin_email,
                'admin_name': admin_name,
                'admin_password': admin_password,
                'url': f"{ODOO_URL}/web?db={db_name}",
                'login_url': f"{ODOO_URL}/web/login?db={db_name}",
                'modules_installed': install_modules,
            },
        }
        
        response = make_response(jsonify(response_data), 201)
        # Set cookie for user session
        response.set_cookie('user_email', admin_email, max_age=30*24*60*60)  # 30 days
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500


@app.route('/api/list-customers', methods=['GET'])
def list_customers():
    """List all customers"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers ORDER BY created_at DESC')
        customers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'success': True, 'count': len(customers), 'customers': customers})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete-customer/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """Delete a customer record from database"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        if deleted:
            return jsonify({'success': True, 'message': 'کاربر با موفقیت حذف شد'})
        else:
            return jsonify({'success': False, 'message': 'کاربر یافت نشد'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete-customer-by-email', methods=['POST'])
def delete_customer_by_email():
    """Delete a customer record by email"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': 'ایمیل الزامی است'}), 400
        
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM customers WHERE admin_email = ?', (email,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        if deleted:
            return jsonify({'success': True, 'message': 'رکورد کاربر با موفقیت حذف شد'})
        else:
            return jsonify({'success': False, 'message': 'کاربری با این ایمیل یافت نشد'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Serve static files - only if not API route
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from website folder - excluding API routes"""
    # Don't intercept API routes
    if filename.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    
    from flask import send_from_directory
    try:
        return send_from_directory(app.static_folder, filename)
    except:
        # If file not found, try index.html
        return send_from_directory(app.static_folder, 'index.html')


@app.route('/')
def index():
    """Serve index.html"""
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🚀 OdooMaster API Server")
    print("="*50)
    print(f"\n  🌐 Server running at: http://localhost:5001")
    print(f"  📁 Data directory: {DATA_DIR}")
    print("\n  API Endpoints:")
    print("    • Health:    http://localhost:5001/api/health")
    print("    • Demos:     http://localhost:5001/api/demo/list")
    print("    • Tickets:   http://localhost:5001/api/tickets/list")
    print("    • User:      http://localhost:5001/api/user/me")
    print("\n  Press Ctrl+C to stop the server\n")
    print("="*50 + "\n")
    
    # Respect $PORT for PaaS environments
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
