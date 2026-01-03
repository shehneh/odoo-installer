# -*- coding: utf-8 -*-
import requests

r = requests.post('https://odoo-online.liara.run/web/database/list', 
                  json={'jsonrpc':'2.0','method':'call','params':{},'id':1})
print('Databases:')
for db in r.json().get('result', []):
    print(f'  - {db}')
