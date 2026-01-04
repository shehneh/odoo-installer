import sqlite3
import hashlib

conn = sqlite3.connect('/data/customers.db')
cursor = conn.cursor()

# Show all users
cursor.execute('SELECT id, full_name, email, phone, auth_method, email_verified, phone_verified, status FROM website_users')
users = cursor.fetchall()

print('=== Users in Database ===')
for u in users:
    print(f'ID: {u[0]}, Name: {u[1]}, Email: {u[2]}, Phone: {u[3]}, Method: {u[4]}, Email Verified: {u[5]}, Phone Verified: {u[6]}, Status: {u[7]}')

# Check password for test user
cursor.execute('SELECT password_hash FROM website_users WHERE email = ?', ('shehneh.m@gmail.com',))
result = cursor.fetchone()
if result:
    stored_hash = result[0]
    test_password = '123456'
    test_hash = hashlib.sha256(test_password.encode()).hexdigest()
    print(f'\nStored hash: {stored_hash[:20]}...')
    print(f'Test hash:   {test_hash[:20]}...')
    print(f'Match: {stored_hash == test_hash}')

conn.close()
