import requests

print("Testing API...")
r = requests.post('https://odoomaster.liara.run/api/create-tenant', 
                  json={'company_name':'FinalSuccess2026','admin_email':'finalsuccess2026@test.com'}, 
                  timeout=60)

d = r.json()
print(f'Status: {r.status_code}')
print(f'Success: {d.get("success")}')
if d.get("success"):
    print(f'DB: {d.get("data",{}).get("database_name")}')
    print(f'Password: {d.get("data",{}).get("admin_password")}')
    print(f'URL: {d.get("data",{}).get("login_url")}')
else:
    print(f'Error: {d.get("message")}')
