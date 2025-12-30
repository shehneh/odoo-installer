#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نصب تمام ماژول‌های Odoo برای داشتن داشبورد کامل مثل OdooFarsi/Chitalk
"""

import xmlrpc.client

def install_all_apps(url, db, username='admin', password='admin'):
    """نصب تمام اپلیکیشن‌های اصلی Odoo"""
    
    print(f"\n🔌 اتصال به {url}...")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print(f"❌ خطا در ورود به {db}")
            return False
        
        print(f"✅ اتصال موفق به {db}")
        
        # لیست ماژول‌های اصلی که باعث نمایش آیکون‌های زیبا در داشبورد می‌شن
        modules_to_install = [
            # مالی و حسابداری
            'account',           # حسابداری
            'account_accountant', # حسابداری پیشرفته
            
            # فروش و CRM
            'crm',               # CRM - مدیریت ارتباط با مشتری
            'sale_management',   # مدیریت فروش
            'point_of_sale',     # صندوق فروش (POS)
            
            # خرید و انبار
            'purchase',          # خرید
            'stock',             # انبار
            'mrp',               # تولید
            
            # منابع انسانی
            'hr',                # منابع انسانی
            'hr_attendance',     # حضور و غیاب
            'hr_holidays',       # مرخصی
            'hr_expense',        # هزینه‌ها
            'hr_timesheet',      # تایم‌شیت
            'hr_recruitment',    # استخدام
            
            # پروژه
            'project',           # مدیریت پروژه
            'helpdesk',          # پشتیبانی
            
            # بازاریابی
            'mass_mailing',      # ایمیل مارکتینگ
            'marketing_automation', # اتوماسیون بازاریابی
            'sms',               # پیامک
            
            # وب‌سایت
            'website',           # وب‌سایت
            'website_sale',      # فروشگاه آنلاین
            'website_blog',      # بلاگ
            'website_slides',    # آموزش الکترونیکی (eLearning)
            
            # ابزارها
            'calendar',          # تقویم
            'contacts',          # مخاطبین
            'mail',              # پیام‌ها
            'discuss',           # گفتگو
            'survey',            # نظرسنجی
            'note',              # یادداشت
            'documents',         # مدیریت اسناد
            'sign',              # امضای الکترونیک
            
            # سایر
            'fleet',             # مدیریت خودرو
            'maintenance',       # تعمیرات
            'rental',            # اجاره
            'quality_control',   # کنترل کیفیت
            'barcode',           # بارکد
            'iot',               # اینترنت اشیا
            'voip',              # تلفن VoIP
            'knowledge',         # پایگاه دانش
            
            # تم‌ها
            'web_enterprise',    # Enterprise theme (اگر موجود باشه)
        ]
        
        print(f"\n📦 شروع نصب {len(modules_to_install)} ماژول...")
        print("=" * 60)
        
        installed_count = 0
        skipped_count = 0
        failed_count = 0
        
        for module_name in modules_to_install:
            try:
                # جستجوی ماژول
                module_ids = models.execute_kw(
                    db, uid, password,
                    'ir.module.module', 'search',
                    [[('name', '=', module_name)]]
                )
                
                if not module_ids:
                    print(f"   ⚪ {module_name} - موجود نیست")
                    skipped_count += 1
                    continue
                
                # بررسی وضعیت ماژول
                module_info = models.execute_kw(
                    db, uid, password,
                    'ir.module.module', 'read',
                    [module_ids, ['state', 'shortdesc']]
                )
                
                state = module_info[0]['state']
                shortdesc = module_info[0].get('shortdesc', module_name)
                
                if state == 'installed':
                    print(f"   ✅ {shortdesc} - قبلاً نصب شده")
                    skipped_count += 1
                elif state in ['uninstalled', 'to install']:
                    print(f"   📥 نصب {shortdesc}...")
                    try:
                        models.execute_kw(
                            db, uid, password,
                            'ir.module.module', 'button_immediate_install',
                            [module_ids]
                        )
                        print(f"   ✅ {shortdesc} - نصب شد!")
                        installed_count += 1
                    except Exception as e:
                        print(f"   ⚠️  {shortdesc} - خطا در نصب: {str(e)[:50]}")
                        failed_count += 1
                else:
                    print(f"   ⏭️  {shortdesc} - وضعیت: {state}")
                    skipped_count += 1
                    
            except Exception as e:
                print(f"   ❌ {module_name} - خطا: {str(e)[:50]}")
                failed_count += 1
        
        print("\n" + "=" * 60)
        print(f"📊 نتیجه:")
        print(f"   ✅ نصب شده: {installed_count}")
        print(f"   ⏭️  رد شده: {skipped_count}")
        print(f"   ❌ خطا: {failed_count}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False


def main():
    instances = [
        {'url': 'http://localhost:8070', 'db': 'demo2'},
    ]
    
    print("=" * 60)
    print("🚀 نصب ماژول‌ها برای داشبورد کامل Odoo")
    print("   این کار ممکنه چند دقیقه طول بکشه...")
    print("=" * 60)
    
    for instance in instances:
        install_all_apps(
            url=instance['url'],
            db=instance['db']
        )
    
    print("\n\n🎉 نصب تمام شد!")
    print("🔄 لطفاً مرورگر رو رفرش کنید")
    print(f"🌐 http://localhost:8070/web")


if __name__ == '__main__':
    main()
