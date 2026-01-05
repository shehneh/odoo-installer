#!/usr/bin/env python3
"""
Script to cleanup test databases from Odoo server
Keeps only one database: odoo_shehnehm_86sh
"""

import xmlrpc.client

ODOO_URL = 'https://odoo-online.liara.run'
MASTER_PASSWORD = 'OdooMaster2025!'  # Master password of Odoo server

# Database to keep
KEEP_DB = 'odoo_shehnehm_86sh'

def cleanup_databases():
    """Remove all test databases except the one we want to keep"""
    try:
        print(f"🔌 Connecting to Odoo at {ODOO_URL}...")
        
        # Connect to Odoo database manager
        db = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/db', allow_none=True)
        
        # Get list of all databases
        print("📋 Fetching database list...")
        db_list = db.list()
        
        print(f"\n📦 Found {len(db_list)} databases:")
        for db_name in db_list:
            print(f"  - {db_name}")
        
        # Remove all databases except the one we keep
        print(f"\n🗑️  Removing all databases except: {KEEP_DB}")
        
        deleted_count = 0
        for db_name in db_list:
            if db_name == KEEP_DB:
                print(f"  ✅ Keeping: {db_name}")
                continue
            
            try:
                print(f"  🗑️  Deleting: {db_name}...", end=' ')
                db.drop(MASTER_PASSWORD, db_name)
                print("✓ Done")
                deleted_count += 1
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print(f"\n✅ Cleanup complete!")
        print(f"   Deleted: {deleted_count} databases")
        print(f"   Kept: {KEEP_DB}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("  Odoo Database Cleanup Script")
    print("="*60)
    print()
    
    confirm = input(f"⚠️  This will DELETE all databases except '{KEEP_DB}'.\n   Are you sure? (yes/no): ")
    
    if confirm.lower() == 'yes':
        cleanup_databases()
    else:
        print("❌ Cancelled.")
