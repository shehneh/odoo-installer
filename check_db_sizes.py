#!/usr/bin/env python3
import psycopg2
import os

# اتصال به دیتابیس
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'odoo-db'),
    port=os.getenv('DB_PORT', '5432'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', 'lu46zbfKF1s8j04thKOUI24b'),
    dbname='postgres'
)

cur = conn.cursor()

# لیست دیتابیس‌ها با حجم
cur.execute("""
    SELECT 
        datname as database_name,
        pg_size_pretty(pg_database_size(datname)) as size,
        pg_database_size(datname) as size_bytes
    FROM pg_database
    WHERE datname LIKE 'odoo%' OR datname LIKE '%odoo%'
    ORDER BY pg_database_size(datname) DESC;
""")

print("\n📊 حجم دیتابیس‌های Odoo:\n")
print("-" * 60)
total_bytes = 0
for row in cur.fetchall():
    print(f"{row[0]:20s} | {row[1]:>15s}")
    total_bytes += row[2]

print("-" * 60)
print(f"{'جمع کل':20s} | {total_bytes / (1024*1024*1024):.2f} GB")
print()

cur.close()
conn.close()
