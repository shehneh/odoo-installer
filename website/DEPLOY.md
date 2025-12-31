# OdooMaster Website

## Deploy to Render.com (Free)

### 1. Push to GitHub
```bash
cd website
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/odoomaster-web.git
git push -u origin main
```

### 2. Deploy on Render
1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Settings:
   - **Name**: odoomaster-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --chdir api server:app --bind 0.0.0.0:$PORT`
5. Click **Create Web Service**

### 3. Your URLs
After deploy, you'll get:
- API: `https://odoomaster-api.onrender.com`
- Website: Same URL serves static files

### 4. Update Offline Installer
Change `ONLINE_WEBSITE` in `web/license.html`:
```javascript
const ONLINE_WEBSITE = 'https://odoomaster-api.onrender.com';
```

---

## Alternative: Railway.app

1. Go to [railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub**
3. Select your repo
4. Railway auto-detects Python and deploys!

---

## Custom Domain (Optional)

After deploying, you can add your own domain:
1. Buy domain (e.g., from Namecheap, GoDaddy, ir-domains)
2. In Render/Railway, add custom domain
3. Update DNS records as instructed
4. Free SSL is automatic!

---

## Environment Variables (if needed)

Set these in Render/Railway dashboard:
- `SECRET_KEY`: Random string for Flask sessions
- `LICENSE_PRIVATE_KEY`: Your license signing key (if using external)
