#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت ساخت خودکار دیتابیس‌های دمو
"""

import requests
import time
from urllib.parse import urljoin

def create_odoo_database(url, db_name, admin_password='admin', demo_data=True):
    """
    ساخت دیتابیس جدید در Odoo
    """
    print(f"\n📦 ساخت دیتابیس '{db_name}' در {url}...")
    
    try:
        # آدرس ساخت دیتابیس
        create_url = urljoin(url, '/web/database/create')
        
        # داده‌های ساخت دیتابیس
        data = {
            'master_pwd': 'admin',  # رمز master پیش‌فرض Odoo
            'name': db_name,
            'login': 'admin',
            'password': admin_password,
            'lang': 'fa_IR',  # زبان فارسی
            'country_code': 'IR',  # ایران
            'phone': '',
            'demo': 'true' if demo_data else 'false',
        }
        
        # ارسال درخواست
        response = requests.post(
            create_url,
            data=data,
            timeout=300  # 5 دقیقه timeout
        )
        
        if response.status_code == 200:
            print(f"✅ دیتابیس '{db_name}' با موفقیت ساخته شد")
            return True
        else:
            print(f"❌ خطا در ساخت دیتابیس: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False


def check_odoo_ready(url, max_retries=30):
    """
    بررسی آماده بودن Odoo
    """
    print(f"⏳ در انتظار آماده شدن Odoo در {url}...")
    
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/web/database/selector", timeout=5)
            if response.status_code in [200, 303]:
                print(f"✅ Odoo آماده است!")
                return True
        except:
            pass
        
        time.sleep(2)
        print(f"   تلاش {i+1}/{max_retries}...")
    
    print("❌ Odoo آماده نشد")
    return False


def main():
    """تابع اصلی"""
    
    instances = [
        {'url': 'http://localhost:8069', 'db': 'demo1', 'name': 'Demo 1'},
        {'url': 'http://localhost:8070', 'db': 'demo2', 'name': 'Demo 2'},
        {'url': 'http://localhost:8071', 'db': 'demo3', 'name': 'Demo 3'},
    ]
    
    print("=" * 60)
    print("🚀 ساخت دیتابیس‌های دمو برای Odoo")
    print("=" * 60)
    
    for instance in instances:
        print(f"\n\n🎯 {instance['name']}: {instance['url']}")
        print("-" * 60)
        
        # بررسی آماده بودن
        if check_odoo_ready(instance['url']):
            # ساخت دیتابیس
            create_odoo_database(
                url=instance['url'],
                db_name=instance['db'],
                admin_password='admin',
                demo_data=True  # با داده‌های نمونه
            )
        else:
            print(f"⚠️  {instance['name']} آماده نیست")
    
    print("\n\n" + "=" * 60)
    print("✨ فرآیند ساخت دیتابیس‌ها تمام شد!")
    print("\n📝 اطلاعات ورود:")
    print("   Email: admin")
    print("   Password: admin")
    print("=" * 60)


if __name__ == '__main__':
    main()
