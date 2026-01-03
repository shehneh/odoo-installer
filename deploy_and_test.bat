@echo off
echo === Deploying Odoo with correct Master Password ===
cd /d "C:\soft\odoo_140410101600\Setup odoo19\odoo-docker"
echo y | liara deploy --app odoo-online

echo.
echo === Waiting 60 seconds for deployment ===
timeout /t 60

echo.
echo === Testing API ===
python "C:\soft\odoo_140410101600\Setup odoo19\test_final.py"

pause
