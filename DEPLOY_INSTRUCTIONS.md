# 🚀 دستورالعمل Deploy روی Liara

## ✅ تغییرات انجام شده

### 1. اصلاح `website_server.py`
- ✅ اضافه شدن route های `/install` و `/installer` برای نمایش صفحه نصب
- ✅ پورت از متغیر محیطی `PORT` خوانده می‌شود (سازگار با Liara)
- ✅ حالت debug به صورت خودکار در production خاموش می‌شود

### 2. فایل‌های مورد نیاز برای Deploy
```
Setup odoo19/
├── website_server.py       ✅ (اصلاح شده)
├── Procfile               ✅ (موجود)
├── requirements.txt       ✅ (موجود)
├── liara.json            ✅ (موجود)
└── website/
    └── install.html       ✅ (موجود)
```

---

## 📋 مراحل Deploy روی Liara

### مرحله 1: بررسی فایل‌ها

در پوشه `Setup odoo19` اطمینان حاصل کنید که این فایل‌ها وجود دارند:

**Procfile:**
```
web: gunicorn website_server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**requirements.txt:**
```
flask>=2.3.0
flask-cors>=4.0.0
gunicorn>=21.0.0
cryptography>=41.0.0
requests>=2.31.0
psycopg2-binary>=2.9.0
```

**liara.json:**
```json
{
  "platform": "flask",
  "port": 5000,
  "app": "odoomaster",
  "network": "my-network"
}
```

### مرحله 2: نصب Liara CLI (اگر نصب نکرده‌اید)

```bash
npm install -g @liara/cli
```

### مرحله 3: ورود به Liara

```bash
liara login
```

### مرحله 4: Deploy از پوشه `Setup odoo19`

```bash
cd "c:\soft\odoo_140410101600\Setup odoo19"
liara deploy --app odoomaster --platform flask
```

### مرحله 5: تنظیم متغیرهای محیطی

در کنسول Liara → برنامه odoomaster → تنظیمات → متغیرهای محیطی:

```env
FLASK_ENV=production
PORT=5000
ODOO_URL=https://odoo-online.liara.run
ODOO_MASTER_PASSWORD=admin
DB_HOST=odoo-db
DB_PORT=5432
DB_USER=root
DB_PASSWORD=lu46zbfKF1s8j04thKOUI24b
```

⚠️ **توجه:** مقادیر `ODOO_MASTER_PASSWORD` و `DB_PASSWORD` را با مقادیر واقعی خود جایگزین کنید.

---

## 🔍 بررسی بعد از Deploy

### 1. چک کردن لاگ‌ها

```bash
liara logs --app odoomaster
```

یا از کنسول Liara:
- کنسول → odoomaster → لاگ‌ها

**لاگ موفق باید شامل این خطوط باشد:**
```
============================================================
  🚀 OdooMaster Multi-Tenant SaaS Platform
============================================================

  🌐 Flask Server: http://localhost:5000
  🔗 Odoo Server: https://odoo-online.liara.run

  📄 Pages:
    • Home:        http://localhost:5000/
    • Install:     http://localhost:5000/install
    • Register:    http://localhost:5000/register_tenant.html
```

### 2. تست صفحات

**صفحه اصلی:**
```
https://odoomaster.liara.run/
```

**صفحه نصب (جدید):**
```
https://odoomaster.liara.run/install
https://odoomaster.liara.run/installer
```

**صفحه ثبت‌نام:**
```
https://odoomaster.liara.run/register_tenant.html
```

**Health Check:**
```
https://odoomaster.liara.run/api/health
```

---

## 🐛 رفع مشکلات احتمالی

### مشکل 1: اپ بالا نمی‌آید (503 Error)

**علت:** Gunicorn نتوانسته روی پورت درست listen کند.

**راه‌حل:**
1. چک کنید `Procfile` دقیقاً این محتوا را دارد:
   ```
   web: gunicorn website_server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   ```

2. چک کنید متغیر `PORT` در محیط Liara تنظیم شده (معمولاً Liara خودش تنظیم می‌کند)

### مشکل 2: خطای Import (ModuleNotFoundError)

**راه‌حل:** مطمئن شوید `requirements.txt` شامل تمام dependencies است:
```bash
cat requirements.txt
```

### مشکل 3: صفحه install نمایش داده نمی‌شود (404)

**راه‌حل:** مطمئن شوید:
1. فایل `website/install.html` در کنار `website_server.py` وجود دارد
2. پوشه `website` به همراه تمام فایل‌های HTML در deploy شده

---

## 📊 مانیتورینگ

### چک کردن وضعیت در Liara Console

1. برو به: https://console.liara.ir/apps/odoomaster/overview
2. بررسی کن:
   - ✅ Status: Running (روشن است)
   - ✅ CPU/RAM: در حد معقول
   - ✅ لاگ‌ها: بدون خطای critical

### تست API ها

```bash
# Health check
curl https://odoomaster.liara.run/api/health

# باید برگرداند:
{
  "status": "healthy",
  "odoo_url": "https://odoo-online.liara.run",
  "timestamp": "2026-01-01T..."
}
```

---

## 🎉 پایان

اگر همه چیز درست پیش رفت، صفحه نصب شما در این آدرس در دسترس است:

**🔗 https://odoomaster.liara.run/install**

برای پشتیبانی بیشتر، لاگ‌های Liara را بررسی کنید یا از تیم پشتیبانی Liara کمک بگیرید.
