# 🚀 OdooMaster Multi-Tenant SaaS Platform

سیستم خودکار راه‌اندازی سرور Odoo اختصاصی برای مشتریان

## 📋 ویژگی‌ها

✅ **ساخت خودکار دیتابیس** - هر مشتری یک دیتابیس مجزا
✅ **ایزوله کامل دیتا** - امنیت کامل اطلاعات مشتریان  
✅ **فارسی و آماده استفاده** - ماژول‌های فارسی نصب شده
✅ **پنل مدیریت** - نظارت بر تمام مشتریان
✅ **API کامل** - امکان یکپارچه‌سازی با سیستم‌های دیگر

## 🏗️ معماری

```
[Website Flask]
      ↓
[API Create Tenant]
      ↓
[Odoo Container] → [PostgreSQL]
                    ├── customer1_db
                    ├── customer2_db
                    └── customer3_db
```

## 📦 نصب Local

### 1. نصب Dependencies:

```bash
pip install -r requirements.txt
```

### 2. اجرای سرور:

```bash
python website_server.py
```

### 3. دسترسی:

- 🌐 Website: http://localhost:5000
- 📝 ثبت‌نام مشتری: http://localhost:5000/register_tenant.html
- 🎯 پنل مدیریت: http://localhost:5000/admin_panel.html

## 🚀 Deploy به Liara

### 1. تنظیم Environment Variables:

```bash
ODOO_URL=https://odoo-online.liara.run
ODOO_MASTER_PASSWORD=your_master_password
DB_HOST=odoo-db
DB_PORT=5432
DB_USER=root
DB_PASSWORD=lu46zbfKF1s8j04thKOUI24b
```

### 2. Deploy:

```bash
liara deploy --app odoomaster --port 5000
```

## 🔌 API Documentation

### 1. ساخت مشتری جدید

**POST** `/api/create-tenant`

```json
{
  "company_name": "شرکت نمونه",
  "admin_email": "admin@example.com",
  "admin_name": "محمد رضایی",
  "phone": "09123456789"
}
```

**Response:**

```json
{
  "success": true,
  "message": "سرور Odoo شما با موفقیت ساخته شد",
  "data": {
    "company_name": "شرکت نمونه",
    "database_name": "odoo_company_abc123",
    "admin_email": "admin@example.com",
    "admin_password": "GeneratedPassword123!",
    "url": "https://odoo-online.liara.run/web?db=odoo_company_abc123",
    "login_url": "https://odoo-online.liara.run/web/login?db=odoo_company_abc123"
  }
}
```

### 2. لیست مشتریان

**GET** `/api/list-customers`

```json
{
  "success": true,
  "count": 10,
  "customers": [
    {
      "id": 1,
      "company_name": "شرکت نمونه",
      "admin_email": "admin@example.com",
      "database_name": "odoo_company_abc123",
      "status": "active",
      "plan": "starter",
      "created_at": "2025-12-31 10:30:00"
    }
  ]
}
```

### 3. Health Check

**GET** `/api/health`

```json
{
  "status": "healthy",
  "odoo_url": "https://odoo-online.liara.run",
  "timestamp": "2025-12-31T10:30:00"
}
```

## 💰 مدل کسب‌وکار

### قیمت‌گذاری پیشنهادی:

- **Starter**: 150,000 تومان/ماه (5 کاربر)
- **Professional**: 350,000 تومان/ماه (20 کاربر)  
- **Enterprise**: 650,000 تومان/ماه (نامحدود)

### هزینه‌های شما (100 مشتری):

```
Odoo App (large-g2):     450,000 تومان/ماه
PostgreSQL (medium):     350,000 تومان/ماه
Storage:                 100,000 تومان/ماه
─────────────────────────────────────
جمع:                     900,000 تومان/ماه
```

### درآمد (100 مشتری):

```
100 × 150,000 = 15,000,000 تومان/ماه
سود خالص:     14,100,000 تومان/ماه 🚀
```

## 🔒 امنیت

- ✅ هر مشتری دیتابیس مجزا
- ✅ رمز عبور قوی خودکار
- ✅ SSL/HTTPS برای تمام ارتباطات
- ✅ Isolation کامل دیتا

## 📊 Monitoring

- لاگ‌ها: `liara logs --app odoomaster`
- وضعیت سرور: `/api/health`
- مشتریان: `/admin_panel.html`

## 🆘 پشتیبانی

برای سوالات و مشکلات:
- Email: info@odoomaster.ir
- Telegram: @OdooMasterSupport

## 📝 License

Copyright © 2025 OdooMaster
All rights reserved.
