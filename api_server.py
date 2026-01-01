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

from flask import Flask, request, jsonify, send_from_directory
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

app = Flask(
    __name__,
    static_folder='website',
    template_folder='website',
)
CORS(app)  # Enable CORS for all routes

# ============================================
# Multi-tenant SaaS configuration (Liara)
# ============================================

ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo-online.liara.run')
ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'admin')

# Local SQLite database for customer management
CUSTOMERS_DB = 'customers.db'


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
        },
        "id": random.randint(1, 1000000),
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        result = response.json()

        if 'error' in result:
            error_msg = result.get('error', {}).get('data', {}).get('message', 'Unknown error')
            return False, error_msg

        return True, f"Database {db_name} created successfully"
    except Exception as e:
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

# Site routes (frontend)
@app.route('/', methods=['GET'])
def site_index():
    return send_from_directory('website', 'index.html')


@app.route('/install', methods=['GET'])
def site_install():
    return send_from_directory('website', 'install.html')


@app.route('/installer', methods=['GET'])
def site_installer():
    return send_from_directory('website', 'install.html')


@app.route('/<path:path>', methods=['GET'])
def site_static(path):
    return send_from_directory('website', path)

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

@app.route('/api/tickets/list', methods=['GET'])
def list_tickets():
    """لیست تیکت‌های کاربر"""
    tickets = load_json(TICKETS_FILE, [])
    
    return jsonify({
        'success': True,
        'tickets': tickets,
        'count': len(tickets)
    })


@app.route('/api/tickets/create', methods=['POST'])
def create_ticket():
    """ثبت تیکت جدید"""
    data = request.get_json()
    
    subject = data.get('subject', '')
    category = data.get('category', 'general')
    message = data.get('message', '')
    urgent = data.get('urgent', False)
    
    if not subject or not message:
        return jsonify({
            'success': False,
            'error': 'موضوع و پیام الزامی است'
        }), 400
    
    # Load existing tickets
    tickets = load_json(TICKETS_FILE, [])
    
    # Create new ticket
    ticket_id = len(tickets) + 1234  # Simple ID
    created_at = datetime.now()
    
    ticket = {
        'id': ticket_id,
        'subject': subject,
        'category': category,
        'message': message,
        'urgent': urgent,
        'status': 'open',
        'replies': [],
        'createdAt': created_at.isoformat(),
        'updatedAt': created_at.isoformat()
    }
    
    tickets.append(ticket)
    save_json(TICKETS_FILE, tickets)
    
    return jsonify({
        'success': True,
        'message': 'تیکت با موفقیت ثبت شد',
        'ticket': ticket
    })


@app.route('/api/tickets/<int:ticket_id>/reply', methods=['POST'])
def reply_ticket(ticket_id):
    """پاسخ به تیکت"""
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({
            'success': False,
            'error': 'پیام نمی‌تواند خالی باشد'
        }), 400
    
    tickets = load_json(TICKETS_FILE, [])
    
    # Find ticket
    ticket = next((t for t in tickets if t['id'] == ticket_id), None)
    if not ticket:
        return jsonify({
            'success': False,
            'error': 'تیکت یافت نشد'
        }), 404
    
    # Add reply
    reply = {
        'message': message,
        'author': 'user',
        'createdAt': datetime.now().isoformat()
    }
    
    ticket['replies'].append(reply)
    ticket['updatedAt'] = datetime.now().isoformat()
    
    save_json(TICKETS_FILE, tickets)
    
    return jsonify({
        'success': True,
        'message': 'پاسخ ارسال شد',
        'reply': reply
    })


# ============================================
# USER & STATS APIs
# ============================================

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


@app.route('/api/create-tenant', methods=['POST'])
def create_tenant():
    """API endpoint to create new tenant (customer Odoo instance)"""
    try:
        data = request.get_json(silent=True) or {}

        company_name = data.get('company_name')
        admin_email = data.get('admin_email')
        admin_name = data.get('admin_name', 'Admin')
        phone = data.get('phone', '')

        if not company_name or not admin_email:
            return jsonify({'success': False, 'message': 'نام شرکت و ایمیل الزامی است'}), 400

        db_name = generate_tenant_db_name(company_name)
        admin_password = generate_tenant_password()

        success, message = create_odoo_tenant_database(
            db_name=db_name,
            admin_email=admin_email,
            admin_password=admin_password,
            company_name=company_name,
        )

        if not success:
            return jsonify({'success': False, 'message': f'خطا در ساخت دیتابیس: {message}'}), 500

        save_customer(company_name, admin_email, admin_name, phone, db_name, admin_password)

        return jsonify(
            {
                'success': True,
                'message': 'سرور Odoo شما با موفقیت ساخته شد',
                'data': {
                    'company_name': company_name,
                    'database_name': db_name,
                    'admin_email': admin_email,
                    'admin_password': admin_password,
                    'url': f"{ODOO_URL}/web?db={db_name}",
                    'login_url': f"{ODOO_URL}/web/login?db={db_name}",
                },
            }
        ), 201
    except Exception as e:
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
