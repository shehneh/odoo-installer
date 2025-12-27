#!/usr/bin/env python3
"""
ZarinPal Payment Gateway Configuration
تنظیمات درگاه پرداخت زرین‌پال

برای استفاده:
1. در پنل زرین‌پال یک درگاه بسازید
2. MERCHANT_ID را با کد مرچنت خود جایگزین کنید
3. CALLBACK_URL را مطابق آدرس سایت خود تنظیم کنید
"""

# ============ تنظیمات زرین‌پال ============

# کد مرچنت (از پنل زرین‌پال بگیرید)
# برای تست از این کد استفاده کنید: "00000000-0000-0000-0000-000000000000"
ZARINPAL_MERCHANT_ID = "00000000-0000-0000-0000-000000000000"

# حالت تست (Sandbox) یا واقعی
# True = حالت تست (بدون پرداخت واقعی)
# False = حالت واقعی (پرداخت واقعی)
ZARINPAL_SANDBOX = True

# آدرس برگشت بعد از پرداخت
# این آدرس باید همان صفحه purchase.html باشد
ZARINPAL_CALLBACK_URL = "http://127.0.0.1:5000/purchase.html"

# توضیحات پرداخت
ZARINPAL_DESCRIPTION = "خرید لایسنس نصب‌کننده OdooMaster"

# ============ قیمت پلن‌ها (تومان) ============
PLANS = {
    "1month": {
        "name": "۱ ماهه",
        "hours": 720,
        "price": 290000,
    },
    "3month": {
        "name": "۳ ماهه", 
        "hours": 2160,
        "price": 690000,
    },
    "1year": {
        "name": "۱ ساله",
        "hours": 8760,
        "price": 1990000,
    },
    "lifetime": {
        "name": "مادام‌العمر",
        "hours": -1,  # نامحدود
        "price": 4990000,
    },
}

# ============ حالت تست (بدون زرین‌پال) ============
# True = پرداخت fake (برای تست قبل از راه‌اندازی زرین‌پال)
# False = پرداخت واقعی از طریق زرین‌پال
FAKE_PAYMENT_MODE = True

# ============ آدرس‌های API زرین‌پال ============
def get_zarinpal_urls():
    """Get ZarinPal API URLs based on sandbox mode."""
    if ZARINPAL_SANDBOX:
        return {
            "request": "https://sandbox.zarinpal.com/pg/v4/payment/request.json",
            "verify": "https://sandbox.zarinpal.com/pg/v4/payment/verify.json",
            "startpay": "https://sandbox.zarinpal.com/pg/StartPay/",
        }
    else:
        return {
            "request": "https://api.zarinpal.com/pg/v4/payment/request.json",
            "verify": "https://api.zarinpal.com/pg/v4/payment/verify.json",
            "startpay": "https://www.zarinpal.com/pg/StartPay/",
        }
