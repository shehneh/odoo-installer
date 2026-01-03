# -*- coding: utf-8 -*-
"""Test direct database creation on Odoo"""
import requests
import time

url = 'https://odoo-online.liara.run/web/database/create'
db_name = f'test_db_{int(time.time())}'
payload = {
    'master_pwd': 'OdooMaster2025!',
    'name': db_name,
    'login': 'testdirect@test.com',
    'password': 'Test123!',
    'lang': 'en_US',  # Use English to be faster
    'country_code': 'US',
    'phone': ''
}

print('Testing direct DB creation...')
print(f'URL: {url}')
print(f'DB Name: {db_name}')

try:
    # First try WITHOUT follow redirects
    print('\n--- Test 1: Without redirects ---')
    r = requests.post(url, data=payload, timeout=300, allow_redirects=False)
    print(f'Status Code: {r.status_code}')
    print(f'Location Header: {r.headers.get("Location", "None")}')
    
    # Now try WITH follow redirects (this actually completes the DB creation)
    print('\n--- Test 2: With redirects (wait...) ---')
    db_name2 = f'test_db2_{int(time.time())}'
    payload2 = payload.copy()
    payload2['name'] = db_name2
    r2 = requests.post(url, data=payload2, timeout=300, allow_redirects=True)
    print(f'Final Status: {r2.status_code}')
    print(f'Final URL: {r2.url}')
    
    # Now check if DB exists
    print('\n--- Checking database list... ---')
    time.sleep(3)
    r3 = requests.post('https://odoo-online.liara.run/web/database/list', 
                       json={'jsonrpc':'2.0','method':'call','params':{},'id':1})
    dbs = r3.json().get('result', [])
    print(f'Databases: {dbs}')
    if db_name2 in dbs:
        print(f'\n*** SUCCESS! Database {db_name2} created! ***')
    else:
        print(f'\n*** FAILED: Database {db_name2} not in list ***')
except Exception as e:
    import traceback
    print(f'Error: {e}')
    traceback.print_exc()
