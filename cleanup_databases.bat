@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════╗
echo ║  پاکسازی دیتابیس‌های قدیمی Odoo - Liara                  ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

cd /d "D:\business\odoo\Setup odoo19\odoo-docker"

echo [1/4] در حال بررسی تغییرات Git...
git status

echo.
echo [2/4] در حال Commit کردن فایل‌ها...
git add .
git commit -m "Add cleanup script for old databases"

echo.
echo [3/4] در حال Deploy به Liara...
echo این مرحله ممکن است 2-3 دقیقه طول بکشد...
liara deploy --app odoo-online

echo.
echo [4/4] در حال اجرای اسکریپت پاکسازی...
liara shell --app odoo-online --command "python3 cleanup_old_dbs.py"

echo.
echo ════════════════════════════════════════════════════════════
echo ✅ پاکسازی تکمیل شد!
echo ════════════════════════════════════════════════════════════
pause
