/**
 * OdooMaster API Client
 * مدیریت ارتباط با سرور API
 */

function normalizeAuthToken(token) {
    if (token === null || token === undefined) return null;
    let t = String(token).trim();
    if (!t) return null;
    if (t === 'null' || t === 'undefined') return null;

    // In case some older code stored the full header value.
    if (/^bearer\s+/i.test(t)) {
        t = t.replace(/^bearer\s+/i, '').trim();
    }

    return t || null;
}

const API = {
    // تنظیمات
    baseUrl: (() => {
        // Production / hosted: same origin
        if (window.location.protocol !== 'file:') {
            const host = (window.location.hostname || '').toLowerCase();
            const port = (window.location.port || '').trim();

            // Local dev convenience:
            // If frontend is served from localhost but NOT from the API port,
            // point API calls to the API server on :5001.
            if (port && port !== '5001') {
                const isDevHost = (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' || /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host));
                if (isDevHost) {
                    const proto = window.location.protocol || 'http:';
                    return `${proto}//${window.location.hostname}:5001/api`;
                }
            }

            return '/api';
        }

        // If opened as a local file, fall back to local dev API
        return 'http://127.0.0.1:5001/api';
    })(),
    token: normalizeAuthToken(localStorage.getItem('authToken')),
    
    // متد عمومی برای درخواست‌ها
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        // اضافه کردن توکن اگر موجود باشد
        const token = normalizeAuthToken(this.token);
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json();

            if (!response.ok) {
                const err = new Error(data.error || 'خطا در ارتباط با سرور');
                err.status = response.status;
                err.payload = data;
                throw err;
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // Build an absolute URL for API-served files (useful in split dev: 8000 frontend + 5001 API)
    toAbsoluteApiUrl(maybeRelativeUrl) {
        if (!maybeRelativeUrl) return maybeRelativeUrl;
        if (/^https?:\/\//i.test(maybeRelativeUrl)) return maybeRelativeUrl;

        const base = (() => {
            try {
                if (typeof this.baseUrl === 'string' && /^https?:\/\//i.test(this.baseUrl)) {
                    return new URL(this.baseUrl).origin;
                }
            } catch (_) {}
            return window.location.origin;
        })();

        try {
            return new URL(maybeRelativeUrl, base).toString();
        } catch (_) {
            return maybeRelativeUrl;
        }
    },
    
    // ==================
    // Authentication
    // ==================
    
    async register(userData) {
        const response = await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
        
        if (response.token) {
            this.setToken(response.token);
        }
        
        return response;
    },
    
    async login(email, password) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        if (response.token) {
            this.setToken(response.token);
        }
        
        return response;
    },

    async adminLogin(username, password) {
        const response = await this.request('/auth/admin-login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        
        if (response.token) {
            this.setToken(response.token);
        }
        
        return response;
    },
    
    async logout() {
        await this.request('/auth/logout', { method: 'POST' });
        this.clearToken();
    },
    
    async getMe() {
        return await this.request('/auth/me');
    },
    
    setToken(token) {
        const normalized = normalizeAuthToken(token);
        if (!normalized) {
            this.clearToken();
            return;
        }
        this.token = normalized;
        localStorage.setItem('authToken', normalized);
    },
    
    clearToken() {
        this.token = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
    },
    
    isLoggedIn() {
        return !!normalizeAuthToken(this.token);
    },
    
    // ==================
    // Licenses
    // ==================
    
    async getLicenses() {
        return await this.request('/licenses');
    },
    
    async activateLicense(licenseKey, hardwareId) {
        return await this.request('/licenses/activate', {
            method: 'POST',
            body: JSON.stringify({ license_key: licenseKey, hardware_id: hardwareId })
        });
    },
    
    async verifyLicense(licenseKey) {
        return await this.request('/licenses/verify', {
            method: 'POST',
            body: JSON.stringify({ license_key: licenseKey })
        });
    },
    
    // ==================
    // Downloads
    // ==================
    
    async getDownloads() {
        return await this.request('/downloads');
    },
    
    async requestDownload(downloadId) {
        const resp = await this.request(`/downloads/${downloadId}`, {
            method: 'POST'
        });

        // Server returns a path like `/api/downloads/file/...`.
        // If frontend is on another port, make it absolute to the API host.
        if (resp && resp.download_url) {
            resp.download_url = this.toAbsoluteApiUrl(resp.download_url);
        }

        return resp;
    },
    
    // ==================
    // Tickets
    // ==================
    
    async getTickets() {
        return await this.request('/tickets');
    },
    
    async createTicket(ticketData) {
        return await this.request('/tickets', {
            method: 'POST',
            body: JSON.stringify(ticketData)
        });
    },
    
    async replyToTicket(ticketId, message) {
        return await this.request(`/tickets/${ticketId}/reply`, {
            method: 'POST',
            body: JSON.stringify({ message })
        });
    },
    
    // ==================
    // Achievements & Gamification
    // ==================
    
    async getAchievements() {
        return await this.request('/achievements');
    },
    
    async getLeaderboard() {
        return await this.request('/leaderboard');
    },
    
    // ==================
    // Stats
    // ==================
    
    async getStats() {
        return await this.request('/stats');
    },
    
    // ==================
    // Plans & Purchase
    // ==================
    
    async getPlans() {
        return await this.request('/plans');
    },
    
    async purchasePlan(planId) {
        return await this.request('/purchase', {
            method: 'POST',
            body: JSON.stringify({ plan_id: planId })
        });
    },

    // ==================
    // License File (v2)
    // ==================

    /**
     * Generate a signed license file for an existing purchased license.
     * @param {string} licenseKey - The license key
     * @param {string} hardwareId - Optional device HWID to bind
     * @param {boolean} download - If true, triggers a .oml file download
     */
    async generateLicenseFile(licenseKey, hardwareId = '', download = false) {
        const url = `/licenses/${encodeURIComponent(licenseKey)}/file${download ? '?download=1' : ''}`;
        const resp = await this.request(url, {
            method: 'POST',
            body: JSON.stringify({ hardware_id: hardwareId })
        });
        return resp;
    },

    /**
     * Trigger a license.oml download by generating the signed file and downloading it as a blob.
     * @returns {Promise<void>}
     */
    async downloadLicenseFile(licenseKey, hardwareId = '') {
        const resp = await this.generateLicenseFile(licenseKey, hardwareId, false);
        if (resp && resp.license_file) {
            const blob = new Blob([JSON.stringify(resp.license_file, null, 2)], { type: 'application/json' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'license.oml';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
        } else {
            throw new Error('فایل لایسنس دریافت نشد');
        }
    }
};

// ==================
// UI Helpers
// ==================

const UI = {
    // نمایش Toast
    showToast(message, type = 'info') {
        // بررسی وجود کانتینر
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            padding: 16px 24px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        
        const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
        toast.innerHTML = `<i class="fas fa-${icon}"></i> ${message}`;
        
        container.appendChild(toast);
        
        // حذف بعد از 3 ثانیه
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    // نمایش لودینگ
    showLoading(element, text = 'در حال پردازش...') {
        const originalContent = element.innerHTML;
        element.dataset.originalContent = originalContent;
        element.disabled = true;
        element.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${text}`;
    },
    
    // برگرداندن حالت اولیه
    hideLoading(element) {
        element.disabled = false;
        element.innerHTML = element.dataset.originalContent;
    },
    
    // فرمت تاریخ فارسی
    formatDate(date) {
        return new Intl.DateTimeFormat('fa-IR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }).format(new Date(date));
    },
    
    // فرمت عدد فارسی
    formatNumber(num) {
        return new Intl.NumberFormat('fa-IR').format(num);
    },
    
    // بررسی ورود و هدایت
    requireAuth(redirectUrl = null) {
        if (!API.isLoggedIn()) {
            const currentUrl = window.location.pathname.split('/').pop();
            window.location.href = `login.html?redirect=${redirectUrl || currentUrl}`;
            return false;
        }
        return true;
    },
    
    // بروزرسانی نوار ناوبری بر اساس وضعیت ورود
    updateNavigation() {
        const navActions = document.querySelector('.nav-actions');
        if (!navActions) return;
        
        if (API.isLoggedIn()) {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            navActions.innerHTML = `
                <a href="dashboard.html" class="btn btn-ghost">
                    <i class="fas fa-user"></i>
                    ${user.name || 'پنل کاربری'}
                </a>
                <button class="btn btn-primary" onclick="UI.logout()">
                    <i class="fas fa-sign-out-alt"></i>
                    خروج
                </button>
            `;
        }
    },
    
    // خروج
    async logout() {
        try {
            await API.logout();
        } catch (e) {
            // حتی اگر خطا داد، لاگ‌اوت محلی انجام شود
        }
        API.clearToken();
        window.location.href = 'index.html';
    }
};

// ==================
// Form Handlers
// ==================

const Forms = {
    // فرم ورود
    async handleLogin(e) {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const email = form.querySelector('#email').value;
        const password = form.querySelector('#password').value;
        
        UI.showLoading(submitBtn, 'ورود...');
        
        try {
            const response = await API.login(email, password);
            
            // ذخیره اطلاعات کاربر
            localStorage.setItem('user', JSON.stringify(response.user));
            
            UI.showToast('ورود موفق!', 'success');
            
            // هدایت
            const redirect = new URLSearchParams(window.location.search).get('redirect');
            setTimeout(() => {
                window.location.href = redirect || 'dashboard.html';
            }, 1000);
            
        } catch (error) {
            UI.showToast(error.message || 'خطا در ورود', 'error');
            UI.hideLoading(submitBtn);
        }
    },
    
    // فرم ثبت‌نام
    async handleRegister(e) {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        const userData = {
            name: form.querySelector('#name').value,
            email: form.querySelector('#email').value,
            password: form.querySelector('#password').value,
            phone: form.querySelector('#phone')?.value
        };
        
        // بررسی تکرار رمز
        const confirmPassword = form.querySelector('#confirmPassword')?.value;
        if (confirmPassword && userData.password !== confirmPassword) {
            UI.showToast('رمز عبور و تکرار آن مطابقت ندارند', 'error');
            return;
        }
        
        UI.showLoading(submitBtn, 'ثبت‌نام...');
        
        try {
            const response = await API.register(userData);
            
            localStorage.setItem('user', JSON.stringify(response.user));
            
            UI.showToast('ثبت‌نام موفق! لایسنس آزمایشی فعال شد', 'success');
            
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1500);
            
        } catch (error) {
            UI.showToast(error.message || 'خطا در ثبت‌نام', 'error');
            UI.hideLoading(submitBtn);
        }
    },
    
    // فرم تیکت
    async handleTicket(e) {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        const ticketData = {
            title: form.querySelector('#ticketTitle').value,
            category: form.querySelector('#ticketCategory').value,
            priority: form.querySelector('#ticketPriority').value,
            description: form.querySelector('#ticketDescription').value
        };
        
        UI.showLoading(submitBtn, 'ارسال...');
        
        try {
            await API.createTicket(ticketData);
            
            UI.showToast('تیکت با موفقیت ثبت شد', 'success');
            form.reset();
            
            // بستن مودال
            document.getElementById('newTicketModal')?.classList.remove('active');
            
            // بروزرسانی لیست
            if (typeof loadTickets === 'function') {
                loadTickets();
            }
            
        } catch (error) {
            UI.showToast(error.message || 'خطا در ثبت تیکت', 'error');
        }
        
        UI.hideLoading(submitBtn);
    }
};

// ==================
// Page Initializers
// ==================

const Pages = {
    // صفحه داشبورد
    async initDashboard() {
        if (!UI.requireAuth()) return;
        
        try {
            // دریافت اطلاعات کاربر
            const userData = await API.getMe();
            localStorage.setItem('user', JSON.stringify(userData.user));
            
            // بروزرسانی UI
            this.updateDashboardUI(userData.user);
            
            // دریافت لایسنس‌ها
            const licenses = await API.getLicenses();
            this.updateLicensesUI(licenses);
            
            // دریافت دستاوردها
            const achievements = await API.getAchievements();
            this.updateAchievementsUI(achievements);
            
        } catch (error) {
            console.error('Dashboard init error:', error);
            UI.showToast('خطا در بارگذاری داشبورد', 'error');
        }
    },
    
    updateDashboardUI(user) {
        // نام کاربر
        const nameEl = document.getElementById('userName');
        if (nameEl) nameEl.textContent = user.name;
        
        // XP
        const xpEl = document.getElementById('userXP');
        if (xpEl) xpEl.textContent = UI.formatNumber(user.xp || 0);
        
        // سطح
        const levelEl = document.getElementById('userLevel');
        if (levelEl) levelEl.textContent = user.level || 1;
        
        // پیشرفت XP
        const xp = user.xp || 0;
        const level = Math.floor(xp / 1000) + 1;
        const xpInLevel = xp % 1000;
        const progress = (xpInLevel / 1000) * 100;
        
        const progressCircle = document.querySelector('.xp-progress');
        if (progressCircle) {
            progressCircle.style.background = `conic-gradient(var(--primary) ${progress}%, transparent 0)`;
        }
    },
    
    updateLicensesUI(licenses) {
        const container = document.getElementById('licensesContainer');
        if (!container || !licenses.licenses) return;
        
        if (licenses.licenses.length === 0) {
            container.innerHTML = '<p class="empty-message">هنوز لایسنسی ندارید</p>';
            return;
        }
        
        container.innerHTML = licenses.licenses.map(lic => `
            <div class="license-card ${lic.status}">
                <div class="license-header">
                    <span class="license-type">${lic.plan_name || lic.type || lic.plan || ''}</span>
                    <span class="license-status ${lic.status}">${lic.status === 'active' ? 'فعال' : 'غیرفعال'}</span>
                </div>
                <div class="license-key">${lic.key}</div>
                <div class="license-info">
                    <span>اعتبار: ${UI.formatDate(lic.expires_at)}</span>
                </div>
                ${lic.status === 'active' ? `
                <div class="license-actions" style="margin-top:12px;">
                    <button class="btn btn-sm btn-ghost download-license-file" data-key="${lic.key}" title="دانلود فایل لایسنس برای نصاب آفلاین">
                        <i class="fas fa-file-download"></i> دانلود فایل لایسنس
                    </button>
                </div>` : ''}
            </div>
        `).join('');

        // Bind download buttons
        container.querySelectorAll('.download-license-file').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const key = btn.getAttribute('data-key');
                // Optional: prompt for HWID (for device binding)
                let hwid = '';
                const useHwid = confirm('آیا می‌خواهید فایل لایسنس را به یک دستگاه خاص متصل کنید؟\n\n(اگر بله زد، مرورگر شماره سخت‌افزار دستگاه‌تان را می‌پرسد)');
                if (useHwid) {
                    hwid = prompt('شناسه سخت‌افزار (Hardware ID) دستگاه را وارد کنید:', '') || '';
                }
                try {
                    btn.disabled = true;
                    await API.downloadLicenseFile(key, (hwid || '').trim());
                    UI.showToast('فایل لایسنس دانلود شد', 'success');
                } catch (err) {
                    UI.showToast(err?.message || 'خطا در دریافت فایل لایسنس', 'error');
                } finally {
                    btn.disabled = false;
                }
            });
        });
    },
    
    updateAchievementsUI(achievements) {
        const container = document.getElementById('achievementsContainer');
        if (!container) return;
        
        container.innerHTML = achievements.map(ach => `
            <div class="achievement ${ach.earned ? 'earned' : 'locked'}">
                <div class="achievement-icon">${ach.icon}</div>
                <div class="achievement-info">
                    <h4>${ach.title}</h4>
                    <p>${ach.description}</p>
                </div>
            </div>
        `).join('');
    }
};

// ==================
// Auto-init
// ==================

document.addEventListener('DOMContentLoaded', () => {
    // بروزرسانی نوار ناوبری
    UI.updateNavigation();
    
    // اتصال فرم‌ها
    const loginForm = document.getElementById('loginForm');
    if (loginForm) loginForm.addEventListener('submit', Forms.handleLogin);
    
    const registerForm = document.getElementById('registerForm');
    if (registerForm) registerForm.addEventListener('submit', Forms.handleRegister);
    
    const ticketForm = document.getElementById('newTicketForm');
    if (ticketForm) ticketForm.addEventListener('submit', Forms.handleTicket);
    
    // اگر صفحه داشبورد است
    if (window.location.pathname.includes('dashboard')) {
        Pages.initDashboard();
    }
});

// Export برای استفاده در سایر فایل‌ها
window.API = API;
window.UI = UI;
window.Forms = Forms;
window.Pages = Pages;

// کپسول‌سازی showToast برای استفاده آسان
window.showToast = UI.showToast.bind(UI);
