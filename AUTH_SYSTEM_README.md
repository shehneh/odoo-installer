# 🔐 سیستم احراز هویت OdooMaster

## ویژگی‌ها

✅ ثبت‌نام کاربران با ایمیل و شماره تلفن
✅ تایید ایمیل با لینک (Email Verification)
✅ تایید شماره تلفن با کد پیامکی (SMS OTP)
✅ محافظت از صفحات (Login Required)
✅ Session Management با Flask
✅ دیتابیس SQLite برای ذخیره کاربران

---

## نصب و راه‌اندازی

### 1. نصب کتابخانه‌های مورد نیاز

```bash
pip install requests
```

### 2. تنظیم متغیرهای محیطی

برای ارسال ایمیل (Gmail SMTP):

```bash
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
```

**نکته**: برای Gmail باید [App Password](https://myaccount.google.com/apppasswords) بسازید.

برای ارسال SMS (Kavenegar):

```bash
export KAVENEGAR_API_KEY="your-api-key"
export KAVENEGAR_TEMPLATE="verify"
```

### 3. راه‌اندازی سرور

```bash
python app.py
```

---

## نحوه استفاده

### 1. ثبت‌نام کاربر جدید

1. بروید به: http://localhost:5000/user-register.html
2. فرم را پر کنید (نام، ایمیل، شماره تلفن، رمز عبور)
3. روی "ثبت‌نام" کلیک کنید
4. یک ایمیل تایید برای شما ارسال می‌شود

### 2. تایید ایمیل

1. ایمیل خود را چک کنید
2. روی لینک تایید کلیک کنید
3. به صفحه تایید حساب منتقل می‌شوید

### 3. تایید شماره تلفن

1. در صفحه تایید حساب، روی "ارسال کد تایید" کلیک کنید
2. کد 6 رقمی را که به شماره شما ارسال شد وارد کنید
3. روی "تایید کد" کلیک کنید

### 4. دسترسی به صفحات محافظت شده

بعد از تایید هر دو (ایمیل + تلفن):
- می‌توانید به صفحه onboarding دسترسی داشته باشید: http://localhost:5000/onboarding.html

---

## API Endpoints

### ثبت‌نام

```http
POST /api/register
Content-Type: application/json

{
    "full_name": "علی احمدی",
    "email": "ali@gmail.com",
    "phone": "09123456789",
    "password": "mypassword123"
}
```

### ورود

```http
POST /api/login
Content-Type: application/json

{
    "email": "ali@gmail.com",
    "password": "mypassword123"
}
```

### ارسال کد SMS

```http
POST /api/send-phone-verification
```

### تایید کد SMS

```http
POST /api/verify-phone
Content-Type: application/json

{
    "code": "123456"
}
```

### دریافت وضعیت کاربر

```http
GET /api/user-status
```

### خروج

```http
POST /api/logout
```

---

## ساختار دیتابیس

### جدول `website_users`

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | شناسه کاربر |
| full_name | TEXT | نام کامل |
| email | TEXT | ایمیل (unique) |
| phone | TEXT | شماره تلفن |
| password_hash | TEXT | هش رمز عبور |
| email_verified | INTEGER | تایید ایمیل (0/1) |
| email_verification_token | TEXT | توکن تایید ایمیل |
| email_verification_expires | TIMESTAMP | انقضای توکن |
| phone_verified | INTEGER | تایید تلفن (0/1) |
| phone_verification_code | TEXT | کد SMS |
| phone_verification_expires | TIMESTAMP | انقضای کد |
| status | TEXT | وضعیت (pending/active) |
| created_at | TIMESTAMP | تاریخ ثبت‌نام |
| last_login | TIMESTAMP | آخرین ورود |

---

## تست بدون ایمیل و SMS

اگر می‌خواهید بدون راه‌اندازی ایمیل یا SMS تست کنید:

1. کاربر را در دیتابیس به صورت دستی تایید کنید:

```sql
UPDATE website_users 
SET email_verified = 1, phone_verified = 1, status = 'active' 
WHERE email = 'test@test.com';
```

2. یا در کد، چک تایید را موقتاً غیرفعال کنید.

---

## نمونه Template پیامک کاوه‌نگار

در پنل کاوه‌نگار، یک template با نام `verify` بسازید:

```
کد تایید OdooMaster: 
%token%
```

---

## نکات امنیتی

🔒 رمزهای عبور با SHA-256 هش می‌شوند
🔒 توکن‌های تایید با secrets.token_urlsafe تولید می‌شوند
🔒 Session با Flask session management
🔒 کدهای SMS حداکثر 5 دقیقه اعتبار دارند
🔒 لینک‌های تایید ایمیل 24 ساعت اعتبار دارند

---

## مشکلات متداول

### ایمیل ارسال نمی‌شود

- Gmail: حتماً [App Password](https://myaccount.google.com/apppasswords) بسازید
- Two-Factor Authentication را فعال کنید

### SMS ارسال نمی‌شود

- API Key کاوه‌نگار را چک کنید
- نام template را درست وارد کنید
- موجودی حساب را بررسی کنید

---

## Deploy در Production

در Liara یا Heroku، متغیرهای محیطی را تنظیم کنید:

```bash
liara env set SMTP_USER=your-email@gmail.com
liara env set SMTP_PASSWORD=your-app-password
liara env set KAVENEGAR_API_KEY=your-key
liara env set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## نمونه کد ساده

```python
# ثبت‌نام
import requests

response = requests.post('http://localhost:5000/api/register', json={
    'full_name': 'علی احمدی',
    'email': 'ali@example.com',
    'phone': '09123456789',
    'password': 'mypassword'
})

print(response.json())
```

---

## مجوزها

MIT License - استفاده آزاد

---

## پشتیبانی

برای سوالات و مشکلات، Issue بسازید.
