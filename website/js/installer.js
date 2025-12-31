/**
 * OdooMaster Online Installer
 * نصاب آنلاین - دانلود از منابع رسمی با Fallback به سرور خودمان
 */

const OnlineInstaller = {
    // تنظیمات پایه
    config: {
        // آدرس پایه سرور خودمان برای fallback
        // وقتی فایل‌ها رو روی هاست گذاشتی، این رو تغییر بده
        selfHostedBaseUrl: '/downloads/installers',
        
        // آیا اول از سایت رسمی دانلود بشه یا از سرور خودمان؟
        preferOfficial: true,
        
        // تایم‌اوت برای چک کردن در دسترس بودن لینک (میلی‌ثانیه)
        linkCheckTimeout: 5000
    },

    // لینک‌های دانلود - هم رسمی و هم fallback
    sources: {
        python: {
            name: 'Python 3.11',
            version: '3.11.9',
            official_url: 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe',
            fallback_file: 'python-3.11.9-amd64.exe',
            size: '25 MB',
            official: 'python.org'
        },
        postgresql: {
            name: 'PostgreSQL 16',
            version: '16.3',
            official_url: 'https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64.exe',
            fallback_file: 'postgresql-16.3-1-windows-x64.exe',
            size: '85 MB',
            official: 'enterprisedb.com'
        },
        git: {
            name: 'Git',
            version: '2.45.2',
            official_url: 'https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe',
            fallback_file: 'Git-2.45.2-64-bit.exe',
            size: '55 MB',
            official: 'git-scm.com'
        },
        nodejs: {
            name: 'Node.js LTS',
            version: '20.14.0',
            official_url: 'https://nodejs.org/dist/v20.14.0/node-v20.14.0-x64.msi',
            fallback_file: 'node-v20.14.0-x64.msi',
            size: '30 MB',
            official: 'nodejs.org'
        },
        vcredist: {
            name: 'Visual C++ Redistributable',
            version: '2022',
            official_url: 'https://aka.ms/vs/17/release/vc_redist.x64.exe',
            fallback_file: 'vc_redist.x64.exe',
            size: '25 MB',
            official: 'microsoft.com'
        },
        wkhtmltopdf: {
            name: 'wkhtmltopdf',
            version: '0.12.6',
            official_url: 'https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe',
            fallback_file: 'wkhtmltox-0.12.6-1.msvc2015-win64.exe',
            size: '35 MB',
            official: 'wkhtmltopdf.org'
        }
    },

    // وضعیت نصب
    state: {
        currentStep: 1,
        checkResults: {},
        installQueue: [],
        isInstalling: false
    },

    // رویدادها
    events: {},

    on(event, callback) {
        if (!this.events[event]) this.events[event] = [];
        this.events[event].push(callback);
    },

    emit(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(cb => cb(data));
        }
    },

    /**
     * بررسی سیستم (شبیه‌سازی در مرورگر)
     * در نسخه واقعی، این کار توسط یک برنامه محلی انجام می‌شود
     */
    async checkSystem() {
        this.emit('check:start');
        
        const checks = ['os', 'python', 'postgresql', 'git', 'nodejs', 'vcredist'];
        
        for (const check of checks) {
            this.emit('check:item:start', { name: check });
            
            // شبیه‌سازی تاخیر بررسی
            await this.delay(600 + Math.random() * 400);
            
            // در مرورگر، نمی‌توانیم واقعاً چک کنیم
            // این اطلاعات باید از یک برنامه محلی (مثل Electron یا API محلی) بیاید
            const result = await this.simulateCheck(check);
            
            this.state.checkResults[check] = result;
            this.emit('check:item:complete', { name: check, result });
        }
        
        // ساخت لیست نیازمندی‌ها برای نصب
        this.buildInstallQueue();
        
        this.emit('check:complete', {
            results: this.state.checkResults,
            installQueue: this.state.installQueue
        });
    },

    async simulateCheck(name) {
        // این فقط برای دمو است
        // در نسخه واقعی، یک API محلی این کار را می‌کند
        const simulations = {
            os: { installed: true, version: 'Windows 11 64-bit', status: 'success' },
            python: { installed: false, version: null, status: 'error' },
            postgresql: { installed: false, version: null, status: 'error' },
            git: { installed: true, version: '2.30.0', status: 'warning', message: 'نسخه قدیمی' },
            nodejs: { installed: true, version: '20.10.0', status: 'success' },
            vcredist: { installed: true, version: '2022', status: 'success' }
        };
        return simulations[name] || { installed: false, status: 'error' };
    },

    buildInstallQueue() {
        this.state.installQueue = [];
        
        for (const [name, result] of Object.entries(this.state.checkResults)) {
            if (result.status === 'error' || result.status === 'warning') {
                if (this.sources[name]) {
                    const source = this.sources[name];
                    this.state.installQueue.push({
                        id: name,
                        ...source,
                        // لینک اصلی (رسمی یا fallback بسته به تنظیمات)
                        url: this.config.preferOfficial ? source.official_url : this.getFallbackUrl(name),
                        fallback_url: this.config.preferOfficial ? this.getFallbackUrl(name) : source.official_url,
                        action: result.status === 'warning' ? 'update' : 'install'
                    });
                }
            }
        }
    },

    /**
     * ساخت لینک fallback از سرور خودمان
     */
    getFallbackUrl(name) {
        const source = this.sources[name];
        if (!source || !source.fallback_file) return null;
        return `${this.config.selfHostedBaseUrl}/${source.fallback_file}`;
    },

    /**
     * چک کردن در دسترس بودن یک لینک
     */
    async checkLinkAvailable(url) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.linkCheckTimeout);
            
            const response = await fetch(url, {
                method: 'HEAD',
                mode: 'no-cors', // برای جلوگیری از CORS errors
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            return true; // اگر خطا نداد، فرض می‌کنیم در دسترسه
        } catch (error) {
            console.warn(`Link not available: ${url}`, error.message);
            return false;
        }
    },

    /**
     * گرفتن بهترین لینک دانلود (با fallback)
     */
    async getBestDownloadUrl(item) {
        // اول لینک اصلی رو امتحان کن
        const primaryAvailable = await this.checkLinkAvailable(item.url);
        if (primaryAvailable) {
            return { url: item.url, source: this.config.preferOfficial ? 'official' : 'self-hosted' };
        }
        
        // اگه نشد، fallback رو امتحان کن
        if (item.fallback_url) {
            const fallbackAvailable = await this.checkLinkAvailable(item.fallback_url);
            if (fallbackAvailable) {
                return { url: item.fallback_url, source: this.config.preferOfficial ? 'self-hosted' : 'official' };
            }
        }
        
        // اگه هیچکدوم نشد، لینک اصلی رو برگردون (کاربر خودش می‌فهمه)
        return { url: item.url, source: 'unknown' };
    },

    /**
     * شروع دانلود با پشتیبانی از fallback
     */
    async downloadFromOfficial(item) {
        this.emit('download:start', item);
        
        // پیدا کردن بهترین لینک
        const { url, source } = await this.getBestDownloadUrl(item);
        
        this.emit('download:source', { item, url, source });
        
        // ایجاد لینک دانلود
        const link = document.createElement('a');
        link.href = url;
        link.download = url.split('/').pop();
        link.target = '_blank';
        
        return new Promise((resolve) => {
            this.emit('download:progress', { item, progress: 100 });
            
            // باز کردن لینک در تب جدید
            window.open(url, '_blank');
            
            setTimeout(() => {
                this.emit('download:complete', { item, url, source });
                resolve(true);
            }, 500);
        });
    },

    /**
     * نصب آیتم (نیاز به برنامه محلی)
     */
    async installItem(item) {
        this.emit('install:start', item);
        
        // در مرورگر، فقط می‌توانیم راهنمایی نشان دهیم
        // نصب واقعی نیاز به اجرای فایل exe/msi دارد
        
        await this.delay(2000);
        
        this.emit('install:complete', item);
        return true;
    },

    /**
     * اجرای کل فرآیند نصب
     */
    async runInstallation() {
        if (this.state.isInstalling) return;
        this.state.isInstalling = true;
        
        this.emit('installation:start');
        
        for (const item of this.state.installQueue) {
            try {
                await this.downloadFromOfficial(item);
                // await this.installItem(item); // نیاز به برنامه محلی
            } catch (error) {
                this.emit('installation:error', { item, error });
            }
        }
        
        this.state.isInstalling = false;
        this.emit('installation:complete');
    },

    /**
     * تولید HTML برای نمایش وضعیت
     */
    renderCheckItem(name, result) {
        const source = this.sources[name];
        const icons = {
            os: 'fas fa-desktop',
            python: 'fab fa-python',
            postgresql: 'fas fa-database',
            git: 'fab fa-git-alt',
            nodejs: 'fab fa-node-js',
            vcredist: 'fas fa-cogs',
            wkhtmltopdf: 'fas fa-file-pdf'
        };
        
        const statusClass = result ? result.status : '';
        const statusText = result 
            ? (result.installed ? result.version : 'نصب نشده')
            : 'در انتظار...';
        
        return `
            <div class="check-item ${statusClass}" data-check="${name}">
                <div class="check-icon">
                    <i class="${icons[name] || 'fas fa-cube'}"></i>
                </div>
                <div class="check-info">
                    <h4>${source?.name || name}</h4>
                    <p>${result?.message || (source ? `دانلود از ${source.official}` : '')}</p>
                </div>
                <span class="check-status">${statusText}</span>
            </div>
        `;
    },

    renderInstallQueue() {
        return this.state.installQueue.map(item => `
            <div class="install-item" data-id="${item.id}">
                <div class="install-info">
                    <strong>${item.name}</strong>
                    <span class="install-meta">
                        ${item.size} • ${item.official}
                    </span>
                </div>
                <div class="install-status">
                    <span class="status-text">آماده</span>
                    <div class="progress-bar" style="display:none;">
                        <div class="progress-fill"></div>
                    </div>
                </div>
                <a href="${item.url}" target="_blank" class="btn btn-sm btn-outline">
                    <i class="fas fa-download"></i>
                    دانلود
                </a>
            </div>
        `).join('');
    },

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OnlineInstaller;
}
