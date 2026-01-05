import sqlite3

conn = sqlite3.connect('customers.db')
c = conn.cursor()

# List tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("=== Tables in customers.db ===")
for t in tables:
    print(t[0])

# Check website_users
print("\n=== website_users table ===")
try:
    c.execute("SELECT id, full_name, email, auth_method, status FROM website_users")
    rows = c.fetchall()
    if rows:
        for r in rows:
            print(r)
    else:
        print("No users found in website_users table")
except Exception as e:
    print(f"Error: {e}")

conn.close()
