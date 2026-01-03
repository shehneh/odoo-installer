# -*- coding: utf-8 -*-
"""Test Odoo connection"""
import requests

r = requests.get('https://odoo-online.liara.run/web/login?db=odoo_2_j4ptnd', timeout=30)
print(f'Status: {r.status_code}')
print(f'Length: {len(r.text)}')
print(f'First 500 chars:\n{r.text[:500]}')
