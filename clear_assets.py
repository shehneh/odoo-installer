# -*- coding: utf-8 -*-
"""Clear Odoo assets cache to fix white screen issue"""
import xmlrpc.client

url = 'https://odoo-online.liara.run'
db = 'odoo_2_j4ptnd'
username = 'shehneh2@gmail.com'
password = 'bc9TjG6MWzdI'

print(f"Connecting to {db}...")

# Connect
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f'UID: {uid}')

if uid:
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    # Clear assets
    try:
        attachments = models.execute_kw(db, uid, password, 'ir.attachment', 'search', 
            [[['name', 'like', 'web.assets%']]])
        print(f'Found {len(attachments)} asset attachments')
        if attachments:
            models.execute_kw(db, uid, password, 'ir.attachment', 'unlink', [attachments])
            print('Assets cleared!')
        else:
            print('No assets to clear')
    except Exception as e:
        print(f'Error: {e}')
else:
    print('Authentication failed!')
