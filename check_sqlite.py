"""Check SQLite database content"""
import sqlite3

CUSTOMERS_DB = 'd:/business/odoo/Setup odoo19/customers.db'

print("=" * 60)
print("Checking SQLite Database")
print("=" * 60)

conn = sqlite3.connect(CUSTOMERS_DB)
cursor = conn.cursor()

# Check customers table
print("\n1. Customers table:")
cursor.execute('SELECT * FROM customers')
customers = cursor.fetchall()

if customers:
    print(f"   Found {len(customers)} records:")
    for row in customers:
        print(f"   - {row}")
else:
    print("   ✅ No customers found - table is empty")

conn.close()
print("\n" + "=" * 60)
