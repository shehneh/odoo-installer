#!/usr/bin/env python3
"""Check Odoo config by testing different master passwords"""
import requests

passwords_to_test = [
    'OdooMaster2025!',
    'admin',
    'odoo',
    '',
    'master',
    'password'
]

ODOO_URL = 'https://odoo-online.liara.run'

print("Testing master passwords...")
print("=" * 50)

for pwd in passwords_to_test:
    try:
        # Try to list databases with this password using XML-RPC
        import xmlrpc.client
        db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db')
        try:
            # server_version doesn't need password
            version = db.server_version()
            print(f"Odoo version: {version}")
        except:
            pass
            
        # Try duplicate database (will fail but shows if password is correct)
        data = {
            'master_pwd': pwd,
            'name': 'test_pwd_check',
            'login': 'admin@test.com', 
            'password': 'admin123',
            'lang': 'en_US',
            'country_code': 'us'
        }
        
        r = requests.post(f'{ODOO_URL}/web/database/create', data=data, timeout=10)
        
        # Check if we got AccessDenied in response
        if 'AccessDenied' in r.text or 'Access Denied' in r.text:
            print(f"❌ Password '{pwd}' - Access Denied")
        else:
            print(f"✅ Password '{pwd}' - ACCEPTED! (or different error)")
            print(f"   Response preview: {r.text[:200]}")
            
    except Exception as e:
        print(f"⚠️ Password '{pwd}' - Error: {e}")

print("\n" + "=" * 50)
print("Test complete")
