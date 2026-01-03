#!/usr/bin/env python3
"""Create database using XML-RPC directly"""
import xmlrpc.client
import time

ODOO_URL = 'https://odoo-online.liara.run'
MASTER_PASSWORD = 'OdooMaster2025!'

db_name = f'xmlrpc_test_{int(time.time())}'
print(f"Creating database: {db_name}")

# Connect to database service
db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db')

# List current databases
print("\nCurrent databases:")
try:
    current_dbs = db.list()
    for d in current_dbs:
        print(f"  - {d}")
except Exception as e:
    print(f"Error listing: {e}")

# Create new database
print(f"\nCreating database '{db_name}'...")
try:
    result = db.create_database(
        MASTER_PASSWORD,  # master password
        db_name,          # database name
        False,            # demo data
        'fa_IR',          # language
        'admin123',       # admin password
        'admin@test.com', # admin login
        'ir',             # country code
        ''                # phone
    )
    print(f"Result: {result}")
except xmlrpc.client.Fault as e:
    print(f"XML-RPC Fault: {e.faultCode} - {e.faultString}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Wait and verify
print("\nWaiting 10 seconds...")
time.sleep(10)

print("\nDatabases after creation:")
try:
    new_dbs = db.list()
    for d in new_dbs:
        marker = " ← NEW!" if d == db_name else ""
        print(f"  - {d}{marker}")
    
    if db_name in new_dbs:
        print(f"\n✅ SUCCESS! Database '{db_name}' created!")
    else:
        print(f"\n❌ FAILED! Database '{db_name}' not found!")
except Exception as e:
    print(f"Error: {e}")
