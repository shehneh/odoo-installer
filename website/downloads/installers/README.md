# فایل‌های نصبی (Installer Downloads)

این پوشه برای نگهداری فایل‌های نصبی به عنوان **Fallback** است.

## هدف
اگر دانلود از سایت‌های رسمی (python.org, postgresql.org و...) با مشکل مواجه شد،
نصاب به صورت خودکار از این پوشه دانلود می‌کند.

## فایل‌های مورد نیاز

| فایل | سایز تقریبی | منبع رسمی |
|------|-------------|-----------|
| `python-3.11.9-amd64.exe` | 25 MB | python.org |
| `postgresql-16.3-1-windows-x64.exe` | 85 MB | enterprisedb.com |
| `Git-2.45.2-64-bit.exe` | 55 MB | git-scm.com |
| `node-v20.14.0-x64.msi` | 30 MB | nodejs.org |
| `vc_redist.x64.exe` | 25 MB | microsoft.com |
| `wkhtmltox-0.12.6-1.msvc2015-win64.exe` | 35 MB | wkhtmltopdf.org |

## نحوه استفاده

1. فایل‌ها رو از لینک‌های رسمی دانلود کن
2. با همون اسم‌های بالا توی این پوشه بذار
3. هنگام Deploy روی Netlify، این پوشه هم آپلود بشه

## تنظیمات

در فایل `js/installer.js` می‌تونی تنظیم کنی:

```javascript
config: {
    // آدرس پایه برای fallback
    selfHostedBaseUrl: '/downloads/installers',
    
    // اول از سایت رسمی دانلود بشه یا از اینجا؟
    preferOfficial: true
}
```

## نکته مهم

- Netlify محدودیت ۱۰۰ MB برای هر فایل داره
- PostgreSQL (~85MB) ممکنه به مشکل بخوره
- برای فایل‌های بزرگ‌تر از GitHub Releases یا سرویس دیگه استفاده کن
