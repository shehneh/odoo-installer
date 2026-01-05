"""Check current Odoo databases"""
import xmlrpc.client
import socket

def set_socket_timeout(timeout):
    socket.setdefaulttimeout(timeout)

ODOO_URL = 'https://odoo-online.liara.run'

print("=" * 60)
print("Checking Odoo Databases")
print("=" * 60)

try:
    set_socket_timeout(30)
    db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db', allow_none=True)
    
    databases = db.list()
    
    if databases:
        print(f"\n❌ Found {len(databases)} database(s) still in Odoo:")
        for db_name in databases:
            print(f"   - {db_name}")
        print("\n⚠️ These databases were NOT deleted from Odoo!")
    else:
        print("\n✅ No databases found - Odoo server is clean!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
