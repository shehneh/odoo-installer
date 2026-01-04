import sqlite3
import hashlib

conn = sqlite3.connect('/data/customers.db')
cursor = conn.cursor()

# Update password for test user
password = '123456'
password_hash = hashlib.sha256(password.encode()).hexdigest()

cursor.execute('UPDATE website_users SET password_hash = ?, status = ?, email_verified = ?, phone_verified = ? WHERE email = ?', 
               (password_hash, 'active', 1, 1, 'shehneh.m@gmail.com'))
conn.commit()

print(f'Password updated for shehneh.m@gmail.com')
print(f'New hash: {password_hash}')
print(f'Email verified: 1, Phone verified: 1, Status: active')

# Also set for phone number
cursor.execute('UPDATE website_users SET password_hash = ?, status = ?, email_verified = ?, phone_verified = ? WHERE phone = ?', 
               (password_hash, 'active', 1, 1, '09961979369'))
conn.commit()

print(f'Password updated for 09961979369')

conn.close()
