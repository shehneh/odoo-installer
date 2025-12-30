# Liara Deployment Guide - Odoo 19 Platform

## 🚀 مراحل Deploy روی Liara

### 1️⃣ نصب Liara CLI

```bash
npm install -g @liara/cli
```

یا با yarn:
```bash
yarn global add @liara/cli
```

### 2️⃣ لاگین به Liara

```bash
liara login
```

### 3️⃣ ساخت اپلیکیشن‌های مورد نیاز

```bash
# اپ اصلی (Docker)
liara app:create --name odoo-platform --platform docker --region iran

# دیتابیس PostgreSQL
liara db:create --name odoo-db --type postgresql --plan g1-2 --region iran
```

### 4️⃣ تنظیم Environment Variables

```bash
liara env:set DB_HOST=odoo-db DB_USER=root DB_PASS=yourpass --app odoo-platform
```

### 5️⃣ Deploy کردن

```bash
liara deploy --app odoo-platform --port 8069
```

---

## ⚙️ تنظیمات اضافی

### Domain دلخواه
```bash
liara domain:add yourdomain.ir --app odoo-platform
```

### SSL رایگان
SSL خودکار فعال می‌شه بعد از اضافه کردن domain

### Scale کردن
```bash
liara app:scale --app odoo-platform --plan g1-4
```

---

## 📊 Plans پیشنهادی

### شروع (تست):
- **App**: g1-2 (2 CPU, 2GB RAM) - ~150,000 تومان/ماه
- **DB**: g1-2 (2 CPU, 2GB RAM) - ~200,000 تومان/ماه

### تولید (حرفه‌ای):
- **App**: g1-4 (4 CPU, 4GB RAM) - ~300,000 تومان/ماه  
- **DB**: g1-4 (4 CPU, 4GB RAM) - ~400,000 تومان/ماه

---

## 🔍 مانیتورینگ

```bash
# لاگ‌ها
liara logs --app odoo-platform

# وضعیت اپ
liara app:list
```

---

## 🆘 نکات مهم

1. **Disk**: حتماً disk برای `/var/lib/odoo` بسازید
2. **Backup**: روزانه از دیتابیس backup بگیرید
3. **Scale**: با افزایش کاربر، resources رو افزایش بدید
4. **Domain**: از Cloudflare برای CDN استفاده کنید

---

## 📞 پشتیبانی Liara
- 📧 support@liara.ir
- 📖 [مستندات](https://docs.liara.ir)
