# 🧹 پاکسازی دیتابیس‌های قدیمی Odoo

Write-Host "📦 در حال دیپلوی اسکریپت پاکسازی..." -ForegroundColor Cyan

Set-Location "D:\business\odoo\Setup odoo19\odoo-docker"
git add .
git commit -m "Add cleanup script"

Write-Host "`n🚀 در حال دیپلوی به Liara..." -ForegroundColor Yellow
liara deploy --app odoo-online --detach

Write-Host "`n⏳ منتظر بمانید تا دیپلوی کامل شود (30 ثانیه)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`n🗑️ در حال اجرای اسکریپت پاکسازی..." -ForegroundColor Green
liara shell --app odoo-online --command "python3 cleanup_old_dbs.py"

Write-Host "`n✅ عملیات پاکسازی تکمیل شد!" -ForegroundColor Green
Write-Host "📊 برای مشاهده وضعیت دیتابیس به پنل Liara مراجعه کنید.`n" -ForegroundColor Cyan
