#!/usr/bin/env python3
"""Debug API endpoint"""
import requests

# Call debug endpoint
r = requests.get('https://odoomaster.liara.run/debug/config')
print("Debug Config Response:")
print(r.text)
