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

# Configuration - همیشه از متغیر محیطی استفاده کن (امن‌تر)
ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo-online.liara.run')
ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'OdooMaster2025!')
DB_HOST = os.environ.get('DB_HOST', 'odoo-db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'lu46zbfKF1s8j04thKOUI24b')

# Local SQLite database for customer management
# Use /data for persistent storage on Liara (or /tmp for development)
DATA_DIR = os.environ.get('DATA_DIR', '/data')
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
    """Generate unique database name from company name (English only)"""
    # Only keep ASCII alphanumeric characters
    import re
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name)[:20]
    if not clean_name:
        clean_name = 'tenant'  # Fallback if no English chars
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"odoo_{clean_name.lower()}_{suffix}"

def generate_password(length=12):
    """Generate secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

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
    # Don't intercept API routes
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory('website', path)


# =====================================
# API Endpoints for Module Installation
# =====================================

import xmlrpc.client

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
        
        installed = []
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
                    print(f"✓ Module '{module_name}' already installed")
                    installed.append(module_name)
                    continue
                
                # Install module
                print(f"⚙️ Installing module '{module_name}'...")
                models.execute_kw(
                    db_name, uid, admin_password,
                    'ir.module.module', 'button_immediate_install',
                    [module_ids]
                )
                
                print(f"✅ Module '{module_name}' installed!")
                installed.append(module_name)
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error installing '{module_name}': {e}")
                failed.append(module_name)
        
        details_parts = []
        if installed:
            details_parts.append(f"✓ Installed: {', '.join(installed)}")
        if skipped:
            details_parts.append(f"⊘ Skipped (not found): {', '.join(skipped)}")
        if failed:
            details_parts.append(f"✗ Failed: {', '.join(failed)}")

        details = " | ".join(details_parts) if details_parts else "No changes"

        report = {
            'requested': list(modules) if modules else [],
            'installed': installed,
            'skipped': skipped,
            'failed': failed,
        }

        # Success rules:
        # - If we installed (or it was already installed) at least one module -> success
        # - If everything was skipped because not found -> not successful (user selected modules but none applicable)
        # - If failures happened but some installed -> still success with warnings
        if installed:
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

