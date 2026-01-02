# -*- coding: utf-8 -*-
"""
OdooMaster Multi-Tenant SaaS Platform
Flask server with auto-provisioning API for creating Odoo instances
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import string
import random
import requests
import json
import os
from pathlib import Path
from datetime import datetime
import sqlite3

app = Flask(__name__, 
            static_folder='website',
            template_folder='website')
CORS(app)

# Configuration - از فایل config.py بخوان، اگر نبود از متغیر محیطی
try:
    from config import ODOO_URL, ODOO_MASTER_PASSWORD, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
except ImportError:
    ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo-online.liara.run')
    ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'admin')
    DB_HOST = os.environ.get('DB_HOST', 'odoo-db')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'lu46zbfKF1s8j04thKOUI24b')

# Local SQLite database for customer management
# Use /tmp for writable storage on Liara (or local path for development)
DATA_DIR = os.environ.get('DATA_DIR', '/tmp')
CUSTOMERS_DB = os.path.join(DATA_DIR, 'customers.db')

def init_customers_db():
    """Initialize SQLite database for customer management"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(CUSTOMERS_DB) if os.path.dirname(CUSTOMERS_DB) else '.', exist_ok=True)
    conn = sqlite3.connect(CUSTOMERS_DB)
    cursor = conn.cursor()
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
            last_login TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_db_name(company_name):
    """Generate unique database name from company name"""
    clean_name = ''.join(c for c in company_name if c.isalnum())[:20]
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"odoo_{clean_name.lower()}_{suffix}"

def generate_password(length=12):
    """Generate secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def create_odoo_database(db_name, admin_email, admin_password, company_name, lang='fa_IR', country='IR'):
    """Create new Odoo database using web_db API (Odoo 18/19 format)"""
    url = f"{ODOO_URL}/web/database/create"
    
    # Odoo 18/19 uses form data, not JSON-RPC
    payload = {
        "master_pwd": ODOO_MASTER_PASSWORD,
        "name": db_name,
        "login": admin_email,
        "password": admin_password,
        "lang": lang,
        "country_code": country,
        "phone": ""
    }
    
    try:
        response = requests.post(url, data=payload, timeout=300, allow_redirects=False)
        
        # Success = redirect to the new database
        if response.status_code in [302, 303]:
            return True, f"Database {db_name} created successfully"
        
        # Check for error in response
        if response.status_code == 200:
            # Check if redirected to login page (success)
            if 'web/login' in response.text or db_name in response.text:
                return True, f"Database {db_name} created successfully"
            return True, f"Database {db_name} created"
        
        return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return False, str(e)

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

def save_customer(company_name, admin_email, admin_name, phone, database_name, admin_password):
    """Save customer information to local database"""
    try:
        conn = sqlite3.connect(CUSTOMERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customers (company_name, admin_email, admin_name, phone, database_name, admin_password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (company_name, admin_email, admin_name, phone, database_name, admin_password))
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
    return send_from_directory('website', 'install.html')

@app.route('/installer')
def installer():
    return send_from_directory('website', 'install.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('website', path)

# API Endpoints
@app.route('/api/create-tenant', methods=['POST'])
def create_tenant():
    """API endpoint to create new tenant (customer Odoo instance)"""
    try:
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
        
        db_name = generate_db_name(company_name)
        admin_password = generate_password()
        
        success, message = create_odoo_database(db_name, admin_email, admin_password, company_name)
        
        if not success:
            return jsonify({'success': False, 'message': f'خطا در ساخت دیتابیس: {message}'}), 500
        
        save_customer(company_name, admin_email, admin_name, phone, db_name, admin_password)
        
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'ok', 
        'message': 'OdooMaster API is running',
        'version': '3.1.0',
        'deploy_test': 'SUCCESS - Liara Deploy Working!',
        'app_file': 'app.py',
        'odoo_url': ODOO_URL, 
        'timestamp': datetime.now().isoformat(),
        'routes': {
            'create_tenant': '/api/create-tenant [POST]',
            'list_customers': '/api/list-customers [GET]',
            'health': '/api/health [GET]'
        }
    })

# Initialize database on module load (for gunicorn in Liara)
init_customers_db()

if __name__ == "__main__":
    # Get port from environment variable (for Liara/Heroku) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    print(f"\n{'='*60}")
    print(f"  🚀 OdooMaster Multi-Tenant SaaS Platform")
    print(f"{'='*60}")
    print(f"\n  🌐 Flask Server: http://localhost:{port}")
    print(f"  🔗 Odoo Server: {ODOO_URL}")
    print(f"\n  📄 Pages:")
    print(f"    • Home:        http://localhost:{port}/")
    print(f"    • Install:     http://localhost:{port}/install")
    print(f"    • Register:    http://localhost:{port}/register_tenant.html")
    print(f"\n  🔌 API:")
    print(f"    • POST /api/create-tenant")
    print(f"    • GET  /api/list-customers")
    print(f"\n  Press Ctrl+C to stop\n")
    print(f"{'='*60}\n")
    
    # Use debug=False in production (Liara)
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)

