# 📘 راهنمای کامل Deploy Odoo روی Liara - گام به گام

## 🎯 هدف
راه‌اندازی سیستم کامل OdooMaster با قابلیت ساخت دموهای آنلاین روی Liara

---

## 📋 پیش‌نیازها

### 1. حساب کاربری
- [x] حساب Liara: https://liara.ir
- [x] دامنه (اختیاری): مثلا odoomaster.com

### 2. ابزارها
```bash
# Liara CLI
npm install -g @liara/cli

# Docker Desktop (برای تست محلی)
# دانلود از: https://www.docker.com/products/docker-desktop
```

---

## 🚀 مرحله 1: تست محلی با Docker

قبل از deploy، روی سیستم خودتون تست کنید.

### 1.1 راه‌اندازی Containers
```bash
cd "d:\business\odoo\Setup odoo19"

# ساخت و اجرای containers
docker-compose up -d

# مشاهده وضعیت
docker-compose ps

# مشاهده لاگ‌ها
docker-compose logs -f
```

### 1.2 دسترسی به دموها
پس از چند دقیقه (اولین بار کمی طول می‌کشه):

- Demo 1: http://localhost:8069
- Demo 2: http://localhost:8070
- Demo 3: http://localhost:8071

**اطلاعات ورود:**
- Email: admin@example.com
- Password: admin

### 1.3 تنظیم اولیه Odoo
1. زبان را به فارسی تغییر دهید
2. موقعیت ایران را انتخاب کنید
3. ماژول‌های مورد نیاز را نصب کنید

### 1.4 متوقف کردن
```bash
docker-compose down

# با حذف دیتا
docker-compose down -v
```

---

## 🚀 مرحله 2: Deploy Backend API روی Liara

### 2.1 ورود به Liara
```bash
liara login
# ایمیل و رمز خود را وارد کنید
```

### 2.2 ایجاد App
```bash
# ایجاد app جدید برای API
liara app:create

# نام: odoomaster-api
# Region: Germany یا Iran (بسته به نیاز)
```

### 2.3 تنظیم Environment Variables
```bash
# وارد پنل Liara شوید و در قسمت Environment Variables:

DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
CORS_ORIGINS=https://odoomaster.com
```

### 2.4 ایجاد Database
```bash
# ایجاد PostgreSQL
liara db:create

# نام: odoomaster-db
# Plan: nano (برای شروع کافیه)
# نسخه: 16
```

### 2.5 اتصال Database به App
```bash
# در پنل Liara:
# App Settings > Network > Link to database > odoomaster-db
```

### 2.6 Deploy
```bash
cd "d:\business\odoo\Setup odoo19"

# Deploy app
liara deploy --app odoomaster-api --platform flask

# منتظر بمانید تا deploy تمام شود
```

### 2.7 بررسی Deploy
```bash
# لاگ‌ها را ببینید
liara logs --app odoomaster-api -f

# وضعیت app
liara app:list
```

---

## 🚀 مرحله 3: Deploy Odoo Instances

### گزینه A: روی VPS جداگانه (پیشنهادی)

Liara برای Odoo چندان مناسب نیست. بهتره Odoo رو روی VPS مجزا بذارید.

#### 3.1 خرید VPS
**پیشنهاد:**
- Hetzner: 5 EUR/month (4 CPU, 8GB RAM)
- Liara Object Storage: برای دیتا

#### 3.2 نصب Docker روی VPS
```bash
# SSH به VPS
ssh root@your-vps-ip

# نصب Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# نصب Docker Compose
apt install docker-compose -y
```

#### 3.3 انتقال فایل‌ها
```bash
# روی سیستم محلی
scp docker-compose.yml root@your-vps-ip:/opt/odoo/
scp Dockerfile.odoo root@your-vps-ip:/opt/odoo/
scp nginx.conf root@your-vps-ip:/opt/odoo/
```

#### 3.4 راه‌اندازی روی VPS
```bash
# روی VPS
cd /opt/odoo

# اجرا
docker-compose up -d

# بررسی
docker-compose ps
```

#### 3.5 تنظیم DNS
در پنل دامنه خود:
```
demo1.odoomaster.com  →  A  →  VPS-IP
demo2.odoomaster.com  →  A  →  VPS-IP
demo3.odoomaster.com  →  A  →  VPS-IP
```

#### 3.6 SSL Certificate (رایگان)
```bash
# نصب Certbot
apt install certbot python3-certbot-nginx -y

# دریافت SSL
certbot --nginx -d demo1.odoomaster.com
certbot --nginx -d demo2.odoomaster.com
certbot --nginx -d demo3.odoomaster.com
```

---

### گزینه B: همه چیز روی Liara (محدودیت دارد)

اگر می‌خواید همه چیز روی Liara باشه:

#### 3.1 ایجاد App برای Odoo
```bash
liara app:create --name odoo-demo1 --platform docker
```

#### 3.2 فایل `liara-docker.json`
```json
{
  "image": "odoo:19",
  "port": 8069,
  "disks": [
    {
      "name": "odoo-data",
      "mountTo": "/var/lib/odoo"
    }
  ]
}
```

#### 3.3 Deploy
```bash
liara deploy --app odoo-demo1 --image odoo:19
```

⚠️ **توجه**: این روش محدودیت‌های زیادی داره و برای production مناسب نیست.

---

## 🚀 مرحله 4: اتصال Backend به Odoo

### 4.1 تنظیم API
در فایل `api_server.py`:

```python
ODOO_INSTANCES = {
    'demo1': 'https://demo1.odoomaster.com',
    'demo2': 'https://demo2.odoomaster.com',
    'demo3': 'https://demo3.odoomaster.com',
}

AVAILABLE_DEMOS = ['demo1', 'demo2', 'demo3']
```

### 4.2 Endpoint جدید برای Assign Demo
وقتی کاربر دمو می‌سازه، یکی از دموهای آزاد رو بهش assign کن.

---

## 🚀 مرحله 5: Deploy Frontend

### 5.1 تنظیم DNS
```
odoomaster.com     →  CNAME  →  odoomaster-api.liara.run
www.odoomaster.com →  CNAME  →  odoomaster-api.liara.run
```

### 5.2 تنظیم SSL
در پنل Liara > App Settings > Domain:
- Add Custom Domain: odoomaster.com
- SSL را فعال کنید (خودکار با Let's Encrypt)

---

## ✅ تست نهایی

### 1. بررسی API
```bash
curl https://odoomaster-api.liara.run/api/health
```

### 2. بررسی دموها
```bash
curl https://demo1.odoomaster.com
```

### 3. تست از داشبورد
1. به https://odoomaster.com بروید
2. دکمه "ساخت دمو" را بزنید
3. بررسی کنید دمو درست ساخته می‌شه

---

## 💰 هزینه نهایی (تخمینی)

### Liara:
- Backend API: 50,000 تومان/ماه
- PostgreSQL: 50,000 تومان/ماه

### VPS (Hetzner):
- VPS 8GB RAM: ~200,000 تومان/ماه (5 EUR)

**جمع کل: ~300,000 تومان/ماه**

برای 100 کاربر با دموی فعال = ~3000 تومان به ازای هر کاربر

---

## 🐛 عیب‌یابی

### مشکل 1: Containers بالا نمیان
```bash
# لاگ‌ها
docker-compose logs

# Restart
docker-compose restart
```

### مشکل 2: Database connection error
```bash
# بررسی PostgreSQL
docker-compose exec db psql -U odoo -l
```

### مشکل 3: Nginx 502
```bash
# بررسی upstream
docker-compose logs nginx
docker-compose logs odoo-demo1
```

---

## 📞 پشتیبانی

- Liara Docs: https://docs.liara.ir
- Odoo Docs: https://www.odoo.com/documentation/19.0
- Docker Docs: https://docs.docker.com

---

**آماده Deploy هستید؟** 🚀

می‌خواید شروع کنیم؟ کدوم قدم رو باید بریم؟
