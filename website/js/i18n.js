/**
 * Internationalization (i18n) System for OdooMaster Website
 * Supports Persian (fa) and English (en)
 */

const I18N = {
    // Default language
    defaultLang: 'fa',
    currentLang: 'fa',
    
    // Available languages
    languages: {
        fa: { name: 'فارسی', dir: 'rtl', flag: '🇮🇷' },
        en: { name: 'English', dir: 'ltr', flag: '🇬🇧' }
    },
    
    // Translations dictionary
    translations: {
        // Navigation
        'nav.features': { fa: 'ویژگی‌ها', en: 'Features' },
        'nav.pricing': { fa: 'قیمت‌گذاری', en: 'Pricing' },
        'nav.demo': { fa: 'دمو', en: 'Demo' },
        'nav.support': { fa: 'پشتیبانی', en: 'Support' },
        'nav.login': { fa: 'ورود', en: 'Login' },
        'nav.register': { fa: 'شروع رایگان', en: 'Get Started' },
        'nav.dashboard': { fa: 'داشبورد', en: 'Dashboard' },
        'nav.licenses': { fa: 'لایسنس‌ها', en: 'Licenses' },
        'nav.downloads': { fa: 'دانلود', en: 'Downloads' },
        'nav.logout': { fa: 'خروج', en: 'Logout' },
        
        // Hero Section
        'hero.badge': { fa: 'نسخه ۲.۰ منتشر شد!', en: 'Version 2.0 Released!' },
        'hero.title.1': { fa: 'قدرت', en: 'The Power of' },
        'hero.title.2': { fa: 'Odoo', en: 'Odoo' },
        'hero.title.3': { fa: 'در دستان شما', en: 'In Your Hands' },
        'hero.desc': { 
            fa: 'با پلتفرم هوشمند OdooMaster، سیستم ERP قدرتمند خود را در کمتر از ۵ دقیقه راه‌اندازی کنید. بدون پیچیدگی، بدون نیاز به دانش فنی.',
            en: 'With OdooMaster smart platform, set up your powerful ERP system in less than 5 minutes. No complexity, no technical knowledge required.'
        },
        'hero.btn.demo': { fa: 'مشاهده دمو نصاب', en: 'View Installer Demo' },
        'hero.btn.buy': { fa: 'خرید لایسنس', en: 'Buy License' },
        'hero.stat.users': { fa: 'کاربر فعال', en: 'Active Users' },
        'hero.stat.installs': { fa: 'نصب موفق', en: 'Successful Installs' },
        'hero.stat.rating': { fa: 'امتیاز کاربران', en: 'User Rating' },
        'hero.scroll': { fa: 'اسکرول کنید', en: 'Scroll Down' },
        
        // Features Section
        'features.badge': { fa: 'ویژگی‌ها', en: 'Features' },
        'features.title': { fa: 'چرا', en: 'Why' },
        'features.title.brand': { fa: 'OdooMaster', en: 'OdooMaster' },
        'features.title.end': { fa: '؟', en: '?' },
        'features.desc': { fa: 'ابزارهای قدرتمندی که کسب‌وکار شما را متحول می‌کنند', en: 'Powerful tools that transform your business' },
        'features.more': { fa: 'بیشتر بدانید', en: 'Learn More' },
        
        'feature.fast.title': { fa: 'نصب برق‌آسا', en: 'Lightning Fast Install' },
        'feature.fast.desc': { fa: 'در کمتر از ۵ دقیقه Odoo را روی سیستم خود نصب کنید.', en: 'Install Odoo on your system in less than 5 minutes.' },
        'feature.online.title': { fa: 'نصب آنلاین هوشمند', en: 'Smart Online Install' },
        'feature.online.desc': { fa: 'دانلود مستقیم از منابع رسمی، بدون نیاز به فایل‌های حجیم.', en: 'Direct download from official sources, no bulky files needed.' },
        'feature.security.title': { fa: 'امنیت بالا', en: 'High Security' },
        'feature.security.desc': { fa: 'فایل‌ها از منابع رسمی با امضای دیجیتال.', en: 'Files from official sources with digital signatures.' },
        'feature.support.title': { fa: 'پشتیبانی ۲۴/۷', en: '24/7 Support' },
        'feature.support.desc': { fa: 'تیم پشتیبانی همیشه در کنار شماست.', en: 'Support team is always by your side.' },
        'feature.allinone.title': { fa: 'همه چیز در یکجا', en: 'All-in-One' },
        'feature.allinone.desc': { fa: 'Python, PostgreSQL و تمام وابستگی‌ها.', en: 'Python, PostgreSQL and all dependencies.' },
        'feature.update.title': { fa: 'آپدیت خودکار', en: 'Auto Update' },
        'feature.update.desc': { fa: 'همیشه به‌روز با آپدیت‌های خودکار.', en: 'Always up-to-date with automatic updates.' },
        
        // Pricing Section
        'pricing.badge': { fa: 'قیمت‌گذاری', en: 'Pricing' },
        'pricing.title': { fa: 'پلن مناسب', en: 'Choose Your' },
        'pricing.title.end': { fa: 'خود را انتخاب کنید', en: 'Perfect Plan' },
        'pricing.popular': { fa: 'پرطرفدار', en: 'Popular' },
        'pricing.currency': { fa: 'تومان', en: 'USD' },
        'pricing.buy': { fa: 'خرید', en: 'Buy Now' },
        'pricing.start': { fa: 'شروع رایگان', en: 'Start Free' },
        
        'plan.free': { fa: 'رایگان', en: 'Free' },
        'plan.pro': { fa: 'حرفه‌ای', en: 'Professional' },
        'plan.enterprise': { fa: 'سازمانی', en: 'Enterprise' },
        
        'plan.free.price': { fa: '۰', en: '0' },
        'plan.pro.price': { fa: '۴۹۰,۰۰۰', en: '49' },
        'plan.enterprise.price': { fa: '۱,۴۹۰,۰۰۰', en: '149' },
        
        'plan.feature.basic': { fa: 'نصاب پایه', en: 'Basic Installer' },
        'plan.feature.community': { fa: 'ماژول‌های Community', en: 'Community Modules' },
        'plan.feature.nosupport': { fa: 'پشتیبانی', en: 'Support' },
        'plan.feature.full': { fa: 'نصاب کامل', en: 'Full Installer' },
        'plan.feature.support3': { fa: 'پشتیبانی ۳ ماهه', en: '3 Months Support' },
        'plan.feature.video': { fa: 'آموزش ویدیویی', en: 'Video Training' },
        'plan.feature.all': { fa: 'همه امکانات', en: 'All Features' },
        'plan.feature.support12': { fa: 'پشتیبانی ۱ ساله', en: '1 Year Support' },
        'plan.feature.remote': { fa: 'نصب از راه دور', en: 'Remote Installation' },
        
        // CTA Section
        'cta.title': { fa: 'آماده نصب Odoo هستید؟', en: 'Ready to Install Odoo?' },
        'cta.desc': { fa: 'ابتدا دمو را ببینید، سپس لایسنس بخرید و Odoo را در چند دقیقه نصب کنید', en: 'First watch the demo, then buy a license and install Odoo in minutes' },
        'cta.btn.demo': { fa: 'مشاهده دمو', en: 'View Demo' },
        'cta.btn.buy': { fa: 'خرید لایسنس', en: 'Buy License' },
        
        // Footer
        'footer.desc': { fa: 'پلتفرم هوشمند نصب Odoo', en: 'Smart Odoo Installation Platform' },
        'footer.about': { fa: 'درباره ما', en: 'About Us' },
        'footer.contact': { fa: 'تماس', en: 'Contact' },
        'footer.support': { fa: 'پشتیبانی', en: 'Support' },
        'footer.blog': { fa: 'بلاگ', en: 'Blog' },
        'footer.copyright': { fa: '© ۱۴۰۴ OdooMaster. تمامی حقوق محفوظ است.', en: '© 2025 OdooMaster. All rights reserved.' },
        
        // Login Page
        'login.title': { fa: 'ورود به حساب کاربری', en: 'Login to Your Account' },
        'login.welcome': { fa: 'خوش برگشتید!', en: 'Welcome Back!' },
        'login.subtitle': { fa: 'وارد حساب کاربری خود شوید', en: 'Sign in to your account' },
        'login.email': { fa: 'ایمیل یا موبایل', en: 'Email or Mobile' },
        'login.email.placeholder': { fa: 'example@email.com', en: 'example@email.com' },
        'login.password': { fa: 'رمز عبور', en: 'Password' },
        'login.password.placeholder': { fa: 'رمز عبور خود را وارد کنید', en: 'Enter your password' },
        'login.remember': { fa: 'مرا به خاطر بسپار', en: 'Remember me' },
        'login.or': { fa: 'یا', en: 'or' },
        'login.google': { fa: 'ورود با گوگل', en: 'Sign in with Google' },
        'login.forgot': { fa: 'فراموشی رمز؟', en: 'Forgot password?' },
        'login.submit': { fa: 'ورود', en: 'Login' },
        'login.noAccount': { fa: 'حساب ندارید؟', en: "Don't have an account?" },
        'login.register': { fa: 'ثبت‌نام کنید', en: 'Register' },
        
        // Register Page
        'register.title': { fa: 'ایجاد حساب کاربری', en: 'Create an Account' },
        'register.subtitle': { fa: 'ثبت‌نام رایگان و در کمتر از ۱ دقیقه!', en: 'Free registration in less than 1 minute!' },
        'register.firstName': { fa: 'نام', en: 'First Name' },
        'register.firstName.placeholder': { fa: 'محمد', en: 'John' },
        'register.lastName': { fa: 'نام خانوادگی', en: 'Last Name' },
        'register.lastName.placeholder': { fa: 'احمدی', en: 'Doe' },
        'register.name': { fa: 'نام و نام خانوادگی', en: 'Full Name' },
        'register.name.placeholder': { fa: 'نام خود را وارد کنید', en: 'Enter your full name' },
        'register.email': { fa: 'ایمیل', en: 'Email' },
        'register.email.placeholder': { fa: 'ایمیل خود را وارد کنید', en: 'Enter your email' },
        'register.phone': { fa: 'شماره موبایل', en: 'Mobile Number' },
        'register.phone.placeholder': { fa: 'شماره تلفن خود را وارد کنید', en: 'Enter your phone number' },
        'register.password': { fa: 'رمز عبور', en: 'Password' },
        'register.password.placeholder': { fa: 'حداقل ۸ کاراکتر', en: 'At least 8 characters' },
        'register.confirm': { fa: 'تکرار رمز عبور', en: 'Confirm Password' },
        'register.confirm.placeholder': { fa: 'رمز عبور را مجدداً وارد کنید', en: 'Confirm your password' },
        'register.terms': { fa: 'با ثبت‌نام،', en: 'By registering,' },
        'register.termsLink': { fa: 'قوانین و مقررات', en: 'Terms and Conditions' },
        'register.termsEnd': { fa: 'را می‌پذیرید.', en: 'you agree to.' },
        'register.google': { fa: 'ثبت‌نام با گوگل', en: 'Sign up with Google' },
        'register.submit': { fa: 'ثبت‌نام', en: 'Register' },
        'register.hasAccount': { fa: 'قبلاً ثبت‌نام کرده‌اید؟', en: 'Already have an account?' },
        'register.login': { fa: 'وارد شوید', en: 'Login' },
        
        // Navigation extras
        'nav.home': { fa: 'صفحه اصلی', en: 'Home' },
        
        // Payment Page extras
        'payment.title': { fa: 'خرید لایسنس OdooMaster', en: 'Purchase OdooMaster License' },
        'payment.desc': { fa: 'لایسنس مورد نظر خود را انتخاب کرده و به راحتی خریداری کنید', en: 'Select your desired license and purchase easily' },
        'payment.backToLicense': { fa: 'بازگشت به صفحه لایسنس', en: 'Back to Licenses' },
        'payment.hwid.label': { fa: 'شناسه سخت‌افزاری دستگاه شما:', en: 'Your Hardware ID:' },
        'payment.hwid.loading': { fa: 'در حال دریافت...', en: 'Loading...' },
        'payment.hwid.placeholder': { fa: 'شناسه سخت‌افزاری را وارد کنید', en: 'Enter Hardware ID' },
        'payment.hwid.validate': { fa: 'تایید', en: 'Validate' },
        'payment.hwid.help': { fa: 'شناسه سخت‌افزاری را از نصاب OdooMaster کپی کنید یا دستی وارد نمایید.', en: 'Copy the Hardware ID from OdooMaster installer or enter manually.' },
        'payment.hwid.invalid': { fa: 'شناسه سخت‌افزاری نامعتبر است. باید 16 کاراکتر هگزادسیمال (0-9, a-f) باشد.', en: 'Invalid Hardware ID. Must be 16 hexadecimal characters (0-9, a-f).' },
        'payment.hwid.validated': { fa: 'تایید شد', en: 'Validated' },
        'payment.selectPlan': { fa: 'انتخاب پلن:', en: 'Select Plan:' },
        'payment.customerInfo': { fa: 'اطلاعات خریدار (اختیاری):', en: 'Buyer Information (Optional):' },
        'payment.name': { fa: 'نام و نام خانوادگی', en: 'Full Name' },
        'payment.name.placeholder': { fa: 'مثال: علی احمدی', en: 'e.g. John Doe' },
        'payment.email': { fa: 'ایمیل', en: 'Email' },
        'payment.phone': { fa: 'شماره موبایل', en: 'Mobile Number' },
        'payment.selectedPlan': { fa: 'پلن انتخابی:', en: 'Selected Plan:' },
        'payment.notSelected': { fa: 'انتخاب نشده', en: 'Not selected' },
        'payment.amount': { fa: 'مبلغ:', en: 'Amount:' },
        'payment.pay': { fa: 'پرداخت', en: 'Pay Now' },
        'payment.secureBadge': { fa: 'پرداخت امن با درگاه زرین‌پال', en: 'Secure payment with ZarinPal' },
        
        // Dashboard
        'dashboard.welcome': { fa: 'خوش آمدید', en: 'Welcome' },
        'dashboard.overview': { fa: 'نمای کلی', en: 'Overview' },
        'dashboard.licenses': { fa: 'لایسنس‌ها', en: 'Licenses' },
        'dashboard.activeLicenses': { fa: 'لایسنس فعال', en: 'Active Licenses' },
        'dashboard.mainMenu': { fa: 'منو اصلی', en: 'Main Menu' },
        'dashboard.dashboard': { fa: 'داشبورد', en: 'Dashboard' },
        'dashboard.financial': { fa: 'مالی', en: 'Financial' },
        'dashboard.invoices': { fa: 'فاکتورها', en: 'Invoices' },
        'dashboard.wallet': { fa: 'کیف پول', en: 'Wallet' },
        'dashboard.account': { fa: 'حساب کاربری', en: 'Account' },
        'dashboard.profile': { fa: 'پروفایل', en: 'Profile' },
        'dashboard.settings': { fa: 'تنظیمات', en: 'Settings' },
        'dashboard.management': { fa: 'مدیریت', en: 'Management' },
        'dashboard.adminPanel': { fa: 'پنل مدیریت', en: 'Admin Panel' },
        'dashboard.hello': { fa: 'سلام،', en: 'Hello,' },
        'dashboard.dearUser': { fa: 'کاربر عزیز', en: 'Dear User' },
        'dashboard.welcomeText': { fa: 'خوش آمدید! از پنل کاربری خود برای مدیریت لایسنس‌ها و دانلود نصاب استفاده کنید.', en: 'Welcome! Use your dashboard to manage licenses and download the installer.' },
        'dashboard.downloads': { fa: 'دانلود', en: 'Downloads' },
        'dashboard.daysRemaining': { fa: 'روز باقیمانده', en: 'Days Remaining' },
        'dashboard.openTickets': { fa: 'تیکت باز', en: 'Open Tickets' },
        'dashboard.totalDownloads': { fa: 'کل دانلودها', en: 'Total Downloads' },
        'dashboard.supportTickets': { fa: 'تیکت‌های پشتیبانی', en: 'Support Tickets' },
        'dashboard.recentActivity': { fa: 'فعالیت‌های اخیر', en: 'Recent Activity' },
        'dashboard.activeLicensesTitle': { fa: 'لایسنس‌های فعال', en: 'Active Licenses' },
        'dashboard.viewAll': { fa: 'مشاهده همه', en: 'View All' },
        'dashboard.lastUpdate': { fa: 'آخرین بروزرسانی:', en: 'Last Update:' },
        'dashboard.preparing': { fa: 'در حال آماده‌سازی...', en: 'Preparing...' },
        'dashboard.achievements': { fa: 'دستاوردها', en: 'Achievements' },
        'dashboard.firstStep': { fa: 'اولین قدم', en: 'First Step' },
        'dashboard.firstDownload': { fa: 'اولین دانلود', en: 'First Download' },
        'dashboard.licenseHolder': { fa: 'لایسنس‌دار', en: 'License Holder' },
        'dashboard.referrer': { fa: 'معرف', en: 'Referrer' },
        'dashboard.legendary': { fa: 'افسانه‌ای', en: 'Legendary' },
        'dashboard.level': { fa: 'سطح', en: 'Level' },
        'dashboard.toNextLevel': { fa: 'تا سطح بعدی:', en: 'To Next Level:' },
        'dashboard.nextLevelReward': { fa: 'پاداش سطح بعدی:', en: 'Next Level Reward:' },
        'dashboard.discount10': { fa: '۱۰% تخفیف خرید بعدی', en: '10% Discount on Next Purchase' },
        'dashboard.notifications': { fa: 'اعلان‌ها', en: 'Notifications' },
        'dashboard.markAllRead': { fa: 'همه خوانده شد', en: 'Mark All Read' },
        'dashboard.buyNewLicense': { fa: 'خرید لایسنس جدید', en: 'Buy New License' },
        
        // Payment Page
        'payment.title': { fa: 'خرید لایسنس', en: 'Purchase License' },
        'payment.selectPlan': { fa: 'انتخاب پلن', en: 'Select a Plan' },
        'payment.customerInfo': { fa: 'اطلاعات مشتری', en: 'Customer Information' },
        'payment.name': { fa: 'نام و نام خانوادگی', en: 'Full Name' },
        'payment.email': { fa: 'ایمیل', en: 'Email' },
        'payment.phone': { fa: 'شماره تلفن', en: 'Phone Number' },
        'payment.hwid': { fa: 'شناسه سخت‌افزاری', en: 'Hardware ID' },
        'payment.hwid.error': { fa: 'شناسه سخت‌افزاری یافت نشد! لطفاً از طریق نصب‌کننده وارد شوید.', en: 'Hardware ID not found! Please enter through the installer.' },
        'payment.summary': { fa: 'خلاصه سفارش', en: 'Order Summary' },
        'payment.plan': { fa: 'پلن', en: 'Plan' },
        'payment.total': { fa: 'جمع کل', en: 'Total' },
        'payment.pay': { fa: 'پرداخت', en: 'Pay Now' },
        'payment.processing': { fa: 'در حال پردازش...', en: 'Processing...' },
        'payment.success': { fa: 'خرید با موفقیت انجام شد! در حال دانلود فایل لایسنس...', en: 'Purchase successful! Downloading license file...' },
        
        // Licenses Page
        'licenses.title': { fa: 'مدیریت لایسنس‌ها', en: 'Manage Licenses' },
        'licenses.desc': { fa: 'لایسنس‌های فعال و تاریخ انقضا', en: 'Active licenses and expiration dates' },
        'licenses.note': { fa: 'برای دانلود فایل‌ها، باید لایسنس غیر Trial فعال داشته باشید.', en: 'To download files, you must have an active non-Trial license.' },
        'licenses.buyLicense': { fa: 'خرید لایسنس', en: 'Buy License' },
        'licenses.panel': { fa: 'پنل', en: 'Panel' },
        'licenses.active': { fa: 'فعال', en: 'Active' },
        'licenses.inactive': { fa: 'غیرفعال', en: 'Inactive' },
        'licenses.expired': { fa: 'منقضی', en: 'Expired' },
        'licenses.trial': { fa: 'آزمایشی', en: 'Trial' },
        'licenses.download': { fa: 'دانلود فایل لایسنس', en: 'Download License File' },
        'licenses.noLicenses': { fa: 'هنوز لایسنسی ندارید', en: 'You have no licenses yet' },
        'licenses.buyNow': { fa: 'خرید لایسنس', en: 'Buy License' },
        'licenses.expiresAt': { fa: 'انقضا:', en: 'Expires:' },
        'licenses.activeDevices': { fa: 'دستگاه‌های فعال', en: 'Active Devices' },
        'licenses.plan': { fa: 'پلن', en: 'Plan' },
        'licenses.key': { fa: 'کلید', en: 'Key' },
        'licenses.issued': { fa: 'صدور', en: 'Issued' },
        'licenses.expires': { fa: 'انقضا', en: 'Expires' },
        'licenses.copyKey': { fa: 'کپی کلید', en: 'Copy Key' },
        'licenses.renew': { fa: 'تمدید', en: 'Renew' },
        'licenses.enterHwid': { fa: 'شناسه سخت‌افزاری دستگاه را وارد کنید:', en: 'Enter your hardware ID:' },
        'licenses.hwidRequired': { fa: 'شناسه سخت‌افزاری الزامی است', en: 'Hardware ID is required' },
        'licenses.generating': { fa: 'در حال تولید...', en: 'Generating...' },
        'licenses.downloadSuccess': { fa: 'فایل لایسنس دانلود شد', en: 'License file downloaded' },
        'licenses.downloadError': { fa: 'خطا در دانلود فایل لایسنس', en: 'Error downloading license file' },
        'licenses.keyCopied': { fa: 'کلید لایسنس کپی شد', en: 'License key copied' },
        'licenses.copyFailed': { fa: 'کپی انجام نشد', en: 'Copy failed' },
        'licenses.hardwareId': { fa: 'شناسه سخت‌افزار:', en: 'Hardware ID:' },
        
        // Navigation extras
        'nav.docs': { fa: 'مستندات', en: 'Docs' },
        
        // Downloads Page
        'downloads.title': { fa: 'دانلودها', en: 'Downloads' },
        'downloads.installer': { fa: 'نصب‌کننده', en: 'Installer' },
        'downloads.version': { fa: 'نسخه', en: 'Version' },
        'downloads.size': { fa: 'حجم', en: 'Size' },
        'downloads.download': { fa: 'دانلود', en: 'Download' },
        'downloads.requirements': { fa: 'پیش‌نیازها', en: 'Requirements' },
        
        // Support Page
        'support.title': { fa: 'پشتیبانی', en: 'Support' },
        'support.faq': { fa: 'سوالات متداول', en: 'FAQ' },
        'support.contact': { fa: 'تماس با ما', en: 'Contact Us' },
        'support.ticket': { fa: 'ارسال تیکت', en: 'Submit Ticket' },
        
        // Demo Page
        'demo.title': { fa: 'دمو نصب‌کننده', en: 'Installer Demo' },
        'demo.desc': { fa: 'نحوه کار با نصب‌کننده OdooMaster را ببینید', en: 'See how the OdooMaster installer works' },
        'demo.watch': { fa: 'مشاهده دمو', en: 'Watch Demo' },
        
        // Dashboard - System Check
        'dashboard.systemCheck': { fa: 'تست سیستم و نصب نیازمندی‌ها', en: 'System Check & Install Requirements' },
        'dashboard.systemCheckDesc': { fa: 'قبل از نصب Odoo، سیستم شما بررسی می‌شود و نیازمندی‌های ناموجود از منابع رسمی دانلود و نصب می‌شوند.', en: 'Before installing Odoo, your system will be checked and missing requirements will be downloaded and installed from official sources.' },
        'dashboard.readyToTest': { fa: 'آماده تست', en: 'Ready to Test' },
        'dashboard.operatingSystem': { fa: 'سیستم عامل', en: 'Operating System' },
        'dashboard.waiting': { fa: 'در انتظار...', en: 'Waiting...' },
        'dashboard.downloadFrom': { fa: 'دانلود از', en: 'Download from' },
        'dashboard.startSystemCheck': { fa: 'شروع بررسی سیستم', en: 'Start System Check' },
        'dashboard.installMissing': { fa: 'نصب نیازمندی‌ها', en: 'Install Missing' },
        'dashboard.quickAccess': { fa: 'دسترسی سریع', en: 'Quick Access' },
        'dashboard.downloadInstaller': { fa: 'دانلود نصاب', en: 'Download Installer' },
        'dashboard.buyLicense': { fa: 'خرید لایسنس', en: 'Buy License' },
        'dashboard.sendTicket': { fa: 'ارسال تیکت', en: 'Send Ticket' },
        'dashboard.documentation': { fa: 'مستندات', en: 'Documentation' },
        'dashboard.search': { fa: 'جستجو...', en: 'Search...' },
        'dashboard.logout': { fa: 'خروج', en: 'Logout' },
        'dashboard.proPlan': { fa: 'پلن حرفه‌ای', en: 'Pro Plan' },
        
        // Common
        'common.loading': { fa: 'در حال بارگذاری...', en: 'Loading...' },
        'common.error': { fa: 'خطا', en: 'Error' },
        'common.success': { fa: 'موفقیت', en: 'Success' },
        'common.cancel': { fa: 'انصراف', en: 'Cancel' },
        'common.confirm': { fa: 'تأیید', en: 'Confirm' },
        'common.save': { fa: 'ذخیره', en: 'Save' },
        'common.delete': { fa: 'حذف', en: 'Delete' },
        'common.edit': { fa: 'ویرایش', en: 'Edit' },
        'common.close': { fa: 'بستن', en: 'Close' },
        'common.back': { fa: 'بازگشت', en: 'Back' },
        'common.next': { fa: 'بعدی', en: 'Next' },
        'common.prev': { fa: 'قبلی', en: 'Previous' },
        'common.search': { fa: 'جستجو...', en: 'Search...' },
        
        // Error messages
        'error.required': { fa: 'این فیلد الزامی است', en: 'This field is required' },
        'error.email': { fa: 'ایمیل نامعتبر است', en: 'Invalid email address' },
        'error.phone': { fa: 'شماره تلفن نامعتبر است', en: 'Invalid phone number' },
        'error.password.min': { fa: 'رمز عبور باید حداقل ۶ کاراکتر باشد', en: 'Password must be at least 6 characters' },
        'error.password.match': { fa: 'رمز عبور تطابق ندارد', en: 'Passwords do not match' },
        'error.login': { fa: 'ایمیل یا رمز عبور اشتباه است', en: 'Invalid email or password' },
        'error.network': { fa: 'خطا در اتصال به سرور', en: 'Network connection error' },
        
        // Validation messages for payment
        'validation.name.required': { fa: 'لطفاً نام و نام خانوادگی خود را وارد کنید (حداقل ۳ کاراکتر)', en: 'Please enter your full name (at least 3 characters)' },
        'validation.email.required': { fa: 'لطفاً ایمیل معتبر وارد کنید', en: 'Please enter a valid email address' },
        'validation.phone.required': { fa: 'لطفاً شماره تلفن همراه معتبر وارد کنید (مثال: 09123456789)', en: 'Please enter a valid mobile number' },
        'validation.plan.required': { fa: 'لطفاً یک پلن انتخاب کنید', en: 'Please select a plan' },
        'validation.hwid.required': { fa: 'شناسه سخت‌افزاری معتبر نیست! برای خرید لایسنس باید از طریق نصب‌کننده OdooMaster وارد این صفحه شوید.', en: 'Invalid hardware ID! To purchase a license, you must access this page through the OdooMaster installer.' },
        'validation.hwid.missing': { fa: 'برای خرید لایسنس، ابتدا باید از طریق نصب‌کننده OdooMaster وارد این صفحه شوید تا شناسه سخت‌افزاری دستگاه شما شناسایی شود.', en: 'To purchase a license, you must first access this page through the OdooMaster installer so your hardware ID can be identified.' },
        
        // Duration texts
        'duration.hour': { fa: 'یک ساعته', en: '1 Hour' },
        'duration.week': { fa: 'یک هفته ای', en: '1 Week' },
        'duration.month': { fa: 'یک ماهه', en: '1 Month' },
        'duration.3months': { fa: 'سه ماهه', en: '3 Months' },
        'duration.6months': { fa: 'شش ماهه', en: '6 Months' },
        'duration.year': { fa: 'یکساله', en: '1 Year' },
        'duration.unlimited': { fa: 'نامحدود', en: 'Unlimited' },

        // Floating cards
        'float.installed': { fa: 'نصب کامل شد!', en: 'Installation Complete!' },
        'float.uptime': { fa: '۹۹.۹% آپتایم', en: '99.9% Uptime' },
        'float.security': { fa: 'امنیت کامل', en: 'Full Security' },
        
        // Theme
        'theme.toggle': { fa: 'تغییر تم', en: 'Toggle Theme' },
        'theme.dark': { fa: 'تم تاریک', en: 'Dark Mode' },
        'theme.light': { fa: 'تم روشن', en: 'Light Mode' },
    },
    
    /**
     * Initialize i18n system
     */
    init() {
        // Get saved language or detect from browser
        const saved = localStorage.getItem('odoomaster_lang');
        if (saved && this.languages[saved]) {
            this.currentLang = saved;
        } else {
            // Detect from browser
            const browserLang = navigator.language.substring(0, 2);
            this.currentLang = browserLang === 'fa' ? 'fa' : 'en';
        }
        
        // Apply language
        this.applyLanguage();
        
        // Create language switcher
        this.createLanguageSwitcher();
        
        console.log(`[i18n] Initialized with language: ${this.currentLang}`);
    },
    
    /**
     * Get translation for a key
     */
    t(key, fallback = '') {
        const trans = this.translations[key];
        if (trans && trans[this.currentLang]) {
            return trans[this.currentLang];
        }
        return fallback || key;
    },
    
    /**
     * Set current language
     */
    setLanguage(lang) {
        if (!this.languages[lang]) return;
        
        this.currentLang = lang;
        localStorage.setItem('odoomaster_lang', lang);
        this.applyLanguage();
        
        // Dispatch event for other components
        document.dispatchEvent(new CustomEvent('languageChange', { detail: { lang } }));
    },
    
    /**
     * Apply current language to document
     */
    applyLanguage() {
        const langInfo = this.languages[this.currentLang];
        
        // Set document direction and language
        document.documentElement.lang = this.currentLang;
        document.documentElement.dir = langInfo.dir;
        document.body.dir = langInfo.dir;
        
        // Add/remove RTL class
        if (langInfo.dir === 'rtl') {
            document.body.classList.add('rtl');
            document.body.classList.remove('ltr');
        } else {
            document.body.classList.add('ltr');
            document.body.classList.remove('rtl');
        }
        
        // Update font family for English
        if (this.currentLang === 'en') {
            document.body.style.fontFamily = "'Inter', 'Segoe UI', sans-serif";
        } else {
            document.body.style.fontFamily = "'Vazirmatn', 'Segoe UI', sans-serif";
        }
        
        // Translate all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.textContent = translation;
            }
        });
        
        // Translate placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.placeholder = translation;
            }
        });
        
        // Translate titles
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.title = translation;
            }
        });
        
        // Update lang switcher button text
        this.updateSwitcherButton();
    },
    
    /**
     * Create language switcher button
     */
    createLanguageSwitcher() {
        // Check if already exists
        if (document.getElementById('langSwitcher')) return;
        
        // For dashboard page, look for topbar switcher container first
        let topbarContainer = document.querySelector('.lang-switcher-topbar, #langSwitcherTopbar');
        if (topbarContainer) {
            this.createTopbarLanguageSwitcher(topbarContainer);
            return;
        }
        
        // Find nav-actions container (for main pages)
        let navActions = document.querySelector('.nav-actions');
        
        // For auth pages (login, register), create floating switcher
        if (!navActions) {
            this.createFloatingLanguageSwitcher();
            return;
        }
        
        // Create switcher container
        const switcher = document.createElement('div');
        switcher.className = 'lang-switcher';
        switcher.id = 'langSwitcher';
        
        // Create button
        const btn = document.createElement('button');
        btn.className = 'lang-btn';
        btn.id = 'langSwitcherBtn';
        btn.type = 'button';
        
        const otherLang = this.currentLang === 'fa' ? 'en' : 'fa';
        const langInfo = this.languages[otherLang];
        btn.innerHTML = `<span class="lang-flag">${langInfo.flag}</span><span class="lang-name">${langInfo.name}</span>`;
        
        btn.addEventListener('click', () => {
            const newLang = this.currentLang === 'fa' ? 'en' : 'fa';
            this.setLanguage(newLang);
        });
        
        switcher.appendChild(btn);
        
        // Insert at the beginning of nav-actions
        navActions.insertBefore(switcher, navActions.firstChild);
    },
    
    /**
     * Create floating language switcher for auth pages
     */
    createFloatingLanguageSwitcher() {
        if (document.getElementById('langSwitcher')) return;
        
        const switcher = document.createElement('div');
        switcher.className = 'lang-switcher';
        switcher.id = 'langSwitcher';
        switcher.style.cssText = 'position: fixed; top: 20px; left: 20px; z-index: 1000;';
        
        const btn = document.createElement('button');
        btn.className = 'lang-btn';
        btn.id = 'langSwitcherBtn';
        btn.type = 'button';
        btn.style.cssText = 'display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); border-radius: 25px; color: #888; font-size: 0.9rem; cursor: pointer; transition: all 0.3s; backdrop-filter: blur(10px);';
        
        const otherLang = this.currentLang === 'fa' ? 'en' : 'fa';
        const langInfo = this.languages[otherLang];
        btn.innerHTML = `<span style="font-size: 1.2rem;">${langInfo.flag}</span><span>${langInfo.name}</span>`;
        
        btn.addEventListener('click', () => {
            const newLang = this.currentLang === 'fa' ? 'en' : 'fa';
            this.setLanguage(newLang);
        });
        
        btn.addEventListener('mouseenter', () => {
            btn.style.background = 'var(--primary, #00d4aa)';
            btn.style.color = '#050505';
            btn.style.borderColor = 'var(--primary, #00d4aa)';
        });
        
        btn.addEventListener('mouseleave', () => {
            btn.style.background = 'rgba(255,255,255,0.1)';
            btn.style.color = '#888';
            btn.style.borderColor = 'rgba(255,255,255,0.15)';
        });
        
        switcher.appendChild(btn);
        document.body.appendChild(switcher);
    },
    
    /**
     * Create language switcher for dashboard topbar
     */
    createTopbarLanguageSwitcher(container) {
        const switcher = document.createElement('div');
        switcher.className = 'lang-switcher';
        switcher.id = 'langSwitcher';
        
        const btn = document.createElement('button');
        btn.className = 'lang-btn topbar-lang-btn';
        btn.id = 'langSwitcherBtn';
        btn.type = 'button';
        
        const otherLang = this.currentLang === 'fa' ? 'en' : 'fa';
        const langInfo = this.languages[otherLang];
        btn.innerHTML = `<span class="lang-flag">${langInfo.flag}</span><span class="lang-name">${langInfo.name}</span>`;
        
        btn.addEventListener('click', () => {
            const newLang = this.currentLang === 'fa' ? 'en' : 'fa';
            this.setLanguage(newLang);
        });
        
        switcher.appendChild(btn);
        container.appendChild(switcher);
    },
    
    /**
     * Update switcher button to show other language
     */
    updateSwitcherButton() {
        const btn = document.getElementById('langSwitcherBtn');
        if (btn) {
            const otherLang = this.currentLang === 'fa' ? 'en' : 'fa';
            const langInfo = this.languages[otherLang];
            btn.innerHTML = `<span class="lang-flag" style="font-size: 1.2rem;">${langInfo.flag}</span><span class="lang-name">${langInfo.name}</span>`;
        }
        
        // Update nav language switcher
        const navLangBtn = document.getElementById('langNameNav');
        if (navLangBtn) {
            const currentLangInfo = this.languages[this.currentLang];
            navLangBtn.textContent = currentLangInfo.name;
        }
        
        // Update floating switcher position based on direction
        const switcher = document.getElementById('langSwitcher');
        if (switcher && switcher.style.position === 'fixed') {
            if (this.currentLang === 'en') {
                // LTR - move to right
                switcher.style.left = 'auto';
                switcher.style.right = '20px';
            } else {
                // RTL - move to left
                switcher.style.right = 'auto';
                switcher.style.left = '20px';
            }
        }
    },
    
    /**
     * Toggle between languages
     */
    toggle() {
        const newLang = this.currentLang === 'fa' ? 'en' : 'fa';
        this.setLanguage(newLang);
    },
    
    /**
     * Get current language
     */
    getLang() {
        return this.currentLang;
    },
    
    /**
     * Check if current language is RTL
     */
    isRTL() {
        return this.languages[this.currentLang].dir === 'rtl';
    },
    
    /**
     * Format number based on language
     */
    formatNumber(num) {
        if (this.currentLang === 'fa') {
            return num.toLocaleString('fa-IR');
        }
        return num.toLocaleString('en-US');
    },
    
    /**
     * Format price based on language
     */
    formatPrice(price) {
        if (this.currentLang === 'fa') {
            return price.toLocaleString('fa-IR') + ' تومان';
        }
        return '$' + price.toLocaleString('en-US');
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => I18N.init());
} else {
    I18N.init();
}

// Export for use in other modules
window.I18N = I18N;
