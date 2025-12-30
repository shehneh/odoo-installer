# 🚀 راهنمای کامل آنلاین کردن OdooMaster

## ✅ چیزهایی که الان آماده است:

### 1. سیستم محلی (Local)
- ✅ 3 نمونه Odoo فارسی در حال اجرا (8069, 8070, 8071)
- ✅ PostgreSQL Database
- ✅ Dashboard فارسی با Glass Morphism design
- ✅ API Server برای مدیریت دموها
- ✅ سیستم تیکت پشتیبانی
- ✅ Nginx reverse proxy

### 2. فایل‌های Deploy آماده
- ✅ `docker-compose.yml` - تنظیمات Docker
- ✅ `Dockerfile.odoo` - Image سفارشی Odoo با فونت فارسی
- ✅ `nginx.conf` - تنظیمات Nginx
- ✅ `liara.json` - تنظیمات Liara
- ✅ `requirements.txt` - وابستگی‌های Python

---

## 🌐 روش‌های آنلاین کردن

### گزینه 1: Liara (پیشنهادی برای شروع) 🎯

Liara یک PaaS ایرانی است که استفاده از آن بسیار ساده است.

#### مرحله 1: نصب Liara CLI
```bash
npm install -g @liara/cli
```

#### مرحله 2: لاگین به Liara
```bash
liara login
```

#### مرحله 3: ساخت برنامه
```bash
liara create --app odoomaster-api --platform flask --plan mini
```

#### مرحله 4: Deploy کردن
```bash
liara deploy --app odoomaster-api --port 5001
```

#### مرحله 5: تنظیم متغیرهای محیطی
```bash
liara env:set SECRET_KEY=your-secret-key-here --app odoomaster-api
liara env:set DEBUG=False --app odoomaster-api
```

#### مزایا ✅
- بدون نیاز به تنظیمات پیچیده
- پشتیبانی فارسی
- قیمت مناسب (از 15 هزار تومان)
- دامنه رایگان .liara.run

#### معایب ⚠️
- برای Odoo نیاز به پلن بالاتر دارید
- ممکن است برای ترافیک بالا گران شود

---

### گزینه 2: VPS (قدرتمندترین روش) ⚡

اگر می‌خواهید کنترل کامل داشته باشید، VPS بهترین انتخابه.

#### سرویس‌دهنده‌های پیشنهادی:
- **Hetzner** - ارزان و قدرتمند (5-10 یورو)
- **DigitalOcean** - ساده و مستندات خوب ($6-12)
- **ارائه‌دهندگان ایرانی** - آسانتر برای پرداخت

#### مراحل نصب روی VPS:

##### 1. اتصال به VPS
```bash
ssh root@your-server-ip
```

##### 2. نصب Docker
```bash
curl -fsSL https://get.docker.com | bash
```

##### 3. نصب Docker Compose
```bash
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

##### 4. کپی فایل‌ها
```bash
# روی کامپیوتر خودتان:
scp -r "D:/business/odoo/Setup odoo19" root@your-server-ip:/opt/odoomaster/
```

##### 5. اجرا
```bash
cd /opt/odoomaster
docker-compose up -d
```

##### 6. تنظیم دامنه
در DNS دامنه خود، رکوردهای زیر را اضافه کنید:
```
A     @                your-server-ip
A     www              your-server-ip
A     demo1            your-server-ip
A     demo2            your-server-ip
A     demo3            your-server-ip
```

##### 7. نصب SSL با Let's Encrypt
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

#### مزایا ✅
- کنترل کامل
- قیمت ثابت و مناسب
- مقیاس‌پذیر
- عملکرد عالی

#### معایب ⚠️
- نیاز به دانش فنی بیشتر
- باید خودتان مدیریت کنید

---

### گزینه 3: ngrok (فقط برای تست) 🧪

برای تست سریع بدون deploy:

```bash
ngrok http 8080
```

این یک آدرس موقت می‌دهد مثل: `https://abc123.ngrok.io`

**توجه**: فقط برای تست! برای production مناسب نیست.

---

## 📋 Checklist قبل از Deploy

### امنیت 🔒
- [ ] تغییر پسورد پیش‌فرض admin در Odoo
- [ ] تنظیم `SECRET_KEY` قوی
- [ ] تغییر `master_pwd` در Odoo
- [ ] فعال‌سازی HTTPS/SSL
- [ ] محدود کردن دسترسی به PostgreSQL

### عملکرد ⚡
- [ ] تنظیم limits برای Docker containers
- [ ] فعال‌سازی caching در Nginx
- [ ] تنظیم backup خودکار
- [ ] مانیتورینگ سرور

### داده‌ها 💾
- [ ] ساخت backup از دیتابیس
- [ ] تنظیم volume persistence برای Docker
- [ ] لاگ‌گیری مناسب

---

## 🏗️ معماری پیشنهادی Production

```
Internet
   ↓
Cloudflare (CDN + DDoS Protection)
   ↓
Nginx (Reverse Proxy + SSL)
   ├── Frontend (Dashboard) - Port 8080
   ├── API Server - Port 5001
   └── Odoo Instances
         ├── Demo 1 - Port 8069
         ├── Demo 2 - Port 8070
         └── Demo 3 - Port 8071
   ↓
PostgreSQL Database
```

---

## 💰 برآورد هزینه ماهانه

### راه‌حل اقتصادی (شروع)
- Liara Flask App: 15,000 تومان
- Liara PostgreSQL: 30,000 تومان
- Liara Odoo (mini): 50,000 تومان
- **جمع**: ~95,000 تومان/ماه

### راه‌حل حرفه‌ای
- VPS Hetzner (4GB RAM): €10 (~500,000 تومان)
- Domain (.ir): 50,000 تومان/سال
- **جمع**: ~545,000 تومان/ماه

---

## 🎯 مراحل Deployment (گام به گام)

### فاز 1: تست محلی ✅
- [x] Docker containers راه افتادن
- [x] Odoo فارسی شد
- [x] API به Odoo وصل شد
- [x] Dashboard کار می‌کند

### فاز 2: آماده‌سازی Deploy
```bash
# 1. تنظیم environment variables
cp .env.example .env
nano .env  # ویرایش تنظیمات

# 2. بیلد کردن images
docker-compose build

# 3. تست production mode
docker-compose -f docker-compose.prod.yml up
```

### فاز 3: Deploy روی سرور
```bash
# 1. کپی فایل‌ها
rsync -avz --exclude 'node_modules' --exclude '.venv' \
  "D:/business/odoo/Setup odoo19/" \
  user@server:/opt/odoomaster/

# 2. اجرای روی سرور
ssh user@server
cd /opt/odoomaster
docker-compose up -d

# 3. بررسی logs
docker-compose logs -f
```

### فاز 4: تنظیمات نهایی
- [ ] تست تمام endpoints
- [ ] بررسی SSL
- [ ] تنظیم monitoring
- [ ] ساخت backup اولیه

---

## 🔧 تنظیمات مهم

### nginx.conf
```nginx
# اضافه کردن برای performance
client_max_body_size 100M;
client_body_buffer_size 128k;

# Gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# Cache static files
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### docker-compose.prod.yml
```yaml
version: '3.8'

services:
  odoo:
    restart: always
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=${DB_PASSWORD}
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## 🆘 عیب‌یابی مشکلات رایج

### مشکل: Odoo راه نمی‌افتد
```bash
# بررسی logs
docker-compose logs odoo-demo1

# بررسی PostgreSQL
docker-compose exec db psql -U odoo -l

# Restart کردن
docker-compose restart odoo-demo1
```

### مشکل: Dashboard به API وصل نمی‌شود
```bash
# بررسی API
curl http://localhost:5001/api/health

# بررسی CORS
# در api_server.py:
CORS(app, origins=["https://yourdomain.com"])
```

### مشکل: فونت‌های فارسی نمایش داده نمی‌شوند
```bash
# Rebuild کردن Odoo image
docker-compose build odoo-demo1
docker-compose up -d
```

---

## 📚 منابع مفید

### مستندات
- [Odoo Documentation](https://www.odoo.com/documentation/19.0/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Liara Documentation](https://docs.liara.ir/)

### ابزارهای کمکی
- [SSL Test](https://www.ssllabs.com/ssltest/)
- [Docker Hub](https://hub.docker.com/_/odoo)
- [Let's Encrypt](https://letsencrypt.org/)

---

## 🎉 مراحل بعدی

پس از deploy موفق:

1. **مانیتورینگ**: نصب Uptime Robot یا Grafana
2. **Backup**: تنظیم backup خودکار روزانه
3. **Scaling**: اضافه کردن Odoo instances بیشتر
4. **CDN**: استفاده از Cloudflare برای سرعت بالاتر
5. **Analytics**: اضافه کردن Google Analytics
6. **پرداخت**: اتصال به درگاه پرداخت
7. **SMS**: اتصال به سرویس SMS برای اطلاع‌رسانی

---

## 💬 پشتیبانی

اگر به کمک نیاز دارید:
- GitHub Issues
- تلگرام: @odoomaster_support  
- ایمیل: support@odoomaster.ir

---

**🎯 آماده هستید؟**

الان سیستم شما کاملاً آماده است. فقط یکی از روش‌های بالا رو انتخاب کنید و deploy کنید!

برای شروع سریع، پیشنهاد می‌کنم با **ngrok** شروع کنید تا ببینید همه چیز کار می‌کنه، بعد روی **Liara** یا **VPS** deploy کنید.
