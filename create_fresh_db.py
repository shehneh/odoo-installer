#!/usr/bin/env python3
"""
ساخت یک دیتابیس تازه و تمیز با تمام ماژول‌ها
"""
import requests
import time

def create_fresh_database():
    url = "http://localhost:8070"
    db_name = "odoofarsi"  # نام جدید
    
    print("🔨 ساخت دیتابیس تازه: odoofarsi")
    print("=" * 50)
    
    # ساخت دیتابیس
    try:
        response = requests.post(
            f"{url}/web/database/create",
            data={
                'master_pwd': 'admin',
                'name': db_name,
                'login': 'admin',
                'password': 'admin',
                'lang': 'fa_IR',
                'country_code': 'IR',
                'phone': '',
                'demo': 'true',
            },
            timeout=300
        )
        
        if response.status_code == 200:
            print("✅ دیتابیس ساخته شد!")
            print(f"\n🌐 لینک: {url}/web?db={db_name}")
            print("📝 ورود: admin / admin")
            return True
        else:
            print(f"❌ خطا: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

if __name__ == '__main__':
    create_fresh_database()
