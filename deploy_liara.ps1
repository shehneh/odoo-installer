# PowerShell Script for Liara Deployment

Write-Host "🚀 Starting Liara Deployment..." -ForegroundColor Green

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js not found. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Check if liara CLI is installed
if (-not (Get-Command liara -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing Liara CLI..." -ForegroundColor Yellow
    npm install -g @liara/cli
}

# Login to Liara
Write-Host "🔐 Please login to Liara..." -ForegroundColor Cyan
liara login

# Create app if not exists
Write-Host "📦 Creating Liara app..." -ForegroundColor Cyan
liara app:create --name odoo-platform --platform docker --region iran 2>$null

# Create database
Write-Host "🗄️ Creating PostgreSQL database..." -ForegroundColor Cyan
liara db:create --name odoo-db --type postgresql --plan g1-2 --region iran 2>$null

# Set environment variables
Write-Host "⚙️ Setting environment variables..." -ForegroundColor Cyan
$DB_PASS = Read-Host "Enter PostgreSQL password" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASS)
$PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
liara env:set POSTGRES_PASSWORD=$PlainPassword --app odoo-platform

# Deploy
Write-Host "🚀 Deploying to Liara..." -ForegroundColor Green
liara deploy --app odoo-platform --port 80

Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host "🌐 Your app will be available at: https://odoo-platform.liara.run" -ForegroundColor Cyan
