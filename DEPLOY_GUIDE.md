# 🚀 راهنمای Deploy روی Liara

## 📌 معماری سیستم

```
┌─────────────────────────────────────────────────────┐
│                   Liara Platform                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────┐      ┌────────────────┐        │
│  │  Frontend      │      │  Backend API   │        │
│  │  (Flask)       │◄────►│  (Flask)       │        │
│  │  Port 80/443   │      │  Port 5001     │        │
│  └────────────────┘      └────────────────┘        │
│         │                         │                  │
│         │                         ▼                  │
│         │                ┌────────────────┐         │
│         │                │  PostgreSQL    │         │
│         │                │  Database      │         │
│         │                └────────────────┘         │
│         │                         │                  │
│         │                         ▼                  │
│         │         ┌──────────────────────────┐     │
│         └────────►│  Odoo Demo Instances     │     │
│                   │  (Docker Containers)     │     │
│                   └──────────────────────────┘     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## 🎯 مرحله 1: آماده‌سازی پروژه برای Deploy

### 1.1 ساختار فایل‌ها
```
Setup odoo19/
├── liara.json              # تنظیمات Liara
├── requirements.txt        # پکیج‌های Python
├── api_server.py          # Backend API
├── Dockerfile.odoo        # Docker image برای Odoo (جدید)
├── docker-compose.yml     # مدیریت Containers (جدید)
└── website/               # Frontend files
```

### 1.2 فایل‌های مورد نیاز

#### ✅ `liara.json` (موجود)
فایل فعلی شما آماده است، فقط باید کمی تغییر بدیم.

#### ✅ `requirements.txt` (موجود)
```txt
flask>=2.3.0
flask-cors>=4.0.0
gunicorn>=21.0.0
cryptography>=41.0.0
requests>=2.31.0
psycopg2-binary>=2.9.0
docker>=6.1.0
```

## 🎯 مرحله 2: ساخت Dockerfile برای Odoo

Odoo باید در یک Docker Container اجرا بشه. هر دمو = یک Container جداگانه.

### ایجاد `Dockerfile.odoo`
این فایل template برای ساخت Odoo instances است.

## 🎯 مرحله 3: Backend API با قابلیت Docker Management

Backend API شما باید بتونه:
1. Docker Container جدید برای هر دمو بسازه
2. دیتابیس PostgreSQL جداگانه بسازه
3. Nginx proxy برای routing
4. مدیریت چرخه عمر دمو (create, delete, expire)

## 🎯 مرحله 4: Deploy روی Liara

### 4.1 نصب Liara CLI
```bash
npm install -g @liara/cli
liara login
```

### 4.2 ایجاد App در Liara
```bash
# ایجاد app جدید
liara create

# نام app: odoomaster-api
# platform: flask
```

### 4.3 تنظیمات Environment Variables
```bash
liara env:set LICENSE_PRIVATE_KEY="your-private-key"
liara env:set DATABASE_URL="postgresql://..."
liara env:set DOCKER_HOST="unix:///var/run/docker.sock"
```

### 4.4 ایجاد دیتابیس PostgreSQL
```bash
liara db:create --name odoomaster-db --plan nano --engine postgres
```

### 4.5 Deploy
```bash
liara deploy
```

---

## 🤔 سوالات مهم قبل از Deploy

### آیا می‌خواهید:

**گزینه A: راه‌حل ساده (پیشنهادی برای شروع)**
- API backend روی Liara
- دموها به چند instance از پیش ساخته شده لینک می‌شن
- هر دمو = یک subdomain مجزا (demo1.odoomaster.com)
- **مزیت**: راه‌اندازی سریع، هزینه کمتر
- **معایب**: تعداد محدود دمو، isolation کمتر

**گزینه B: راه‌حل پیشرفته (Production-Ready)**
- API backend روی Liara با Docker support
- هر دمو = یک Container جداگانه
- Auto-scaling و load balancing
- **مزیت**: scalable، امن، حرفه‌ای
- **معایب**: پیچیده‌تر، هزینه بیشتر

**گزینه C: راه‌حل Hybrid**
- Backend API روی Liara
- Odoo instances روی سرور جداگانه (VPS)
- API از طریق Docker API به سرور Odoo متصل می‌شه
- **مزیت**: تعادل بین هزینه و قدرت
- **معایب**: نیاز به مدیریت دو سرور

---

## 💡 پیشنهاد من

برای شروع، **گزینه A** رو پیشنهاد می‌دم:

### 1. Deploy Backend API روی Liara
- همین `api_server.py` که ساختیم
- با یک PostgreSQL database

### 2. دموها Pre-configured
- 3 تا instance Odoo از قبل آماده
- هر کاربر وقتی دمو می‌سازه، یکی از این 3 تا بهش assign می‌شه
- بعد از 14 روز، reset و آماده کاربر بعدی

### 3. بعدا Upgrade کنید
- وقتی کاربر زیاد شد، به گزینه B یا C ارتقا بدید

---

## 📊 هزینه تخمینی روی Liara

### گزینه A (ساده):
- Flask App: **50,000 تومان/ماه** (plan استارتر)
- PostgreSQL: **50,000 تومان/ماه** (plan nano)
- 3 Instance Odoo ثابت: **150,000 تومان/ماه** (3 × 50k)
- **جمع: ~250,000 تومان/ماه**

### گزینه B (پیشرفته):
- Flask App + Docker: **200,000 تومان/ماه** (plan پرو)
- PostgreSQL: **100,000 تومان/ماه** (plan استاندارد)
- Auto-scaling instances: متغیر بر اساس استفاده
- **جمع: 300,000+ تومان/ماه**

---

## ❓ کدوم رو انتخاب می‌کنید؟

1. **گزینه A** - ساده و سریع (پیشنهادی)
2. **گزینه B** - حرفه‌ای و scalable
3. **گزینه C** - ترکیبی (Liara + VPS)

بهم بگید تا کامل پیاده‌سازی کنم! 🚀
