"""Create plans table in database"""
import sqlite3

CUSTOMERS_DB = 'd:/business/odoo/Setup odoo19/customers.db'

print("=" * 60)
print("Creating plans table")
print("=" * 60)

try:
    conn = sqlite3.connect(CUSTOMERS_DB)
    cursor = conn.cursor()
    
    # Create plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT UNIQUE NOT NULL,
            name_fa TEXT NOT NULL,
            name_en TEXT NOT NULL,
            price INTEGER NOT NULL,
            duration_months INTEGER NOT NULL,
            duration_display_fa TEXT,
            duration_display_en TEXT,
            discount_percent INTEGER DEFAULT 0,
            features TEXT,
            is_popular INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    print("✓ Plans table created successfully")
    
    # Check if table is empty and insert default plans
    cursor.execute('SELECT COUNT(*) FROM plans')
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("\nInserting default plans...")
        default_plans = [
            ('monthly', 'ماهانه', 'Monthly', 500000, 1, '۱ ماه', '1 Month', 0, 
             'پشتیبانی ۲۴/۷|به‌روزرسانی رایگان|فضای ذخیره‌سازی نامحدود|تعداد کاربران نامحدود', 0, 1, 3),
            ('quarterly', 'سه ماهه', 'Quarterly', 1350000, 3, '۳ ماه', '3 Months', 10,
             'پشتیبانی ۲۴/۷ اختصاصی|به‌روزرسانی رایگان|فضای ذخیره‌سازی نامحدود|تعداد کاربران نامحدود|پشتیبان‌گیری خودکار', 1, 1, 2),
            ('yearly', 'سالانه', 'Yearly', 4800000, 12, '۱۲ ماه', '12 Months', 20,
             'پشتیبانی ۲۴/۷ VIP|به‌روزرسانی رایگان|فضای ذخیره‌سازی نامحدود|تعداد کاربران نامحدود|پشتیبان‌گیری خودکار|مشاوره رایگان', 0, 1, 1)
        ]
        
        cursor.executemany('''
            INSERT INTO plans (plan_id, name_fa, name_en, price, duration_months, duration_display_fa, 
                             duration_display_en, discount_percent, features, is_popular, is_active, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_plans)
        
        conn.commit()
        print(f"✓ Inserted {len(default_plans)} default plans")
    else:
        print(f"\n✓ Plans table already contains {count} plan(s)")
    
    conn.close()
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
