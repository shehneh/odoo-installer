"""Test the database deletion API"""
import xmlrpc.client
import socket

def set_socket_timeout(timeout):
    """Set global socket timeout"""
    socket.setdefaulttimeout(timeout)

# Configuration
ODOO_URL = 'https://odoo-online.liara.run'
MASTER_PASSWORD = 'OdooMaster2025!'

# Test: List databases first
print("=" * 60)
print("Testing Odoo XML-RPC Database Management")
print("=" * 60)

try:
    set_socket_timeout(30)
    db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db', allow_none=True)
    
    # List databases
    print("\n1. Listing all databases...")
    databases = db.list()
    print(f"   Found {len(databases)} databases:")
    for db_name in databases:
        print(f"   - {db_name}")
    
    if not databases:
        print("\n✅ No databases found - server is clean!")
    else:
        # Test deletion on first database
        test_db = databases[0]
        print(f"\n2. Testing deletion of: {test_db}")
        
        try:
            result = db.drop(MASTER_PASSWORD, test_db)
            print(f"   ✅ Result: {result}")
            
            # List again to confirm
            print("\n3. Listing databases again...")
            databases_after = db.list()
            print(f"   Found {len(databases_after)} databases:")
            for db_name in databases_after:
                print(f"   - {db_name}")
            
            if test_db not in databases_after:
                print(f"\n✅ SUCCESS: {test_db} was deleted successfully!")
            else:
                print(f"\n❌ FAILED: {test_db} still exists!")
                
        except Exception as e:
            print(f"   ❌ Error during deletion: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"❌ Connection error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
