import sqlite3

CUSTOMERS_DB = 'customers.db'

conn = sqlite3.connect(CUSTOMERS_DB)
cursor = conn.cursor()

print("Creating website_users table...")

# Website users table (برای احراز هویت سایت)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS website_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        password_hash TEXT NOT NULL,
        auth_method TEXT DEFAULT 'email',
        profile_picture TEXT,
        email_verified INTEGER DEFAULT 0,
        email_verification_token TEXT,
        email_verification_expires TIMESTAMP,
        phone_verified INTEGER DEFAULT 0,
        phone_verification_code TEXT,
        phone_verification_expires TIMESTAMP,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

conn.commit()
conn.close()

print("✓ website_users table created successfully!")

# Verify
conn = sqlite3.connect(CUSTOMERS_DB)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='website_users'")
result = c.fetchone()
if result:
    print(f"✓ Verified: {result[0]} table exists")
    
    # Show columns
    c.execute("PRAGMA table_info(website_users)")
    columns = c.fetchall()
    print("\nColumns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
else:
    print("✗ Table not found!")

conn.close()
