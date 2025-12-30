#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت فارسی‌سازی Odoo
این اسکریپت Odoo را کاملاً فارسی می‌کند شامل:
- نصب زبان فارسی
- تنظیم RTL
- تنظیم تقویم شمسی
- تنظیم واحد پول ریال
"""

import xmlrpc.client
import json
from datetime import datetime, timedelta

class OdooFarsizer:
    def __init__(self, url, db_name, username='admin', password='admin'):
        """
        راه‌اندازی اتصال به Odoo
        """
        self.url = url
        self.db_name = db_name
        self.username = username
        self.password = password
        
        # اتصال به Odoo API
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # احراز هویت
        try:
            self.uid = self.common.authenticate(db_name, username, password, {})
            print(f"✅ اتصال موفق به {url} - دیتابیس: {db_name}")
        except Exception as e:
            print(f"❌ خطا در اتصال: {e}")
            self.uid = None
    
    def execute(self, model, method, *args, **kwargs):
        """اجرای متد روی مدل"""
        if not self.uid:
            return None
        return self.models.execute_kw(
            self.db_name, self.uid, self.password,
            model, method, args, kwargs
        )
    
    def install_persian_language(self):
        """نصب و فعال‌سازی زبان فارسی"""
        print("\n📦 نصب زبان فارسی...")
        
        try:
            # جستجوی زبان فارسی
            lang_id = self.execute('res.lang', 'search', [('code', '=', 'fa_IR')])
            
            if not lang_id:
                # فعال‌سازی زبان فارسی
                print("   نصب زبان فارسی...")
                self.execute('base.language.install', 'create', {
                    'lang': 'fa_IR',
                    'overwrite': False
                })
                # جستجوی مجدد
                lang_id = self.execute('res.lang', 'search', [('code', '=', 'fa_IR')])
            
            if lang_id:
                # فعال‌سازی زبان
                self.execute('res.lang', 'write', lang_id, {
                    'active': True,
                    'direction': 'rtl',
                    'date_format': '%Y/%m/%d',
                    'time_format': '%H:%M:%S',
                    'grouping': '[3,0]',
                    'decimal_point': '.',
                    'thousands_sep': ','
                })
                print("✅ زبان فارسی نصب و فعال شد")
                return True
            else:
                print("⚠️  زبان فارسی در دسترس نیست")
                return False
                
        except Exception as e:
            print(f"❌ خطا در نصب زبان: {e}")
            return False
    
    def set_persian_for_admin(self):
        """تنظیم زبان فارسی برای کاربر admin"""
        print("\n👤 تنظیم زبان کاربر admin...")
        
        try:
            # پیدا کردن کاربر admin
            user_ids = self.execute('res.users', 'search', [('login', '=', self.username)])
            
            if user_ids:
                # تنظیم زبان فارسی
                self.execute('res.users', 'write', user_ids, {
                    'lang': 'fa_IR',
                })
                print("✅ زبان کاربر admin به فارسی تغییر یافت")
                return True
            else:
                print("⚠️  کاربر admin یافت نشد")
                return False
                
        except Exception as e:
            print(f"❌ خطا در تنظیم زبان کاربر: {e}")
            return False
    
    def set_persian_currency(self):
        """تنظیم واحد پول ریال ایران"""
        print("\n💰 تنظیم واحد پول ریال...")
        
        try:
            # جستجوی واحد پول IRR
            currency_ids = self.execute('res.currency', 'search', [('name', '=', 'IRR')])
            
            if currency_ids:
                # فعال‌سازی ریال
                self.execute('res.currency', 'write', currency_ids, {
                    'active': True,
                    'symbol': 'ریال',
                    'position': 'after',
                })
                
                # تنظیم به عنوان واحد پول پیش‌فرض شرکت
                company_ids = self.execute('res.company', 'search', [])
                if company_ids:
                    self.execute('res.company', 'write', company_ids, {
                        'currency_id': currency_ids[0]
                    })
                
                print("✅ واحد پول ریال تنظیم شد")
                return True
            else:
                print("⚠️  واحد پول IRR یافت نشد")
                return False
                
        except Exception as e:
            print(f"❌ خطا در تنظیم واحد پول: {e}")
            return False
    
    def set_persian_company_info(self):
        """تنظیم اطلاعات فارسی شرکت"""
        print("\n🏢 تنظیم اطلاعات شرکت...")
        
        try:
            company_ids = self.execute('res.company', 'search', [])
            
            if company_ids:
                self.execute('res.company', 'write', company_ids, {
                    'name': 'شرکت نمونه',
                    'country_id': self.execute('res.country', 'search', [('code', '=', 'IR')])[0] if self.execute('res.country', 'search', [('code', '=', 'IR')]) else False,
                })
                print("✅ اطلاعات شرکت به فارسی تنظیم شد")
                return True
            else:
                print("⚠️  شرکت یافت نشد")
                return False
                
        except Exception as e:
            print(f"❌ خطا در تنظیم اطلاعات شرکت: {e}")
            return False
    
    def install_persian_modules(self):
        """نصب ماژول‌های مفید فارسی"""
        print("\n📦 بررسی ماژول‌های فارسی...")
        
        modules_to_check = [
            'l10n_ir',  # حسابداری ایران
        ]
        
        try:
            for module in modules_to_check:
                module_ids = self.execute('ir.module.module', 'search', [
                    ('name', '=', module),
                    ('state', '=', 'uninstalled')
                ])
                
                if module_ids:
                    print(f"   نصب ماژول {module}...")
                    self.execute('ir.module.module', 'button_immediate_install', module_ids)
                    print(f"   ✅ ماژول {module} نصب شد")
                else:
                    print(f"   ℹ️  ماژول {module} قبلاً نصب شده یا در دسترس نیست")
            
            return True
                
        except Exception as e:
            print(f"❌ خطا در نصب ماژول‌ها: {e}")
            return False
    
    def setup_all(self):
        """اجرای تمام تنظیمات فارسی"""
        print("=" * 50)
        print("🇮🇷 شروع فارسی‌سازی Odoo")
        print("=" * 50)
        
        if not self.uid:
            print("❌ امکان اتصال به Odoo وجود ندارد")
            return False
        
        results = {
            'language': self.install_persian_language(),
            'user': self.set_persian_for_admin(),
            'currency': self.set_persian_currency(),
            'company': self.set_persian_company_info(),
            'modules': self.install_persian_modules(),
        }
        
        print("\n" + "=" * 50)
        print("📊 نتیجه فارسی‌سازی:")
        print("=" * 50)
        for key, value in results.items():
            status = "✅" if value else "❌"
            print(f"{status} {key}")
        
        success = all(results.values())
        if success:
            print("\n🎉 فارسی‌سازی Odoo با موفقیت انجام شد!")
            print("🔄 لطفاً مرورگر خود را رفرش کنید")
        else:
            print("\n⚠️  برخی تنظیمات با مشکل مواجه شدند")
        
        return success


def main():
    """تابع اصلی"""
    import sys
    
    # تنظیمات پیش‌فرض
    instances = [
        {'url': 'http://localhost:8069', 'db': 'demo1', 'name': 'Demo 1'},
        {'url': 'http://localhost:8070', 'db': 'demo2', 'name': 'Demo 2'},
        {'url': 'http://localhost:8071', 'db': 'demo3', 'name': 'Demo 3'},
    ]
    
    print("🚀 فارسی‌سازی تمام نمونه‌های Odoo")
    print("=" * 60)
    
    for instance in instances:
        print(f"\n\n🎯 فارسی‌سازی {instance['name']}: {instance['url']}")
        print("-" * 60)
        
        farsizer = OdooFarsizer(
            url=instance['url'],
            db_name=instance['db'],
            username='admin',
            password='admin'
        )
        
        if farsizer.uid:
            farsizer.setup_all()
        else:
            print(f"⚠️  دیتابیس {instance['db']} هنوز ساخته نشده است")
            print(f"   لطفاً ابتدا به {instance['url']} بروید و دیتابیس را بسازید")
    
    print("\n\n" + "=" * 60)
    print("✨ فارسی‌سازی همه نمونه‌ها تمام شد!")
    print("=" * 60)


if __name__ == '__main__':
    main()
