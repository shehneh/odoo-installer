"""Check customers table schema"""
import sqlite3

CUSTOMERS_DB = 'd:/business/odoo/Setup odoo19/customers.db'

conn = sqlite3.connect(CUSTOMERS_DB)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(customers)")
columns = cursor.fetchall()

print("=" * 60)
print("Customers Table Schema:")
print("=" * 60)
for col in columns:
    print(f"{col[1]:<20} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10} {'PK' if col[5] else ''}")

conn.close()
