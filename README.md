# ابزار نصب آفلاین Odoo 19

این ابزار برای نصب آفلاین Odoo و وابستگی‌های آن (Python، PostgreSQL، wkhtmltopdf) طراحی شده است.

## ویژگی‌ها

✅ دانلود خودکار Python 3.11.5، PostgreSQL 16، و wkhtmltopdf  
✅ ذخیره‌سازی بسته‌ها در پوشه آفلاین برای استفاده بدون اینترنت  
✅ بررسی SHA256 برای فایل‌های دانلود شده (در صورت وجود)  
✅ لاگ دقیق برای ردیابی عملیات  
✅ پرامپت قبل از نصب (یا نصب خودکار با سوییچ `-AutoRun`)  
✅ دانلود wheelhouse از requirements.txt برای نصب آفلاین pip  

## نیازمندی‌ها

- Windows 10/11
- PowerShell 5.1 یا بالاتر
- دسترسی Administrator برای نصب نرم‌افزارها
- اتصال اینترنت برای دانلود اولیه (اختیاری)

## استفاده

### 1. دانلود بسته‌ها (با اینترنت)

```powershell
# اجرا به‌صورت معمولی - پرامپت قبل از نصب
powershell -ExecutionPolicy Bypass -File .\auto_fetch_and_setup.ps1

# اجرا با نصب خودکار بدون پرسش
powershell -ExecutionPolicy Bypass -File .\auto_fetch_and_setup.ps1 -AutoRun

# تعیین مسیر پایه سفارشی
powershell -ExecutionPolicy Bypass -File .\auto_fetch_and_setup.ps1 -BasePath "D:\MyOdooSetup"
```

### 2. نصب آفلاین (بدون اینترنت)

فایل‌های دانلود شده را به سیستم هدف منتقل کرده و اسکریپت را اجرا کنید:

```powershell
powershell -ExecutionPolicy Bypass -File .\auto_fetch_and_setup.ps1
```

## ساختار پوشه

```
Setup odoo19/
├── auto_fetch_and_setup.ps1    # اسکریپت اصلی
├── fetch_setup.log              # فایل لاگ
├── README.md                    # این فایل
└── offline/
    ├── python/
    │   └── python-3.11.5-amd64.exe
    ├── postgresql/
    │   └── postgresql-16.0-1-windows-x64.exe
    ├── wkhtmltopdf/
    │   └── wkhtmltox-0.12.6.1-2.msvc2015-win64.exe
    └── wheels/
        └── [Python packages]
```

## پارامترهای نصب

### Python
- نصب برای تمام کاربران (InstallAllUsers=1)
- اضافه کردن به PATH (PrependPath=1)
- نصب خاموش (quiet install)

### PostgreSQL
- نصب بدون دخالت کاربر (unattended mode)
- رمز عبور پیش‌فرض superuser: `odoo`
- ⚠️ **توصیه**: رمز عبور را بعد از نصب تغییر دهید

### wkhtmltopdf
- نصب خاموش (quiet install)

## نکات مهم

1. **دسترسی Administrator**: برای نصب نرم‌افزارها نیاز است
2. **Execution Policy**: از `-ExecutionPolicy Bypass` استفاده کنید
3. **requirements.txt**: برای دانلود Python packages، فایل را در `offline/requirements.txt` قرار دهید
4. **Checksum**: اگر فایل `.sha256` در کنار فایل نصبی باشد، خودکار بررسی می‌شود

## عیب‌یابی

### خطای Execution Policy

```powershell
# راه‌حل موقت
powershell -ExecutionPolicy Bypass -File .\auto_fetch_and_setup.ps1

# یا تغییر دائمی (نیاز به Admin)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### خطای دانلود

اگر دانلود ناموفق بود:
1. فایل‌های نصبی را دستی دانلود و در پوشه‌های مربوطه قرار دهید
2. اسکریپت خودکار فایل‌های موجود را تشخیص می‌دهد

### بررسی لاگ

```powershell
Get-Content 'C:\Program Files\Setup odoo19\fetch_setup.log' -Tail 50
```

## مراحل پس‌نصب (ایجاد نقش PostgreSQL و دیتابیس برای Odoo)

در بسیاری از نصب‌ها لازم است که نقش (role) مخصوص Odoo در PostgreSQL ساخته شود و به آن اجازهٔ ایجاد دیتابیس داده شود. برای ثبت این مرحله در پروژه یک اسکریپت کمکی اضافه شده است:

- فایل: `create_postgres_role.ps1`
- عملکرد: خواندن `db_user` و `db_password` از `C:\Program Files\odoo19\config\odoo.conf` (در صورت موجود نبودن، از شما می‌پرسد)، سپس با استفاده از `psql` و رمز کاربر `postgres` نقش را می‌سازد و در صورت نیاز دیتابیس نمونهٔ تست را ایجاد می‌کند.

نمونهٔ اجرای دستی (پس از دانلود یا نصب PostgreSQL و دانستن رمز سوپروزر `postgres`):

```powershell
# اجرا با پرامپت رمز سوپر یوزر
powershell -ExecutionPolicy Bypass -File .\create_postgres_role.ps1
```

اسکریپت محیطی امن فراهم می‌کند تا این مراحل را برای سیستم‌های بعدی تکرارپذیر کند و لاگ کوتاهی از اقدامات در `fetch_setup.log` ثبت می‌کند.

## سفارشی‌سازی

برای تغییر نسخه‌ها، URL‌ها را در اسکریپت ویرایش کنید:

```powershell
$urls = @{
    python = 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe'
    postgresql = 'https://get.enterprisedb.com/postgresql/postgresql-17.0-1-windows-x64.exe'
    wkhtmltopdf = '...'
}
```

## لایسنس

این ابزار برای استفاده داخلی و نصب Odoo طراحی شده است.

## پشتیبانی

برای مشکلات یا سوالات، لاگ فایل (`fetch_setup.log`) را بررسی کنید.
