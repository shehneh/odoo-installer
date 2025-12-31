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

# Configuration
ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo-online.liara.run')
ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'admin')
DB_HOST = os.environ.get('DB_HOST', 'odoo-db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'lu46zbfKF1s8j04thKOUI24b')

# Local SQLite database for customer management
CUSTOMERS_DB = 'customers.db'

def init_customers_db():
    """Initialize SQLite database for customer management"""
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
    """Create new Odoo database using web_db API"""
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
            "phone": ""
        },
        "id": random.randint(1, 1000000)
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

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('website', path)

# API Endpoints
@app.route('/api/create-tenant', methods=['POST'])
def create_tenant():
    """API endpoint to create new tenant (customer Odoo instance)"""
    try:
        data = request.json
        
        company_name = data.get('company_name')
        admin_email = data.get('admin_email')
        admin_name = data.get('admin_name', 'Admin')
        phone = data.get('phone', '')
        
        if not company_name or not admin_email:
            return jsonify({'success': False, 'message': 'نام شرکت و ایمیل الزامی است'}), 400
        
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({'status': 'healthy', 'odoo_url': ODOO_URL, 'timestamp': datetime.now().isoformat()})

if __name__ == "__main__":
    init_customers_db()
    
    print(f"\n{'='*60}")
    print(f"  🚀 OdooMaster Multi-Tenant SaaS Platform")
    print(f"{'='*60}")
    print(f"\n  🌐 Flask Server: http://localhost:5000")
    print(f"  🔗 Odoo Server: {ODOO_URL}")
    print(f"\n  📄 Pages:")
    print(f"    • Home:        http://localhost:5000/")
    print(f"    • Register:    http://localhost:5000/register_tenant.html")
    print(f"\n  🔌 API:")
    print(f"    • POST /api/create-tenant")
    print(f"    • GET  /api/list-customers")
    print(f"\n  Press Ctrl+C to stop\n")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

