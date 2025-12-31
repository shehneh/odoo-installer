"""
Auto Provisioning API for Multi-tenant Odoo SaaS
Creates new Odoo database for each customer automatically
"""

from flask import Flask, request, jsonify
import psycopg2
import string
import random
import requests
import json

app = Flask(__name__)

# Configuration
ODOO_URL = "https://odoo-online.liara.run"
ODOO_MASTER_PASSWORD = "your_master_password"  # Change this!
DB_HOST = "odoo-db"
DB_PORT = "5432"
DB_USER = "root"
DB_PASSWORD = "lu46zbfKF1s8j04thKOUI24b"

def generate_db_name(company_name):
    """Generate unique database name from company name"""
    # Remove special characters and spaces
    clean_name = ''.join(c for c in company_name if c.isalnum())
    # Add random suffix
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"odoo_{clean_name.lower()}_{suffix}"

def generate_password(length=12):
    """Generate secure random password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def create_database(db_name, admin_email, admin_password, company_name, lang='fa_IR', country='IR'):
    """
    Create new Odoo database using web_db API
    """
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
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        result = response.json()
        
        if 'error' in result:
            return False, result['error']['data']['message']
        
        return True, f"Database {db_name} created successfully"
    except Exception as e:
        return False, str(e)

def install_modules(db_name, admin_password, modules=['web_responsive', 'home_menu_fullscreen']):
    """
    Install additional modules after database creation
    """
    # This would use Odoo XML-RPC API
    # Implementation depends on your needs
    pass

@app.route('/api/create-tenant', methods=['POST'])
def create_tenant():
    """
    API endpoint to create new tenant (customer Odoo instance)
    
    Request body:
    {
        "company_name": "شرکت نمونه",
        "admin_email": "admin@example.com",
        "admin_name": "محمد رضایی",
        "phone": "09123456789"
    }
    """
    try:
        data = request.json
        
        # Validate input
        company_name = data.get('company_name')
        admin_email = data.get('admin_email')
        admin_name = data.get('admin_name', 'Admin')
        phone = data.get('phone', '')
        
        if not company_name or not admin_email:
            return jsonify({
                'success': False,
                'message': 'Company name and admin email are required'
            }), 400
        
        # Generate credentials
        db_name = generate_db_name(company_name)
        admin_password = generate_password()
        
        # Create database
        success, message = create_database(
            db_name=db_name,
            admin_email=admin_email,
            admin_password=admin_password,
            company_name=company_name,
            lang='fa_IR',
            country='IR'
        )
        
        if not success:
            return jsonify({
                'success': False,
                'message': f'Failed to create database: {message}'
            }), 500
        
        # Store customer info in your database (implement this)
        # save_customer_info(company_name, admin_email, db_name, phone)
        
        # Send credentials via email (implement this)
        # send_welcome_email(admin_email, db_name, admin_password)
        
        return jsonify({
            'success': True,
            'message': 'Odoo instance created successfully',
            'data': {
                'company_name': company_name,
                'database_name': db_name,
                'admin_email': admin_email,
                'admin_password': admin_password,  # Send via email in production!
                'url': f"{ODOO_URL}/web?db={db_name}",
                'login_url': f"{ODOO_URL}/web/login?db={db_name}"
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/list-tenants', methods=['GET'])
def list_tenants():
    """
    List all customer databases
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database='postgres'
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT datname, pg_size_pretty(pg_database_size(datname))
            FROM pg_database
            WHERE datname LIKE 'odoo_%'
            AND datname NOT IN ('odoo', 'odoo2', 'odoo18')
            ORDER BY datname
        """)
        
        databases = []
        for row in cursor.fetchall():
            databases.append({
                'database_name': row[0],
                'size': row[1]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(databases),
            'databases': databases
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/delete-tenant', methods=['DELETE'])
def delete_tenant():
    """
    Delete customer database
    
    Request body:
    {
        "database_name": "odoo_company_abc123"
    }
    """
    try:
        data = request.json
        db_name = data.get('database_name')
        
        if not db_name or not db_name.startswith('odoo_'):
            return jsonify({
                'success': False,
                'message': 'Invalid database name'
            }), 400
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Terminate connections
        cursor.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{db_name}'
        """)
        
        # Drop database
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Database {db_name} deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
