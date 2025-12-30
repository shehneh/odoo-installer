#!/bin/bash

echo "🚀 Starting Liara Deployment..."

# Check if liara CLI is installed
if ! command -v liara &> /dev/null; then
    echo "❌ Liara CLI not found. Installing..."
    npm install -g @liara/cli
fi

# Login to Liara
echo "🔐 Please login to Liara..."
liara login

# Create app if not exists
echo "📦 Creating Liara app..."
liara app:create --name odoo-platform --platform docker --region iran || echo "App already exists"

# Create database
echo "🗄️ Creating PostgreSQL database..."
liara db:create --name odoo-db --type postgresql --plan g1-2 --region iran || echo "Database already exists"

# Set environment variables
echo "⚙️ Setting environment variables..."
read -p "Enter PostgreSQL password: " DB_PASS
liara env:set POSTGRES_PASSWORD=$DB_PASS --app odoo-platform

# Deploy
echo "🚀 Deploying to Liara..."
liara deploy --app odoo-platform --port 80

echo "✅ Deployment completed!"
echo "🌐 Your app will be available at: https://odoo-platform.liara.run"
