# راهنمای تست پایداری Session

این سند توضیح می‌دهد که چگونه سیستم Session را تست کنید.

## ✅ چه چیزهایی Fix شده است

### 1. **SECRET_KEY ثابت**
```python
app.secret_key = 'OdooMaster-Fixed-Secret-Key-2025-Do-Not-Change!'
```
- قبلاً: SECRET_KEY در هر بار restart تصادفی بود → همه session ها invalid می‌شدند
- حالا: SECRET_KEY ثابت است → session ها پس از restart سرور هم پایدار می‌مانند

### 2. **Session Permanent**
```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
session.permanent = True  # در همه login endpoints
```
- Session ها 7 روز اعتبار دارند
- در 4 جای مختلف اعمال شده:
  1. Login با ایمیل/موبایل و پسورد
  2. Login با OTP (بدون پسورد)
  3. Google OAuth - کاربر موجود
  4. Google OAuth - کاربر جدید

### 3. **Cookie Settings**
```python
app.config['SESSION_COOKIE_SECURE'] = False  # برای HTTP
app.config['SESSION_COOKIE_HTTPONLY'] = True  # امنیت XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # امنیت CSRF
```

## 🧪 نحوه تست

### روش 1: صفحه تست اتوماتیک
1. به `/test-session.html` بروید
2. صفحه هر 5 ثانیه session را چک می‌کند
3. لاگ در پایین صفحه نمایش داده می‌شود
4. اگر session از بین برود، خودکار redirect به login می‌شوید

### روش 2: تست دستی
```javascript
// در Console مرورگر این کد را اجرا کنید:

// چک کردن session
fetch('/api/user-status')
  .then(r => r.json())
  .then(data => console.log('Session:', data));

// باید result.logged_in = true باشد
```

### روش 3: تست با Restart سرور
1. لاگین کنید
2. سرور را restart کنید (`Ctrl+C` و دوباره `python app.py`)
3. صفحه را refresh کنید
4. باید همچنان لاگین باشید ✅

### روش 4: تست با بستن مرورگر
1. لاگین کنید
2. مرورگر را کاملاً ببندید (نه فقط tab)
3. مرورگر را دوباره باز کنید
4. به سایت برگردید
5. باید همچنان لاگین باشید ✅

## 📊 نتایج مورد انتظار

### ✅ حالت نرمال
- Session 7 روز پایدار می‌ماند
- بعد از restart سرور همچنان لاگین هستید
- بعد از بستن مرورگر همچنان لاگین هستید
- در همه صفحات نام کاربر در navigation نمایش داده می‌شود

### ❌ حالت‌های خروج طبیعی
- کلیک روی دکمه "خروج"
- بعد از 7 روز (انقضای طبیعی session)
- پاک کردن دستی Cookie ها

## 🔍 مشاهده Session در مرورگر

### Chrome/Edge
1. `F12` → `Application` tab
2. `Storage` → `Cookies` → `http://localhost:5000`
3. باید cookie با نام `session` وجود داشته باشد
4. `Expires` باید 7 روز بعد باشد

### Firefox  
1. `F12` → `Storage` tab
2. `Cookies` → `http://localhost:5000`
3. باید cookie با نام `session` وجود داشته باشد

## 🐛 Debugging

اگر session از بین می‌رود، این موارد را چک کنید:

1. **SECRET_KEY تغییر نکرده؟**
```bash
# در console سرور باید این خط را ببینید:
# WARNING: Using fixed SECRET_KEY (این خوب است!)
```

2. **session.permanent در login ها هست؟**
```python
# باید در همه login endpoints این خط باشد:
session.permanent = True
```

3. **Cookie ذخیره می‌شود؟**
- مرورگر را در حالت Incognito/Private تست کنید
- تنظیمات مرورگر را چک کنید (Cookie ها فعال باشند)

4. **همه صفحات checkUserStatus() را صدا می‌زنند؟**
```javascript
// باید در همه صفحات این کد باشد:
checkUserStatus();  // در nav-header.html یا global-nav.js
```

## 📝 لاگ های مفید

در console سرور Flask این لاگ ها را مشاهده کنید:

```
[LOGIN] User 1 logged in with email (password)
[LOGIN-OTP] User 1 logged in with phone OTP
[GOOGLE-OAUTH] User 1 logged in with Google OAuth
```

اگر session load می‌شود:
```
127.0.0.1 - - [04/Jan/2026] "GET /api/user-status HTTP/1.1" 200
```

اگر session وجود ندارد:
```
127.0.0.1 - - [04/Jan/2026] "GET /api/user-status HTTP/1.1" 401
```

## ⚙️ تنظیمات پیشرفته

### تغییر مدت زمان session
```python
# در app.py
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30 روز
```

### فعال کردن HTTPS
```python
app.config['SESSION_COOKIE_SECURE'] = True  # فقط برای HTTPS
```

### تغییر SECRET_KEY
```python
# با environment variable
export SECRET_KEY="your-very-secret-and-long-key-here"

# یا مستقیم در app.py
app.secret_key = "your-very-secret-and-long-key-here"
```

⚠️ **هشدار**: اگر SECRET_KEY را تغییر دهید، همه session های فعلی invalid می‌شوند!
