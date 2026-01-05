"""Add user_id column to customers table"""
import sqlite3

CUSTOMERS_DB = 'd:/business/odoo/Setup odoo19/customers.db'

print("=" * 60)
print("Adding user_id column to customers table")
print("=" * 60)

try:
    conn = sqlite3.connect(CUSTOMERS_DB)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_id' in columns:
        print("✓ user_id column already exists")
    else:
        # Add user_id column
        cursor.execute("ALTER TABLE customers ADD COLUMN user_id INTEGER")
        conn.commit()
        print("✓ user_id column added successfully")
    
    # Add index for better performance
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_user_id ON customers(user_id)")
        conn.commit()
        print("✓ Index created on user_id column")
    except Exception as e:
        print(f"Index creation (may already exist): {e}")
    
    conn.close()
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
