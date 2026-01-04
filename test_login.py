#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سیستم لاگین
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def test_email_login():
    """تست لاگین با ایمیل"""
    print("=" * 60)
    print("تست لاگین با ایمیل")
    print("=" * 60)
    
    data = {
        'email': 'shehneh.m@gmail.com',
        'password': '123456',
        'auth_method': 'email'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/login', json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ لاگین با ایمیل موفق!")
                return True
            else:
                print(f"❌ خطا: {result.get('error')}")
                return False
        else:
            print(f"❌ خطای HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

def test_phone_login():
    """تست لاگین با موبایل"""
    print("\n" + "=" * 60)
    print("تست لاگین با موبایل")
    print("=" * 60)
    
    data = {
        'phone': '09961979369',
        'password': '123456',
        'auth_method': 'phone'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/login', json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ لاگین با موبایل موفق!")
                return True
            else:
                print(f"❌ خطا: {result.get('error')}")
                return False
        else:
            print(f"❌ خطای HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

def test_wrong_password():
    """تست لاگین با رمز عبور اشتباه"""
    print("\n" + "=" * 60)
    print("تست لاگین با رمز عبور اشتباه")
    print("=" * 60)
    
    data = {
        'email': 'shehneh.m@gmail.com',
        'password': 'wrong_password',
        'auth_method': 'email'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/login', json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 401:
            print("✅ رمز عبور اشتباه به درستی رد شد")
            return True
        else:
            print(f"❌ انتظار کد 401 بود ولی {response.status_code} دریافت شد")
            return False
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

if __name__ == '__main__':
    print("\n🧪 شروع تست‌های سیستم لاگین\n")
    
    results = []
    results.append(("لاگین با ایمیل", test_email_login()))
    results.append(("لاگین با موبایل", test_phone_login()))
    results.append(("رد رمز عبور اشتباه", test_wrong_password()))
    
    print("\n" + "=" * 60)
    print("خلاصه نتایج تست")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for test_name, result in results:
        status = "✅ موفق" if result else "❌ ناموفق"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nکل: {len(results)} | موفق: {passed} | ناموفق: {failed}")
    print("=" * 60 + "\n")
